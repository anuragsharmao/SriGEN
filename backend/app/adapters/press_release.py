"""Press Release deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class PressReleaseAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="press_release.txt")
