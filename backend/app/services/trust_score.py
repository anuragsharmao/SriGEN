"""Trust Score engine: computes Grounding, Consistency, and Policy into a single composite score."""

from typing import List, Optional
from app.db.schemas import ClaimGroundingResult, ConsistencyJudgement, SecurityActionItem, TrustScoreBreakdown


class TrustScoreCalculator:
    """Calculates explainable high-assurance Trust Scores according to the SriGEN specification.

    Dimensions:
    1. Grounding = entailed claims / total claims (dual-verified via NLI & entity/number match)
    2. Consistency = cross-output factual agreement
    3. Policy = policy and operational constraint compliance

    Note: Redactions in the Security Actions Log are never penalized in the score.
    """

    def calculate_score(
        self,
        claim_results: List[ClaimGroundingResult],
        consistency_judgement: Optional[ConsistencyJudgement] = None,
        security_actions: Optional[List[SecurityActionItem]] = None,
        unresolved_policy_violations: int = 0,
        total_policy_checks: int = 0,
        total_flagged: Optional[int] = None,
        unresolved_violations: Optional[int] = None,
        consistency_score_override: Optional[float] = None,
        policy_score_override: Optional[float] = None,
    ) -> TrustScoreBreakdown:
        # 1. Grounding Dimension
        total_claims = len(claim_results)
        if total_claims == 0:
            grounding_score = 100.0
        else:
            entailed_count = sum(1 for c in claim_results if c.entailed)
            grounding_score = round((entailed_count / total_claims) * 100.0, 1)

        # 2. Consistency Dimension
        # Formula: 1 - (contradicting facts / total cross-checked facts).
        # A caller that already computed a consistency score directly (e.g. the
        # orchestrator's multi-deliverable cross-output check) may pass it
        # straight through via consistency_score_override instead of
        # reconstructing a ConsistencyJudgement object.
        if consistency_score_override is not None:
            consistency_score = round(consistency_score_override, 1)
        elif consistency_judgement is None:
            consistency_score = 100.0
        else:
            total_checked = max(1, getattr(consistency_judgement, "total_facts_checked", 1))
            contradiction_count = len(consistency_judgement.contradictions)
            consistency_score = round(max(0.0, (1.0 - (contradiction_count / total_checked)) * 100.0), 1)

        # 3. Policy Dimension
        # Formula: 100% if total_flagged == 0, otherwise 1 - (unresolved_violations / total_flagged)
        if policy_score_override is not None:
            policy_score = round(policy_score_override, 1)
        else:
            flagged = total_flagged if total_flagged is not None else total_policy_checks
            unresolved = unresolved_violations if unresolved_violations is not None else unresolved_policy_violations

            if flagged == 0 or unresolved == 0:
                policy_score = 100.0
            else:
                policy_score = round(max(0.0, (1.0 - (unresolved / flagged)) * 100.0), 1)

        # 4. Composite Trust Score
        # Weights: 50% Grounding, 30% Consistency, 20% Policy
        composite = round(
            (0.50 * grounding_score) + (0.30 * consistency_score) + (0.20 * policy_score),
            1
        )

        explanation = (
            f"Trust Score: {composite}/100. "
            f"[Grounding: {grounding_score}% ({sum(1 for c in claim_results if c.entailed)}/{total_claims} verified claims); "
            f"Consistency: {consistency_score}%; "
            f"Policy: {policy_score}%]. "
            f"Redactions are tracked separately in the Security Actions Log."
        )

        return TrustScoreBreakdown(
            grounding_score=grounding_score,
            consistency_score=consistency_score,
            policy_score=policy_score,
            composite_trust_score=composite,
            formula_explanation=explanation,
        )


trust_score_calculator = TrustScoreCalculator()
