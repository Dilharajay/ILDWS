"""ILEWS Edge Gateway Processor – Main entry point.

Systemd-friendly service that:
1. Initializes SQLite buffer
2. Subscribes to local MQTT (ChirpStack LoRa packets)
3. Starts cloud sync agent
4. Runs edge inference every 5 minutes
5. Handles SIGTERM gracefully
"""

import json
import signal
import sys
import time
import threading

from loguru import logger

from config import settings
from buffer import init_db, write_reading, get_pending_count
from validator import validate_packet
from mqtt_local import create_local_mqtt_client, start_local_mqtt, set_packet_callback
from cloud_sync import CloudSyncAgent
from connectivity import check_internet


_shutdown_event = threading.Event()
_db_conn = None


def on_sensor_packet(node_id: str, payload_json: str):
    """Callback for received sensor packets from local MQTT."""
    global _db_conn

    try:
        packet = json.loads(payload_json)

        # Ensure node_id is set
        if "node_id" not in packet:
            packet["node_id"] = node_id

        # Validate
        is_valid, issues, cleaned = validate_packet(packet)
        if not is_valid:
            logger.warning(
                f"Invalid packet from {node_id}: {issues}"
            )
            return

        # Buffer to SQLite
        row_id = write_reading(_db_conn, json.dumps(cleaned), node_id)
        logger.debug(
            f"Buffered reading from {node_id} (row_id={row_id})"
        )

    except Exception as e:
        logger.error(f"Error processing packet from {node_id}: {e}")


def run_inference_cycle():
    """Run edge inference if local_inference module is available."""
    try:
        sys.path.insert(0, "../local_inference")
        from inference_engine import EdgeInferenceEngine
        from feature_builder import build_edge_features
        from alert_trigger import AlertTrigger

        engine = EdgeInferenceEngine()
        if not engine.is_model_loaded():
            engine.load_model(settings.MODEL_PATH)

        if not engine.is_model_loaded():
            logger.debug("No model loaded, skipping inference")
            return

        features = build_edge_features(
            _db_conn, settings.SLOPE_ID, window_minutes=30
        )
        if features is None:
            logger.debug("Insufficient data for edge inference")
            return

        risk_score = engine.predict(features)
        logger.info(
            f"Edge inference: score={risk_score:.4f} "
            f"for slope {settings.SLOPE_ID}"
        )

        trigger = AlertTrigger(_db_conn)
        trigger.check_and_trigger(risk_score)

    except ImportError:
        logger.debug("local_inference not available, skipping edge ML")
    except Exception as e:
        logger.error(f"Edge inference error: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    _shutdown_event.set()


def main():
    """Main entry point."""
    global _db_conn

    logger.info(
        f"Starting ILEWS Edge Gateway Processor "
        f"(gateway={settings.GATEWAY_ID}, slope={settings.SLOPE_ID})"
    )

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize SQLite buffer
    _db_conn = init_db()

    # Set up local MQTT
    set_packet_callback(on_sensor_packet)
    local_mqtt = create_local_mqtt_client()
    start_local_mqtt(local_mqtt)

    # Start cloud sync agent
    has_internet = check_internet()
    logger.info(f"Internet connectivity: {has_internet}")

    sync_agent = CloudSyncAgent(_db_conn)
    if has_internet:
        sync_agent.start()
    else:
        logger.warning("No internet, cloud sync deferred")

    # Main loop
    inference_counter = 0
    inference_interval = settings.INFERENCE_INTERVAL_SECONDS

    logger.info("Edge gateway running. Press Ctrl+C to stop.")

    while not _shutdown_event.is_set():
        _shutdown_event.wait(timeout=1)
        inference_counter += 1

        # Run inference every INFERENCE_INTERVAL_SECONDS
        if inference_counter >= inference_interval:
            inference_counter = 0
            run_inference_cycle()

            # Log buffer status
            pending = get_pending_count(_db_conn)
            if pending > 0:
                logger.info(f"Buffer: {pending} readings pending sync")

            # Check connectivity and start sync if needed
            if not sync_agent.connected and check_internet():
                logger.info("Internet restored, restarting cloud sync")
                sync_agent.start()

    # Graceful shutdown
    logger.info("Shutting down...")
    sync_agent.stop()
    local_mqtt.loop_stop()
    local_mqtt.disconnect()

    if _db_conn:
        _db_conn.close()

    logger.info("Edge gateway shut down complete")


if __name__ == "__main__":
    main()
