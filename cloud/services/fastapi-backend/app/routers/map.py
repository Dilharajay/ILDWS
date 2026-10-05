"""ILEWS backend – Map data API router."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.sensor_nodes import SensorNode
from app.models.slopes import Slope
from app.models.users import User
from app.services import risk_service
from app.utils.dependencies import get_current_user
from app.utils.response import success_response

router = APIRouter(prefix="/v1/map", tags=["map"])


@router.get("/data")
async def get_map_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    """Return all nodes with positions and current risk for map rendering."""
    redis = None
    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        pass

    # Nodes
    nodes_q = select(SensorNode).where(SensorNode.is_deleted.is_(False))
    nodes = (await db.execute(nodes_q)).scalars().all()

    # Slopes (for risk + polygon)
    slopes = (await db.execute(select(Slope))).scalars().all()
    slope_map = {s.slope_id: s for s in slopes}

    # Build risk per slope
    risk_map = {}
    for slope in slopes:
        r = await risk_service.get_current_risk(db, slope.slope_id, redis=redis)
        if r:
            risk_map[slope.slope_id] = r

    if redis:
        await redis.aclose()

    node_list = []
    for n in nodes:
        r = risk_map.get(n.slope_id, {})
        node_list.append({
            "node_id": n.node_id,
            "slope_id": n.slope_id,
            "latitude": float(n.latitude) if n.latitude else None,
            "longitude": float(n.longitude) if n.longitude else None,
            "risk_level": r.get("risk_level", "GREEN"),
            "risk_score": r.get("risk_score", 0.0),
            "last_seen": n.last_seen.isoformat() if n.last_seen else None,
            "status": n.status,
        })

    risk_zones = []
    for slope in slopes:
        r = risk_map.get(slope.slope_id, {})
        risk_zones.append({
            "slope_id": slope.slope_id,
            "risk_level": r.get("risk_level", "GREEN"),
            "risk_score": r.get("risk_score", 0.0),
            "zone_polygon": slope.zone_polygon,
        })

    return success_response({
        "nodes": node_list,
        "risk_zones": risk_zones,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
