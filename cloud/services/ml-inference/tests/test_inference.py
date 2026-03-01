"""Tests for ML Inference Service (Prompt 5.3)."""

import numpy as np
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.scorer import _score_to_risk_level, score_slope
from app.feature_builder import build_live_features
from app.model_loader import get_model_info
from app.main import app


client = TestClient(app)


# ── Risk level mapping tests ────────────────────────────────────────────


def test_score_to_risk_green():
    """Score <= 0.39 maps to GREEN."""
    assert _score_to_risk_level(0.0) == "GREEN"
    assert _score_to_risk_level(0.39) == "GREEN"


def test_score_to_risk_yellow():
    """Score 0.40-0.64 maps to YELLOW."""
    assert _score_to_risk_level(0.40) == "YELLOW"
    assert _score_to_risk_level(0.64) == "YELLOW"


def test_score_to_risk_orange():
    """Score 0.65-0.84 maps to ORANGE."""
    assert _score_to_risk_level(0.65) == "ORANGE"
    assert _score_to_risk_level(0.84) == "ORANGE"


def test_score_to_risk_red():
    """Score > 0.84 maps to RED."""
    assert _score_to_risk_level(0.85) == "RED"
    assert _score_to_risk_level(1.0) == "RED"


# ── Feature builder tests ───────────────────────────────────────────────


def test_build_features_insufficient_data():
    """Returns None when not enough readings."""
    result = build_live_features([{"val": 1}], timesteps=96)
    assert result is None


def test_build_features_empty():
    """Returns None for empty readings."""
    result = build_live_features([], timesteps=10)
    assert result is None


def test_build_features_adequate_data():
    """Returns valid feature array with enough readings."""
    rng = np.random.default_rng(42)
    n = 120
    readings = []
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)

    for i in range(n):
        from datetime import timedelta
        ts = base + timedelta(minutes=15 * i)
        readings.append({
            "timestamp": ts.isoformat(),
            "soil_moisture_1_pct": rng.uniform(20, 80),
            "rainfall_mm": rng.exponential(0.5),
            "tilt_x_deg": rng.normal(0, 2),
            "tilt_y_deg": rng.normal(0, 1),
        })

    result = build_live_features(readings, timesteps=50)
    assert result is not None
    assert result.ndim == 3
    assert result.shape[0] == 1
    assert result.shape[1] == 50


# ── API endpoint tests ──────────────────────────────────────────────────


def test_health_endpoint():
    """GET /health returns success."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["service"] == "ml-inference"


def test_status_endpoint():
    """GET /status returns model and inference info."""
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "model" in data["data"]
    assert "last_inference" in data["data"]
    assert "score_interval_minutes" in data["data"]


def test_metrics_endpoint():
    """GET /metrics returns prometheus format."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "ilews_ml_" in resp.text or "python_" in resp.text


# ── Scorer tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_score_slope_no_model():
    """Scoring without model returns error."""
    mock_client = AsyncMock()

    with patch("app.scorer.get_model", return_value=None):
        result = await score_slope(mock_client, "SLOPE-001")
        assert "error" in result
        assert result["error"] == "model_not_loaded"


@pytest.mark.asyncio
async def test_score_slope_no_readings():
    """Scoring with no available readings returns error."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": []}
    mock_client.get.return_value = mock_resp

    mock_model = MagicMock()
    with patch("app.scorer.get_model", return_value=mock_model):
        result = await score_slope(mock_client, "SLOPE-001")
        assert "error" in result
        assert result["error"] == "no_readings"


# ── Model info tests ────────────────────────────────────────────────────


def test_model_info_default():
    """Default model info shows not loaded."""
    info = get_model_info()
    assert "loaded" in info
    assert "version" in info
    assert "source" in info
