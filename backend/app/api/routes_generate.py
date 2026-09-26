"""Routes for Transformation Mode: multi-select deliverable generation and fan-out."""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas import (
    AudienceType,
    CommunicationObjective,
    ContentStyle,
    DeliverableType,
    DetailFocus,
    GenerateRequest,
    GenerateResponse,
    LanguageType,
    LengthType,
    ToneType,
)
from app.core.llm_client import LLMUnavailableError
from app.services.ingestion import UploadTooLargeError
from app.services.orchestrator import orchestrator

router = APIRouter()


def _handle_pipeline_error(e: Exception):
    if isinstance(e, UploadTooLargeError):
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
    if isinstance(e, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if isinstance(e, LLMUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "LLM_UNAVAILABLE", "detail": str(e), "stage": getattr(e, "stage", "generation")},
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Transformation pipeline error: {str(e)}",
    )


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Multi-Format Transformation Fan-Out",
    description=(
        "Primary Transformation Mode: Ingests source document, executes Sensitivity Firewall, "
        "builds canonical Fact Graph once, fans out to selected deliverable adapters in parallel, "
        "and runs Grounding Guard verification."
    ),
)
async def generate_deliverables(
    request: GenerateRequest,
    db: Session = Depends(get_db),
):
    if not request.source_text or not request.source_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source text cannot be empty.",
        )
    if not request.deliverable_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one deliverable type must be selected.",
        )

    try:
        response = await orchestrator.execute_transformation(
            db=db,
            request=request,
            file_bytes=None,
            filename="input_text.txt",
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        _handle_pipeline_error(e)


@router.post(
    "/generate/upload",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload Document(s) and Fan-Out Deliverables",
    description=(
        "Ingests one or more files (PDF, DOCX, TXT/MD, image, audio, or video) and executes "
        "multi-format deliverable transformation. Multiple files are concatenated into a single "
        "coherent source document (with `--- SOURCE: {filename} ---` separators) so one Fact "
        "Graph is built across all of them."
    ),
)
async def generate_deliverables_upload(
    files: List[UploadFile] = File(..., description="One or more source files."),
    deliverable_types: str = Form(..., description="JSON array of deliverable types e.g. ['executive_summary', 'linkedin_post']"),
    additional_instructions: Optional[str] = Form(""),
    audience: Optional[str] = Form("Auto"),
    tone: Optional[str] = Form("Auto"),
    language: Optional[str] = Form("Auto"),
    length: Optional[str] = Form("Standard"),
    detail_focus: Optional[str] = Form("['Key Facts']"),
    communication_objective: Optional[str] = Form("Auto"),
    content_style: Optional[str] = Form("Auto"),
    db: Session = Depends(get_db),
):
    try:
        parsed_types = [DeliverableType(t) for t in json.loads(deliverable_types)]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deliverable_types format. Must be a JSON list of valid deliverable names.",
        )

    try:
        parsed_focus = [DetailFocus(f) for f in json.loads(detail_focus)]
    except Exception:
        parsed_focus = [DetailFocus.KEY_FACTS]

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one file must be uploaded.")

    primary_file = files[0]
    primary_bytes = await primary_file.read()
    additional_files = []
    for extra in files[1:]:
        extra_bytes = await extra.read()
        additional_files.append((extra_bytes, extra.filename or "additional_source"))

    request = GenerateRequest(
        source_text=None,
        deliverable_types=parsed_types,
        additional_instructions=additional_instructions,
        audience=AudienceType(audience) if audience in AudienceType._value2member_map_ else AudienceType.AUTO,
        tone=ToneType(tone) if tone in ToneType._value2member_map_ else ToneType.AUTO,
        language=LanguageType(language) if language in LanguageType._value2member_map_ else LanguageType.AUTO,
        length=LengthType(length) if length in LengthType._value2member_map_ else LengthType.STANDARD,
        detail_focus=parsed_focus,
        communication_objective=(
            CommunicationObjective(communication_objective)
            if communication_objective in CommunicationObjective._value2member_map_
            else CommunicationObjective.AUTO
        ),
        content_style=(
            ContentStyle(content_style) if content_style in ContentStyle._value2member_map_ else ContentStyle.AUTO
        ),
    )

    try:
        response = await orchestrator.execute_transformation(
            db=db,
            request=request,
            file_bytes=primary_bytes,
            filename=primary_file.filename or "uploaded_document",
            additional_files=additional_files or None,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        _handle_pipeline_error(e)
