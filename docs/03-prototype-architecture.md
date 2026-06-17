# Stage 3: Prototype Architecture

**Status:** Built and tested
**Builds on:** [01-architecture-design.md](01-architecture-design.md), [02-agent-spec-overview.md](02-agent-spec-overview.md)
**Code:** [app/](../app/), [agent/](../agent/), [scenarios/](../scenarios/), [tests/](../tests/)

This doc covers the architecture/structure/flow side of Stage 3's deliverables. Run instructions live in [README.md](../README.md) (kept there since that's where you'd actually look first when picking this up).

## 1. Prototype Architecture

```
                          ┌──────────────────────────┐
                          │   JLL staff (internal)     │
                          └─────────────┬──────────────┘
                  ┌────────────────────┼────────────────────┐
                  ▼                                          ▼
        CLI (app/cli.py)                          FastAPI (app/api.py)
        interactive REPL,                          /opportunities, /chat,
        /approve, /state, /events                   /approvals/.../decision
                  └────────────────────┬────────────────────┘
                                        ▼
                    BidCopilotOrchestrator (app/orchestrator.py)
                    - loads agent/system_prompt.md (parsed verbatim)
                    - loads agent/tools.json (10 tool schemas)
                    - runs the Claude Messages API tool-use loop
                    - persists chat history via ConversationStore
                                        │
                              dispatch(tool_name, input)
                                        ▼
                         app/tools/registry.py
            ┌──────────────┬──────────────┬──────────────┬──────────────┐
            ▼              ▼              ▼              ▼              ▼
   property_tools.py   fm_tools.py   state_tools.py  workflow_tools.py
   search_properties    get_fm_       get/update_     save_draft_artifact
   score_shortlist      catalog       opportunity_    request_human_approval
   get_market_                        state           log_pipeline_event
   benchmark
   get_competitor_intel
            │              │              │              │
            └──────┬───────┴──────┬───────┴──────┬───────┘
                   ▼               ▼              ▼
          app/data/*.json   OpportunityStore   (same store)
          (mock inventory,   (app/state/store.py)
           benchmarks,       JSON file per opportunity,
           competitor intel, shaped like agent/memory_schema.json,
           FM catalog)       under app/storage/opportunities/
```

Two things worth calling out structurally:

- **The orchestrator is the only thing that talks to Claude.** Every tool function is plain, network-free Python operating on local JSON. This means the tool layer is fully testable (and tested — see §9) without an API key or live model call, while the orchestration layer is isolated and swappable (e.g. if you later move to a different model or add streaming).
- **No tool can deliver anything to a client.** `save_draft_artifact` persists; `request_human_approval` requests. The only way an artifact's status changes from `draft`/`pending` is a human action via `OpportunityStore.resolve_approval`, invoked from the CLI's `/approve` command or the API's approval-decision endpoint — both outside the LLM's own tool surface. This is Stage 2's guardrail made concrete, not just instructed.

## 2. Folder/Project Structure

See the tree in [README.md](../README.md#project-structure) — not duplicated here to avoid the two going out of sync.

## 3. Backend Logic / Orchestration Flow

Per-turn flow in `BidCopilotOrchestrator.chat()`:

1. Load the opportunity's prior chat history (`ConversationStore`); confirm the opportunity exists (fails loudly if not — no silent auto-create mid-chat).
2. Append the new user message; call `Anthropic.messages.create()` with `system` = the parsed system prompt, `tools` = the 10 schemas, `messages` = history.
3. If `stop_reason == "tool_use"`: for every `tool_use` block in the response, call `dispatch()`, wrap the result (or an `is_error` block, on exception) as a `tool_result`, append both the assistant turn and the tool results to history, and loop back to step 2.
4. Loop capped at `MAX_TOOL_ITERATIONS` (default 8) to guard against runaway tool-call chains.
5. Once the model returns plain text (`stop_reason != "tool_use"`), persist history and return the text to the caller.

This directly implements the workflow contract in [workflow_state_machine.md](../agent/workflow_state_machine.md) — the *state machine itself* lives in the data (the `stage` field, updated via the `update_opportunity_state` tool) and in the system prompt's instructions to respect it; the orchestrator doesn't hard-code stage transitions, by design, so the agent can handle the documented backward loops (re-negotiation, requirement changes) without code changes.

**Approval flow specifically** (`app/approvals.py`): when a human approves/rejects via CLI or API, `OpportunityStore.resolve_approval()` updates the approval record and the matching draft's status, and a synthetic `[HUMAN REVIEWER NOTE]` user-role message is appended to the conversation so the agent is explicitly told the outcome on its next turn — it isn't expected to infer approval from silence or guess via a speculative `get_opportunity_state` call.

## 4. Mock Datasets

All under [app/data/](../app/data/):

| File | Contents |
|---|---|
| `properties.json` | 12 office properties across Austin, Chicago, Denver, Atlanta, Seattle — price/sqft, square footage, seat capacity, lease term options, availability, amenities |
| `market_benchmarks.json` | Per-city/property-type average $/sqft, escalation %, typical term, source, confidence |
| `competitor_intel.json` | Per-city competitor positioning notes (CBRE, Cushman & Wakefield, Newmark), each with a mandatory `confidence` field |
| `fm_catalog.json` | 6 FM categories (pantry, stationery, washroom, electrical, plumbing, general_ops) × 3 tiers (Essential/Standard/Premium), priced per-seat-per-month |

These are placeholders per the agreed Stage 1/2 open-question defaults (FM pricing tiers placeholder, generic structure) — swapping in real JLL data later means replacing these files' contents; no tool/orchestrator code changes are needed since the tool functions just read whatever's in `app/data/`.

## 5. Sample Conversations

[scenarios/scenario_won.md](../scenarios/scenario_won.md) and [scenarios/scenario_lost_fm_upsell.md](../scenarios/scenario_lost_fm_upsell.md) — both built around real tool outputs (actually executed against the mock data, not hand-written numbers), covering the full `INTAKE → ... → LOGGED` flow including the mandatory `OUTCOME_PENDING → LOST_FM_UPSELL` pivot when a bid is lost.

## 6. API Endpoints / App Flow

Two interchangeable front-ends over the same orchestrator/store:

- **CLI** (`python -m app.cli`): `/new`, `/switch`, `/list`, `/state`, `/approvals`, `/approve`, `/reject`, `/events`, `/quit`, plus free-text chat.
- **FastAPI** (`uvicorn app.api:app`): see the endpoint table in [README.md](../README.md#running-the-api-live-chat-requires-api-key). Both read/write the same `app/storage/` files, so a CLI-started opportunity can be resumed via the API and vice versa.

## 7. Instructions to Run Locally

See [README.md § Setup](../README.md#setup) onward — kept there as the single canonical run-book.

## 8. Human Approval Checkpoints

Concretely wired at:
- After every `save_draft_artifact` call for `bid_proposal` (v1 and the FM-bundled v2), `negotiation_brief`, and `fm_upsell_pitch` — the system prompt instructs `request_human_approval` to follow immediately.
- Pricing/concession changes during `NEGOTIATION` are framed as "options," with `request_human_approval` required before any could be considered final (per the system prompt's "no pricing authority" guardrail).
- Enforcement is structural, not just instructional: see §1 above.

## 9. Test Coverage

`tests/test_scenario_won.py` and `tests/test_scenario_lost_fm_upsell.py` drive the tool layer and `OpportunityStore` directly (bypassing the LLM, so they run with no API key) through the entire state machine for both outcomes. Both currently pass:

```
$ python -m pytest tests/ -v
tests/test_scenario_lost_fm_upsell.py::test_lost_deal_triggers_fm_upsell PASSED
tests/test_scenario_won.py::test_won_deal_end_to_end PASSED
2 passed in 1.15s
```

One real bug was caught and fixed while writing these: the original lost-deal test's budget ceiling ($45/sqft) had zero matching Chicago properties with 24x7 access in the mock data, correctly producing an empty shortlist — adjusted the test's budget assumption to $50/sqft to reflect a winnable-but-lost scenario rather than a no-data scenario.

FastAPI endpoints were additionally smoke-tested via `TestClient` (create → get → list → approvals → events → health), confirming the HTTP layer wires to the same store correctly.

## Carried-over open items

FM pricing tiers remain placeholders (per your Stage-3-kickoff instruction to use placeholders for now) and there's still no real CRM mapping — both noted as "Not real yet" in [README.md](../README.md#whats-mocked-vs-real) rather than repeated here.
