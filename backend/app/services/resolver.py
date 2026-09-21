"""Content Intelligence Resolver: resolves multi-select requests and auto-infers
tone, language, communication objective, and content style."""

from typing import List
from app.db.schemas import (
    AudienceType,
    CommunicationObjective,
    ContentStyle,
    DeliverableSpec,
    DeliverableType,
    DetailFocus,
    GenerateRequest,
    LanguageType,
    LengthType,
    ToneType,
)


class ContentIntelligenceResolver:
    """Resolves operator generation requests into strongly typed DeliverableSpecs.

    Ensures that operator free-text instructions shape only presentation parameters
    and never alter the canonical Fact Graph.
    """

    TONE_AUDIENCE_MAP = {
        AudienceType.SENIOR_LEADERSHIP: ToneType.FORMAL,
        AudienceType.GOVERNMENT_OFFICIALS: ToneType.FORMAL,
        AudienceType.GENERAL_PUBLIC: ToneType.NEUTRAL,
        AudienceType.TECHNICAL_TEAM: ToneType.TECHNICAL,
        AudienceType.INTERNAL_RESTRICTED: ToneType.FORMAL,
        AudienceType.AUTO: ToneType.NEUTRAL,
    }

    # Objective inferred from deliverable type when the operator leaves it on Auto.
    OBJECTIVE_BY_TYPE = {
        DeliverableType.ADVISORY: CommunicationObjective.WARN,
        DeliverableType.PUBLIC_FAQ: CommunicationObjective.INFORM,
        DeliverableType.LINKEDIN_POST: CommunicationObjective.ANNOUNCE,
        DeliverableType.TWITTER_THREAD: CommunicationObjective.ANNOUNCE,
        DeliverableType.EXECUTIVE_SUMMARY: CommunicationObjective.INFORM,
        DeliverableType.PRESS_RELEASE: CommunicationObjective.ANNOUNCE,
        DeliverableType.BRIEFING_NOTE: CommunicationObjective.INFORM,
        DeliverableType.SITREP: CommunicationObjective.INFORM,
        DeliverableType.INCIDENT_REPORT: CommunicationObjective.INFORM,
        DeliverableType.PRESENTATION: CommunicationObjective.INFORM,
        DeliverableType.INFOGRAPHIC: CommunicationObjective.INFORM,
        DeliverableType.VIDEO_PACKAGE: CommunicationObjective.REASSURE,
        DeliverableType.CUSTOM: CommunicationObjective.INFORM,
    }

    # Style inferred from deliverable type when the operator leaves it on Auto.
    STYLE_BY_TYPE = {
        DeliverableType.PUBLIC_FAQ: ContentStyle.QA,
        DeliverableType.INFOGRAPHIC: ContentStyle.DATA_LED,
        DeliverableType.VIDEO_PACKAGE: ContentStyle.STORYTELLING,
        DeliverableType.PRESENTATION: ContentStyle.BULLETED,
        DeliverableType.LINKEDIN_POST: ContentStyle.NARRATIVE,
        DeliverableType.TWITTER_THREAD: ContentStyle.BULLETED,
        DeliverableType.ADVISORY: ContentStyle.BULLETED,
        DeliverableType.EXECUTIVE_SUMMARY: ContentStyle.NARRATIVE,
        DeliverableType.PRESS_RELEASE: ContentStyle.NARRATIVE,
        DeliverableType.BRIEFING_NOTE: ContentStyle.BULLETED,
        DeliverableType.SITREP: ContentStyle.BULLETED,
        DeliverableType.INCIDENT_REPORT: ContentStyle.NARRATIVE,
        DeliverableType.CUSTOM: ContentStyle.NARRATIVE,
    }

    def resolve_spec(
        self,
        deliverable_type: DeliverableType,
        request: GenerateRequest,
        source_language: LanguageType = LanguageType.ENGLISH,
    ) -> DeliverableSpec:
        """Resolve a single DeliverableSpec from the operator's parameters."""
        # 1. Resolve Audience
        audience = request.audience if request.audience and request.audience != AudienceType.AUTO else AudienceType.GENERAL_PUBLIC

        # 2. Resolve Tone (Auto infers from Audience)
        if not request.tone or request.tone == ToneType.AUTO:
            tone = self.TONE_AUDIENCE_MAP.get(audience, ToneType.NEUTRAL)
        else:
            tone = request.tone

        # 3. Resolve Language (Auto infers from source language)
        if not request.language or request.language == LanguageType.AUTO:
            language = source_language
        else:
            language = request.language

        # 4. Resolve Length
        length = request.length if request.length else LengthType.STANDARD

        # 5. Resolve Detail Focus
        detail_focus = request.detail_focus if request.detail_focus else [DetailFocus.KEY_FACTS]

        # 6. Resolve Communication Objective (Auto infers from deliverable type)
        objective = request.communication_objective
        if not objective or objective == CommunicationObjective.AUTO:
            objective = self.OBJECTIVE_BY_TYPE.get(deliverable_type, CommunicationObjective.INFORM)

        # 7. Resolve Content Style (Auto infers from deliverable type)
        style = request.content_style
        if not style or style == ContentStyle.AUTO:
            style = self.STYLE_BY_TYPE.get(deliverable_type, ContentStyle.NARRATIVE)

        # 8. Sanitize instructions (treated as presentation hints only — for CUSTOM,
        # this doubles as the format description itself; see app/prompts/custom.txt)
        presentation_instructions = (request.additional_instructions or "").strip()

        return DeliverableSpec(
            deliverable_type=deliverable_type,
            audience=audience,
            tone=tone,
            language=language,
            length=length,
            detail_focus=detail_focus,
            communication_objective=objective,
            content_style=style,
            presentation_instructions=presentation_instructions,
        )

    def resolve_all_specs(
        self,
        request: GenerateRequest,
        source_language: LanguageType = LanguageType.ENGLISH,
    ) -> List[DeliverableSpec]:
        """Resolve specs for all selected deliverable types (multi-select fan-out)."""
        return [
            self.resolve_spec(dtype, request, source_language)
            for dtype in request.deliverable_types
        ]


resolver = ContentIntelligenceResolver()
