"""ILEWS backend – Pydantic schemas for users."""

from datetime import datetime

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    """Public user response object."""

    model_config = {"from_attributes": True}

    user_id: str
    email: str
    name: str
    role: str
    organisation: str | None = None
    phone: str | None = None
    is_active: bool = True
    is_sms_alert_enabled: bool = False
    is_push_alert_enabled: bool = False
    slope_access: list[str] | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserCreate(BaseModel):
    """Payload for creating a new user."""

    email: str = Field(..., max_length=200)
    name: str = Field(..., max_length=150)
    role: str = Field(
        ..., pattern="^(system_admin|operator|analyst|government_viewer|read_only)$"
    )
    organisation: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=30)
    password: str | None = Field(None, min_length=8)


class UserRoleUpdate(BaseModel):
    """Payload for updating a user's role."""

    role: str = Field(
        ..., pattern="^(system_admin|operator|analyst|government_viewer|read_only)$"
    )
