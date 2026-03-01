"""ILEWS Notification Service – Configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Notification service configuration from environment."""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CHANNEL: str = "ilews:alerts:new"

    # Backend API
    BACKEND_URL: str = "http://localhost:8000"
    SERVICE_API_KEY: str = "dev-service-key"

    # Twilio SMS
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Firebase Cloud Messaging
    FCM_PROJECT_ID: str = ""
    FCM_SERVICE_ACCOUNT_JSON: str = ""

    # MQTT (for siren commands)
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CLIENT_ID: str = "ilews-notification-svc"

    # Dashboard URL for alert links
    DASHBOARD_URL: str = "https://dashboard.ilews.gov"

    # Service
    METRICS_PORT: int = 8002
    LOG_LEVEL: str = "INFO"

    # Retry config
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_INTERVAL_SECONDS: int = 60
    RETRY_COOLDOWN_SECONDS: int = 30

    model_config = {"env_prefix": "NOTIF_", "env_file": ".env"}


settings = Settings()
