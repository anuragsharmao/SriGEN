"""Official Advisory deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class AdvisoryAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="advisory.txt")
