"""Fact Graph extraction service: builds canonical, structured single-source-of-truth."""

import logging
from pathlib import Path
from app.core.llm_client import llm_client, LLMUnavailableError
from app.db.schemas import FactGraph

logger = logging.getLogger("srigen.fact_graph")

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "fact_graph_prompt.txt"


class FactGraphService:
    """Service to extract canonical Fact Graphs using Groq structured output."""

    def __init__(self):
        if PROMPT_FILE.exists():
            self.system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
        else:
            self.system_prompt = "You are SriGEN's Canonical Fact Graph Extractor."

    async def extract_fact_graph(self, text: str) -> FactGraph:
        """Extract canonical structured facts, entities, numbers, and dates from text."""
        user_prompt = (
            f"Please extract the canonical Fact Graph from the following source text.\n\n"
            f"--- SOURCE TEXT ---\n{text}\n--- END SOURCE TEXT ---"
        )

        try:
            fact_graph = await llm_client.structured_completion(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                response_model=FactGraph,
                stage="fact_graph",
            )
            return fact_graph
        except LLMUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error extracting Fact Graph: {e}.")
            raise LLMUnavailableError(f"Fact graph extraction failed: {e}", stage="fact_graph") from e


fact_graph_service = FactGraphService()
