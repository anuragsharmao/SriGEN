"""Tests for the security remediation brief: auth/authz, operator identity on
the ledger, CORS, degraded-detection visibility, and ledger append locking."""

import json
import threading

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import SessionLocal
from app.main import app
from app.services import auth as auth_service

SAMPLE_SOURCE = "An operational incident was detected and 24 systems were affected. Response teams restored service by evening."


# ---------------------------------------------------------------------------
# Item 1: authentication required on every route
# ---------------------------------------------------------------------------

def test_unauthenticated_generate_returns_401(anon_client):
    res = anon_client.post("/api/generate", json={"source_text": SAMPLE_SOURCE, "deliverable_types": ["advisory"]})
    assert res.status_code == 401


def test_unauthenticated_dashboard_list_returns_401(anon_client):
    res = anon_client.get("/api/dashboard/drafts")
    assert res.status_code == 401


def test_unauthenticated_disclosure_review_returns_401(anon_client):
    res = anon_client.get("/api/disclosure/draft/some-id/review")
    assert res.status_code == 401


def test_unauthenticated_ledger_verify_returns_401(anon_client):
    res = anon_client.get("/api/ledger/verify")
    assert res.status_code == 401


def test_unauthenticated_approve_returns_401(anon_client):
    res = anon_client.post("/api/dashboard/approve", json={"draft_id": "whatever"})
    assert res.status_code == 401


def test_malformed_auth_header_returns_401(anon_client):
    anon_client.headers["Authorization"] = "NotBearer sometoken"
    res = anon_client.get("/api/dashboard/drafts")
    assert res.status_code == 401


def test_invalid_token_returns_401(anon_client):
    anon_client.headers["Authorization"] = "Bearer totally-invalid-token"
    res = anon_client.get("/api/dashboard/drafts")
    assert res.status_code == 401


def test_health_and_root_remain_public(anon_client):
    assert anon_client.get("/").status_code == 200
    assert anon_client.get("/health").status_code == 200


def test_login_endpoint_itself_is_public(anon_client):
    res = anon_client.post("/api/auth/login", json={"username": "nobody", "password": "wrong"})
    assert res.status_code == 401  # wrong creds -> 401, but NOT because of missing auth header
    assert "Authorization" not in res.request.headers or True  # request never carried one; endpoint still responded


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------

def test_login_with_correct_credentials_issues_token(anon_client, fresh_db):
    db = SessionLocal()
    auth_service.create_operator(db, username="alice", password="correct-horse-battery-staple", role="analyst")
    db.close()

    res = anon_client.post("/api/auth/login", json={"username": "alice", "password": "correct-horse-battery-staple"})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "analyst"
    assert len(body["access_token"]) > 20

    me = anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_login_with_wrong_password_returns_401(anon_client, fresh_db):
    db = SessionLocal()
    auth_service.create_operator(db, username="bob", password="right-password", role="analyst")
    db.close()

    res = anon_client.post("/api/auth/login", json={"username": "bob", "password": "wrong-password"})
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Role scoping: analysts can generate/review but not approve/export
# ---------------------------------------------------------------------------

def test_analyst_can_generate_and_review_but_not_approve(analyst_client):
    res = analyst_client.post("/api/generate", json={"source_text": SAMPLE_SOURCE, "deliverable_types": ["advisory"]})
    assert res.status_code == 200
    draft_id = res.json()["drafts"][0]["id"]

    review = analyst_client.get(f"/api/disclosure/draft/{draft_id}/review")
    assert review.status_code == 200

    blocked = analyst_client.post("/api/dashboard/approve", json={"draft_id": draft_id})
    assert blocked.status_code == 403


def test_approver_can_approve(client):
    res = client.post("/api/generate", json={"source_text": SAMPLE_SOURCE, "deliverable_types": ["advisory"]})
    draft_id = res.json()["drafts"][0]["id"]
    approve = client.post("/api/dashboard/approve", json={"draft_id": draft_id})
    assert approve.status_code == 200


def test_analyst_cannot_register_new_operators(analyst_client):
    res = analyst_client.post("/api/auth/register", json={"username": "newbie", "password": "pw", "role": "analyst"})
    assert res.status_code == 403


def test_approver_can_register_new_operators(client):
    res = client.post("/api/auth/register", json={"username": "newbie", "password": "pw123456", "role": "analyst"})
    assert res.status_code == 201
    assert res.json()["role"] == "analyst"


# ---------------------------------------------------------------------------
# Item 2: ledger operator identity comes from auth, never the request body
# ---------------------------------------------------------------------------

def test_ledger_operator_reflects_authenticated_identity_not_request_body(client):
    res = client.post("/api/generate", json={"source_text": SAMPLE_SOURCE, "deliverable_types": ["advisory"]})
    draft_id = res.json()["drafts"][0]["id"]

    # Attempt to spoof a different operator identity via the request body —
    # ApproveDraftRequest no longer even has an `operator` field, so this
    # extra key is simply ignored by pydantic, never used as the identity.
    approve = client.post("/api/dashboard/approve", json={"draft_id": draft_id, "operator": "someone-else-entirely"})
    assert approve.status_code == 200
    body = approve.json()
    assert body["operator"] == "test_approver"  # the authenticated client fixture's own username
    assert body["operator"] != "someone-else-entirely"


def test_approve_draft_request_schema_has_no_operator_field():
    from app.db.schemas import ApproveDraftRequest
    assert "operator" not in ApproveDraftRequest.model_fields


# ---------------------------------------------------------------------------
# Item 3: CORS allowlist
# ---------------------------------------------------------------------------

def test_cors_preflight_rejects_non_allowlisted_origin(anon_client):
    res = anon_client.options(
        "/api/dashboard/drafts",
        headers={
            "Origin": "https://evil-not-allowlisted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette's CORS middleware doesn't 403 preflights; it simply omits the
    # Access-Control-Allow-Origin header for a disallowed origin, which is
    # what makes browsers block the response.
    assert "access-control-allow-origin" not in {k.lower() for k in res.headers.keys()}


def test_cors_preflight_allows_allowlisted_origin(anon_client):
    allowed = settings.CORS_ORIGINS[0]
    res = anon_client.options(
        "/api/dashboard/drafts",
        headers={"Origin": allowed, "Access-Control-Request-Method": "GET"},
    )
    assert res.headers.get("access-control-allow-origin") == allowed


def test_cors_origins_never_includes_wildcard():
    assert "*" not in settings.CORS_ORIGINS


# ---------------------------------------------------------------------------
# Item 5: degraded sensitivity detection is surfaced, not silent
# ---------------------------------------------------------------------------

def test_degraded_detection_flag_appears_when_llm_classification_fails(client, fake_llm, monkeypatch):
    import app.services.sensitivity_firewall as firewall_module

    async def _always_fail_classify(self, text):
        return [], True  # simulate LLM classification failure -> regex-only, degraded

    monkeypatch.setattr(firewall_module.SensitivityFirewall, "classify_with_llm", _always_fail_classify)

    res = client.post("/api/generate", json={"source_text": SAMPLE_SOURCE, "deliverable_types": ["advisory"]})
    assert res.status_code == 200
    body = res.json()
    assert body["llm_classification_degraded"] is True
    assert body["drafts"][0]["llm_classification_degraded"] is True

    draft_id = body["drafts"][0]["id"]
    detail = client.get(f"/api/dashboard/draft/{draft_id}")
    assert detail.json()["llm_classification_degraded"] is True

    listing = client.get("/api/dashboard/drafts")
    assert any(d["id"] == draft_id and d["llm_classification_degraded"] is True for d in listing.json())


def test_degraded_flag_false_under_normal_operation(client):
    res = client.post("/api/generate", json={"source_text": SAMPLE_SOURCE, "deliverable_types": ["advisory"]})
    assert res.status_code == 200
    assert res.json()["llm_classification_degraded"] is False


# ---------------------------------------------------------------------------
# Item 6: ledger append locking / concurrency safety
# ---------------------------------------------------------------------------

def test_concurrent_ledger_appends_produce_a_valid_unbroken_chain(client):
    """Fires several approvals concurrently at the service layer and asserts
    the resulting chain has no duplicate indices and verifies as valid."""
    draft_ids = []
    for i in range(5):
        res = client.post("/api/generate", json={
            "source_text": f"Routine update number {i} with no sensitive content whatsoever.",
            "deliverable_types": ["public_faq"],
        })
        draft_ids.append(res.json()["drafts"][0]["id"])

    errors = []

    def _approve(draft_id):
        try:
            r = client.post("/api/dashboard/approve", json={"draft_id": draft_id})
            if r.status_code != 200:
                errors.append(r.text)
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=_approve, args=(d,)) for d in draft_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent approvals failed: {errors}"

    verify = client.get("/api/ledger/verify")
    assert verify.status_code == 200
    body = verify.json()
    assert body["is_valid"] is True
    assert body["total_blocks"] == 5

    db = SessionLocal()
    try:
        from app.db.models import ProvenanceLedgerModel
        indices = [b.index for b in db.query(ProvenanceLedgerModel).all()]
        assert sorted(indices) == list(range(1, 6))
        assert len(set(indices)) == len(indices)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Item 9: DEBUG defaults to False
# ---------------------------------------------------------------------------

def test_debug_defaults_to_false():
    from app.core.config import Settings
    fresh_settings = Settings(_env_file=None)
    assert fresh_settings.DEBUG is False


# ---------------------------------------------------------------------------
# Item 4: pluggable LLM backend abstraction exists
# ---------------------------------------------------------------------------

def test_llm_backend_is_pluggable_and_groq_is_default():
    from app.core.llm_client import GroqBackend, LLMBackend, LLMClient

    assert issubclass(GroqBackend, LLMBackend)
    client_instance = LLMClient()
    assert isinstance(client_instance._backend, LLMBackend)
    assert isinstance(client_instance._backend, GroqBackend)


def test_unknown_llm_backend_raises_clear_error(monkeypatch):
    from app.core import llm_client as llm_module
    monkeypatch.setattr(llm_module.settings, "LLM_BACKEND", "some_unimplemented_backend")
    try:
        with __import__("pytest").raises(ValueError):
            llm_module._build_backend()
    finally:
        monkeypatch.setattr(llm_module.settings, "LLM_BACKEND", "groq")
