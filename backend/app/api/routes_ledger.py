"""Routes for Provenance Ledger: inspect chain entries and verify cryptographic integrity."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ProvenanceLedgerModel
from app.db.schemas import LedgerEntryResponse, LedgerVerificationResponse
from app.services.ledger import ledger_service

router = APIRouter()


@router.get(
    "/ledger",
    response_model=List[LedgerEntryResponse],
    summary="List Provenance Ledger Blocks",
    description="Retrieve all cryptographically linked blocks in the Provenance Ledger.",
)
def get_ledger_entries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    entries = (
        db.query(ProvenanceLedgerModel)
        .order_by(ProvenanceLedgerModel.index.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries


@router.get(
    "/ledger/verify",
    response_model=LedgerVerificationResponse,
    summary="Verify Cryptographic Hash-Chain Integrity",
    description=(
        "Traverses every block in the ledger from genesis to tip, verifying previous_hash links "
        "and recalculating SHA-256 block digests. Detects any tampering or unauthorized alterations."
    ),
)
def verify_ledger(db: Session = Depends(get_db)):
    result = ledger_service.verify_chain(db)
    return LedgerVerificationResponse(
        is_valid=result["is_valid"],
        total_blocks=result["total_blocks"],
        genesis_block_hash=result.get("genesis_block_hash"),
        latest_block_hash=result.get("latest_block_hash"),
        details=result["details"],
    )


@router.get(
    "/ledger/{block_index}",
    response_model=LedgerEntryResponse,
    summary="Get Specific Ledger Block",
    description="Inspect a single ledger block by index, including draft_hash, final_hash, and diff_reference.",
)
def get_ledger_block(
    block_index: int,
    db: Session = Depends(get_db),
):
    block = (
        db.query(ProvenanceLedgerModel)
        .filter(ProvenanceLedgerModel.index == block_index)
        .first()
    )
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ledger block with index {block_index} not found.",
        )
    return block
