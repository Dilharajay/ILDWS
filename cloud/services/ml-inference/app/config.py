"""ILEWS ML Inference Service – Configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ML Inference Service configuration."""

    # Backend API
    BACKEND_URL: str = "http://localhost:8000"
    SERVICE_API_KEY: str = "dev-service-key"

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_MODEL_NAME: str = "ilews-lstm-all"
    MLFLOW_MODEL_STAGE: str = "Production"

    # Model
    MODEL_PATH: str = ""  # Local path override (skip MLflow)
    SCALER_PATH: str = ""

    # Scoring
    SCORE_INTERVAL_MINUTES: int = 15
    LOOKBACK_HOURS: int = 24

    # Risk thresholds
    RISK_GREEN_MAX: float = 0.39
    RISK_YELLOW_MAX: float = 0.64
    RISK_ORANGE_MAX: float = 0.84

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8003
    LOG_LEVEL: str = "INFO"

    model_config = {"env_prefix": "MLINF_", "env_file": ".env"}


settings = Settings()
