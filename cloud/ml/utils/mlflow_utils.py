"""ILEWS ML Pipeline – MLflow experiment and run helpers."""

import mlflow
from loguru import logger

from config import settings


def init_mlflow() -> str:
    """Initialize MLflow tracking and return experiment ID."""
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    experiment = mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
    logger.info(
        f"MLflow tracking URI: {settings.MLFLOW_TRACKING_URI}, "
        f"experiment: {settings.MLFLOW_EXPERIMENT_NAME} "
        f"(id={experiment.experiment_id})"
    )
    return experiment.experiment_id


def log_training_params(params: dict) -> None:
    """Log training hyperparameters to active MLflow run."""
    mlflow.log_params(params)


def log_training_metrics(metrics: dict, step: int = None) -> None:
    """Log training metrics to active MLflow run."""
    mlflow.log_metrics(metrics, step=step)


def log_model_artifact(
    model,
    artifact_path: str = "model",
    registered_name: str = None,
) -> None:
    """Log Keras model to MLflow."""
    mlflow.tensorflow.log_model(
        model,
        artifact_path=artifact_path,
        registered_model_name=registered_name,
    )


def log_file_artifact(file_path: str, artifact_path: str = None) -> None:
    """Log a file artifact to MLflow."""
    mlflow.log_artifact(file_path, artifact_path=artifact_path)
