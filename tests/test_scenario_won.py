"""
Scenario test: end-to-end WON deal (lease transaction).

Drives the tool layer and OpportunityStore directly (bypassing the LLM)
to prove the workflow's business logic, state machine fields, and
human-approval gating actually work — independent of whether a live LLM
API key is available. This is what a real conversation, mediated by the
orchestrator, would ultimately cause to happen in storage.
"""
from app.state import OpportunityStore
from app.tools.fm_tools import get_fm_catalog
from app.tools.property_tools import (
    get_competitor_intel,
    get_market_benchmark,
    score_shortlist,
    search_properties,
)
from app.tools.workflow_tools import log_pipeline_event, request_human_approval, save_draft_artifact


def test_won_deal_end_to_end(tmp_path):
    store = OpportunityStore(storage_dir=tmp_path)
    record = store.create("Acme Robotics")
    opp_id = record["opportunity_id"]
    assert record["stage"] == "INTAKE"

    # --- 1. INTAKE -------------------------------------------------------
    store.update(
        opp_id,
        {
            "requirements": {
                "transaction_type": "lease",
                "property_type": "office",
                "locations": ["Austin", "Denver"],
                "budget": {"max_amount": 40, "currency": "USD", "basis": "per_sqft"},
                "timeline": {"target_date": "2026-09-30"},
                "seats": 140,
                "lease_term_months": 36,
                "must_have_facilities": ["parking", "24x7_access"],
                "nice_to_have_facilities": ["conference_center"],
                "industry": "robotics",
            }
        },
        reason="captured client requirements",
    )
    store.update(opp_id, {"stage": "SHORTLISTING"}, reason="requirements complete, ready to search")

    # --- 2. SHORTLISTING ---------------------------------------------------
    search_result = search_properties(
        {
            "locations": ["Austin", "Denver"],
            "transaction_type": "lease",
            "budget": {"max_amount": 40, "basis": "per_sqft"},
            "min_seats": 140,
            "lease_term_months_min": 36,
            "must_have_facilities": ["parking", "24x7_access"],
            "needed_by": "2026-09-30",
        },
        store,
    )
    assert search_result["count"] > 0, "expected at least one matching mock property"

    scored = score_shortlist({"opportunity_id": opp_id, "candidates": search_result["candidates"]}, store)
    assert scored["ranked"], "expected at least one ranked candidate"
    assert scored["weights_used"] == {"price": 0.40, "location": 0.25, "amenities": 0.20, "availability": 0.15}
    top = scored["ranked"][0]
    assert top["name"] == "Riverside Commons"
    assert top["fit_score"] == 0.712  # known-correct value, verified by hand against the mock data
    # Ranking should be sorted descending by fit_score.
    assert all(scored["ranked"][i]["fit_score"] >= scored["ranked"][i + 1]["fit_score"] for i in range(len(scored["ranked"]) - 1))

    store.update(opp_id, {"shortlist": scored["ranked"], "stage": "COMPARISON"}, reason="shortlist scored")

    # --- 3. COMPARISON ------------------------------------------------------
    benchmark = get_market_benchmark({"location": top["location"], "property_type": "office", "transaction_type": "lease"}, store)
    assert benchmark["found"]
    intel = get_competitor_intel({"location": top["location"]}, store)

    store.update(
        opp_id,
        {"market_benchmark": benchmark, "competitor_intel": intel["items"]},
        reason="comparison and competitive benchmarking complete",
    )
    # Client confirms which option to proceed with -> advance.
    store.update(opp_id, {"stage": "PROPOSAL_DRAFTING"}, reason="client confirmed top-ranked option")

    # --- 4. PROPOSAL_DRAFTING (+ approval gate) ------------------------------
    draft_v1 = save_draft_artifact(
        {"opportunity_id": opp_id, "artifact_type": "bid_proposal", "content": f"Draft proposal for {top['name']}."},
        store,
    )
    assert draft_v1["artifact"]["version"] == 1
    assert draft_v1["artifact"]["status"] == "draft"

    approval_v1 = request_human_approval(
        {"opportunity_id": opp_id, "artifact_type": "bid_proposal", "summary": "Review v1 bid proposal"}, store
    )
    assert approval_v1["status"] == "pending_approval"

    # A human (bid manager) approves it outside the LLM's tool surface.
    decided_v1 = store.resolve_approval(opp_id, approval_v1["approval_id"], "approve", reviewer="bid-manager")
    assert decided_v1["status"] == "approved"

    store.update(opp_id, {"stage": "FM_BUNDLING"}, reason="proposal v1 approved")

    # --- 5. FM_BUNDLING -------------------------------------------------------
    fm = get_fm_catalog({"headcount": 140, "service_categories": ["pantry", "general_ops"]}, store)
    assert set(fm["categories"]) == {"pantry", "general_ops"}

    fm_bundle = {
        "tier": "standard",
        "services": [
            {"category": "pantry", "description": fm["categories"]["pantry"]["standard"]["description"], "indicative_price": fm["categories"]["pantry"]["standard"]["indicative_monthly_total"]},
            {"category": "general_ops", "description": fm["categories"]["general_ops"]["standard"]["description"], "indicative_price": fm["categories"]["general_ops"]["standard"]["indicative_monthly_total"]},
        ],
        "indicative_total_price": fm["categories"]["pantry"]["standard"]["indicative_monthly_total"]
        + fm["categories"]["general_ops"]["standard"]["indicative_monthly_total"],
        "rationale": "Standard tier sized to 140 seats, strengthens the core leasing bid.",
    }
    store.update(opp_id, {"fm_bundle": fm_bundle}, reason="FM bundle recommendation finalized")

    draft_v2 = save_draft_artifact(
        {"opportunity_id": opp_id, "artifact_type": "bid_proposal", "content": "Proposal v2, now including FM bundle."},
        store,
    )
    assert draft_v2["artifact"]["version"] == 2

    approval_v2 = request_human_approval(
        {"opportunity_id": opp_id, "artifact_type": "bid_proposal", "summary": "Review v2 with FM bundle folded in"}, store
    )
    store.resolve_approval(opp_id, approval_v2["approval_id"], "approve", reviewer="bid-manager")
    store.update(opp_id, {"stage": "NEGOTIATION"}, reason="combined proposal approved")

    # --- 6. NEGOTIATION ----------------------------------------------------
    log_pipeline_event({"opportunity_id": opp_id, "stage": "NEGOTIATION", "event": "proposal v2 presented to client"}, store)
    store.update(opp_id, {"stage": "OUTCOME_PENDING"}, reason="awaiting client decision")

    # --- 7. OUTCOME: WON ------------------------------------------------------
    store.update(
        opp_id,
        {
            "outcome": {"result": "won", "decided_at": "2026-10-01T00:00:00Z", "reason": "best price + FM bundle"},
            "stage": "WON_CLOSEOUT",
        },
        reason="client selected JLL",
    )
    log_pipeline_event(
        {"opportunity_id": opp_id, "stage": "WON_CLOSEOUT", "event": "lease won", "outcome": "won"}, store
    )

    store.update(opp_id, {"stage": "LOGGED"}, reason="closed out, handoff complete")
    log_pipeline_event(
        {"opportunity_id": opp_id, "stage": "LOGGED", "event": "opportunity closed", "outcome": "won"}, store
    )

    # --- Assertions on final state -------------------------------------------
    final = store.get(opp_id)
    assert final["stage"] == "LOGGED"
    assert final["outcome"]["result"] == "won"
    assert len(final["proposal_drafts"]) == 2
    assert all(a["status"] == "approved" for a in final["approvals"])
    assert any(e["event"] == "lease won" for e in final["pipeline_events"])
    assert final["fm_bundle"]["tier"] == "standard"
    assert final["requirements"]["transaction_type"] == "lease"
