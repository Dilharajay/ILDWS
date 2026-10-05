"""ILEWS Edge Gateway – Local MQTT subscriber for ChirpStack."""

import json

import paho.mqtt.client as mqtt
from loguru import logger

from config import settings


_on_packet_callback = None


def set_packet_callback(callback):
    """Set callback for received packets: callback(node_id, payload_json)."""
    global _on_packet_callback
    _on_packet_callback = callback


def on_connect(client, userdata, flags, rc, properties=None):
    """Handle MQTT connection to local broker."""
    if rc == 0:
        logger.info("Connected to local MQTT broker")
        client.subscribe(settings.LOCAL_MQTT_TOPIC, qos=1)
        logger.info(f"Subscribed to {settings.LOCAL_MQTT_TOPIC}")
    else:
        logger.error(f"Local MQTT connection failed: rc={rc}")


def on_message(client, userdata, msg):
    """Handle incoming LoRa packet from ChirpStack."""
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        # ChirpStack wraps data in an 'object' field
        sensor_data = data.get("object", data)
        node_id = data.get("deviceName", sensor_data.get("node_id", "unknown"))

        logger.debug(f"Received from {node_id}: {payload[:200]}")

        if _on_packet_callback:
            _on_packet_callback(node_id, json.dumps(sensor_data))

    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON on {msg.topic}")
    except Exception as e:
        logger.error(f"Error processing local MQTT message: {e}")


def create_local_mqtt_client() -> mqtt.Client:
    """Create MQTT client for local Mosquitto broker."""
    client = mqtt.Client(
        client_id=f"ilews-gw-{settings.GATEWAY_ID}",
        protocol=mqtt.MQTTv5,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    return client


def start_local_mqtt(client: mqtt.Client) -> None:
    """Connect and start the MQTT network loop."""
    try:
        client.connect(
            settings.LOCAL_MQTT_HOST,
            settings.LOCAL_MQTT_PORT,
            keepalive=60,
        )
        client.loop_start()
        logger.info(
            f"Local MQTT started: "
            f"{settings.LOCAL_MQTT_HOST}:{settings.LOCAL_MQTT_PORT}"
        )
    except Exception as e:
        logger.error(f"Failed to connect to local MQTT: {e}")
