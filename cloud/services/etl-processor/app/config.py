"""ILEWS ETL Processor – application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # MQTT
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_TOPIC: str = "sensors/+/data"

    # FastAPI backend (internal endpoint)
    BACKEND_URL: str = "http://localhost:8000"
    SERVICE_API_KEY: str = "change-me-service-key"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Runtime
    ENVIRONMENT: str = "development"
    METRICS_PORT: int = 8001


settings = Settings()
