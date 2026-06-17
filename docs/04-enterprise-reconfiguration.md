# Stage 4: Enterprise Reconfiguration

**Status:** Built and tested
**Builds on:** Stages 1–3 ([01](01-architecture-design.md), [02](02-agent-spec-overview.md), [03](03-prototype-architecture.md))

## Why this stage exists

Feedback after Stage 3: the agent's intake was too narrow (no square footage, no property type, no purchase support, no zoning), and the codebase needed to meet a higher engineering bar — referencing the standard set by the Report Rationalizer project (TypeScript/React/Express, Zod validation, Pino logging, security middleware, deterministic business logic).

Two scoping decisions were made explicit before starting, because "production-grade, enterprise-level" is otherwise ambiguous enough to justify wildly different amounts of work:

1. **Stack stays Python/FastAPI.** Rather than a TypeScript rewrite, the engineering rigor (validation, logging, layering, tests) was raised within the existing stack.
2. **Data stays mocked, but enterprise-structured.** Real property listings, purchase transaction data, and zoning lookups still aren't available. Mock data was expanded and the data-access layer was rebuilt behind repository interfaces so a real integration later is a wiring change, not a rewrite.
3. **No new infrastructure.** No database, no auth — this is still a single-tenant internal tool. JSON-file storage remains, now with full validation in front of every read/write.

## What changed

### 1. New primary intake inputs

The requirements schema now requires, for every opportunity:

| Field | Notes |
|---|---|
| `transaction_type` | `lease` or `purchase` — determines which other fields apply |
| `property_type` | office / retail / industrial / warehouse / mixed_use / land |
| `locations` | at least one, priority-ordered |
| `budget` | `max_amount` (required) + optional `min_amount`, in a basis matching transaction_type |
| `timeline` | `target_date` (move-in or closing) + optional `decision_deadline` + flexibility |

Plus, captured when relevant: `square_footage_min/max`, `seats`, `lease_term_months` (lease only, enforced), `zoning_classifications`, `must_have_facilities`/`nice_to_have_facilities`, `industry`, `special_needs`.

This directly answers the brief: location, square footage, timeline, budget range, and property type are now structurally required primary inputs, not optional context; transaction type (lease/purchase) and zoning are real filters all the way through search and scoring, not just labels.

### 2. Domain models replace untyped dicts

`app/domain/models.py` defines every shape in the system as a Pydantic model — `Requirements`, `PropertyListing`, `ScoredProperty`, `OpportunityRecord`, etc. — with cross-field validation (e.g. a lease requires `lease_term_months`; a purchase's budget basis can't be a per-sqft lease rate; `square_footage_min` can't exceed `square_footage_max`). This is the actual fix for the bug class found during DeepSeek testing in Stage 3, where the agent invented plausible-but-wrong field names because nothing actually constrained the shape it was given.

### 3. Generated, not hand-maintained, agent spec

`agent/tools.json` and `agent/memory_schema.json` are now **generated** from those Pydantic models via `python scripts/generate_schemas.py` (see the file header in both — they say so). The agent-facing schema and the runtime validation can no longer silently drift apart, because they come from the same source.

### 4. Layered architecture

```
tools/      (LLM-facing adapters — parse input, call a service, return JSON)
   ↓
services/   (business logic — search, scoring, FM pricing; transaction-type branching lives here)
   ↓
repositories/  (data access interfaces; mock.py is the only implementation today)
   ↓
data/*.json (mock inventory, benchmarks, competitor intel, FM catalog)
```

Swapping in a real listings feed, a zoning GIS lookup, or a live market-data API later means writing a new class against `app/repositories/base.py`'s interfaces and changing one assignment in `app/repositories/instances.py` — not touching scoring logic, tool code, or the agent spec.

### 5. Enterprise rigor in the API layer

- **Structured logging** (`structlog`, JSON lines) — every HTTP request and every tool dispatch is logged with a request ID, duration, and outcome.
- **Rate limiting** (`slowapi`) — global default (60/min) plus a stricter limit on `/chat` (15/min), the expensive LLM-calling endpoint. Verified live: request #16 within a minute gets a 429.
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` on every response.
- **Consistent error envelope** — `{"error": {"code", "message", "details"}}` for every failure mode (404 not-found, 400 bad request, 422 validation, 429 rate-limited, 500 unexpected), instead of ad hoc `HTTPException` strings. Unexpected exceptions are logged with full detail server-side and never leak internals to the client.

### 6. Mock data expansion

`app/data/properties.json` grew from 12 to 15 listings, now including `property_type`, `zoning_classification`, `transaction_types_available`, and (where applicable) purchase economics (`purchase_price_total`, `purchase_price_per_sqft`, `cap_rate_pct`) alongside lease economics. Three new listings specifically exercise the new dimensions: a dual lease+purchase office (Austin), a purchase-only industrial property (Chicago), and a retail listing (Denver). `market_benchmarks.json` now benchmarks lease and purchase separately per location/property type.

## What this does NOT include (explicitly out of scope per the scoping decision)

- Real property/zoning/purchase-transaction data sources — still mocked, now just structured to swap in cleanly.
- A real database — still JSON files, now fully Pydantic-validated on every read/write.
- Authentication/authorization — still a single-tenant internal tool.
- Containerization/CI — not requested at this stage.

## Verification

- 13/13 automated tests pass: the original won/lost-with-FM-upsell scenarios (updated to the new schema), a new end-to-end **purchase**-transaction scenario, and a new validation-rules suite proving the domain model actually rejects malformed data (wrong basis for transaction type, missing lease term, inverted budget/square-footage ranges, invalid enum values) at both the model level and the tool-dispatch boundary.
- Rate limiting, security headers, and the error envelope were verified live via FastAPI's TestClient (15 successful requests then a confirmed 429; headers present on every response; structured error bodies for 404/400/422).
- The full chat flow was re-verified live against DeepSeek after this reconfiguration (see README's "what's mocked vs real" section) — fit-score values continue to match hand-computed expected results against the new mock dataset.
