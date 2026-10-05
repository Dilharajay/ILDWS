"""Tests for the ILEWS Alerts API (Prompt 2.4)."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.alerts import Alert
from app.models.alert_notifications import AlertNotification
from app.models.users import User
from app.utils.security import create_access_token, hash_password

_HASHED = hash_password("pass123")


def _make_user(**overrides):
    user = MagicMock(spec=User)
    defaults = {
        "user_id": "USR001", "email": "op@ilews.io",
        "name": "Operator", "role": "operator",
        "is_active": True, "password_hash": _HASHED,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_alert(**overrides):
    a = MagicMock(spec=Alert)
    defaults = {
        "alert_id": "ALT-2026-001247",
        "slope_id": "SLOPE_BKT_01",
        "level": "RED",
        "risk_score": Decimal("0.910"),
        "source": "ml_inference",
        "status": "active",
        "triggered_at": datetime(2026, 2, 28, 7, 45, tzinfo=timezone.utc),
        "acknowledged_by": None,
        "acknowledged_at": None,
        "acknowledged_notes": None,
        "resolved_at": None,
        "resolution_notes": None,
        "false_alarm_confirmed": False,
        "false_alarm_reason": None,
        "trigger_score_id": None,
        "created_at": datetime(2026, 2, 28, 7, 45, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 2, 28, 7, 45, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(a, k, v)
    return a


def _auth_header(role="operator"):
    token = create_access_token({"sub": "USR001", "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.clear()


def test_list_alerts():
    """GET /v1/alerts returns paginated list."""
    user = _make_user()
    a1 = _make_alert()

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        rows_result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = [a1]
        rows_result.scalars.return_value = scalars
        session.execute.side_effect = [user_result, count_result, rows_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get("/v1/alerts", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 1
    assert body["data"][0]["alert_id"] == "ALT-2026-001247"


def test_get_alert():
    """GET /v1/alerts/{id} returns a single alert."""
    user = _make_user()
    alert = _make_alert()

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        alert_result = MagicMock()
        alert_result.scalar_one_or_none.return_value = alert
        session.execute.side_effect = [user_result, alert_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get("/v1/alerts/ALT-2026-001247", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["data"]["level"] == "RED"


def test_get_alert_not_found():
    """GET /v1/alerts/{id} returns 404 for missing alert."""
    user = _make_user()

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        alert_result = MagicMock()
        alert_result.scalar_one_or_none.return_value = None
        session.execute.side_effect = [user_result, alert_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get("/v1/alerts/NONEXIST", headers=_auth_header())
    assert resp.status_code == 404


def test_acknowledge_alert():
    """POST /v1/alerts/{id}/acknowledge marks alert as acknowledged."""
    user = _make_user()
    alert = _make_alert()

    async def _get_db():
        session = AsyncMock()
        # 1: user lookup
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        # 2: alert lookup in service
        alert_result = MagicMock()
        alert_result.scalar_one_or_none.return_value = alert
        session.execute.side_effect = [user_result, alert_result]

        async def _refresh(obj):
            if hasattr(obj, "status"):
                obj.status = "acknowledged"
                obj.acknowledged_by = "op@ilews.io"
                obj.acknowledged_at = datetime.now(timezone.utc)

        session.refresh.side_effect = _refresh
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.post(
        "/v1/alerts/ALT-2026-001247/acknowledge",
        json={"notes": "Evacuation issued."},
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "acknowledged"


def test_resolve_alert():
    """POST /v1/alerts/{id}/resolve marks alert as resolved."""
    user = _make_user()
    alert = _make_alert()

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        alert_result = MagicMock()
        alert_result.scalar_one_or_none.return_value = alert
        session.execute.side_effect = [user_result, alert_result]

        async def _refresh(obj):
            if hasattr(obj, "status"):
                obj.status = "resolved"
                obj.resolved_at = datetime.now(timezone.utc)

        session.refresh.side_effect = _refresh
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.post(
        "/v1/alerts/ALT-2026-001247/resolve",
        json={"resolution_notes": "Slope stable."},
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "resolved"


def test_manual_override():
    """POST /v1/alerts/override creates a RED alert."""
    user = _make_user()

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [user_result]

        async def _refresh(obj):
            if hasattr(obj, "alert_id"):
                obj.status = "active"
                obj.triggered_at = datetime.now(timezone.utc)
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)

        session.refresh.side_effect = _refresh
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.post(
        "/v1/alerts/override",
        json={"slope_id": "SLOPE_BKT_01", "reason": "Visual crack detected"},
        headers=_auth_header(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["level"] == "RED"
    assert body["data"]["source"] == "manual_override"


def test_alerts_require_auth():
    """GET /v1/alerts without token returns 401."""
    client = TestClient(app)
    resp = client.get("/v1/alerts")
    assert resp.status_code == 401


def test_readonly_cannot_acknowledge():
    """POST /v1/alerts/{id}/acknowledge with readonly role returns 403."""
    user = _make_user(role="read_only")

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [user_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    token = create_access_token({"sub": "USR001", "role": "read_only"})
    resp = client.post(
        "/v1/alerts/ALT-2026-001247/acknowledge",
        json={"notes": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_get_alert_notifications():
    """GET /v1/alerts/{id}/notifications returns delivery status."""
    user = _make_user()
    alert = _make_alert()
    notif = MagicMock(spec=AlertNotification)
    notif.notification_id = 1
    notif.alert_id = "ALT-2026-001247"
    notif.channel = "sms"
    notif.recipient = "60123456789"
    notif.status = "delivered"
    notif.attempt_count = 1
    notif.last_attempt_at = datetime(2026, 2, 28, 7, 45, 8, tzinfo=timezone.utc)
    notif.delivered_at = datetime(2026, 2, 28, 7, 45, 10, tzinfo=timezone.utc)
    notif.error_message = None
    notif.created_at = datetime(2026, 2, 28, 7, 45, 8, tzinfo=timezone.utc)

    async def _get_db():
        session = AsyncMock()
        # 1: user
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        # 2: alert exists check
        alert_result = MagicMock()
        alert_result.scalar_one_or_none.return_value = alert
        # 3: notifications
        notif_result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = [notif]
        notif_result.scalars.return_value = scalars
        session.execute.side_effect = [user_result, alert_result, notif_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get(
        "/v1/alerts/ALT-2026-001247/notifications",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["channel"] == "sms"
    assert body["data"][0]["status"] == "delivered"
