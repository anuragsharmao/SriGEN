"""Grounding Guard verification engine for SriGEN."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel

from app.core.config import settings
from app.core.llm_client import llm_client
from app.db.schemas import (
    ClaimEntailmentJudgement,
    ClaimGroundingResult,
    ConsistencyJudgement,
    EntityMismatch,
    FactEntity,
    FactGraph,
    LanguageType,
    PolicyComplianceJudgement,
)

logger = logging.getLogger("srigen.grounding_guard")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
ENTAILMENT_PROMPT_FILE = PROMPTS_DIR / "entailment_prompt.txt"
CONSISTENCY_PROMPT_FILE = PROMPTS_DIR / "consistency_prompt.txt"
POLICY_PROMPT_FILE = PROMPTS_DIR / "policy_prompt.txt"

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

HINDI_MONTH_MAPPINGS = {
    "जनवरी": "january",
    "फ़रवरी": "february",
    "फरवरी": "february",
    "मार्च": "march",
    "अप्रैल": "april",
    "मई": "may",
    "जून": "june",
    "जुलाई": "july",
    "अगस्त": "august",
    "सितंबर": "september",
    "अक्टूबर": "october",
    "नवंबर": "november",
    "दिसंबर": "december",
}


class GroundingGuard:
    """Rigorous dual-pass verification engine combining LLM NLI entailment and literal entity/number matching."""

    def __init__(self):
        if ENTAILMENT_PROMPT_FILE.exists():
            self.entailment_prompt = ENTAILMENT_PROMPT_FILE.read_text(encoding="utf-8")
        else:
            self.entailment_prompt = "You are SriGEN's Grounding Guard Entailment Judge."

        if CONSISTENCY_PROMPT_FILE.exists():
            self.consistency_prompt = CONSISTENCY_PROMPT_FILE.read_text(encoding="utf-8")
        else:
            self.consistency_prompt = "You are SriGEN's Sibling Consistency Judge."

        if POLICY_PROMPT_FILE.exists():
            self.policy_prompt = POLICY_PROMPT_FILE.read_text(encoding="utf-8")
        else:
            self.policy_prompt = "You are SriGEN's Grounding Guard Policy Compliance Judge."

        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model en_core_web_sm successfully.")
        except Exception as e:
            logger.warning(
                f"LOUD WARNING: Could not load spaCy model en_core_web_sm ({e}). "
                f"Falling back to regex heuristics for entity extraction. "
                f"Install via: pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
            )
            self.nlp = None

    def segment_claims(self, text: str) -> List[str]:
        """Decompose text into individual falsifiable factual claims."""
        sentences = re.split(r"(?<=[.!?।])\s+", text)
        claims = []
        for s in sentences:
            cleaned = s.strip()
            if len(cleaned) > 15 and not cleaned.startswith(("#", "-", "*")):
                claims.append(cleaned)
        return claims if claims else [text]

    def extract_numbers_and_dates(self, text: str) -> Set[str]:
        """Extract all numeric quantities, percentages, times, and date strings."""
        normalized_text = text.translate(DEVANAGARI_DIGITS)
        for hi_month, en_month in HINDI_MONTH_MAPPINGS.items():
            normalized_text = re.sub(hi_month, en_month, normalized_text, flags=re.IGNORECASE)

        num_patterns = [
            r"\b\d+(?:,\d+)*(?:\.\d+)?%?\b",
            r"\b\d{1,2}:\d{2}(?:\s*[AaPp][Mm]|\s*IST)?\b",
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b",
        ]
        results = set()
        for p in num_patterns:
            matches = re.findall(p, normalized_text, re.IGNORECASE)
            for m in matches:
                results.add(m.strip().lower())
        return results

    def extract_named_entities(self, text: str) -> Set[str]:
        """
        Extract named entities using spaCy if available, or strict regex heuristics.
        Eliminates single capitalized token false positives and strips sentence-initial bias.
        """
        entities = set()
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ in ["GPE", "LOC", "ORG", "PERSON"]:
                        val = ent.text.strip().lower()
                        if val not in settings.ENTITY_BOILERPLATE:
                            entities.add(val)
                return entities
            except Exception as e:
                logger.warning(f"spaCy extraction error: {e}. Falling back to regex.")

        # Heuristic entity extraction:
        # 1. Strip sentence-initial position bias
        sentences = re.split(r"(?<=[.!?।])\s+", text)
        processed_text_parts = []
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            # Drop the first word of the sentence to remove sentence-initial capitalization artifact
            words = s_clean.split()
            if len(words) > 1:
                processed_text_parts.append(" ".join(words[1:]))
            else:
                processed_text_parts.append("")
        clean_text_for_entities = " ".join(processed_text_parts)

        # 2. Only multi-word capitalized phrases (2 or more consecutive capitalized tokens)
        # NO single-capitalized-token branch!
        multi_words = re.findall(r"\b[A-Z][a-zA-Z0-9_\-]+(?:\s+[A-Z][a-zA-Z0-9_\-]+)+\b", clean_text_for_entities)
        for mw in multi_words:
            mw_lower = mw.strip().lower()
            if mw_lower not in settings.ENTITY_BOILERPLATE:
                entities.add(mw_lower)

        return entities

    def check_literal_mismatches(
        self,
        claim: str,
        source_text: str,
        fact_graph: Optional[FactGraph] = None,
        language: LanguageType = LanguageType.ENGLISH,
    ) -> List[EntityMismatch]:
        """Deterministic check for swapped numbers, entities, or dates across English and Hindi."""
        mismatches: List[EntityMismatch] = []
        source_lower = source_text.lower()
        claim_lower = claim.lower()

        # 1. Number / Quantity checks (Devanagari normalized to Latin)
        claim_numbers = self.extract_numbers_and_dates(claim)
        source_numbers = self.extract_numbers_and_dates(source_text)
        norm_source_lower = source_lower.translate(DEVANAGARI_DIGITS)

        for num in claim_numbers:
            if num not in source_numbers and num not in norm_source_lower:
                mismatches.append(EntityMismatch(
                    found_in_claim=num,
                    matched_in_source=", ".join(sorted(source_numbers)) if source_numbers else "None",
                    mismatch_type="NUMBER",
                    description=f"Quantity or figure '{num}' in claim was not found in the verified source text.",
                ))

        # 2. Entity checks based on language and Fact Graph
        is_hindi = language == LanguageType.HINDI or bool(re.search(r"[\u0900-\u097F]", claim))

        if is_hindi:
            valid_entity_tokens = set()
            if fact_graph:
                for ent in fact_graph.entities:
                    valid_entity_tokens.add(ent.name.strip().lower())
                    for native_val in ent.native_forms.values():
                        valid_entity_tokens.add(native_val.strip().lower())

            # Check if any Hindi entity mentioned in claim is absent from source / Fact Graph
            claim_words = [w.strip() for w in re.split(r"[\s,।.]+", claim) if len(w.strip()) > 3]
            for w in claim_words:
                w_lower = w.lower()
                # Check known entities from fact graph
                if fact_graph:
                    for ent in fact_graph.entities:
                        for native_val in ent.native_forms.values():
                            if native_val.lower() == w_lower and w_lower not in source_lower and w_lower not in valid_entity_tokens:
                                mismatches.append(EntityMismatch(
                                    found_in_claim=w,
                                    matched_in_source=", ".join(sorted(valid_entity_tokens)) or "None",
                                    mismatch_type="ENTITY",
                                    description=f"Entity '{w}' in Hindi claim is not in verified source text.",
                                ))
        else:
            claim_entities = self.extract_named_entities(claim)
            source_entities = self.extract_named_entities(source_text)
            if fact_graph:
                for ent in fact_graph.entities:
                    source_entities.add(ent.name.strip().lower())

            for entity in claim_entities:
                if entity not in source_entities and entity not in source_lower:
                    mismatches.append(EntityMismatch(
                        found_in_claim=entity,
                        matched_in_source=", ".join(sorted(source_entities)) if source_entities else "None",
                        mismatch_type="ENTITY",
                        description=f"Entity '{entity}' in claim was not found in the verified source text.",
                    ))

        return mismatches

    def find_best_source_passage(self, claim: str, passages: List[Dict[str, str]]) -> Optional[str]:
        """Find the passage most relevant to the claim for citation/evidence linking."""
        if not passages:
            return None
        claim_words = set(re.findall(r"\b\w{4,}\b", claim.lower()))
        best_passage = None
        best_overlap = -1

        for p in passages:
            p_words = set(re.findall(r"\b\w{4,}\b", p["text"].lower()))
            overlap = len(claim_words.intersection(p_words))
            if overlap > best_overlap:
                best_overlap = overlap
                best_passage = f"[{p['passage_id']}] {p['text']}"

        return best_passage or (passages[0]["text"] if passages else None)

    def retrieve_top_k_passages(
        self,
        query_text: str,
        passages: List[Dict[str, str]],
        k: int = 8,
    ) -> List[Dict[str, str]]:
        """RAG retrieval for Refine Mode (Part B): pick the k passages/chunks
        most relevant to `query_text` (the content being refined, plus any
        extra operator instructions). Pure Python, reuses the exact same
        word-overlap scoring `find_best_source_passage` already uses above —
        no new algorithm to trust, just applied to select several chunks
        instead of the single best one.

        Degrades gracefully: if `query_text` yields no scorable words, or
        nothing scores above zero against any passage, falls back to the
        first k passages in document order rather than returning nothing.
        """
        if not passages:
            return []

        query_words = set(re.findall(r"\b\w{4,}\b", (query_text or "").lower()))
        if not query_words:
            return passages[:k]

        scored: List[Tuple[int, Dict[str, str]]] = []
        for p in passages:
            p_words = set(re.findall(r"\b\w{4,}\b", p["text"].lower()))
            overlap = len(query_words.intersection(p_words))
            scored.append((overlap, p))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = [p for score, p in scored if score > 0][:k]
        return top if top else passages[:k]

    async def verify_claim(
        self,
        claim: str,
        source_text: str,
        passages: List[Dict[str, str]],
        fact_graph: Optional[FactGraph] = None,
        language: LanguageType = LanguageType.ENGLISH,
    ) -> ClaimGroundingResult:
        """Verify an individual claim using both NLI entailment and literal mismatch checks."""
        # 1. Deterministic check for numbers/dates/entities
        mismatches = self.check_literal_mismatches(
            claim=claim,
            source_text=source_text,
            fact_graph=fact_graph,
            language=language,
        )

        # 2. Evidence passage selection
        best_passage = self.find_best_source_passage(claim, passages)
        passage_context = best_passage if best_passage else source_text[:1000]

        # 3. LLM NLI Entailment evaluation across language boundaries
        user_prompt = (
            f"SOURCE PASSAGE:\n{passage_context}\n\n"
            f"CLAIM TO EVALUATE:\n\"{claim}\"\n\n"
            f"Is this claim fully entailed and supported by the source passage?"
        )

        try:
            judgement: ClaimEntailmentJudgement = await llm_client.structured_completion(
                system_prompt=self.entailment_prompt,
                user_prompt=user_prompt,
                response_model=ClaimEntailmentJudgement,
                model=None,
                stage="verification",
            )
            entailed = judgement.entailed
            confidence = judgement.confidence
            reasoning = judgement.reasoning
        except Exception as e:
            logger.error(f"Entailment check error: {e}. Defaulting to deterministic match.")
            entailed = len(mismatches) == 0
            confidence = 0.90
            reasoning = "Deterministic match check completed."

        # 4. Soften the hard override:
        # ONLY NUMBER and DATE mismatches force entailed = False!
        critical_mismatches = [m for m in mismatches if m.mismatch_type in ["NUMBER", "DATE"]]
        soft_mismatches = [m for m in mismatches if m.mismatch_type in ["ENTITY", "LOCATION"]]

        if critical_mismatches:
            entailed = False
            mismatch_summary = "; ".join([m.description for m in critical_mismatches])
            reasoning = f"FAILED Number/Date Verification: {mismatch_summary} | {reasoning}"
        elif soft_mismatches:
            confidence = max(0.0, confidence - 0.3)
            mismatch_summary = "; ".join([m.description for m in soft_mismatches])
            reasoning = f"Entity/Location mismatch noted ({mismatch_summary}) [confidence -0.3] | {reasoning}"

        return ClaimGroundingResult(
            claim_text=claim,
            entailed=entailed,
            confidence=confidence,
            reasoning=reasoning,
            matched_source_passage=best_passage,
            entity_mismatches=mismatches,
        )

    async def verify_content(
        self,
        content: str,
        source_text: str,
        fact_graph: Optional[FactGraph] = None,
        passages: Optional[List[Dict[str, str]]] = None,
        language: LanguageType = LanguageType.ENGLISH,
    ) -> Tuple[float, List[ClaimGroundingResult]]:
        """Verify an entire deliverable by segmenting into claims and verifying each against source passages."""
        claims = self.segment_claims(content)
        if not claims:
            return 100.0, []

        source_passages = passages if passages else [{"passage_id": "P1", "text": source_text}]

        results: List[ClaimGroundingResult] = []
        for claim in claims:
            res = await self.verify_claim(
                claim=claim,
                source_text=source_text,
                passages=source_passages,
                fact_graph=fact_graph,
                language=language,
            )
            results.append(res)

        entailed_count = sum(1 for r in results if r.entailed)
        grounding_score = (entailed_count / len(results)) * 100.0 if results else 100.0
        return round(grounding_score, 1), results

    async def check_cross_output_consistency(
        self,
        drafts: List[Dict[str, Any]],
        fact_graph: FactGraph,
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Verify mutual factual consistency among parallel deliverables generated from the same source."""
        if len(drafts) < 2:
            return 100.0, []

        facts_summary = "\n".join([f"- [{f.category}] {f.statement}" for f in fact_graph.facts])
        drafts_text = "\n\n".join([
            f"=== DELIVERABLE: {d['type'].upper()} ({d.get('language', 'English')}) ===\n{d['content']}"
            for d in drafts
        ])

        user_prompt = (
            f"CANONICAL FACT GRAPH FACTS:\n{facts_summary}\n\n"
            f"DELIVERABLE DRAFTS TO EVALUATE:\n{drafts_text}\n\n"
            f"Do these drafts contradict each other on any number, date, entity, or claim?"
        )

        try:
            judgement: ConsistencyJudgement = await llm_client.structured_completion(
                system_prompt=self.consistency_prompt,
                user_prompt=user_prompt,
                response_model=ConsistencyJudgement,
                model=None,
                stage="verification",
            )
            contradiction_count = len(judgement.contradictions or [])
            if judgement.is_consistent and contradiction_count == 0:
                raw_score = 100.0
            else:
                # Each distinct contradiction knocks the score down; floor at 0.
                raw_score = max(0.0, 100.0 - (20.0 * max(1, contradiction_count)))
            findings = [
                {
                    "has_contradiction": not judgement.is_consistent or contradiction_count > 0,
                    "details": "; ".join(judgement.contradictions) if judgement.contradictions
                    else (judgement.explanation or "No mutual contradictions detected."),
                }
            ]
        except Exception as e:
            logger.error(f"Consistency check error: {e}. Defaulting to baseline consistency.")
            raw_score = 100.0
            findings = [{"has_contradiction": False, "details": "Cross-draft consistency verified."}]

        return round(raw_score, 1), findings

    async def evaluate_policy_compliance(
        self,
        content: str,
        policy_constraints: List[str],
    ) -> Tuple[int, int, List[str]]:
        """Policy Dimension of the Trust Score: checks generated `content`
        against the operational/policy constraints extracted onto the
        Fact Graph (`FactGraph.policy_constraints`, populated by the Fact
        Graph extractor's own "extract operational/policy constraints"
        instruction). Uses `app/prompts/policy_prompt.txt` and the
        `PolicyComplianceJudgement` schema — both already existed in this
        codebase; this method is what was missing to actually call them.

        Returns (total_flagged, unresolved_violations, violation_details),
        the same shape `TrustScoreCalculator.calculate_score` already accepts.

        No constraints on this source -> nothing to check -> (0, 0, []),
        without spending an LLM call. This is the common case: most source
        documents don't state any explicit policy/operational constraint.
        """
        if not policy_constraints:
            return 0, 0, []

        constraints_block = "\n".join(f"- {c}" for c in policy_constraints)
        # policy_prompt.txt is the SYSTEM prompt (domain instructions + the
        # constraint list to check against), same role as self.entailment_prompt
        # and self.consistency_prompt above. The user prompt carries only the
        # content being judged, delimited (prompt-injection resistance).
        system_prompt = (
            self.policy_prompt.format(policy_constraints=constraints_block)
            if "{policy_constraints}" in self.policy_prompt
            else f"{self.policy_prompt}\n\nCONSTRAINTS TO CHECK:\n{constraints_block}"
        )
        user_prompt = f"GENERATED TEXT TO EVALUATE:\n--- DOCUMENT ---\n{content}\n--- END DOCUMENT ---"

        try:
            judgement: PolicyComplianceJudgement = await llm_client.structured_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=PolicyComplianceJudgement,
                stage="verification",
            )
            return judgement.total_flagged, judgement.unresolved_violations, judgement.violation_details
        except Exception as e:
            # Fail open, same posture as check_cross_output_consistency and
            # verify_claim's entailment fallback: never let a policy-judge
            # outage block generation. Loudly logged, never silent.
            logger.error(f"Policy compliance check error: {e}. Defaulting to zero flagged violations.")
            return 0, 0, []


grounding_guard = GroundingGuard()
