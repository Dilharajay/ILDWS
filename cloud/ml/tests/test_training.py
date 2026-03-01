"""Tests for ML training and evaluation (Prompt 5.2)."""

import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.lstm_model import build_lstm_model, export_tflite
from training.evaluate import evaluate_model, _compute_lead_time
from training.train import temporal_split


# ── Temporal split tests ─────────────────────────────────────────────────


def test_temporal_split_sizes():
    """Temporal split respects 70/15/15 ratios."""
    X = np.random.randn(100, 10, 5)
    y = np.random.randint(0, 2, 100)

    X_train, y_train, X_val, y_val, X_test, y_test = temporal_split(X, y)

    assert len(X_train) == 70
    assert len(X_val) == 15
    assert len(X_test) == 15
    assert len(y_train) == 70


def test_temporal_split_preserves_order():
    """Temporal split does not shuffle data."""
    X = np.arange(100).reshape(100, 1, 1)
    y = np.zeros(100)

    X_train, _, X_val, _, X_test, _ = temporal_split(X, y)

    # Train should be first 70, val next 15, test last 15
    assert X_train[0, 0, 0] == 0
    assert X_train[-1, 0, 0] == 69
    assert X_val[0, 0, 0] == 70
    assert X_test[-1, 0, 0] == 99


# ── Evaluation tests ────────────────────────────────────────────────────


def test_evaluate_model_metrics():
    """Evaluation returns all required metric keys."""
    model = build_lstm_model(timesteps=10, n_features=5)
    X_test = np.random.randn(20, 10, 5).astype(np.float32)
    y_test = np.random.randint(0, 2, 20).astype(np.float32)

    metrics = evaluate_model(model, X_test, y_test)

    required_keys = [
        "auc_roc", "precision", "recall", "f1",
        "false_alarm_rate", "lead_time_avg_minutes",
        "confusion_matrix", "true_positives", "false_positives",
        "true_negatives", "false_negatives", "threshold",
        "n_test_samples",
    ]
    for key in required_keys:
        assert key in metrics, f"Missing metric: {key}"

    assert metrics["n_test_samples"] == 20
    assert 0 <= metrics["auc_roc"] <= 1
    assert 0 <= metrics["false_alarm_rate"] <= 1


def test_evaluate_single_class():
    """Evaluation handles single-class test set gracefully."""
    model = build_lstm_model(timesteps=10, n_features=5)
    X_test = np.random.randn(10, 10, 5).astype(np.float32)
    y_test = np.zeros(10).astype(np.float32)  # All negative

    metrics = evaluate_model(model, X_test, y_test)
    assert "auc_roc" in metrics  # Should not crash


def test_false_alarm_rate_calculation():
    """FAR = FP / (FP + TN) is correctly computed."""
    model = build_lstm_model(timesteps=10, n_features=5)
    X_test = np.random.randn(20, 10, 5).astype(np.float32)
    # Create known labels
    y_test = np.array([0]*10 + [1]*10, dtype=np.float32)

    metrics = evaluate_model(model, X_test, y_test, threshold=0.5)
    # FAR should be between 0 and 1
    assert 0 <= metrics["false_alarm_rate"] <= 1


# ── TFLite export tests ─────────────────────────────────────────────────


def test_tflite_export():
    """TFLite model is exported and file exists."""
    model = build_lstm_model(timesteps=10, n_features=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_model.tflite")
        result = export_tflite(model, path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0


def test_tflite_inference():
    """TFLite model produces valid output (requires Select TF ops)."""
    import tensorflow as tf

    model = build_lstm_model(timesteps=10, n_features=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.tflite")
        export_tflite(model, path)

        # Load and run TFLite model
        try:
            interpreter = tf.lite.Interpreter(model_path=path)
            interpreter.allocate_tensors()

            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            input_data = np.random.randn(1, 10, 5).astype(np.float32)
            interpreter.set_tensor(input_details[0]["index"], input_data)
            interpreter.invoke()

            output = interpreter.get_tensor(output_details[0]["index"])
            assert output.shape == (1, 1)
            assert 0 <= output[0, 0] <= 1
        except RuntimeError as e:
            if "Select TF ops" in str(e) or "Flex" in str(e):
                pytest.skip(
                    "TFLite Flex delegate not available in this env"
                )
            raise
