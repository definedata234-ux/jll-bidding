"""get_opportunity_state / update_opportunity_state."""
from __future__ import annotations

from app.state import OpportunityStore

from .schemas import GetOpportunityStateInput, UpdateOpportunityStateInput


def get_opportunity_state(input: dict, store: OpportunityStore) -> dict:
    parsed = GetOpportunityStateInput.model_validate(input)
    return store.get(parsed.opportunity_id)


def update_opportunity_state(input: dict, store: OpportunityStore) -> dict:
    parsed = UpdateOpportunityStateInput.model_validate(input)
    patch = parsed.model_dump(mode="json", exclude_none=True, exclude={"opportunity_id", "reason"})
    record = store.update(parsed.opportunity_id, patch, reason=parsed.reason)
    return {"status": "updated", "reason": parsed.reason, "record": record}
