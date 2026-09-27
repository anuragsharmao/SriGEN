"""Tests for the LLM token-optimization changes to Fact Graph extraction:
  - app/services/fact_graph.py::_batch_chunks (chunk batching)
  - app/services/fact_graph.py::FactGraphService._extract_batch (labeled
    multi-chunk calls + chunk-id attribution fallback)
  - app/services/text_cleaning.py::clean_text (pre-chunking boilerplate strip)

See docs/token_optimization_plan.md for the design rationale.
"""

import asyncio

from app.services.fact_graph import _batch_chunks, _ChunkLike, fact_graph_service
from app.services.grounding_guard import grounding_guard
from app.services.text_cleaning import clean_text


# ---------------------------------------------------------------------------
# _batch_chunks
# ---------------------------------------------------------------------------

def _chunk(id_, n_chars):
    return _ChunkLike(id=id_, text="x" * n_chars, page_start=None, page_end=None)


def test_batch_chunks_groups_small_chunks_into_one_batch():
    chunks = [_chunk("c1", 1000), _chunk("c2", 1000), _chunk("c3", 1000)]
    batches = _batch_chunks(chunks, max_chars=5000)
    assert len(batches) == 1
    assert [c.id for c in batches[0]] == ["c1", "c2", "c3"]


def test_batch_chunks_splits_when_over_budget():
    chunks = [_chunk("c1", 3000), _chunk("c2", 3000), _chunk("c3", 3000)]
    batches = _batch_chunks(chunks, max_chars=5000)
    # c1 alone (3000), c2 would push to 6000 > 5000 so it starts a new
    # batch; c3 would push that batch to 6000 too, so it starts a third.
    assert len(batches) == 3
    assert [c.id for b in batches for c in b] == ["c1", "c2", "c3"]


def test_batch_chunks_never_drops_or_reorders_chunks():
    chunks = [_chunk(f"c{i}", 500) for i in range(10)]
    batches = _batch_chunks(chunks, max_chars=1200)
    flat = [c.id for b in batches for c in b]
    assert flat == [f"c{i}" for i in range(10)]


def test_batch_chunks_oversized_single_chunk_gets_its_own_batch():
    chunks = [_chunk("small", 100), _chunk("huge", 10_000)]
    batches = _batch_chunks(chunks, max_chars=5000)
    assert any(len(b) == 1 and b[0].id == "huge" for b in batches)


# ---------------------------------------------------------------------------
# FactGraphService._extract_batch — chunk-id attribution fallback
# ---------------------------------------------------------------------------

def test_extract_batch_falls_back_to_all_batch_ids_when_llm_tags_are_unreliable(fake_llm):
    """FakeLLMClient's canned FactGraph never sets source_chunk_id(s), so
    every fact/entity should fall back to the whole batch's chunk ids
    rather than being left with an empty/invalid attribution."""
    batch = [_chunk("chunk-0", 500), _chunk("chunk-1", 500)]
    fact_graph = asyncio.run(fact_graph_service._extract_batch(batch))

    assert len(fact_graph.entities) >= 1
    for ent in fact_graph.entities:
        assert set(ent.source_chunk_ids) == {"chunk-0", "chunk-1"}
    for fact in fact_graph.facts:
        assert fact.source_chunk_id is None  # never a hallucinated id


def test_extract_batch_single_chunk_matches_extract_single_call_shape(fake_llm):
    """A one-chunk batch must take the plain _extract_single path (no
    CHUNK/END CHUNK labels in the prompt) — zero behavior change for the
    common case where batching doesn't actually combine anything."""
    batch = [_chunk("only-chunk", 500)]
    asyncio.run(fact_graph_service._extract_batch(batch))
    calls = [c for c in fake_llm.structured_calls if c["model_name"] == "FactGraph"]
    assert len(calls) == 1
    assert "--- CHUNK" not in calls[-1]["user_prompt"]


# ---------------------------------------------------------------------------
# Per-stage model routing (GROQ_REASONING_MODEL for fact-graph/sensitivity,
# GROQ_DEFAULT_MODEL implicitly for everything else)
# ---------------------------------------------------------------------------

def test_fact_graph_extraction_uses_reasoning_model(fake_llm):
    from app.core.config import settings

    asyncio.run(fact_graph_service.extract_fact_graph("Some short single-chunk source text."))
    calls = [c for c in fake_llm.structured_calls if c["model_name"] == "FactGraph"]
    assert len(calls) == 1
    assert calls[-1]["model"] == settings.GROQ_REASONING_MODEL
    assert calls[-1]["model"] != settings.GROQ_DEFAULT_MODEL


def test_fact_graph_batch_extraction_uses_reasoning_model(fake_llm, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(fact_graph_service, "BATCH_MAX_CHARS", 100)
    batch = [_chunk("c0", 500), _chunk("c1", 500)]
    asyncio.run(fact_graph_service._extract_batch(batch))
    calls = [c for c in fake_llm.structured_calls if c["model_name"] == "FactGraph"]
    assert calls[-1]["model"] == settings.GROQ_REASONING_MODEL


def test_sensitivity_classification_uses_reasoning_model(fake_llm):
    from app.core.config import settings
    from app.services.sensitivity_firewall import firewall

    asyncio.run(firewall.classify_with_llm("Some source text to classify."))
    calls = [c for c in fake_llm.structured_calls if c["model_name"] == "SensitivityClassificationResult"]
    assert len(calls) == 1
    assert calls[-1]["model"] == settings.GROQ_REASONING_MODEL


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------

def test_clean_text_is_a_no_op_on_text_with_no_boilerplate():
    text = "Paragraph one about the incident.\n\nParagraph two with more detail."
    assert clean_text(text) == text


def test_clean_text_strips_page_number_lines():
    text = "\n\n".join(
        f"Page {i}\n\nReal content for page {i} goes here."
        for i in range(1, 6)
    )
    cleaned = clean_text(text)
    assert "Page 1" not in cleaned
    assert "Real content for page 1 goes here." in cleaned
    assert "Real content for page 5 goes here." in cleaned


def test_clean_text_never_drops_repeated_real_content():
    # A short line recurring across a document (e.g. "No casualties
    # reported." across several incident summaries) must never be treated
    # as boilerplate and dropped — SriGEN's whole premise is that no fact
    # is silently lost. Only unambiguous page-number lines are stripped.
    text = "\n\n".join(["No casualties reported."] * 5)
    cleaned = clean_text(text)
    assert cleaned.count("No casualties reported.") == 5


def test_clean_text_collapses_excess_blank_lines():
    text = "Line one.\n\n\n\n\nLine two."
    cleaned = clean_text(text)
    assert "\n\n\n" not in cleaned
    assert "Line one." in cleaned and "Line two." in cleaned


def test_clean_text_handles_empty_input():
    assert clean_text("") == ""
    assert clean_text("   \n\n  ") == ""


# ---------------------------------------------------------------------------
# compute_suggested_default — tier + deliverable-type gating
# (sensitivity_plan_clean.md §3-4: two honest fields, no confidence threshold)
# ---------------------------------------------------------------------------

def test_suggested_default_always_withholds_classified_asset_regardless_of_tier():
    """category alone forces withhold for restricted categories — tier is
    informational only and never overrides it (sensitivity_plan_clean.md §3)."""
    from app.services.orchestrator import compute_suggested_default
    from app.db.schemas import AudienceType, DeliverableType

    for tier in ("routine", "contextual", "sensitive"):
        default, _ = compute_suggested_default(
            category="CLASSIFIED_ASSET",
            sensitivity_tier=tier,
            audience=AudienceType.GENERAL_PUBLIC,
            deliverable_type=DeliverableType.BRIEFING_NOTE,
        )
        assert default == "withhold"


def test_suggested_default_always_withholds_ip_address_regardless_of_tier():
    from app.services.orchestrator import compute_suggested_default
    from app.db.schemas import AudienceType, DeliverableType

    for tier in ("routine", "contextual", "sensitive"):
        default, _ = compute_suggested_default(
            category="IP_ADDRESS",
            sensitivity_tier=tier,
            audience=AudienceType.GENERAL_PUBLIC,
            deliverable_type=DeliverableType.BRIEFING_NOTE,
        )
        assert default == "withhold"


def test_suggested_default_discloses_routine_tier_regardless_of_deliverable():
    """A 'routine' item (e.g. a name quoted in a public statement) carries no
    operational meaning by itself and should disclose everywhere."""
    from app.services.orchestrator import compute_suggested_default
    from app.db.schemas import AudienceType, DeliverableType

    for deliverable in (DeliverableType.PUBLIC_FAQ, DeliverableType.BRIEFING_NOTE):
        default, _ = compute_suggested_default(
            category="PERSON",
            sensitivity_tier="routine",
            audience=AudienceType.GENERAL_PUBLIC,
            deliverable_type=deliverable,
        )
        assert default == "disclose"


def test_suggested_default_contextual_tier_is_deliverable_dependent():
    """A 'contextual' item discloses for internal-facing deliverables
    (sitreps, briefings, advisories, executive summaries, incident reports)
    but withholds for external/public-facing ones (press releases, social
    posts, FAQs, etc.) — this is the deliverable_type gating that was
    previously a checked-but-unused parameter."""
    from app.services.orchestrator import compute_suggested_default
    from app.db.schemas import AudienceType, DeliverableType

    default, reason = compute_suggested_default(
        category="LOCATION",
        sensitivity_tier="contextual",
        audience=AudienceType.GENERAL_PUBLIC,
        deliverable_type=DeliverableType.SITREP,
    )
    assert default == "disclose"
    assert "sitrep" in reason.lower()

    default, _ = compute_suggested_default(
        category="LOCATION",
        sensitivity_tier="contextual",
        audience=AudienceType.GENERAL_PUBLIC,
        deliverable_type=DeliverableType.PRESS_RELEASE,
    )
    assert default == "withhold"


def test_suggested_default_always_withholds_sensitive_tier_outside_internal_audience():
    from app.services.orchestrator import compute_suggested_default
    from app.db.schemas import AudienceType, DeliverableType

    for deliverable in (DeliverableType.PUBLIC_FAQ, DeliverableType.BRIEFING_NOTE, DeliverableType.SITREP):
        default, _ = compute_suggested_default(
            category="PERSON",
            sensitivity_tier="sensitive",
            audience=AudienceType.GENERAL_PUBLIC,
            deliverable_type=deliverable,
        )
        assert default == "withhold"


def test_suggested_default_internal_audience_still_overrides_everything():
    """Audience-authorized disclosure must still win regardless of category
    or tier — publication_status and internal-audience are checked before
    the restricted-category / tier logic runs at all."""
    from app.services.orchestrator import compute_suggested_default
    from app.db.schemas import AudienceType, DeliverableType

    default, _ = compute_suggested_default(
        category="CLASSIFIED_ASSET",
        sensitivity_tier="sensitive",
        audience=AudienceType.SENIOR_LEADERSHIP,
        deliverable_type=DeliverableType.BRIEFING_NOTE,
    )
    assert default == "disclose"


def test_suggested_default_released_publication_status_overrides_everything():
    from app.services.orchestrator import compute_suggested_default
    from app.db.schemas import AudienceType, DeliverableType

    default, _ = compute_suggested_default(
        category="CLASSIFIED_ASSET",
        sensitivity_tier="sensitive",
        audience=AudienceType.GENERAL_PUBLIC,
        deliverable_type=DeliverableType.PRESS_RELEASE,
        publication_status="Released",
    )
    assert default == "disclose"


def test_no_confidence_threshold_or_generation_mode_remnants_in_orchestrator():
    """Regression guard: the old overloaded-confidence design and the old
    Direct/Protected mode toggle must never reappear in orchestrator.py."""
    import inspect
    from app.services import orchestrator as orchestrator_module

    source = inspect.getsource(orchestrator_module)
    assert "0.7" not in source
    assert "GenerationMode" not in source
    assert "generation_mode" not in source
    assert "_LOW_CONFIDENCE_DISCLOSE_THRESHOLD" not in source


# ---------------------------------------------------------------------------
# Claim entailment batching (grounding_guard.py::verify_content) — one LLM
# call per BATCH of claims instead of one call per claim/sentence. See
# GroundingGuard._batch_claim_items / _judge_entailment_batch /
# _verify_claims_batched.
# ---------------------------------------------------------------------------

def _make_multi_sentence_draft(n_sentences: int) -> str:
    return " ".join(f"This is factual sentence number {i} about the incident." for i in range(n_sentences))


def test_batch_claim_items_groups_by_count_cap():
    items = [(i, f"claim {i}", "short passage") for i in range(15)]
    batches = grounding_guard._batch_claim_items(items)
    assert len(batches) == 2  # ceil(15 / ENTAILMENT_BATCH_SIZE=12)
    assert [i for b in batches for i, _, _ in b] == list(range(15))  # order preserved, nothing dropped


def test_batch_claim_items_respects_char_cap_even_under_count_cap():
    # 10 items well under the count cap (12) but each ~4000 chars -> forced
    # into multiple batches by ENTAILMENT_BATCH_MAX_CHARS (18_000).
    items = [(i, "x" * 2000, "y" * 2000) for i in range(10)]
    batches = grounding_guard._batch_claim_items(items)
    assert len(batches) > 1
    for b in batches:
        total_chars = sum(len(c) + len(p) for _, c, p in b)
        assert total_chars <= grounding_guard.ENTAILMENT_BATCH_MAX_CHARS


def test_verify_content_uses_far_fewer_calls_than_one_per_claim(fake_llm):
    """The actual regression test for the fix: a draft with many sentences
    must NOT generate one entailment LLM call per sentence."""
    draft = _make_multi_sentence_draft(15)
    source = "The incident affected several systems and was fully contained by response teams."

    score, results = asyncio.run(grounding_guard.verify_content(content=draft, source_text=source))

    assert len(results) == 15  # every claim still gets its own judged result
    batch_calls = [c for c in fake_llm.structured_calls if c["model_name"] == "BatchClaimEntailmentJudgement"]
    single_calls = [c for c in fake_llm.structured_calls if c["model_name"] == "ClaimEntailmentJudgement"]
    assert single_calls == [], "multi-claim content must go through the batched path, not the per-claim one"
    assert len(batch_calls) == 2, f"expected ceil(15/12)=2 batch calls, got {len(batch_calls)}"


def test_verify_content_single_claim_still_works_via_one_batch_call(fake_llm):
    """Edge case: a one-sentence draft still goes through the batch path
    (a batch of size 1), not the standalone verify_claim path — keeping
    exactly one code path responsible for calling the entailment LLM from
    verify_content."""
    score, results = asyncio.run(grounding_guard.verify_content(
        content="A single factual sentence about the incident occurred.",
        source_text="A single factual sentence about the incident occurred.",
    ))
    assert len(results) == 1
    batch_calls = [c for c in fake_llm.structured_calls if c["model_name"] == "BatchClaimEntailmentJudgement"]
    assert len(batch_calls) == 1


def test_batched_entailment_still_enforces_number_mismatch_override(fake_llm):
    """Acceptance-level regression: the deterministic NUMBER-mismatch override
    (the thing that actually catches factual tampering) must still fire
    through the batched path exactly as it did through the old per-claim
    loop — even though the fake LLM's batch judgement says entailed=True for
    every claim, a tampered number must still force that one claim False."""
    source = (
        "An incident affected 24 systems at the facility. Response teams restored "
        "all systems by evening. No further disruption has been reported since containment."
    )
    tampered = (
        "The incident affected 42 systems at the facility. "
        "Response teams restored all systems by evening. "
        "No further disruption has been reported since containment."
    )
    score, results = asyncio.run(grounding_guard.verify_content(content=tampered, source_text=source))
    assert score < 70.0
    assert not results[0].entailed
    assert "42" in " ".join(m.description for m in results[0].entity_mismatches)
    # And this all still happened inside ONE batch call, not three.
    batch_calls = [c for c in fake_llm.structured_calls if c["model_name"] == "BatchClaimEntailmentJudgement"]
    assert len(batch_calls) == 1


def test_batch_entailment_failure_falls_back_per_claim_without_crashing(fake_llm):
    """If the batched entailment call fails outright, every claim in that
    batch must fall back to the deterministic-only judgement (same posture
    as the old per-claim except-branch) rather than raising or silently
    dropping claims."""
    fake_llm.should_fail = True
    score, results = asyncio.run(grounding_guard.verify_content(
        content=_make_multi_sentence_draft(3),
        source_text="Some source text with matching factual content.",
    ))
    assert len(results) == 3
    for r in results:
        assert r.reasoning == "Deterministic match check completed."
