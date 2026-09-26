"""Situation Report (SITREP) deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class SitrepAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="sitrep.txt")
