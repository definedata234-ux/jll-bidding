# JLL Bid Copilot — Claude Code Guidance

## Purpose

JLL Bid Copilot is an internal AI decision-support tool for JLL bid managers and brokers pursuing commercial real estate deals (lease or purchase). It collects client requirements, shortlists and scores properties, benchmarks the market, drafts proposals, recommends FM (facility management) bundles, and — on a lost bid — automatically pivots to a standalone FM upsell pitch. It is **not client-facing**; JLL staff review and approve every output before it reaches a client.

---

## Non-Negotiables

- **Never hand-edit `agent/tools.json` or `agent/memory_schema.json`.** Both are generated from `app/domain/models.py` + `app/tools/schemas.py` by running `python scripts/generate_schemas.py`. Any hand-edit will be silently overwritten on the next generation run, and until you regenerate the agent-facing schema and the runtime Pydantic validation will disagree — this exact divergence caused the Stage 3→4 rework.
- **Never add a tool that sends content directly to a client.** `save_draft_artifact` persists only; `request_human_approval` requests only. A human resolves approvals outside the LLM's tool surface. This is structural, not instructional — keep it that way.
- **Never commit `.env`.** It is gitignored. Only `.env.example` (placeholder values) is committed. Never print, log, or expose API key values anywhere.
- **Never weaken the safety rules in `agent/system_prompt.md`** — no fabricating property data, no pricing/contract authority, opportunities must stay isolated from each other, FM upsell must always trigger on a lost or at-risk bid.
- **`app/domain/models.py` is the single source of truth for every data shape.** If you change a field there, update `app/tools/schemas.py`, re-run the generator, update `agent/system_prompt.md` if the field is a primary intake input, and add/update tests.

---

## Architecture

```
tools/      (LLM-facing adapters — parse input via Pydantic, call a service, return JSON)
   ↓
services/   (business logic — search, scoring, FM pricing; transaction-type branching lives here)
   ↓
repositories/  (data-access interfaces; mock.py is the only implementation today)
   ↓
data/*.json (mock inventory, market benchmarks, competitor intel, FM catalog)
```

**State** lives in `app/state/store.py` (one JSON file per opportunity, fully validated against `OpportunityRecord` on every read/write). Chat history lives in `app/state/conversation_store.py`.

**The web UI** (`app/static/`) is a single-page vanilla JS dashboard served by FastAPI. It has no build step — edit `app.js`, `index.html`, or `styles.css` and the server's `--reload` picks them up instantly. Do not introduce a JS framework or bundler.

---

## Critical Files

| File | What it is | What to do if you change it |
|---|---|---|
| `app/domain/models.py` | Pydantic domain models (Requirements, PropertyListing, OpportunityRecord, …) | Run `python scripts/generate_schemas.py` after any change |
| `app/tools/schemas.py` | One Pydantic input model per LLM tool | Run `python scripts/generate_schemas.py` after any change |
| `agent/tools.json` | **GENERATED** — tool-use schemas sent to the LLM | Never edit; re-run the generator |
| `agent/memory_schema.json` | **GENERATED** — per-opportunity JSON Schema | Never edit; re-run the generator |
| `agent/system_prompt.md` | Agent persona, guardrails, primary-intake-inputs block | Update the PRIMARY INTAKE INPUTS section if domain fields change |
| `agent/workflow_state_machine.md` | 10-stage state machine and transition guards | Keep in sync with `OpportunityRecord.stage` enum |
| `app/repositories/instances.py` | Singleton wiring — which implementation backs each interface | The only file to change when swapping a mock for a real integration |
| `app/static/app.js` | All dashboard interactivity (no framework, vanilla JS) | No build step needed; server --reload picks it up |

---

## Common Tasks

**Add a new tool**
1. Define its input model in `app/tools/schemas.py`
2. Implement the function in the appropriate `app/tools/*.py` file
3. Register it in `TOOL_FUNCTIONS` in `app/tools/registry.py`
4. Add its `(name, description, model)` to `TOOL_DEFINITIONS` in `scripts/generate_schemas.py`
5. Run `python scripts/generate_schemas.py`
6. Add a test in `tests/`

**Add or change a domain field**
1. Edit `app/domain/models.py` (or `queries.py`)
2. Update any service/repository logic that reads it
3. Update `app/tools/schemas.py` if a tool exposes it
4. Run `python scripts/generate_schemas.py`
5. Update `agent/system_prompt.md` PRIMARY INTAKE INPUTS section if it's a required input
6. Update/add tests

**Add mock data**
Edit the relevant file in `app/data/` and validate it against the domain model before trusting it:
```python
from app.domain.models import PropertyListing
PropertyListing.model_validate(row)   # raises on bad data
```
Mock repositories validate at load time and will raise on load if data is malformed.

**Swap a mock for a real integration**
Implement the relevant abstract interface in `app/repositories/base.py`, then change the assignment in `app/repositories/instances.py`. No other file needs to change.

**Switch LLM provider**
Set `LLM_PROVIDER` and the matching key in `.env`; restart the process. Do not switch providers mid-opportunity — Claude and DeepSeek use incompatible message-history shapes.

---

## Running / Verifying Changes

```bash
# Tests (no API key needed — exercises tool/service/repository layers directly)
python -m pytest tests/ -v

# API + web UI
uvicorn app.api:app --reload --port 8000
# Then open http://127.0.0.1:8000

# Regenerate agent spec after domain/tool-schema changes
python scripts/generate_schemas.py

# CLI (requires API key)
python -m app.cli
```

Run the test suite after every change that touches `app/domain/`, `app/tools/`, `app/services/`, or `app/repositories/`. The 13 tests cover lease-won, lease-lost-FM-upsell, purchase-won, and domain validation — they catch regressions without needing an LLM call.

---

## Troubleshooting

- **Tool call rejected with Pydantic validation error** — the LLM or test used a field name that doesn't match `app/tools/schemas.py`. Fix the schema description (so the LLM understands it) or fix the test; never loosen the schema.
- **Agent invents an `opportunity_id`** — check `app/orchestrator.py::_system_prompt_for()` is actually called per-turn.
- **`score_shortlist` returns ~0.5 on every dimension** — inspect stored requirements via `GET /opportunities/{id}`; the field names likely don't match the scoring logic.
- **429 from the API** — rate limiter (`slowapi`), default 60/min global, 15/min on `/chat`. Expected, not a bug.
- **`agent/tools.json` looks stale** — run `python scripts/generate_schemas.py`.

---

## What NOT to Add

- A tool that sends, emails, or delivers anything to a client (structural guardrail — must stay absent).
- Hand-edits to `agent/tools.json` or `agent/memory_schema.json`.
- Static fallback data in the web UI that could mask a missing API connection.
- Auth, real database, or containerization — explicitly out of scope for this stage.
- A JS framework or build toolchain for the frontend — vanilla JS only; no bundler.
- Real API keys, credentials, or secrets committed to the repository.
