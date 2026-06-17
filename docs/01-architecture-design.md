# JLL Bidding & Office Leasing AI Agent — Architecture & Design Document

**Stage 1 of 3** (Design Doc → Agent Spec → Prototype)
**Status:** Draft for review
**Owner:** JLL Bid & Business Development team

---

## 1. Business Context

A client wants to lease office space. Multiple real estate service providers (bidders) — including JLL — compete to win the engagement. JLL's goal is twofold:

1. **Win the primary leasing mandate** by being the most compelling bidder on location, price, terms, and service quality.
2. **Capture secondary revenue regardless of outcome**, by pitching facility management (FM) and workplace support services (pantry, stationery, washroom, electrical, plumbing, general ops) — to the same client even if a competitor wins the lease.

The agent exists to make JLL's bid teams faster, more consistent, and more commercially aggressive across both motions.

## 2. Objectives (from business brief)

The agent must:

1. Understand client requirements (location, budget, seating capacity, facilities, lease duration, etc.)
2. Search and shortlist suitable office spaces
3. Compare market options, competitor offerings, and pricing
4. Prepare competitive bid proposals
5. Recommend bundled value-added FM services to strengthen the proposal
6. Assist with lease negotiation and agreement preparation
7. Identify FM upsell opportunities even when the leasing bid is lost
8. Maximize overall conversion and revenue

## 3. Scope Boundaries (what this agent is / is not)

**In scope:**
- Conversational requirement-gathering with clients/internal bid teams
- Structured shortlisting and comparison logic over property data
- Competitive benchmarking (price, terms, FM bundle) against known/assumed competitor patterns
- Proposal drafting (content generation), not legal execution
- Negotiation *support* (talking points, counter-offer framing, concession trade-offs) — not autonomous deal-making
- Win/loss-triggered FM upsell playbook generation
- Pipeline/opportunity tracking signals for revenue reporting

**Out of scope / requires human sign-off:**
- Final pricing authorization and contract execution
- Legally binding commitments or signatures
- Direct client-facing negotiation without a JLL broker/relationship manager in the loop
- Any data the agent wasn't explicitly given access to (no scraping/inventing live market data)

This boundary matters because leasing deals carry legal and financial risk — the agent is a **decision-support and drafting copilot**, not an autonomous dealmaker. This should be reflected as a hard guardrail in Stage 2 (system prompt) and Stage 3 (human-in-the-loop checkpoints before anything client-facing goes out).

## 4. Primary Users

| User | Need from the agent |
|---|---|
| JLL Bid Manager / Broker | Fast shortlist, competitive intel, proposal draft, negotiation prep |
| JLL Account/Relationship Manager | FM upsell talking points, pipeline visibility, win/loss follow-up |
| (Indirectly) Client | Receives clearer comparisons and faster, more tailored proposals — agent does not interact with the client directly in v1 |

v1 assumption: the agent is an **internal copilot** used by JLL staff, not a client-facing chatbot. This avoids client-data and liability exposure during the early build. (Flag for confirmation — see Open Questions §9.)

## 5. End-to-End Workflow

```
 ┌─────────────────────────┐
 │ 1. Requirement Intake     │  location, budget, headcount/seats, lease term,
 │    (structured interview) │  must-have facilities, move-in date, special needs
 └────────────┬──────────────┘
              ▼
 ┌─────────────────────────┐
 │ 2. Market Search &        │  query property inventory → filter by hard
 │    Shortlisting           │  constraints → rank by fit score
 └────────────┬──────────────┘
              ▼
 ┌─────────────────────────┐
 │ 3. Comparative Analysis   │  price/sq.ft, total occupancy cost, lease terms,
 │    (incl. competitors)    │  amenities, known competitor bid patterns
 └────────────┬──────────────┘
              ▼
 ┌─────────────────────────┐
 │ 4. Bid Proposal Drafting  │  shortlist + pricing + commercial terms +
 │                            │  FM bundle + differentiators → draft proposal
 └────────────┬──────────────┘
              ▼
 ┌─────────────────────────┐
 │ 5. Value-Added Bundling   │  recommend FM services (pantry, stationery,
 │                            │  washroom, electrical, plumbing, ops support)
 │                            │  sized/priced to the deal
 └────────────┬──────────────┘
              ▼
 ┌─────────────────────────┐
 │ 6. Negotiation Support    │  counter-offer framing, concession trade-offs,
 │                            │  what to hold/give on price vs. term vs. FM scope
 └────────────┬──────────────┘
              ▼
 ┌─────────────────────────┐
 │ 7. Outcome Branch          │
 └──────┬─────────────┬───────┘
        │ WON          │ LOST
        ▼              ▼
 ┌─────────────┐  ┌─────────────────────────────┐
 │ Close-out:   │  │ 8. FM Upsell Path:            │
 │ agreement    │  │   client leased elsewhere →   │
 │ prep handoff │  │   pitch standalone FM services│
 └─────────────┘  └─────────────────────────────┘
              ▼ (both paths)
 ┌─────────────────────────┐
 │ 9. Pipeline & Revenue      │  log outcome, FM attach rate, conversion
 │    Tracking                │  metrics for reporting
 └─────────────────────────┘
```

Steps 1–6 happen per opportunity; step 7 branches; step 8 is the key "even-if-we-lose" revenue path called out explicitly in the business brief; step 9 feeds reporting/KPIs.

## 6. Capability Breakdown

### 6.1 Requirement Intake
- Conversational slot-filling: location(s), budget (per sq.ft or total), headcount/seats, lease duration, must-have vs nice-to-have facilities, move-in timeline, industry-specific needs (e.g. trading floor power, lab space).
- Should detect missing/ambiguous inputs and ask targeted follow-ups rather than assuming.

### 6.2 Market Search & Shortlisting
- Filters property inventory against hard constraints (budget ceiling, min seats, location radius).
- Produces a ranked shortlist with a transparent fit score (e.g. weighted: price 40%, location 25%, amenities 20%, availability/move-in fit 15% — weights configurable).
- Flags trade-offs explicitly ("Option B is 8% over budget but cuts commute time by 15 min for 60% of staff").

### 6.3 Comparative & Competitive Analysis
- Side-by-side comparison table: price/sq.ft, total occupancy cost (rent + estimated FM + fit-out), lease flexibility (break clauses, escalation), amenities.
- Competitor positioning: where data exists (past win/loss notes, known market rates), surface how JLL's offer likely compares — clearly labeled as *estimate/inference*, never fabricated as fact.

### 6.4 Bid Proposal Drafting
- Generates a structured proposal draft: executive summary, shortlisted options, recommended option with rationale, commercial terms, FM bundle, differentiators vs. likely competitor angles.
- Always produced as a **draft for human review** — never auto-sent.

### 6.5 Value-Added FM Bundling
- Maps client profile (headcount, building type, industry) to relevant FM services from the catalog: pantry, stationery, washroom, electrical, plumbing, general ops.
- Suggests bundle tiers (e.g. Essential / Standard / Premium) with indicative pricing logic, to strengthen the core leasing bid.

### 6.6 Negotiation Support
- Given client pushback (e.g. "price too high", "need shorter term"), suggests concession options and trade-offs (e.g. trade rent reduction for longer term, or bundle FM services to offset a price gap).
- Provides talking points, not final authority — pricing changes require human approval.

### 6.7 Win/Loss Branch → FM Upsell
- On **loss** of the leasing bid: agent automatically generates a standalone FM services pitch (independent of the lease), tailored to the property/landlord situation if known, to keep JLL in the account.
- On **win**: agent prepares handoff notes for lease/agreement preparation (non-legal drafting support) and still checks for FM upsell beyond what's already bundled.

### 6.8 Pipeline & Revenue Tracking
- Logs each opportunity's stage, outcome, and FM attach (whether FM services were sold alongside or instead of the lease).
- Surfaces KPIs (see §8).

## 7. System Architecture (high level)

```
┌────────────────────────────────────────────────────────────────┐
│                         JLL Bid Agent                              │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  LLM Core (Claude)                                         │    │
│  │  - System prompt / persona / guardrails                    │    │
│  │  - Conversation & workflow state machine                   │    │
│  │  - Tool-use orchestration                                  │    │
│  └───────────────┬─────────────────────────────────┬──────────┘    │
│                  │                                 │                │
│        ┌─────────▼─────────┐             ┌─────────▼─────────┐     │
│        │   Tool Layer        │             │   Memory / State    │     │
│        │  (function calls)   │             │  (per-opportunity)  │     │
│        └─────────┬─────────┘             └─────────────────────┘     │
└──────────────────┼──────────────────────────────────────────────────┘
                    │
   ┌────────────────┼─────────────────────────────────────────┐
   ▼                ▼                       ▼                  ▼
┌────────┐  ┌────────────────┐   ┌──────────────────┐  ┌───────────────┐
│Property │  │ Pricing/Market  │   │ FM Services        │  │ CRM / Pipeline │
│Inventory│  │ Benchmark data  │   │ Catalog & Pricing   │  │ (opportunity   │
│ (DB/API)│  │ (rates, comps)  │   │                     │  │  tracking)     │
└────────┘  └────────────────┘   └──────────────────┘  └───────────────┘
```

- **LLM Core**: Claude, holding the persona/system prompt and orchestrating tool calls (Stage 2 deliverable).
- **Tool layer**: discrete functions the agent can call — `search_properties`, `get_market_benchmark`, `get_fm_catalog`, `draft_proposal`, `log_opportunity`, etc. (defined precisely in Stage 2).
- **Memory/state**: per-opportunity context (client requirements, shortlist, stage, outcome) so the agent doesn't re-ask settled questions across a multi-session engagement.
- **Data sources**: in v1 these are mocked/stubbed (per your instruction — "logic only"); designed so real JLL systems (property DB, CRM e.g. Salesforce, market data feeds) can be swapped in later without changing the agent's reasoning logic.

## 8. Success Metrics / KPIs

| Metric | What it measures |
|---|---|
| Bid win rate | % of leasing bids JLL wins where the agent was used |
| Time-to-proposal | Time from requirement intake to first draft proposal |
| FM attach rate (on win) | % of won leases that also include FM services |
| FM attach rate (on loss) | % of lost leases where JLL still secured FM business |
| Proposal revision cycles | How many human edit rounds a draft needs before client-ready |
| Shortlist acceptance rate | % of agent-shortlisted properties the client actually shows interest in |

## 9. Risks & Guardrails

- **No fabricated data**: agent must never invent property listings, prices, or competitor figures — only reason over data explicitly provided via tools; if data is missing, it asks or flags the gap.
- **Human-in-the-loop**: no proposal, price, or negotiation message goes to a client without JLL staff review/approval in v1.
- **Confidentiality**: client requirements and competitor inferences are sensitive — agent should not leak one client's data into another's context.
- **Estimate labeling**: anything inferred (e.g. "likely competitor pricing") must be clearly flagged as an estimate, not stated as fact.

## 10. Open Questions for You (before Stage 2)

1. **Confirmed: internal copilot, not client-facing** — is that the right v1 scope, or should the agent eventually talk directly to clients?
2. **FM catalog detail**: do you have real tiers/pricing for pantry, stationery, washroom, electrical, plumbing, ops support, or should Stage 3's prototype use placeholder tiers?
3. **Fit-score weights** (§6.2: price/location/amenities/availability) — keep my defaults or do you have JLL's actual scoring methodology?
4. **CRM target**: any specific system (Salesforce, internal tool) the "pipeline tracking" tool should eventually map to, or keep it generic for now?

## 11. Next Steps

- **Stage 2**: Translate §6–§7 into a concrete agent spec — system prompt, persona, full tool/function schemas (JSON), conversation/workflow state logic, and guardrail enforcement — built for the Claude API.
- **Stage 3**: A runnable prototype (chat-style app) wired to Stage 2's spec, using stubbed tool responses (since no real data is available yet) so the end-to-end flow can be demoed and reasoning validated before any real integration work.
