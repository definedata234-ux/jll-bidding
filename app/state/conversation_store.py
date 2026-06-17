"""
ConversationStore — persists raw Claude message-history (the chat
transcript, including tool_use/tool_result blocks) per opportunity.

This is deliberately separate from OpportunityStore: OpportunityStore holds
business state (memory_schema.json — what's true about the deal),
ConversationStore holds the literal back-and-forth needed to resume a chat
across turns/sessions. Keeping them apart means business state stays clean
and inspectable on its own (e.g. for the CRM-style /state view) without
wading through raw LLM message blocks.
"""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from app.config import CONVERSATIONS_DIR


class ConversationStore:
    def __init__(self, storage_dir: Path = CONVERSATIONS_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _path(self, opportunity_id: str) -> Path:
        return self.storage_dir / f"{opportunity_id}.json"

    def load(self, opportunity_id: str) -> list[dict]:
        path = self._path(opportunity_id)
        if not path.exists():
            return []
        with self._lock:
            return json.loads(path.read_text(encoding="utf-8"))

    def save(self, opportunity_id: str, messages: list[dict]) -> None:
        with self._lock:
            self._path(opportunity_id).write_text(json.dumps(messages, indent=2), encoding="utf-8")
