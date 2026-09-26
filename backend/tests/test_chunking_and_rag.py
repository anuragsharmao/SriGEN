"""Tests for the Chunking + RAG-based Refinement build plan:
  - app/services/chunking.py (Part A2)
  - app/db/models.py::DocumentChunkModel persistence (Part A3)
  - app/services/fact_graph.py federated extraction (Part A4)
  - app/services/orchestrator.py wiring `passages` into Grounding Guard (Part A5)
  - app/api/routes_refine.py draft_id RAG path + ad-hoc chunking (Part B)
  - app/api/routes_verify.py ad-hoc chunking (Part B3)

Mirrors the "Test checklist before you trust it" section of the build plan.
"""

import asyncio

import pytest

from app.db.models import DocumentChunkModel, SourceDocumentModel
from app.services.chunking import chunk_document
from app.services.fact_graph import fact_graph_service

SMALL_SOURCE = "An incident affected 24 systems at the facility. Response teams restored all systems by evening."

# One paragraph per "page" of a synthetic large document, comfortably over
# chunk_document's default target_chars (3500) so it is guaranteed to split
# into multiple chunks. Kept modest in paragraph count (not just char count)
# so per-claim spaCy NER during Grounding Guard verification stays fast in
# tests — the plan's chunking behavior doesn't depend on document length in
# paragraphs, just characters.
LARGE_SOURCE = "\n\n".join(
    f"Paragraph {i}: Sector-{i} reported a status update at {i:02d}:00 hours involving unit {1000 + i}. "
    f"The situation remained stable with {i} personnel on site and no further incidents recorded."
    for i in range(1, 40)
)


# ---------------------------------------------------------------------------
# Part A2 — chunk_document itself
# ---------------------------------------------------------------------------

def test_small_document_returns_single_chunk_no_op():
    """Checklist item 1: a small document must produce exactly one chunk —
    the graceful-degradation, zero-behavior-change path."""
    chunks = chunk_document(SMALL_SOURCE)
    assert len(chunks) == 1
    assert chunks[0]["text"] == SMALL_SOURCE.strip()
    assert chunks[0]["chunk_index"] == 0


def test_empty_document_returns_no_chunks():
    assert chunk_document("") == []
    assert chunk_document("   \n\n  ") == []


def test_large_document_splits_into_multiple_chunks_covering_all_content():
    chunks = chunk_document(LARGE_SOURCE)
    assert len(chunks) > 1
    # Every chunk stays close to the target size (generous bound to allow
    # for the overlap and the oversized-unit fallback splitting).
    for c in chunks:
        assert c["char_count"] <= 3500 * 2 + 600
    # Content coverage: the first and last paragraphs must each appear in
    # at least one chunk — nothing is silently dropped.
    combined = "\n".join(c["text"] for c in chunks)
    assert "Paragraph 1:" in combined
    assert "Paragraph 39:" in combined


def test_oversized_single_paragraph_is_hard_split_never_unbounded():
    """A pathological single paragraph with no blank lines and no sentence
    punctuation must still be bounded, never shipped as one giant chunk."""
    giant_word_soup = "word " * 5000  # ~25000 chars, no sentence punctuation
    chunks = chunk_document(giant_word_soup, target_chars=1000)
    assert len(chunks) > 1
    for c in chunks:
        assert c["char_count"] <= 1000 * 2


# ---------------------------------------------------------------------------
# Part A3 — chunks persisted at ingestion (via orchestrator)
# ---------------------------------------------------------------------------

def test_generate_persists_document_chunks_for_source(client, db_session):
    res = client.post("/api/generate", json={
        "source_text": LARGE_SOURCE,
        "deliverable_types": ["advisory"],
    })
    assert res.status_code == 200
    source_id = res.json()["source_id"]

    chunks = (
        db_session.query(DocumentChunkModel)
        .filter_by(source_id=source_id)
        .order_by(DocumentChunkModel.chunk_index)
        .all()
    )
    assert len(chunks) > 1
    # Chunk indices are contiguous starting at 0.
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_generate_small_source_persists_exactly_one_chunk(client, db_session):
    res = client.post("/api/generate", json={
        "source_text": SMALL_SOURCE,
        "deliverable_types": ["advisory"],
    })
    assert res.status_code == 200
    source_id = res.json()["source_id"]
    chunks = db_session.query(DocumentChunkModel).filter_by(source_id=source_id).all()
    assert len(chunks) == 1


# ---------------------------------------------------------------------------
# Part A4 — federated Fact Graph extraction
# ---------------------------------------------------------------------------

def test_extract_fact_graph_accepts_plain_string_single_call_path(fake_llm):
    """Backward compatibility: calling with a raw string (as pre-existing
    tests/callers do) still works and issues exactly one LLM call."""
    fact_graph = asyncio.run(fact_graph_service.extract_fact_graph(SMALL_SOURCE))
    assert fact_graph.source_title
    calls = [c for c in fake_llm.structured_calls if c["model_name"] == "FactGraph"]
    assert len(calls) == 1


def test_extract_fact_graph_from_chunks_merges_partials(fake_llm):
    """Batching: LARGE_SOURCE's 3 chunks total well under BATCH_MAX_CHARS,
    so they ride in a single batched LLM call instead of 3 separate ones —
    the whole point of the token-optimization change. Merge behavior itself
    (entities/facts present) must be unaffected."""
    chunk_dicts = chunk_document(LARGE_SOURCE)
    assert len(chunk_dicts) > 1

    class _FakeChunk:
        def __init__(self, cd, idx):
            self.id = f"chunk-{idx}"
            self.text = cd["text"]
            self.page_start = cd["page_start"]
            self.page_end = cd["page_end"]

    fake_chunks = [_FakeChunk(cd, i) for i, cd in enumerate(chunk_dicts)]
    fact_graph = asyncio.run(fact_graph_service.extract_fact_graph(fake_chunks))

    calls = [c for c in fake_llm.structured_calls if c["model_name"] == "FactGraph"]
    assert len(calls) == 1
    assert len(calls) < len(chunk_dicts)
    # Merge must not have silently lost entities from the (identical, since
    # FakeLLMClient always returns the same canned FactGraph) per-batch results.
    assert len(fact_graph.entities) >= 1
    assert len(fact_graph.facts) > 0


def test_extract_fact_graph_batches_multiple_chunks_per_call_when_over_budget(fake_llm, monkeypatch):
    """With a small BATCH_MAX_CHARS forcing 3 separate batches (one per
    chunk, matching pre-batching granularity), call count should track
    batch count, not stay fixed at 1 — batching adapts to document size
    rather than always collapsing to a single call."""
    monkeypatch.setattr(fact_graph_service, "BATCH_MAX_CHARS", 100)
    chunk_dicts = chunk_document(LARGE_SOURCE)
    assert len(chunk_dicts) > 1

    class _FakeChunk:
        def __init__(self, cd, idx):
            self.id = f"chunk-{idx}"
            self.text = cd["text"]
            self.page_start = cd["page_start"]
            self.page_end = cd["page_end"]

    fake_chunks = [_FakeChunk(cd, i) for i, cd in enumerate(chunk_dicts)]
    fact_graph = asyncio.run(fact_graph_service.extract_fact_graph(fake_chunks))

    calls = [c for c in fake_llm.structured_calls if c["model_name"] == "FactGraph"]
    assert len(calls) == len(chunk_dicts)
    assert len(fact_graph.entities) >= 1


def test_extract_fact_graph_skips_failed_chunk_but_returns_partial_graph(fake_llm, monkeypatch):
    """Checklist item 5: a corrupted/failing chunk must not fail the whole
    extraction — Fact Graph extraction should skip it and still succeed.
    Forces one-chunk-per-batch (small BATCH_MAX_CHARS) so a single failure
    only costs one chunk's worth of coverage, same as pre-batching."""
    monkeypatch.setattr(fact_graph_service, "BATCH_MAX_CHARS", 100)
    chunk_dicts = chunk_document(LARGE_SOURCE)
    assert len(chunk_dicts) > 1

    class _FakeChunk:
        def __init__(self, cd, idx):
            self.id = f"chunk-{idx}"
            self.text = cd["text"]
            self.page_start = None
            self.page_end = None

    fake_chunks = [_FakeChunk(cd, i) for i, cd in enumerate(chunk_dicts)]

    real_structured_completion = fake_llm.structured_completion
    call_count = {"n": 0}

    async def flaky_structured_completion(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            from app.core.llm_client import LLMUnavailableError
            raise LLMUnavailableError("simulated single-chunk failure", stage="fact_graph")
        return await real_structured_completion(*args, **kwargs)

    monkeypatch.setattr(fake_llm, "structured_completion", flaky_structured_completion)

    fact_graph = asyncio.run(fact_graph_service.extract_fact_graph(fake_chunks))
    assert fact_graph is not None
    assert len(fact_graph.entities) >= 1


def test_extract_fact_graph_raises_when_every_chunk_fails(fake_llm):
    chunk_dicts = chunk_document(LARGE_SOURCE)

    class _FakeChunk:
        def __init__(self, cd, idx):
            self.id = f"chunk-{idx}"
            self.text = cd["text"]
            self.page_start = None
            self.page_end = None

    fake_chunks = [_FakeChunk(cd, i) for i, cd in enumerate(chunk_dicts)]
    fake_llm.should_fail = True

    from app.core.llm_client import LLMUnavailableError
    with pytest.raises(LLMUnavailableError):
        asyncio.run(fact_graph_service.extract_fact_graph(fake_chunks))


# ---------------------------------------------------------------------------
# Part A5 — real passages wired into Grounding Guard for large documents
# ---------------------------------------------------------------------------

def test_generate_on_large_document_completes_and_uses_real_passages(client, fake_llm):
    """Checklist item 2: a large document must complete generation without
    ever sending the whole document as a single verification passage."""
    res = client.post("/api/generate", json={
        "source_text": LARGE_SOURCE,
        "deliverable_types": ["advisory"],
    })
    assert res.status_code == 200
    body = res.json()
    draft = body["drafts"][0]
    assert draft["claims"], "expected at least one claim to have been verified"

    matched = [c["matched_source_passage"] for c in draft["claims"] if c["matched_source_passage"]]
    assert matched
    # No verification passage should be the entire (multi-KB) document —
    # each one should be roughly chunk-sized, not the whole thing.
    for m in matched:
        assert len(m) < len(LARGE_SOURCE)


# ---------------------------------------------------------------------------
# Part B — Refine Mode RAG
# ---------------------------------------------------------------------------

def test_refine_requires_draft_id_or_claimed_source(client):
    res = client.post("/api/refine", json={
        "content_to_verify": "Some content to verify.",
    })
    assert res.status_code == 422


def test_refine_with_draft_id_retrieves_server_side_without_claimed_source(client, fake_llm):
    """Checklist item 3: /api/refine with draft_id set and no claimed_source
    must work and return a sensible result."""
    gen = client.post("/api/generate", json={
        "source_text": LARGE_SOURCE,
        "deliverable_types": ["advisory"],
    })
    assert gen.status_code == 200
    draft = gen.json()["drafts"][0]
    draft_id = draft["id"]
    draft_content = draft["draft_content"]

    res = client.post("/api/refine", json={
        "content_to_verify": draft_content,
        "draft_id": draft_id,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["original"] is not None
    assert body["final_content"] == draft_content


def test_refine_with_unknown_draft_id_returns_404(client):
    res = client.post("/api/refine", json={
        "content_to_verify": "Some content.",
        "draft_id": "does-not-exist",
    })
    assert res.status_code == 404


def test_refine_ad_hoc_large_claimed_source_does_not_error(client):
    """Checklist item 4: /api/verify (and /api/refine's ad-hoc path) with a
    large pasted claimed_source and no draft_id must not blow up."""
    res = client.post("/api/refine", json={
        "content_to_verify": "Sector-3 reported a status update involving unit 1003.",
        "claimed_source": LARGE_SOURCE,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["original"]["content"]


def test_verify_ad_hoc_large_claimed_source_does_not_error(client):
    res = client.post("/api/verify", json={
        "content_to_verify": "Sector-3 reported a status update involving unit 1003.",
        "claimed_source": LARGE_SOURCE,
    })
    assert res.status_code == 200
