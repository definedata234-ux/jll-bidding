"""
Shared approval-resolution helper used by both cli.py and api.py.

Approving/rejecting an artifact is a human action that happens OUTSIDE the
LLM's tool calls — by design, the agent has no tool that can grant its own
approval requests. After a human decides, we inject a synthetic user-role
note into the conversation so the agent is explicitly told the outcome on
its next turn, rather than having to guess or re-call get_opportunity_state
speculatively.
"""
from __future__ import annotations

from app.state import ConversationStore, OpportunityStore


def decide_approval(
    opportunity_id: str,
    approval_id: str,
    decision: str,
    reviewer: str,
    opportunity_store: OpportunityStore,
    conversation_store: ConversationStore,
) -> dict:
    approval = opportunity_store.resolve_approval(opportunity_id, approval_id, decision, reviewer)

    history = conversation_store.load(opportunity_id)
    note = (
        f"[HUMAN REVIEWER NOTE] Reviewer '{reviewer}' has {approval['status'].upper()} "
        f"approval request {approval_id} (artifact type: {approval['artifact_type']}). "
        "You may proceed accordingly on the next relevant step."
    )
    history.append({"role": "user", "content": note})
    conversation_store.save(opportunity_id, history)

    return approval
