"""
Mock, JSON-file-backed implementations of the repository interfaces in
base.py. These are the ONLY place in the codebase that knows mock data
lives in app/data/*.json — services and tools never read those files
directly. Records are validated against the domain models at load time
(fail fast on malformed mock data) rather than trusting raw JSON.
"""
from __future__ import annotations

from typing import Optional

from app.config import load_mock_data
from app.domain import (
    BudgetBasis,
    CompetitorIntelItem,
    MarketBenchmark,
    PropertyListing,
    PropertySearchCriteria,
    PropertyType,
    TransactionType,
)

from .base import CompetitorIntelRepository, FmCatalogRepository, MarketBenchmarkRepository, PropertyRepository


class MockPropertyRepository(PropertyRepository):
    def __init__(self) -> None:
        raw = load_mock_data("properties.json")
        self._listings = [PropertyListing.model_validate(p) for p in raw]

    def search(self, criteria: PropertySearchCriteria) -> list[PropertyListing]:
        wanted_locations = {loc.lower() for loc in criteria.locations}
        results: list[PropertyListing] = []

        for listing in self._listings:
            if listing.location.lower() not in wanted_locations:
                continue
            if criteria.transaction_type not in listing.transaction_types_available:
                continue
            if criteria.property_type is not None and listing.property_type != criteria.property_type:
                continue
            if (
                criteria.zoning_classifications
                and listing.zoning_classification not in criteria.zoning_classifications
            ):
                continue
            if criteria.square_footage_min is not None and listing.square_footage < criteria.square_footage_min:
                continue
            if criteria.square_footage_max is not None and listing.square_footage > criteria.square_footage_max:
                continue
            if criteria.min_seats is not None and listing.seats_capacity < criteria.min_seats:
                continue
            if criteria.must_have_facilities and not set(criteria.must_have_facilities).issubset(
                set(listing.amenities)
            ):
                continue
            if criteria.needed_by is not None and listing.availability_date > criteria.needed_by:
                continue

            if criteria.transaction_type == TransactionType.LEASE:
                if (
                    criteria.lease_term_months_min is not None
                    and not any(
                        t >= criteria.lease_term_months_min
                        for t in (listing.lease_term_months_options or [])
                    )
                ):
                    continue
                if criteria.budget is not None and not self._lease_budget_ok(listing, criteria.budget):
                    continue
            else:  # PURCHASE
                if criteria.budget is not None and not self._purchase_budget_ok(listing, criteria.budget):
                    continue

            results.append(listing)

        return results[: criteria.max_results]

    @staticmethod
    def _lease_budget_ok(listing: PropertyListing, budget) -> bool:
        if budget.basis == BudgetBasis.PER_SQFT:
            value = listing.lease_price_per_sqft
        else:  # TOTAL_ANNUAL
            value = (listing.lease_price_per_sqft or 0) * listing.square_footage
        if value is None:
            return False
        if value > budget.max_amount:
            return False
        if budget.min_amount is not None and value < budget.min_amount:
            return False
        return True

    @staticmethod
    def _purchase_budget_ok(listing: PropertyListing, budget) -> bool:
        if budget.basis == BudgetBasis.TOTAL_PURCHASE_PRICE:
            value = listing.purchase_price_total
        else:  # PER_SQFT_PURCHASE
            value = listing.purchase_price_per_sqft
        if value is None:
            return False
        if value > budget.max_amount:
            return False
        if budget.min_amount is not None and value < budget.min_amount:
            return False
        return True


class MockMarketBenchmarkRepository(MarketBenchmarkRepository):
    def __init__(self) -> None:
        raw = load_mock_data("market_benchmarks.json")
        self._benchmarks = [MarketBenchmark.model_validate(b) for b in raw]

    def get(
        self, location: str, property_type: PropertyType, transaction_type: TransactionType
    ) -> Optional[MarketBenchmark]:
        for b in self._benchmarks:
            if (
                b.location.lower() == location.lower()
                and b.property_type == property_type
                and b.transaction_type == transaction_type
            ):
                return b
        return None


class MockCompetitorIntelRepository(CompetitorIntelRepository):
    def __init__(self) -> None:
        raw = load_mock_data("competitor_intel.json")
        self._items = [CompetitorIntelItem.model_validate(c) for c in raw]

    def get(
        self,
        location: str,
        property_id: Optional[str] = None,
        competitor_names: Optional[list[str]] = None,
    ) -> list[CompetitorIntelItem]:
        results = [c for c in self._items if c.location.lower() == location.lower()]
        if competitor_names:
            wanted = {n.lower() for n in competitor_names}
            results = [c for c in results if c.competitor_name.lower() in wanted]
        return results


class MockFmCatalogRepository(FmCatalogRepository):
    def __init__(self) -> None:
        self._catalog = load_mock_data("fm_catalog.json")

    def get_raw_catalog(self) -> dict:
        return self._catalog
