"""Test configuration and FakeLLMClient fixture for SriGEN.

IMPORTANT: there is exactly ONE FakeLLMClient instance for the whole test
session (`fake_llm_client`, exposed via the `fake_llm` fixture). Every test
that needs to simulate an LLM failure or inspect call history must go through
that fixture — creating a second, separate FakeLLMClient and mutating it has
no effect, since it is never the instance actually patched into the app
modules (this was a real bug in the previous test suite: a module-level
`default_fake` was created and mutated, while an unrelated autouse fixture
patched in a completely different instance every test).
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import app.adapters.base as base_module
import app.services.content_refiner as content_refiner_module
import app.services.fact_fixer as fact_fixer_module
import app.services.fact_graph as fact_graph_module
import app.services.grounding_guard as grounding_guard_module
from app.core import llm_client as llm_client_module
from app.core.llm_client import LLMUnavailableError
from app.db.database import Base, SessionLocal, engine, get_db
from app.db.schemas import (
    ClaimEntailmentJudgement,
    ConsistencyJudgement,
    ContentRefineResult,
    FactEntity,
    FactFixResult,
    FactGraph,
    FactNumberDate,
    FactStatement,
    InfographicPackage,
    InfographicSection,
    PolicyComplianceJudgement,
    PresentationPackage,
    SensitivityClassificationResult,
    Slide,
    SubtitleCue,
    VideoPackage,
    VideoScene,
)
from app.main import app


class FakeLLMClient:
    """Deterministic stand-in for LLMClient. Dispatches structured_completion by
    response_model.__name__ so it never needs to know about call sites."""

    def __init__(self):
        self.should_fail = False
        self.complete_calls: List[Dict[str, str]] = []
        self.structured_calls: List[Dict[str, Any]] = []

    def reset(self):
        self.should_fail = False
        self.complete_calls.clear()
        self.structured_calls.clear()

    async def check_reachable(self) -> bool:
        return not self.should_fail

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        stage: str = "generation",
    ) -> str:
        if self.should_fail:
            raise LLMUnavailableError(f"Simulated LLM unavailable at stage {stage}", stage=stage)
        self.complete_calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt, "model": model})

        # Echo the raw source-context section back into the "generated" text so
        # tests exercising the output-side disclosure scan (and grounding
        # checks) have real source content to detect, just as a real LLM would
        # naturally carry facts (including sensitive raw values, since
        # generation reads the raw source directly) through into its output.
        source_excerpt = ""
        marker = "=== SOURCE TEXT CONTEXT ==="
        if marker in user_prompt:
            after = user_prompt.split(marker, 1)[1]
            end_marker = "=== OPERATOR DELIVERABLE SPEC ==="
            source_excerpt = after.split(end_marker, 1)[0].strip()

        return (
            "This is a deterministic test deliverable generated from the canonical fact graph. "
            f"{source_excerpt}"
        ).strip()

    async def structured_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        model: Optional[str] = None,
        stage: str = "generation",
    ) -> BaseModel:
        if self.should_fail:
            raise LLMUnavailableError(f"Simulated LLM unavailable at stage {stage}", stage=stage)
        self.structured_calls.append({"model_name": response_model.__name__, "user_prompt": user_prompt, "model": model})

        name = response_model.__name__

        if name == "FactGraph":
            return FactGraph(
                source_title="Test Incident Report",
                summary="A test incident affecting several systems was reported and contained.",
                entities=[
                    FactEntity(name="Sector-7 Facility", category="LOCATION", native_forms={"hi": "सेक्टर-7 सुविधा"}),
                    FactEntity(name="Regional Response Team", category="ORG", native_forms={}),
                ],
                facts=[
                    FactStatement(statement="An incident was detected and contained.", category="KEY_FACT"),
                    FactStatement(statement="Response teams restored affected systems.", category="RESPONSE_ACTIONS"),
                ],
                numbers_and_dates=[
                    FactNumberDate(value="24", unit="systems", context="systems affected by the incident"),
                ],
                policy_constraints=[],
            )

        if name == "SensitivityClassificationResult":
            # Regex layer (structural patterns) covers the test suite's sensitivity
            # cases; the fake semantic layer deliberately adds nothing extra so
            # tests stay deterministic.
            return SensitivityClassificationResult(sensitive_spans=[])

        if name == "ClaimEntailmentJudgement":
            # Deliberately always "entailed": the deterministic NUMBER/DATE hard
            # override in grounding_guard.verify_claim is what actually catches
            # factual tampering in tests, independent of this fake judgement.
            return ClaimEntailmentJudgement(entailed=True, confidence=0.95, reasoning="Entailed by source context.")

        if name == "ConsistencyJudgement":
            return ConsistencyJudgement(
                is_consistent=True,
                contradictions=[],
                total_facts_checked=3,
                confidence=0.95,
                explanation="No contradictions detected across drafts.",
            )

        if name == "PolicyComplianceJudgement":
            return PolicyComplianceJudgement(total_flagged=0, unresolved_violations=0, violation_details=[])

        if name == "FactFixResult":
            return self._fake_fact_fix(system_prompt)

        if name == "ContentRefineResult":
            return self._fake_content_refine(system_prompt)

        if name == "PresentationPackage":
            return PresentationPackage(
                title="Test Presentation",
                subtitle="Generated for testing",
                slides=[
                    Slide(slide_number=1, layout="title", title="Test Presentation", bullets=[], speaker_notes="Welcome the audience and frame the incident.", visual_suggestion="Title card with agency seal"),
                    Slide(slide_number=2, layout="bullets", title="Key Facts", bullets=["Incident detected", "Systems affected: 24"], speaker_notes="Walk through the key facts from the fact graph.", visual_suggestion="Icon row of affected systems"),
                    Slide(slide_number=3, layout="closing", title="Next Steps", bullets=["Continue monitoring"], speaker_notes="Close with the recommended next steps and point of contact.", visual_suggestion="Contact card"),
                ],
            )

        if name == "InfographicPackage":
            return InfographicPackage(
                title="Test Infographic",
                key_message="The incident was detected and contained quickly.",
                sections=[
                    InfographicSection(heading="Systems Affected", stat_value="24", stat_label="systems", body="Systems affected by the incident.", icon_hint="alert"),
                    InfographicSection(heading="Response", body="Response teams restored affected systems.", icon_hint="shield"),
                ],
                layout_recommendation="Vertical 3-band layout, stat row at 40% height, dark accent header.",
                color_palette=["#1a1a2e", "#e94560"],
                footer="Source: Test Incident Report",
            )

        if name == "VideoPackage":
            return VideoPackage(
                title="Test Video Package",
                total_duration_seconds=45.0,
                narration_script="An incident was detected. Response teams restored affected systems.",
                scenes=[
                    VideoScene(scene_number=1, start_seconds=0, end_seconds=20, visual_description="Establishing shot of the facility.", narration="An incident was detected.", on_screen_text="INCIDENT DETECTED"),
                    VideoScene(scene_number=2, start_seconds=20, end_seconds=45, visual_description="Response teams at work.", narration="Response teams restored affected systems.", on_screen_text=None),
                ],
                subtitles=[
                    SubtitleCue(index=1, start_seconds=0, end_seconds=3, text="An incident was detected."),
                    SubtitleCue(index=2, start_seconds=3, end_seconds=6, text="Response teams restored affected systems, ensuring continuity of operations across the facility."),
                ],
                visual_recommendations=["Wide establishing shot of the facility", "Data callout showing systems restored"],
            )

        # Fallback: instantiate with defaults for any model not explicitly handled.
        return response_model()

    @staticmethod
    def _extract_between(text: str, start_marker: str, end_marker: str) -> str:
        if start_marker not in text:
            return ""
        after = text.split(start_marker, 1)[1]
        if end_marker in after:
            return after.split(end_marker, 1)[0].strip()
        return after.strip()

    @staticmethod
    def _numbers_in(text: str) -> List[str]:
        return re.findall(r"\b\d+\b", text)

    def _fake_fact_fix(self, system_prompt: str) -> "FactFixResult":
        """Deterministic fake: finds a number present in DRAFT but absent from
        CLAIMED SOURCE, and a number present in SOURCE but absent from DRAFT,
        and swaps the former for the latter. Mirrors what a real correction
        pass does for a single swapped-number case (Test 2 in the Refine spec)."""
        draft = self._extract_between(system_prompt, "DRAFT\n\n", "\n\n--------------------------------------------------\n\nCLAIMED SOURCE")
        source = self._extract_between(system_prompt, "CLAIMED SOURCE\n\n", "\n\n--------------------------------------------------\n\nDETECTED FACTUAL PROBLEMS")

        draft_numbers = set(self._numbers_in(draft))
        source_numbers = set(self._numbers_in(source))
        bad_numbers = draft_numbers - source_numbers
        candidate_corrections = source_numbers - draft_numbers

        corrected = draft
        changes = []
        if len(bad_numbers) == 1 and len(candidate_corrections) == 1:
            bad = next(iter(bad_numbers))
            good = next(iter(candidate_corrections))
            corrected = re.sub(rf"\b{re.escape(bad)}\b", good, draft)
            changes.append(f"Corrected number '{bad}' to '{good}' per claimed source.")

        if not changes:
            return FactFixResult(corrected_content=draft or "corrected content", changes_summary="No unambiguous single-number correction was identified from the flagged issues.", unresolved_flags=[])

        return FactFixResult(corrected_content=corrected, changes_summary=" ".join(changes), unresolved_flags=[])

    def _fake_content_refine(self, system_prompt: str) -> "ContentRefineResult":
        """Deterministic fake: echoes CONTENT largely unchanged (so factual
        content — including numbers — is naturally preserved for grounding
        assertions), applies one visible, testable transformation per
        explicitly-requested dimension, and NEVER inserts a number from
        EXTRA INSTRUCTIONS that conflicts with CLAIMED SOURCE (Test 13)."""
        content = self._extract_between(system_prompt, "CONTENT TO REFINE\n\n", "\n\n--------------------------------------------------\n\nCLAIMED SOURCE")
        source = self._extract_between(system_prompt, "\n\nCLAIMED SOURCE\n\n", "\n\n--------------------------------------------------\n\nOUTPUT REQUIREMENTS")
        spec_block = self._extract_between(system_prompt, "DELIVERABLE SPECIFICATION\n\n", "\n\n--------------------------------------------------\n\nHOW TO APPLY")
        extra = self._extract_between(system_prompt, "EXTRA INSTRUCTIONS\n\n", "\n\nTreat extra instructions")

        refined = content or "refined content"
        changes: List[str] = []

        active_dims = [line.split(":", 1)[0].strip() for line in spec_block.splitlines() if line.strip() and "KEEP AS IS" not in line]
        kept_dims = [line.split(":", 1)[0].strip() for line in spec_block.splitlines() if "KEEP AS IS" in line]

        if active_dims:
            changes.append(f"Actively transformed: {', '.join(active_dims)}.")
        if kept_dims:
            changes.append(f"Preserved as-is: {', '.join(kept_dims)}.")

        # Length=Brief: meaningfully condense (first sentence only) — a real,
        # visible transformation, not cosmetic.
        if "Length: Brief" in spec_block:
            first_sentence = refined.split(". ")[0].strip()
            if first_sentence:
                refined = first_sentence if first_sentence.endswith(".") else first_sentence + "."
            changes.append("Condensed for Brief length.")

        # Extra-instruction numeric conflict detection: if extra instructions
        # mention a number that isn't in the claimed source, never inject it —
        # the echoed `refined` content already only carries source-grounded
        # numbers, so this is enforced by construction; just surface the conflict.
        extra_numbers = set(self._numbers_in(extra))
        source_numbers = set(self._numbers_in(source))
        conflicting = extra_numbers - source_numbers
        if conflicting:
            changes.append(
                f"Ignored extra-instruction request to use unsupported number(s) {sorted(conflicting)}; "
                f"kept source-grounded value(s) instead."
            )

        if not changes:
            changes.append("No structured dimensions or extra instructions required a change.")

        return ContentRefineResult(refined_content=refined, changes_summary=" ".join(changes))

    async def describe_image(self, image_bytes: bytes, mime_type: str, prompt: str, model: Optional[str] = None, stage: str = "ingestion") -> str:
        if self.should_fail:
            raise LLMUnavailableError(f"Simulated LLM unavailable at stage {stage}", stage=stage)
        return "A test image showing a facility exterior. Visible text: 'SECTOR-7 ENTRANCE'."

    async def transcribe_audio(self, audio_bytes: bytes, filename: str, model: Optional[str] = None, stage: str = "ingestion") -> str:
        if self.should_fail:
            raise LLMUnavailableError(f"Simulated LLM unavailable at stage {stage}", stage=stage)
        return "This is a test transcription of the audio recording describing the incident response."


# Single shared instance for the whole test session.
fake_llm_client = FakeLLMClient()


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    """Resets and (re-)patches the ONE shared FakeLLMClient into every module
    that imported `llm_client` at module scope, before every test. Modules that
    do a local/dynamic `from app.core.llm_client import llm_client` (ingestion,
    sensitivity_firewall) automatically pick up this same patched instance at
    call time, since they read it from `app.core.llm_client` fresh each call."""
    fake_llm_client.reset()
    monkeypatch.setattr(llm_client_module, "llm_client", fake_llm_client)
    monkeypatch.setattr(grounding_guard_module, "llm_client", fake_llm_client)
    monkeypatch.setattr(fact_graph_module, "llm_client", fake_llm_client)
    monkeypatch.setattr(base_module, "llm_client", fake_llm_client)
    monkeypatch.setattr(fact_fixer_module, "llm_client", fake_llm_client)
    monkeypatch.setattr(content_refiner_module, "llm_client", fake_llm_client)
    yield fake_llm_client


@pytest.fixture(autouse=True)
def fresh_db():
    """Every test starts with clean tables."""
    import app.db.models  # noqa: F401 ensure models registered
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


DEFAULT_TEST_USERNAME = "test_approver"
DEFAULT_TEST_PASSWORD = "test-password-not-for-production"


def _bootstrap_and_issue_token(role: str = "approver", username: str = DEFAULT_TEST_USERNAME, password: str = DEFAULT_TEST_PASSWORD) -> str:
    """Creates an operator directly (bypassing HTTP) and issues a session
    token for it — used to pre-authenticate the default `client` fixture so
    the bulk of the suite doesn't need to thread login calls through every test."""
    from app.services import auth as auth_service

    db = SessionLocal()
    try:
        existing = db.query(auth_service.OperatorModel).filter(auth_service.OperatorModel.username == username).first()
        operator = existing or auth_service.create_operator(db, username=username, password=password, role=role)
        return auth_service.issue_session(db, operator)
    finally:
        db.close()


@pytest.fixture
def client(fresh_db):
    """Pre-authenticated TestClient with an 'approver'-role bearer token
    attached by default, so the bulk of the suite (which exercises normal,
    authorized behavior) doesn't need to handle login on every test. Use
    `anon_client` for tests that specifically need to exercise unauthenticated
    or under-privileged requests."""
    with TestClient(app) as c:
        token = _bootstrap_and_issue_token(role="approver")
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest.fixture
def anon_client(fresh_db):
    """Plain TestClient with NO Authorization header — for testing that
    unauthenticated requests are correctly rejected."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def analyst_client(fresh_db):
    """Pre-authenticated as an 'analyst' (not 'approver') — for testing that
    role-scoped endpoints (approve/export) correctly reject the analyst role."""
    with TestClient(app) as c:
        token = _bootstrap_and_issue_token(role="analyst", username="test_analyst", password="test-password-not-for-production")
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def setup_fresh_db():
    """Kept for any test that wants an explicit mid-test reset beyond the
    autouse fresh_db fixture (e.g. resetting after intentionally leaving
    partial state)."""
    import app.db.models  # noqa: F401
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
