"""ILEWS backend – Event broadcaster for real-time WebSocket push.

Functions in this module publish events to Redis pub/sub AND broadcast
directly to connected WebSocket clients via the connection manager.
"""

import json
from datetime import datetime
from decimal import Decimal

from app.utils.ws_manager import manager


class _Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


async def broadcast_risk_update(
    slope_id: str,
    risk_level: str,
    risk_score: float,
    timestamp: str,
    redis=None,
):
    """Broadcast RISK_UPDATE event."""
    event = {
        "event": "RISK_UPDATE",
        "data": {
            "slope_id": slope_id,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "timestamp": timestamp,
        },
    }
    await manager.broadcast_to_slope(slope_id, event)
    if redis:
        try:
            await redis.publish(
                "ilews:ws:events",
                json.dumps(event, cls=_Encoder),
            )
        except Exception:
            pass


async def broadcast_alert_triggered(alert: dict, redis=None):
    """Broadcast ALERT_TRIGGERED event."""
    event = {
        "event": "ALERT_TRIGGERED",
        "data": alert,
    }
    slope_id = alert.get("slope_id")
    if slope_id:
        await manager.broadcast_to_slope(slope_id, event)
    else:
        await manager.broadcast_all(event)

    if redis:
        try:
            await redis.publish(
                "ilews:ws:events",
                json.dumps(event, cls=_Encoder),
            )
        except Exception:
            pass


async def broadcast_node_status_change(
    node_id: str,
    status: str,
    timestamp: str,
    slope_id: str | None = None,
    redis=None,
):
    """Broadcast NODE_STATUS_CHANGE event."""
    event = {
        "event": "NODE_STATUS_CHANGE",
        "data": {
            "node_id": node_id,
            "status": status,
            "timestamp": timestamp,
        },
    }
    if slope_id:
        await manager.broadcast_to_slope(slope_id, event)
    else:
        await manager.broadcast_all(event)

    if redis:
        try:
            await redis.publish(
                "ilews:ws:events",
                json.dumps(event, cls=_Encoder),
            )
        except Exception:
            pass


async def broadcast_new_reading(reading: dict, redis=None):
    """Broadcast NEW_READING event."""
    event = {
        "event": "NEW_READING",
        "data": reading,
    }
    slope_id = reading.get("slope_id")
    if slope_id:
        await manager.broadcast_to_slope(slope_id, event)

    if redis:
        try:
            await redis.publish(
                "ilews:ws:events",
                json.dumps(event, cls=_Encoder),
            )
        except Exception:
            pass
