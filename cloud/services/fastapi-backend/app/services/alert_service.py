"""ILEWS backend – Alert service layer."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import Alert
from app.models.alert_notifications import AlertNotification
from app.schemas.alerts import AlertNotificationOut, AlertOut


def _alert_dict(a: Alert) -> dict:
    return AlertOut.model_validate(a).model_dump(mode="json")


def _notif_dict(n: AlertNotification) -> dict:
    return AlertNotificationOut.model_validate(n).model_dump(mode="json")


def _generate_alert_id() -> str:
    """Generate alert_id in ALT-YYYY-NNNNNN format."""
    import random
    year = datetime.now(timezone.utc).year
    seq = random.randint(1, 999999)
    return f"ALT-{year}-{seq:06d}"


async def list_alerts(
    db: AsyncSession,
    slope_id: str | None = None,
    level: str | None = None,
    alert_status: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict], int]:
    """Return paginated, filtered list of alerts."""
    q = select(Alert)
    count_q = select(func.count()).select_from(Alert)

    if slope_id:
        q = q.where(Alert.slope_id == slope_id)
        count_q = count_q.where(Alert.slope_id == slope_id)
    if level:
        q = q.where(Alert.level == level)
        count_q = count_q.where(Alert.level == level)
    if alert_status:
        q = q.where(Alert.status == alert_status)
        count_q = count_q.where(Alert.status == alert_status)
    if start_time:
        q = q.where(Alert.triggered_at >= start_time)
        count_q = count_q.where(Alert.triggered_at >= start_time)
    if end_time:
        q = q.where(Alert.triggered_at <= end_time)
        count_q = count_q.where(Alert.triggered_at <= end_time)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(Alert.triggered_at.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).scalars().all()
    return [_alert_dict(a) for a in rows], total


async def get_alert(db: AsyncSession, alert_id: str) -> dict:
    """Get a single alert by ID."""
    alert = (
        await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_ALERT_NOT_FOUND")
    return _alert_dict(alert)


async def create_alert(
    db: AsyncSession,
    slope_id: str,
    level: str,
    risk_score: float,
    source: str = "ml_inference",
) -> dict:
    """Create a new alert with auto-generated ID."""
    alert = Alert(
        alert_id=_generate_alert_id(),
        slope_id=slope_id,
        level=level,
        risk_score=risk_score,
        source=source,
        status="active",
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _alert_dict(alert)


async def acknowledge_alert(
    db: AsyncSession,
    alert_id: str,
    user_email: str,
    notes: str | None = None,
) -> dict:
    """Mark an alert as acknowledged."""
    alert = (
        await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_ALERT_NOT_FOUND")

    alert.status = "acknowledged"
    alert.acknowledged_by = user_email
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_notes = notes
    await db.commit()
    await db.refresh(alert)
    return _alert_dict(alert)


async def resolve_alert(
    db: AsyncSession,
    alert_id: str,
    user_email: str,
    resolution_notes: str | None = None,
) -> dict:
    """Mark an alert as resolved."""
    alert = (
        await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_ALERT_NOT_FOUND")

    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_notes = resolution_notes
    await db.commit()
    await db.refresh(alert)
    return _alert_dict(alert)


async def manual_override_alert(
    db: AsyncSession,
    slope_id: str,
    reason: str,
    user_email: str,
) -> dict:
    """Force a RED alert on a slope (manual override)."""
    alert = Alert(
        alert_id=_generate_alert_id(),
        slope_id=slope_id,
        level="RED",
        risk_score=1.0,
        source="manual_override",
        status="active",
        acknowledged_notes=f"Manual override by {user_email}: {reason}",
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _alert_dict(alert)


async def mark_false_alarm(
    db: AsyncSession,
    alert_id: str,
    reason: str,
    user_email: str,
) -> dict:
    """Mark an alert as a false alarm."""
    alert = (
        await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_ALERT_NOT_FOUND")

    alert.status = "false_alarm"
    alert.false_alarm_confirmed = True
    alert.false_alarm_reason = reason
    alert.resolution_notes = f"Marked as false alarm by {user_email}: {reason}"
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return _alert_dict(alert)


async def get_alert_notifications(
    db: AsyncSession,
    alert_id: str,
) -> list[dict]:
    """Return notification delivery records for an alert."""
    # Verify alert exists
    alert = (
        await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_ALERT_NOT_FOUND")

    rows = (
        await db.execute(
            select(AlertNotification).where(
                AlertNotification.alert_id == alert_id
            )
        )
    ).scalars().all()
    return [_notif_dict(n) for n in rows]
