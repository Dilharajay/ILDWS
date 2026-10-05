"""Tests for ETL Processor validator and deduplicator (Prompt 3.1)."""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from app.validator import validate_packet
from app.deduplicator import is_duplicate


# ── Validator tests ──────────────────────────────────────────────────────


def _valid_packet(**overrides):
    """Build a valid sensor packet with sensible defaults."""
    now = datetime.now(timezone.utc)
    pkt = {
        "node_id": "A1",
        "ts": now.isoformat(),
        "bat": 12.4,
        "rssi": -85,
        "sm1": 45.2,
        "sm2": 52.1,
        "rn": 0.2,
        "tx": 0.01,
        "ty": 0.00,
    }
    pkt.update(overrides)
    return pkt


def test_valid_packet_passes():
    """A complete, valid packet passes validation."""
    ok, issues, data = validate_packet(_valid_packet())
    assert ok is True
    assert issues == []
    assert data["node_id"] == "A1"
    assert "ts" in data


def test_missing_required_field():
    """Packet missing node_id fails validation."""
    pkt = _valid_packet()
    del pkt["node_id"]
    ok, issues, data = validate_packet(pkt)
    assert ok is False
    assert any("node_id" in i for i in issues)


def test_missing_battery():
    """Packet missing bat field fails validation."""
    pkt = _valid_packet()
    del pkt["bat"]
    ok, issues, data = validate_packet(pkt)
    assert ok is False
    assert any("bat" in i for i in issues)


def test_missing_rssi():
    """Packet missing rssi field fails validation."""
    pkt = _valid_packet()
    del pkt["rssi"]
    ok, issues, data = validate_packet(pkt)
    assert ok is False
    assert any("rssi" in i for i in issues)


def test_nan_numeric_field():
    """NaN in battery voltage fails validation."""
    pkt = _valid_packet(bat=float("nan"))
    ok, issues, data = validate_packet(pkt)
    assert ok is False
    assert any("battery" in i.lower() or "bat" in i.lower() for i in issues)


def test_soil_moisture_out_of_range():
    """Soil moisture > 100 fails validation."""
    pkt = _valid_packet(sm1=150.0)
    ok, issues, data = validate_packet(pkt)
    assert ok is False
    assert any("sm1" in i for i in issues)


def test_battery_out_of_range_low():
    """Battery < 7.0 fails validation."""
    pkt = _valid_packet(bat=3.0)
    ok, issues, data = validate_packet(pkt)
    assert ok is False
    assert any("bat" in i for i in issues)


def test_battery_out_of_range_high():
    """Battery > 15.0 fails validation."""
    pkt = _valid_packet(bat=20.0)
    ok, issues, data = validate_packet(pkt)
    assert ok is False


def test_tilt_out_of_range():
    """Tilt > 90 fails validation."""
    pkt = _valid_packet(tx=100.0)
    ok, issues, data = validate_packet(pkt)
    assert ok is False
    assert any("tx" in i for i in issues)


def test_stale_timestamp_rejected():
    """Timestamp older than 5 minutes is rejected."""
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    pkt = _valid_packet(ts=old_ts)
    ok, issues, data = validate_packet(pkt)
    assert ok is False
    assert any("stale" in i.lower() for i in issues)


def test_unix_timestamp_supported():
    """Unix epoch timestamps are accepted."""
    now_unix = datetime.now(timezone.utc).timestamp()
    pkt = _valid_packet(ts=now_unix)
    ok, issues, data = validate_packet(pkt)
    assert ok is True


def test_optional_fields_not_required():
    """Packet with only required fields passes."""
    now = datetime.now(timezone.utc)
    pkt = {"node_id": "A1", "ts": now.isoformat(), "bat": 12.4, "rssi": -85}
    ok, issues, data = validate_packet(pkt)
    assert ok is True
    assert len(issues) == 0


# ── Deduplicator tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_packet_not_duplicate():
    """First occurrence of a packet is not a duplicate."""
    redis_mock = AsyncMock()
    redis_mock.exists.return_value = 0
    redis_mock.set.return_value = True

    result = await is_duplicate(redis_mock, "A1", "2026-02-28T08:25:00Z")
    assert result is False
    redis_mock.set.assert_called_once()


@pytest.mark.asyncio
async def test_second_packet_is_duplicate():
    """Second occurrence of same node+minute is a duplicate."""
    redis_mock = AsyncMock()
    redis_mock.exists.return_value = 1

    result = await is_duplicate(redis_mock, "A1", "2026-02-28T08:25:00Z")
    assert result is True
    redis_mock.set.assert_not_called()


@pytest.mark.asyncio
async def test_redis_failure_allows_packet():
    """If Redis is unavailable, packet is allowed through."""
    redis_mock = AsyncMock()
    redis_mock.exists.side_effect = Exception("Redis down")

    result = await is_duplicate(redis_mock, "A1", "2026-02-28T08:25:00Z")
    assert result is False
