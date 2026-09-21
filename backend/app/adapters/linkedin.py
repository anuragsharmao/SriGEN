"""LinkedIn Post deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class LinkedInAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="linkedin.txt")
