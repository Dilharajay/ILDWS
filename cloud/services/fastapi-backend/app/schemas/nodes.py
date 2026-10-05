"""ILEWS backend – Pydantic schemas for sensor nodes."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class NodeCreate(BaseModel):
    node_id: str = Field(..., min_length=1, max_length=20)
    slope_id: str = Field(..., min_length=1, max_length=20)
    name: str | None = Field(None, max_length=100)
    latitude: Decimal = Field(..., ge=-90, le=90, description="Manually entered latitude")
    longitude: Decimal = Field(..., ge=-180, le=180, description="Manually entered longitude")
    depth_config: list[float] = Field(
        default=[0.5, 1.0, 2.0], min_length=1, max_length=5,
    )
    coordinate_source: str | None = Field(
        None, max_length=100,
        description="e.g. topographic_survey, manual_estimate, satellite_imagery",
    )
    survey_reference: str | None = Field(None, max_length=100)
    firmware_version: str | None = Field(None, max_length=20)
    hardware_revision: str | None = Field(None, max_length=20)
    installed_date: date | None = None


class NodeUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)
    depth_config: list[float] | None = Field(None, min_length=1, max_length=5)
    coordinate_source: str | None = Field(None, max_length=100)
    survey_reference: str | None = Field(None, max_length=100)
    firmware_version: str | None = Field(None, max_length=20)
    hardware_revision: str | None = Field(None, max_length=20)
    installed_date: date | None = None
    status: str | None = Field(
        None, pattern=r"^(active|inactive|error|decommissioned)$"
    )


class NodeOut(BaseModel):
    node_id: str
    slope_id: str
    name: str | None = None
    latitude: Decimal
    longitude: Decimal
    depth_config: list[float] | None = None
    coordinate_source: str | None = None
    survey_reference: str | None = None
    firmware_version: str | None = None
    hardware_revision: str | None = None
    installed_date: date | None = None
    last_maintenance_at: datetime | None = None
    status: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
