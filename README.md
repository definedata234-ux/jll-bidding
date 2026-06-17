# JLL Bid & Leasing Copilot — Prototype (Stage 4: Enterprise Reconfiguration)

An internal AI copilot for JLL's commercial real estate bid process — **lease or purchase** — covering requirement intake, property shortlisting, competitive analysis, bid proposal drafting, FM (facility management) bundling, negotiation support, and — critically — an automatic pivot to a standalone FM services upsell pitch whenever a bid is lost.

This is a **prototype with mocked data only**. No real property inventory, CRM, zoning registry, or market-data integration exists yet — see [docs/01-architecture-design.md](docs/01-architecture-design.md) and [docs/04-enterprise-reconfiguration.md](docs/04-enterprise-reconfiguration.md) for how real systems would plug in later, and why mocked-but-enterprise-structured was the deliberate choice for this stage.

## Project structure

```
JLL-Bidding-Agent/
├── docs/                                  Design docs (Stage 1–4)
│   ├── 01-architecture-design.md
│   ├── 02-agent-spec-overview.md
│   ├── 03-prototype-architecture.md
│   └── 04-enterprise-reconfiguration.md
├── agent/                                 Agent spec (loaded at runtime)
│   ├── system_prompt.md                   Persona + guardrails + primary-intake-inputs (verbatim block parsed by app/config.py)
│   ├── tools.json                         GENERATED — 10 tool-use schemas (run scripts/generate_schemas.py after model changes)
│   ├── workflow_state_machine.md          10-stage state machine + transition guards
│   └── memory_schema.json                 GENERATED — per-opportunity JSON Schema
├── scripts/
│   └── generate_schemas.py                Generates the two files above FROM app/domain + app/tools/schemas.py
├── app/
│   ├── config.py                          Paths, env vars, provider selection, system-prompt/tool loaders
│   ├── logging_config.py                  Structured (structlog) JSON logging setup
│   ├── orchestrator.py                    Provider-pluggable tool-use loop (Claude or DeepSeek)
│   ├── approvals.py                       Human-approval resolution (shared by CLI + API)
│   ├── cli.py                             Interactive terminal chat client
│   ├── api.py                             FastAPI HTTP surface — rate limiting, security headers, structured errors
│   ├── domain/                            Pydantic models — the single source of truth for every data shape
│   │   ├── models.py                      Requirements, PropertyListing, ScoredProperty, OpportunityRecord, etc.
│   │   └── queries.py                     PropertySearchCriteria (transient query DTO)
│   ├── repositories/                      Data-access interfaces + mock implementations
│   │   ├── base.py                        Abstract PropertyRepository / MarketBenchmarkRepository / etc.
│   │   ├── mock.py                        JSON-file-backed implementations (the only ones today)
│   │   └── instances.py                   Default singleton wiring — swap a mock for a real one here
│   ├── services/                          Business logic (search/scoring/FM pricing), depends only on repository interfaces
│   │   ├── property_service.py            Transaction-type-aware scoring (lease vs purchase)
│   │   ├── market_service.py
│   │   └── fm_service.py
│   ├── tools/                             LLM-facing adapters — parse input (Pydantic), call a service, return JSON
│   │   ├── schemas.py                     One Pydantic input model per tool — source for agent/tools.json
│   │   ├── property_tools.py / fm_tools.py / state_tools.py / workflow_tools.py
│   │   └── registry.py                    dispatch() + per-call structured logging
│   ├── state/
│   │   ├── store.py                       OpportunityStore — validates every read/write against OpportunityRecord
│   │   └── conversation_store.py          Chat transcript persistence per opportunity
│   ├── data/                              Mock datasets (properties, market benchmarks, competitor intel, FM catalog)
│   └── storage/                           Runtime JSON files (opportunities + conversations) — created on first run
├── scenarios/                             Sample end-to-end conversation transcripts
├── tests/                                 13 automated tests (no API key needed)
│   ├── test_scenario_won.py / test_scenario_lost_fm_upsell.py / test_scenario_purchase.py
│   └── test_domain_validation.py
├── requirements.txt
└── .env.example
```

## How it fits together

```
 You (JLL staff) ──chat──▶ CLI (app/cli.py)  or  API (app/api.py)
                                  │
                                  ▼
                BidCopilotOrchestrator (app/orchestrator.py)
              loads agent/system_prompt.md + agent/tools.json
                 drives the Claude OR DeepSeek tool-use loop
                                  │
                          dispatches tool calls
                                  ▼
                  app/tools/* (10 tools, Pydantic-validated)
                                  │
                          calls into a service
                                  ▼
        app/services/* (search, scoring, FM pricing — transaction-
                 type-aware business logic, no data access)
                                  │
                       calls into a repository interface
                                  ▼
       app/repositories/mock.py (the only implementation today,
              JSON-backed; swap via repositories/instances.py)
                                  │
                                  ▼
                OpportunityStore (app/state/store.py) — one JSON
                file per opportunity, fully Pydantic-validated
```

There is **no tool that sends anything to a client**. `save_draft_artifact` only persists drafts; `request_human_approval` raises a request that a human resolves via `/approve` (CLI), the approvals API endpoint, or the web UI's approval buttons — outside the LLM's own tool surface entirely.

## Setup

1. **Python 3.10+** required.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your key:
   ```
   cp .env.example .env
   ```
   Pick a provider:
   ```
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-...
   ```
   or
   ```
   LLM_PROVIDER=deepseek
   DEEPSEEK_API_KEY=sk-...
   ```
   (Only needed for live chat via `cli.py`/`api.py`. The automated tests in `tests/` don't call any LLM — they exercise the tool/service/repository layers directly — so they run with no API key at all.)

4. If you ever change `app/domain/models.py` or `app/tools/schemas.py`, regenerate the agent spec:
   ```
   python scripts/generate_schemas.py
   ```

## Running the automated tests (no API key needed)

```
cd JLL-Bidding-Agent
python -m pytest tests/ -v
```

13 tests: end-to-end **lease-won**, **lease-lost-with-FM-upsell**, and **purchase-won** scenarios against the real service/repository layers and mock data, plus a domain-validation suite proving malformed requirements (wrong budget basis for the transaction type, missing lease term, inverted ranges, invalid enums) are actually rejected — both at the model level and at the tool-dispatch boundary an LLM would actually go through.

## Running the interactive CLI (live chat, requires API key)

```
cd JLL-Bidding-Agent
python -m app.cli
```

```
/new Acme Robotics          # creates an opportunity, prints its ID
We need to lease office space in Austin or Denver, budget up to $40/sqft,
140 seats, 36-month term, move-in by end of September 2026...
/state                       # inspect the full memory record
/approvals                   # list pending approval requests
/approve APR-XXXXXX           # approve as the human reviewer
/events                       # view the pipeline event log
/quit
```

## Running the API + web UI (live chat, requires API key)

```
cd JLL-Bidding-Agent
uvicorn app.api:app --reload --port 8000
```

Open `http://127.0.0.1:8000` for the branded chat UI, or `http://127.0.0.1:8000/docs` for interactive API docs.

| Method | Path | Purpose |
|---|---|---|
| POST | `/opportunities` | Create a new opportunity (`{"client_name": "..."}`) |
| GET | `/opportunities` | List opportunity IDs |
| GET | `/opportunities/{id}` | Full memory record |
| POST | `/opportunities/{id}/chat` | Send a chat message, get the agent's reply (rate-limited: 15/min) |
| GET | `/opportunities/{id}/approvals` | List approval requests |
| POST | `/opportunities/{id}/approvals/{approval_id}/decision` | Approve/reject (`{"decision": "approve", "reviewer": "..."}`) |
| GET | `/opportunities/{id}/events` | Pipeline event log |
| GET | `/healthz` | Health check (also reports active LLM provider) |

All endpoints return a consistent error envelope on failure: `{"error": {"code", "message", "details"}}`.

## Transaction types & primary inputs

Every opportunity's requirements now require: `transaction_type` (lease or purchase), `property_type`, `locations`, a `budget` range (basis depends on transaction type), and a tentative `timeline`. Square footage, seats, lease term (lease only), zoning classifications, and facility preferences are captured as they become known. See [docs/04-enterprise-reconfiguration.md](docs/04-enterprise-reconfiguration.md) for the full schema and rationale.

## What's mocked vs. real

| Layer | Status |
|---|---|
| Property inventory, market benchmarks, competitor intel, FM catalog | **Mocked** — static JSON in `app/data/`, behind repository interfaces so a real source is a wiring change |
| Fit-scoring math (lease- and purchase-aware), search filtering, FM pricing scaling | **Real** — deterministic Python in `app/services/`, covered by tests |
| Domain validation (cross-field rules: lease needs a term, purchase needs a purchase-basis budget, etc.) | **Real** — Pydantic models, covered by tests |
| State machine, memory persistence, approval gating | **Real** — JSON-file-backed, fully schema-validated on every read/write |
| LLM tool-use orchestration | **Real** — works against live Anthropic or DeepSeek APIs |
| Structured logging, rate limiting, security headers, error envelope | **Real** — verified live (see docs/04) |
| CRM integration | **Not built** — `log_pipeline_event`/`pipeline_events` are generic, ready to map to a real CRM later |
| Auth, real database, containerization | **Not built** — explicitly out of scope for this stage (still single-tenant, local-prototype) |

## Known limitations (by design, for this stage)

- Single-process, file-backed storage — fine for a demo, not for concurrent multi-user production use.
- No authentication/authorization on the API.
- FM pricing tiers and zoning/purchase mock data are placeholders, not JLL's real rate card or listings.
- Switching `LLM_PROVIDER` mid-opportunity breaks that opportunity's stored chat history (Claude and DeepSeek use incompatible message-history shapes) — switch providers between opportunities, not within one.
- The orchestrator's tool-call loop caps at `MAX_TOOL_ITERATIONS` (default 8) per turn as a runaway-loop guard; very complex multi-tool turns may need this raised.
