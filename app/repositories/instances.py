"""
Default repository singletons, wired to the mock implementations. This is
the one place that decides which concrete repository backs each interface
— swapping a mock for a real integration later means changing the
right-hand side of one assignment here, not touching services or tools.
"""
from .mock import (
    MockCompetitorIntelRepository,
    MockFmCatalogRepository,
    MockMarketBenchmarkRepository,
    MockPropertyRepository,
)

property_repository = MockPropertyRepository()
market_benchmark_repository = MockMarketBenchmarkRepository()
competitor_intel_repository = MockCompetitorIntelRepository()
fm_catalog_repository = MockFmCatalogRepository()
