"""ILEWS ML Inference Service – Background scheduler.

Periodically scores all active slopes and tracks last inference times.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict

import httpx
from loguru import logger
from prometheus_client import Counter, Histogram, Gauge

from app.config import settings
from app.scorer import score_slope

inference_counter = Counter(
    "mlinf_inferences_total", "Total slope inferences performed"
)
inference_errors = Counter(
    "mlinf_inference_errors_total", "Failed slope inferences"
)
inference_duration = Histogram(
    "mlinf_inference_duration_seconds",
    "Time per slope inference",
    buckets=[0.5, 1, 2, 5, 10, 30],
)
active_slopes_gauge = Gauge(
    "mlinf_active_slopes", "Number of active slopes being scored"
)

# Track last inference time per slope
_last_inference: Dict[str, str] = {}


def get_last_inference_times() -> dict:
    """Return last inference timestamp per slope."""
    return dict(_last_inference)


async def fetch_active_slopes(client: httpx.AsyncClient) -> list[str]:
    """Fetch list of active slope IDs from backend."""
    url = f"{settings.BACKEND_URL}/v1/slopes"
    headers = {"X-Service-Api-Key": settings.SERVICE_API_KEY}

    try:
        resp = await client.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            slopes = data.get("data", [])
            return [
                s.get("slope_id") or s.get("id")
                for s in slopes
                if s.get("status", "active") == "active"
            ]
    except Exception as e:
        logger.error(f"Error fetching active slopes: {e}")

    return []


async def score_all_slopes(client: httpx.AsyncClient) -> dict:
    """Score all active slopes. Returns summary."""
    slopes = await fetch_active_slopes(client)
    active_slopes_gauge.set(len(slopes))

    if not slopes:
        logger.warning("No active slopes to score")
        return {"scored": 0, "errors": 0, "slopes": []}

    results = []
    errors = 0

    for slope_id in slopes:
        with inference_duration.time():
            try:
                result = await score_slope(client, slope_id)
                if "error" not in result:
                    inference_counter.inc()
                    _last_inference[slope_id] = result.get(
                        "timestamp",
                        datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    errors += 1
                    inference_errors.inc()
                results.append(result)
            except Exception as e:
                errors += 1
                inference_errors.inc()
                logger.error(f"Error scoring {slope_id}: {e}")
                results.append({"slope_id": slope_id, "error": str(e)})

    logger.info(
        f"Scoring cycle complete: {len(slopes)} slopes, "
        f"{errors} errors"
    )

    return {
        "scored": len(slopes) - errors,
        "errors": errors,
        "slopes": results,
    }


async def run_scheduler(client: httpx.AsyncClient):
    """Background loop that scores all slopes periodically."""
    interval = settings.SCORE_INTERVAL_MINUTES * 60
    logger.info(
        f"Scheduler started: scoring every {settings.SCORE_INTERVAL_MINUTES}min"
    )

    while True:
        try:
            await score_all_slopes(client)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(interval)
