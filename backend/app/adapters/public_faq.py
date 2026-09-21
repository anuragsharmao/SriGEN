"""Public FAQ deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class PublicFaqAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="public_faq.txt")
