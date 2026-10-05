"""ILEWS ML Inference Service – Feature builder for live data.

Replicates the preprocessing pipeline from cloud/ml/data/preprocess.py
for real-time inference on live sensor readings.
"""

import pickle
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from app.config import settings

# Short field → full column name (same mapping as ETL enricher)
FIELD_MAP = {
    "soil_moisture_d1_pct": "soil_moisture_1_pct",
    "soil_moisture_d2_pct": "soil_moisture_2_pct",
    "soil_moisture_d3_pct": "soil_moisture_3_pct",
    "soil_moisture_d4_pct": "soil_moisture_4_pct",
    "soil_moisture_d5_pct": "soil_moisture_5_pct",
    "rainfall_mm": "rainfall_mm",
    "tilt_x_deg": "tilt_x_deg",
    "tilt_y_deg": "tilt_y_deg",
}

ROLLING_WINDOWS = {"1h": 4, "6h": 24, "24h": 96}
ANTECEDENT_DECAY = 0.85

_scaler = None


def load_scaler(path: str = None) -> bool:
    """Load fitted MinMaxScaler from disk."""
    global _scaler
    path = path or settings.SCALER_PATH
    if not path:
        logger.warning("No scaler path configured")
        return False

    try:
        with open(path, "rb") as f:
            _scaler = pickle.load(f)
        logger.info(f"Scaler loaded from {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to load scaler: {e}")
        return False


def build_live_features(
    readings: list[dict],
    timesteps: int = 96,
) -> Optional[np.ndarray]:
    """Build feature sequences from live sensor readings.

    Args:
        readings: List of reading dicts from the backend API,
                  sorted by timestamp ascending.
        timesteps: Number of time steps for LSTM input.

    Returns:
        Feature array of shape (1, timesteps, n_features) or None.
    """
    if not readings or len(readings) < timesteps:
        logger.warning(
            f"Insufficient readings: {len(readings or [])} < {timesteps}"
        )
        return None

    # Convert to DataFrame
    df = pd.DataFrame(readings)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)

    # Select numeric columns
    numeric_df = df.select_dtypes(include=[np.number])

    # Compute rolling stats
    features = pd.DataFrame(index=numeric_df.index)
    sensor_cols = [c for c in numeric_df.columns if any(
        k in c for k in ["moisture", "rainfall", "tilt", "accel", "vibration"]
    )]

    for col in sensor_cols:
        for label, window in ROLLING_WINDOWS.items():
            features[f"{col}_mean_{label}"] = (
                numeric_df[col].rolling(window=window, min_periods=1).mean()
            )
            features[f"{col}_std_{label}"] = (
                numeric_df[col].rolling(window=window, min_periods=1).std().fillna(0)
            )

    # Antecedent rainfall
    if "rainfall_mm" in numeric_df.columns:
        rain = numeric_df["rainfall_mm"].fillna(0).values
        ari = np.zeros(len(rain))
        ari[0] = rain[0]
        for i in range(1, len(rain)):
            ari[i] = rain[i] + ANTECEDENT_DECAY * ari[i - 1]
        features["antecedent_rainfall"] = ari

    # Tilt rates
    for col in ["tilt_x_deg", "tilt_y_deg"]:
        if col in numeric_df.columns:
            features[f"{col}_rate"] = numeric_df[col].diff().fillna(0)

    # Temporal features
    if hasattr(features.index, "hour"):
        hours = features.index.hour + features.index.minute / 60
        features["hour_sin"] = np.sin(2 * np.pi * hours / 24)
        features["hour_cos"] = np.cos(2 * np.pi * hours / 24)
        features["month_sin"] = np.sin(2 * np.pi * features.index.month / 12)
        features["month_cos"] = np.cos(2 * np.pi * features.index.month / 12)

    # Combine with raw
    all_features = pd.concat([numeric_df, features], axis=1)
    all_features = all_features.dropna()

    if len(all_features) < timesteps:
        logger.warning(
            f"After feature engineering: {len(all_features)} < {timesteps}"
        )
        return None

    # Normalize if scaler available
    values = all_features.values[-timesteps:]
    if _scaler is not None:
        try:
            # Handle feature count mismatch gracefully
            if values.shape[1] == _scaler.n_features_in_:
                values = _scaler.transform(values)
            else:
                logger.warning(
                    f"Feature count mismatch: {values.shape[1]} vs "
                    f"{_scaler.n_features_in_}, skipping normalization"
                )
        except Exception as e:
            logger.warning(f"Scaler transform failed: {e}")

    # Return as (1, timesteps, features)
    return values.reshape(1, timesteps, -1).astype(np.float32)
