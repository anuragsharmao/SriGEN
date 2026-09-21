"""Presentation deliverable adapter — content-only (slides + speaker notes), no .pptx file."""
from app.adapters.base import BaseDeliverableAdapter
from app.db.schemas import PresentationPackage


class PresentationAdapter(BaseDeliverableAdapter):
    output_model = PresentationPackage

    def __init__(self):
        super().__init__(template_filename="presentation.txt")
