"""Tests for Edge local inference (Prompt 6.2)."""

import json
import os
import sys
import sqlite3
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from inference_engine import EdgeInferenceEngine
from feature_builder import build_edge_features
from alert_trigger import AlertTrigger


@pytest.fixture
def db_conn():
    """Create a temporary SQLite database with edge schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Apply edge schema
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "gateway_processor", "schema.sql",
    )
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    yield conn

    conn.close()
    os.unlink(db_path)


# ── Inference engine tests ──────────────────────────────────────────────


def test_engine_not_loaded():
    """Engine reports not loaded before loading."""
    engine = EdgeInferenceEngine()
    assert engine.is_model_loaded() is False


def test_engine_load_nonexistent():
    """Loading non-existent model returns False."""
    engine = EdgeInferenceEngine()
    result = engine.load_model("/nonexistent/model.tflite")
    assert result is False
    assert engine.is_model_loaded() is False


def test_engine_predict_not_loaded():
    """Predict raises error when model not loaded."""
    engine = EdgeInferenceEngine()
    with pytest.raises(RuntimeError, match="No model loaded"):
        engine.predict(np.zeros((1, 10, 5)))


# ── Feature builder tests ──────────────────────────────────────────────


def test_build_features_empty_db(db_conn):
    """Returns None when no readings in buffer."""
    result = build_edge_features(db_conn, "SLOPE-001", window_minutes=30)
    assert result is None


def test_build_features_with_data(db_conn):
    """Returns feature array when buffer has data."""
    # Insert some test readings
    for i in range(10):
        payload = json.dumps({
            "node_id": "A1",
            "sm1": 45.0 + i, "sm2": 50.0,
            "rn": 0.1, "tx": 0.5, "ty": 0.3,
            "bat": 12.4, "rssi": -85,
        })
        db_conn.execute(
            "INSERT INTO raw_readings (node_id, payload_json) VALUES (?, ?)",
            ("A1", payload),
        )
    db_conn.commit()

    result = build_edge_features(db_conn, "SLOPE-001", window_minutes=60)
    assert result is not None
    assert result.ndim == 3
    assert result.shape[0] == 1  # batch dimension
    assert result.shape[1] == 10  # 10 readings
    assert result.shape[2] == 15  # 15 sensor fields


# ── Alert trigger tests ─────────────────────────────────────────────────


def test_alert_trigger_red(db_conn):
    """RED score activates siren and logs alert."""
    trigger = AlertTrigger(db_conn, red_threshold=0.85)
    level = trigger.check_and_trigger(0.92)

    assert level == "RED"
    # Verify alert was logged
    cursor = db_conn.execute("SELECT * FROM local_alerts")
    alerts = cursor.fetchall()
    assert len(alerts) == 1
    assert alerts[0]["risk_level"] == "RED"
    assert alerts[0]["siren_activated"] == 1

    # Clean up timer
    trigger.deactivate_siren()


def test_alert_trigger_orange(db_conn):
    """ORANGE score logs alert without siren."""
    trigger = AlertTrigger(db_conn, red_threshold=0.85)
    level = trigger.check_and_trigger(0.72)

    assert level == "ORANGE"
    cursor = db_conn.execute("SELECT * FROM local_alerts")
    alerts = cursor.fetchall()
    assert len(alerts) == 1
    assert alerts[0]["siren_activated"] == 0


def test_alert_trigger_green(db_conn):
    """GREEN score does not log alert."""
    trigger = AlertTrigger(db_conn, red_threshold=0.85)
    level = trigger.check_and_trigger(0.15)

    assert level == "GREEN"
    cursor = db_conn.execute("SELECT * FROM local_alerts")
    assert len(cursor.fetchall()) == 0


def test_siren_deactivate(db_conn):
    """Siren can be deactivated."""
    trigger = AlertTrigger(db_conn)
    trigger.activate_siren()
    assert trigger._siren_active is True

    trigger.deactivate_siren()
    assert trigger._siren_active is False


def test_score_to_level():
    """Risk level mapping is correct."""
    assert AlertTrigger._score_to_level(0.0) == "GREEN"
    assert AlertTrigger._score_to_level(0.39) == "GREEN"
    assert AlertTrigger._score_to_level(0.40) == "YELLOW"
    assert AlertTrigger._score_to_level(0.64) == "YELLOW"
    assert AlertTrigger._score_to_level(0.65) == "ORANGE"
    assert AlertTrigger._score_to_level(0.84) == "ORANGE"
    assert AlertTrigger._score_to_level(0.85) == "RED"
    assert AlertTrigger._score_to_level(1.0) == "RED"
