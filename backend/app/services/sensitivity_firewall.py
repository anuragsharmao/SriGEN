"""Sensitivity Firewall: two-layer hybrid (regex + LLM classification) detection,
typed placeholder redaction for source-document transparency logging, and
deterministic (no second LLM pass) disclosure-decision resolution.
"""

import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.config import settings
from app.db.schemas import (
    AudienceType,
    SecurityActionItem,
    SensitiveSpanCandidate,
    SensitivityClassificationResult,
)

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

        # Delimited so ingested content can never be mistaken for instructions
        # (prompt-injection resistance) — the classification prompt itself
        # states the same rule explicitly; see sensitivity_classification_prompt.txt.
        user_prompt = f"--- DOCUMENT ---\n{text}\n--- END DOCUMENT ---"

        try:
            result: SensitivityClassificationResult = await llm_client.structured_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=SensitivityClassificationResult,
            )
        except Exception as e:
            logger.error(f"LLM sensitivity classification failed: {e}. Proceeding with regex-only results — DEGRADED.")
            return [], True

        # Validate: exact_text must actually appear verbatim in the source.
        # Drop (and log) any hallucinated span rather than crashing or silently
        # trying to redact text that doesn't exist.
        validated: List[SensitiveSpanCandidate] = []
        for span in result.sensitive_spans:
            if span.exact_text and span.exact_text in text:
                validated.append(span)
            else:
                logger.warning(f"Dropped non-verbatim LLM span candidate: {span.exact_text!r}")
        return validated, False

    async def _collect_candidate_spans(self, text: str) -> Tuple[List[Dict], bool]:
        """Regex + LLM span collection, de-duplicated by overlap. Shared by both
        the source-side redaction pass and the output-side disclosure scan.
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
                        "source": "regex",
                        "reasoning": "Matched known pattern",
                    })

        # --- Layer 2: LLM semantic pass ---
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
                    "confidence": span.confidence,
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
                "reasoning": span.get("reasoning", "Matched sensitive criteria"),
            }
            seen[norm_key] = entry
            ordered.append(entry)

        return ordered, degraded

    async def apply_redaction(
        self,
        text: str,
        audience: AudienceType = AudienceType.GENERAL_PUBLIC,
    ) -> Tuple[str, List[SecurityActionItem], Dict[str, str], bool]:
        """Scan the SOURCE document and replace sensitive terms with typed
        placeholders. Used only for the source-document transparency log
        (`SecurityActionModel` / `SourceDocumentModel.redacted_text`) — NOT fed
        into generation (generation reads the raw source text directly; see
        `app/adapters/base.py`).

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

        accepted_spans, degraded = await self._collect_candidate_spans(text)

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

    def _generic_phrase_for(self, category: str, cycle_index: int) -> str:
        category_phrases = settings.GENERIC_PLACEHOLDER_PHRASES.get(category, {})
        phrases = category_phrases.get("en") if isinstance(category_phrases, dict) else category_phrases
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

        withhold_cycle: Dict[str, int] = {}
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
                idx = withhold_cycle.get(category, 0)
                phrase = self._generic_phrase_for(category, idx)
                withhold_cycle[category] = idx + 1
                resolved = resolved.replace(literal_value, phrase)

        return resolved


firewall = SensitivityFirewall()
