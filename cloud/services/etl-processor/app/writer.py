"""ILEWS ETL Processor – Backend writer with retry queue.

Posts enriched sensor data to the FastAPI backend internal endpoint.
Handles retries on 5xx errors and dedup 409 responses.
"""

import asyncio
from collections import deque

import httpx
from loguru import logger
from prometheus_client import Counter

from app.config import settings


write_success_counter = Counter(
    "etl_writes_success_total", "Successfully written readings"
)
write_fail_counter = Counter(
    "etl_writes_failed_total", "Failed write attempts"
)
dedup_counter = Counter(
    "etl_writes_dedup_total", "Deduplicated (409) readings"
)

# Retry queue for failed writes
_retry_queue: deque = deque(maxlen=10000)
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds, exponential backoff


async def post_reading(client: httpx.AsyncClient, enriched: dict) -> bool:
    """Post a single enriched reading to the backend.

    Args:
        client: httpx async client.
        enriched: Enriched packet dict.

    Returns:
        True if successfully written, False otherwise.
    """
    url = f"{settings.BACKEND_URL}/v1/internal/readings"
    headers = {
        "X-Service-Api-Key": settings.SERVICE_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        resp = await client.post(url, json=enriched, headers=headers, timeout=10)

        if resp.status_code in (200, 201):
            write_success_counter.inc()
            logger.debug(
                f"Written reading for node {enriched.get('node_id')}"
            )
            return True
        elif resp.status_code == 409:
            dedup_counter.inc()
            logger.debug(
                f"Dedup 409 for node {enriched.get('node_id')}"
            )
            return True  # Already exists, not an error
        else:
            write_fail_counter.inc()
            logger.warning(
                f"Backend returned {resp.status_code}: {resp.text[:200]}"
            )
            return False

    except httpx.TimeoutException:
        write_fail_counter.inc()
        logger.warning(
            f"Timeout posting reading for {enriched.get('node_id')}"
        )
        return False
    except Exception as e:
        write_fail_counter.inc()
        logger.error(f"Error posting reading: {e}")
        return False


async def write_with_retry(
    client: httpx.AsyncClient, enriched: dict, max_retries: int = MAX_RETRIES
) -> bool:
    """Write reading with exponential backoff retry."""
    for attempt in range(max_retries + 1):
        success = await post_reading(client, enriched)
        if success:
            return True

        if attempt < max_retries:
            delay = RETRY_DELAY_BASE ** (attempt + 1)
            logger.info(
                f"Retry {attempt + 1}/{max_retries} "
                f"for {enriched.get('node_id')} in {delay}s"
            )
            await asyncio.sleep(delay)

    # All retries exhausted, queue for later
    _retry_queue.append(enriched)
    logger.warning(
        f"Queued reading for {enriched.get('node_id')} "
        f"after {max_retries} retries (queue size: {len(_retry_queue)})"
    )
    return False


async def flush_retry_queue(client: httpx.AsyncClient) -> int:
    """Attempt to flush the retry queue. Returns count of successful writes."""
    flushed = 0
    remaining: deque = deque()

    while _retry_queue:
        enriched = _retry_queue.popleft()
        success = await post_reading(client, enriched)
        if success:
            flushed += 1
        else:
            remaining.append(enriched)

    _retry_queue.extend(remaining)
    if flushed:
        logger.info(
            f"Flushed {flushed} from retry queue, "
            f"{len(_retry_queue)} remaining"
        )
    return flushed


def get_retry_queue_size() -> int:
    """Return current retry queue size."""
    return len(_retry_queue)
