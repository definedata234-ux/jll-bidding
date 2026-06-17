# JLL Bid Copilot — Skill Reference

An internal AI agent for JLL bid managers, brokers, and account managers pursuing commercial real estate deals (lease or purchase). The agent gathers client requirements, shortlists and scores available properties, benchmarks the market and competitors, drafts proposals, configures FM (facility management) service bundles, supports negotiation, and — on a lost bid — automatically pivots to a standalone FM upsell pitch. JLL staff review and approve everything before it reaches a client.

---

## What it does

| Stage | Agent activity |
|---|---|
| INTAKE | Extracts and validates client requirements from conversation |
| SHORTLISTING | Searches property inventory; filters by budget, location, seats, facilities |
| COMPARISON | Scores shortlisted properties; fetches market benchmark and competitor intel |
| PROPOSAL_DRAFTING | Drafts bid proposal; calculates 5-year total cost of occupancy |
| FM_BUNDLING | Configures facility management service bundle; prices by headcount tier |
| NEGOTIATION | Produces talking points; models rent-free vs. TI vs. FM-subsidy trade-offs |
| OUTCOME_PENDING | Awaits client decision |
| WON_CLOSEOUT | Closes out with FM contract attached; sets 90-day check-in |
| LOST_FM_UPSELL | Immediately pivots to standalone FM pitch — "wherever you land, JLL runs the facility" |
| LOGGED | Opportunity archived; pipeline event log complete |

---

## The 10 tools

| Tool | What it does |
|---|---|
| `get_opportunity_state` | Reads the full in-memory record for the current opportunity |
| `update_opportunity_state` | Writes partial updates (requirements, stage, shortlist, …) |
| `search_properties` | Searches the property inventory against validated criteria |
| `get_market_benchmark` | Fetches rent benchmarks, vacancy, and supply data for a submarket |
| `get_competitor_intel` | Returns active competitor bids and risk assessments |
| `score_shortlist` | Scores shortlisted properties across 8 dimensions; lease- and purchase-aware |
| `get_fm_catalog` | Returns the FM service catalog with per-headcount pricing tiers |
| `save_draft_artifact` | Persists a proposal/FM pitch draft (does NOT send it anywhere) |
| `request_human_approval` | Raises an approval request; the agent blocks until a human resolves it |
| `log_pipeline_event` | Appends a timestamped event to the opportunity's pipeline log |

There is **no send tool**. Nothing reaches a client without human action on the approval queue.

---

## Workflow stages — quick reference

```
INTAKE → SHORTLISTING → COMPARISON → PROPOSAL_DRAFTING → FM_BUNDLING
       → NEGOTIATION → OUTCOME_PENDING → WON_CLOSEOUT ──┐
                                       → LOST_FM_UPSELL ─┴→ LOGGED
```

Full transition guards and re-entrancy rules: [`agent/workflow_state_machine.md`](agent/workflow_state_machine.md)

---

## Running the agent

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure provider
cp .env.example .env
# Edit .env: set LLM_PROVIDER=anthropic or deepseek, plus the matching API key

# 3a. Web UI + API (recommended)
uvicorn app.api:app --reload --port 8000
# Open http://127.0.0.1:8000 for the full interactive dashboard

# 3b. CLI
python -m app.cli
# Commands: /new <client>, /state, /approvals, /approve <id>, /events, /quit

# 4. Tests (no API key needed)
python -m pytest tests/ -v
```

---

## Web UI dashboard

The dashboard at `http://127.0.0.1:8000` provides:

- **13-view navigation** — Bid Copilot, Dashboard, Opportunities, Requirements, Property Search, Comparisons, Proposals, Negotiations, FM Services, Win/Loss, Pipeline, Reports, Knowledge Center
- **Run AI Demo** — animated step-by-step simulation of the full agent workflow (bid creation → requirement intake → property search → scoring → market benchmark → competitor intel → proposal draft → approval request → FM upsell) with live tool-call log and output cards
- **+ New Bid wizard** — 4-step structured form: (1) Client details, (2) Location & Space, (3) Commercial terms, (4) FM service selection with live cost estimate
- **Property comparison matrix** — side-by-side comparison of shortlisted properties against 12 criteria
- **FM bundle configurator** — checkbox-driven service selection with live total recalculation
- **Human approval panel** — inline Approve/Reject cards; nothing is sent until approved

All UI logic is in `app/static/app.js` (vanilla JS, no build step).

---

## Extending the agent

**Add a new tool** — define input model in `app/tools/schemas.py`, implement in `app/tools/*.py`, register in `app/tools/registry.py`, add to `TOOL_DEFINITIONS` in `scripts/generate_schemas.py`, run the generator, add a test.

**Add a domain field** — edit `app/domain/models.py`, update services/tools that read it, run `python scripts/generate_schemas.py`, update `agent/system_prompt.md` PRIMARY INTAKE INPUTS if required, add a test.

**Add mock data** — edit `app/data/*.json`, validate against the domain model (`PropertyListing.model_validate(row)`) before committing.

**Swap mock for real integration** — implement the abstract interface in `app/repositories/base.py`, wire it in `app/repositories/instances.py`. No other file needs to change.

See [`CLAUDE.md`](CLAUDE.md) for the full guide and safety rules.

---

## Safety rules (non-negotiable)

- Never fabricate property data, prices, or competitor intel — every factual claim must trace to a tool call.
- Every estimate/inference must be labeled as such.
- Nothing reaches a client without `request_human_approval` — this is structural, not instructional.
- No pricing or contract authority — commercial terms are options to consider, not decisions made.
- Opportunities are isolated; no client's data may appear in another's context.
- On a lost or at-risk bid, the FM upsell pivot is **mandatory** — it is the core commercial logic.

---

## Key files

| Path | Purpose |
|---|---|
| `app/domain/models.py` | Single source of truth for every data shape |
| `app/tools/schemas.py` | Pydantic input models for all 10 tools |
| `agent/tools.json` | GENERATED — LLM tool-use schemas (never hand-edit) |
| `agent/system_prompt.md` | Agent persona, guardrails, primary intake inputs |
| `agent/workflow_state_machine.md` | Stage transition contract |
| `app/orchestrator.py` | Provider-pluggable tool-use loop |
| `app/repositories/instances.py` | Swap mock for real integration here |
| `app/static/app.js` | All dashboard interactivity |
| `scripts/generate_schemas.py` | Regenerates `agent/tools.json` and `agent/memory_schema.json` |
| `CLAUDE.md` | Claude Code guidance — read before editing this codebase |
