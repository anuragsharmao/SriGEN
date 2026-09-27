"""Source Understanding: merges Fact Graph extraction and Sensitivity
Classification into ONE chunked/batched LLM pass instead of two.

BEFORE this module existed:
  - fact_graph.py chunked+batched the source at ~28k chars/call, in parallel.
  - sensitivity_firewall.py independently re-chunked the SAME raw text at
    3.5k chars/call, calling the LLM once per chunk SEQUENTIALLY.
Same source text, two separate chunking schemes, two separate call sets —
one of them not even parallelized. Both were asking an LLM to read a piece
of text and report structured findings; they just asked two different
questions ("what are the facts" vs "what's sensitive").

AFTER: one prompt, one schema (`SourceUnderstanding`), one chunk/batch
boundary, one call per batch — answering both questions from the same read.
Batching/merge mechanics are intentionally identical in shape to
fact_graph.py's original federated-extraction design (see that file's
docstring for the full rationale); this module reuses its chunk-normalizing
and batching helpers directly rather than re-implementing them.

Chunk/batch sizing (`settings.SOURCE_CHUNK_TARGET_CHARS` /
`settings.SOURCE_UNDERSTANDING_BATCH_MAX_CHARS`) is currently small and equal
to each other — effectively one chunk per call, no re-batching — because
this is running against Groq's FREE tier, where smaller requests are safer
against a free-tier reasoning model's per-request token limits. That trades
away some of fact_graph.py's original "batch many chunks into one call"
savings, but every call here still does BOTH jobs at once, and every batch
still runs fully in parallel via asyncio.gather, so the merge's core saving
(no more separate, sequential sensitivity pass) holds regardless of tier.
Raise SOURCE_UNDERSTANDING_BATCH_MAX_CHARS once off the free tier to fold
several chunks into fewer calls again.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union

from app.core.config import settings
from app.core.llm_client import llm_client, LLMUnavailableError
from app.db.schemas import SensitiveSpanCandidate, SourceUnderstanding
from app.services.fact_graph import _ChunkLike, _batch_chunks, _normalize_chunks, fact_graph_service

logger = logging.getLogger("srigen.source_understanding")

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "source_understanding_prompt.txt"


class SourceUnderstandingService:
    """Single-pass Fact Graph + Sensitivity Classification extraction."""

    # See module docstring re: free-tier sizing. Read from settings (not a
    # hardcoded literal) so it can be raised later without a code change.
    BATCH_MAX_CHARS = settings.SOURCE_UNDERSTANDING_BATCH_MAX_CHARS

    def __init__(self):
        if PROMPT_FILE.exists():
            self.system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
        else:
            self.system_prompt = (
                "You are SriGEN's combined Fact Graph Extractor and "
                "Sensitivity Classification layer."
            )

    async def _extract_single(
        self,
        text: str,
        chunk_id: Optional[str] = None,
        page: Optional[tuple] = None,
    ) -> SourceUnderstanding:
        """Extract both the Fact Graph and the sensitive spans from a single
        block of text (one chunk, or the whole document when it fits in
        one chunk) in one LLM call."""
        user_prompt = (
            "Please extract the canonical Fact Graph AND identify every "
            "sensitive span from the following source text, in one pass.\n\n"
            f"--- SOURCE TEXT ---\n{text}\n--- END SOURCE TEXT ---"
        )

        try:
            result: SourceUnderstanding = await llm_client.structured_completion(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                response_model=SourceUnderstanding,
                model=settings.REASONING_MODEL,
                stage="source_understanding",
            )
        except LLMUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error extracting Source Understanding: {e}.")
            raise LLMUnavailableError(
                f"Source understanding extraction failed: {e}", stage="source_understanding"
            ) from e

        # Exact-text validation for sensitive spans, same posture as
        # sensitivity_firewall's original classify_with_llm: a span the
        # model claims but that isn't a verbatim substring of this chunk is
        # dropped and logged rather than trusted or silently redacted.
        validated_spans = []
        for span in result.sensitive_spans:
            if span.exact_text and span.exact_text in text:
                validated_spans.append(span)
            else:
                logger.warning(f"Dropped non-verbatim LLM span candidate: {span.exact_text!r}")
        result.sensitive_spans = validated_spans

        if chunk_id is not None:
            page_start, page_end = page or (None, None)
            for ent in result.fact_graph.entities:
                ent.source_chunk_ids = [chunk_id]
            for fact in result.fact_graph.facts:
                fact.source_chunk_id = chunk_id
                fact.page_start = page_start
                fact.page_end = page_end
        return result

    async def _extract_batch(self, batch: List[_ChunkLike]) -> SourceUnderstanding:
        """Extract one combined result from a BATCH of chunks in a single
        LLM call. A one-chunk batch delegates to _extract_single (identical
        call shape). A multi-chunk batch labels each chunk so facts/entities
        can be tagged with their source chunk id, exactly as fact_graph.py
        does — sensitive_spans don't need chunk labels since their offsets
        are resolved against the full original text downstream, in
        sensitivity_firewall._collect_candidate_spans."""
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
            "Please extract the canonical Fact Graph AND identify every sensitive "
            "span from the following source text, in one pass. The source is split "
            "into labeled chunks. For every fact and entity, set its source chunk id "
            "(source_chunk_id for facts, source_chunk_ids for entities) to the exact "
            "CHUNK label(s) it came from. sensitive_spans do not need chunk labels.\n\n"
            f"--- SOURCE TEXT ---\n{combined_text}\n--- END SOURCE TEXT ---"
        )

        try:
            result: SourceUnderstanding = await llm_client.structured_completion(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                response_model=SourceUnderstanding,
                model=settings.REASONING_MODEL,
                stage="source_understanding",
            )
        except LLMUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error extracting Source Understanding (batch of {len(batch)} chunks): {e}.")
            raise LLMUnavailableError(
                f"Source understanding extraction failed: {e}", stage="source_understanding"
            ) from e

        full_batch_text = "\n\n".join(c.text for c in batch)
        result.sensitive_spans = [
            span for span in result.sensitive_spans
            if span.exact_text and span.exact_text in full_batch_text
        ]

        valid_ids = {c.id for c in batch if c.id is not None}
        page_by_id = {c.id: (c.page_start, c.page_end) for c in batch}
        all_ids_in_batch = list(page_by_id.keys())
        batch_page_start = min((p[0] for p in page_by_id.values() if p[0] is not None), default=None)
        batch_page_end = max((p[1] for p in page_by_id.values() if p[1] is not None), default=None)

        for ent in result.fact_graph.entities:
            valid = [i for i in ent.source_chunk_ids if i in valid_ids]
            ent.source_chunk_ids = valid or all_ids_in_batch

        for fact in result.fact_graph.facts:
            if fact.source_chunk_id in valid_ids:
                fact.page_start, fact.page_end = page_by_id[fact.source_chunk_id]
            else:
                fact.source_chunk_id = None
                fact.page_start = batch_page_start
                fact.page_end = batch_page_end

        return result

    def _merge_partials(self, partials: List[SourceUnderstanding]) -> SourceUnderstanding:
        """Merge per-batch partial results into one canonical result.
        Fact-graph merging is delegated to fact_graph_service's own
        (unchanged) merge logic — entity dedup, fact concatenation, etc.
        sensitive_spans are concatenated and de-duplicated by
        (category, exact_text.lower()), same key sensitivity_firewall
        already uses downstream for its own overlap de-dup."""
        if len(partials) == 1:
            return partials[0]

        merged_fact_graph = fact_graph_service._merge_partials([p.fact_graph for p in partials])

        merged_spans: List[SensitiveSpanCandidate] = []
        seen_spans = set()
        for p in partials:
            for span in p.sensitive_spans:
                key = (span.category, span.exact_text.strip().lower())
                if key in seen_spans:
                    continue
                seen_spans.add(key)
                merged_spans.append(span)

        return SourceUnderstanding(fact_graph=merged_fact_graph, sensitive_spans=merged_spans)

    async def extract(self, source: Union[str, list]) -> Tuple[SourceUnderstanding, bool]:
        """Extract a combined Source Understanding result from `source`
        (raw string, or a list of DocumentChunkModel rows / chunk dicts).
        Mirrors fact_graph_service.extract_fact_graph's call shape for the
        happy path (single-chunk input takes the single-call path with zero
        behavior change; multi-chunk input batches, runs batches in
        parallel, and merges), but ALSO returns a `degraded` flag — the
        merged sensitivity half of this pass carries the same "the caller
        MUST surface this" contract classify_with_llm always had. A batch
        that fails is logged and skipped rather than failing the whole
        document (both its facts AND its sensitive-span coverage are lost
        for that batch — regex detection still covers that text
        independently downstream); `degraded=True` whenever any batch was
        skipped this way. If every batch fails, this raises."""
        chunks = _normalize_chunks(source)

        if not chunks:
            if isinstance(source, str):
                return await self._extract_single(source), False
            raise LLMUnavailableError(
                "Source understanding extraction called with zero chunks and no fallback text",
                stage="source_understanding",
            )

        if len(chunks) == 1:
            c = chunks[0]
            return await self._extract_single(c.text), False

        batches = _batch_chunks(chunks, self.BATCH_MAX_CHARS)

        partials = await asyncio.gather(
            *[self._extract_batch(b) for b in batches],
            return_exceptions=True,
        )

        ok_partials: List[SourceUnderstanding] = []
        for i, p in enumerate(partials):
            if isinstance(p, Exception):
                logger.warning(
                    f"Source understanding extraction failed on batch {i + 1} of {len(batches)} "
                    f"({len(batches[i])} chunks): {p}. Skipping batch."
                )
            else:
                ok_partials.append(p)

        if not ok_partials:
            raise LLMUnavailableError(
                "Source understanding extraction failed on every batch", stage="source_understanding"
            )

        degraded = len(ok_partials) < len(batches)
        return self._merge_partials(ok_partials), degraded


source_understanding_service = SourceUnderstandingService()
