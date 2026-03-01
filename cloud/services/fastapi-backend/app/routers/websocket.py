"""ILEWS backend – WebSocket endpoint for real-time dashboard streaming."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.security import verify_token
from app.utils.ws_manager import manager

router = APIRouter()


@router.websocket("/v1/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = None):
    """WebSocket endpoint. Authenticate via ?token=<jwt> query param."""
    # Validate token
    if not token:
        await ws.close(code=4001, reason="Missing token")
        return

    try:
        payload = verify_token(token)
    except Exception:
        await ws.close(code=4001, reason="Invalid token")
        return

    await manager.connect(ws)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"event": "error", "message": "Invalid JSON"})
                continue

            action = msg.get("action")

            if action == "ping":
                await ws.send_json({
                    "event": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif action == "subscribe":
                slope_ids = msg.get("slope_ids", [])
                manager.subscribe(ws, slope_ids)
                await ws.send_json({
                    "event": "subscribed",
                    "slope_ids": slope_ids,
                })

            elif action == "unsubscribe":
                slope_ids = msg.get("slope_ids", [])
                manager.unsubscribe(ws, slope_ids)
                await ws.send_json({
                    "event": "unsubscribed",
                    "slope_ids": slope_ids,
                })

            else:
                await ws.send_json({
                    "event": "error",
                    "message": f"Unknown action: {action}",
                })

    except WebSocketDisconnect:
        manager.disconnect(ws)
