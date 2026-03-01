"""ILEWS Notification Service – Main entry point.

Starts the Redis pub/sub event consumer and retry handler as
async tasks with /health and /metrics HTTP endpoints.
"""

import asyncio
import signal

import httpx
from aiohttp import web
from loguru import logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import settings
from app.event_consumer import run_consumer
from app.retry_handler import run_retry_loop


_http_client = None


async def health_handler(request):
    """GET /health endpoint."""
    return web.json_response({
        "service": "notification-svc",
        "status": "healthy",
    })


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


async def main():
    """Main entry point."""
    logger.info("Starting ILEWS Notification Service")

    global _http_client
    _http_client = httpx.AsyncClient(timeout=30)

    # Start HTTP server
    runner = await start_http_server()

    # Start consumer and retry handler as async tasks
    consumer_task = asyncio.create_task(run_consumer(_http_client))
    retry_task = asyncio.create_task(run_retry_loop(_http_client))

    # Wait for shutdown signal
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await shutdown_event.wait()

    # Cleanup
    logger.info("Shutting down...")
    consumer_task.cancel()
    retry_task.cancel()
    await _http_client.aclose()
    await runner.cleanup()
    logger.info("Notification Service shut down complete")


if __name__ == "__main__":
    asyncio.run(main())
