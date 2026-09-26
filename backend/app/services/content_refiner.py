"""Content Refiner: multi-dimensional deliverable refinement. All seven
Deliverable Specification dimensions (Audience, Tone, Language, Length,
Content Style, Communication Objective, Detail Focus) are equal peers — tone
is not the primary axis. A dimension left as None means "keep it as it
currently is", applied together with whichever dimensions ARE explicitly
requested, as one coherent transformation. See app/prompts/content_refine_prompt.txt.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Tuple

from app.core.llm_client import llm_client
from app.db.schemas import ContentRefineResult
from app.services.spec_formatting import EQUAL_WEIGHT_NOTICE, format_deliverable_spec_block

logger = logging.getLogger("srigen.content_refiner")
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "content_refine_prompt.txt"


class ContentRefiner:
    async def refine(
        self,
        content: str,
        source_text: str,
        spec_fields: Dict[str, Any],
        extra_instructions: str = "",
    ) -> Tuple[str, str]:
        """spec_fields keys: audience, tone, language, length, content_style,
        communication_objective, detail_focus — any of which may be None,
        meaning 'keep as is'. Returns (refined_content, changes_summary)."""
        spec_block = format_deliverable_spec_block(
            audience=spec_fields.get("audience"),
            tone=spec_fields.get("tone"),
            language=spec_fields.get("language"),
            length=spec_fields.get("length"),
            content_style=spec_fields.get("content_style"),
            communication_objective=spec_fields.get("communication_objective"),
            detail_focus=spec_fields.get("detail_focus"),
        )

        template = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else (
            "You are SriGEN's Content Refiner. {equal_weight_notice}\n\n"
            "SPEC:\n{spec_block}\n\nEXTRA INSTRUCTIONS:\n{extra_instructions}\n\n"
            "CONTENT:\n{content}\n\nSOURCE:\n{claimed_source}"
        )
        prompt = template.format(
            equal_weight_notice=EQUAL_WEIGHT_NOTICE,
            spec_block=spec_block,
            extra_instructions=extra_instructions or "(none provided)",
            content=content,
            claimed_source=source_text,
        )

        result: ContentRefineResult = await llm_client.structured_completion(
            system_prompt=prompt,
            user_prompt="Perform the multi-dimensional refinement now, following the rules above exactly.",
            response_model=ContentRefineResult,
            stage="generation",
        )

        return result.refined_content, result.changes_summary


content_refiner = ContentRefiner()
