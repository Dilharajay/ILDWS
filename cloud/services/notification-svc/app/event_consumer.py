"""ILEWS Notification Service – Redis pub/sub event consumer.

Subscribes to alert events and dispatches notifications via
SMS, push, and siren channels in parallel.
"""

import asyncio
import json

import httpx
import redis.asyncio as redis_async
from loguru import logger
from prometheus_client import Counter

from app.config import settings
from app.dispatchers.sms import send_sms, AlertPayload
from app.dispatchers.push import send_push
from app.dispatchers.siren import activate_siren

events_received_counter = Counter(
    "notif_events_received_total", "Alert events received from Redis"
)
events_processed_counter = Counter(
    "notif_events_processed_total", "Alert events processed"
)


async def fetch_slope_users(
    client: httpx.AsyncClient, slope_id: str
) -> dict:
    """Fetch registered users for a slope from the backend.

    Returns dict with 'sms_numbers' and 'push_tokens' lists.
    """
    url = f"{settings.BACKEND_URL}/v1/internal/slopes/{slope_id}/contacts"
    headers = {"X-Service-Api-Key": settings.SERVICE_API_KEY}

    try:
        resp = await client.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", {})
    except Exception as e:
        logger.error(f"Error fetching contacts for {slope_id}: {e}")

    return {"sms_numbers": [], "push_tokens": [], "gateway_id": None}


async def record_notification(
    client: httpx.AsyncClient,
    alert_id: str,
    channel: str,
    status: str,
    recipient: str = "",
) -> None:
    """Record notification dispatch result to the backend."""
    url = f"{settings.BACKEND_URL}/v1/internal/notifications"
    headers = {
        "X-Service-Api-Key": settings.SERVICE_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "alert_id": alert_id,
        "channel": channel,
        "status": status,
        "recipient": recipient,
    }

    try:
        await client.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        logger.error(f"Error recording notification: {e}")


async def dispatch_alert(
    client: httpx.AsyncClient, event_data: dict
) -> None:
    """Dispatch notifications for an alert event."""
    slope_id = event_data.get("slope_id", "")
    level = event_data.get("level", "")
    alert_id = event_data.get("alert_id", "")

    alert = AlertPayload(
        alert_id=alert_id,
        slope_id=slope_id,
        slope_name=event_data.get("slope_name", slope_id),
        level=level,
        risk_score=event_data.get("risk_score", 0.0),
        timestamp=event_data.get("timestamp", ""),
    )

    # Fetch contacts
    contacts = await fetch_slope_users(client, slope_id)
    sms_numbers = contacts.get("sms_numbers", [])
    push_tokens = contacts.get("push_tokens", [])
    gateway_id = contacts.get("gateway_id")

    tasks = []

    # SMS dispatch for RED and ORANGE alerts
    if level in ("RED", "ORANGE") and sms_numbers:
        for number in sms_numbers:
            tasks.append(_dispatch_sms(client, number, alert))

    # Push notification for all alert levels
    if push_tokens:
        tasks.append(_dispatch_push(client, push_tokens, alert))

    # Siren for RED alerts only
    if level == "RED" and gateway_id:
        tasks.append(_dispatch_siren(client, gateway_id, alert))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    events_processed_counter.inc()
    logger.info(
        f"Dispatched {level} alert for slope {slope_id}: "
        f"{len(sms_numbers)} SMS, {len(push_tokens)} push, "
        f"siren={'yes' if level == 'RED' and gateway_id else 'no'}"
    )


async def _dispatch_sms(
    client: httpx.AsyncClient, number: str, alert: AlertPayload
):
    """Send SMS and record result."""
    success = await send_sms(number, alert)
    await record_notification(
        client,
        alert.alert_id,
        "sms",
        "delivered" if success else "pending",
        recipient=number,
    )


async def _dispatch_push(
    client: httpx.AsyncClient,
    tokens: list[str],
    alert: AlertPayload,
):
    """Send push notifications and record result."""
    result = await send_push(tokens, alert)
    status = "delivered" if result.get("sent", 0) > 0 else "pending"
    await record_notification(
        client, alert.alert_id, "push", status
    )


async def _dispatch_siren(
    client: httpx.AsyncClient,
    gateway_id: str,
    alert: AlertPayload,
):
    """Activate siren and record result."""
    success = await activate_siren(gateway_id)
    await record_notification(
        client,
        alert.alert_id,
        "siren",
        "delivered" if success else "pending",
    )


async def run_consumer(client: httpx.AsyncClient):
    """Run the Redis pub/sub consumer loop."""
    redis_client = redis_async.from_url(
        settings.REDIS_URL, decode_responses=True
    )
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(settings.REDIS_CHANNEL)
    logger.info(f"Subscribed to Redis channel: {settings.REDIS_CHANNEL}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                events_received_counter.inc()
                try:
                    event_data = json.loads(message["data"])
                    logger.info(
                        f"Received alert event: "
                        f"{event_data.get('level')} for "
                        f"{event_data.get('slope_id')}"
                    )
                    await dispatch_alert(client, event_data)
                except json.JSONDecodeError:
                    logger.error(
                        f"Invalid JSON in alert event: "
                        f"{message['data'][:200]}"
                    )
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
    finally:
        await pubsub.unsubscribe(settings.REDIS_CHANNEL)
        await redis_client.close()
