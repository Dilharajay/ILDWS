"""Tests for Map, Users, System Health, Reports APIs (Prompt 2.5)."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.node_health_snapshots import NodeHealthSnapshot
from app.models.reports import Report
from app.models.sensor_nodes import SensorNode
from app.models.slopes import Slope
from app.models.users import User
from app.utils.security import create_access_token, hash_password

_HASHED = hash_password("pass123")


def _make_user(**overrides):
    user = MagicMock(spec=User)
    defaults = {
        "user_id": "USR001", "email": "admin@ilews.io",
        "name": "Admin", "role": "system_admin",
        "is_active": True, "password_hash": _HASHED,
        "organisation": "NDMC", "phone": "+601234",
        "is_sms_alert_enabled": False, "is_push_alert_enabled": False,
        "slope_access": None, "last_login_at": None,
        "created_at": datetime(2025, 7, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 7, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _auth_header(role="system_admin"):
    token = create_access_token({"sub": "USR001", "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.clear()


# ── Map API ──────────────────────────────────────────────────────────────


def test_map_data():
    """GET /v1/map/data returns nodes + risk zones."""
    user = _make_user()
    node = MagicMock(spec=SensorNode)
    node.node_id = "A1"
    node.slope_id = "SLOPE_BKT_01"
    node.latitude = Decimal("3.152")
    node.longitude = Decimal("101.712")
    node.last_seen = datetime(2026, 2, 28, 8, 25, tzinfo=timezone.utc)
    node.status = "active"
    node.is_deleted = False

    slope = MagicMock(spec=Slope)
    slope.slope_id = "SLOPE_BKT_01"
    slope.name = "Bukit Bintang"
    slope.latitude_centroid = Decimal("3.152")
    slope.longitude_centroid = Decimal("101.712")
    slope.zone_polygon = [[3.151, 101.711], [3.153, 101.713]]

    async def _get_db():
        session = AsyncMock()
        # 1: user lookup
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        # 2: nodes query
        nodes_result = MagicMock()
        n_scalars = MagicMock()
        n_scalars.all.return_value = [node]
        nodes_result.scalars.return_value = n_scalars
        # 3: slopes query
        slopes_result = MagicMock()
        s_scalars = MagicMock()
        s_scalars.all.return_value = [slope]
        slopes_result.scalars.return_value = s_scalars
        # 4: risk query (get_current_risk for slope → none)
        risk_result = MagicMock()
        risk_result.scalar_one_or_none.return_value = None
        session.execute.side_effect = [
            user_result, nodes_result, slopes_result, risk_result,
        ]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get("/v1/map/data", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert "nodes" in body["data"]
    assert "risk_zones" in body["data"]
    assert len(body["data"]["nodes"]) == 1


# ── Users API ────────────────────────────────────────────────────────────


def test_list_users():
    """GET /v1/users returns user list for admins."""
    admin = _make_user()
    user2 = _make_user(user_id="USR002", email="op@ilews.io", role="operator")

    async def _get_db():
        session = AsyncMock()
        # 1: user auth lookup
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = admin
        # 2: count
        count_result = MagicMock()
        count_result.scalar.return_value = 2
        # 3: list
        list_result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = [admin, user2]
        list_result.scalars.return_value = scalars
        session.execute.side_effect = [user_result, count_result, list_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get("/v1/users", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 2


def test_list_users_forbidden_for_operator():
    """GET /v1/users returns 403 for non-admin."""
    user = _make_user(role="operator")

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.return_value = user_result
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    token = create_access_token({"sub": "USR001", "role": "operator"})
    resp = client.get("/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_create_user():
    """POST /v1/users creates a new user."""
    admin = _make_user()

    async def _get_db():
        session = AsyncMock()
        # 1: admin auth
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = admin
        # 2: email duplicate check
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = None
        session.execute.side_effect = [admin_result, dup_result]

        async def _refresh(obj):
            if hasattr(obj, "user_id"):
                obj.is_active = True
                obj.is_sms_alert_enabled = False
                obj.is_push_alert_enabled = False
                obj.slope_access = None
                obj.last_login_at = None
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)

        session.refresh.side_effect = _refresh
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.post(
        "/v1/users",
        json={
            "email": "new@uni.edu",
            "name": "Dr New",
            "role": "analyst",
            "password": "secure-pass!",
        },
        headers=_auth_header(),
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["role"] == "analyst"


def test_deactivate_user():
    """DELETE /v1/users/{id} deactivates user."""
    admin = _make_user()
    target = _make_user(user_id="USR002", email="target@ilews.io")

    async def _get_db():
        session = AsyncMock()
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = admin
        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = target
        session.execute.side_effect = [admin_result, target_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.delete("/v1/users/USR002", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["data"]["deactivated"] is True


# ── System Health API ────────────────────────────────────────────────────


def test_system_health():
    """GET /v1/system/health returns system status."""
    user = _make_user(role="operator")

    async def _get_db():
        session = AsyncMock()
        # 1: user auth
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        # 2: SELECT 1
        one_result = MagicMock()
        # 3-6: four count queries (total, active, offline, error)
        count1 = MagicMock()
        count1.scalar.return_value = 5
        count2 = MagicMock()
        count2.scalar.return_value = 4
        count3 = MagicMock()
        count3.scalar.return_value = 1
        count4 = MagicMock()
        count4.scalar.return_value = 0
        session.execute.side_effect = [
            user_result, one_result, count1, count2, count3, count4,
        ]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    token = create_access_token({"sub": "USR001", "role": "operator"})
    resp = client.get(
        "/v1/system/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["services"]["fastapi_backend"] == "healthy"
    assert body["data"]["node_summary"]["total"] == 5


def test_node_health():
    """GET /v1/nodes/{id}/health returns latest snapshot."""
    user = _make_user(role="operator")
    snapshot = MagicMock(spec=NodeHealthSnapshot)
    snapshot.node_id = "A1"
    snapshot.connectivity_status = "online"
    snapshot.timestamp = datetime(2026, 2, 28, 8, 25, tzinfo=timezone.utc)
    snapshot.battery_voltage_v = Decimal("12.4")
    snapshot.solar_input_w = Decimal("3.2")
    snapshot.firmware_version = "1.3.2"
    snapshot.enclosure_temp_c = Decimal("34.2")
    snapshot.rssi_dbm_avg = -85

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        snap_result = MagicMock()
        snap_result.scalar_one_or_none.return_value = snapshot
        session.execute.side_effect = [user_result, snap_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    token = create_access_token({"sub": "USR001", "role": "operator"})
    resp = client.get(
        "/v1/nodes/A1/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["connectivity"] == "online"


# ── Reports API ──────────────────────────────────────────────────────────


def test_generate_report():
    """POST /v1/reports/generate creates a queued report."""
    user = _make_user(role="analyst")

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [user_result]

        async def _refresh(obj):
            if hasattr(obj, "report_id"):
                obj.status = "queued"
                obj.created_at = datetime.now(timezone.utc)
                obj.output_format = "pdf"
                obj.download_url = None
                obj.url_expires_at = None
                obj.file_size_bytes = None
                obj.error_message = None
                obj.generated_at = None

        session.refresh.side_effect = _refresh
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    token = create_access_token({"sub": "USR001", "role": "analyst"})
    resp = client.post(
        "/v1/reports/generate",
        json={
            "report_type": "weekly_summary",
            "slope_ids": ["SLOPE_BKT_01"],
            "start_date": "2026-02-21",
            "end_date": "2026-02-28",
            "format": "pdf",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    assert resp.json()["data"]["status"] == "queued"


def test_get_report():
    """GET /v1/reports/{id} returns report status."""
    user = _make_user(role="analyst")
    report = MagicMock(spec=Report)
    report.report_id = "RPT-2026-00321"
    report.report_type = "weekly_summary"
    report.requested_by = "admin@ilews.io"
    report.slope_ids = ["SLOPE_BKT_01"]
    report.start_date = None
    report.end_date = None
    report.output_format = "pdf"
    report.status = "ready"
    report.download_url = "https://storage.ilews.gov/reports/RPT-2026-00321.pdf"
    report.url_expires_at = None
    report.file_size_bytes = 12345
    report.error_message = None
    report.generated_at = datetime(2026, 2, 28, 9, 0, tzinfo=timezone.utc)
    report.created_at = datetime(2026, 2, 28, 8, 30, tzinfo=timezone.utc)

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        report_result = MagicMock()
        report_result.scalar_one_or_none.return_value = report
        session.execute.side_effect = [user_result, report_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    token = create_access_token({"sub": "USR001", "role": "analyst"})
    resp = client.get(
        "/v1/reports/RPT-2026-00321",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "ready"
