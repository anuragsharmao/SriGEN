"""Tests for the LLM token-optimization changes to Fact Graph extraction:
  - app/services/fact_graph.py::_batch_chunks (chunk batching)
  - app/services/fact_graph.py::FactGraphService._extract_batch (labeled
    multi-chunk calls + chunk-id attribution fallback)
  - app/services/text_cleaning.py::clean_text (pre-chunking boilerplate strip)

See docs/token_optimization_plan.md for the design rationale.
"""

import asyncio

from app.services.fact_graph import _batch_chunks, _ChunkLike, fact_graph_service
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
