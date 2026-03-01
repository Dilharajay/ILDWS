"""Tests for ML Pipeline – preprocessing and model architecture (Prompt 5.1)."""

import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

# Add parent dir to path for config imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.preprocess import (
    compute_rolling_stats,
    compute_antecedent_rainfall,
    compute_tilt_rate,
    compute_soil_moisture_gradient,
    compute_temporal_features,
    create_sequences,
    build_features,
    SENSOR_COLUMNS,
)


def _make_sensor_df(n_rows: int = 200) -> pd.DataFrame:
    """Create a synthetic sensor DataFrame for testing."""
    rng = np.random.default_rng(42)
    idx = pd.date_range(
        "2026-01-01", periods=n_rows, freq="15min"
    )
    data = {
        "soil_moisture_1_pct": rng.uniform(20, 80, n_rows),
        "soil_moisture_2_pct": rng.uniform(25, 75, n_rows),
        "soil_moisture_3_pct": rng.uniform(30, 70, n_rows),
        "soil_moisture_4_pct": rng.uniform(35, 65, n_rows),
        "soil_moisture_5_pct": rng.uniform(40, 60, n_rows),
        "rainfall_mm": rng.exponential(0.5, n_rows),
        "tilt_x_deg": rng.normal(0, 2, n_rows),
        "tilt_y_deg": rng.normal(0, 1.5, n_rows),
        "acceleration_x": rng.normal(0, 0.1, n_rows),
        "acceleration_y": rng.normal(0, 0.1, n_rows),
        "acceleration_z": rng.normal(9.8, 0.1, n_rows),
        "vibration_frequency_hz": rng.uniform(0, 50, n_rows),
        "vibration_amplitude": rng.uniform(0, 0.5, n_rows),
    }
    return pd.DataFrame(data, index=idx)


# ── Preprocessing tests ─────────────────────────────────────────────────


def test_rolling_stats_shape():
    """Rolling stats creates mean and std for each window."""
    df = _make_sensor_df(100)
    result = compute_rolling_stats(df)
    # Each sensor × 3 windows × 2 stats (mean, std) = n_sensors × 6
    n_sensors = sum(1 for c in SENSOR_COLUMNS if c in df.columns)
    expected_cols = n_sensors * 6  # 3 windows × 2 stats
    assert result.shape[1] == expected_cols
    assert len(result) == len(df)


def test_antecedent_rainfall():
    """ARI accumulates with decay factor."""
    df = pd.DataFrame(
        {"rainfall_mm": [10, 0, 0, 5, 0]},
        index=pd.date_range("2026-01-01", periods=5, freq="15min"),
    )
    ari = compute_antecedent_rainfall(df, decay=0.85)
    assert ari.iloc[0] == 10.0
    assert ari.iloc[1] == pytest.approx(0 + 0.85 * 10, rel=1e-3)
    assert ari.iloc[3] > 5.0  # accumulated from prior


def test_tilt_rate_computed():
    """Tilt rate of change is computed."""
    df = _make_sensor_df(50)
    result = compute_tilt_rate(df)
    assert "tilt_x_deg_rate" in result.columns
    assert "tilt_y_deg_rate" in result.columns
    assert len(result) == len(df)


def test_soil_moisture_gradient():
    """Gradient between adjacent depth layers is computed."""
    df = _make_sensor_df(50)
    result = compute_soil_moisture_gradient(df)
    # 5 moisture layers → 4 gradients
    assert result.shape[1] == 4
    assert "sm_gradient_1_2" in result.columns


def test_temporal_features_cyclical():
    """Temporal features use sin/cos encoding."""
    df = _make_sensor_df(50)
    result = compute_temporal_features(df)
    assert "hour_sin" in result.columns
    assert "hour_cos" in result.columns
    assert "month_sin" in result.columns
    assert "month_cos" in result.columns
    # Sin/cos values are in [-1, 1]
    assert result["hour_sin"].between(-1, 1).all()
    assert result["hour_cos"].between(-1, 1).all()


def test_create_sequences_shape():
    """Sequences have correct 3D shape."""
    data = np.random.randn(100, 10)  # 100 samples, 10 features
    timesteps = 24
    result = create_sequences(data, timesteps)
    assert result.shape == (100 - timesteps, timesteps, 10)


def test_create_sequences_empty():
    """Returns empty array when data shorter than timesteps."""
    data = np.random.randn(5, 10)
    result = create_sequences(data, 24)
    assert result.shape[0] == 0


def test_build_features_full_pipeline():
    """Full feature pipeline produces normalized LSTM-ready sequences."""
    with tempfile.TemporaryDirectory() as tmpdir:
        scaler_path = os.path.join(tmpdir, "scaler.pkl")
        df = _make_sensor_df(200)
        sequences, scaler, feature_names = build_features(
            df,
            window_hours=6,  # Smaller window for test
            scaler_path=scaler_path,
            fit_scaler=True,
        )

        # Sequences should be 3D
        assert sequences.ndim == 3
        timesteps = 6 * 4  # 6 hours × 4 per hour = 24
        assert sequences.shape[1] == timesteps
        assert sequences.shape[2] == len(feature_names)

        # Values should be normalized to [0, 1]
        assert sequences.min() >= -0.01  # Small tolerance
        assert sequences.max() <= 1.01

        # Scaler was saved
        assert os.path.exists(scaler_path)

        # Feature names should include originals + derived
        assert len(feature_names) > len(SENSOR_COLUMNS)


# ── Model architecture tests ────────────────────────────────────────────


def test_lstm_model_shape():
    """LSTM model has correct input/output shape."""
    from models.lstm_model import build_lstm_model

    model = build_lstm_model(timesteps=24, n_features=50)
    assert model.input_shape == (None, 24, 50)
    assert model.output_shape == (None, 1)


def test_lstm_model_output_range():
    """LSTM model outputs values in [0, 1] (sigmoid)."""
    from models.lstm_model import build_lstm_model

    model = build_lstm_model(timesteps=10, n_features=5)
    dummy_input = np.random.randn(3, 10, 5).astype(np.float32)
    output = model.predict(dummy_input, verbose=0)
    assert output.min() >= 0.0
    assert output.max() <= 1.0


def test_autoencoder_model_shape():
    """Autoencoder reconstructs input shape."""
    from models.autoencoder_model import build_autoencoder_model

    model = build_autoencoder_model(timesteps=10, n_features=5)
    assert model.input_shape == (None, 10, 5)
    assert model.output_shape == (None, 10, 5)
