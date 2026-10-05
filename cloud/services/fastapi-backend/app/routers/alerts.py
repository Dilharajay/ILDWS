"""ILEWS backend – Alerts API router."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.services import alert_service
from app.schemas.alerts import (
    AlertAcknowledge,
    AlertFalseAlarm,
    AlertOverride,
    AlertResolve,
)
from app.utils.audit import write_audit_log
from app.utils.dependencies import get_current_user, require_role
from app.utils.response import paginated_meta, success_response

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


# ---------- LIST alerts ------------------------------------------------------

@router.get("")
async def list_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    slope_id: str | None = None,
    level: str | None = None,
    status: str | None = Query(None, alias="status"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    rows, total = await alert_service.list_alerts(
        db,
        slope_id=slope_id,
        level=level,
        alert_status=status,
        start_time=start_time,
        end_time=end_time,
        page=page,
        per_page=per_page,
    )
    return success_response(
        rows,
        meta=paginated_meta(page=page, per_page=per_page, total=total),
    )


# ---------- GET single alert -------------------------------------------------

@router.get("/{alert_id}")
async def get_alert(
    alert_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    data = await alert_service.get_alert(db, alert_id)
    return success_response(data)


# ---------- ACKNOWLEDGE alert ------------------------------------------------

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator",
    ))],
    body: AlertAcknowledge | None = None,
):
    data = await alert_service.acknowledge_alert(
        db, alert_id, user.email, notes=body.notes if body else None,
    )
    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="alert.acknowledge",
        resource_type="alert",
        resource_id=alert_id,
        new_value=data,
    )
    await db.commit()
    return success_response(data)


# ---------- RESOLVE alert ----------------------------------------------------

@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator",
    ))],
    body: AlertResolve | None = None,
):
    data = await alert_service.resolve_alert(
        db, alert_id, user.email,
        resolution_notes=body.resolution_notes if body else None,
    )
    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="alert.resolve",
        resource_type="alert",
        resource_id=alert_id,
        new_value=data,
    )
    await db.commit()
    return success_response(data)


# ---------- MANUAL OVERRIDE (force RED) --------------------------------------

@router.post("/override", status_code=201)
async def manual_override(
    body: AlertOverride,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator",
    ))],
):
    data = await alert_service.manual_override_alert(
        db, body.slope_id, body.reason, user.email,
    )
    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="alert.manual_override",
        resource_type="alert",
        resource_id=data["alert_id"],
        new_value=data,
    )
    await db.commit()
    return success_response(data)


# ---------- MARK FALSE ALARM -------------------------------------------------

@router.post("/{alert_id}/false-alarm")
async def mark_false_alarm(
    alert_id: str,
    body: AlertFalseAlarm,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager",
    ))],
):
    data = await alert_service.mark_false_alarm(
        db, alert_id, body.reason, user.email,
    )
    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="alert.false_alarm",
        resource_type="alert",
        resource_id=alert_id,
        new_value=data,
    )
    await db.commit()
    return success_response(data)


# ---------- GET notification status ------------------------------------------

@router.get("/{alert_id}/notifications")
async def get_alert_notifications(
    alert_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator",
    ))],
):
    data = await alert_service.get_alert_notifications(db, alert_id)
    return success_response(data)
