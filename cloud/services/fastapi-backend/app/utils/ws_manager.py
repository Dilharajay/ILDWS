"""ILEWS backend – WebSocket connection manager."""

import json
from datetime import datetime, timezone

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and slope subscriptions."""

    def __init__(self):
        # ws -> set of slope_ids
        self._connections: dict[WebSocket, set[str]] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections[ws] = set()

    def disconnect(self, ws: WebSocket):
        self._connections.pop(ws, None)

    def subscribe(self, ws: WebSocket, slope_ids: list[str]):
        if ws in self._connections:
            self._connections[ws].update(slope_ids)

    def unsubscribe(self, ws: WebSocket, slope_ids: list[str]):
        if ws in self._connections:
            self._connections[ws].difference_update(slope_ids)

    async def broadcast_to_slope(self, slope_id: str, event: dict):
        """Send event to all clients subscribed to slope_id."""
        dead = []
        for ws, subscriptions in self._connections.items():
            if slope_id in subscriptions:
                try:
                    await ws.send_json(event)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_all(self, event: dict):
        """Send event to all connected clients."""
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()
