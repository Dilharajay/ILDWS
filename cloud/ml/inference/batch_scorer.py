"""ILEWS ML Pipeline – Batch scorer for periodic inference."""

import httpx
from loguru import logger

from config import settings


async def fetch_active_slopes(client: httpx.AsyncClient) -> list[str]:
    """Fetch list of active slope IDs from the backend."""
    url = f"{settings.BACKEND_URL}/v1/slopes"
    headers = {"X-Service-Api-Key": settings.SERVICE_API_KEY}

    try:
        resp = await client.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            slopes = data.get("data", [])
            return [
                s["slope_id"] for s in slopes
                if s.get("status") == "active"
            ]
    except Exception as e:
        logger.error(f"Error fetching slopes: {e}")

    return []


async def score_slope_batch(
    client: httpx.AsyncClient, slope_id: str
) -> dict:
    """Trigger scoring for a slope via the ML inference service.

    In production, this would call the ml-inference service.
    This is a placeholder for the batch scoring orchestration.
    """
    url = f"{settings.BACKEND_URL}/v1/internal/score/{slope_id}"
    headers = {"X-Service-Api-Key": settings.SERVICE_API_KEY}

    try:
        resp = await client.post(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("data", {})
    except Exception as e:
        logger.error(f"Error scoring slope {slope_id}: {e}")

    return {}
