"""ILEWS backend – application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ilews_dev:ilews_dev_pass@localhost:5432/ilews"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MQTT
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883

    # JWT
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Firebase Cloud Messaging
    FCM_SERVER_KEY: str = ""

    # Runtime
    ENVIRONMENT: str = "development"


settings = Settings()
