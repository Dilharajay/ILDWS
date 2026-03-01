"""ILEWS ML Inference Service – Model loader.

Loads trained LSTM model from MLflow registry or local path,
caches in memory, and supports hot-reload.
"""

import os
from typing import Optional

import numpy as np
from loguru import logger

from app.config import settings

_model = None
_model_version: str = "none"
_model_loaded: bool = False


def get_model():
    """Return the currently loaded model."""
    return _model


def get_model_info() -> dict:
    """Return model metadata."""
    return {
        "loaded": _model_loaded,
        "version": _model_version,
        "source": "local" if settings.MODEL_PATH else "mlflow",
    }


async def load_model() -> bool:
    """Load model from MLflow registry or local path.

    Returns True if model loaded successfully.
    """
    global _model, _model_version, _model_loaded

    try:
        if settings.MODEL_PATH and os.path.exists(settings.MODEL_PATH):
            return _load_local_model()
        else:
            return _load_mlflow_model()
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        _model_loaded = False
        return False


def _load_local_model() -> bool:
    """Load model from local filesystem."""
    global _model, _model_version, _model_loaded

    try:
        import tensorflow as tf
        _model = tf.keras.models.load_model(settings.MODEL_PATH)
        _model_version = "local"
        _model_loaded = True
        logger.info(f"Model loaded from {settings.MODEL_PATH}")
        return True
    except Exception as e:
        logger.error(f"Local model load failed: {e}")
        return False


def _load_mlflow_model() -> bool:
    """Load model from MLflow model registry."""
    global _model, _model_version, _model_loaded

    try:
        import mlflow.tensorflow

        model_uri = (
            f"models:/{settings.MLFLOW_MODEL_NAME}/"
            f"{settings.MLFLOW_MODEL_STAGE}"
        )
        _model = mlflow.tensorflow.load_model(model_uri)
        _model_version = f"{settings.MLFLOW_MODEL_NAME}@{settings.MLFLOW_MODEL_STAGE}"
        _model_loaded = True
        logger.info(f"Model loaded from MLflow: {model_uri}")
        return True
    except Exception as e:
        logger.warning(
            f"MLflow model load failed: {e}; "
            f"service will start without model"
        )
        _model_loaded = False
        return False


async def reload_model() -> bool:
    """Hot-reload the model without service restart."""
    logger.info("Reloading model...")
    return await load_model()


def predict(sequences: np.ndarray) -> np.ndarray:
    """Run inference on input sequences.

    Args:
        sequences: Input array of shape (N, timesteps, features).

    Returns:
        Risk scores array of shape (N,) in range [0, 1].
    """
    if _model is None:
        raise RuntimeError("Model not loaded")

    predictions = _model.predict(sequences, verbose=0)
    return predictions.flatten()
