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
from typing import Dict, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DeliverableDraftModel, DocumentChunkModel
from app.db.schemas import RefineRequest, RefineResponse
from app.services.chunking import chunk_document
from app.services.content_refiner import content_refiner
from app.services.fact_fixer import fact_fixer
from app.services.grounding_guard import grounding_guard
from app.services.verification import build_stage_result

router = APIRouter()
logger = logging.getLogger("srigen.routes_refine")


def _resolve_source_and_passages(request: RefineRequest, db: Session) -> Tuple[str, List[Dict[str, str]]]:
    """Part B: resolve evidence for Refine Mode without requiring the client
    to hold and resend the full source text on every call.

    - draft_id set: server-side RAG (Part B2). Retrieve the persisted chunks
      for that draft's source document and pick the k most relevant to the
      content being refined (plus extra_instructions) via the same
      word-overlap retrieval find_best_source_passage already uses.
    - draft_id not set (claimed_source only): backward-compatible ad-hoc path
      (Part B3). `claimed_source` is chunked in-memory, on the fly, using the
      exact same deterministic chunker Part A built — no DB persistence,
      one-off — closing the same "whole document, once per claim" bug for
      pasted/ad-hoc content too.
    """
    if request.draft_id:
        draft = db.query(DeliverableDraftModel).filter_by(id=request.draft_id).first()
        if not draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Draft with ID {request.draft_id} not found.")

        if request.claimed_source and request.claimed_source.strip():
            logger.info(
                f"RefineRequest for draft {request.draft_id} included claimed_source as well as "
                f"draft_id — draft_id takes precedence (server-side retrieval); claimed_source ignored."
            )

        all_chunks = (
            db.query(DocumentChunkModel)
            .filter_by(source_id=draft.source_id)
            .order_by(DocumentChunkModel.chunk_index)
            .all()
        )
        if not all_chunks:
            # Defensive fallback: a draft from before chunk persistence existed,
            # or whose source document somehow has no chunks. Fall back to the
            # draft's raw source text rather than erroring the whole request.
            source_text = draft.source_doc.raw_text if draft.source_doc else ""
            return source_text, []

        query_text = f"{request.content_to_verify} {request.extra_instructions or ''}"
        relevant_chunks = grounding_guard.retrieve_top_k_passages(
            query_text=query_text,
            passages=[{"passage_id": c.id, "text": c.text} for c in all_chunks],
            k=8,
        )
        source_text_for_literal_check = " ".join(c["text"] for c in relevant_chunks)
        return source_text_for_literal_check, relevant_chunks

    # Ad-hoc / backward-compatible path: chunk the pasted claimed_source
    # in-memory (no persistence) so a large pasted document doesn't hit the
    # same "whole document, once per claim" bug.
    claimed_source = request.claimed_source or ""
    ephemeral_chunks = chunk_document(claimed_source)
    passages = [{"passage_id": f"E{i}", "text": c["text"]} for i, c in enumerate(ephemeral_chunks)]
    return claimed_source, passages


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
async def refine_content_endpoint(request: RefineRequest, db: Session = Depends(get_db)):
    if not request.content_to_verify.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content to verify cannot be empty.")

    try:
        # Resolve evidence once up front: either server-side retrieval against
        # a draft's persisted chunks (draft_id set) or in-memory chunking of
        # a pasted claimed_source (ad-hoc/backward-compatible path). See
        # _resolve_source_and_passages above (Part B).
        source_text, passages = _resolve_source_and_passages(request, db)

        # 1. Always verify original content.
        original = await build_stage_result(request.content_to_verify, source_text, passages=passages)
        working_content = request.content_to_verify

        fact_fixed = None
        refined = None

        # 2. Optional narrow factual correction pass.
        if request.fix_facts:
            unentailed_claims = [c for c in original.claims if not c.entailed]
            fixed_text, changes_summary = await fact_fixer.fix(
                content=working_content,
                source_text=source_text,
                mismatches=original.entity_mismatches,
                unentailed_claims=unentailed_claims,
            )
            fact_fixed = await build_stage_result(fixed_text, source_text, changes_summary=changes_summary, passages=passages)
            working_content = fixed_text

        # 3. Optional multi-dimensional refinement — all seven dimensions applied
        # together as one transformation; unset dimensions are explicitly
        # preserved via the shared spec-formatting helper's "KEEP AS IS".
        if request.refine_content:
            refined_text, changes_summary = await content_refiner.refine(
                content=working_content,
                source_text=source_text,
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
            refined = await build_stage_result(refined_text, source_text, changes_summary=changes_summary, passages=passages)
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
