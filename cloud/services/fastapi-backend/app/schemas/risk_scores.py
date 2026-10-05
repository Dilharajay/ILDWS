"""ILEWS backend – Pydantic schemas for risk scores."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RiskScoreOut(BaseModel):
    """Public risk score response object."""

    model_config = {"from_attributes": True}

    score_id: int | None = None
    slope_id: str
    timestamp: datetime
    risk_score: Decimal = Field(..., ge=0, le=1)
    risk_level: str
    model_version: str
    inference_source: str = "cloud"
    contributing_nodes: list[str] | None = None
    model_confidence: Decimal | None = None
    created_at: datetime | None = None


class RiskOverviewItem(BaseModel):
    """Summarised risk for map overview."""

    slope_id: str
    slope_name: str | None = None
    risk_level: str
    risk_score: Decimal
    latitude_centroid: Decimal | None = None
    longitude_centroid: Decimal | None = None
    node_count: int | None = None
    active_nodes: int | None = None
    computed_at: datetime | None = None


class RiskScoreCreate(BaseModel):
    """Internal payload for recording a new risk score."""

    slope_id: str = Field(..., max_length=20)
    timestamp: datetime
    risk_score: Decimal = Field(..., ge=0, le=1)
    risk_level: str = Field(..., pattern="^(GREEN|YELLOW|ORANGE|RED)$")
    model_version: str = Field(..., max_length=30)
    inference_source: str = Field("cloud", pattern="^(cloud|edge)$")
    contributing_nodes: list[str] | None = None
    model_confidence: Decimal | None = Field(None, ge=0, le=1)
