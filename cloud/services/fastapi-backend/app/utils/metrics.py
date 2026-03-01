"""ILEWS backend – Prometheus metrics endpoint."""

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

registry = CollectorRegistry()

REQUEST_COUNT = Counter(
    "ilews_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

REQUEST_LATENCY = Histogram(
    "ilews_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    registry=registry,
)

ACTIVE_WS_CONNECTIONS = Gauge(
    "ilews_active_websocket_connections",
    "Active WebSocket connections",
    registry=registry,
)

ACTIVE_RED_ALERTS = Gauge(
    "ilews_active_red_alerts_total",
    "Number of active RED level alerts",
    registry=registry,
)

router = APIRouter(tags=["observability"])


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        path = request.url.path
        # Normalize path to avoid high-cardinality labels
        if "/v1/" in path:
            parts = path.split("/")
            normalized = "/".join(
                p if not p.replace("-", "").replace("_", "").isalnum()
                or p.startswith("v1") or len(p) < 20
                else "{id}"
                for p in parts
            )
        else:
            normalized = path

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=normalized,
            status_code=str(response.status_code),
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=normalized,
        ).observe(duration)

        return response


@router.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )
