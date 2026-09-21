"""Provenance Ledger: local cryptographically linked hash-chain for artifact verifiability."""

import difflib
import hashlib
import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import DeliverableDraftModel, ProvenanceLedgerModel

# Process-wide lock around the ledger's read-latest-block -> compute-next-block
# -> insert critical section. SQLite serializes writes at the file level
# anyway, but without this lock two concurrent approvals can both read the
# same "latest block" before either commits, compute the same next_index and
# previous_hash, and one of the two would either violate the unique index on
# `index`/`current_hash` or (worse, if that constraint were ever loosened)
# silently produce a broken chain. The unique constraints on both columns are
# kept as a hard backstop; this lock is what prevents hitting that backstop
# under normal concurrent load, and the retry-on-conflict handles the rare
# case where they're hit anyway (e.g. multiple worker processes, where an
# in-process lock alone isn't enough).
_LEDGER_APPEND_LOCK = threading.Lock()
_MAX_APPEND_RETRIES = 5


class ProvenanceLedger:
    """Tamper-evident SHA-256 hash-chain ledger for published artifacts."""

    @staticmethod
    def compute_sha256(data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_unified_diff(original: str, modified: str) -> str:
        """Compute human-readable unified diff between original AI draft and approved text."""
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile="ai_draft.txt",
            tofile="approved_publication.txt",
            lineterm=""
        )
        return "".join(diff)

    def calculate_block_hash(
        self,
        index: int,
        timestamp_str: str,
        operator: str,
        model_version: str,
        source_hash: str,
        draft_hash: str,
        final_hash: str,
        diff_reference: str,
        previous_hash: str,
    ) -> str:
        """Compute SHA-256 hash of a ledger block."""
        block_string = (
            f"{index}|{timestamp_str}|{operator}|{model_version}|"
            f"{source_hash}|{draft_hash}|{final_hash}|{diff_reference}|{previous_hash}"
        )
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def append_entry(
        self,
        db: Session,
        draft: DeliverableDraftModel,
        final_content: str,
        operator: Optional[str] = None,
        model_version: Optional[str] = None,
    ) -> ProvenanceLedgerModel:
        """Append an approved deliverable to the hash-chain.

        Wrapped in a process-wide lock plus retry-on-conflict (see module
        docstring above the lock) so concurrent approvals can never produce
        duplicate `index`/`current_hash` values or a broken previous_hash
        pointer.
        """
        operator_id = operator or settings.OPERATOR_ID
        model_ver = model_version or settings.GROQ_DEFAULT_MODEL

        last_error: Optional[Exception] = None
        for attempt in range(1, _MAX_APPEND_RETRIES + 1):
            with _LEDGER_APPEND_LOCK:
                # Get latest block in chain
                latest_block = (
                    db.query(ProvenanceLedgerModel)
                    .order_by(ProvenanceLedgerModel.index.desc())
                    .first()
                )

                if latest_block:
                    next_index = latest_block.index + 1
                    previous_hash = latest_block.current_hash
                else:
                    next_index = 1
                    previous_hash = settings.LEDGER_GENESIS_HASH

                now_utc = datetime.now(timezone.utc)
                timestamp_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

                source_hash = draft.source_doc.source_hash if draft.source_doc else self.compute_sha256("")
                draft_hash = self.compute_sha256(draft.draft_content)
                final_hash = self.compute_sha256(final_content)
                diff_ref = self.generate_unified_diff(draft.draft_content, final_content)

                current_hash = self.calculate_block_hash(
                    index=next_index,
                    timestamp_str=timestamp_str,
                    operator=operator_id,
                    model_version=model_ver,
                    source_hash=source_hash,
                    draft_hash=draft_hash,
                    final_hash=final_hash,
                    diff_reference=diff_ref,
                    previous_hash=previous_hash,
                )

                ledger_entry = ProvenanceLedgerModel(
                    index=next_index,
                    timestamp=now_utc,
                    operator=operator_id,
                    model_version=model_ver,
                    source_hash=source_hash,
                    draft_hash=draft_hash,
                    final_hash=final_hash,
                    diff_reference=diff_ref,
                    previous_hash=previous_hash,
                    current_hash=current_hash,
                    draft_id=draft.id,
                )

                db.add(ledger_entry)

                try:
                    # Update draft status
                    draft.approved_content = final_content
                    draft.status = "approved"
                    db.commit()
                    db.refresh(ledger_entry)
                    return ledger_entry
                except IntegrityError as e:
                    # Another process appended a block with the same index/hash
                    # between our read and our commit — back off, re-read the
                    # (now-updated) latest block, and retry.
                    db.rollback()
                    last_error = e
                    time.sleep(0.05 * attempt)
                    continue

        raise RuntimeError(
            f"Failed to append ledger entry after {_MAX_APPEND_RETRIES} attempts due to concurrent writes: {last_error}"
        )

    def verify_chain(self, db: Session) -> Dict[str, Any]:
        """Verify complete cryptographic integrity of the ledger chain."""
        blocks = (
            db.query(ProvenanceLedgerModel)
            .order_by(ProvenanceLedgerModel.index.asc())
            .all()
        )

        if not blocks:
            return {
                "is_valid": True,
                "total_blocks": 0,
                "genesis_block_hash": None,
                "latest_block_hash": None,
                "details": "Ledger is currently empty (valid initial state).",
            }

        expected_previous_hash = settings.LEDGER_GENESIS_HASH

        for block in blocks:
            # 1. Check previous hash pointer
            if block.previous_hash != expected_previous_hash:
                return {
                    "is_valid": False,
                    "total_blocks": len(blocks),
                    "failed_block_index": block.index,
                    "details": (
                        f"Chain broken at block index #{block.index}. "
                        f"Expected previous_hash {expected_previous_hash}, got {block.previous_hash}."
                    ),
                }

            # 2. Recompute current block hash
            timestamp_str = (
                block.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
                if hasattr(block.timestamp, "strftime")
                else str(block.timestamp)
            )
            recalculated = self.calculate_block_hash(
                index=block.index,
                timestamp_str=timestamp_str,
                operator=block.operator,
                model_version=block.model_version,
                source_hash=block.source_hash,
                draft_hash=block.draft_hash,
                final_hash=block.final_hash,
                diff_reference=block.diff_reference,
                previous_hash=block.previous_hash,
            )

            if recalculated != block.current_hash:
                return {
                    "is_valid": False,
                    "total_blocks": len(blocks),
                    "failed_block_index": block.index,
                    "details": (
                        f"Data tampering detected at block #{block.index}. "
                        f"Stored hash: {block.current_hash}, Recalculated hash: {recalculated}."
                    ),
                }

            expected_previous_hash = block.current_hash

        return {
            "is_valid": True,
            "total_blocks": len(blocks),
            "genesis_block_hash": blocks[0].current_hash,
            "latest_block_hash": blocks[-1].current_hash,
            "details": f"All {len(blocks)} blocks successfully validated with zero tampering detected.",
        }


ledger_service = ProvenanceLedger()
