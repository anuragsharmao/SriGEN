"""Infographic deliverable adapter — content-only (sections, key messaging, layout
recommendation), no image file rendered."""
from app.adapters.base import BaseDeliverableAdapter
from app.db.schemas import InfographicPackage


class InfographicAdapter(BaseDeliverableAdapter):
    output_model = InfographicPackage

    def __init__(self):
        super().__init__(template_filename="infographic.txt")
