---
name: jll-bid-copilot
description: Operate, extend, or troubleshoot the JLL Bid & Leasing Copilot — an internal AI agent for commercial real estate lease/purchase bidding, property shortlisting, competitive analysis, FM (facility management) upsell, and pipeline tracking. Use this skill when starting or running the agent (CLI, API, or web UI), adding/changing tools or domain fields, regenerating agent/tools.json or agent/memory_schema.json, switching LLM providers (Anthropic/DeepSeek), adding mock data, writing tests for it, or debugging tool-call validation errors. Always consult this skill before hand-editing agent/tools.json or agent/memory_schema.json — they are GENERATED files and hand-edits will be silently overwritten and will drift from the code that actually validates them.
metadata:
  version: "1.0.0"
  project: JLL-Bidding-Agent
  stage: "4 — Enterprise Reconfiguration"
  source: internal
---

# JLL Bid & Leasing Copilot

An internal decision-support agent for JLL bid managers/brokers/account managers pursuing commercial real estate deals — lease or purchase. It gathers client requirements, shortlists and scores properties, benchmarks against the market and competitors, drafts bid proposals, recommends FM service bundles, and — if a bid is lost — automatically pivots to a standalone FM services upsell pitch. It is **not client-facing**; it assists JLL staff, who approve everything before it reaches a client.

## Architecture (read this before changing anything)

```
tools/      (LLM-facing adapters — parse input via Pydantic, call a service, return JSON)
   ↓
services/   (business logic — search, scoring, FM pricing; transaction-type branching lives here)
   ↓
repositories/  (data-access interfaces; mock.py is the only implementation today)
   ↓
data/*.json (mock inventory, market benchmarks, competitor intel, FM catalog)
```

Single source of truth for every data shape: `app/domain/models.py` (persisted state) and `app/domain/queries.py` (transient query DTOs) and `app/tools/schemas.py` (one Pydantic model per tool input). **`agent/tools.json` and `agent/memory_schema.json` are GENERATED from those models** — run `python scripts/generate_schemas.py` after changing any of them. Never hand-edit those two JSON files; the next generation run will overwrite your edits, and until you regenerate, the agent-facing schema and the runtime validation will disagree (this exact bug — the agent inventing field names because nothing constrained them — is what caused the Stage 3→4 rework).

## Running it

```
cd JLL-Bidding-Agent
pip install -r requirements.txt
cp .env.example .env   # then set LLM_PROVIDER + the matching API key
```

- **Tests (no API key needed):** `python -m pytest tests/ -v` — 13 tests exercise the tool/service/repository layers directly, bypassing the LLM.
- **CLI:** `python -m app.cli` — `/new <client>`, `/state`, `/approvals`, `/approve <id>`, `/events`, `/quit`.
- **API + web UI:** `uvicorn app.api:app --reload --port 8000`, then open `http://127.0.0.1:8000`. Docs at `/docs`.
- **Regenerate the agent spec after any domain/tool-schema change:** `python scripts/generate_schemas.py`.

Both providers are supported via `LLM_PROVIDER` in `.env` (`anthropic` or `deepseek`) — see `app/orchestrator.py`. Do not switch providers mid-opportunity; Claude and DeepSeek use incompatible message-history shapes, so an in-progress conversation will break.

## Primary inputs (the requirements schema)

Every opportunity requires, before shortlisting can run: `transaction_type` (`lease`|`purchase`), `property_type`, `locations` (≥1), `budget` (a `max_amount` + basis matching the transaction type — `per_sqft`/`total_annual` for lease, `total_purchase_price`/`per_sqft_purchase` for purchase), and `timeline` (`target_date` + optional deadline/flexibility). `lease_term_months` is required for lease, forbidden in spirit for purchase. Optional: `square_footage_min/max`, `seats`, `zoning_classifications`, `must_have_facilities`/`nice_to_have_facilities`, `industry`, `special_needs`. Full model: `app/domain/models.py::Requirements`.

## The 10 tools

`get_opportunity_state`, `update_opportunity_state`, `search_properties`, `get_market_benchmark`, `get_competitor_intel`, `score_shortlist`, `get_fm_catalog`, `save_draft_artifact`, `request_human_approval`, `log_pipeline_event`. Implementations: `app/tools/*.py`, dispatch table: `app/tools/registry.py`. There is **no tool that sends anything to a client** — `save_draft_artifact` only persists, `request_human_approval` only requests. A human resolves approvals via the CLI's `/approve`, the API's approval-decision endpoint, or the web UI's buttons — never via a tool call.

## Workflow stages

`INTAKE → SHORTLISTING → COMPARISON → PROPOSAL_DRAFTING → FM_BUNDLING → NEGOTIATION → OUTCOME_PENDING → (WON_CLOSEOUT | LOST_FM_UPSELL) → LOGGED`. Full transition guards and re-entrancy rules: `agent/workflow_state_machine.md`. The state machine is enforced by convention/prompt instruction, not hard-coded in the orchestrator — `stage` lives in the data (`OpportunityRecord.stage`) and the system prompt tells the agent to respect it.

## Safety Rules (do not weaken these)

- Never fabricate property data, prices, or competitor intel — every factual claim must trace to a tool call.
- Every inference/estimate must be labeled as such, with confidence when known.
- Nothing reaches a client without `request_human_approval` — this is structural (no send-capable tool exists), not just an instruction; keep it that way in any extension.
- No pricing/contract authority — commercial terms are "options to consider," never decisions made.
- Opportunities are isolated; never let one client's data leak into another's context.
- On a lost or at-risk bid, the agent must proactively pitch standalone FM services — this is the core commercial logic ("win or not, find revenue"), not optional.

## Common Tasks

**Add a new tool:** define its input model in `app/tools/schemas.py`, implement the function in the matching `app/tools/*.py` file, register it in `TOOL_FUNCTIONS` in `app/tools/registry.py`, add its `(name, description, model)` entry to `TOOL_DEFINITIONS` in `scripts/generate_schemas.py`, then run the generator.

**Add/change a domain field:** edit `app/domain/models.py` (or `queries.py`), update any service/repository logic that reads it, update `app/tools/schemas.py` if a tool exposes it, run `python scripts/generate_schemas.py`, update `agent/system_prompt.md`'s "PRIMARY INTAKE INPUTS" section if it's a primary input, update/add tests.

**Add mock data:** edit the relevant file in `app/data/` and validate it against the matching domain model before trusting it (e.g. `PropertyListing.model_validate(row)` for `properties.json`) — the mock repositories validate at load time and will raise on bad data.

**Swap a mock for a real integration:** implement the relevant interface in `app/repositories/base.py`, then change the assignment in `app/repositories/instances.py`. No other file should need to change.

**Switch LLM provider:** set `LLM_PROVIDER` and the matching key in `.env`; restart the process (env is read at import time).

## Troubleshooting Heuristics

- Tool call rejected with a Pydantic validation error → the caller (LLM or test) used a field name/shape that doesn't match `app/tools/schemas.py`. Don't loosen the schema to accept the wrong shape; fix the caller, or fix the schema's `description` field if it's genuinely ambiguous, then regenerate.
- Agent invents an `opportunity_id` → check `app/orchestrator.py::_system_prompt_for()` is actually being called per-turn; this was a real bug once (the model never knew its own opportunity_id).
- `score_shortlist` returns suspiciously neutral scores (~0.5 on every dimension) → the stored `requirements` likely don't match the expected field names/shapes; inspect via `get_opportunity_state` or the API's `/opportunities/{id}`.
- 429 from the API → rate limiter (`slowapi`), default 60/min global, 15/min on `/chat`. Expected behavior, not a bug.
- `agent/tools.json` or `agent/memory_schema.json` look stale or wrong → you forgot to run `python scripts/generate_schemas.py` after a model change.

## What Good Looks Like

- Every tool input is a typed Pydantic model with field-level descriptions, not a loose dict.
- `agent/tools.json` and `agent/memory_schema.json` are regenerated (never hand-edited) and committed alongside the model change that produced them.
- New domain capabilities (new transaction types, new filters) get a repository method + service logic + tool schema + a passing test, in that order.
- Tests exercise the tool/service/repository layers directly (no LLM call needed) for anything that can be tested deterministically; live LLM verification is reserved for proving the orchestration/prompt actually drives the tools correctly.

## Resources

- [docs/01-architecture-design.md](../../../docs/01-architecture-design.md) — original business case and architecture
- [docs/02-agent-spec-overview.md](../../../docs/02-agent-spec-overview.md) — system prompt / tools / workflow / memory design rationale
- [docs/03-prototype-architecture.md](../../../docs/03-prototype-architecture.md) — Stage 3 prototype build
- [docs/04-enterprise-reconfiguration.md](../../../docs/04-enterprise-reconfiguration.md) — domain model expansion, layering, enterprise rigor additions
- [README.md](../../../README.md) — canonical run instructions and project structure
- [agent/system_prompt.md](../../../agent/system_prompt.md) — the agent's actual persona/guardrails
- [agent/workflow_state_machine.md](../../../agent/workflow_state_machine.md) — stage transition contract
