"""Market benchmark + competitor intel lookups — thin service wrappers over
the repository abstractions, kept separate from property_service.py since
they're a different concern (market context vs. candidate scoring)."""
from __future__ import annotations

from typing import Optional

from app.domain import CompetitorIntelItem, MarketBenchmark, PropertyType, TransactionType
from app.repositories.base import CompetitorIntelRepository, MarketBenchmarkRepository


def get_market_benchmark(
    location: str,
    property_type: PropertyType,
    transaction_type: TransactionType,
    repo: MarketBenchmarkRepository,
) -> Optional[MarketBenchmark]:
    return repo.get(location, property_type, transaction_type)


def get_competitor_intel(
    location: str,
    repo: CompetitorIntelRepository,
    property_id: Optional[str] = None,
    competitor_names: Optional[list[str]] = None,
) -> list[CompetitorIntelItem]:
    return repo.get(location, property_id=property_id, competitor_names=competitor_names)
