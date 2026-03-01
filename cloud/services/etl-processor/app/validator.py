"""ILEWS ETL Processor – Incoming sensor packet validation.

Validates raw MQTT payloads before they enter the processing pipeline.
Returns (is_valid, issues, cleaned_data) tuple.
"""

import math
from datetime import datetime, timezone, timedelta


# Maximum age of a packet timestamp before it's rejected as stale replay
MAX_STALENESS_SECONDS = 300  # 5 minutes

REQUIRED_FIELDS = ["node_id", "ts", "bat", "rssi"]

FIELD_RANGES = {
    "sm1": (0, 100),
    "sm2": (0, 100),
    "sm3": (0, 100),
    "sm4": (0, 100),
    "sm5": (0, 100),
    "bat": (7.0, 15.0),
    "tx": (-90, 90),
    "ty": (-90, 90),
}


def _is_numeric_invalid(value) -> bool:
    """Check if a numeric value is NaN, None, or not a number."""
    if value is None:
        return True
    try:
        return math.isnan(float(value)) or math.isinf(float(value))
    except (TypeError, ValueError):
        return True


def validate_packet(raw: dict) -> tuple[bool, list[str], dict]:
    """Validate an incoming sensor packet.

    Args:
        raw: Raw packet dictionary from MQTT message.

    Returns:
        (is_valid, issues, cleaned_data) where cleaned_data is the
        sanitised payload ready for enrichment.
    """
    issues: list[str] = []
    cleaned: dict = {}

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in raw or raw[field] is None:
            issues.append(f"Missing required field: {field}")

    if issues:
        return False, issues, {}

    # Copy and validate node_id
    cleaned["node_id"] = str(raw["node_id"])

    # Validate timestamp
    ts = raw.get("ts")
    try:
        if isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        elif isinstance(ts, (int, float)):
            ts_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            issues.append(f"Invalid timestamp format: {ts}")
            return False, issues, {}

        # Ensure timezone-aware
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age = abs((now - ts_dt).total_seconds())
        if age > MAX_STALENESS_SECONDS:
            issues.append(
                f"Timestamp too stale: {age:.0f}s old (max {MAX_STALENESS_SECONDS}s)"
            )
            return False, issues, {}

        cleaned["ts"] = ts_dt.isoformat()

    except (ValueError, OSError) as e:
        issues.append(f"Cannot parse timestamp: {e}")
        return False, issues, {}

    # Validate numeric fields
    for field, (lo, hi) in FIELD_RANGES.items():
        val = raw.get(field)
        if val is None:
            continue  # optional fields
        if _is_numeric_invalid(val):
            issues.append(f"Invalid numeric value for {field}: {val}")
            continue
        fval = float(val)
        if fval < lo or fval > hi:
            issues.append(f"{field} out of range [{lo}, {hi}]: {fval}")
            continue
        cleaned[field] = fval

    # Battery and RSSI (required)
    bat = raw.get("bat")
    if _is_numeric_invalid(bat):
        issues.append(f"Invalid battery voltage: {bat}")
    else:
        cleaned["bat"] = float(bat)

    rssi = raw.get("rssi")
    if _is_numeric_invalid(rssi):
        issues.append(f"Invalid RSSI: {rssi}")
    else:
        cleaned["rssi"] = int(float(rssi))

    # Copy remaining optional numeric fields
    for field in ("rn", "ax", "ay", "az", "vhz", "vamp", "sol"):
        val = raw.get(field)
        if val is not None and not _is_numeric_invalid(val):
            cleaned[field] = float(val)

    is_valid = len(issues) == 0
    return is_valid, issues, cleaned if is_valid else {}
