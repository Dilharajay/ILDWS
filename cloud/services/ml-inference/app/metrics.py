"""ML Inference Service – Prometheus metrics."""

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

registry = CollectorRegistry()

INFERENCE_REQUESTS = Counter(
    "ilews_ml_inference_requests_total",
    "Total inference requests",
    ["slope_id"],
    registry=registry,
)

INFERENCE_LATENCY = Histogram(
    "ilews_ml_inference_latency_seconds",
    "Inference latency in seconds",
    ["slope_id"],
    registry=registry,
)

CURRENT_RISK_LEVEL = Gauge(
    "ilews_ml_current_risk_level",
    "Current risk level for slope",
    ["slope_id", "level"],
    registry=registry,
)

MODEL_VERSION_INFO = Gauge(
    "ilews_ml_model_version_info",
    "Model version information",
    ["model_version"],
    registry=registry,
)


def get_metrics_response():
    """Generate Prometheus metrics response."""
    return generate_latest(registry), CONTENT_TYPE_LATEST
