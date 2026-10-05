"""Tests for WebSocket endpoint and event broadcasting (Prompt 2.6)."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.security import create_access_token
from app.utils.ws_manager import ConnectionManager, manager


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.clear()


def _token(role="operator"):
    return create_access_token({"sub": "USR001", "role": role})


# ── WebSocket connect/disconnect ─────────────────────────────────────────


def test_ws_connect_with_valid_token():
    """WebSocket /v1/ws with valid token accepts connection."""
    token = _token()
    client = TestClient(app)

    with client.websocket_connect(f"/v1/ws?token={token}") as ws:
        ws.send_json({"action": "ping"})
        resp = ws.receive_json()
        assert resp["event"] == "pong"
        assert "timestamp" in resp


def test_ws_connect_without_token():
    """WebSocket /v1/ws without token closes with 4001."""
    client = TestClient(app)

    with pytest.raises(Exception):
        with client.websocket_connect("/v1/ws") as ws:
            pass


def test_ws_connect_with_invalid_token():
    """WebSocket /v1/ws with bad token closes with 4001."""
    client = TestClient(app)

    with pytest.raises(Exception):
        with client.websocket_connect("/v1/ws?token=bad-token") as ws:
            pass


# ── Subscribe/Unsubscribe ───────────────────────────────────────────────


def test_ws_subscribe_and_unsubscribe():
    """Client can subscribe and unsubscribe to slopes."""
    token = _token()
    client = TestClient(app)

    with client.websocket_connect(f"/v1/ws?token={token}") as ws:
        ws.send_json({"action": "subscribe", "slope_ids": ["SLOPE_BKT_01"]})
        resp = ws.receive_json()
        assert resp["event"] == "subscribed"
        assert "SLOPE_BKT_01" in resp["slope_ids"]

        ws.send_json({"action": "unsubscribe", "slope_ids": ["SLOPE_BKT_01"]})
        resp = ws.receive_json()
        assert resp["event"] == "unsubscribed"


# ── Event broadcasting ──────────────────────────────────────────────────


def test_ws_receives_risk_update():
    """Client subscribed to slope receives RISK_UPDATE event."""
    from app.utils.event_broadcaster import broadcast_risk_update

    token = _token()
    client = TestClient(app)

    with client.websocket_connect(f"/v1/ws?token={token}") as ws:
        # Subscribe
        ws.send_json({"action": "subscribe", "slope_ids": ["SLOPE_BKT_01"]})
        ws.receive_json()  # consume subscribed ack

        # Broadcast risk update (simulate from service)
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            broadcast_risk_update(
                slope_id="SLOPE_BKT_01",
                risk_level="RED",
                risk_score=0.91,
                timestamp="2026-02-28T07:45:00Z",
            )
        )

        resp = ws.receive_json()
        assert resp["event"] == "RISK_UPDATE"
        assert resp["data"]["slope_id"] == "SLOPE_BKT_01"
        assert resp["data"]["risk_level"] == "RED"


def test_ws_unknown_action():
    """Unknown action returns error message."""
    token = _token()
    client = TestClient(app)

    with client.websocket_connect(f"/v1/ws?token={token}") as ws:
        ws.send_json({"action": "unknown_thing"})
        resp = ws.receive_json()
        assert resp["event"] == "error"
        assert "Unknown action" in resp["message"]


# ── ConnectionManager unit tests ────────────────────────────────────────


def test_connection_manager_count():
    """ConnectionManager tracks active connections."""
    mgr = ConnectionManager()
    assert mgr.active_count == 0


def test_broadcast_alert_triggered():
    """broadcast_alert_triggered sends to subscribed clients."""
    from app.utils.event_broadcaster import broadcast_alert_triggered

    token = _token()
    client = TestClient(app)

    with client.websocket_connect(f"/v1/ws?token={token}") as ws:
        ws.send_json({"action": "subscribe", "slope_ids": ["SLOPE_BKT_01"]})
        ws.receive_json()

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            broadcast_alert_triggered({
                "alert_id": "ALT-2026-001247",
                "slope_id": "SLOPE_BKT_01",
                "level": "RED",
                "risk_score": 0.91,
            })
        )

        resp = ws.receive_json()
        assert resp["event"] == "ALERT_TRIGGERED"
        assert resp["data"]["alert_id"] == "ALT-2026-001247"
