"""ILEWS ML Pipeline – Configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ML pipeline configuration from environment."""

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://ilews:ilews_dev@localhost:5432/ilews"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg2://ilews:ilews_dev@localhost:5432/ilews"
    )

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "ilews-slope-risk"

    # Training
    DEFAULT_WINDOW_HOURS: int = 24
    DEFAULT_TIMESTEPS: int = 96  # 24h at 15-min intervals
    DEFAULT_BATCH_SIZE: int = 32
    DEFAULT_EPOCHS: int = 100
    DEFAULT_LEARNING_RATE: float = 0.001
    EARLY_STOP_PATIENCE: int = 10

    # Inference
    BACKEND_URL: str = "http://localhost:8000"
    SERVICE_API_KEY: str = "dev-service-key"
    SCORE_INTERVAL_MINUTES: int = 15

    # Model storage
    MODEL_DIR: str = "./models_artifacts"
    TFLITE_DIR: str = "./tflite_artifacts"

    # Risk thresholds
    RISK_GREEN_MAX: float = 0.39
    RISK_YELLOW_MAX: float = 0.64
    RISK_ORANGE_MAX: float = 0.84
    # Anything above RISK_ORANGE_MAX is RED

    model_config = {"env_prefix": "ML_", "env_file": ".env"}


settings = Settings()
