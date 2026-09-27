"""Fact Graph extraction service: builds canonical, structured single-source-of-truth.

Previously sent the ENTIRE raw source text in one LLM call, which breaks on
large documents. Extraction is chunked, but chunks are BATCHED into as few
LLM calls as fit under BATCH_MAX_CHARS rather than one call per chunk — a
500-page source used to mean 300+ chunk-level calls, each repeating the full
system prompt; batching cuts both the call count and that repeated overhead
by roughly the average batch size. Documents that fit in a single chunk (the
common case — almost every document seen in testing) still take the exact
same single-call path as before. See SriGEN Build Plan, Part A4, and
docs/token_optimization_plan.md.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Union

from app.core.config import settings
from app.core.llm_client import llm_client, LLMUnavailableError
from app.db.schemas import FactEntity, FactGraph, FactStatement

logger = logging.getLogger("srigen.fact_graph")

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "fact_graph_prompt.txt"


class _ChunkLike:
    """Minimal duck-typed shape this module needs from a chunk, so it accepts
    either real DocumentChunkModel rows or the ephemeral dicts produced by
    app/services/chunking.py::chunk_document without importing the ORM model
    here (avoids a service -> db.models dependency in this file)."""

    __slots__ = ("id", "text", "page_start", "page_end")

    def __init__(self, id: Optional[str], text: str, page_start: Optional[int], page_end: Optional[int]):
        self.id = id
        self.text = text
        self.page_start = page_start
        self.page_end = page_end


def _normalize_chunks(source) -> List[_ChunkLike]:
    """Accepts a raw string (backward-compatible single-call path, still used
    directly by tests and any other caller that hasn't been updated to pass
    chunks), a list of DocumentChunkModel ORM rows, or a list of chunk dicts
    from chunking.chunk_document — normalizes all of them to _ChunkLike."""
    if isinstance(source, str):
        return [_ChunkLike(id=None, text=source, page_start=None, page_end=None)]

    normalized: List[_ChunkLike] = []
    for c in source:
        if isinstance(c, dict):
            normalized.append(_ChunkLike(
                id=c.get("id"),
                text=c["text"],
                page_start=c.get("page_start"),
                page_end=c.get("page_end"),
            ))
        else:
            # ORM DocumentChunkModel (or any object exposing these attrs)
            normalized.append(_ChunkLike(
                id=getattr(c, "id", None),
                text=getattr(c, "text"),
                page_start=getattr(c, "page_start", None),
                page_end=getattr(c, "page_end", None),
            ))
    return normalized


def _batch_chunks(chunks: List[_ChunkLike], max_chars: int) -> List[List[_ChunkLike]]:
    """Group consecutive chunks into batches whose combined text stays under
    max_chars, so one LLM call can cover several chunks instead of one call
    per chunk. Order-preserving and never splits a single chunk. A chunk
    larger than max_chars on its own still gets its own one-chunk batch
    (falls back to the single-chunk call path) rather than being cut."""
    batches: List[List[_ChunkLike]] = []
    current: List[_ChunkLike] = []
    current_len = 0
    for c in chunks:
        if current and current_len + len(c.text) > max_chars:
            batches.append(current)
            current, current_len = [], 0
        current.append(c)
        current_len += len(c.text)
    if current:
        batches.append(current)
    return batches


class FactGraphService:
    """Service to extract canonical Fact Graphs using Groq structured output."""

    # Char budget per batched LLM call. Kept comfortably under
    # llm_client's _enforce_prompt_budget ceiling (40k chars) to leave
    # headroom for the system prompt, the chunk-boundary markers, and the
    # model's own output tokens. A class attribute (not a hardcoded
    # literal) so tests can tune it to force multi-batch scenarios without
    # needing genuinely huge fixtures.
    BATCH_MAX_CHARS = 28_000

    def __init__(self):
        if PROMPT_FILE.exists():
            self.system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
        else:
            self.system_prompt = "You are SriGEN's Canonical Fact Graph Extractor."

    async def _extract_single(
        self,
        text: str,
        chunk_id: Optional[str] = None,
        page: Optional[tuple] = None,
    ) -> FactGraph:
        """Extract canonical structured facts, entities, numbers, and dates
        from a single block of text (one chunk, or the whole document when
        it fits in one chunk). This is the exact call every non-chunked
        caller used before federated extraction existed — unchanged."""
        user_prompt = (
            f"Please extract the canonical Fact Graph from the following source text.\n\n"
            f"--- SOURCE TEXT ---\n{text}\n--- END SOURCE TEXT ---"
        )

        try:
            fact_graph = await llm_client.structured_completion(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                response_model=FactGraph,
                model=settings.REASONING_MODEL,
                stage="fact_graph",
            )
        except LLMUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error extracting Fact Graph: {e}.")
            raise LLMUnavailableError(f"Fact graph extraction failed: {e}", stage="fact_graph") from e

        if chunk_id is not None:
            page_start, page_end = page or (None, None)
            for ent in fact_graph.entities:
                ent.source_chunk_ids = [chunk_id]
            for fact in fact_graph.facts:
                fact.source_chunk_id = chunk_id
                fact.page_start = page_start
                fact.page_end = page_end
        return fact_graph

    async def _extract_batch(self, batch: List[_ChunkLike]) -> FactGraph:
        """Extract one Fact Graph from a BATCH of chunks in a single LLM
        call. A one-chunk batch is just delegated to _extract_single (same
        call shape as before, zero behavior change). A multi-chunk batch
        gets a prompt with explicit CHUNK ... END CHUNK labels per piece,
        and the model is asked to tag each fact/entity with the chunk label
        it came from.

        That per-fact tag is the model's claim, not a fact — same posture
        as the Sensitivity Firewall's span validation. Anything that isn't
        a real chunk id from this batch is not trusted silently: it falls
        back to attributing the fact/entity to the whole batch (all chunk
        ids, and the batch's overall page range) rather than shipping a
        wrong or empty source.
        """
        if len(batch) == 1:
            c = batch[0]
            return await self._extract_single(c.text, chunk_id=c.id, page=(c.page_start, c.page_end))

        labeled_parts = []
        for c in batch:
            label = c.id or "UNLABELED"
            page_note = f" (pages {c.page_start}-{c.page_end})" if c.page_start is not None else ""
            labeled_parts.append(f"--- CHUNK {label}{page_note} ---\n{c.text}\n--- END CHUNK {label} ---")
        combined_text = "\n\n".join(labeled_parts)

        user_prompt = (
            "Please extract the canonical Fact Graph from the following source text. "
            "The source is split into labeled chunks. For every fact and entity, set "
            "its source chunk id (source_chunk_id for facts, source_chunk_ids for "
            "entities) to the exact CHUNK label(s) it came from.\n\n"
            f"--- SOURCE TEXT ---\n{combined_text}\n--- END SOURCE TEXT ---"
        )

        try:
            fact_graph = await llm_client.structured_completion(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                response_model=FactGraph,
                model=settings.REASONING_MODEL,
                stage="fact_graph",
            )
        except LLMUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error extracting Fact Graph (batch of {len(batch)} chunks): {e}.")
            raise LLMUnavailableError(f"Fact graph extraction failed: {e}", stage="fact_graph") from e

        valid_ids = {c.id for c in batch if c.id is not None}
        page_by_id = {c.id: (c.page_start, c.page_end) for c in batch}
        all_ids_in_batch = list(page_by_id.keys())
        batch_page_start = min((p[0] for p in page_by_id.values() if p[0] is not None), default=None)
        batch_page_end = max((p[1] for p in page_by_id.values() if p[1] is not None), default=None)

        for ent in fact_graph.entities:
            valid = [i for i in ent.source_chunk_ids if i in valid_ids]
            ent.source_chunk_ids = valid or all_ids_in_batch

        for fact in fact_graph.facts:
            if fact.source_chunk_id in valid_ids:
                fact.page_start, fact.page_end = page_by_id[fact.source_chunk_id]
            else:
                fact.source_chunk_id = None
                fact.page_start = batch_page_start
                fact.page_end = batch_page_end

        return fact_graph

    def _merge_partials(self, partials: List[FactGraph]) -> FactGraph:
        """Merge per-chunk partial Fact Graphs into one canonical graph.

        Deliberate scoping decision (see Build Plan Part A4): entities are
        deduplicated on (name.lower(), category) — their contributing chunk
        ids are unioned. Facts are NOT deduplicated; near-duplicate facts
        from overlapping/adjacent chunks are harmless noise for Grounding
        Guard (a claim just ends up with two citable sources instead of
        one), and real cross-chunk fact dedup is a genuine research problem,
        not something this pipeline attempts. numbers_and_dates and
        policy_constraints are likewise concatenated with light literal
        dedup only.
        """
        if len(partials) == 1:
            return partials[0]

        merged_entities: dict = {}
        entity_order: List[str] = []
        for p in partials:
            for ent in p.entities:
                key = (ent.name.strip().lower(), ent.category.strip().lower())
                if key not in merged_entities:
                    merged_entities[key] = ent
                    entity_order.append(key)
                else:
                    existing = merged_entities[key]
                    existing.source_chunk_ids = list(dict.fromkeys(
                        existing.source_chunk_ids + ent.source_chunk_ids
                    ))
                    if not existing.description and ent.description:
                        existing.description = ent.description
                    for lang, val in ent.native_forms.items():
                        existing.native_forms.setdefault(lang, val)

        all_facts: List[FactStatement] = []
        for p in partials:
            all_facts.extend(p.facts)

        all_numbers = []
        seen_numbers = set()
        for p in partials:
            for nd in p.numbers_and_dates:
                key = (nd.value.strip().lower(), (nd.context or "").strip().lower())
                if key not in seen_numbers:
                    seen_numbers.add(key)
                    all_numbers.append(nd)

        all_constraints: List[str] = []
        seen_constraints = set()
        for p in partials:
            for c in p.policy_constraints:
                c_key = c.strip().lower()
                if c_key not in seen_constraints:
                    seen_constraints.add(c_key)
                    all_constraints.append(c)

        # Title/summary: take the first non-empty ones (typically the first
        # chunk, which usually carries the document's opening/lede).
        source_title = next((p.source_title for p in partials if p.source_title), partials[0].source_title)
        summary = next((p.summary for p in partials if p.summary), partials[0].summary)

        return FactGraph(
            source_title=source_title,
            summary=summary,
            entities=[merged_entities[k] for k in entity_order],
            facts=all_facts,
            numbers_and_dates=all_numbers,
            policy_constraints=all_constraints,
        )

    async def extract_fact_graph(self, source: Union[str, list]) -> FactGraph:
        """Extract a canonical Fact Graph from `source`, which may be:
          - a raw string (single-call path, unchanged from before — still
            used directly by any caller/test that passes text straight in), or
          - a list of DocumentChunkModel rows / chunk dicts (federated
            per-chunk extraction + merge).

        A single-chunk input (including the plain-string case) takes the
        exact original code path with zero behavior change. Multi-chunk
        input is first grouped into batches (see BATCH_MAX_CHARS/_batch_chunks)
        so several chunks can ride in one LLM call instead of one call each,
        then extraction runs in parallel across batches via asyncio.gather.
        A batch whose extraction fails (LLM error, timeout) is logged and
        skipped rather than failing the whole document — partial coverage
        beats total failure. Note the blast radius of one failure is now a
        batch's worth of chunks rather than a single chunk; that's the
        accepted trade-off for fewer/cheaper calls, not something this
        method tries to paper over with retries. If every batch fails, or
        this is ever called with zero chunks, it raises/falls back rather
        than silently returning nothing.
        """
        chunks = _normalize_chunks(source)

        if not chunks:
            # Defensive fallback: should not happen (ingestion never persists
            # zero chunks for non-empty text), but never let an empty chunk
            # list produce a confusing downstream error.
            if isinstance(source, str):
                return await self._extract_single(source)
            raise LLMUnavailableError("Fact graph extraction called with zero chunks and no fallback text", stage="fact_graph")

        if len(chunks) == 1:
            c = chunks[0]
            return await self._extract_single(c.text)

        batches = _batch_chunks(chunks, self.BATCH_MAX_CHARS)

        partials = await asyncio.gather(
            *[self._extract_batch(b) for b in batches],
            return_exceptions=True,
        )

        ok_partials: List[FactGraph] = []
        for i, p in enumerate(partials):
            if isinstance(p, Exception):
                logger.warning(
                    f"Fact graph extraction failed on batch {i + 1} of {len(batches)} "
                    f"({len(batches[i])} chunks): {p}. Skipping batch."
                )
            else:
                ok_partials.append(p)

        if not ok_partials:
            raise LLMUnavailableError("Fact graph extraction failed on every batch", stage="fact_graph")

        return self._merge_partials(ok_partials)


fact_graph_service = FactGraphService()
