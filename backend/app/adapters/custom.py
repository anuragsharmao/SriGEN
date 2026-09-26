"""Custom deliverable adapter — free-form plain-text output. `additional_instructions`
(spec.presentation_instructions) is interpreted as the format description itself,
not a style hint layered on a known format. See app/prompts/custom.txt for the
guardrail that keeps this from becoming a license to invent facts."""
from app.adapters.base import BaseDeliverableAdapter


class CustomAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="custom.txt")
