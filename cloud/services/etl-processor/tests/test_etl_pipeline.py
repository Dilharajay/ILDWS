"""Tests for ETL Processor – enricher, writer, MQTT pipeline (Prompt 3.2)."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.enricher import enrich_packet, generate_packet_id, FIELD_MAP
from app.writer import post_reading, write_with_retry, _retry_queue
from app.main import process_message


# ── Enricher tests ──────────────────────────────────────────────────────


def test_generate_packet_id_deterministic():
    """Same inputs produce same packet_id."""
    id1 = generate_packet_id("A1", "2026-01-01T00:00:00Z", '{"bat":12}')
    id2 = generate_packet_id("A1", "2026-01-01T00:00:00Z", '{"bat":12}')
    assert id1 == id2
    assert len(id1) == 40


def test_generate_packet_id_different_inputs():
    """Different inputs produce different packet_ids."""
    id1 = generate_packet_id("A1", "2026-01-01T00:00:00Z", '{"bat":12}')
    id2 = generate_packet_id("A2", "2026-01-01T00:00:00Z", '{"bat":12}')
    assert id1 != id2


def test_enrich_maps_short_fields():
    """Short field names are mapped to full DB column names."""
    cleaned = {
        "node_id": "A1",
        "ts": "2026-01-01T00:00:00Z",
        "bat": 12.4,
        "rssi": -85,
        "sm1": 45.2,
        "rn": 0.5,
        "tx": 1.2,
    }
    result = enrich_packet(cleaned, "SLOPE-001", json.dumps(cleaned))

    assert result["node_id"] == "A1"
    assert result["slope_id"] == "SLOPE-001"
    assert result["soil_moisture_d1_pct"] == 45.2
    assert result["rainfall_mm"] == 0.5
    assert result["tilt_x_deg"] == 1.2
    assert result["battery_voltage_v"] == 12.4
    assert result["rssi_dbm"] == -85
    assert "packet_id" in result
    assert "received_at" in result
    assert result["data_quality"] == "valid"
    assert result["source"] == "lora"


def test_enrich_preserves_timestamp():
    """Enrichment preserves original timestamp."""
    cleaned = {
        "node_id": "A1",
        "ts": "2026-02-15T10:30:00Z",
        "bat": 12.0,
        "rssi": -90,
    }
    result = enrich_packet(cleaned, "SLOPE-002", json.dumps(cleaned))
    assert result["timestamp"] == "2026-02-15T10:30:00Z"


def test_enrich_handles_all_fields():
    """All known short fields are mapped."""
    cleaned = {
        "node_id": "A1",
        "ts": "2026-01-01T00:00:00Z",
        "bat": 12.0,
        "rssi": -85,
    }
    # Add all short fields
    for short in FIELD_MAP:
        if short not in cleaned:
            cleaned[short] = 1.0

    result = enrich_packet(cleaned, "SLOPE-001", json.dumps(cleaned))
    for short, full in FIELD_MAP.items():
        assert full in result, f"Missing {full} (from {short})"


# ── Writer tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_reading_success():
    """Successful POST returns True."""
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    client.post.return_value = mock_resp

    result = await post_reading(client, {"node_id": "A1"})
    assert result is True


@pytest.mark.asyncio
async def test_post_reading_409_dedup():
    """409 response (duplicate) returns True (not an error)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 409
    client.post.return_value = mock_resp

    result = await post_reading(client, {"node_id": "A1"})
    assert result is True


@pytest.mark.asyncio
async def test_post_reading_500_fails():
    """500 response returns False."""
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    client.post.return_value = mock_resp

    result = await post_reading(client, {"node_id": "A1"})
    assert result is False


@pytest.mark.asyncio
async def test_post_reading_timeout():
    """Timeout returns False."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post.side_effect = httpx.TimeoutException("timeout")

    result = await post_reading(client, {"node_id": "A1"})
    assert result is False


@pytest.mark.asyncio
async def test_write_with_retry_success_first_try():
    """Successful write on first attempt."""
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    client.post.return_value = mock_resp

    result = await write_with_retry(client, {"node_id": "A1"}, max_retries=0)
    assert result is True


# ── Pipeline integration test ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_message_invalid_json():
    """Invalid JSON is handled gracefully."""
    # Should not raise
    await process_message("SLOPE-001", "not-json{{{")


@pytest.mark.asyncio
async def test_process_message_invalid_packet():
    """Invalid packet (missing required fields) is rejected."""
    payload = json.dumps({"foo": "bar"})
    await process_message("SLOPE-001", payload)


@pytest.mark.asyncio
async def test_process_message_valid_packet():
    """Valid packet goes through the full pipeline."""
    now = datetime.now(timezone.utc)
    packet = {
        "node_id": "A1",
        "ts": now.isoformat(),
        "bat": 12.4,
        "rssi": -85,
        "sm1": 45.0,
    }
    payload = json.dumps(packet)

    # Mock the global resources in main
    mock_redis = AsyncMock()
    mock_redis.exists.return_value = 0
    mock_redis.set.return_value = True

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_client.post.return_value = mock_resp

    with patch("app.main._redis", mock_redis), \
         patch("app.main._http_client", mock_client):
        await process_message("SLOPE-001", payload)

    # Verify write was attempted
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    posted_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert posted_data["node_id"] == "A1"
    assert posted_data["slope_id"] == "SLOPE-001"
    assert posted_data["soil_moisture_d1_pct"] == 45.0
