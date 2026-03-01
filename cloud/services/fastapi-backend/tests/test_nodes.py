"""Tests for ILEWS Sensor Nodes CRUD API (/v1/nodes)."""

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.sensor_nodes import SensorNode
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


def _make_node(**kw):
    n = MagicMock(spec=SensorNode)
    now = datetime.now(timezone.utc)
    defaults = {
        "node_id": "A1",
        "slope_id": "SLOPE_TEST_01",
        "name": "Node Alpha-1",
        "latitude": Decimal("3.1520"),
        "longitude": Decimal("101.7120"),
        "depth_config": [0.5, 1.0, 2.0],
        "coordinate_source": "topographic_survey",
        "survey_reference": None,
        "firmware_version": "1.3.2",
        "hardware_revision": "v2",
        "installed_date": None,
        "last_maintenance_at": None,
        "status": "active",
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kw)
    for k, v in defaults.items():
        setattr(n, k, v)
    return n


def _override_db(user=None, nodes=None, scalar_chain=None):
    """Override get_db.  scalar_chain is a list of return values for
    successive scalar_one_or_none() calls."""

    async def _get_db():
        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()

        chain = list(scalar_chain) if scalar_chain else []
        if user is not None and not chain:
            chain = [user, None]
        result_mock.scalar_one_or_none.side_effect = chain
        result_mock.scalar.return_value = len(nodes) if nodes else 0
        scalars_mock.all.return_value = nodes or []
        result_mock.scalars.return_value = scalars_mock

        session.execute.return_value = result_mock
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        yield session

    return _get_db


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.clear()


# ── Tests ────────────────────────────────────────────────────────────────

def test_list_nodes_success():
    user = _make_user()
    node = _make_node()
    app.dependency_overrides[get_db] = _override_db(
        nodes=[node], scalar_chain=[user],
    )
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "system_admin"})

    resp = client.get("/v1/nodes", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 1
    assert body["data"][0]["node_id"] == "A1"
    assert "meta" in body


def test_list_nodes_requires_auth():
    client = TestClient(app)
    resp = client.get("/v1/nodes")
    assert resp.status_code == 401


def test_get_node_not_found():
    user = _make_user()
    app.dependency_overrides[get_db] = _override_db(
        scalar_chain=[user, None],
    )
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "system_admin"})

    resp = client.get(
        "/v1/nodes/GHOST",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["status"] == "error"


def test_create_node_success():
    user = _make_user()
    slope = MagicMock(spec=Slope)

    async def _get_db():
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.side_effect = [user, slope, None]
        session.execute.return_value = result_mock
        session.flush = AsyncMock()
        session.commit = AsyncMock()

        def _refresh(obj):
            now = datetime.now(timezone.utc)
            obj.status = obj.status or "active"
            obj.is_deleted = obj.is_deleted if obj.is_deleted is not None else False
            obj.created_at = now
            obj.updated_at = now

        session.refresh = AsyncMock(side_effect=_refresh)
        session.add = MagicMock()
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "system_admin"})

    resp = client.post(
        "/v1/nodes",
        json={
            "node_id": "B5",
            "slope_id": "SLOPE_TEST_01",
            "latitude": 3.15,
            "longitude": 101.71,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "success"


def test_create_node_slope_not_found():
    user = _make_user()
    app.dependency_overrides[get_db] = _override_db(
        scalar_chain=[user, None],  # user found, slope NOT found
    )
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "system_admin"})

    resp = client.post(
        "/v1/nodes",
        json={
            "node_id": "C1",
            "slope_id": "NONEXISTENT",
            "latitude": 3.15,
            "longitude": 101.71,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_delete_node_success():
    user = _make_user()
    node = _make_node()
    app.dependency_overrides[get_db] = _override_db(
        scalar_chain=[user, node],
    )
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "system_admin"})

    resp = client.delete(
        "/v1/nodes/A1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted"] is True


def test_create_node_forbidden_for_readonly():
    user = _make_user(role="read_only")
    app.dependency_overrides[get_db] = _override_db(scalar_chain=[user])
    client = TestClient(app)
    token = create_access_token({"sub": "USR-0001", "role": "read_only"})

    resp = client.post(
        "/v1/nodes",
        json={
            "node_id": "X1",
            "slope_id": "SLOPE_TEST_01",
            "latitude": 3.15,
            "longitude": 101.71,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
