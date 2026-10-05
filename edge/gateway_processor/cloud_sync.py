"""ILEWS Edge Gateway – Cloud MQTT sync agent.

Forwards buffered sensor data to the cloud MQTT broker over TLS.
"""

import json
import ssl
import time
import threading

import paho.mqtt.client as mqtt
from loguru import logger

from config import settings
from buffer import get_unsynced, mark_synced, log_sync


class CloudSyncAgent:
    """Syncs buffered readings to cloud MQTT broker."""

    def __init__(self, db_conn):
        self.conn = db_conn
        self.client = None
        self.connected = False
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        """Establish MQTT connection to cloud broker."""
        try:
            self.client = mqtt.Client(
                client_id=f"ilews-sync-{settings.GATEWAY_ID}",
                protocol=mqtt.MQTTv5,
            )

            if settings.CLOUD_MQTT_USERNAME:
                self.client.username_pw_set(
                    settings.CLOUD_MQTT_USERNAME,
                    settings.CLOUD_MQTT_PASSWORD,
                )

            if settings.CLOUD_MQTT_TLS:
                self.client.tls_set(
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                )

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.reconnect_delay_set(min_delay=5, max_delay=120)

            self.client.connect(
                settings.CLOUD_MQTT_HOST,
                settings.CLOUD_MQTT_PORT,
                keepalive=60,
            )
            self.client.loop_start()
            return True

        except Exception as e:
            logger.error(f"Cloud MQTT connection failed: {e}")
            self.connected = False
            return False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            logger.info("Connected to cloud MQTT broker")
        else:
            self.connected = False
            logger.error(f"Cloud MQTT connect failed: rc={rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None, reasonCode=None):
        self.connected = False
        logger.warning(f"Cloud MQTT disconnected: rc={rc}")

    def sync_batch(self) -> tuple[int, int]:
        """Sync a batch of unsynced records.

        Returns: (success_count, failed_count)
        """
        if not self.connected or self.client is None:
            return 0, 0

        records = get_unsynced(self.conn, limit=settings.SYNC_BATCH_SIZE)
        if not records:
            return 0, 0

        topic = f"sensors/{settings.SLOPE_ID}/data"
        synced_ids = []
        failed = 0

        for record in records:
            try:
                result = self.client.publish(
                    topic,
                    record["payload_json"],
                    qos=1,
                )
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    synced_ids.append(record["id"])
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Publish failed for record {record['id']}: {e}")

        if synced_ids:
            mark_synced(self.conn, synced_ids)

        log_sync(self.conn, len(records), len(synced_ids), failed)

        if synced_ids or failed:
            logger.info(
                f"Sync batch: {len(synced_ids)} synced, {failed} failed"
            )

        return len(synced_ids), failed

    def run_sync_loop(self) -> None:
        """Run sync loop in background thread."""
        logger.info(
            f"Cloud sync loop started "
            f"(interval={settings.SYNC_INTERVAL_SECONDS}s)"
        )

        while not self._stop_event.is_set():
            try:
                if self.connected:
                    self.sync_batch()
                else:
                    logger.debug("Cloud not connected, skipping sync")
            except Exception as e:
                logger.error(f"Sync loop error: {e}")

            self._stop_event.wait(settings.SYNC_INTERVAL_SECONDS)

    def start(self) -> threading.Thread:
        """Start sync loop in a background thread."""
        self.connect()
        thread = threading.Thread(
            target=self.run_sync_loop, daemon=True, name="cloud-sync"
        )
        thread.start()
        return thread

    def stop(self) -> None:
        """Stop the sync agent."""
        self._stop_event.set()
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        logger.info("Cloud sync agent stopped")
