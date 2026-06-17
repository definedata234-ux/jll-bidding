"""FM catalog pricing — scales the rate card to a given headcount."""
from __future__ import annotations

from app.domain import FmTierPricing
from app.repositories.base import FmCatalogRepository


def get_fm_catalog(
    headcount: int, service_categories: list[str] | None, repo: FmCatalogRepository
) -> dict[str, dict[str, FmTierPricing]]:
    catalog = repo.get_raw_catalog()
    requested = service_categories or list(catalog["categories"].keys())

    result: dict[str, dict[str, FmTierPricing]] = {}
    for category in requested:
        tiers = catalog["categories"].get(category)
        if not tiers:
            continue
        tier_pricing: dict[str, FmTierPricing] = {}
        for tier_name, tier in tiers.items():
            monthly = round(tier["price_per_seat_per_month"] * headcount, 2)
            tier_pricing[tier_name] = FmTierPricing(
                description=tier["description"],
                price_per_seat_per_month=tier["price_per_seat_per_month"],
                indicative_monthly_total=monthly,
                indicative_annual_total=round(monthly * 12, 2),
            )
        result[category] = tier_pricing
    return result
