"""
Property search + scoring business logic. This is where transaction-type-
aware behavior lives — lease and purchase deals are priced and scored
differently, but both go through the exact same shortlist/comparison
workflow, so the branching is isolated here rather than scattered across
tool functions.

Depends only on the PropertyRepository abstraction, never on the mock
implementation directly — see app/repositories/base.py.
"""
from __future__ import annotations

from app.domain import (
    BudgetBasis,
    FitBreakdown,
    PropertyListing,
    PropertySearchCriteria,
    Requirements,
    ScoredProperty,
    ShortlistStatus,
    TransactionType,
)
from app.repositories.base import PropertyRepository

DEFAULT_FIT_WEIGHTS = {
    "price": 0.40,
    "location": 0.25,
    "amenities": 0.20,
    "availability": 0.15,
}


def search_properties(criteria: PropertySearchCriteria, repo: PropertyRepository) -> list[PropertyListing]:
    return repo.search(criteria)


def _listing_price_value(listing: PropertyListing, requirements: Requirements) -> float | None:
    """The dollar figure to compare against the client's budget ceiling,
    chosen based on transaction type AND the budget's stated basis."""
    basis = requirements.budget.basis
    if requirements.transaction_type == TransactionType.LEASE:
        if listing.lease_price_per_sqft is None:
            return None
        if basis == BudgetBasis.TOTAL_ANNUAL:
            return listing.lease_price_per_sqft * listing.square_footage
        return listing.lease_price_per_sqft  # PER_SQFT
    else:  # PURCHASE
        if basis == BudgetBasis.TOTAL_PURCHASE_PRICE:
            return listing.purchase_price_total
        return listing.purchase_price_per_sqft  # PER_SQFT_PURCHASE


def _total_occupancy_cost(listing: PropertyListing, requirements: Requirements) -> float | None:
    if requirements.transaction_type == TransactionType.LEASE:
        if listing.lease_price_per_sqft is None:
            return None
        return listing.lease_price_per_sqft * listing.square_footage
    return listing.purchase_price_total


def _price_score(value: float | None, budget_max: float | None) -> float:
    if value is None:
        return 0.0
    if not budget_max:
        return 0.5  # no ceiling given — neutral
    if value > budget_max:
        return 0.0
    return max(0.0, min(1.0, 1 - (value / budget_max) * 0.6))


def _location_score(location: str, priority_locations: list[str]) -> float:
    if not priority_locations:
        return 0.5
    normalized = [loc.lower() for loc in priority_locations]
    if location.lower() not in normalized:
        return 0.0
    rank = normalized.index(location.lower())
    return max(0.2, 1.0 - 0.2 * rank)


def _amenities_score(amenities: list[str], must_have: list[str], nice_to_have: list[str]) -> float:
    amenity_set = set(amenities)
    must = set(must_have)
    nice = set(nice_to_have)
    must_coverage = 1.0 if not must else len(must & amenity_set) / len(must)
    nice_coverage = 0.0 if not nice else len(nice & amenity_set) / len(nice)
    return round(0.7 * must_coverage + 0.3 * nice_coverage, 4)


def _availability_score(availability_date, target_date) -> float:
    if target_date is None:
        return 0.5
    return 1.0 if availability_date <= target_date else 0.3


def score_candidates(
    candidates: list[PropertyListing],
    requirements: Requirements,
    weights: dict | None = None,
) -> list[ScoredProperty]:
    w = {**DEFAULT_FIT_WEIGHTS, **(weights or {})}
    scored: list[ScoredProperty] = []

    for listing in candidates:
        price_value = _listing_price_value(listing, requirements)
        price_s = _price_score(price_value, requirements.budget.max_amount)
        loc_s = _location_score(listing.location, requirements.locations)
        amen_s = _amenities_score(
            listing.amenities, requirements.must_have_facilities, requirements.nice_to_have_facilities
        )
        avail_s = _availability_score(listing.availability_date, requirements.timeline.target_date)

        fit_score = round(
            price_s * w["price"] + loc_s * w["location"] + amen_s * w["amenities"] + avail_s * w["availability"],
            4,
        )

        status = ShortlistStatus.STRETCH if price_s == 0.0 and price_value is not None else ShortlistStatus.ALTERNATE

        scored.append(
            ScoredProperty(
                **listing.model_dump(),
                total_occupancy_cost=_total_occupancy_cost(listing, requirements),
                fit_score=fit_score,
                fit_breakdown=FitBreakdown(
                    price=round(price_s, 4), location=round(loc_s, 4), amenities=round(amen_s, 4), availability=round(avail_s, 4)
                ),
                shortlist_status=status,
            )
        )

    scored.sort(key=lambda p: p.fit_score, reverse=True)
    if scored:
        scored[0].shortlist_status = ShortlistStatus.PRIMARY
    return scored
