"""ILEWS Notification Service – Push notification dispatcher via FCM HTTP v1."""

from typing import Optional

import httpx
from loguru import logger
from prometheus_client import Counter

from app.config import settings
from app.dispatchers.sms import AlertPayload

push_sent_counter = Counter("notif_push_sent_total", "Push notifications sent")
push_failed_counter = Counter(
    "notif_push_failed_total", "Push notifications failed"
)


def _build_push_payload(alert: AlertPayload) -> dict:
    """Build FCM v1 push notification payload."""
    action = alert.action_text or {
        "RED": "EVACUATE IMMEDIATELY",
        "ORANGE": "Prepare for possible evacuation",
        "YELLOW": "Monitor closely",
    }.get(alert.level, "Check dashboard")

    color_map = {
        "RED": "#FF0000",
        "ORANGE": "#FF8C00",
        "YELLOW": "#FFD700",
        "GREEN": "#00AA00",
    }

    return {
        "notification": {
            "title": f"ILEWS {alert.level} Alert - {alert.slope_name}",
            "body": (
                f"Risk Score: {alert.risk_score:.2f} | {action}"
            ),
        },
        "data": {
            "alert_id": alert.alert_id,
            "slope_id": alert.slope_id,
            "level": alert.level,
            "risk_score": str(alert.risk_score),
            "click_action": (
                f"{settings.DASHBOARD_URL}/map?slope={alert.slope_id}"
            ),
        },
        "android": {
            "priority": "high",
            "notification": {
                "color": color_map.get(alert.level, "#808080"),
                "channel_id": "ilews_alerts",
            },
        },
    }


async def _get_access_token() -> Optional[str]:
    """Get OAuth2 access token for FCM using service account."""
    if not settings.FCM_SERVICE_ACCOUNT_JSON:
        logger.warning("FCM service account not configured")
        return None

    try:
        import google.oauth2.service_account as sa
        import google.auth.transport.requests

        credentials = sa.Credentials.from_service_account_file(
            settings.FCM_SERVICE_ACCOUNT_JSON,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        credentials.refresh(google.auth.transport.requests.Request())
        return credentials.token
    except Exception as e:
        logger.error(f"Failed to get FCM access token: {e}")
        return None


async def send_push(
    device_tokens: list[str], alert: AlertPayload
) -> dict:
    """Send push notifications to all device tokens via FCM HTTP v1 API.

    Args:
        device_tokens: List of FCM device registration tokens.
        alert: Alert payload data.

    Returns:
        Dict with 'sent' and 'failed' counts.
    """
    if not settings.FCM_PROJECT_ID:
        logger.warning("FCM project not configured, skipping push")
        return {"sent": 0, "failed": 0, "skipped": True}

    access_token = await _get_access_token()
    if not access_token:
        return {"sent": 0, "failed": len(device_tokens), "skipped": True}

    payload = _build_push_payload(alert)
    url = (
        f"https://fcm.googleapis.com/v1/projects/"
        f"{settings.FCM_PROJECT_ID}/messages:send"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    sent = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        for token in device_tokens:
            message = {
                "message": {
                    **payload,
                    "token": token,
                }
            }
            try:
                resp = await client.post(
                    url, json=message, headers=headers, timeout=10
                )
                if resp.status_code == 200:
                    sent += 1
                    push_sent_counter.inc()
                else:
                    failed += 1
                    push_failed_counter.inc()
                    logger.warning(
                        f"FCM push failed for token {token[:20]}...: "
                        f"{resp.status_code}"
                    )
            except Exception as e:
                failed += 1
                push_failed_counter.inc()
                logger.error(f"FCM push error: {e}")

    logger.info(
        f"Push dispatch: {sent} sent, {failed} failed "
        f"(out of {len(device_tokens)} tokens)"
    )
    return {"sent": sent, "failed": failed}
