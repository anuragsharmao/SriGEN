"""Routes for Refine Mode: verification + optional factual correction + optional
multi-dimensional content refinement.

Pipeline (Section 10 of the Refine spec):
    1. Always verify original content against claimed_source.
    2. If fix_facts: correct only detected factual issues, then re-verify.
    3. If refine_content: apply every explicitly requested Deliverable Spec
       dimension together (Audience, Tone, Language, Length, Content Style,
       Communication Objective, Detail Focus are equal peers — tone is not
       primary), then re-verify.
    4. Return every stage that ran, plus final_content (the last stage's content).

Every stage is re-verified — a refinement is never assumed to be factually
safe just because an LLM produced it.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.db.schemas import RefineRequest, RefineResponse
from app.services.content_refiner import content_refiner
from app.services.fact_fixer import fact_fixer
from app.services.verification import build_stage_result

router = APIRouter()
logger = logging.getLogger("srigen.routes_refine")


@router.post(
    "/refine",
    response_model=RefineResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify, Optionally Fact-Fix, Optionally Multi-Dimensionally Refine",
    description=(
        "Always verifies content_to_verify against claimed_source via Grounding Guard. "
        "If fix_facts=True, narrowly corrects only the factual problems that were actually "
        "detected. If refine_content=True, transforms the content toward the requested "
        "Deliverable Specification — Audience, Tone, Language, Length, Content Style, "
        "Communication Objective, and Detail Focus are treated as equal peer dimensions, not "
        "a tone-primary transformation; any dimension left unset is explicitly preserved "
        "('keep as is'), never left to model discretion. Every stage is re-verified."
    ),
)
async def refine_content_endpoint(request: RefineRequest):
    if not request.content_to_verify.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content to verify cannot be empty.")
    if not request.claimed_source.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Claimed source text cannot be empty.")

    try:
        # 1. Always verify original content.
        original = await build_stage_result(request.content_to_verify, request.claimed_source)
        working_content = request.content_to_verify

        fact_fixed = None
        refined = None

        # 2. Optional narrow factual correction pass.
        if request.fix_facts:
            unentailed_claims = [c for c in original.claims if not c.entailed]
            fixed_text, changes_summary = await fact_fixer.fix(
                content=working_content,
                source_text=request.claimed_source,
                mismatches=original.entity_mismatches,
                unentailed_claims=unentailed_claims,
            )
            fact_fixed = await build_stage_result(fixed_text, request.claimed_source, changes_summary=changes_summary)
            working_content = fixed_text

        # 3. Optional multi-dimensional refinement — all seven dimensions applied
        # together as one transformation; unset dimensions are explicitly
        # preserved via the shared spec-formatting helper's "KEEP AS IS".
        if request.refine_content:
            refined_text, changes_summary = await content_refiner.refine(
                content=working_content,
                source_text=request.claimed_source,
                spec_fields={
                    "audience": request.audience,
                    "tone": request.tone,
                    "language": request.language,
                    "length": request.length,
                    "content_style": request.content_style,
                    "communication_objective": request.communication_objective,
                    "detail_focus": request.detail_focus,
                },
                extra_instructions=request.extra_instructions or "",
            )
            refined = await build_stage_result(refined_text, request.claimed_source, changes_summary=changes_summary)
            working_content = refined_text

        final_content = working_content

        return RefineResponse(
            original=original,
            fact_fixed=fact_fixed,
            refined=refined,
            final_content=final_content,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refine pipeline error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Refine pipeline failed: {str(e)}")
