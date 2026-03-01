"""ILEWS ML Pipeline – Training script.

Trains the LSTM model for slope risk prediction with MLflow tracking,
early stopping, and TFLite export.
"""

import os
import sys
import argparse

import numpy as np
import mlflow
import tensorflow as tf
from tensorflow import keras
from loguru import logger

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from models.lstm_model import build_lstm_model, export_tflite
from training.evaluate import evaluate_model


def temporal_split(
    X: np.ndarray,
    y: np.ndarray,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> tuple:
    """Split data preserving temporal order (no random shuffle).

    Args:
        X: Sequences of shape (N, timesteps, features).
        y: Labels of shape (N,).
        train_frac: Fraction for training (default 70%).
        val_frac: Fraction for validation (default 15%).

    Returns:
        (X_train, y_train, X_val, y_val, X_test, y_test)
    """
    n = len(X)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    logger.info(
        f"Temporal split: train={len(X_train)}, "
        f"val={len(X_val)}, test={len(X_test)}"
    )

    return X_train, y_train, X_val, y_val, X_test, y_test


def train_model(
    X: np.ndarray,
    y: np.ndarray,
    slope_id: str = "all",
    timestamps: np.ndarray = None,
) -> dict:
    """Train the LSTM model with MLflow tracking.

    Args:
        X: Feature sequences of shape (N, timesteps, features).
        y: Binary labels of shape (N,).
        slope_id: Slope identifier for MLflow run name.
        timestamps: Optional timestamps for lead time calculation.

    Returns:
        Dict with training results and metrics.
    """
    timesteps = X.shape[1]
    n_features = X.shape[2]

    # Temporal split
    X_train, y_train, X_val, y_val, X_test, y_test = temporal_split(X, y)

    # Initialize MLflow
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run(run_name=f"lstm-{slope_id}") as run:
        # Log hyperparameters
        params = {
            "slope_id": slope_id,
            "timesteps": timesteps,
            "n_features": n_features,
            "batch_size": settings.DEFAULT_BATCH_SIZE,
            "epochs": settings.DEFAULT_EPOCHS,
            "learning_rate": settings.DEFAULT_LEARNING_RATE,
            "early_stop_patience": settings.EARLY_STOP_PATIENCE,
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "test_samples": len(X_test),
        }
        mlflow.log_params(params)

        # Build model
        model = build_lstm_model(
            timesteps=timesteps,
            n_features=n_features,
            learning_rate=settings.DEFAULT_LEARNING_RATE,
        )

        # Callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor="val_auc",
                patience=settings.EARLY_STOP_PATIENCE,
                mode="max",
                restore_best_weights=True,
                verbose=1,
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor="val_auc",
                factor=0.5,
                patience=5,
                mode="max",
                verbose=1,
            ),
        ]

        # Train
        logger.info(
            f"Training LSTM for slope {slope_id} "
            f"({len(X_train)} samples)"
        )
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            batch_size=settings.DEFAULT_BATCH_SIZE,
            epochs=settings.DEFAULT_EPOCHS,
            callbacks=callbacks,
            verbose=1,
        )

        # Evaluate
        test_timestamps = timestamps[-len(X_test):] if timestamps is not None else None
        metrics = evaluate_model(
            model, X_test, y_test, timestamps=test_timestamps
        )

        # Log metrics
        mlflow.log_metrics({
            "test_auc": metrics["auc_roc"],
            "test_precision": metrics["precision"],
            "test_recall": metrics["recall"],
            "test_f1": metrics["f1"],
            "test_far": metrics["false_alarm_rate"],
            "lead_time_avg_min": metrics["lead_time_avg_minutes"],
        })

        # Save model
        os.makedirs(settings.MODEL_DIR, exist_ok=True)
        model_path = os.path.join(settings.MODEL_DIR, f"lstm_{slope_id}")
        model.save(model_path)
        logger.info(f"Model saved to {model_path}")

        # Export TFLite
        os.makedirs(settings.TFLITE_DIR, exist_ok=True)
        tflite_path = os.path.join(
            settings.TFLITE_DIR, f"lstm_{slope_id}.tflite"
        )
        export_tflite(model, tflite_path)

        # Log artifacts to MLflow
        mlflow.log_artifact(tflite_path)
        mlflow.tensorflow.log_model(
            model,
            artifact_path="model",
            registered_model_name=f"ilews-lstm-{slope_id}",
        )

        logger.info(
            f"Training complete for {slope_id}: "
            f"AUC={metrics['auc_roc']:.4f}, "
            f"F1={metrics['f1']:.4f}, "
            f"FAR={metrics['false_alarm_rate']:.4f}"
        )

        return {
            "run_id": run.info.run_id,
            "model_path": model_path,
            "tflite_path": tflite_path,
            "metrics": metrics,
            "history": {
                k: [float(v) for v in vals]
                for k, vals in history.history.items()
            },
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train ILEWS LSTM model"
    )
    parser.add_argument(
        "--slope-id", default="all",
        help="Slope ID to train for (default: all)"
    )
    args = parser.parse_args()

    # Generate synthetic data for testing
    logger.info("Using synthetic data for training demo")
    n_samples = 1000
    timesteps = settings.DEFAULT_TIMESTEPS
    n_features = 50

    rng = np.random.default_rng(42)
    X = rng.random((n_samples, timesteps, n_features)).astype(np.float32)
    y = rng.integers(0, 2, n_samples).astype(np.float32)

    result = train_model(X, y, slope_id=args.slope_id)
    print(f"Training complete. Metrics: {result['metrics']}")
