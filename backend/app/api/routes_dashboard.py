"""Routes for Operator Dashboard: review drafts, evidence view, edit, and approve."""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import (
    DeliverableDraftModel,
    DisclosureItemModel,
    GroundingReportModel,
    OperatorModel,
    SecurityActionModel,
    SourceDocumentModel,
)
from app.db.schemas import (
    ApproveDraftRequest,
    AudienceType,
    ClaimGroundingResult,
    DraftOutput,
    EntityMismatch,
    LanguageType,
    LedgerEntryResponse,
    SecurityActionItem,
    TrustScoreBreakdown,
)
from app.services.auth import ROLE_APPROVER, get_current_operator, require_role
from app.services.ledger import ledger_service
from app.services.sensitivity_firewall import firewall

router = APIRouter()


@router.get(
    "/dashboard/drafts",
    summary="List All Generated Deliverables",
    description="Retrieve list of all deliverable drafts, their current status, and Trust Scores.",
)
def list_drafts(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    drafts = (
        db.query(DeliverableDraftModel)
        .order_by(DeliverableDraftModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for d in drafts:
        source_doc = db.query(SourceDocumentModel).filter(SourceDocumentModel.id == d.source_id).first()
        results.append({
            "id": d.id,
            "source_id": d.source_id,
            "batch_id": d.batch_id,
            "deliverable_type": d.deliverable_type,
            "status": d.status,
            "grounding_score": d.grounding_score,
            "consistency_score": d.consistency_score,
            "policy_score": d.policy_score,
            "composite_trust_score": d.composite_trust_score,
            "has_structured_content": bool(d.structured_json),
            "llm_classification_degraded": bool(source_doc.llm_classification_degraded) if source_doc else False,
            "snippet": d.draft_content[:150] + "...",
            "created_at": d.created_at,
        })
    return results


@router.get(
    "/dashboard/draft/{draft_id}",
    response_model=DraftOutput,
    summary="Get Detailed Deliverable with Evidence View",
    description="Fetches draft text, claim-level evidence citations, security action logs, and structured content (for Presentation/Infographic/Video Package).",
)
def get_draft_details(
    draft_id: str,
    db: Session = Depends(get_db),
):
    draft = db.query(DeliverableDraftModel).filter(DeliverableDraftModel.id == draft_id).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft with ID {draft_id} not found.",
        )

    # Fetch grounding report
    report = (
        db.query(GroundingReportModel)
        .filter(GroundingReportModel.draft_id == draft_id)
        .first()
    )

    claims_data = []
    if report and report.claims_json:
        try:
            raw_claims = json.loads(report.claims_json)
            claims_data = [ClaimGroundingResult(**c) for c in raw_claims]
        except Exception:
            pass

    policy_violations_data: List[str] = []
    if report and report.policy_violations_json:
        try:
            policy_violations_data = json.loads(report.policy_violations_json)
        except Exception:
            pass

    # Fetch security actions for source
    sec_actions = (
        db.query(SecurityActionModel)
        .filter(SecurityActionModel.source_id == draft.source_id)
        .all()
    )
    security_items = [
        SecurityActionItem(
            id=s.id,
            placeholder=s.placeholder,
            category=s.category,
            original_value=s.original_value,
            confidence=s.confidence if hasattr(s, "confidence") and s.confidence is not None else 1.0,
            reasoning=s.reasoning if hasattr(s, "reasoning") else None,
            audience_level=s.audience_level,
            is_overridden=s.is_overridden,
            created_at=s.created_at,
        )
        for s in sec_actions
    ]

    trust_score = TrustScoreBreakdown(
        grounding_score=draft.grounding_score,
        consistency_score=draft.consistency_score,
        policy_score=draft.policy_score,
        composite_trust_score=draft.composite_trust_score,
        formula_explanation="Composite trust score derived from verified grounding, sibling consistency, and policy adherence.",
    )

    structured_content = None
    if draft.structured_json:
        try:
            structured_content = json.loads(draft.structured_json)
        except Exception:
            structured_content = None

    source_doc = db.query(SourceDocumentModel).filter(SourceDocumentModel.id == draft.source_id).first()

    return DraftOutput(
        id=draft.id,
        deliverable_type=draft.deliverable_type,
        status=draft.status,
        draft_content=draft.draft_content,
        structured_content=structured_content,
        approved_content=draft.approved_content,
        trust_score=trust_score,
        claims=claims_data,
        security_actions=security_items,
        policy_violations=policy_violations_data,
        llm_classification_degraded=bool(source_doc.llm_classification_degraded) if source_doc else False,
        created_at=draft.created_at,
    )


@router.get(
    "/dashboard/draft/{draft_id}/export/json",
    summary="Export Structured Content Package (Presentation / Infographic / Video Package)",
    description=(
        "Returns the raw structured content package for content-only deliverable types. "
        "Returns 415 if this draft's deliverable_type has no structured package (i.e. it is "
        "a plain-text deliverable) — use /dashboard/draft/{draft_id}/export for those."
    ),
)
def export_structured_json(
    draft_id: str,
    db: Session = Depends(get_db),
    current_operator: OperatorModel = Depends(require_role(ROLE_APPROVER)),
):
    draft = db.query(DeliverableDraftModel).filter(DeliverableDraftModel.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Draft with ID {draft_id} not found.")
    if not draft.structured_json:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Draft {draft_id} (type '{draft.deliverable_type}') has no structured content package.",
        )
    return {
        "draft_id": draft.id,
        "deliverable_type": draft.deliverable_type,
        "structured_content": json.loads(draft.structured_json),
    }


def _assert_disclosure_reviewed(draft_id: str, db: Session):
    """Approval/export gate: blocks only on undecided disclosure items. Satisfied
    by any combination of individual decisions, group batch-decides, or the
    bulk 'accept all recommendations' endpoint — never by an implicit read of
    suggested_default. Combination/mosaic-risk (aggregation) checking is not a
    PS requirement and is intentionally NOT part of this gate (see Phase 2
    correction — aggregation_check.py is left in the repo, disconnected)."""
    pending_items = db.query(DisclosureItemModel).filter(
        DisclosureItemModel.draft_id == draft_id,
        DisclosureItemModel.analyst_choice.is_(None),
    ).all()
    if pending_items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f"{len(pending_items)} disclosure item(s) require a decision before approval.",
                "pending_item_ids": [i.id for i in pending_items],
                "pending_categories": list({i.category for i in pending_items}),
            },
        )


@router.post(
    "/dashboard/approve",
    response_model=LedgerEntryResponse,
    summary="Approve & Commit Deliverable to Provenance Ledger",
    description=(
        "Human review step: Operator approves the deliverable (optionally with manual edits). "
        "Approval triggers the write to the tamper-evident Provenance Ledger. Blocked only by "
        "undecided disclosure items — resolvable in one click via 'accept all recommendations'. "
        "Requires the 'approver' role — the identity recorded in the ledger is always the "
        "authenticated operator, never a client-supplied value."
    ),
)
async def approve_deliverable(
    request: ApproveDraftRequest,
    db: Session = Depends(get_db),
    current_operator: OperatorModel = Depends(require_role(ROLE_APPROVER)),
):
    _assert_disclosure_reviewed(request.draft_id, db)

    draft = db.query(DeliverableDraftModel).filter(DeliverableDraftModel.id == request.draft_id).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft with ID {request.draft_id} not found.",
        )

    # Use operator's edited text if provided, else original draft text
    base_text = request.final_content if request.final_content is not None else draft.draft_content

    # Resolve disclosure decisions (deterministic literal-substring substitution;
    # no LLM rewrite pass — see Phase 2 correction). If no disclosure items exist
    # for this draft at all, there is nothing sensitive to resolve — publish as-is.
    disclosure_items = (
        db.query(DisclosureItemModel)
        .filter(DisclosureItemModel.draft_id == draft.id)
        .all()
    )
    if disclosure_items:
        final_text = firewall.resolve_with_disclosure_decisions(
            content=base_text,
            disclosure_items=disclosure_items,
        )
    else:
        final_text = base_text

    # Item 2 fix: operator identity of record on the ledger is ALWAYS the
    # authenticated session's username — never anything from the request body.
    # (ApproveDraftRequest no longer even has an `operator` field to ignore.)
    ledger_entry = ledger_service.append_entry(
        db=db,
        draft=draft,
        final_content=final_text,
        operator=current_operator.username,
    )

    return LedgerEntryResponse(
        id=ledger_entry.id,
        index=ledger_entry.index,
        timestamp=ledger_entry.timestamp,
        operator=ledger_entry.operator,
        model_version=ledger_entry.model_version,
        source_hash=ledger_entry.source_hash,
        draft_hash=ledger_entry.draft_hash,
        final_hash=ledger_entry.final_hash,
        diff_reference=ledger_entry.diff_reference,
        previous_hash=ledger_entry.previous_hash,
        current_hash=ledger_entry.current_hash,
        draft_id=ledger_entry.draft_id,
    )


@router.get(
    "/dashboard/draft/{draft_id}/export",
    summary="Export Deliverable Content",
    description=(
        "Exports deliverable text with disclosure decisions resolved (deterministic substitution, "
        "no LLM rewrite). Requires the 'approver' role, same as approval."
    ),
)
async def export_deliverable(
    draft_id: str,
    db: Session = Depends(get_db),
    current_operator: OperatorModel = Depends(require_role(ROLE_APPROVER)),
):
    _assert_disclosure_reviewed(draft_id, db)

    draft = db.query(DeliverableDraftModel).filter(DeliverableDraftModel.id == draft_id).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft with ID {draft_id} not found.",
        )

    content_to_export = draft.approved_content or draft.draft_content

    audience = AudienceType.GENERAL_PUBLIC
    if draft.spec_json:
        try:
            spec_data = json.loads(draft.spec_json)
            aud_str = spec_data.get("audience", "General Public")
            audience = AudienceType(aud_str) if aud_str in AudienceType._value2member_map_ else AudienceType.GENERAL_PUBLIC
        except Exception:
            pass

    disclosure_items = (
        db.query(DisclosureItemModel)
        .filter(DisclosureItemModel.draft_id == draft.id)
        .all()
    )
    if disclosure_items:
        exported_content = firewall.resolve_with_disclosure_decisions(
            content=content_to_export,
            disclosure_items=disclosure_items,
        )
        is_resolved = any(i.analyst_choice == "disclose" for i in disclosure_items)
    else:
        exported_content = content_to_export
        is_resolved = True

    return {
        "draft_id": draft.id,
        "deliverable_type": draft.deliverable_type,
        "audience": audience.value if hasattr(audience, "value") else str(audience),
        "status": draft.status,
        "content": exported_content,
        "is_placeholders_resolved": is_resolved,
    }


@router.post(
    "/dashboard/security-action/{action_id}/override",
    summary="Override Security Action (False Positive)",
    description="Allows operator to override a redaction false positive.",
)
def override_security_action(
    action_id: str,
    db: Session = Depends(get_db),
):
    action = db.query(SecurityActionModel).filter(SecurityActionModel.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security action item not found.",
        )
    action.is_overridden = True
    db.commit()
    return {"status": "success", "action_id": action_id, "is_overridden": True}
