"""Routes for Standalone Verification Mode (/verify).

Kept as a thin backward-compatible alias over the same verification logic
used by the first stage of /refine (app/services/verification.py). It never
runs factual correction or content refinement — for that, use POST /refine
with fix_facts and/or refine_content set.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from app.db.schemas import VerifyRequest, VerifyResponse
from app.services.verification import build_stage_result

router = APIRouter()
logger = logging.getLogger("srigen.routes_verify")


@router.post(
    "/verify",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Standalone Grounding Verification Mode (alias of the /refine 'original' stage)",
    description=(
        "Secondary capability / side-door into Grounding Guard: verifies an external draft or "
        "claimed document against its source. Flags swapped numbers, altered locations, and "
        "hallucinations. Read-only: never writes to the provenance ledger, never corrects facts, "
        "never refines content — see POST /refine for those."
    ),
)
async def verify_external_content(request: VerifyRequest):
    if not request.content_to_verify.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content to verify cannot be empty.")
    if not request.claimed_source.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Claimed source text cannot be empty.")

    try:
        stage = await build_stage_result(request.content_to_verify, request.claimed_source)
        return VerifyResponse(
            trust_score=stage.trust_score,
            claims=stage.claims,
            entity_mismatches=stage.entity_mismatches,
            overall_verdict=stage.verdict,
            is_corrupted_detected=stage.is_corrupted_detected,
        )
    except Exception as e:
        logger.error(f"Verification error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Verification failed: {str(e)}")
