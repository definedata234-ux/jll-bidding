# Stage 2: Agent Spec — Overview

**Status:** Draft for review
**Builds on:** [01-architecture-design.md](01-architecture-design.md)
**Next stage:** Stage 3 — runnable prototype wired to this spec with stubbed tool responses

This stage turns the architecture doc's §6–§7 into a concrete, loadable agent spec for the Claude API. Four artifacts, all under [agent/](../agent/):

| File | What it is |
|---|---|
| [system_prompt.md](../agent/system_prompt.md) | The `system` block: persona, non-negotiable guardrails, workflow awareness, the "win or not, find revenue" principle, tool usage rules, communication style |
| [tools.json](../agent/tools.json) | 10 tool definitions in Claude tool-use JSON Schema format, ready to pass as the `tools` array |
| [workflow_state_machine.md](../agent/workflow_state_machine.md) | The 10-state machine (`INTAKE` → ... → `LOGGED`), transition guards, and cross-cutting guardrail checkpoints |
| [memory_schema.json](../agent/memory_schema.json) | JSON Schema for the per-opportunity record that `get_opportunity_state`/`update_opportunity_state` read and write |

## How the four pieces fit together

```
 system_prompt.md  ──instructs──▶  "call get_opportunity_state, know your stage,
                                     never fabricate, always gate on human approval"
        │
        ▼
 tools.json  ───────defines─────▶  the only ways the agent can touch data or
                                     leave a trace (search, score, draft, log,
                                     request approval) — no "send to client" tool
                                     exists, by design
        │
        ▼
 workflow_state_machine.md ─────▶  the contract for *which* tools fire *when*,
                                     and the guard conditions before advancing
        │
        ▼
 memory_schema.json ────────────▶  the shape of state that persists across
                                     turns/sessions, keyed by opportunity_id
```

## Design decisions worth flagging

1. **10 tools, not more.** Drafting (proposals, negotiation briefs, FM pitches) is left to the LLM's own generation — `save_draft_artifact` just persists it. I didn't add a separate "generate_proposal" tool because forcing generation through a tool call would add no value (it's not a deterministic computation) and would only obscure the text from you in this review. `score_shortlist`, by contrast, *is* a tool because ranking should be deterministic and auditable, not LLM arithmetic.
2. **No "send" tool exists, anywhere.** This is the structural backstop for the human-in-the-loop guardrail from Stage 1 — the agent literally cannot deliver anything to a client even if instructions were ignored. `request_human_approval` is the only path from "draft" to "client-ready," and that approval is tracked outside the agent's own tool surface (e.g. a human confirms back in conversation, or via whatever approval workflow Stage 3 stubs).
3. **`get_competitor_intel` is separate from `get_market_benchmark`**, even though both could plausibly be one tool, specifically so the confidence/estimate-labeling guardrail has a single, obvious enforcement point — every competitor-intel item carries a mandatory `confidence` field.
4. **The state machine allows backward transitions** (§"Re-entrancy / Loops" in workflow_state_machine.md). Real bids loop — budgets change, clients counter-offer twice. The machine isn't a one-way checklist; the agent is told to reconcile against `get_opportunity_state` rather than assume forward progress.
5. **Memory is opportunity-scoped, not client-scoped or global**, to enforce the confidentiality guardrail from Stage 1 — there's no field or tool that aggregates across opportunities, so cross-client leakage would require the agent to actively misuse data, not just retrieve it normally.

## Carried-over open questions (from Stage 1 §10)

Still unanswered, and now slightly more concrete now that schemas exist:

1. Internal-copilot scope — confirmed for this spec (no client-facing tool exists).
2. FM catalog tiers/pricing — `get_fm_catalog`'s response shape is defined (`memory_schema.json#/fm_bundle`), but real tier names/pricing vs. Stage 3 placeholders still need your input.
3. Fit-score weights — defaults coded into `score_shortlist`'s description (price 0.40 / location 0.25 / amenities 0.20 / availability 0.15) per Stage 1's draft; confirm or override.
4. CRM target — `log_pipeline_event`/`pipeline_events` are generic; no system-specific mapping yet.

## Next: Stage 3

A runnable prototype (chat-style app) that loads `system_prompt.md` + `tools.json` against the Claude API, implements the 10 tools with stubbed/mock responses (no real data sources per your "logic only" decision), and persists `memory_schema.json`-shaped state in-memory or to a local JSON file — so the full INTAKE → ... → LOGGED flow, including the loss → FM upsell pivot, can be exercised end-to-end and reviewed before any real integration work begins.
