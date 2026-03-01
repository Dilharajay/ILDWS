"""Tests for the ILEWS Sensor Readings API (Prompt 2.3)."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.sensor_readings import SensorReading
from app.models.users import User
from app.utils.security import create_access_token, hash_password

_HASHED = hash_password("pass123")


def _make_user(**overrides):
    user = MagicMock(spec=User)
    defaults = {
        "user_id": "USR001",
        "email": "test@ilews.io",
        "name": "Test User",
        "role": "operator",
        "is_active": True,
        "password_hash": _HASHED,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_reading(**overrides):
    reading = MagicMock(spec=SensorReading)
    defaults = {
        "reading_id": 1,
        "node_id": "A1",
        "slope_id": "SLOPE_BKT_01",
        "timestamp": datetime(2026, 2, 28, 8, 25, 0, tzinfo=timezone.utc),
        "received_at": datetime(2026, 2, 28, 8, 25, 1, tzinfo=timezone.utc),
        "packet_id": "abc123",
        "soil_moisture_d1_pct": Decimal("45.20"),
        "soil_moisture_d2_pct": Decimal("52.10"),
        "soil_moisture_d3_pct": Decimal("60.80"),
        "soil_moisture_d4_pct": None,
        "soil_moisture_d5_pct": None,
        "rainfall_mm": Decimal("0.20"),
        "tilt_x_deg": Decimal("0.0100"),
        "tilt_y_deg": Decimal("0.0000"),
        "accel_x_ms2": Decimal("0.0200"),
        "accel_y_ms2": Decimal("0.0100"),
        "accel_z_ms2": Decimal("9.8100"),
        "vibration_hz": Decimal("12.500"),
        "vibration_amplitude": None,
        "battery_voltage_v": Decimal("12.40"),
        "solar_input_w": None,
        "rssi_dbm": -85,
        "data_quality": "valid",
        "source": "lora",
        "quality_flags": None,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(reading, k, v)
    return reading


def _token(role="operator"):
    return create_access_token({"sub": "USR001", "role": role})


def _auth_header(role="operator"):
    return {"Authorization": f"Bearer {_token(role)}"}


def _override_db(user=None, readings=None, scalar_values=None):
    """DB override. scalar_values is a list of return values for sequential
    execute() calls (each is scalar_one_or_none result)."""

    async def _get_db():
        session = AsyncMock()

        if scalar_values is not None:
            # Multiple sequential execute calls
            results = []
            for val in scalar_values:
                result = MagicMock()
                result.scalar_one_or_none.return_value = val
                result.scalar.return_value = val if isinstance(val, int) else 0
                scalars = MagicMock()
                scalars.all.return_value = val if isinstance(val, list) else []
                result.scalars.return_value = scalars
                results.append(result)
            session.execute.side_effect = results
        else:
            result = MagicMock()
            if user is not None:
                result.scalar_one_or_none.return_value = user
            if readings is not None:
                scalars = MagicMock()
                scalars.all.return_value = readings
                result.scalars.return_value = scalars
                result.scalar.return_value = len(readings)
            session.execute.return_value = result

        # refresh populates server defaults
        async def _refresh(obj):
            if hasattr(obj, "reading_id") and obj.reading_id is None:
                obj.reading_id = 99
            if hasattr(obj, "received_at") and obj.received_at is None:
                obj.received_at = datetime.now(timezone.utc)

        session.refresh.side_effect = _refresh
        yield session

    return _get_db


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


# ── Ingest + Retrieve ────────────────────────────────────────────────────


def test_ingest_reading_success():
    """POST /v1/internal/readings with valid API key creates a reading."""
    user = _make_user()

    async def _get_db():
        session = AsyncMock()
        # First execute: dedup check → no existing
        dedup_result = MagicMock()
        dedup_result.scalar_one_or_none.return_value = None
        session.execute.return_value = dedup_result

        async def _refresh(obj):
            obj.reading_id = 99
            obj.received_at = datetime.now(timezone.utc)

        session.refresh.side_effect = _refresh
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.post(
        "/v1/internal/readings",
        json={
            "node_id": "A1",
            "slope_id": "SLOPE_BKT_01",
            "timestamp": "2026-02-28T08:25:00Z",
            "packet_id": "abc123",
            "soil_moisture_d1_pct": 45.2,
            "rainfall_mm": 0.2,
            "battery_voltage_v": 12.4,
            "rssi_dbm": -85,
            "data_quality": "valid",
            "source": "lora",
        },
        headers={"X-Service-Api-Key": "change-me-service-key"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["node_id"] == "A1"


def test_ingest_reading_invalid_api_key():
    """POST /v1/internal/readings with bad key returns 401."""
    client = TestClient(app)

    resp = client.post(
        "/v1/internal/readings",
        json={
            "node_id": "A1",
            "slope_id": "SLOPE_BKT_01",
            "timestamp": "2026-02-28T08:25:00Z",
        },
        headers={"X-Service-Api-Key": "wrong-key"},
    )

    assert resp.status_code == 401


def test_ingest_duplicate_reading():
    """POST /v1/internal/readings with duplicate packet_id returns 409."""
    existing = _make_reading()

    async def _get_db():
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        session.execute.return_value = result
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.post(
        "/v1/internal/readings",
        json={
            "node_id": "A1",
            "slope_id": "SLOPE_BKT_01",
            "timestamp": "2026-02-28T08:25:00Z",
            "packet_id": "abc123",
        },
        headers={"X-Service-Api-Key": "change-me-service-key"},
    )

    assert resp.status_code == 409


def test_get_latest_reading():
    """GET /v1/nodes/{node_id}/readings/latest returns most recent reading."""
    user = _make_user()
    reading = _make_reading()

    async def _get_db():
        session = AsyncMock()
        # First call: get_current_user lookup
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        # Second call: latest reading query
        reading_result = MagicMock()
        reading_result.scalar_one_or_none.return_value = reading
        session.execute.side_effect = [user_result, reading_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get(
        "/v1/nodes/A1/readings/latest",
        headers=_auth_header(),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["node_id"] == "A1"


def test_get_latest_reading_not_found():
    """GET /v1/nodes/{node_id}/readings/latest returns 404 for no readings."""
    user = _make_user()

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        reading_result = MagicMock()
        reading_result.scalar_one_or_none.return_value = None
        session.execute.side_effect = [user_result, reading_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get(
        "/v1/nodes/NONODE/readings/latest",
        headers=_auth_header(),
    )

    assert resp.status_code == 404


def test_get_readings_history():
    """GET /v1/nodes/{id}/readings returns paginated list."""
    user = _make_user()
    r1 = _make_reading(reading_id=1)
    r2 = _make_reading(reading_id=2)

    async def _get_db():
        session = AsyncMock()
        # 1st: user lookup
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        # 2nd: count query
        count_result = MagicMock()
        count_result.scalar.return_value = 2
        # 3rd: readings query
        readings_result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = [r1, r2]
        readings_result.scalars.return_value = scalars
        session.execute.side_effect = [user_result, count_result, readings_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get(
        "/v1/nodes/A1/readings",
        params={
            "start_time": "2026-02-27T00:00:00Z",
            "end_time": "2026-02-28T23:59:59Z",
        },
        headers=_auth_header(),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 2
    assert body["meta"]["total"] == 2


def test_get_readings_without_auth():
    """GET /v1/nodes/{id}/readings/latest without token returns 401."""
    client = TestClient(app)

    resp = client.get("/v1/nodes/A1/readings/latest")

    assert resp.status_code == 401


def test_get_slope_latest_readings():
    """GET /v1/slopes/{slope_id}/readings/latest returns readings per node."""
    user = _make_user()

    async def _get_db():
        session = AsyncMock()
        # 1st: user lookup
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        # 2nd: DISTINCT ON query
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = [
            {"node_id": "A1", "slope_id": "SLOPE_BKT_01", "rainfall_mm": 0.2},
            {"node_id": "A2", "slope_id": "SLOPE_BKT_01", "rainfall_mm": 0.5},
        ]
        session.execute.side_effect = [user_result, rows_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get(
        "/v1/slopes/SLOPE_BKT_01/readings/latest",
        headers=_auth_header(),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 2


# ── Cache hit vs miss ────────────────────────────────────────────────────


def test_cache_hit_returns_cached_data():
    """get_latest_reading returns cached data from Redis mock."""
    import json
    from app.services.reading_service import get_latest_reading

    cached = json.dumps({"node_id": "A1", "cached": True})
    redis_mock = AsyncMock()
    redis_mock.get.return_value = cached
    db_mock = AsyncMock()

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        get_latest_reading(db_mock, "A1", redis=redis_mock)
    )

    assert result["cached"] is True
    db_mock.execute.assert_not_called()


def test_cache_miss_queries_db():
    """get_latest_reading queries DB when Redis returns None."""
    from app.services.reading_service import get_latest_reading

    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True

    reading = _make_reading()
    db_mock = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = reading
    db_mock.execute.return_value = exec_result

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        get_latest_reading(db_mock, "A1", redis=redis_mock)
    )

    assert result["node_id"] == "A1"
    db_mock.execute.assert_called_once()
    redis_mock.set.assert_called_once()
