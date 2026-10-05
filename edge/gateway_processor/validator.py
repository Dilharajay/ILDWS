"""ILEWS Edge Gateway – Packet validation (shared spec with ETL service)."""

import math
from datetime import datetime, timezone, timedelta

from loguru import logger

REQUIRED_FIELDS = ["node_id", "ts", "bat", "rssi"]

RANGE_CHECKS = {
    "sm1": (0, 100), "sm2": (0, 100), "sm3": (0, 100),
    "sm4": (0, 100), "sm5": (0, 100),
    "bat": (7.0, 15.0),
    "rn": (0, 500),
    "tx": (-90, 90), "ty": (-90, 90),
    "ax": (-20, 20), "ay": (-20, 20), "az": (-20, 20),
    "vhz": (0, 1000), "vamp": (0, 100),
    "rssi": (-130, 0),
}

STALENESS_MINUTES = 5


def validate_packet(packet: dict) -> tuple[bool, list[str], dict]:
    """Validate a sensor packet.

    Returns: (is_valid, issues, cleaned_data)
    """
    issues = []
    cleaned = {}

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in packet:
            issues.append(f"Missing required field: {field}")

    if issues:
        return False, issues, cleaned

    # Copy all fields
    cleaned = dict(packet)

    # Check for NaN values in numeric fields
    for key, val in packet.items():
        if isinstance(val, float) and math.isnan(val):
            issues.append(f"NaN value in field: {key}")

    # Range checks
    for field, (low, high) in RANGE_CHECKS.items():
        if field in packet:
            val = packet[field]
            if isinstance(val, (int, float)) and not math.isnan(val):
                if val < low or val > high:
                    issues.append(
                        f"{field} out of range [{low}, {high}]: {val}"
                    )

    # Timestamp staleness check
    ts = packet.get("ts")
    if ts is not None:
        try:
            if isinstance(ts, (int, float)):
                pkt_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                cleaned["ts"] = pkt_time.isoformat()
            else:
                pkt_time = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if pkt_time.tzinfo is None:
                    pkt_time = pkt_time.replace(tzinfo=timezone.utc)

            age = datetime.now(timezone.utc) - pkt_time
            if age > timedelta(minutes=STALENESS_MINUTES):
                issues.append(
                    f"Stale timestamp: {age.total_seconds():.0f}s old"
                )
        except (ValueError, OSError):
            issues.append(f"Invalid timestamp format: {ts}")

    if issues:
        return False, issues, cleaned

    return True, [], cleaned
