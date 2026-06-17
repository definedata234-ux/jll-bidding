"""
OpportunityStore — file-backed persistence for the per-opportunity memory
record, now backed end-to-end by the OpportunityRecord Pydantic model
(app/domain/models.py) instead of an untyped dict. Every read parses and
validates the stored JSON against the model; every write re-validates
before it touches disk. A malformed write is rejected before it's
persisted, not discovered later by something trying to read it back.

Public methods still return plain JSON-safe dicts (via model_dump(mode=
"json")) rather than Pydantic objects, so existing dict-style consumers
(app/api.py, app/cli.py, the test suite) don't all need rewriting to
attribute access — validation rigor without a sweeping interface change.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from app.config import OPPORTUNITIES_DIR
from app.domain import OpportunityRecord


class OpportunityNotFound(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OpportunityStore:
    def __init__(self, storage_dir: Path = OPPORTUNITIES_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _path(self, opportunity_id: str) -> Path:
        return self.storage_dir / f"{opportunity_id}.json"

    def create(self, client_name: str, opportunity_id: Optional[str] = None) -> dict:
        opportunity_id = opportunity_id or f"OPP-{uuid.uuid4().hex[:8].upper()}"
        now = _now()
        record = OpportunityRecord(
            opportunity_id=opportunity_id, client_name=client_name, created_at=now, updated_at=now
        )
        self._write(record)
        return record.model_dump(mode="json")

    def get(self, opportunity_id: str) -> dict:
        return self._load(opportunity_id).model_dump(mode="json")

    def _load(self, opportunity_id: str) -> OpportunityRecord:
        path = self._path(opportunity_id)
        if not path.exists():
            raise OpportunityNotFound(
                f"No opportunity found with id '{opportunity_id}'. Use the exact "
                "opportunity_id given for this session — do not invent or guess one."
            )
        with self._lock:
            raw = json.loads(path.read_text(encoding="utf-8"))
        return OpportunityRecord.model_validate(raw)

    def _write(self, record: OpportunityRecord) -> None:
        record.updated_at = _now()
        with self._lock:
            self._path(record.opportunity_id).write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self.storage_dir.glob("*.json"))

    def update(self, opportunity_id: str, patch: dict, reason: str = "") -> dict:
        """Merge a partial patch into the stored record, then re-validate the
        WHOLE record before writing. Top-level fields in the patch replace
        the existing value outright (e.g. a new `requirements` object
        replaces the old one wholesale — partial patching of a validated
        nested model isn't meaningful, so callers must send complete
        objects). `flags` is the one exception: its list fields are
        appended and de-duplicated rather than replaced, since flags
        accumulate over the life of an opportunity."""
        record = self._load(opportunity_id)
        data = record.model_dump(mode="json")

        for key, value in patch.items():
            if key in ("opportunity_id", "created_at", "audit_log"):
                continue  # immutable / managed separately
            if key == "flags" and isinstance(value, dict):
                merged = data.get("flags") or {"data_gaps": [], "confidentiality_notes": []}
                for fk in ("data_gaps", "confidentiality_notes"):
                    if fk in value:
                        merged[fk] = list(dict.fromkeys((merged.get(fk) or []) + value[fk]))
                data["flags"] = merged
            else:
                data[key] = value

        if reason:
            data.setdefault("audit_log", []).append({"timestamp": _now().isoformat(), "reason": reason})

        updated = OpportunityRecord.model_validate(data)
        self._write(updated)
        return updated.model_dump(mode="json")

    def append_pipeline_event(
        self,
        opportunity_id: str,
        stage: str,
        event: str,
        outcome: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        record = self._load(opportunity_id)
        data = record.model_dump(mode="json")
        entry = {"timestamp": _now().isoformat(), "stage": stage, "event": event}
        if outcome:
            entry["outcome"] = outcome
        if notes:
            entry["notes"] = notes
        data["pipeline_events"].append(entry)
        updated = OpportunityRecord.model_validate(data)
        self._write(updated)
        return entry

    def append_draft(
        self,
        opportunity_id: str,
        artifact_type: str,
        content: str,
        status: str = "draft",
    ) -> dict:
        record = self._load(opportunity_id)
        data = record.model_dump(mode="json")
        existing_versions = [
            d["version"] for d in data["proposal_drafts"] if d["artifact_type"] == artifact_type
        ]
        version = max(existing_versions, default=0) + 1
        entry = {
            "artifact_type": artifact_type,
            "version": version,
            "created_at": _now().isoformat(),
            "content": content,
            "status": status,
        }
        data["proposal_drafts"].append(entry)
        updated = OpportunityRecord.model_validate(data)
        self._write(updated)
        return entry

    def append_approval_request(
        self,
        opportunity_id: str,
        artifact_type: str,
        summary: str,
        urgency: str = "normal",
    ) -> dict:
        record = self._load(opportunity_id)
        data = record.model_dump(mode="json")
        approval = {
            "approval_id": f"APR-{uuid.uuid4().hex[:6].upper()}",
            "artifact_type": artifact_type,
            "summary": summary,
            "urgency": urgency,
            "status": "pending",
            "requested_at": _now().isoformat(),
        }
        data["approvals"].append(approval)
        updated = OpportunityRecord.model_validate(data)
        self._write(updated)
        return approval

    def resolve_approval(
        self, opportunity_id: str, approval_id: str, decision: str, reviewer: str = "human"
    ) -> dict:
        if decision not in ("approve", "reject"):
            raise ValueError("decision must be 'approve' or 'reject'")
        record = self._load(opportunity_id)
        data = record.model_dump(mode="json")

        target = next((a for a in data["approvals"] if a["approval_id"] == approval_id), None)
        if target is None:
            raise ValueError(f"No approval request {approval_id} on opportunity {opportunity_id}")
        target["status"] = "approved" if decision == "approve" else "rejected"
        target["decided_at"] = _now().isoformat()
        target["reviewer"] = reviewer

        matching_drafts = [d for d in data["proposal_drafts"] if d["artifact_type"] == target["artifact_type"]]
        if matching_drafts:
            latest = max(matching_drafts, key=lambda d: d["version"])
            latest["status"] = "approved" if decision == "approve" else "rejected"

        updated = OpportunityRecord.model_validate(data)
        self._write(updated)
        return target
