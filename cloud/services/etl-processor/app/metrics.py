"""ETL Processor – Prometheus metrics."""

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

registry = CollectorRegistry()

MQTT_RECEIVED = Counter(
    "ilews_etl_mqtt_messages_received_total",
    "Total MQTT messages received",
    ["node_id"],
    registry=registry,
)

MQTT_VALID = Counter(
    "ilews_etl_mqtt_messages_valid_total",
    "Total valid MQTT messages",
    registry=registry,
)

MQTT_INVALID = Counter(
    "ilews_etl_mqtt_messages_invalid_total",
    "Total invalid MQTT messages",
    ["reason"],
    registry=registry,
)

MQTT_DUPLICATE = Counter(
    "ilews_etl_mqtt_messages_duplicate_total",
    "Total duplicate MQTT messages",
    registry=registry,
)

INGESTION_LATENCY = Histogram(
    "ilews_etl_end_to_end_ingestion_latency_seconds",
    "End-to-end ingestion latency in seconds",
    registry=registry,
)


def get_metrics_response():
    """Generate Prometheus metrics response."""
    return generate_latest(registry), CONTENT_TYPE_LATEST
