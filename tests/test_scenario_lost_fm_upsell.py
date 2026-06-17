"""
Scenario test: LOST leasing bid that pivots into an FM services upsell.

This exercises the "win or not, find revenue" principle from the system
prompt and the OUTCOME_PENDING -> LOST_FM_UPSELL transition in
workflow_state_machine.md: losing the lease must not end engagement with
the client — it must trigger a standalone FM pitch.
"""
from app.state import OpportunityStore
from app.tools.fm_tools import get_fm_catalog
from app.tools.property_tools import get_competitor_intel, get_market_benchmark, score_shortlist, search_properties
from app.tools.workflow_tools import log_pipeline_event, request_human_approval, save_draft_artifact


def test_lost_deal_triggers_fm_upsell(tmp_path):
    store = OpportunityStore(storage_dir=tmp_path)
    record = store.create("Northwind Logistics")
    opp_id = record["opportunity_id"]

    # --- INTAKE -> SHORTLISTING -> COMPARISON -> PROPOSAL_DRAFTING ------------
    store.update(
        opp_id,
        {
            "requirements": {
                "transaction_type": "lease",
                "property_type": "office",
                "locations": ["Chicago"],
                "budget": {"max_amount": 50, "currency": "USD", "basis": "per_sqft"},
                "timeline": {"target_date": "2026-08-01"},
                "seats": 130,
                "lease_term_months": 36,
                "must_have_facilities": ["24x7_access"],
                "industry": "logistics",
            }
        },
        reason="intake complete",
    )
    store.update(opp_id, {"stage": "SHORTLISTING"}, reason="ready to search")

    search_result = search_properties(
        {
            "locations": ["Chicago"],
            "transaction_type": "lease",
            "budget": {"max_amount": 50, "basis": "per_sqft"},
            "min_seats": 130,
            "lease_term_months_min": 36,
            "must_have_facilities": ["24x7_access"],
            "needed_by": "2026-08-01",
        },
        store,
    )
    assert search_result["count"] > 0

    scored = score_shortlist({"opportunity_id": opp_id, "candidates": search_result["candidates"]}, store)
    top = scored["ranked"][0]
    assert top["name"] == "Wacker Plaza"
    store.update(opp_id, {"shortlist": scored["ranked"], "stage": "COMPARISON"}, reason="shortlisted")

    benchmark = get_market_benchmark({"location": top["location"], "property_type": "office", "transaction_type": "lease"}, store)
    intel = get_competitor_intel({"location": top["location"]}, store)
    store.update(
        opp_id,
        {"market_benchmark": benchmark, "competitor_intel": intel["items"], "stage": "PROPOSAL_DRAFTING"},
        reason="comparison complete",
    )

    save_draft_artifact({"opportunity_id": opp_id, "artifact_type": "bid_proposal", "content": "Proposal v1"}, store)
    approval = request_human_approval(
        {"opportunity_id": opp_id, "artifact_type": "bid_proposal", "summary": "Review v1 proposal"}, store
    )
    store.resolve_approval(opp_id, approval["approval_id"], "approve", reviewer="bid-manager")
    store.update(opp_id, {"stage": "NEGOTIATION"}, reason="approved, proceeding to negotiation")

    log_pipeline_event({"opportunity_id": opp_id, "stage": "NEGOTIATION", "event": "proposal presented to client"}, store)
    store.update(opp_id, {"stage": "OUTCOME_PENDING"}, reason="awaiting client decision")

    # --- OUTCOME: LOST ----------------------------------------------------------
    store.update(
        opp_id,
        {
            "outcome": {
                "result": "lost",
                "decided_at": "2026-09-01T00:00:00Z",
                "reason": "competitor offered a lower headline rent",
            },
            "stage": "LOST_FM_UPSELL",
        },
        reason="client chose a competitor for the lease",
    )
    log_pipeline_event(
        {"opportunity_id": opp_id, "stage": "LOST_FM_UPSELL", "event": "lease lost to competitor", "outcome": "lost"},
        store,
    )

    # --- FM UPSELL PIVOT (must always be attempted on loss) ----------------------
    fm = get_fm_catalog({"headcount": 130, "service_categories": ["pantry", "washroom", "general_ops"]}, store)
    assert set(fm["categories"]) == {"pantry", "washroom", "general_ops"}

    pitch_content = (
        "Standalone facility management services pitch for Northwind Logistics "
        "(lease awarded to a competitor): pantry, washroom, and general operations support."
    )
    pitch_draft = save_draft_artifact(
        {"opportunity_id": opp_id, "artifact_type": "fm_upsell_pitch", "content": pitch_content}, store
    )
    assert pitch_draft["artifact"]["artifact_type"] == "fm_upsell_pitch"

    fm_approval = request_human_approval(
        {"opportunity_id": opp_id, "artifact_type": "fm_upsell_pitch", "summary": "Review standalone FM upsell pitch"},
        store,
    )
    store.resolve_approval(opp_id, fm_approval["approval_id"], "approve", reviewer="account-manager")

    store.update(
        opp_id,
        {"fm_upsell": {"pitched": True, "pitched_at": "2026-09-05T00:00:00Z", "status": "pending"}},
        reason="FM upsell pitch approved internally, ready to present to client",
    )
    log_pipeline_event(
        {
            "opportunity_id": opp_id,
            "stage": "LOST_FM_UPSELL",
            "event": "FM upsell pitch approved internally",
            "outcome": "lost",
        },
        store,
    )

    store.update(opp_id, {"stage": "LOGGED"}, reason="closed out")
    log_pipeline_event(
        {
            "opportunity_id": opp_id,
            "stage": "LOGGED",
            "event": "opportunity closed (lease lost, FM upsell pursued)",
            "outcome": "lost",
        },
        store,
    )

    # --- Assertions -------------------------------------------------------------
    final = store.get(opp_id)
    assert final["stage"] == "LOGGED"
    assert final["outcome"]["result"] == "lost"
    assert final["fm_upsell"]["pitched"] is True
    assert any(d["artifact_type"] == "fm_upsell_pitch" for d in final["proposal_drafts"])
    assert any(a["artifact_type"] == "fm_upsell_pitch" and a["status"] == "approved" for a in final["approvals"])
    assert any(e["event"].startswith("lease lost") for e in final["pipeline_events"])
    # The losing outcome must not be the last word — an FM revenue path was opened.
    assert any("FM upsell" in e["event"] for e in final["pipeline_events"])
