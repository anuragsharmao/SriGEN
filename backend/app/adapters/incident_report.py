"""Technical Incident Report deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class IncidentReportAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="incident_report.txt")
