"""
Validation tests — the cross-field rules in app/domain/models.py are the
actual enforcement of "primary inputs are required and internally
consistent." These tests prove the rules reject bad data rather than
silently accepting it (which is what the old free-form dict schema did,
and which directly caused the requirements-field-name bug found during
DeepSeek testing).
"""
import pytest
from pydantic import ValidationError

from app.domain import BudgetBasis, BudgetRange, PropertyType, Requirements, Timeline, TransactionType
from app.state import OpportunityStore
from app.tools import dispatch


def _valid_lease_kwargs(**overrides):
    base = dict(
        transaction_type=TransactionType.LEASE,
        property_type=PropertyType.OFFICE,
        locations=["Austin"],
        budget=BudgetRange(max_amount=40, basis=BudgetBasis.PER_SQFT),
        timeline=Timeline(target_date="2026-09-30"),
        lease_term_months=36,
    )
    base.update(overrides)
    return base


def test_lease_requires_lease_term_months():
    with pytest.raises(ValidationError, match="lease_term_months is required"):
        Requirements(**_valid_lease_kwargs(lease_term_months=None))


def test_lease_rejects_purchase_budget_basis():
    with pytest.raises(ValidationError, match="budget.basis must be one of"):
        Requirements(**_valid_lease_kwargs(budget=BudgetRange(max_amount=400, basis=BudgetBasis.PER_SQFT_PURCHASE)))


def test_purchase_rejects_lease_budget_basis():
    with pytest.raises(ValidationError, match="budget.basis must be one of"):
        Requirements(
            transaction_type=TransactionType.PURCHASE,
            property_type=PropertyType.INDUSTRIAL,
            locations=["Chicago"],
            budget=BudgetRange(max_amount=40, basis=BudgetBasis.PER_SQFT),
            timeline=Timeline(target_date="2026-12-01"),
        )


def test_budget_min_cannot_exceed_max():
    with pytest.raises(ValidationError, match="min_amount cannot exceed"):
        BudgetRange(min_amount=50, max_amount=40, basis=BudgetBasis.PER_SQFT)


def test_timeline_deadline_must_precede_target():
    with pytest.raises(ValidationError, match="decision_deadline must be on or before"):
        Timeline(target_date="2026-09-01", decision_deadline="2026-10-01")


def test_square_footage_min_cannot_exceed_max():
    with pytest.raises(ValidationError, match="square_footage_min cannot exceed"):
        Requirements(**_valid_lease_kwargs(square_footage_min=20000, square_footage_max=10000))


def test_unknown_transaction_type_rejected():
    with pytest.raises(ValidationError):
        Requirements(**_valid_lease_kwargs(transaction_type="rent-to-own"))


# --- Tool-boundary validation (via dispatch, the actual agent-facing path) ----

def test_update_opportunity_state_rejects_invalid_requirements_shape(tmp_path):
    store = OpportunityStore(storage_dir=tmp_path)
    record = store.create("Bad Data Co")
    opp_id = record["opportunity_id"]

    with pytest.raises(ValidationError):
        dispatch(
            "update_opportunity_state",
            {
                "opportunity_id": opp_id,
                "reason": "trying the old, wrong field names",
                "requirements": {
                    "location": {"city": "Austin"},  # wrong: should be 'locations': [...]
                    "budget_max_per_sqft": 40,  # wrong: should be nested 'budget' object
                },
            },
            store,
        )
    # The opportunity's requirements must remain unset — the bad call never persisted.
    assert store.get(opp_id)["requirements"] is None


def test_search_properties_rejects_unknown_property_type(tmp_path):
    store = OpportunityStore(storage_dir=tmp_path)
    with pytest.raises(ValidationError):
        dispatch(
            "search_properties",
            {"locations": ["Austin"], "transaction_type": "lease", "property_type": "spaceship"},
            store,
        )


def test_get_fm_catalog_rejects_non_positive_headcount(tmp_path):
    store = OpportunityStore(storage_dir=tmp_path)
    with pytest.raises(ValidationError):
        dispatch("get_fm_catalog", {"headcount": 0}, store)
