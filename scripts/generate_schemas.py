"""
Generates agent/tools.json and agent/memory_schema.json FROM the Pydantic
models in app/tools/schemas.py and app/domain/models.py.

This is the fix for the bug class found during DeepSeek testing (the
agent inventing wrong field names because the hand-written tool schema
didn't actually constrain the data shape): code defines the shape once,
these two docs are generated outputs, not independently hand-maintained
copies that can drift from what the tools actually accept.

Run after any change to app/tools/schemas.py or app/domain/models.py:
    python scripts/generate_schemas.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.domain import OpportunityRecord  # noqa: E402
from app.tools import schemas as tool_schemas  # noqa: E402

AGENT_DIR = PROJECT_ROOT / "agent"


def _clean(node: Any, defs: dict) -> Any:
    """Recursively inline $ref/$defs and $allOf-wrapped single refs (how
    Pydantic v2 represents 'a field typed as another model'), and drop
    Pydantic's 'title' noise. Tool-calling APIs (Claude, OpenAI-compatible)
    expect a self-contained JSON Schema, not $ref pointers."""
    if isinstance(node, list):
        return [_clean(x, defs) for x in node]
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        ref_key = node["$ref"].split("/")[-1]
        resolved = _clean(defs[ref_key], defs)
        merged = dict(resolved)
        for k, v in node.items():
            if k not in ("$ref", "title"):
                merged[k] = _clean(v, defs)
        return merged

    if "allOf" in node and len(node["allOf"]) == 1:
        inner = _clean(node["allOf"][0], defs)
        merged = dict(inner)
        for k, v in node.items():
            if k not in ("allOf", "title"):
                merged[k] = _clean(v, defs)
        return merged

    return {k: _clean(v, defs) for k, v in node.items() if k not in ("$defs", "title")}


def to_input_schema(model: type) -> dict:
    raw = model.model_json_schema()
    defs = raw.get("$defs", {})
    return _clean(raw, defs)


# Tool name -> (description, input model). Descriptions are hand-written
# (Pydantic field-level descriptions cover the per-field detail); this is
# the per-tool "why/when to call this" text the agent actually reads.
TOOL_DEFINITIONS = [
    (
        "get_opportunity_state",
        "Retrieve the full stored state for an opportunity: client requirements, current workflow stage, shortlist, FM bundle, drafts, negotiation log, and outcome. Call this at the start of a session, or whenever unsure of current stage/known facts, instead of relying solely on chat history.",
        tool_schemas.GetOpportunityStateInput,
    ),
    (
        "update_opportunity_state",
        "Persist new or changed information into an opportunity's memory record (e.g. newly gathered requirements, a stage transition, a new shortlist, an outcome). Use this so facts survive across turns/sessions rather than living only in chat history. Gather ALL primary requirement inputs (transaction_type, property_type, locations, budget, timeline, plus whatever else is known) before sending the requirements object — it replaces the stored requirements wholesale, it does not patch one field at a time.",
        tool_schemas.UpdateOpportunityStateInput,
    ),
    (
        "search_properties",
        "Query the property inventory data source for candidate spaces matching hard constraints, for either a lease or a purchase transaction. Returns only what the data source actually has — fewer or zero results if nothing matches, never invented candidates.",
        tool_schemas.SearchPropertiesInput,
    ),
    (
        "get_market_benchmark",
        "Retrieve market-rate benchmark data for a given location, property type, AND transaction type (lease vs purchase pricing are benchmarked separately), to support pricing-competitiveness analysis. Results are labeled benchmark data with source/confidence, not exact quotes.",
        tool_schemas.GetMarketBenchmarkInput,
    ),
    (
        "get_competitor_intel",
        "Retrieve any known historical or inferred intel about competitor bidders' pricing/positioning for a location or specific property. Every returned item must be treated and presented as an estimate, not fact, and includes a confidence field.",
        tool_schemas.GetCompetitorIntelInput,
    ),
    (
        "score_shortlist",
        "Deterministically compute a weighted fit score for each candidate property against the opportunity's stored requirements (price scoring is transaction-type-aware: lease rate vs purchase price). Use this instead of manually estimating scores, so ranking stays consistent and auditable. Requires that update_opportunity_state has already been called with the full requirements object. Default weights are price 0.40, location 0.25, amenities 0.20, availability 0.15 unless overridden.",
        tool_schemas.ScoreShortlistInput,
    ),
    (
        "get_fm_catalog",
        "Retrieve available facility management (FM) service tiers and indicative pricing for the requested categories (pantry, stationery, washroom, electrical, plumbing, general_ops), sized to the client's headcount/building profile. Use before recommending any FM bundle or upsell pitch.",
        tool_schemas.GetFmCatalogInput,
    ),
    (
        "save_draft_artifact",
        "Persist a generated draft (bid proposal, negotiation brief, FM bundle recommendation, or FM upsell pitch) to the opportunity record for human review. This ONLY saves a draft — it never sends, emails, or finalizes anything to a client. Always follow with request_human_approval before treating the artifact as client-ready.",
        tool_schemas.SaveDraftArtifactInput,
    ),
    (
        "request_human_approval",
        "Notify a human JLL bid manager/account manager that an artifact (proposal, negotiation brief, pricing change, FM pitch) is ready and requires review/approval before anything is sent to the client. This is the mandatory gate before any client-facing action — call it before treating any artifact as final.",
        tool_schemas.RequestHumanApprovalInput,
    ),
    (
        "log_pipeline_event",
        "Record a pipeline/event log entry for reporting (win rate, time-to-proposal, FM attach rate, cycle time). Call at every stage transition, and always at outcome determination (won/lost) and at FM upsell pitch/attach events.",
        tool_schemas.LogPipelineEventInput,
    ),
]


def generate_tools_json() -> dict:
    tools = []
    for name, description, model in TOOL_DEFINITIONS:
        tools.append({"name": name, "description": description, "input_schema": to_input_schema(model)})
    return {
        "_comment": (
            "GENERATED FILE — do not hand-edit. Run `python scripts/generate_schemas.py` after "
            "changing app/tools/schemas.py. Claude API tool-use definitions for the JLL Bid & "
            "Leasing Copilot; pass this 'tools' array directly in the Messages API request "
            "alongside system_prompt.md. Every tool below is implemented with stubbed/mock "
            "responses in Stage 3/4 (no real data sources yet)."
        ),
        "tools": tools,
    }


def generate_memory_schema() -> dict:
    schema = to_input_schema(OpportunityRecord)
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://jll.internal/bid-agent/memory_schema.json",
        "title": "JLL Bid & Leasing Copilot — Opportunity Memory Record",
        "description": (
            "GENERATED FILE — do not hand-edit. Run `python scripts/generate_schemas.py` after "
            "changing app/domain/models.py. One record per leasing/purchase opportunity. This is "
            "what get_opportunity_state returns and what update_opportunity_state patches."
        ),
        **{k: v for k, v in schema.items() if k not in ("description",)},
    }


def main() -> None:
    tools_path = AGENT_DIR / "tools.json"
    memory_path = AGENT_DIR / "memory_schema.json"

    tools_path.write_text(json.dumps(generate_tools_json(), indent=2) + "\n", encoding="utf-8")
    memory_path.write_text(json.dumps(generate_memory_schema(), indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {tools_path.relative_to(PROJECT_ROOT)} ({len(TOOL_DEFINITIONS)} tools)")
    print(f"Wrote {memory_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
