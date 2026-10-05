"""ILEWS Edge – Feature builder from SQLite buffer data.

Constructs sliding window features for TFLite inference,
matching the preprocessing used during cloud training.
"""

import json
import os

import numpy as np
from loguru import logger


# Default scaler parameters (loaded from JSON config)
_scaler_params = None


def load_scaler_config(path: str) -> bool:
    """Load pre-saved scaler parameters from JSON file.

    The JSON should contain:
      {"feature_names": [...], "min": [...], "scale": [...]}
    where min and scale are from sklearn MinMaxScaler.
    """
    global _scaler_params
    if not os.path.exists(path):
        logger.warning(f"Scaler config not found: {path}")
        return False

    try:
        with open(path, "r") as f:
            _scaler_params = json.load(f)
        logger.info(f"Scaler config loaded: {len(_scaler_params.get('feature_names', []))} features")
        return True
    except Exception as e:
        logger.error(f"Failed to load scaler config: {e}")
        return False


def build_edge_features(
    sqlite_conn,
    slope_id: str,
    window_minutes: int = 30,
) -> np.ndarray:
    """Build feature array from SQLite buffered readings.

    Args:
        sqlite_conn: SQLite connection to the edge buffer DB.
        slope_id: Slope identifier.
        window_minutes: Lookback window in minutes.

    Returns:
        Feature array shaped for TFLite input, or None if insufficient data.
    """
    # Fetch recent readings from buffer
    cursor = sqlite_conn.execute(
        "SELECT payload_json, received_at FROM raw_readings "
        "WHERE received_at >= datetime('now', ?) "
        "ORDER BY received_at ASC",
        (f"-{window_minutes} minutes",),
    )
    rows = cursor.fetchall()

    if not rows:
        logger.debug(f"No readings in last {window_minutes} minutes")
        return None

    # Parse JSON payloads into numeric arrays
    sensor_fields = [
        "sm1", "sm2", "sm3", "sm4", "sm5",
        "rn", "tx", "ty", "ax", "ay", "az",
        "vhz", "vamp", "bat", "rssi",
    ]

    readings = []
    for row in rows:
        try:
            data = json.loads(row[0] if isinstance(row, tuple) else row["payload_json"])
            values = [float(data.get(f, 0.0)) for f in sensor_fields]
            readings.append(values)
        except (json.JSONDecodeError, ValueError):
            continue

    if len(readings) < 2:
        logger.debug(f"Insufficient readings: {len(readings)}")
        return None

    raw = np.array(readings, dtype=np.float32)

    # Apply normalization if scaler is available
    if _scaler_params is not None:
        try:
            mins = np.array(_scaler_params["min"][:raw.shape[1]], dtype=np.float32)
            scales = np.array(_scaler_params["scale"][:raw.shape[1]], dtype=np.float32)
            raw = (raw - mins) * scales
            raw = np.clip(raw, 0, 1)
        except Exception as e:
            logger.warning(f"Normalization failed: {e}")

    # Reshape for TFLite: (1, timesteps, features)
    return raw.reshape(1, raw.shape[0], raw.shape[1])
