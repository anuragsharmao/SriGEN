"""Tests for the three remediation fixes applied on top of the reviewed backend:

1. Policy Dimension of the Trust Score was hardcoded to 100.0 regardless of
   fact_graph.policy_constraints; now actually evaluated via
   grounding_guard.evaluate_policy_compliance() (app/prompts/policy_prompt.txt
   + PolicyComplianceJudgement, both of which already existed but were never
   called from anywhere).
2. `language: Auto` on a GenerateRequest always resolved to English, never the
   actual detected source language; now resolved via
   app/services/ingestion.py::detect_source_language (Devanagari-density
   heuristic) and threaded through the orchestrator into the resolver.
3. Generation's raw source-text context was silently truncated at a hardcoded
   4000 chars; now a documented, configurable
   settings.MAX_GENERATION_CONTEXT_CHARS, with truncation surfaced (never
   silent) via GenerateResponse.source_context_truncated and a loud log line.
"""

import asyncio

import pytest

from app.core.config import settings
from app.db.schemas import LanguageType
from app.services.ingestion import detect_source_language

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

SAMPLE_SOURCE = """
An operational incident was detected at Sector-7 on 15 August, affecting 24 systems.
Unit 4821 responded within the hour and restored all affected systems by evening.
No further disruption has been reported since containment was completed.
"""

HINDI_SOURCE = (
    "सेक्टर-7 में 15 अगस्त को एक परिचालन घटना का पता चला, जिससे 24 प्रणालियाँ प्रभावित हुईं। "
    "यूनिट 4821 ने एक घंटे के भीतर प्रतिक्रिया दी और शाम तक सभी प्रभावित प्रणालियों को बहाल कर दिया। "
    "नियंत्रण पूरा होने के बाद से किसी और व्यवधान की सूचना नहीं मिली है।"
)


# ---------------------------------------------------------------------------
# Fix 1: Policy Dimension actually evaluated, not hardcoded
# ---------------------------------------------------------------------------

def test_policy_score_is_100_with_no_constraints_and_skips_llm_call(fake_llm):
    """Common case: source states no explicit policy constraint -> (0, 0, [])
    without spending an LLM call at all (asserted via structured_calls)."""
    from app.services.grounding_guard import grounding_guard

    calls_before = len(fake_llm.structured_calls)
    flagged, unresolved, details = asyncio.run(grounding_guard.evaluate_policy_compliance(
        content="Some generated deliverable text.",
        policy_constraints=[],
    ))
    assert (flagged, unresolved, details) == (0, 0, [])
    assert len(fake_llm.structured_calls) == calls_before  # no LLM call was made


def test_policy_score_reflects_llm_judgement_when_constraints_present(fake_llm, monkeypatch):
    """With non-empty constraints, the (now-wired) PolicyComplianceJudgement
    call is actually made and its result actually used."""
    from app.db.schemas import PolicyComplianceJudgement
    from app.services import grounding_guard as gg_module

    async def fake_structured_completion(system_prompt, user_prompt, response_model, model=None, stage="generation"):
        assert response_model is PolicyComplianceJudgement
        return PolicyComplianceJudgement(
            total_flagged=2,
            unresolved_violations=1,
            violation_details=["Mentions an unreleased operation codename."],
        )

    monkeypatch.setattr(fake_llm, "structured_completion", fake_structured_completion)

    flagged, unresolved, details = asyncio.run(gg_module.grounding_guard.evaluate_policy_compliance(
        content="Operation Falcon details were included verbatim.",
        policy_constraints=["Do not name unreleased operation codenames."],
    ))
    assert flagged == 2
    assert unresolved == 1
    assert details == ["Mentions an unreleased operation codename."]


def test_policy_check_fails_open_on_llm_error(fake_llm):
    """A policy-judge outage must never block generation — fails open to
    zero flagged violations, same posture as the consistency/entailment
    fallbacks elsewhere in grounding_guard.py."""
    from app.services.grounding_guard import grounding_guard

    fake_llm.should_fail = True
    flagged, unresolved, details = asyncio.run(grounding_guard.evaluate_policy_compliance(
        content="Some text.",
        policy_constraints=["Some constraint that will never actually be checked."],
    ))
    assert (flagged, unresolved, details) == (0, 0, [])


def test_trust_score_calculator_uses_policy_flagged_and_unresolved():
    """Direct unit check on the (pre-existing, previously-unused) calculator
    path: unresolved violations pull the composite score down via the 20%
    Policy weight, rather than always landing on a flat 100."""
    from app.services.trust_score import trust_score_calculator

    breakdown_clean = trust_score_calculator.calculate_score(
        claim_results=[], consistency_score_override=100.0,
        total_flagged=0, unresolved_violations=0,
    )
    assert breakdown_clean.policy_score == 100.0

    breakdown_violated = trust_score_calculator.calculate_score(
        claim_results=[], consistency_score_override=100.0,
        total_flagged=2, unresolved_violations=1,
    )
    assert breakdown_violated.policy_score == 50.0  # 1 - (1/2)
    assert breakdown_violated.composite_trust_score < breakdown_clean.composite_trust_score


def test_generate_endpoint_surfaces_policy_violations_field(client):
    """End-to-end: /api/generate response now carries a policy_violations
    field per draft (empty list in the default no-constraint case, but the
    field itself must exist so a frontend can render it once populated)."""
    res = client.post("/api/generate", json={
        "source_text": SAMPLE_SOURCE,
        "deliverable_types": ["advisory"],
    })
    assert res.status_code == 200
    draft = res.json()["drafts"][0]
    assert "policy_violations" in draft
    assert draft["policy_violations"] == []
    assert draft["trust_score"]["policy_score"] == 100.0


# ---------------------------------------------------------------------------
# Fix 2: language: Auto resolves against the real detected source language
# ---------------------------------------------------------------------------

def test_detect_source_language_english():
    assert detect_source_language(SAMPLE_SOURCE) == LanguageType.ENGLISH


def test_detect_source_language_hindi():
    assert detect_source_language(HINDI_SOURCE) == LanguageType.HINDI


def test_detect_source_language_single_quoted_hindi_term_stays_english():
    """A lone Hindi proper noun quoted inside an English document must not
    flip the whole-document detection — guards the dominance threshold."""
    mixed = SAMPLE_SOURCE + " The unit is locally known as 'सेक्टर-7'."
    assert detect_source_language(mixed) == LanguageType.ENGLISH


def test_detect_source_language_empty_text_defaults_english():
    assert detect_source_language("   ") == LanguageType.ENGLISH


def test_generate_with_hindi_source_and_auto_language_resolves_to_hindi(client):
    """The actual end-to-end bug fix: previously this always produced English
    specs regardless of source language."""
    res = client.post("/api/generate", json={
        "source_text": HINDI_SOURCE,
        "deliverable_types": ["advisory"],
        "language": "Auto",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["detected_source_language"] == "Hindi"

    from app.db.database import SessionLocal
    from app.db.models import DeliverableDraftModel
    import json as jsonlib

    db = SessionLocal()
    try:
        draft = db.query(DeliverableDraftModel).filter(DeliverableDraftModel.source_id == body["source_id"]).first()
        spec = jsonlib.loads(draft.spec_json)
        assert spec["language"] == "Hindi"
    finally:
        db.close()


def test_generate_with_english_source_and_auto_language_resolves_to_english(client):
    res = client.post("/api/generate", json={
        "source_text": SAMPLE_SOURCE,
        "deliverable_types": ["advisory"],
        "language": "Auto",
    })
    assert res.status_code == 200
    assert res.json()["detected_source_language"] == "English"


def test_explicit_language_request_overrides_detection(client):
    """An operator-specified language (not Auto) must still win over
    detection, unchanged from prior behavior."""
    res = client.post("/api/generate", json={
        "source_text": HINDI_SOURCE,
        "deliverable_types": ["advisory"],
        "language": "English",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["detected_source_language"] == "Hindi"  # detection is still reported...

    from app.db.database import SessionLocal
    from app.db.models import DeliverableDraftModel
    import json as jsonlib

    db = SessionLocal()
    try:
        draft = db.query(DeliverableDraftModel).filter(DeliverableDraftModel.source_id == body["source_id"]).first()
        spec = jsonlib.loads(draft.spec_json)
        assert spec["language"] == "English"  # ...but the explicit request still wins
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fix 3: generation context truncation is configurable and never silent
# ---------------------------------------------------------------------------

def test_max_generation_context_chars_is_configurable():
    assert hasattr(settings, "MAX_GENERATION_CONTEXT_CHARS")
    assert settings.MAX_GENERATION_CONTEXT_CHARS > 4000  # raised from the old hardcoded value


def test_generate_response_reports_no_truncation_for_short_source(client):
    res = client.post("/api/generate", json={
        "source_text": SAMPLE_SOURCE,
        "deliverable_types": ["advisory"],
    })
    assert res.status_code == 200
    assert res.json()["source_context_truncated"] is False


def test_generate_response_reports_truncation_for_long_source(client, monkeypatch):
    from app.core.config import settings as settings_module
    monkeypatch.setattr(settings_module, "MAX_GENERATION_CONTEXT_CHARS", 100)

    long_source = SAMPLE_SOURCE * 20  # comfortably over the lowered 100-char limit
    res = client.post("/api/generate", json={
        "source_text": long_source,
        "deliverable_types": ["advisory"],
    })
    assert res.status_code == 200
    assert res.json()["source_context_truncated"] is True


def test_fact_graph_extraction_receives_full_untruncated_text(client, fake_llm, monkeypatch):
    """The truncation cap must apply ONLY to the adapter's raw-context slice,
    never to Fact Graph extraction — the Fact Graph stays the complete,
    canonical source of truth regardless of this limit."""
    from app.core.config import settings as settings_module
    monkeypatch.setattr(settings_module, "MAX_GENERATION_CONTEXT_CHARS", 50)

    long_source = SAMPLE_SOURCE * 20
    res = client.post("/api/generate", json={
        "source_text": long_source,
        "deliverable_types": ["advisory"],
    })
    assert res.status_code == 200

    fact_graph_calls = [c for c in fake_llm.structured_calls if c["model_name"] == "FactGraph"]
    assert len(fact_graph_calls) == 1
    # The full (untruncated) source text must have reached the Fact Graph prompt.
    assert long_source.strip()[-50:] in fact_graph_calls[0]["user_prompt"]
