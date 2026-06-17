"""
Tool input models — one Pydantic model per tool in agent/tools.json.

These are the actual validation boundary the LLM's tool calls pass through
(see registry.py's dispatch()), AND the source from which
agent/tools.json's input_schema blocks are generated (see
scripts/generate_schemas.py). There is exactly one place that defines what
a valid tool call looks like — here — so the agent-facing schema doc and
the runtime validation can never silently drift apart again (that drift is
what caused the requirements-field-name bug found during DeepSeek testing).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.domain import (
    ArtifactType,
    Flags,
    FmBundle,
    Outcome,
    PropertyListing,
    PropertySearchCriteria,
    PropertyType,
    Requirements,
    ScoredProperty,
    Stage,
    TransactionType,
)


class GetOpportunityStateInput(BaseModel):
    opportunity_id: str = Field(description="Unique identifier for the opportunity/deal.")


class UpdateOpportunityStateInput(BaseModel):
    opportunity_id: str = Field(description="Unique identifier for the opportunity/deal.")
    reason: str = Field(description="Short note on why this update is being made (for the audit trail).")
    stage: Optional[Stage] = Field(default=None, description="New workflow stage, if transitioning.")
    requirements: Optional[Requirements] = Field(
        default=None,
        description=(
            "The FULL client requirements object — gather every primary input "
            "(transaction_type, property_type, locations, budget, timeline, and "
            "any of square footage/seats/lease term/zoning/facilities you have) "
            "in conversation first, then send them together here. This REPLACES "
            "any previously stored requirements; it does not patch one field at "
            "a time."
        ),
    )
    shortlist: Optional[list[ScoredProperty]] = Field(
        default=None, description="Scored/ranked property shortlist to store, typically the output of score_shortlist."
    )
    fm_bundle: Optional[FmBundle] = Field(default=None, description="FM service bundle recommendation to store.")
    outcome: Optional[Outcome] = Field(default=None, description="Outcome record (result/decided_at/reason).")
    flags: Optional[Flags] = Field(default=None, description="Data gaps or confidentiality notes to record.")


class SearchPropertiesInput(PropertySearchCriteria):
    """Identical shape to the domain's PropertySearchCriteria — reused
    directly so the search tool and the repository layer never disagree
    about what a search request looks like."""


class GetMarketBenchmarkInput(BaseModel):
    location: str = Field(description="City/submarket to benchmark.")
    property_type: PropertyType
    transaction_type: TransactionType


class GetCompetitorIntelInput(BaseModel):
    location: str
    property_id: Optional[str] = Field(default=None, description="Specific property to check intel against, if known.")
    competitor_names: Optional[list[str]] = Field(default=None, description="Specific named competitors to check, if known.")


class ScoreShortlistInput(BaseModel):
    opportunity_id: str = Field(description="Opportunity whose stored requirements the candidates are scored against.")
    candidates: list[PropertyListing] = Field(description="Property candidates to score, typically the output of search_properties.")
    weights: Optional[dict[str, float]] = Field(
        default=None,
        description="Optional override of default scoring weights (price/location/amenities/availability), must sum to 1.0.",
    )


class GetFmCatalogInput(BaseModel):
    headcount: int = Field(gt=0, description="Client's expected seat/headcount, used to size service tiers.")
    service_categories: Optional[list[str]] = Field(
        default=None,
        description="Specific FM categories to retrieve (pantry, stationery, washroom, electrical, plumbing, general_ops). Omit for the full catalog.",
    )


class SaveDraftArtifactInput(BaseModel):
    opportunity_id: str
    artifact_type: ArtifactType
    content: str = Field(description="The full drafted content (markdown or plain text).")
    version: Optional[int] = None
    status: str = Field(default="draft", description="Draft status. Never set directly to an approved/sent state via this tool.")


class RequestHumanApprovalInput(BaseModel):
    opportunity_id: str
    artifact_type: str = Field(description="What kind of artifact or decision needs approval.")
    summary: str = Field(description="Concise summary of what's being requested for approval and why.")
    urgency: str = Field(default="normal", description="'normal' or 'high' if there's a client deadline.")


class LogPipelineEventInput(BaseModel):
    opportunity_id: str
    stage: Stage
    event: str = Field(description="Short description of what happened.")
    outcome: Optional[str] = Field(default=None, description="'won', 'lost', or 'pending' — set only for outcome-determination events.")
    notes: Optional[str] = None
