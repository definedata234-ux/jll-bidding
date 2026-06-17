"""
Repository interfaces — the boundary between business logic (app/services)
and data access. Every repository here has exactly one implementation today
(a mock, JSON-file-backed one in mock.py), but the business logic in
app/services never imports that mock directly — it depends on these
abstractions. Swapping in a real listings feed, a zoning GIS lookup, or a
live market-data API later means writing a new class that satisfies one of
these interfaces and changing the wiring in one place (app/services or a
DI container), not touching scoring/search logic at all.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain import (
    CompetitorIntelItem,
    MarketBenchmark,
    PropertyListing,
    PropertySearchCriteria,
    PropertyType,
    TransactionType,
)


class PropertyRepository(ABC):
    @abstractmethod
    def search(self, criteria: PropertySearchCriteria) -> list[PropertyListing]:
        """Return listings matching the given hard constraints. Implementations
        must return [] rather than fabricate results when nothing matches."""
        raise NotImplementedError


class MarketBenchmarkRepository(ABC):
    @abstractmethod
    def get(
        self, location: str, property_type: PropertyType, transaction_type: TransactionType
    ) -> Optional[MarketBenchmark]:
        """Return the benchmark for this location/property_type/transaction_type
        combination, or None if no benchmark is available."""
        raise NotImplementedError


class CompetitorIntelRepository(ABC):
    @abstractmethod
    def get(
        self,
        location: str,
        property_id: Optional[str] = None,
        competitor_names: Optional[list[str]] = None,
    ) -> list[CompetitorIntelItem]:
        raise NotImplementedError


class FmCatalogRepository(ABC):
    @abstractmethod
    def get_raw_catalog(self) -> dict:
        """Return the raw FM catalog structure (categories -> tiers ->
        per-seat pricing). Per-headcount scaling happens in the service
        layer, not here — this just returns the rate card."""
        raise NotImplementedError
