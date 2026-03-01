"""Tests for the ILEWS Risk Scores API (Prompt 2.4)."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.risk_scores import RiskScore
from app.models.slopes import Slope
from app.models.users import User
from app.utils.security import create_access_token, hash_password

_HASHED = hash_password("pass123")


def _make_user(**overrides):
    user = MagicMock(spec=User)
    defaults = {
        "user_id": "USR001", "email": "test@ilews.io",
        "name": "Test User", "role": "operator",
        "is_active": True, "password_hash": _HASHED,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_risk(**overrides):
    r = MagicMock(spec=RiskScore)
    defaults = {
        "score_id": 1,
        "slope_id": "SLOPE_BKT_01",
        "timestamp": datetime(2026, 2, 28, 8, 15, 0, tzinfo=timezone.utc),
        "risk_score": Decimal("0.720"),
        "risk_level": "ORANGE",
        "model_version": "lstm_v3.1.2",
        "inference_source": "cloud",
        "contributing_nodes": ["A1", "A2", "A3"],
        "model_confidence": Decimal("0.850"),
        "created_at": datetime(2026, 2, 28, 8, 15, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(r, k, v)
    return r


def _auth_header(role="operator"):
    token = create_access_token({"sub": "USR001", "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.clear()


def test_get_current_risk():
    """GET /v1/slopes/{slope_id}/risk returns latest risk score."""
    user = _make_user()
    risk = _make_risk()

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        risk_result = MagicMock()
        risk_result.scalar_one_or_none.return_value = risk
        session.execute.side_effect = [user_result, risk_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get("/v1/slopes/SLOPE_BKT_01/risk", headers=_auth_header())

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["risk_level"] == "ORANGE"


def test_get_current_risk_not_found():
    """GET /v1/slopes/{id}/risk returns 404 when no risk data."""
    user = _make_user()

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        risk_result = MagicMock()
        risk_result.scalar_one_or_none.return_value = None
        session.execute.side_effect = [user_result, risk_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get("/v1/slopes/NOEXIST/risk", headers=_auth_header())

    assert resp.status_code == 404


def test_get_risk_history():
    """GET /v1/slopes/{id}/risk/history returns paginated list."""
    user = _make_user()
    r1 = _make_risk(score_id=1)
    r2 = _make_risk(score_id=2)

    async def _get_db():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        count_result = MagicMock()
        count_result.scalar.return_value = 2
        rows_result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = [r1, r2]
        rows_result.scalars.return_value = scalars
        session.execute.side_effect = [user_result, count_result, rows_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get(
        "/v1/slopes/SLOPE_BKT_01/risk/history",
        params={"start_time": "2026-02-01T00:00:00Z", "end_time": "2026-03-01T00:00:00Z"},
        headers=_auth_header(),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total"] == 2


def test_get_risk_requires_auth():
    """GET /v1/slopes/{id}/risk without token returns 401."""
    client = TestClient(app)
    resp = client.get("/v1/slopes/SLOPE_BKT_01/risk")
    assert resp.status_code == 401


def test_risk_overview():
    """GET /v1/slopes/risk/overview returns risk for all slopes."""
    user = _make_user()
    slope = MagicMock(spec=Slope)
    slope.slope_id = "SLOPE_BKT_01"
    slope.name = "Bukit Bintang"
    slope.latitude_centroid = Decimal("3.152")
    slope.longitude_centroid = Decimal("101.712")

    risk = _make_risk()

    async def _get_db():
        session = AsyncMock()
        # 1: user lookup
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        # 2: select all slopes
        slopes_result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = [slope]
        slopes_result.scalars.return_value = scalars
        # 3: get_current_risk for slope
        risk_result = MagicMock()
        risk_result.scalar_one_or_none.return_value = risk
        session.execute.side_effect = [user_result, slopes_result, risk_result]
        yield session

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)

    resp = client.get("/v1/slopes/risk/overview", headers=_auth_header())

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 1
    assert body["data"][0]["slope_id"] == "SLOPE_BKT_01"
    assert body["data"][0]["risk_level"] == "ORANGE"
