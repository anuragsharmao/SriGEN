"""Executive Summary deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class ExecutiveSummaryAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="executive_summary.txt")
