"""
Query/DTO shapes — transient inputs used to ask repositories for data.
Kept separate from models.py (which holds *persisted* opportunity state)
because these are request shapes, not things that get saved.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from .models import BudgetRange, PropertyType, TransactionType, ZoningClassification


class PropertySearchCriteria(BaseModel):
    locations: list[str] = Field(min_length=1)
    transaction_type: TransactionType
    property_type: Optional[PropertyType] = None
    zoning_classifications: list[ZoningClassification] = Field(default_factory=list)
    budget: Optional[BudgetRange] = None
    square_footage_min: Optional[int] = Field(default=None, ge=0)
    square_footage_max: Optional[int] = Field(default=None, ge=0)
    min_seats: Optional[int] = Field(default=None, ge=0)
    lease_term_months_min: Optional[int] = Field(default=None, ge=0)
    must_have_facilities: list[str] = Field(default_factory=list)
    needed_by: Optional[date] = None
    max_results: int = Field(default=10, ge=1, le=50)
