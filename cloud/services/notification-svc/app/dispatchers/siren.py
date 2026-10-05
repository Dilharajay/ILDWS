"""ILEWS Notification Service – Siren dispatcher via MQTT."""

import json

import paho.mqtt.client as mqtt
from loguru import logger
from prometheus_client import Counter

from app.config import settings

siren_activated_counter = Counter(
    "notif_siren_activated_total", "Siren activations sent"
)
siren_failed_counter = Counter(
    "notif_siren_failed_total", "Siren activation failures"
)


async def activate_siren(
    gateway_id: str, duration_seconds: int = 300
) -> bool:
    """Publish MQTT command to activate siren on edge gateway.

    Args:
        gateway_id: Edge gateway identifier.
        duration_seconds: Siren duration in seconds (default 5 minutes).

    Returns:
        True if MQTT publish succeeded, False otherwise.
    """
    topic = f"gateways/{gateway_id}/commands"
    payload = json.dumps({
        "command": "ACTIVATE_SIREN",
        "duration_seconds": duration_seconds,
    })

    try:
        client = mqtt.Client(
            client_id=f"{settings.MQTT_CLIENT_ID}-siren",
            protocol=mqtt.MQTTv5,
        )

        if settings.MQTT_USERNAME:
            client.username_pw_set(
                settings.MQTT_USERNAME, settings.MQTT_PASSWORD
            )

        client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=10)
        result = client.publish(topic, payload, qos=1)
        client.disconnect()

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            siren_activated_counter.inc()
            logger.info(
                f"Siren activated on gateway {gateway_id} "
                f"for {duration_seconds}s"
            )
            return True
        else:
            siren_failed_counter.inc()
            logger.error(
                f"MQTT publish failed for siren on {gateway_id}: "
                f"rc={result.rc}"
            )
            return False

    except Exception as e:
        siren_failed_counter.inc()
        logger.error(f"Siren activation error for {gateway_id}: {e}")
        return False
