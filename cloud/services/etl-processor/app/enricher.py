"""ILEWS ETL Processor – Packet enrichment.

Maps short field names from sensor packets to full DB column names,
generates packet_id, and adds received_at timestamp.
"""

import hashlib
import json
from datetime import datetime, timezone

from loguru import logger


# Short field → full DB column name mapping
FIELD_MAP = {
    "sm1": "soil_moisture_d1_pct",
    "sm2": "soil_moisture_d2_pct",
    "sm3": "soil_moisture_d3_pct",
    "sm4": "soil_moisture_d4_pct",
    "sm5": "soil_moisture_d5_pct",
    "rn": "rainfall_mm",
    "tx": "tilt_x_deg",
    "ty": "tilt_y_deg",
    "ax": "accel_x_ms2",
    "ay": "accel_y_ms2",
    "az": "accel_z_ms2",
    "vhz": "vibration_hz",
    "vamp": "vibration_amplitude",
    "bat": "battery_voltage_v",
    "sol": "solar_input_w",
    "rssi": "rssi_dbm",
}


def generate_packet_id(node_id: str, timestamp: str, raw_payload: str) -> str:
    """Generate a unique packet_id as SHA256 hash."""
    content = f"{node_id}:{timestamp}:{raw_payload}"
    return hashlib.sha256(content.encode()).hexdigest()[:40]


def enrich_packet(
    cleaned: dict,
    slope_id: str,
    raw_payload: str,
) -> dict:
    """Enrich a validated packet with metadata and map field names.

    Args:
        cleaned: Validated/cleaned packet from validator.
        slope_id: Slope ID extracted from MQTT topic.
        raw_payload: Original raw JSON string for packet_id hashing.

    Returns:
        Enriched dict ready for POST to backend /v1/internal/readings.
    """
    node_id = cleaned["node_id"]
    timestamp = cleaned["ts"]

    enriched = {
        "node_id": node_id,
        "slope_id": slope_id,
        "timestamp": timestamp,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "packet_id": generate_packet_id(node_id, timestamp, raw_payload),
        "data_quality": "valid",
        "source": "lora",
    }

    # Map short field names to full DB column names
    for short, full in FIELD_MAP.items():
        if short in cleaned:
            enriched[full] = cleaned[short]

    return enriched
