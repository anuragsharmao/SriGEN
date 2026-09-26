"""Standalone source sensitivity scanning for the generation workspace."""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.db.schemas import AudienceType, SecurityActionItem, SensitivityScanResponse
from app.services.ingestion import ingest_document
from app.services.sensitivity_firewall import firewall

router = APIRouter()


@router.post(
    "/sensitivity/scan",
    response_model=SensitivityScanResponse,
    summary="Scan source material for sensitive information",
)
async def scan_source_sensitivity(
    source_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    audience: Optional[str] = Form("Auto"),
):
    if not source_text and not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source text or a file is required.")

    file_bytes = await file.read() if file else None
    document = await ingest_document(
        text=source_text,
        file_bytes=file_bytes,
        filename=file.filename if file else "input_text.txt",
    )
    _, security_actions, _, degraded = await firewall.apply_redaction(
        text=document["raw_text"],
        audience=AudienceType(audience) if audience in AudienceType._value2member_map_ else AudienceType.AUTO,
    )

    findings = [
        SecurityActionItem(
            id=item.id,
            placeholder=item.placeholder,
            category=item.category,
            original_value=item.original_value,
            confidence=item.confidence,
            sensitivity_tier=item.sensitivity_tier,
            reasoning=item.reasoning,
            audience_level=item.audience_level,
            is_overridden=item.is_overridden,
        )
        for item in security_actions
    ]
    return SensitivityScanResponse(
        findings=findings,
        source_hash=document["source_hash"],
        llm_classification_degraded=degraded,
    )