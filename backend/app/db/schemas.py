"""Pydantic schemas for request/response models and internal domain types."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class DeliverableType(str, Enum):
    # PS-named (priority) — content-only structured deliverables (no binary file rendering)
    PRESENTATION = "presentation"
    INFOGRAPHIC = "infographic"
    VIDEO_PACKAGE = "video_package"
    LINKEDIN_POST = "linkedin_post"
    TWITTER_THREAD = "twitter_thread"
    ADVISORY = "advisory"
    EXECUTIVE_SUMMARY = "executive_summary"
    # Already built — kept, no further investment
    PRESS_RELEASE = "press_release"
    PUBLIC_FAQ = "public_faq"
    BRIEFING_NOTE = "briefing_note"
    SITREP = "sitrep"
    INCIDENT_REPORT = "incident_report"
    # Free-form
    CUSTOM = "custom"


# The PS-named deliverables that should be presented first/prominently in any
# frontend grouping; the rest are "More formats".
PS_PRIORITY_DELIVERABLE_TYPES: List[str] = [
    DeliverableType.PRESENTATION.value,
    DeliverableType.INFOGRAPHIC.value,
    DeliverableType.VIDEO_PACKAGE.value,
    DeliverableType.LINKEDIN_POST.value,
    DeliverableType.TWITTER_THREAD.value,
    DeliverableType.ADVISORY.value,
    DeliverableType.EXECUTIVE_SUMMARY.value,
]


class CommunicationObjective(str, Enum):
    AUTO = "Auto"
    INFORM = "Inform"
    REASSURE = "Reassure"
    WARN = "Warn"
    PERSUADE = "Persuade"
    INSTRUCT = "Instruct"
    ANNOUNCE = "Announce"


class ContentStyle(str, Enum):
    AUTO = "Auto"
    NARRATIVE = "Narrative"
    BULLETED = "Bulleted"
    QA = "Q&A"
    DATA_LED = "Data-led"
    STORYTELLING = "Storytelling"


class AudienceType(str, Enum):
    AUTO = "Auto"
    GENERAL_PUBLIC = "General Public"
    GOVERNMENT_OFFICIALS = "Government Officials"
    SENIOR_LEADERSHIP = "Senior Leadership"
    TECHNICAL_TEAM = "Technical Team"
    INTERNAL_RESTRICTED = "Internal/Restricted"


class ToneType(str, Enum):
    AUTO = "Auto"
    FORMAL = "Formal"
    REASSURING = "Reassuring"
    NEUTRAL = "Neutral"
    URGENT = "Urgent"
    TECHNICAL = "Technical"


class LanguageType(str, Enum):
    AUTO = "Auto"
    ENGLISH = "English"
    HINDI = "Hindi"


class LengthType(str, Enum):
    BRIEF = "Brief"
    STANDARD = "Standard"
    DETAILED = "Detailed"


class DetailFocus(str, Enum):
    KEY_FACTS = "Key Facts"
    TIMELINE = "Timeline"
    IMPACT = "Impact"
    RESPONSE_ACTIONS = "Response Actions"
    RISKS = "Risks"
    RECOMMENDATIONS = "Recommendations"


# ---------------------------------------------------------
# Fact / Entity Graph Schemas (Canonical Source of Truth)
# ---------------------------------------------------------

class FactEntity(BaseModel):
    name: str
    category: str  # ORG, PERSON, LOCATION, UNIT, ASSET, etc.
    description: Optional[str] = None
    native_forms: Dict[str, str] = Field(default_factory=dict)  # e.g. {"hi": "कानपुर"}
    # Populated only when this entity was extracted from a chunked source
    # (see app/services/fact_graph.py's federated extraction). A dedup-merged
    # entity found in multiple chunks carries every contributing chunk id.
    # Optional and defaults empty so nothing that constructs a FactEntity
    # without chunk context needs to change.
    source_chunk_ids: List[str] = Field(default_factory=list)


class FactStatement(BaseModel):
    statement: str
    confidence: float = 1.0
    category: str = "KEY_FACT"
    # Same as FactEntity.source_chunk_ids: which chunk this fact was
    # extracted from, when extraction was chunked. Optional, defaults None.
    source_chunk_id: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class FactNumberDate(BaseModel):
    value: str
    unit: Optional[str] = None
    context: str


class FactGraph(BaseModel):
    source_title: str
    summary: str
    entities: List[FactEntity] = []
    facts: List[FactStatement] = []
    numbers_and_dates: List[FactNumberDate] = []
    policy_constraints: List[str] = []


# ---------------------------------------------------------
# Structured Content-Package Schemas (Presentation / Infographic / Video)
#
# Per product decision: these three PS-named deliverables are CONTENT ONLY.
# No .pptx / .svg / .png / .mp4 file is rendered — the adapter's job is to
# produce the structured text content (slides + speaker notes, infographic
# sections + layout guidance, video script + storyboard + subtitles) as
# structured, reviewable, groundable data. A human or a downstream tool can
# turn this content into an actual file later; SriGEN's job stops at content.
# ---------------------------------------------------------

class Slide(BaseModel):
    slide_number: int
    layout: Literal["title", "bullets", "two_column", "stat", "closing"]
    title: str
    bullets: List[str] = []
    speaker_notes: str = ""
    visual_suggestion: Optional[str] = None


class PresentationPackage(BaseModel):
    title: str
    subtitle: Optional[str] = None
    slides: List[Slide]


class InfographicSection(BaseModel):
    heading: str
    stat_value: Optional[str] = None      # "7", "cr 3.4", "11 min"
    stat_label: Optional[str] = None
    body: str
    icon_hint: Optional[str] = None       # "shield", "clock", "alert"


class InfographicPackage(BaseModel):
    title: str
    key_message: str
    sections: List[InfographicSection]
    layout_recommendation: str            # PS names this explicitly
    color_palette: List[str] = []         # hex values
    footer: Optional[str] = None


class VideoScene(BaseModel):
    scene_number: int
    start_seconds: float
    end_seconds: float
    visual_description: str               # storyboard frame description
    on_screen_text: Optional[str] = None
    narration: str
    b_roll_suggestion: Optional[str] = None


class SubtitleCue(BaseModel):
    index: int
    start_seconds: float
    end_seconds: float
    text: str


class VideoPackage(BaseModel):
    title: str
    total_duration_seconds: float
    narration_script: str                 # full continuous script
    scenes: List[VideoScene]              # storyboard + scene descriptions
    subtitles: List[SubtitleCue]
    visual_recommendations: List[str]


# ---------------------------------------------------------
# Deliverable Spec (Resolved from Operator Form)
# ---------------------------------------------------------

class DeliverableSpec(BaseModel):
    deliverable_type: DeliverableType
    audience: AudienceType
    tone: ToneType
    language: LanguageType
    length: LengthType
    detail_focus: List[DetailFocus]
    communication_objective: CommunicationObjective = CommunicationObjective.AUTO
    content_style: ContentStyle = ContentStyle.AUTO
    presentation_instructions: str = ""


# ---------------------------------------------------------
# Grounding Guard & Verification Models
# ---------------------------------------------------------

class EntityMismatch(BaseModel):
    found_in_claim: str
    matched_in_source: Optional[str] = None
    mismatch_type: str  # "LOCATION", "NUMBER", "DATE", "ENTITY"
    description: str


class ClaimGroundingResult(BaseModel):
    claim_text: str
    entailed: bool
    confidence: float
    reasoning: str
    matched_source_passage: Optional[str] = None
    entity_mismatches: List[EntityMismatch] = []


class ClaimEntailmentJudgement(BaseModel):
    entailed: bool
    confidence: float = 0.95
    reasoning: str
    contradiction_details: Optional[str] = None


class ConsistencyJudgement(BaseModel):
    is_consistent: bool = True
    contradictions: List[str] = []
    total_facts_checked: int = 1
    confidence: float = 0.95
    explanation: Optional[str] = None


class PolicyComplianceJudgement(BaseModel):
    total_flagged: int = 0
    unresolved_violations: int = 0
    violation_details: List[str] = []
    reasoning: Optional[str] = None


class TrustScoreBreakdown(BaseModel):
    grounding_score: float = Field(..., description="entailed claims / total claims (0-100)")
    consistency_score: float = Field(..., description="cross-output agreement (0-100)")
    policy_score: float = Field(..., description="policy and constraint compliance (0-100)")
    composite_trust_score: float = Field(..., description="Weighted composite trust index (0-100)")
    formula_explanation: str


# ---------------------------------------------------------
# Security Actions Log & Sensitivity Classification Schemas
# ---------------------------------------------------------

class SensitiveSpanCandidate(BaseModel):
    """A single sensitive span identified by the LLM classification pass.

    Two separate judgments, not one overloaded number:
    - detection_confidence: how sure the model is this span really IS an
      instance of `category` at all.
    - sensitivity_tier: a direct judgment of actual disclosure risk,
      decided from context. NEVER derived from detection_confidence —
      a routine mention of a real person's name can be detected with
      100% confidence and still be "routine" risk; the two questions
      are independent.
    For CLASSIFIED_ASSET / IP_ADDRESS, category alone already implies
    "restricted" risk regardless of context — see
    `_RESTRICTED_CATEGORIES` in `orchestrator.py` — so `sensitivity_tier`
    on those is informational only and never overrides that.
    """
    exact_text: str = Field(..., description="The exact substring from the source text, verbatim, that should be redacted.")
    category: str = Field(..., description="One of: LOCATION, UNIT_NAME, CLASSIFIED_ASSET, PERSON, IP_ADDRESS, OTHER_SENSITIVE")
    detection_confidence: float = Field(..., ge=0.0, le=1.0, description="How sure the model is this span really is an instance of `category`.")
    sensitivity_tier: Literal["routine", "contextual", "sensitive"] = Field(
        ..., description="Direct judgment of real disclosure risk: 'routine' (an ordinary, "
                          "already-appropriate mention), 'contextual' (tied to an operational "
                          "role/asset/capability but not independently dangerous alone), or "
                          "'sensitive' (meaningfully helps an adversary or violates privacy on its own)."
    )
    reasoning: str = Field(..., description="Why this sensitivity_tier was chosen, in context — not just why it was flagged.")


class SensitivityClassificationResult(BaseModel):
    """Full output of the LLM classification pass over a document."""
    sensitive_spans: List[SensitiveSpanCandidate] = []


class SecurityActionItem(BaseModel):
    id: str
    placeholder: str
    category: str
    original_value: str
    confidence: float = 1.0
    sensitivity_tier: Optional[Literal["routine", "contextual", "sensitive"]] = None
    reasoning: Optional[str] = None
    audience_level: str
    is_overridden: bool = False
    created_at: Optional[datetime] = None


# ---------------------------------------------------------
# API Request & Response Models
# ---------------------------------------------------------

class GenerateRequest(BaseModel):
    source_text: Optional[str] = None
    deliverable_types: List[DeliverableType]
    additional_instructions: Optional[str] = ""
    audience: Optional[AudienceType] = AudienceType.AUTO
    tone: Optional[ToneType] = ToneType.AUTO
    language: Optional[LanguageType] = LanguageType.AUTO
    length: Optional[LengthType] = LengthType.STANDARD
    detail_focus: Optional[List[DetailFocus]] = [DetailFocus.KEY_FACTS]
    communication_objective: Optional[CommunicationObjective] = CommunicationObjective.AUTO
    content_style: Optional[ContentStyle] = ContentStyle.AUTO


class DraftOutput(BaseModel):
    id: str
    deliverable_type: DeliverableType
    status: str
    draft_content: str
    structured_content: Optional[Dict[str, Any]] = None  # populated for presentation/infographic/video_package
    approved_content: Optional[str] = None
    trust_score: TrustScoreBreakdown
    claims: List[ClaimGroundingResult] = []
    security_actions: List[SecurityActionItem] = []
    policy_violations: List[str] = []  # from PolicyComplianceJudgement.violation_details; [] if no constraints or none flagged
    llm_classification_degraded: bool = False
    created_at: datetime


class GenerateResponse(BaseModel):
    source_id: str
    source_hash: str
    batch_id: str
    fact_graph: FactGraph
    drafts: List[DraftOutput]
    security_actions: List[SecurityActionItem]
    content_provenance_note: Optional[str] = None  # set when source is a machine transcription (image/audio/video)
    llm_classification_degraded: bool = False  # True if sensitivity detection fell back to regex-only for this source
    detected_source_language: Optional[str] = None  # "English" | "Hindi" — what `language: Auto` resolved against
    source_context_truncated: bool = False  # True if raw source exceeded settings.MAX_GENERATION_CONTEXT_CHARS


class SensitivityScanResponse(BaseModel):
    findings: List[SecurityActionItem] = []
    source_hash: str
    llm_classification_degraded: bool = False


class VerifyRequest(BaseModel):
    """Standalone Verification Mode entry point."""
    content_to_verify: str
    claimed_source: str
    deliverable_type_hint: Optional[str] = "advisory"


class VerifyResponse(BaseModel):
    """Read-only Verification Report. Never writes to provenance ledger."""
    trust_score: TrustScoreBreakdown
    claims: List[ClaimGroundingResult]
    entity_mismatches: List[EntityMismatch]
    overall_verdict: str
    is_corrupted_detected: bool


# ---------------------------------------------------------
# Refine (multi-dimensional content refinement)
#
# Verification is always run. Factual correction and content refinement are
# each independently optional. Refinement treats all seven Deliverable Spec
# dimensions (Audience, Tone, Language, Length, Content Style, Communication
# Objective, Detail Focus) as equal peers — tone is not the primary axis.
# `None` on any dimension means "keep it as it currently is", never "Auto"
# and never "the model may decide".
# ---------------------------------------------------------

class RefineRequest(BaseModel):
    content_to_verify: str
    # Now optional: when `draft_id` is set, the claimed source's evidence is
    # retrieved server-side from the persisted DocumentChunkModel rows for
    # that draft's source document (RAG), so the client never needs to hold
    # and resend the full source text on every refine iteration. Exactly one
    # of `draft_id` / `claimed_source` must be set — see the validator below.
    claimed_source: Optional[str] = None
    draft_id: Optional[str] = None

    deliverable_type_hint: Optional[str] = "advisory"

    # Pipeline controls
    fix_facts: bool = False
    refine_content: bool = False

    # Deliverable specification — None means "keep this dimension as it
    # currently is"; an explicit value means "actively transform toward it".
    audience: Optional[AudienceType] = None
    tone: Optional[ToneType] = None
    language: Optional[LanguageType] = None
    length: Optional[LengthType] = None
    content_style: Optional[ContentStyle] = None
    communication_objective: Optional[CommunicationObjective] = None
    detail_focus: Optional[List[DetailFocus]] = None

    # Additional natural-language guidance layered on top of the structured
    # spec; may shape wording/emphasis/presentation but never overrides
    # factual grounding.
    extra_instructions: Optional[str] = ""

    @model_validator(mode="after")
    def _validate_source_reference(self) -> "RefineRequest":
        has_draft = bool(self.draft_id and self.draft_id.strip())
        has_claimed = bool(self.claimed_source and self.claimed_source.strip())
        if not has_draft and not has_claimed:
            raise ValueError("Exactly one of 'draft_id' or 'claimed_source' must be set.")
        return self


class StageResult(BaseModel):
    content: str
    trust_score: TrustScoreBreakdown
    claims: List[ClaimGroundingResult]
    entity_mismatches: List[EntityMismatch]
    verdict: str
    is_corrupted_detected: bool
    changes_summary: Optional[str] = None


class RefineResponse(BaseModel):
    original: StageResult
    fact_fixed: Optional[StageResult] = None
    refined: Optional[StageResult] = None
    final_content: str


class FactFixResult(BaseModel):
    """Structured output of the narrowly-scoped factual correction pass."""
    corrected_content: str
    changes_summary: str
    unresolved_flags: List[str] = []


class ContentRefineResult(BaseModel):
    """Structured output of the multi-dimensional content refinement pass."""
    refined_content: str
    changes_summary: str


class ApproveDraftRequest(BaseModel):
    draft_id: str
    final_content: Optional[str] = None  # Operator's edited content or None to approve draft as-is
    # NOTE: no client-settable `operator` field — the identity recorded on the
    # Provenance Ledger is always the authenticated session's operator
    # (see app/services/auth.py::get_current_operator), never request-body data.


class LedgerEntryResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    index: int
    timestamp: datetime
    operator: str
    model_version: str
    source_hash: str
    draft_hash: str
    final_hash: str
    diff_reference: str
    previous_hash: str
    current_hash: str
    draft_id: str


class LedgerVerificationResponse(BaseModel):
    is_valid: bool
    total_blocks: int
    genesis_block_hash: Optional[str] = None
    latest_block_hash: Optional[str] = None
    details: str


# ---------------------------------------------------------
# Disclosure Control Schemas
# ---------------------------------------------------------

class DisclosureItem(BaseModel):
    id: str
    draft_id: str
    placeholder: str
    category: str
    detected_value_preview: Optional[str] = None
    confidence: float = 1.0
    sensitivity_tier: Optional[Literal["routine", "contextual", "sensitive"]] = None
    reasoning: Optional[str] = None
    suggested_default: str  # "disclose" | "withhold"
    analyst_choice: Optional[str] = None  # "disclose" | "withhold" | "edit"
    manual_edit_text: Optional[str] = None
    decision_source: Optional[str] = None  # "individual" | "batch" | "bulk_accept_all"
    group_key: str
    detected_at: str = "output"  # "output" | "both" — where this finding was detected
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime


class DisclosureItemDecisionRequest(BaseModel):
    choice: Literal["disclose", "withhold", "edit"]
    manual_edit_text: Optional[str] = None
    decided_by: Optional[str] = "analyst"

    @model_validator(mode="after")
    def validate_edit_text(self):
        if self.choice == "edit":
            if not self.manual_edit_text or not self.manual_edit_text.strip():
                raise ValueError("manual_edit_text is required and cannot be empty when choice is 'edit'")
        return self


class DisclosureGroupDecisionRequest(BaseModel):
    choice: Literal["disclose", "withhold"]
    decided_by: Optional[str] = "analyst"


class DisclosureBulkAcceptRequest(BaseModel):
    """Stamps every currently-undecided item on a draft with its own suggested_default.
    One explicit, logged human action — never an implicit fallback used by approval itself."""
    decided_by: Optional[str] = "analyst"


class AggregationFinding(BaseModel):
    id: str
    draft_id: str
    description: str
    severity: str = "medium"
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime


class AggregationAcknowledgeRequest(BaseModel):
    acknowledged_by: Optional[str] = "analyst"


class DisclosureGroupSummary(BaseModel):
    group_key: str
    label: str
    total: int
    decided: int
    pending: int
    items: List[DisclosureItem]


class DisclosureReviewResponse(BaseModel):
    draft_id: str
    groups: List[DisclosureGroupSummary]
    aggregation_findings: List[AggregationFinding] = []
    total_items: int = 0
    suggested_disclose_count: int = 0
    suggested_withhold_count: int = 0
    pending_count: int = 0
