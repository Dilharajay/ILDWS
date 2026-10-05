"""Tests for ILEWS Slopes CRUD API (/v1/slopes)."""

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.slopes import Slope
from app.models.users import User
from app.utils.security import create_access_token


# ── helpers ──────────────────────────────────────────────────────────────

def _make_user(**kw):
    u = MagicMock(spec=User)
    defaults = {
        "user_id": "USR-0001",
        "email": "admin@ilews.io",
        "name": "Admin",
        "role": "system_admin",
        "is_active": True,
    }
    defaults.update(kw)
    for k, v in defaults.items():
        setattr(u, k, v)
    return u


def _make_slope(**kw):
    s = MagicMock(spec=Slope)
    now = datetime.now(timezone.utc)
    defaults = {
        "slope_id": "SLOPE_TEST_01",
        "name": "Test Slope",
        "description": None,
        "location_name": "Kuala Lumpur",
        "latitude_centroid": Decimal("3.1520"),
        "longitude_centroid": Decimal("101.7120"),
        "area_m2": Decimal("45000"),
        "zone_polygon": None,
        "monitoring_status": "active",
        "risk_threshold_red": Decimal("0.85"),
        "risk_threshold_orange": Decimal("0.65"),
        "risk_threshold_yellow": Decimal("0.40"),
        "created_at": now,
        "updated_at": now,
        "created_by": "USR-0001",
    }
    defaults.update(kw)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _override_db(user=None, slopes=None, scalar_one=None):
    """Override get_db with a mock session."""

    async def _get_db():
        session = AsyncMock()

        result_mock = MagicMock()
        scalars_mock = MagicMock()

        # scalar_one_or_none returns the user, then the slope result
        side_effects = []
        if user is not None:
            side_effects.append(user)
        if scalar_one is not None:
            side_effects.append(scalar_one)
        else:
            side_effects.append(None)

        result_mock.scalar_one_or_none.side_effect = side_effects
        result_mock.scalar.return_value = len(slopes) if slopes else 0
        scalars_mock.all.return_value = slopes or []
        result_mock.scalars.return_value = scalars_mock

        session.execute.return_value = result_mock
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        yield session

    return _get_db


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.clear()


# ── Tests ────────────────────────────────────────────────────────────────

def test_list_slopes_success():
    user = _make_user()
    slope = _make_slope()
    app.dependency_overrides[get_db] = _override_db(user=user, slopes=[slope])
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "system_admin"})

    resp = client.get("/v1/slopes", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 1
    assert body["data"][0]["slope_id"] == "SLOPE_TEST_01"
    assert "meta" in body


def test_list_slopes_requires_auth():
    client = TestClient(app)
    resp = client.get("/v1/slopes")
    assert resp.status_code == 401


def test_get_slope_not_found():
    user = _make_user()
    app.dependency_overrides[get_db] = _override_db(user=user, scalar_one=None)
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "system_admin"})

    resp = client.get(
        "/v1/slopes/NONEXISTENT",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["status"] == "error"


def test_create_slope_success():
    user = _make_user()

    async def _get_db():
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.side_effect = [user, None]
        session.execute.return_value = result_mock
        session.flush = AsyncMock()
        session.commit = AsyncMock()

        def _refresh(obj):
            """Simulate DB server-defaults after INSERT."""
            now = datetime.now(timezone.utc)
            obj.monitoring_status = obj.monitoring_status or "active"
            obj.risk_threshold_red = obj.risk_threshold_red or Decimal("0.85")
            obj.risk_threshold_orange = obj.risk_threshold_orange or Decimal("0.65")
            obj.risk_threshold_yellow = obj.risk_threshold_yellow or Decimal("0.40")
            obj.created_at = now
            obj.updated_at = now

        session.refresh = AsyncMock(side_effect=_refresh)
        session.add = MagicMock()
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "system_admin"})

    resp = client.post(
        "/v1/slopes",
        json={
            "slope_id": "SLOPE_NEW",
            "name": "New Slope",
            "latitude_centroid": 3.15,
            "longitude_centroid": 101.71,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "success"


def test_create_slope_forbidden_for_readonly():
    user = _make_user(role="read_only")
    app.dependency_overrides[get_db] = _override_db(user=user)
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "read_only"})

    resp = client.post(
        "/v1/slopes",
        json={
            "slope_id": "SLOPE_NEW",
            "name": "New Slope",
            "latitude_centroid": 3.15,
            "longitude_centroid": 101.71,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
