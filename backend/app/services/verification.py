"""Shared helper: runs Grounding Guard + Trust Score over a piece of content
against its claimed source and packages the result as a StageResult. Used by
both the standalone /verify endpoint and every stage of the /refine pipeline
(original, fact-fixed, refined) — the same verification logic runs after
every transformation, unconditionally, so a refinement step can never
silently hide a newly introduced factual problem.
"""

from typing import Dict, List, Optional

from app.db.schemas import StageResult
from app.services.grounding_guard import grounding_guard
from app.services.trust_score import trust_score_calculator


async def build_stage_result(
    content: str,
    source_text: str,
    changes_summary: Optional[str] = None,
    passages: Optional[List[Dict[str, str]]] = None,
) -> StageResult:
    """`passages`, when provided, is a set of retrieved evidence chunks (RAG)
    to verify claims against instead of the whole `source_text` as one
    passage — see app/api/routes_refine.py's draft_id / ad-hoc chunking
    paths (Part B). Optional and defaults to None so every existing caller
    that verifies against a single small pasted source is unaffected."""
    grounding_score, claim_results = await grounding_guard.verify_content(
        content=content,
        source_text=source_text,
        passages=passages,
    )
    mismatches = [m for c in claim_results for m in c.entity_mismatches]

    trust_breakdown = trust_score_calculator.calculate_score(
        claim_results=claim_results,
        consistency_judgement=None,
        security_actions=None,
    )

    is_corrupted = len(mismatches) > 0 or any(not c.entailed for c in claim_results)

    if not is_corrupted and trust_breakdown.composite_trust_score >= 90:
        verdict = "VERIFIED: Content is strictly grounded in the claimed source with zero contradictions."
    elif is_corrupted and trust_breakdown.composite_trust_score < 70:
        verdict = "HIGH RISK / CORRUPTED: Significant discrepancies or factual tampering detected against source truth."
    else:
        verdict = "CAUTION: Partial grounding; discrepancies or unentailed claims identified."

    return StageResult(
        content=content,
        trust_score=trust_breakdown,
        claims=claim_results,
        entity_mismatches=mismatches,
        verdict=verdict,
        is_corrupted_detected=is_corrupted,
        changes_summary=changes_summary,
    )
