"""Fact Fixer: narrowly-scoped factual correction pass. Corrects ONLY the
specific mismatches/unentailed claims it is handed — never rewrites tone,
audience, language, length, content style, communication objective, or
detail focus. See app/prompts/fact_fix_prompt.txt for the full contract."""

import logging
from pathlib import Path
from typing import List, Tuple

from app.core.llm_client import llm_client
from app.db.schemas import ClaimGroundingResult, EntityMismatch, FactFixResult

logger = logging.getLogger("srigen.fact_fixer")
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "fact_fix_prompt.txt"


def _build_issues_block(mismatches: List[EntityMismatch], unentailed_claims: List[ClaimGroundingResult]) -> str:
    lines: List[str] = []
    if mismatches:
        lines.append("Entity/Number/Date mismatches:")
        for m in mismatches:
            lines.append(f"- [{m.mismatch_type}] {m.description}")
    if unentailed_claims:
        lines.append("\nUnentailed claims:")
        for c in unentailed_claims:
            lines.append(f"- Claim: \"{c.claim_text}\" — Reasoning: {c.reasoning}")
    if not lines:
        lines.append("(No specific factual problems were provided.)")
    return "\n".join(lines)


class FactFixer:
    async def fix(
        self,
        content: str,
        source_text: str,
        mismatches: List[EntityMismatch],
        unentailed_claims: List[ClaimGroundingResult],
    ) -> Tuple[str, str]:
        """Returns (corrected_content, changes_summary). If nothing was flagged,
        returns the content unchanged rather than calling the LLM at all."""
        if not mismatches and not unentailed_claims:
            return content, "No factual issues detected; content unchanged."

        template = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else (
            "You are SriGEN's Fact Fixer. Correct only the flagged factual problems: {issues_block}\n\n"
            "DRAFT:\n{content}\n\nSOURCE:\n{source_text}"
        )
        issues_block = _build_issues_block(mismatches, unentailed_claims)
        prompt = template.format(content=content, source_text=source_text, issues_block=issues_block)

        result: FactFixResult = await llm_client.structured_completion(
            system_prompt=prompt,
            user_prompt="Perform the factual correction pass now, following the rules above exactly.",
            response_model=FactFixResult,
            stage="verification",
        )

        summary = result.changes_summary
        if result.unresolved_flags:
            summary += " Unresolved (flagged for human review): " + "; ".join(result.unresolved_flags)

        return result.corrected_content, summary


fact_fixer = FactFixer()
