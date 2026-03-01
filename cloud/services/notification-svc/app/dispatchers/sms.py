"""ILEWS Notification Service – SMS dispatcher via Twilio."""

from dataclasses import dataclass
from typing import Optional

from loguru import logger
from prometheus_client import Counter

from app.config import settings

sms_sent_counter = Counter("notif_sms_sent_total", "SMS notifications sent")
sms_failed_counter = Counter("notif_sms_failed_total", "SMS notifications failed")


@dataclass
class AlertPayload:
    """Alert data for notification dispatch."""

    alert_id: str
    slope_id: str
    slope_name: str
    level: str  # RED, ORANGE, YELLOW, GREEN
    risk_score: float
    timestamp: str
    action_text: str = ""


def _build_sms_message(alert: AlertPayload) -> str:
    """Build SMS message from alert payload."""
    action = alert.action_text or _default_action(alert.level)
    return (
        f"[ILEWS ALERT] Level: {alert.level} | "
        f"Slope: {alert.slope_name} | Score: {alert.risk_score:.2f}\n"
        f"Time: {alert.timestamp} | Action: {action}\n"
        f"Map: {settings.DASHBOARD_URL}/map?slope={alert.slope_id}"
    )


def _default_action(level: str) -> str:
    """Default action text based on alert level."""
    actions = {
        "RED": "EVACUATE IMMEDIATELY",
        "ORANGE": "Prepare for possible evacuation",
        "YELLOW": "Monitor closely, be alert",
        "GREEN": "Normal conditions",
    }
    return actions.get(level, "Check dashboard for details")


async def send_sms(to_number: str, alert: AlertPayload) -> bool:
    """Send SMS notification via Twilio.

    Args:
        to_number: Recipient phone number (E.164 format).
        alert: Alert payload data.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials not configured, skipping SMS")
        return False

    message_body = _build_sms_message(alert)

    try:
        # Import here to avoid import error when Twilio is not installed
        from twilio.rest import Client

        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        message = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_number,
        )
        logger.info(
            f"SMS sent to {to_number}: SID={message.sid}"
        )
        sms_sent_counter.inc()
        return True

    except Exception as e:
        logger.error(f"SMS send failed to {to_number}: {e}")
        sms_failed_counter.inc()
        return False
