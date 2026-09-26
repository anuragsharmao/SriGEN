"""Deliverable Adapters package for SriGEN."""
from app.adapters.base import BaseDeliverableAdapter
from app.adapters.linkedin import LinkedInAdapter
from app.adapters.twitter_thread import TwitterThreadAdapter
from app.adapters.press_release import PressReleaseAdapter
from app.adapters.public_faq import PublicFaqAdapter
from app.adapters.advisory import AdvisoryAdapter
from app.adapters.executive_summary import ExecutiveSummaryAdapter
from app.adapters.briefing_note import BriefingNoteAdapter
from app.adapters.sitrep import SitrepAdapter
from app.adapters.incident_report import IncidentReportAdapter
from app.adapters.presentation import PresentationAdapter
from app.adapters.infographic import InfographicAdapter
from app.adapters.video_package import VideoPackageAdapter
from app.adapters.custom import CustomAdapter

ADAPTER_REGISTRY = {
    "linkedin_post": LinkedInAdapter(),
    "twitter_thread": TwitterThreadAdapter(),
    "press_release": PressReleaseAdapter(),
    "public_faq": PublicFaqAdapter(),
    "advisory": AdvisoryAdapter(),
    "executive_summary": ExecutiveSummaryAdapter(),
    "briefing_note": BriefingNoteAdapter(),
    "sitrep": SitrepAdapter(),
    "incident_report": IncidentReportAdapter(),
    "presentation": PresentationAdapter(),
    "infographic": InfographicAdapter(),
    "video_package": VideoPackageAdapter(),
    "custom": CustomAdapter(),
}

__all__ = [
    "BaseDeliverableAdapter",
    "LinkedInAdapter",
    "TwitterThreadAdapter",
    "PressReleaseAdapter",
    "PublicFaqAdapter",
    "AdvisoryAdapter",
    "ExecutiveSummaryAdapter",
    "BriefingNoteAdapter",
    "SitrepAdapter",
    "IncidentReportAdapter",
    "PresentationAdapter",
    "InfographicAdapter",
    "VideoPackageAdapter",
    "CustomAdapter",
    "ADAPTER_REGISTRY",
]
