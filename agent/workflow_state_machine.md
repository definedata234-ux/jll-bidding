# Workflow State Machine

Concrete state machine behind the workflow diagram in [01-architecture-design.md §5](../docs/01-architecture-design.md). This is the contract between the system prompt's stage-awareness instructions, the tools in [tools.json](tools.json), and the `stage` field in [memory_schema.json](memory_schema.json). Stage 3's prototype should implement transition guards against this table (even if only loosely enforced at first).

## States

| Stage | Purpose | Typical tools used |
|---|---|---|
| `INTAKE` | Gather client requirements | `update_opportunity_state` |
| `SHORTLISTING` | Search and rank candidate properties | `search_properties`, `score_shortlist`, `update_opportunity_state` |
| `COMPARISON` | Side-by-side + competitive benchmarking | `get_market_benchmark`, `get_competitor_intel`, `update_opportunity_state` |
| `PROPOSAL_DRAFTING` | Draft the bid proposal | `save_draft_artifact` (bid_proposal), `request_human_approval` |
| `FM_BUNDLING` | Recommend FM value-add bundle, fold into proposal | `get_fm_catalog`, `save_draft_artifact` (fm_bundle_recommendation), `update_opportunity_state` |
| `NEGOTIATION` | Support back-and-forth with client | `save_draft_artifact` (negotiation_brief), `request_human_approval` |
| `OUTCOME_PENDING` | Awaiting client decision | `log_pipeline_event` |
| `WON_CLOSEOUT` | Lease won — handoff to agreement prep, check residual FM upsell | `update_opportunity_state`, `log_pipeline_event` |
| `LOST_FM_UPSELL` | Lease lost — pivot to standalone FM services pitch | `get_fm_catalog`, `save_draft_artifact` (fm_upsell_pitch), `request_human_approval` |
| `LOGGED` | Opportunity closed out, fully recorded for reporting | `log_pipeline_event` |

## Transition Table

| From | To | Trigger / Guard Condition |
|---|---|---|
| *(new opportunity)* | `INTAKE` | Opportunity created; `requirements` object initialized (likely empty). |
| `INTAKE` | `SHORTLISTING` | All primary intake inputs present and accepted by `update_opportunity_state`: `transaction_type`, `property_type`, at least one `location`, `budget` (max_amount + correct basis for the transaction type), and `timeline`. For lease deals, `lease_term_months` is additionally required (enforced by the requirements schema itself). If anything is missing or the tool call is rejected as invalid, stay in `INTAKE` and ask the user — do not guess field values to force a transition. |
| `SHORTLISTING` | `COMPARISON` | At least one candidate returned by `search_properties` and scored by `score_shortlist`. If zero candidates match, stay in `SHORTLISTING`, surface the gap, and ask whether to relax constraints. |
| `COMPARISON` | `PROPOSAL_DRAFTING` | User has confirmed (explicitly, in conversation) which shortlisted option(s) to proceed with. Do not auto-advance on the agent's own ranking alone. |
| `PROPOSAL_DRAFTING` | `FM_BUNDLING` | A `bid_proposal` draft has been saved via `save_draft_artifact`. |
| `FM_BUNDLING` | `NEGOTIATION` | An `fm_bundle_recommendation` has been saved and folded into an updated proposal draft (new version saved); `request_human_approval` called for the combined proposal. |
| `NEGOTIATION` | `OUTCOME_PENDING` | Proposal has been approved by a human (tracked outside the agent, e.g. via CRM/manual confirmation back to the agent) and presented to the client. |
| `OUTCOME_PENDING` | `WON_CLOSEOUT` | Outcome recorded as `won` via `update_opportunity_state` + `log_pipeline_event`. |
| `OUTCOME_PENDING` | `LOST_FM_UPSELL` | Outcome recorded as `lost` via `update_opportunity_state` + `log_pipeline_event`. **This transition must always trigger an FM upsell attempt** — see "Win or Not, Find Revenue" principle in the system prompt. |
| `WON_CLOSEOUT` | `LOGGED` | Handoff notes prepared; residual FM upsell (if any, beyond what's bundled) checked and either pitched or explicitly declined. |
| `LOST_FM_UPSELL` | `LOGGED` | FM upsell pitch saved, approval requested, and outcome (pitched/accepted/declined) recorded via `log_pipeline_event`. |

## Guardrail Checkpoints (apply across states)

These are not states themselves, but mandatory checks before specific transitions or actions, regardless of which stage triggers them:

- **Before `PROPOSAL_DRAFTING → FM_BUNDLING`, `FM_BUNDLING → NEGOTIATION`, and any `*_UPSELL` artifact being treated as final**: `request_human_approval` must be called. The agent does not self-certify an artifact as client-ready.
- **Before any property/price/competitor claim in `SHORTLISTING` or `COMPARISON`**: must trace back to a tool call (`search_properties`, `get_market_benchmark`, `get_competitor_intel`). No claim should be sourced purely from the LLM's own reasoning.
- **At every state transition**: call `update_opportunity_state` (to persist `stage`) and `log_pipeline_event` (for reporting). These are two different concerns — state for continuity, log for KPIs — and both should fire together rather than one substituting for the other.

## Re-entrancy / Loops

Real bids aren't strictly linear. The state machine allows backward moves:

- `COMPARISON → SHORTLISTING`: client requirements change mid-process (e.g. budget shifts) — re-run search/scoring.
- `NEGOTIATION → PROPOSAL_DRAFTING`: client counter-offer requires a revised proposal version (increment `version` in `save_draft_artifact`).
- `OUTCOME_PENDING → NEGOTIATION`: client comes back with further negotiation before a final decision.

The agent should treat the stage as the user's actual situation, not a one-way checklist — always reconcile via `get_opportunity_state` rather than assuming forward progress.

## Diagram

```
INTAKE → SHORTLISTING → COMPARISON → PROPOSAL_DRAFTING → FM_BUNDLING → NEGOTIATION → OUTCOME_PENDING
   ↑___________|              ↑_________________________________________|              │
                                                                            ┌─────────────┴─────────────┐
                                                                            ▼                            ▼
                                                                      WON_CLOSEOUT               LOST_FM_UPSELL
                                                                            │                            │
                                                                            └──────────→ LOGGED ←─────────┘
```
