"""ILEWS Notification Service – Notification retry handler.

Background task that periodically retries failed notification dispatches.
"""

import asyncio

import httpx
from loguru import logger
from prometheus_client import Counter

from app.config import settings
from app.dispatchers.sms import send_sms, AlertPayload
from app.dispatchers.push import send_push

retry_success_counter = Counter(
    "notif_retry_success_total", "Successful retry attempts"
)
retry_exhaust_counter = Counter(
    "notif_retry_exhausted_total", "Retries exhausted (marked failed)"
)


async def get_pending_notifications(
    client: httpx.AsyncClient,
) -> list[dict]:
    """Fetch pending notifications from the backend that need retry."""
    url = (
        f"{settings.BACKEND_URL}/v1/internal/notifications/pending"
    )
    headers = {"X-Service-Api-Key": settings.SERVICE_API_KEY}

    try:
        resp = await client.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", [])
        else:
            logger.warning(
                f"Failed to fetch pending notifications: "
                f"{resp.status_code}"
            )
            return []
    except Exception as e:
        logger.error(f"Error fetching pending notifications: {e}")
        return []


async def update_notification_status(
    client: httpx.AsyncClient,
    notification_id: str,
    status: str,
    attempt_count: int,
) -> bool:
    """Update notification status in the backend."""
    url = (
        f"{settings.BACKEND_URL}/v1/internal/notifications/"
        f"{notification_id}/status"
    )
    headers = {
        "X-Service-Api-Key": settings.SERVICE_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "status": status,
        "attempt_count": attempt_count,
    }

    try:
        resp = await client.put(
            url, json=payload, headers=headers, timeout=10
        )
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.error(
            f"Error updating notification {notification_id}: {e}"
        )
        return False


async def retry_notification(
    client: httpx.AsyncClient, notification: dict
) -> bool:
    """Retry a single failed notification."""
    channel = notification.get("channel", "")
    attempt = notification.get("attempt_count", 0) + 1
    notif_id = notification.get("id", "")

    alert = AlertPayload(
        alert_id=notification.get("alert_id", ""),
        slope_id=notification.get("slope_id", ""),
        slope_name=notification.get("slope_name", "Unknown"),
        level=notification.get("level", "RED"),
        risk_score=notification.get("risk_score", 0.0),
        timestamp=notification.get("timestamp", ""),
    )

    success = False

    if channel == "sms":
        to_number = notification.get("recipient", "")
        if to_number:
            success = await send_sms(to_number, alert)
    elif channel == "push":
        tokens = notification.get("device_tokens", [])
        if tokens:
            result = await send_push(tokens, alert)
            success = result.get("sent", 0) > 0

    if success:
        retry_success_counter.inc()
        await update_notification_status(
            client, notif_id, "delivered", attempt
        )
        logger.info(f"Retry succeeded for notification {notif_id}")
        return True

    # Check if max retries exhausted
    if attempt >= settings.MAX_RETRY_ATTEMPTS:
        retry_exhaust_counter.inc()
        await update_notification_status(
            client, notif_id, "failed", attempt
        )
        logger.warning(
            f"Notification {notif_id} failed after "
            f"{attempt} attempts, marking as failed"
        )
    else:
        await update_notification_status(
            client, notif_id, "pending", attempt
        )
        logger.info(
            f"Notification {notif_id} retry {attempt} failed, "
            f"will retry again"
        )

    return False


async def run_retry_loop(client: httpx.AsyncClient):
    """Background loop that retries pending notifications."""
    logger.info(
        f"Retry handler started "
        f"(interval={settings.RETRY_INTERVAL_SECONDS}s)"
    )

    while True:
        await asyncio.sleep(settings.RETRY_INTERVAL_SECONDS)

        try:
            pending = await get_pending_notifications(client)
            if pending:
                logger.info(
                    f"Processing {len(pending)} pending notifications"
                )
                for notification in pending:
                    await retry_notification(client, notification)
        except Exception as e:
            logger.error(f"Retry loop error: {e}")
