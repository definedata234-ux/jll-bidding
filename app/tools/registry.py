"""
Tool registry — maps the tool names defined in agent/tools.json (a
GENERATED file — see scripts/generate_schemas.py) to their Python
implementations, and provides a single dispatch() entry point used by the
orchestrator's tool-use loop.
"""
from __future__ import annotations

import time

from app.config import load_tool_schemas
from app.logging_config import get_logger
from app.state import OpportunityStore

from .fm_tools import get_fm_catalog
from .property_tools import (
    get_competitor_intel,
    get_market_benchmark,
    score_shortlist,
    search_properties,
)
from .state_tools import get_opportunity_state, update_opportunity_state
from .workflow_tools import log_pipeline_event, request_human_approval, save_draft_artifact

TOOL_FUNCTIONS = {
    "get_opportunity_state": get_opportunity_state,
    "update_opportunity_state": update_opportunity_state,
    "search_properties": search_properties,
    "get_market_benchmark": get_market_benchmark,
    "get_competitor_intel": get_competitor_intel,
    "score_shortlist": score_shortlist,
    "get_fm_catalog": get_fm_catalog,
    "save_draft_artifact": save_draft_artifact,
    "request_human_approval": request_human_approval,
    "log_pipeline_event": log_pipeline_event,
}

TOOLS_SCHEMA = load_tool_schemas()

_SCHEMA_NAMES = {t["name"] for t in TOOLS_SCHEMA}
_MISSING = _SCHEMA_NAMES - set(TOOL_FUNCTIONS)
if _MISSING:
    raise RuntimeError(f"tools.json defines tools with no implementation: {_MISSING}")


def _to_openai_tool(claude_tool: dict) -> dict:
    """Convert a Claude-format tool schema ({name, description, input_schema})
    into the OpenAI/DeepSeek function-calling format
    ({type: function, function: {name, description, parameters}}).
    agent/tools.json stays in Claude format as the single source of truth;
    this is a runtime-only adapter for the DeepSeek provider."""
    return {
        "type": "function",
        "function": {
            "name": claude_tool["name"],
            "description": claude_tool["description"],
            "parameters": claude_tool["input_schema"],
        },
    }


OPENAI_TOOLS_SCHEMA = [_to_openai_tool(t) for t in TOOLS_SCHEMA]

logger = get_logger(__name__)


def dispatch(tool_name: str, tool_input: dict, store: OpportunityStore) -> dict:
    """Execute a tool call by name. Raises KeyError for unknown tools so the
    orchestrator can convert that into a tool_result error block rather than
    crashing the whole conversation. Every call is logged (tool name,
    opportunity_id if present, outcome, duration) for audit/observability —
    this is the agent's equivalent of an access log."""
    opportunity_id = tool_input.get("opportunity_id") if isinstance(tool_input, dict) else None
    started = time.monotonic()

    if tool_name not in TOOL_FUNCTIONS:
        logger.error("tool_dispatch_unknown", tool=tool_name, opportunity_id=opportunity_id)
        raise KeyError(f"Unknown tool '{tool_name}'")

    fn = TOOL_FUNCTIONS[tool_name]
    try:
        result = fn(tool_input, store)
    except Exception as exc:  # noqa: BLE001 - logged then re-raised for the orchestrator to surface
        logger.error(
            "tool_dispatch_failed",
            tool=tool_name,
            opportunity_id=opportunity_id,
            error=str(exc),
            duration_ms=round((time.monotonic() - started) * 1000, 1),
        )
        raise
    logger.info(
        "tool_dispatch_ok",
        tool=tool_name,
        opportunity_id=opportunity_id,
        duration_ms=round((time.monotonic() - started) * 1000, 1),
    )
    return result
