"""ILEWS backend – Pydantic schemas for sensor readings."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ReadingCreate(BaseModel):
    """Payload accepted from ETL service for ingesting a new reading."""

    node_id: str = Field(..., max_length=20)
    slope_id: str = Field(..., max_length=20)
    timestamp: datetime
    packet_id: str | None = Field(None, max_length=40)
    soil_moisture_d1_pct: Decimal | None = None
    soil_moisture_d2_pct: Decimal | None = None
    soil_moisture_d3_pct: Decimal | None = None
    soil_moisture_d4_pct: Decimal | None = None
    soil_moisture_d5_pct: Decimal | None = None
    rainfall_mm: Decimal | None = None
    tilt_x_deg: Decimal | None = None
    tilt_y_deg: Decimal | None = None
    accel_x_ms2: Decimal | None = None
    accel_y_ms2: Decimal | None = None
    accel_z_ms2: Decimal | None = None
    vibration_hz: Decimal | None = None
    vibration_amplitude: Decimal | None = None
    battery_voltage_v: Decimal | None = None
    solar_input_w: Decimal | None = None
    rssi_dbm: int | None = None
    data_quality: str = "valid"
    source: str = "lora"


class ReadingOut(BaseModel):
    """Public reading response object."""

    model_config = {"from_attributes": True}

    reading_id: int | None = None
    node_id: str
    slope_id: str
    timestamp: datetime
    received_at: datetime | None = None
    packet_id: str | None = None
    soil_moisture_d1_pct: Decimal | None = None
    soil_moisture_d2_pct: Decimal | None = None
    soil_moisture_d3_pct: Decimal | None = None
    soil_moisture_d4_pct: Decimal | None = None
    soil_moisture_d5_pct: Decimal | None = None
    rainfall_mm: Decimal | None = None
    tilt_x_deg: Decimal | None = None
    tilt_y_deg: Decimal | None = None
    accel_x_ms2: Decimal | None = None
    accel_y_ms2: Decimal | None = None
    accel_z_ms2: Decimal | None = None
    vibration_hz: Decimal | None = None
    vibration_amplitude: Decimal | None = None
    battery_voltage_v: Decimal | None = None
    solar_input_w: Decimal | None = None
    rssi_dbm: int | None = None
    data_quality: str = "valid"
    source: str = "lora"


class ReadingExportParams(BaseModel):
    """Query parameters for reading export."""

    start_time: datetime
    end_time: datetime
    format: str = Field("csv", pattern="^(csv|json)$")
