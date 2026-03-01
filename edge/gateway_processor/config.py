"""ILEWS Edge Gateway Processor – Configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Edge gateway configuration from .env file."""

    GATEWAY_ID: str = "GW-001"
    SLOPE_ID: str = "SLOPE-001"

    # Local MQTT (ChirpStack → Mosquitto)
    LOCAL_MQTT_HOST: str = "localhost"
    LOCAL_MQTT_PORT: int = 1883
    LOCAL_MQTT_TOPIC: str = "application/+/device/+/event/up"

    # Cloud MQTT
    CLOUD_MQTT_HOST: str = "mqtt.cloud.ilews.gov"
    CLOUD_MQTT_PORT: int = 8883
    CLOUD_MQTT_TLS: bool = True
    CLOUD_MQTT_USERNAME: str = ""
    CLOUD_MQTT_PASSWORD: str = ""

    # SQLite buffer
    SQLITE_PATH: str = "./edge_buffer.db"

    # Siren
    SIREN_GPIO_PIN: int = 17
    ALERT_THRESHOLD_RED: float = 0.85

    # Sync
    SYNC_INTERVAL_SECONDS: int = 30
    SYNC_BATCH_SIZE: int = 50

    # Inference
    INFERENCE_INTERVAL_SECONDS: int = 300  # 5 minutes
    MODEL_PATH: str = "../local_inference/model/model.tflite"
    SCALER_CONFIG_PATH: str = "../local_inference/model/scaler_config.json"

    LOG_LEVEL: str = "INFO"

    model_config = {"env_prefix": "EDGE_", "env_file": ".env"}


settings = Settings()
