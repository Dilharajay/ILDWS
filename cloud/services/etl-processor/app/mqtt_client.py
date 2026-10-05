"""ILEWS ETL Processor – MQTT client with reconnect and metrics.

Subscribes to sensor data topics, processes incoming packets through
the validation → dedup → enrichment → write pipeline.
"""

import json
import asyncio
import threading
from typing import Optional

import paho.mqtt.client as mqtt
from loguru import logger
from prometheus_client import Counter, Gauge, Histogram

from app.config import settings

# Prometheus metrics
mqtt_messages_received = Counter(
    "etl_mqtt_messages_total", "Total MQTT messages received"
)
mqtt_messages_valid = Counter(
    "etl_mqtt_messages_valid_total", "Valid MQTT messages"
)
mqtt_messages_invalid = Counter(
    "etl_mqtt_messages_invalid_total", "Invalid MQTT messages"
)
mqtt_messages_duplicate = Counter(
    "etl_mqtt_messages_duplicate_total", "Duplicate MQTT messages"
)
mqtt_connected = Gauge(
    "etl_mqtt_connected", "MQTT connection status (1=connected)"
)
processing_duration = Histogram(
    "etl_processing_duration_seconds",
    "Time to process one MQTT message",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

# Global callback for async processing
_message_callback = None


def set_message_callback(callback):
    """Set the async callback for processing messages."""
    global _message_callback
    _message_callback = callback


def on_connect(client, userdata, flags, rc, properties=None):
    """Handle MQTT connection."""
    if rc == 0:
        logger.info("Connected to MQTT broker")
        mqtt_connected.set(1)
        # Subscribe to sensor data topics
        topic = settings.MQTT_TOPIC
        client.subscribe(topic, qos=1)
        logger.info(f"Subscribed to {topic}")
    else:
        logger.error(f"MQTT connection failed with code {rc}")
        mqtt_connected.set(0)


def on_disconnect(client, userdata, rc, properties=None, reasonCode=None):
    """Handle MQTT disconnection."""
    logger.warning(f"MQTT disconnected (rc={rc})")
    mqtt_connected.set(0)


def on_message(client, userdata, msg):
    """Handle incoming MQTT message."""
    mqtt_messages_received.inc()
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        logger.debug(f"Received on {topic}: {payload[:200]}")

        # Extract slope_id from topic: sensors/{slope_id}/data
        parts = topic.split("/")
        slope_id = parts[1] if len(parts) >= 3 else "unknown"

        if _message_callback:
            # Schedule async processing
            loop = userdata.get("loop") if userdata else None
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    _message_callback(slope_id, payload), loop
                )
            else:
                logger.warning("No event loop available for async processing")

    except Exception as e:
        logger.error(f"Error handling MQTT message: {e}")


def create_mqtt_client(loop: asyncio.AbstractEventLoop) -> mqtt.Client:
    """Create and configure MQTT client."""
    client = mqtt.Client(
        client_id=settings.MQTT_CLIENT_ID,
        protocol=mqtt.MQTTv5,
        userdata={"loop": loop},
    )

    if settings.MQTT_USERNAME:
        client.username_pw_set(
            settings.MQTT_USERNAME, settings.MQTT_PASSWORD
        )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Enable reconnect with exponential backoff
    client.reconnect_delay_set(min_delay=1, max_delay=120)

    return client


def start_mqtt_loop(client: mqtt.Client) -> threading.Thread:
    """Connect MQTT client and start network loop in a background thread."""
    try:
        client.connect(
            settings.MQTT_HOST,
            settings.MQTT_PORT,
            keepalive=60,
        )
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        mqtt_connected.set(0)

    # Start network loop in background thread
    client.loop_start()
    logger.info(
        f"MQTT loop started for {settings.MQTT_HOST}:{settings.MQTT_PORT}"
    )
    return None
