"""Briefing Note deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class BriefingNoteAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="briefing_note.txt")
