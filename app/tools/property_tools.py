"""
Property/market-related tools: search_properties, score_shortlist,
get_market_benchmark, get_competitor_intel.

Thin adapters: parse the raw tool-call dict into the matching Pydantic
input model (app/tools/schemas.py), call the business logic in
app/services/, return a JSON-safe dict. All real logic — filtering,
scoring, transaction-type branching — lives in the service layer, not
here; see app/services/property_service.py and market_service.py.
"""
from __future__ import annotations

from app.domain import Requirements
from app.repositories.instances import competitor_intel_repository, market_benchmark_repository, property_repository
from app.services import market_service, property_service
from app.state import OpportunityStore

from .schemas import GetCompetitorIntelInput, GetMarketBenchmarkInput, ScoreShortlistInput, SearchPropertiesInput


def search_properties(input: dict, store: OpportunityStore) -> dict:
    criteria = SearchPropertiesInput.model_validate(input)
    candidates = property_service.search_properties(criteria, property_repository)
    return {
        "count": len(candidates),
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "note": None if candidates else "No properties matched these constraints in the mock inventory.",
    }


def score_shortlist(input: dict, store: OpportunityStore) -> dict:
    parsed = ScoreShortlistInput.model_validate(input)
    record = store.get(parsed.opportunity_id)
    if not record.get("requirements"):
        return {
            "error": (
                f"Opportunity {parsed.opportunity_id} has no stored requirements yet. "
                "Call update_opportunity_state with the full requirements object before scoring."
            )
        }
    requirements = Requirements.model_validate(record["requirements"])
    scored = property_service.score_candidates(parsed.candidates, requirements, parsed.weights)
    return {
        "weights_used": {**property_service.DEFAULT_FIT_WEIGHTS, **(parsed.weights or {})},
        "ranked": [s.model_dump(mode="json") for s in scored],
    }


def get_market_benchmark(input: dict, store: OpportunityStore) -> dict:
    parsed = GetMarketBenchmarkInput.model_validate(input)
    benchmark = market_service.get_market_benchmark(
        parsed.location, parsed.property_type, parsed.transaction_type, market_benchmark_repository
    )
    if benchmark is None:
        return {
            "found": False,
            "note": (
                f"No market benchmark available for {parsed.location} "
                f"({parsed.property_type.value}/{parsed.transaction_type.value}) in mock data."
            ),
        }
    return benchmark.model_dump(mode="json")


def get_competitor_intel(input: dict, store: OpportunityStore) -> dict:
    parsed = GetCompetitorIntelInput.model_validate(input)
    items = market_service.get_competitor_intel(
        parsed.location, competitor_intel_repository, parsed.property_id, parsed.competitor_names
    )
    return {
        "count": len(items),
        "items": [i.model_dump(mode="json") for i in items],
        "disclaimer": "All entries are historical/inferred estimates, not confirmed competitor pricing.",
        "note": None if items else f"No competitor intel available for {parsed.location} in mock data.",
    }
