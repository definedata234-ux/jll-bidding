"""get_fm_catalog — facility management service catalog, scaled to headcount."""
from __future__ import annotations

from app.repositories.instances import fm_catalog_repository
from app.services import fm_service
from app.state import OpportunityStore

from .schemas import GetFmCatalogInput


def get_fm_catalog(input: dict, store: OpportunityStore) -> dict:
    parsed = GetFmCatalogInput.model_validate(input)
    categories = fm_service.get_fm_catalog(parsed.headcount, parsed.service_categories, fm_catalog_repository)
    return {
        "currency": fm_catalog_repository.get_raw_catalog()["currency"],
        "headcount_used": parsed.headcount,
        "categories": {
            cat: {tier: pricing.model_dump(mode="json") for tier, pricing in tiers.items()}
            for cat, tiers in categories.items()
        },
    }
