"""Aggregation Check Service: detects mosaic intelligence and combination risks."""

import json
import logging
import uuid
from typing import Any, List
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.llm_client import llm_client
from app.db.models import AggregationFindingModel, DisclosureItemModel

logger = logging.getLogger("srigen.aggregation_check")


class AggregationFindingCandidate(BaseModel):
    description: str
    severity: str = "medium"


class AggregationEvaluationResult(BaseModel):
    has_combination_risk: bool
    findings: List[AggregationFindingCandidate] = []


class AggregationChecker:
    """Evaluates combinations of disclosed entities/facts for emergent classified or sensitive risk."""

    async def run_aggregation_check(
        self,
        draft_id: str,
        draft_content: str,
        db: Session,
    ) -> List[AggregationFindingModel]:
        """
        Run combination/mosaic intelligence analysis on the draft and currently disclosed items.
        Creates and returns unacknowledged AggregationFindingModel records.
        """
        existing_findings = (
            db.query(AggregationFindingModel)
            .filter(AggregationFindingModel.draft_id == draft_id)
            .all()
        )
        if existing_findings:
            return existing_findings

        # Fetch disclosed items for this draft
        disclosed_items = (
            db.query(DisclosureItemModel)
            .filter(
                DisclosureItemModel.draft_id == draft_id,
                DisclosureItemModel.analyst_choice == "disclose",
            )
            .all()
        )

        disclosed_facts = [
            f"Category: {item.category}, Value: {item.detected_value_preview or item.placeholder}"
            for item in disclosed_items
        ]

        system_prompt = (
            "You are a military and intelligence operational security (OPSEC) analyst. "
            "Your task is to analyze a proposed deliverable draft and its disclosed facts for MOSAIC INTELLIGENCE / AGGREGATION RISKS.\n"
            "An aggregation risk occurs when two or more facts, individually unclassified or low-risk, combine to reveal sensitive "
            "capabilities, specific deployments, unit strengths, or critical vulnerabilities that none reveal alone."
        )

        user_prompt = (
            f"=== DRAFT CONTENT ===\n{draft_content}\n\n"
            f"=== DISCLOSED FACTS / ENTITIES ===\n"
            + ("\n".join(disclosed_facts) if disclosed_facts else "None explicitly disclosed yet.")
            + "\n\n"
            f"Evaluate if any combination of these facts creates an operational security hazard. "
            f"If so, detail each combination finding and assign severity (low, medium, high, critical)."
        )

        try:
            eval_result: AggregationEvaluationResult = await llm_client.structured_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=AggregationEvaluationResult,
            )
        except Exception as e:
            logger.warning(f"Aggregation LLM check failed: {e}. Falling back to rule simulation.")
            eval_result = self._simulate_fallback(disclosed_items)

        created_findings = []
        if eval_result.has_combination_risk and eval_result.findings:
            for candidate in eval_result.findings:
                finding = AggregationFindingModel(
                    id=str(uuid.uuid4()),
                    draft_id=draft_id,
                    description=candidate.description,
                    severity=candidate.severity,
                    acknowledged=False,
                )
                db.add(finding)
                created_findings.append(finding)
            db.commit()

        return created_findings

    def _simulate_fallback(self, disclosed_items: List[DisclosureItemModel]) -> AggregationEvaluationResult:
        """Deterministic simulation for offline / testing mode."""
        categories = {i.category for i in disclosed_items}
        if "UNIT_NAME" in categories and "LOCATION" in categories:
            return AggregationEvaluationResult(
                has_combination_risk=True,
                findings=[
                    AggregationFindingCandidate(
                        description="Combining unit identity with specific operational location discloses tactical deployment staging.",
                        severity="high",
                    )
                ],
            )
        if "CLASSIFIED_ASSET" in categories and "LOCATION" in categories:
            return AggregationEvaluationResult(
                has_combination_risk=True,
                findings=[
                    AggregationFindingCandidate(
                        description="Correlating classified defense asset with geographical coordinates exposes critical infrastructure vulnerability.",
                        severity="critical",
                    )
                ],
            )
        return AggregationEvaluationResult(has_combination_risk=False, findings=[])


aggregation_checker = AggregationChecker()
