"""ILEWS ML Pipeline – Feature engineering and preprocessing."""

import os
import pickle

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from loguru import logger

from config import settings


# Sensor columns for feature engineering
SENSOR_COLUMNS = [
    "soil_moisture_1_pct",
    "soil_moisture_2_pct",
    "soil_moisture_3_pct",
    "soil_moisture_4_pct",
    "soil_moisture_5_pct",
    "rainfall_mm",
    "tilt_x_deg",
    "tilt_y_deg",
    "acceleration_x",
    "acceleration_y",
    "acceleration_z",
    "vibration_frequency_hz",
    "vibration_amplitude",
]

ROLLING_WINDOWS = {
    "1h": 4,    # 4 x 15-min = 1 hour
    "6h": 24,   # 24 x 15-min = 6 hours
    "24h": 96,  # 96 x 15-min = 24 hours
}

ANTECEDENT_RAINFALL_DECAY = 0.85


def compute_rolling_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling mean and std for each sensor column."""
    features = pd.DataFrame(index=df.index)

    for col in SENSOR_COLUMNS:
        if col not in df.columns:
            continue
        for label, window in ROLLING_WINDOWS.items():
            features[f"{col}_mean_{label}"] = (
                df[col].rolling(window=window, min_periods=1).mean()
            )
            features[f"{col}_std_{label}"] = (
                df[col].rolling(window=window, min_periods=1).std().fillna(0)
            )

    return features


def compute_antecedent_rainfall(
    df: pd.DataFrame, decay: float = ANTECEDENT_RAINFALL_DECAY
) -> pd.Series:
    """Compute Antecedent Rainfall Index with exponential decay."""
    if "rainfall_mm" not in df.columns:
        return pd.Series(0, index=df.index, name="antecedent_rainfall")

    rain = df["rainfall_mm"].fillna(0).values
    ari = np.zeros(len(rain))
    ari[0] = rain[0]

    for i in range(1, len(rain)):
        ari[i] = rain[i] + decay * ari[i - 1]

    return pd.Series(ari, index=df.index, name="antecedent_rainfall")


def compute_tilt_rate(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rate of change for tilt sensors."""
    features = pd.DataFrame(index=df.index)

    for col in ["tilt_x_deg", "tilt_y_deg"]:
        if col in df.columns:
            features[f"{col}_rate"] = df[col].diff().fillna(0)
            features[f"{col}_rate_6h"] = (
                df[col].diff(periods=24).fillna(0)
            )

    return features


def compute_soil_moisture_gradient(df: pd.DataFrame) -> pd.DataFrame:
    """Compute soil moisture gradient between depth layers."""
    features = pd.DataFrame(index=df.index)
    sm_cols = [c for c in df.columns if c.startswith("soil_moisture_")]
    sm_cols = sorted([c for c in sm_cols if c in df.columns])

    for i in range(len(sm_cols) - 1):
        name = f"sm_gradient_{i+1}_{i+2}"
        features[name] = df[sm_cols[i + 1]] - df[sm_cols[i]]

    return features


def compute_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cyclical hour-of-day and month features."""
    features = pd.DataFrame(index=df.index)
    idx = df.index

    # Hour of day (cyclical encoding)
    hours = idx.hour + idx.minute / 60.0
    features["hour_sin"] = np.sin(2 * np.pi * hours / 24)
    features["hour_cos"] = np.cos(2 * np.pi * hours / 24)

    # Month (cyclical encoding)
    months = idx.month
    features["month_sin"] = np.sin(2 * np.pi * months / 12)
    features["month_cos"] = np.cos(2 * np.pi * months / 12)

    return features


def build_features(
    df: pd.DataFrame,
    window_hours: int = 24,
    scaler_path: str = None,
    fit_scaler: bool = True,
) -> tuple[np.ndarray, MinMaxScaler, list[str]]:
    """Build complete feature set and create LSTM-ready sequences.

    Args:
        df: Raw sensor DataFrame indexed by timestamp.
        window_hours: Lookback window in hours for sequences.
        scaler_path: Path to save/load scaler. If None, uses default.
        fit_scaler: If True, fit a new scaler. If False, load existing.

    Returns:
        Tuple of (sequences, scaler, feature_names) where sequences
        has shape [N, timesteps, features].
    """
    logger.info(
        f"Building features from {len(df)} records, "
        f"window={window_hours}h"
    )

    # Drop non-numeric columns except index
    numeric_df = df.select_dtypes(include=[np.number])

    # Compute all feature groups
    rolling = compute_rolling_stats(numeric_df)
    ari = compute_antecedent_rainfall(numeric_df)
    tilt_rate = compute_tilt_rate(numeric_df)
    sm_gradient = compute_soil_moisture_gradient(numeric_df)
    temporal = compute_temporal_features(numeric_df)

    # Combine all features
    all_features = pd.concat(
        [numeric_df, rolling, ari, tilt_rate, sm_gradient, temporal],
        axis=1,
    )

    # Drop any remaining NaN rows from rolling window warmup
    all_features = all_features.dropna()
    feature_names = list(all_features.columns)

    logger.info(f"Total features: {len(feature_names)}")

    # Normalize
    scaler_path = scaler_path or os.path.join(
        settings.MODEL_DIR, "feature_scaler.pkl"
    )

    if fit_scaler:
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = scaler.fit_transform(all_features.values)
        os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)
        logger.info(f"Scaler saved to {scaler_path}")
    else:
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        scaled = scaler.transform(all_features.values)
        logger.info(f"Scaler loaded from {scaler_path}")

    # Create windowed sequences for LSTM
    timesteps = window_hours * 4  # 15-min intervals
    sequences = create_sequences(scaled, timesteps)

    logger.info(
        f"Created {len(sequences)} sequences of shape "
        f"({timesteps}, {len(feature_names)})"
    )

    return sequences, scaler, feature_names


def create_sequences(
    data: np.ndarray, timesteps: int
) -> np.ndarray:
    """Create sliding window sequences for LSTM input.

    Args:
        data: 2D array of shape (n_samples, n_features).
        timesteps: Number of time steps per sequence.

    Returns:
        3D array of shape (n_sequences, timesteps, n_features).
    """
    sequences = []
    for i in range(len(data) - timesteps):
        sequences.append(data[i: i + timesteps])

    return np.array(sequences) if sequences else np.empty(
        (0, timesteps, data.shape[1])
    )
