"""X / Twitter Thread deliverable adapter."""
from app.adapters.base import BaseDeliverableAdapter


class TwitterThreadAdapter(BaseDeliverableAdapter):
    def __init__(self):
        super().__init__(template_filename="twitter_thread.txt")
