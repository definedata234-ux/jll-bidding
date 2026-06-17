"""
Scenario test: end-to-end WON deal on a PURCHASE transaction.

Lease was the only transaction type Stage 3 supported. This proves the
transaction_type="purchase" path — different budget basis, different
pricing fields (purchase_price_total/per_sqft instead of lease rate, no
lease term), different market benchmark lookup — works through the same
shortlist/comparison/proposal/approval workflow as a lease deal.
"""
from app.state import OpportunityStore
from app.tools.property_tools import get_market_benchmark, score_shortlist, search_properties
from app.tools.workflow_tools import log_pipeline_event, request_human_approval, save_draft_artifact


def test_purchase_deal_end_to_end(tmp_path):
    store = OpportunityStore(storage_dir=tmp_path)
    record = store.create("Northwind Logistics Holdings")
    opp_id = record["opportunity_id"]

    # --- INTAKE: a purchase, not a lease -------------------------------------
    store.update(
        opp_id,
        {
            "requirements": {
                "transaction_type": "purchase",
                "property_type": "industrial",
                "locations": ["Chicago"],
                "budget": {"max_amount": 160, "basis": "per_sqft_purchase"},
                "timeline": {"target_date": "2026-12-01"},
                "zoning_classifications": ["industrial_light"],
                "must_have_facilities": ["loading_dock"],
                "industry": "logistics",
            }
        },
        reason="captured purchase requirements",
    )
    store.update(opp_id, {"stage": "SHORTLISTING"}, reason="ready to search")

    # --- SHORTLISTING ----------------------------------------------------------
    search_result = search_properties(
        {
            "locations": ["Chicago"],
            "transaction_type": "purchase",
            "property_type": "industrial",
            "zoning_classifications": ["industrial_light"],
            "budget": {"max_amount": 160, "basis": "per_sqft_purchase"},
            "must_have_facilities": ["loading_dock"],
            "needed_by": "2026-12-01",
        },
        store,
    )
    assert search_result["count"] > 0, "expected the purchase-only industrial mock listing to match"
    assert search_result["candidates"][0]["name"] == "Riverfront Industrial Park"
    # Lease-only fields should not be populated on a purchase-only listing.
    assert search_result["candidates"][0]["lease_price_per_sqft"] is None
    assert search_result["candidates"][0]["purchase_price_per_sqft"] == 150

    scored = score_shortlist({"opportunity_id": opp_id, "candidates": search_result["candidates"]}, store)
    top = scored["ranked"][0]
    assert top["total_occupancy_cost"] == 9_600_000  # purchase total price, not an annual lease cost
    store.update(opp_id, {"shortlist": scored["ranked"], "stage": "COMPARISON"}, reason="shortlisted")

    # --- COMPARISON: purchase-specific benchmark --------------------------------
    benchmark = get_market_benchmark(
        {"location": "Chicago", "property_type": "industrial", "transaction_type": "purchase"}, store
    )
    assert benchmark["found"]
    assert benchmark["basis"] == "per_sqft_purchase"
    store.update(opp_id, {"market_benchmark": benchmark, "stage": "PROPOSAL_DRAFTING"}, reason="comparison complete")

    # --- PROPOSAL_DRAFTING + approval ---------------------------------------------
    save_draft_artifact(
        {"opportunity_id": opp_id, "artifact_type": "bid_proposal", "content": "Purchase offer draft for Riverfront Industrial Park."},
        store,
    )
    approval = request_human_approval(
        {"opportunity_id": opp_id, "artifact_type": "bid_proposal", "summary": "Review purchase offer"}, store
    )
    store.resolve_approval(opp_id, approval["approval_id"], "approve", reviewer="bid-manager")
    store.update(opp_id, {"stage": "NEGOTIATION"}, reason="approved, proceeding to negotiation")
    log_pipeline_event({"opportunity_id": opp_id, "stage": "NEGOTIATION", "event": "purchase offer presented"}, store)
    store.update(opp_id, {"stage": "OUTCOME_PENDING"}, reason="awaiting seller decision")

    # --- OUTCOME: WON ------------------------------------------------------------
    store.update(
        opp_id,
        {"outcome": {"result": "won", "decided_at": "2026-11-01T00:00:00Z", "reason": "offer accepted"}, "stage": "WON_CLOSEOUT"},
        reason="seller accepted offer",
    )
    log_pipeline_event({"opportunity_id": opp_id, "stage": "WON_CLOSEOUT", "event": "purchase won", "outcome": "won"}, store)
    store.update(opp_id, {"stage": "LOGGED"}, reason="closed out")

    final = store.get(opp_id)
    assert final["stage"] == "LOGGED"
    assert final["requirements"]["transaction_type"] == "purchase"
    assert final["outcome"]["result"] == "won"
