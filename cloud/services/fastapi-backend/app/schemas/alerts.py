"""ILEWS backend – Pydantic schemas for alerts."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AlertOut(BaseModel):
    """Public alert response object."""

    model_config = {"from_attributes": True}

    alert_id: str
    slope_id: str
    level: str
    risk_score: Decimal
    source: str = "ml_inference"
    status: str = "active"
    triggered_at: datetime | None = None
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    acknowledged_notes: str | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    false_alarm_confirmed: bool | None = False
    false_alarm_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AlertAcknowledge(BaseModel):
    """Body for acknowledging an alert."""

    notes: str | None = None


class AlertResolve(BaseModel):
    """Body for resolving an alert."""

    resolution_notes: str | None = None


class AlertOverride(BaseModel):
    """Body for manual override (force RED)."""

    slope_id: str = Field(..., max_length=20)
    reason: str


class AlertFalseAlarm(BaseModel):
    """Body for marking an alert as false alarm."""

    reason: str


class AlertNotificationOut(BaseModel):
    """Alert notification delivery status."""

    model_config = {"from_attributes": True}

    notification_id: int
    alert_id: str
    channel: str
    recipient: str | None = None
    status: str = "pending"
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime | None = None
