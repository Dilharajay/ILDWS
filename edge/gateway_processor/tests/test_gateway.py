"""Tests for Edge Gateway Processor (Prompt 6.1)."""

import json
import os
import sys
import sqlite3
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from buffer import init_db, write_reading, get_unsynced, mark_synced, get_pending_count, log_local_alert
from validator import validate_packet
from connectivity import check_internet


@pytest.fixture
def db_conn():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    with patch("buffer.settings") as mock_settings:
        mock_settings.SQLITE_PATH = db_path
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schema.sql",
        )
        with open(schema_path, "r") as f:
            conn.executescript(f.read())

        yield conn

        conn.close()
        os.unlink(db_path)


# ── Buffer tests ────────────────────────────────────────────────────────


def test_write_and_read(db_conn):
    """Write a reading and retrieve it as unsynced."""
    payload = json.dumps({"node_id": "A1", "bat": 12.4})
    row_id = write_reading(db_conn, payload, "A1")
    assert row_id > 0

    unsynced = get_unsynced(db_conn, limit=10)
    assert len(unsynced) == 1
    assert unsynced[0]["node_id"] == "A1"
    assert json.loads(unsynced[0]["payload_json"]) == {"node_id": "A1", "bat": 12.4}


def test_mark_synced(db_conn):
    """Synced records are no longer returned by get_unsynced."""
    write_reading(db_conn, '{"a": 1}', "A1")
    write_reading(db_conn, '{"a": 2}', "A2")

    unsynced = get_unsynced(db_conn)
    assert len(unsynced) == 2

    mark_synced(db_conn, [unsynced[0]["id"]])

    remaining = get_unsynced(db_conn)
    assert len(remaining) == 1
    assert remaining[0]["node_id"] == "A2"


def test_pending_count(db_conn):
    """Pending count reflects unsynced records."""
    assert get_pending_count(db_conn) == 0
    write_reading(db_conn, '{}', "A1")
    write_reading(db_conn, '{}', "A2")
    assert get_pending_count(db_conn) == 2

    unsynced = get_unsynced(db_conn)
    mark_synced(db_conn, [r["id"] for r in unsynced])
    assert get_pending_count(db_conn) == 0


def test_log_local_alert(db_conn):
    """Local alert is persisted to SQLite."""
    alert_id = log_local_alert(db_conn, 0.92, "RED", siren_activated=True)
    assert alert_id > 0

    cursor = db_conn.execute("SELECT * FROM local_alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()
    assert row["risk_score"] == 0.92
    assert row["risk_level"] == "RED"
    assert row["siren_activated"] == 1


# ── Validator tests ─────────────────────────────────────────────────────


def test_valid_packet():
    """Valid packet passes validation."""
    now = datetime.now(timezone.utc)
    pkt = {"node_id": "A1", "ts": now.isoformat(), "bat": 12.4, "rssi": -85}
    ok, issues, data = validate_packet(pkt)
    assert ok is True
    assert issues == []


def test_missing_node_id():
    """Missing node_id fails."""
    now = datetime.now(timezone.utc)
    pkt = {"ts": now.isoformat(), "bat": 12.4, "rssi": -85}
    ok, issues, _ = validate_packet(pkt)
    assert ok is False
    assert any("node_id" in i for i in issues)


def test_stale_packet():
    """Stale timestamp fails."""
    from datetime import timedelta
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    pkt = {"node_id": "A1", "ts": old.isoformat(), "bat": 12.4, "rssi": -85}
    ok, issues, _ = validate_packet(pkt)
    assert ok is False
    assert any("stale" in i.lower() for i in issues)


# ── Connectivity test ───────────────────────────────────────────────────


def test_connectivity_checker():
    """Connectivity check returns a boolean."""
    result = check_internet(timeout=1)
    assert isinstance(result, bool)
