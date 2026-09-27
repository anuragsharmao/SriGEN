"""Sensitivity Firewall: two-layer hybrid (regex + LLM classification) detection,
typed placeholder redaction for source-document transparency logging, and
deterministic (no second LLM pass) disclosure-decision resolution.
"""

import asyncio
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.db.schemas import (
    AudienceType,
    SecurityActionItem,
    SensitiveSpanCandidate,
    SensitivityClassificationResult,
)
from app.services.chunking import chunk_document

logger = logging.getLogger("srigen.sensitivity_firewall")
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "sensitivity_classification_prompt.txt"


class SensitivityFirewall:
    """Two-layer hybrid sensitivity firewall (deterministic regex + semantic LLM classification).

    Detection runs at TWO points in the pipeline (Phase 2 dual-scan):
    1. Source-side: once per ingested source document, over the raw source text
       (`apply_redaction`, used for the transparency log / Security Actions Log).
    2. Output-side: once per generated deliverable draft, over the generated
       text (`scan_for_disclosure_items`), since generation can introduce,
       rephrase, or recombine sensitive information the source-side scan alone
       cannot anticipate.

    Both share the same underlying `_collect_candidate_spans` detection logic.
    """

    def __init__(self):
        self.patterns = settings.SENSITIVE_PATTERNS

    async def classify_with_llm(self, text: str) -> Tuple[List[SensitiveSpanCandidate], bool]:
        """LLM semantic pass: catches sensitive spans regex can't anticipate.
        Returns (spans, degraded) — degraded=True means this call fell back to
        regex-only detection because the LLM call itself failed, which the
        caller MUST surface to the operator rather than swallow silently."""
        from app.core.llm_client import llm_client

        system_prompt = (
            PROMPT_FILE.read_text(encoding="utf-8")
            if PROMPT_FILE.exists()
            else (
                "You are SriGEN's Sensitivity Classification layer. "
                "Identify operationally or personally sensitive spans."
            )
        )

        # Classify bounded chunks so a large document cannot exceed the model's
        # per-request token limit. Exact-text validation below still checks
        # every returned span against the complete original document.
        # Chunks are classified IN PARALLEL (asyncio.gather) rather than one
        # at a time — this path is still used standalone (e.g. the
        # output-side disclosure scan on generated draft text, and any
        # caller of apply_redaction/classify_with_llm that doesn't pass
        # precomputed spans from the merged Source Understanding pass — see
        # app/services/source_understanding.py for the source-side merge).
        chunks = chunk_document(
            text,
            target_chars=settings.SOURCE_CHUNK_TARGET_CHARS,
            overlap_chars=settings.SOURCE_CHUNK_OVERLAP_CHARS,
        )

        async def _classify_chunk(chunk: Dict) -> Tuple[List[SensitiveSpanCandidate], bool]:
            user_prompt = f"--- DOCUMENT CHUNK ---\n{chunk['text']}\n--- END DOCUMENT CHUNK ---"
            try:
                result: SensitivityClassificationResult = await llm_client.structured_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=SensitivityClassificationResult,
                    model=settings.REASONING_MODEL,
                )
                return result.sensitive_spans, False
            except Exception as e:
                logger.error(
                    f"LLM sensitivity classification failed for chunk {chunk['chunk_index']}: {e}. "
                    "Proceeding with regex-only results for that chunk — DEGRADED."
                )
                return [], True

        chunk_results = await asyncio.gather(*[_classify_chunk(c) for c in chunks])
        candidates: List[SensitiveSpanCandidate] = []
        degraded = False
        for spans, chunk_degraded in chunk_results:
            candidates.extend(spans)
            degraded = degraded or chunk_degraded

        # Validate: exact_text must actually appear verbatim in the source.
        # Drop (and log) any hallucinated span rather than crashing or silently
        # trying to redact text that doesn't exist.
        validated: List[SensitiveSpanCandidate] = []
        for span in candidates:
            if span.exact_text and span.exact_text in text:
                validated.append(span)
            else:
                logger.warning(f"Dropped non-verbatim LLM span candidate: {span.exact_text!r}")
        return validated, degraded

    async def _collect_candidate_spans(
        self,
        text: str,
        precomputed_llm_spans: Optional[Tuple[List[SensitiveSpanCandidate], bool]] = None,
    ) -> Tuple[List[Dict], bool]:
        """Regex + LLM span collection, de-duplicated by overlap. Shared by both
        the source-side redaction pass and the output-side disclosure scan.

        `precomputed_llm_spans`, when given, is an (llm_spans, degraded) pair
        already produced elsewhere for this exact text — e.g. the merged
        Source Understanding pass (app/services/source_understanding.py),
        which extracts sensitivity spans in the SAME call as the Fact Graph
        instead of this method calling `classify_with_llm` a second time
        over the same source text. When omitted (the output-side disclosure
        scan on generated draft text always omits it, since that text was
        never part of the source-side pass), this method falls back to
        calling `classify_with_llm` itself, unchanged from before.

        Returns (accepted_spans, degraded)."""
        candidate_spans: List[Dict] = []

        # --- Layer 1: regex ---
        for category, regex_list in self.patterns.items():
            for pattern_str in regex_list:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                for match in pattern.finditer(text):
                    matched_value = match.group(0)
                    if matched_value.startswith("[") and matched_value.endswith("]"):
                        continue
                    candidate_spans.append({
                        "start": match.start(),
                        "end": match.end(),
                        "text": matched_value,
                        "category": category,
                        "confidence": 1.0,
                        # Regex patterns only match precise, structured
                        # identifiers (named ops, grid refs, IPs, ranks+names)
                        # with no surrounding context to judge "routine" vs
                        # "contextual" — default to the conservative tier.
                        # A human still reviews every item; this only sets
                        # the pre-filled suggestion.
                        "sensitivity_tier": "sensitive",
                        "source": "regex",
                        "reasoning": "Matched known pattern",
                    })

        # --- Layer 2: LLM semantic pass ---
        if precomputed_llm_spans is not None:
            llm_spans, degraded = precomputed_llm_spans
        else:
            llm_spans, degraded = await self.classify_with_llm(text)
        for span in llm_spans:
            start_search = 0
            while True:
                idx = text.find(span.exact_text, start_search)
                if idx == -1:
                    break
                candidate_spans.append({
                    "start": idx,
                    "end": idx + len(span.exact_text),
                    "text": span.exact_text,
                    "category": span.category,
                    "confidence": span.detection_confidence,
                    "sensitivity_tier": span.sensitivity_tier,
                    "source": "llm",
                    "reasoning": span.reasoning,
                })
                start_search = idx + len(span.exact_text)

        # --- De-duplicate overlaps: prefer the earliest/highest-confidence span. ---
        candidate_spans.sort(key=lambda s: (s["start"], -s["confidence"]))
        accepted_spans: List[Dict] = []
        last_end = -1
        for span in candidate_spans:
            if span["start"] >= last_end:
                accepted_spans.append(span)
                last_end = span["end"]

        return accepted_spans, degraded

    async def scan_for_disclosure_items(self, text: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Output-side (or standalone) scan: detect sensitive spans in `text` and
        return one entry per UNIQUE (category, normalized value), in reading
        order, with a synthetic display placeholder assigned for grouping/UI
        purposes only (it is never inserted into any content). No text
        substitution happens here — this is detection only. Returns
        (items, degraded)."""
        accepted_spans, degraded = await self._collect_candidate_spans(text)

        seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
        category_counters: Dict[str, int] = {}
        ordered: List[Dict[str, Any]] = []

        for span in accepted_spans:
            cat = span["category"]
            norm_key = (cat, span["text"].strip().lower())
            if norm_key in seen:
                continue
            counter = category_counters.get(cat, 0) + 1
            category_counters[cat] = counter
            entry = {
                "display_placeholder": f"[{cat}_{counter}]",
                "category": cat,
                "value": span["text"],
                "confidence": span.get("confidence", 1.0),
                "sensitivity_tier": span.get("sensitivity_tier", "sensitive"),
                "reasoning": span.get("reasoning", "Matched sensitive criteria"),
            }
            seen[norm_key] = entry
            ordered.append(entry)

        return ordered, degraded

    async def apply_redaction(
        self,
        text: str,
        audience: AudienceType = AudienceType.GENERAL_PUBLIC,
        precomputed_llm_spans: Optional[Tuple[List[SensitiveSpanCandidate], bool]] = None,
    ) -> Tuple[str, List[SecurityActionItem], Dict[str, str], bool]:
        """Scan the SOURCE document and replace sensitive terms with typed
        placeholders. Used only for the source-document transparency log
        (`SecurityActionModel` / `SourceDocumentModel.redacted_text`) — NOT fed
        into generation (generation reads the raw source text directly; see
        `app/adapters/base.py`).

        `precomputed_llm_spans`: pass the (sensitive_spans, degraded) result
        already produced by the merged Source Understanding pass
        (source_understanding_service.extract) for this same source text, so
        this call reuses that LLM output instead of re-running
        `classify_with_llm` a second time over the same document. Omit it
        (the default) to keep the old standalone behavior — this is what
        `routes_sensitivity.py`'s standalone endpoint and existing tests
        still do, and it is unchanged.

        Returns:
            redacted_text: Text with placeholders like [LOCATION_1], [UNIT_NAME_1]
            security_actions: List of actions logged for transparency
            placeholder_map: Dictionary mapping placeholder -> original_value
            degraded: True if the LLM classification layer failed for this
                document and detection fell back to regex-only — the caller
                MUST surface this to the operator, never swallow it silently.
        """
        redacted_text = text
        security_actions: List[SecurityActionItem] = []
        placeholder_map: Dict[str, str] = {}
        category_counters: Dict[str, int] = {}

        accepted_spans, degraded = await self._collect_candidate_spans(
            text, precomputed_llm_spans=precomputed_llm_spans
        )

        # --- Two-Pass Replacement: Reading-Order Numbering & Safe Replacement ---
        entity_placeholders: Dict[Tuple[str, str], str] = {}
        span_assignments: List[Tuple[Dict, str]] = []

        for span in accepted_spans:
            cat = span["category"]
            norm_key = (cat, span["text"].strip().lower())
            if norm_key in entity_placeholders:
                placeholder = entity_placeholders[norm_key]
            else:
                counter = category_counters.get(cat, 0) + 1
                category_counters[cat] = counter
                placeholder = f"[{cat}_{counter}]"
                entity_placeholders[norm_key] = placeholder
                placeholder_map[placeholder] = span["text"]

            span_assignments.append((span, placeholder))
            security_actions.append(SecurityActionItem(
                id=str(uuid.uuid4()),
                placeholder=placeholder,
                category=cat,
                original_value=span["text"],
                confidence=span.get("confidence", 1.0),
                sensitivity_tier=span.get("sensitivity_tier", "sensitive"),
                reasoning=span.get("reasoning", "Matched sensitive criteria"),
                audience_level=audience.value if hasattr(audience, "value") else str(audience),
                is_overridden=False,
            ))

        # Pass 2 (Reverse pass, sorted by start descending): text substitution
        # using the pre-assigned reading-order placeholders.
        for span, placeholder in sorted(span_assignments, key=lambda x: x[0]["start"], reverse=True):
            redacted_text = redacted_text[:span["start"]] + placeholder + redacted_text[span["end"]:]

        return redacted_text, security_actions, placeholder_map, degraded

    def _extract_category_from_placeholder(self, placeholder: str) -> str:
        """'[LOCATION_1]' -> 'LOCATION'."""
        inner = placeholder.strip("[]")
        parts = inner.rsplit("_", 1)
        return parts[0] if len(parts) == 2 and parts[1].isdigit() else inner

    def _generic_phrase_for(self, category: str, tier: str, cycle_index: int) -> str:
        """Look up a generic withhold phrase by (category, tier). Falls back to
        the "sensitive" bucket for a tier with no dedicated phrase set (e.g. a
        "routine" item an analyst chose to withhold anyway), then to a
        hardcoded default — never raises on an unrecognized category or tier."""
        category_phrases = settings.GENERIC_PLACEHOLDER_PHRASES.get(category, {})
        tier_phrases = category_phrases.get(tier) or category_phrases.get("sensitive") or {}
        phrases = tier_phrases.get("en") if isinstance(tier_phrases, dict) else tier_phrases
        if not phrases:
            phrases = ["a redacted detail"]
        return phrases[cycle_index % len(phrases)]

    def resolve_with_disclosure_decisions(
        self,
        content: str,
        disclosure_items: List[Any],
    ) -> str:
        """Resolve a draft's disclosure items directly against the literal text
        that was detected (`detected_value_preview`), by exact substring
        replacement:
        - 'disclose' -> no-op (the real value is already present; generation
          reads the raw source directly, so nothing needs to be substituted in).
        - 'edit'     -> replace the literal detected text with manual_edit_text.
        - 'withhold' -> replace the literal detected text with a generic,
          category-appropriate phrase.

        Deliberately synchronous and deterministic: no second LLM rewrite pass.
        Static phrase substitution can occasionally read awkwardly in an unusual
        sentence structure — a real but accepted tradeoff for determinism,
        testability, and zero additional LLM latency/cost/failure surface in a
        security-adjacent feature.

        Enforces that `suggested_default` is NEVER read or used as an implicit
        fallback — every item here must already carry an explicit analyst_choice.
        """
        resolved = content

        for item in disclosure_items:
            choice = getattr(item, "analyst_choice", None)
            if choice is None:
                raise ValueError(
                    f"Unreviewed item '{getattr(item, 'placeholder', 'unknown')}' encountered during resolution. "
                    f"No unreviewed item may reach output."
                )

        # Sort by literal value length descending to avoid sub-string collisions
        # (e.g. replacing "Sector-7" before a shorter overlapping match).
        items_sorted = sorted(
            disclosure_items,
            key=lambda x: len(getattr(x, "detected_value_preview", "") or ""),
            reverse=True,
        )

        withhold_cycle: Dict[Tuple[str, str], int] = {}
        for item in items_sorted:
            choice = getattr(item, "analyst_choice", None)
            literal_value = getattr(item, "detected_value_preview", None)
            if not literal_value or literal_value not in resolved:
                continue

            if choice == "disclose":
                continue  # already present verbatim; nothing to do
            elif choice == "edit":
                edit_text = getattr(item, "manual_edit_text", "") or ""
                resolved = resolved.replace(literal_value, edit_text)
            elif choice == "withhold":
                category = getattr(item, "category", "OTHER_SENSITIVE")
                tier = getattr(item, "sensitivity_tier", None) or "sensitive"
                cycle_key = (category, tier)
                idx = withhold_cycle.get(cycle_key, 0)
                phrase = self._generic_phrase_for(category, tier, idx)
                withhold_cycle[cycle_key] = idx + 1
                resolved = resolved.replace(literal_value, phrase)

        return resolved


firewall = SensitivityFirewall()
