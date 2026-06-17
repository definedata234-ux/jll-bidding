"""
Domain models — the single source of truth for this agent's data shapes.

This replaces the old "loose dict, described in a markdown comment" approach
from Stage 3 with real Pydantic models. Two things downstream are generated
FROM these models rather than hand-maintained in parallel (see
scripts/generate_schemas.py):
  - agent/memory_schema.json  (from OpportunityRecord.model_json_schema())
  - agent/tools.json's per-tool input_schema (from the *Input models in
    app/tools/schemas.py, which compose these domain models)

Rationale for "transaction_type" and "property_type" sitting at the top of
Requirements: these are the two fields that change which other fields are
even valid (lease_term_months only makes sense for a lease; cap_rate only
for a purchase), so cross-field validation below keys off them.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransactionType(str, Enum):
    LEASE = "lease"
    PURCHASE = "purchase"


class PropertyType(str, Enum):
    OFFICE = "office"
    RETAIL = "retail"
    INDUSTRIAL = "industrial"
    WAREHOUSE = "warehouse"
    MIXED_USE = "mixed_use"
    LAND = "land"


class ZoningClassification(str, Enum):
    COMMERCIAL_OFFICE = "commercial_office"
    COMMERCIAL_RETAIL = "commercial_retail"
    INDUSTRIAL_LIGHT = "industrial_light"
    INDUSTRIAL_HEAVY = "industrial_heavy"
    MIXED_USE = "mixed_use"
    AGRICULTURAL = "agricultural"
    SPECIAL_PURPOSE = "special_purpose"


class BudgetBasis(str, Enum):
    PER_SQFT = "per_sqft"                       # lease: annual rate per sqft
    TOTAL_ANNUAL = "total_annual"                # lease: total annual occupancy cost
    TOTAL_PURCHASE_PRICE = "total_purchase_price"  # purchase: total asking/sale price
    PER_SQFT_PURCHASE = "per_sqft_purchase"      # purchase: price per sqft


_LEASE_BASES = {BudgetBasis.PER_SQFT, BudgetBasis.TOTAL_ANNUAL}
_PURCHASE_BASES = {BudgetBasis.TOTAL_PURCHASE_PRICE, BudgetBasis.PER_SQFT_PURCHASE}


class FlexibilityPreference(str, Enum):
    RIGID = "rigid"
    FLEXIBLE = "flexible"


class Stage(str, Enum):
    INTAKE = "INTAKE"
    SHORTLISTING = "SHORTLISTING"
    COMPARISON = "COMPARISON"
    PROPOSAL_DRAFTING = "PROPOSAL_DRAFTING"
    FM_BUNDLING = "FM_BUNDLING"
    NEGOTIATION = "NEGOTIATION"
    OUTCOME_PENDING = "OUTCOME_PENDING"
    WON_CLOSEOUT = "WON_CLOSEOUT"
    LOST_FM_UPSELL = "LOST_FM_UPSELL"
    LOGGED = "LOGGED"


class ArtifactType(str, Enum):
    BID_PROPOSAL = "bid_proposal"
    NEGOTIATION_BRIEF = "negotiation_brief"
    FM_BUNDLE_RECOMMENDATION = "fm_bundle_recommendation"
    FM_UPSELL_PITCH = "fm_upsell_pitch"


class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OutcomeResult(str, Enum):
    WON = "won"
    LOST = "lost"
    PENDING = "pending"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Requirements (primary intake inputs)
# ---------------------------------------------------------------------------

class BudgetRange(BaseModel):
    min_amount: Optional[float] = Field(default=None, ge=0)
    max_amount: float = Field(ge=0)
    currency: str = "USD"
    basis: BudgetBasis

    @model_validator(mode="after")
    def _min_le_max(self) -> "BudgetRange":
        if self.min_amount is not None and self.min_amount > self.max_amount:
            raise ValueError("budget.min_amount cannot exceed budget.max_amount")
        return self


class Timeline(BaseModel):
    """Tentative timeline for the deal — move-in (lease) or closing (purchase)."""
    target_date: date
    decision_deadline: Optional[date] = None
    flexibility: FlexibilityPreference = FlexibilityPreference.FLEXIBLE

    @model_validator(mode="after")
    def _deadline_before_target(self) -> "Timeline":
        if self.decision_deadline is not None and self.decision_deadline > self.target_date:
            raise ValueError("timeline.decision_deadline must be on or before timeline.target_date")
        return self


class Requirements(BaseModel):
    transaction_type: TransactionType
    property_type: PropertyType
    locations: list[str] = Field(min_length=1)
    budget: BudgetRange
    timeline: Timeline

    square_footage_min: Optional[int] = Field(default=None, ge=0)
    square_footage_max: Optional[int] = Field(default=None, ge=0)
    seats: Optional[int] = Field(default=None, ge=0)
    lease_term_months: Optional[int] = Field(default=None, ge=0)
    zoning_classifications: list[ZoningClassification] = Field(default_factory=list)
    must_have_facilities: list[str] = Field(default_factory=list)
    nice_to_have_facilities: list[str] = Field(default_factory=list)
    industry: Optional[str] = None
    special_needs: Optional[str] = None

    @model_validator(mode="after")
    def _cross_field_rules(self) -> "Requirements":
        if self.square_footage_min is not None and self.square_footage_max is not None:
            if self.square_footage_min > self.square_footage_max:
                raise ValueError("square_footage_min cannot exceed square_footage_max")

        if self.transaction_type == TransactionType.LEASE:
            if self.lease_term_months is None:
                raise ValueError("lease_term_months is required when transaction_type is 'lease'")
            if self.budget.basis not in _LEASE_BASES:
                raise ValueError(
                    f"budget.basis must be one of {[b.value for b in _LEASE_BASES]} "
                    "for a lease transaction"
                )
        else:  # PURCHASE
            if self.budget.basis not in _PURCHASE_BASES:
                raise ValueError(
                    f"budget.basis must be one of {[b.value for b in _PURCHASE_BASES]} "
                    "for a purchase transaction"
                )
        return self


# ---------------------------------------------------------------------------
# Property listings (mock inventory) + scoring output
# ---------------------------------------------------------------------------

class PropertyListing(BaseModel):
    property_id: str
    name: str
    address: str
    location: str
    currency: str = "USD"
    property_type: PropertyType
    zoning_classification: ZoningClassification
    transaction_types_available: list[TransactionType] = Field(min_length=1)
    square_footage: int = Field(gt=0)
    seats_capacity: int = Field(gt=0)
    amenities: list[str] = Field(default_factory=list)
    availability_date: date

    # Lease economics — present only if "lease" in transaction_types_available.
    lease_price_per_sqft: Optional[float] = Field(default=None, ge=0)
    lease_term_months_options: Optional[list[int]] = None

    # Purchase economics — present only if "purchase" in transaction_types_available.
    purchase_price_total: Optional[float] = Field(default=None, ge=0)
    purchase_price_per_sqft: Optional[float] = Field(default=None, ge=0)
    cap_rate_pct: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _economics_present_for_available_transactions(self) -> "PropertyListing":
        if TransactionType.LEASE in self.transaction_types_available:
            if self.lease_price_per_sqft is None or not self.lease_term_months_options:
                raise ValueError(
                    f"{self.property_id}: lease_price_per_sqft and lease_term_months_options "
                    "are required when 'lease' is in transaction_types_available"
                )
        if TransactionType.PURCHASE in self.transaction_types_available:
            if self.purchase_price_total is None or self.purchase_price_per_sqft is None:
                raise ValueError(
                    f"{self.property_id}: purchase_price_total and purchase_price_per_sqft "
                    "are required when 'purchase' is in transaction_types_available"
                )
        return self


class FitBreakdown(BaseModel):
    price: float = Field(ge=0, le=1)
    location: float = Field(ge=0, le=1)
    amenities: float = Field(ge=0, le=1)
    availability: float = Field(ge=0, le=1)


class ShortlistStatus(str, Enum):
    PRIMARY = "primary"
    ALTERNATE = "alternate"
    STRETCH = "stretch"  # exceeds budget or another soft constraint, shown for context


class ScoredProperty(PropertyListing):
    total_occupancy_cost: Optional[float] = None  # lease: annual; purchase: total price
    fit_score: float = Field(ge=0, le=1)
    fit_breakdown: FitBreakdown
    shortlist_status: ShortlistStatus = ShortlistStatus.ALTERNATE


# ---------------------------------------------------------------------------
# Market / competitor / FM catalog
# ---------------------------------------------------------------------------

class MarketBenchmark(BaseModel):
    found: bool = True
    location: str
    property_type: PropertyType
    transaction_type: TransactionType
    avg_price: float
    basis: BudgetBasis
    typical_escalation_pct: Optional[float] = None
    typical_lease_term_months: Optional[int] = None
    source: str
    confidence: Confidence


class CompetitorIntelItem(BaseModel):
    location: str
    competitor_name: str
    estimated_position: str
    source: str
    confidence: Confidence


class FmTierPricing(BaseModel):
    description: str
    price_per_seat_per_month: float
    indicative_monthly_total: float
    indicative_annual_total: float


class FmBundleService(BaseModel):
    category: str
    description: str
    indicative_price: float


class FmBundle(BaseModel):
    tier: str = "standard"
    services: list[FmBundleService] = Field(default_factory=list)
    indicative_total_price: float = 0
    rationale: str = ""


# ---------------------------------------------------------------------------
# Workflow artifacts
# ---------------------------------------------------------------------------

class ProposalDraft(BaseModel):
    artifact_type: ArtifactType
    version: int
    created_at: datetime
    content: str
    status: ArtifactStatus = ArtifactStatus.DRAFT


class NegotiationLogEntry(BaseModel):
    date: date
    client_ask: str
    jll_response_options: list[str] = Field(default_factory=list)
    status: str = "open"


class Outcome(BaseModel):
    result: OutcomeResult = OutcomeResult.PENDING
    decided_at: Optional[datetime] = None
    reason: Optional[str] = None


class FmUpsell(BaseModel):
    pitched: bool = False
    pitched_at: Optional[datetime] = None
    artifact_ref: Optional[str] = None
    status: str = "not_applicable"


class PipelineEvent(BaseModel):
    timestamp: datetime
    stage: Stage
    event: str
    outcome: Optional[OutcomeResult] = None
    notes: Optional[str] = None


class Flags(BaseModel):
    data_gaps: list[str] = Field(default_factory=list)
    confidentiality_notes: list[str] = Field(default_factory=list)


class AuditLogEntry(BaseModel):
    timestamp: datetime
    reason: str


class ApprovalRequest(BaseModel):
    approval_id: str
    artifact_type: ArtifactType
    summary: str
    urgency: str = "normal"
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: datetime
    decided_at: Optional[datetime] = None
    reviewer: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level opportunity record
# ---------------------------------------------------------------------------

class OpportunityRecord(BaseModel):
    opportunity_id: str
    client_name: str
    created_at: datetime
    updated_at: datetime
    stage: Stage = Stage.INTAKE

    requirements: Optional[Requirements] = None
    shortlist: list[ScoredProperty] = Field(default_factory=list)
    market_benchmark: Optional[MarketBenchmark] = None
    competitor_intel: list[CompetitorIntelItem] = Field(default_factory=list)
    fm_bundle: Optional[FmBundle] = None
    proposal_drafts: list[ProposalDraft] = Field(default_factory=list)
    negotiation_log: list[NegotiationLogEntry] = Field(default_factory=list)
    outcome: Outcome = Field(default_factory=Outcome)
    fm_upsell: FmUpsell = Field(default_factory=FmUpsell)
    pipeline_events: list[PipelineEvent] = Field(default_factory=list)
    flags: Flags = Field(default_factory=Flags)
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    audit_log: list[AuditLogEntry] = Field(default_factory=list)
