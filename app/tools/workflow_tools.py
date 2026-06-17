"""save_draft_artifact, request_human_approval, log_pipeline_event.

These three are the workflow/guardrail backbone: drafts are only ever
saved (never sent), approval requests are only ever raised (never
self-granted by the agent), and every stage transition gets logged for
reporting. See agent/workflow_state_machine.md for the contract these
implement.
"""
from __future__ import annotations

from app.state import OpportunityStore

from .schemas import LogPipelineEventInput, RequestHumanApprovalInput, SaveDraftArtifactInput


def save_draft_artifact(input: dict, store: OpportunityStore) -> dict:
    parsed = SaveDraftArtifactInput.model_validate(input)
    entry = store.append_draft(
        opportunity_id=parsed.opportunity_id,
        artifact_type=parsed.artifact_type.value,
        content=parsed.content,
        status=parsed.status,
    )
    return {"status": "saved", "artifact": entry}


def request_human_approval(input: dict, store: OpportunityStore) -> dict:
    parsed = RequestHumanApprovalInput.model_validate(input)
    approval = store.append_approval_request(
        opportunity_id=parsed.opportunity_id,
        artifact_type=parsed.artifact_type,
        summary=parsed.summary,
        urgency=parsed.urgency,
    )
    return {
        "status": "pending_approval",
        "approval_id": approval["approval_id"],
        "message": (
            f"Approval request {approval['approval_id']} raised for "
            f"{parsed.artifact_type}. A JLL reviewer must approve this "
            "before it can be treated as client-ready. Do not proceed as if "
            "approved until informed otherwise."
        ),
    }


def log_pipeline_event(input: dict, store: OpportunityStore) -> dict:
    parsed = LogPipelineEventInput.model_validate(input)
    entry = store.append_pipeline_event(
        opportunity_id=parsed.opportunity_id,
        stage=parsed.stage.value,
        event=parsed.event,
        outcome=parsed.outcome,
        notes=parsed.notes,
    )
    return {"status": "logged", "event": entry}
