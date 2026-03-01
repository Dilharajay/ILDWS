"""ILEWS backend – System Health API router."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.sensor_nodes import SensorNode
from app.models.node_health_snapshots import NodeHealthSnapshot
from app.models.users import User
from app.utils.dependencies import get_current_user, require_role
from app.utils.response import success_response

router = APIRouter(tags=["system"])


# ---------- GET overall system health ----------------------------------------

@router.get("/v1/system/health")
async def get_system_health(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator",
    ))],
):
    """Check connectivity to DB, Redis and return node summary."""
    services = {
        "fastapi_backend": "healthy",
        "timescaledb": "unknown",
        "redis_cache": "unknown",
    }

    # DB check
    try:
        await db.execute(text("SELECT 1"))
        services["timescaledb"] = "healthy"
    except Exception:
        services["timescaledb"] = "unhealthy"

    # Redis check
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        services["redis_cache"] = "healthy"
        await r.aclose()
    except Exception:
        services["redis_cache"] = "unhealthy"

    # Node summary
    total = (
        await db.execute(
            select(func.count()).select_from(SensorNode).where(
                SensorNode.is_deleted.is_(False)
            )
        )
    ).scalar() or 0

    active = (
        await db.execute(
            select(func.count()).select_from(SensorNode).where(
                SensorNode.is_deleted.is_(False),
                SensorNode.status == "active",
            )
        )
    ).scalar() or 0

    offline = (
        await db.execute(
            select(func.count()).select_from(SensorNode).where(
                SensorNode.is_deleted.is_(False),
                SensorNode.status == "offline",
            )
        )
    ).scalar() or 0

    error = (
        await db.execute(
            select(func.count()).select_from(SensorNode).where(
                SensorNode.is_deleted.is_(False),
                SensorNode.status == "error",
            )
        )
    ).scalar() or 0

    overall = "healthy"
    if any(v == "unhealthy" for v in services.values()):
        overall = "degraded"
    if offline > 0 or error > 0:
        overall = "degraded"

    return success_response({
        "overall": overall,
        "services": services,
        "node_summary": {
            "total": total,
            "active": active,
            "offline": offline,
            "error": error,
        },
        "last_checked": datetime.now(timezone.utc).isoformat(),
    })


# ---------- GET node health details ------------------------------------------

@router.get("/v1/nodes/{node_id}/health")
async def get_node_health(
    node_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator",
    ))],
):
    """Return latest health snapshot for a specific node."""
    q = (
        select(NodeHealthSnapshot)
        .where(NodeHealthSnapshot.node_id == node_id)
        .order_by(NodeHealthSnapshot.timestamp.desc())
        .limit(1)
    )
    snapshot = (await db.execute(q)).scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_NO_HEALTH_DATA")

    return success_response({
        "node_id": snapshot.node_id,
        "connectivity": snapshot.connectivity_status,
        "last_packet_received": snapshot.timestamp.isoformat() if snapshot.timestamp else None,
        "battery_voltage": float(snapshot.battery_voltage_v) if snapshot.battery_voltage_v else None,
        "solar_input": float(snapshot.solar_input_w) if snapshot.solar_input_w else None,
        "firmware_version": snapshot.firmware_version,
        "enclosure_temp_c": float(snapshot.enclosure_temp_c) if snapshot.enclosure_temp_c else None,
        "rssi_dbm_avg": snapshot.rssi_dbm_avg,
    })


# ---------- POST OTA firmware update -----------------------------------------

@router.post("/v1/nodes/{node_id}/firmware/update", status_code=202)
async def trigger_firmware_update(
    node_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(require_role("system_admin"))],
):
    """Queue an OTA firmware update (stub – publishes MQTT command later)."""
    import random
    job_id = f"OTA-{datetime.now(timezone.utc).year}-{random.randint(1, 9999):04d}"

    return success_response({
        "job_id": job_id,
        "node_id": node_id,
        "status": "queued",
    })
