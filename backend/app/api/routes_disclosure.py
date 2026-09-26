"""Routes for Disclosure Control: grouped/individual review and one-click bulk accept.

Phase 2 correction: aggregation (combination/mosaic-risk) checking is NOT part
of the active request path or the approval gate — it was never a PS
requirement and only added a blocking dependency. `app/services/aggregation_check.py`
is left in the repo, untouched, for a possible future iteration, but nothing
here calls it.
"""

import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DeliverableDraftModel, DisclosureItemModel
from app.db.schemas import (
    DisclosureBulkAcceptRequest,
    DisclosureGroupDecisionRequest,
    DisclosureGroupSummary,
    DisclosureItem,
    DisclosureItemDecisionRequest,
    DisclosureReviewResponse,
)

logger = logging.getLogger("srigen.disclosure_routes")

router = APIRouter()

GROUP_LABELS = {
    "PERSON": "Personal names",
    "LOCATION": "Locations",
    "UNIT_NAME": "Unit names",
    "CLASSIFIED_ASSET": "Classified assets",
    "IP_ADDRESS": "IP addresses",
    "OTHER_SENSITIVE": "Sensitive operational details",
}


def _get_draft_or_404(draft_id: str, db: Session) -> DeliverableDraftModel:
    draft = db.query(DeliverableDraftModel).filter(DeliverableDraftModel.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Draft with ID {draft_id} not found.")
    return draft


def _assert_not_approved(draft: DeliverableDraftModel):
    if draft.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot alter disclosure decisions on an already-approved deliverable draft.",
        )


def _to_schema(item: DisclosureItemModel) -> DisclosureItem:
    return DisclosureItem(
        id=item.id,
        draft_id=item.draft_id,
        placeholder=item.placeholder,
        category=item.category,
        detected_value_preview=item.detected_value_preview,
        confidence=item.confidence or 1.0,
        sensitivity_tier=item.sensitivity_tier,
        reasoning=item.reasoning,
        suggested_default=item.suggested_default,
        analyst_choice=item.analyst_choice,
        manual_edit_text=item.manual_edit_text,
        decision_source=item.decision_source,
        group_key=item.group_key,
        detected_at=item.detected_at or "output",
        decided_by=item.decided_by,
        decided_at=item.decided_at,
        created_at=item.created_at,
    )


@router.post(
    "/disclosure/draft/{draft_id}/group/{group_key}/decide",
    summary="Batch Decision on Group of Disclosure Items",
    description="Sets analyst choice on all unreviewed items in the group. Never overwrites previously individually decided items.",
)
def decide_group(
    draft_id: str,
    group_key: str,
    request: DisclosureGroupDecisionRequest,
    db: Session = Depends(get_db),
):
    draft = _get_draft_or_404(draft_id, db)
    _assert_not_approved(draft)

    undecided_items = (
        db.query(DisclosureItemModel)
        .filter(
            DisclosureItemModel.draft_id == draft_id,
            DisclosureItemModel.group_key == group_key,
            DisclosureItemModel.analyst_choice.is_(None),
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    for item in undecided_items:
        item.analyst_choice = request.choice
        item.decision_source = "batch"
        item.decided_by = request.decided_by or "analyst"
        item.decided_at = now

    db.commit()

    return {
        "status": "success",
        "draft_id": draft_id,
        "group_key": group_key,
        "choice": request.choice,
        "affected_count": len(undecided_items),
    }


@router.post(
    "/disclosure/item/{item_id}/decide",
    response_model=DisclosureItem,
    summary="Individual Decision on Single Disclosure Item",
    description="Sets decision on a single item. Always overwrites any prior batch or individual decision.",
)
def decide_item(
    item_id: str,
    request: DisclosureItemDecisionRequest,
    db: Session = Depends(get_db),
):
    item = db.query(DisclosureItemModel).filter(DisclosureItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Disclosure item with ID {item_id} not found.")

    draft = db.query(DeliverableDraftModel).filter(DeliverableDraftModel.id == item.draft_id).first()
    if draft:
        _assert_not_approved(draft)

    if request.choice == "edit" and (not request.manual_edit_text or not request.manual_edit_text.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="manual_edit_text is required and cannot be empty when choice is 'edit'.",
        )

    now = datetime.now(timezone.utc)
    item.analyst_choice = request.choice
    item.manual_edit_text = request.manual_edit_text.strip() if request.choice == "edit" and request.manual_edit_text else None
    item.decision_source = "individual"
    item.decided_by = request.decided_by or "analyst"
    item.decided_at = now

    db.commit()
    db.refresh(item)

    return _to_schema(item)


@router.post(
    "/disclosure/draft/{draft_id}/accept-all-recommendations",
    summary="Accept All Recommendations (Bulk)",
    description=(
        "Stamps every currently-undecided disclosure item across the ENTIRE draft (all groups "
        "at once) with its own suggested_default. This is still one explicit, single, logged "
        "human action — nothing in the approval/export path ever reads suggested_default as an "
        "implicit fallback; it only ever becomes analyst_choice through this endpoint, the group "
        "batch-decide endpoint, or the individual decide endpoint."
    ),
)
def accept_all_recommendations(
    draft_id: str,
    request: DisclosureBulkAcceptRequest = DisclosureBulkAcceptRequest(),
    db: Session = Depends(get_db),
):
    draft = _get_draft_or_404(draft_id, db)
    _assert_not_approved(draft)

    undecided_items = (
        db.query(DisclosureItemModel)
        .filter(
            DisclosureItemModel.draft_id == draft_id,
            DisclosureItemModel.analyst_choice.is_(None),
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    for item in undecided_items:
        item.analyst_choice = item.suggested_default
        item.decision_source = "bulk_accept_all"
        item.decided_by = request.decided_by or "analyst"
        item.decided_at = now

    db.commit()

    return {
        "status": "success",
        "draft_id": draft_id,
        "affected_count": len(undecided_items),
        "decision_source": "bulk_accept_all",
    }


@router.get(
    "/disclosure/draft/{draft_id}/review",
    response_model=DisclosureReviewResponse,
    summary="Get Disclosure Review Panel Data",
    description="Fetches grouped disclosure items (with recommendation counts) for the operator review panel.",
)
def get_disclosure_review(
    draft_id: str,
    db: Session = Depends(get_db),
):
    draft = _get_draft_or_404(draft_id, db)

    items = (
        db.query(DisclosureItemModel)
        .filter(DisclosureItemModel.draft_id == draft_id)
        .order_by(DisclosureItemModel.created_at.asc())
        .all()
    )

    grouped: dict = {}
    for it in items:
        grouped.setdefault(it.group_key, []).append(it)

    group_summaries: List[DisclosureGroupSummary] = []
    for gk, it_list in grouped.items():
        total = len(it_list)
        decided = sum(1 for i in it_list if i.analyst_choice is not None)
        pending = total - decided
        label = GROUP_LABELS.get(gk, gk.replace("_", " ").title())
        group_summaries.append(
            DisclosureGroupSummary(
                group_key=gk,
                label=label,
                total=total,
                decided=decided,
                pending=pending,
                items=[_to_schema(i) for i in it_list],
            )
        )

    suggested_disclose = sum(1 for i in items if i.analyst_choice is None and i.suggested_default == "disclose")
    suggested_withhold = sum(1 for i in items if i.analyst_choice is None and i.suggested_default == "withhold")
    pending_count = sum(1 for i in items if i.analyst_choice is None)

    return DisclosureReviewResponse(
        draft_id=draft_id,
        groups=group_summaries,
        aggregation_findings=[],
        total_items=len(items),
        suggested_disclose_count=suggested_disclose,
        suggested_withhold_count=suggested_withhold,
        pending_count=pending_count,
    )
