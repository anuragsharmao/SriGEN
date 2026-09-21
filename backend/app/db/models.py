"""SQLAlchemy database models for SriGEN."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceDocumentModel(Base):
    """Normalized ingested source document."""
    __tablename__ = "source_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False, default="pasted_text.txt")
    file_type = Column(String(50), nullable=False, default="text")
    # Deterministic (Devanagari-density) English/Hindi detection — see
    # app/services/ingestion.py::detect_source_language. Used to resolve
    # `language: Auto` on a GenerateRequest instead of that silently always
    # defaulting to English regardless of the actual source language.
    detected_language = Column(String(20), nullable=False, default="English")
    raw_text = Column(Text, nullable=False)
    redacted_text = Column(Text, nullable=False)
    placeholder_map_json = Column(Text, nullable=False, default="{}")
    placeholder_native_map_json = Column(Text, nullable=True, default="{}")
    source_hash = Column(String(64), nullable=False, index=True)
    # Set only for image/audio/video-derived sources: flags that raw_text is a
    # machine transcription/description, not the original primary document, so
    # an operator reviewing grounding evidence knows the ground truth itself is derived.
    content_provenance_note = Column(Text, nullable=True)
    # Set when the LLM semantic sensitivity-classification pass failed for this
    # document and detection fell back to regex-only. Surfaced to operators so
    # degraded detection is visible, never silent.
    llm_classification_degraded = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utc_now)

    fact_graphs = relationship("FactGraphModel", back_populates="source_doc", cascade="all, delete-orphan")
    drafts = relationship("DeliverableDraftModel", back_populates="source_doc", cascade="all, delete-orphan")
    security_actions = relationship("SecurityActionModel", back_populates="source_doc", cascade="all, delete-orphan")


class FactGraphModel(Base):
    """Canonical single-source-of-truth Fact/Entity Graph extracted once per source."""
    __tablename__ = "fact_graphs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("source_documents.id"), nullable=False, index=True)
    graph_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    source_doc = relationship("SourceDocumentModel", back_populates="fact_graphs")


class DeliverableDraftModel(Base):
    """Generated deliverable draft per adapter."""
    __tablename__ = "deliverable_drafts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("source_documents.id"), nullable=False, index=True)
    batch_id = Column(String(36), nullable=False, index=True)
    deliverable_type = Column(String(50), nullable=False, index=True)
    spec_json = Column(Text, nullable=False)
    draft_content = Column(Text, nullable=False)
    structured_json = Column(Text, nullable=True)  # serialized structured package; null for plain-text deliverable types
    approved_content = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft")  # draft, edited, approved, rejected
    
    # Trust Score Breakdown
    grounding_score = Column(Float, nullable=False, default=100.0)
    consistency_score = Column(Float, nullable=False, default=100.0)
    policy_score = Column(Float, nullable=False, default=100.0)
    composite_trust_score = Column(Float, nullable=False, default=100.0)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    source_doc = relationship("SourceDocumentModel", back_populates="drafts")
    grounding_reports = relationship("GroundingReportModel", back_populates="draft", cascade="all, delete-orphan")
    ledger_entries = relationship("ProvenanceLedgerModel", back_populates="draft")
    disclosure_items = relationship("DisclosureItemModel", back_populates="draft", cascade="all, delete-orphan")
    aggregation_findings = relationship("AggregationFindingModel", back_populates="draft", cascade="all, delete-orphan")


class GroundingReportModel(Base):
    """Grounding Guard verification report for draft or external content."""
    __tablename__ = "grounding_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    draft_id = Column(String(36), ForeignKey("deliverable_drafts.id"), nullable=True, index=True)
    source_id = Column(String(36), nullable=True)
    is_verification_mode = Column(Boolean, default=False)
    target_content = Column(Text, nullable=False)
    claims_json = Column(Text, nullable=False)
    entity_mismatches_json = Column(Text, nullable=False)
    policy_violations_json = Column(Text, nullable=False, default="[]")

    grounding_score = Column(Float, nullable=False, default=100.0)
    consistency_score = Column(Float, nullable=False, default=100.0)
    policy_score = Column(Float, nullable=False, default=100.0)
    composite_trust_score = Column(Float, nullable=False, default=100.0)

    created_at = Column(DateTime, default=utc_now)

    draft = relationship("DeliverableDraftModel", back_populates="grounding_reports")


class SecurityActionModel(Base):
    """Transparency log for redacted terms and PII removals (never subtracted from Trust Score)."""
    __tablename__ = "security_actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("source_documents.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    placeholder = Column(String(100), nullable=False)
    original_value = Column(String(255), nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    reasoning = Column(Text, nullable=True)
    audience_level = Column(String(50), default="Public")
    is_overridden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    source_doc = relationship("SourceDocumentModel", back_populates="security_actions")


class ProvenanceLedgerModel(Base):
    """Immutable hash-chain provenance ledger, appended ONLY on human approval."""
    __tablename__ = "provenance_ledger"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    index = Column(Integer, nullable=False, unique=True, index=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    operator = Column(String(100), nullable=False)
    model_version = Column(String(100), nullable=False)
    source_hash = Column(String(64), nullable=False)
    draft_hash = Column(String(64), nullable=False)
    final_hash = Column(String(64), nullable=False)
    diff_reference = Column(Text, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    draft_id = Column(String(36), ForeignKey("deliverable_drafts.id"), nullable=False)
    draft = relationship("DeliverableDraftModel", back_populates="ledger_entries")


class DisclosureItemModel(Base):
    """Granular disclosure review record for sensitive terms / placeholders in a draft."""
    __tablename__ = "disclosure_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    draft_id = Column(String(36), ForeignKey("deliverable_drafts.id"), nullable=False, index=True)
    placeholder = Column(String(100), nullable=False)          # e.g. "[LOCATION_1]"
    category = Column(String(50), nullable=False)              # e.g. "LOCATION"
    detected_value_preview = Column(String(255), nullable=True) # what was detected, for review card
    confidence = Column(Float, default=1.0)
    reasoning = Column(Text, nullable=True)
    suggested_default = Column(String(20), nullable=False)     # "disclose" | "withhold" — UI hint only, never output fallback
    analyst_choice = Column(String(20), nullable=True)         # "disclose" | "withhold" | "edit" — NULL until reviewed
    manual_edit_text = Column(Text, nullable=True)          # populated only when analyst_choice == "edit"
    decision_source = Column(String(20), nullable=True)         # "individual" | "batch" | "bulk_accept_all"
    group_key = Column(String(50), nullable=False, index=True)              # grouping key for batch UI
    detected_at = Column(String(10), nullable=False, default="output")      # "output" | "both"
    decided_by = Column(String(100), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    draft = relationship("DeliverableDraftModel", back_populates="disclosure_items")


class AggregationFindingModel(Base):
    """Mosaic intelligence / aggregation risk findings for combinations of disclosed facts."""
    __tablename__ = "aggregation_findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    draft_id = Column(String(36), ForeignKey("deliverable_drafts.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="medium")
    acknowledged = Column(Boolean, default=False)           # must be True before approval
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    draft = relationship("DeliverableDraftModel", back_populates="aggregation_findings")


class OperatorModel(Base):
    """Authenticated operator/user account.

    Default auth model implemented per the security remediation brief's item
    1: simple credential-based auth (no external SSO/OAuth2 assumed) with two
    roles. Analysts can generate, review, and make disclosure decisions;
    approvers can additionally approve/export deliverables (the ledger-write
    path). This is a default, not a locked-in decision — swap it for SSO/OAuth2
    by replacing app/services/auth.py's implementation of get_current_operator
    without touching route wiring, since every route depends on that one
    function's return type (OperatorModel), not on how it authenticated.
    """
    __tablename__ = "operators"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(64), nullable=False)
    role = Column(String(20), nullable=False, default="analyst")  # "analyst" | "approver"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now)

    sessions = relationship("OperatorSessionModel", back_populates="operator", cascade="all, delete-orphan")


class OperatorSessionModel(Base):
    """Opaque bearer-token session. Stored server-side (not a JWT) so a
    session can be revoked immediately by deleting the row."""
    __tablename__ = "operator_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    operator_id = Column(String(36), ForeignKey("operators.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=False)

    operator = relationship("OperatorModel", back_populates="sessions")
