"""ILEWS ETL Processor – Main entry point.

Runs the MQTT client in a background thread, processes messages through
the validation → dedup → enrichment → write pipeline, and exposes
/health and /metrics HTTP endpoints.
"""

import asyncio
import json
import signal
import sys

import httpx
import redis.asyncio as redis_async
from loguru import logger
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
    Gauge,
)
from aiohttp import web

from app.config import settings
from app.mqtt_client import (
    create_mqtt_client,
    set_message_callback,
    start_mqtt_loop,
    mqtt_messages_valid,
    mqtt_messages_invalid,
    mqtt_messages_duplicate,
    processing_duration,
)
from app.validator import validate_packet
from app.deduplicator import is_duplicate
from app.enricher import enrich_packet
from app.writer import write_with_retry, get_retry_queue_size, flush_retry_queue

# Metrics
retry_queue_size = Gauge(
    "etl_retry_queue_size", "Current retry queue size"
)

# Global resources
_redis = None
_http_client = None
_mqtt_client = None


async def init_redis():
    """Initialize async Redis connection."""
    global _redis
    _redis = redis_async.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    logger.info(f"Redis connected: {settings.REDIS_URL}")
    return _redis


async def init_http_client():
    """Initialize httpx async client."""
    global _http_client
    _http_client = httpx.AsyncClient(timeout=30)
    logger.info(f"HTTP client ready, backend: {settings.BACKEND_URL}")
    return _http_client


async def process_message(slope_id: str, raw_payload: str):
    """Process a single MQTT message through the ETL pipeline."""
    with processing_duration.time():
        try:
            # Parse JSON
            packet = json.loads(raw_payload)
        except json.JSONDecodeError:
            mqtt_messages_invalid.inc()
            logger.warning(f"Invalid JSON from slope {slope_id}")
            return

        # Step 1: Validate
        is_valid, issues, cleaned = validate_packet(packet)
        if not is_valid:
            mqtt_messages_invalid.inc()
            logger.warning(
                f"Invalid packet from slope {slope_id}: {issues}"
            )
            return

        # Step 2: Deduplicate
        if _redis:
            duplicate = await is_duplicate(
                _redis, cleaned["node_id"], cleaned["ts"]
            )
            if duplicate:
                mqtt_messages_duplicate.inc()
                return

        # Step 3: Enrich
        enriched = enrich_packet(cleaned, slope_id, raw_payload)

        # Step 4: Write to backend
        mqtt_messages_valid.inc()
        if _http_client:
            await write_with_retry(_http_client, enriched)

        # Update retry queue gauge
        retry_queue_size.set(get_retry_queue_size())


# ── HTTP endpoints for health and metrics ────────────────────────────


async def health_handler(request):
    """GET /health endpoint."""
    status = {
        "service": "etl-processor",
        "status": "healthy",
        "mqtt_connected": bool(_mqtt_client and _mqtt_client.is_connected()),
        "redis_connected": bool(_redis),
        "retry_queue_size": get_retry_queue_size(),
    }
    return web.json_response(status)


async def metrics_handler(request):
    """GET /metrics endpoint in Prometheus format."""
    return web.Response(
        body=generate_latest(),
        content_type=CONTENT_TYPE_LATEST,
    )


async def start_http_server():
    """Start aiohttp server for /health and /metrics."""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.METRICS_PORT)
    await site.start()
    logger.info(f"HTTP server on port {settings.METRICS_PORT}")
    return runner


async def periodic_retry_flush():
    """Periodically flush retry queue."""
    while True:
        await asyncio.sleep(60)
        if _http_client and get_retry_queue_size() > 0:
            await flush_retry_queue(_http_client)


async def main():
    """Main entry point."""
    logger.info("Starting ILEWS ETL Processor")

    # Initialize resources
    await init_redis()
    await init_http_client()

    # Set up message processing callback
    loop = asyncio.get_event_loop()
    set_message_callback(process_message)

    # Start MQTT client
    global _mqtt_client
    _mqtt_client = create_mqtt_client(loop)
    start_mqtt_loop(_mqtt_client)

    # Start HTTP server for health/metrics
    runner = await start_http_server()

    # Start retry flush task
    retry_task = asyncio.create_task(periodic_retry_flush())

    # Wait for shutdown signal
    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await shutdown_event.wait()

    # Cleanup
    logger.info("Shutting down...")
    retry_task.cancel()
    if _mqtt_client:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
    if _http_client:
        await _http_client.aclose()
    if _redis:
        await _redis.close()
    await runner.cleanup()

    logger.info("ETL Processor shut down complete")


if __name__ == "__main__":
    asyncio.run(main())
