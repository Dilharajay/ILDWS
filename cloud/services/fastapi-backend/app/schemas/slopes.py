"""ILEWS backend – Pydantic schemas for slopes."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SlopeCreate(BaseModel):
    slope_id: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    location_name: str | None = Field(None, max_length=200)
    latitude_centroid: Decimal = Field(..., ge=-90, le=90)
    longitude_centroid: Decimal = Field(..., ge=-180, le=180)
    area_m2: Decimal | None = None
    zone_polygon: list | None = None
    monitoring_status: str = Field("active", pattern=r"^(active|inactive|archived)$")
    risk_threshold_red: Decimal = Field(Decimal("0.85"), ge=0, le=1)
    risk_threshold_orange: Decimal = Field(Decimal("0.65"), ge=0, le=1)
    risk_threshold_yellow: Decimal = Field(Decimal("0.40"), ge=0, le=1)


class SlopeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    location_name: str | None = Field(None, max_length=200)
    latitude_centroid: Decimal | None = Field(None, ge=-90, le=90)
    longitude_centroid: Decimal | None = Field(None, ge=-180, le=180)
    area_m2: Decimal | None = None
    zone_polygon: list | None = None
    monitoring_status: str | None = Field(
        None, pattern=r"^(active|inactive|archived)$"
    )
    risk_threshold_red: Decimal | None = Field(None, ge=0, le=1)
    risk_threshold_orange: Decimal | None = Field(None, ge=0, le=1)
    risk_threshold_yellow: Decimal | None = Field(None, ge=0, le=1)


class SlopeOut(BaseModel):
    slope_id: str
    name: str
    description: str | None = None
    location_name: str | None = None
    latitude_centroid: Decimal
    longitude_centroid: Decimal
    area_m2: Decimal | None = None
    zone_polygon: list | None = None
    monitoring_status: str
    risk_threshold_red: Decimal
    risk_threshold_orange: Decimal
    risk_threshold_yellow: Decimal
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None

    model_config = {"from_attributes": True}
