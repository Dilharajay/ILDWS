"""ILEWS ML Inference Service – Slope scorer.

Fetches readings, builds features, runs inference, and posts results.
"""

from datetime import datetime, timezone, timedelta

import httpx
from loguru import logger

from app.config import settings
from app.model_loader import predict, get_model
from app.feature_builder import build_live_features


def _score_to_risk_level(score: float) -> str:
    """Map risk score to risk level."""
    if score <= settings.RISK_GREEN_MAX:
        return "GREEN"
    elif score <= settings.RISK_YELLOW_MAX:
        return "YELLOW"
    elif score <= settings.RISK_ORANGE_MAX:
        return "ORANGE"
    else:
        return "RED"


async def fetch_readings(
    client: httpx.AsyncClient, slope_id: str
) -> list[dict]:
    """Fetch last 24h of readings for a slope."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=settings.LOOKBACK_HOURS)

    url = f"{settings.BACKEND_URL}/v1/slopes/{slope_id}/readings/latest"
    headers = {"X-Service-Api-Key": settings.SERVICE_API_KEY}
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "limit": 1000,
    }

    try:
        resp = await client.get(
            url, headers=headers, params=params, timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", [])
    except Exception as e:
        logger.error(f"Error fetching readings for {slope_id}: {e}")

    return []


async def post_risk_score(
    client: httpx.AsyncClient,
    slope_id: str,
    risk_score: float,
    risk_level: str,
) -> bool:
    """Post risk score to the backend."""
    url = f"{settings.BACKEND_URL}/v1/internal/risk-scores"
    headers = {
        "X-Service-Api-Key": settings.SERVICE_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "slope_id": slope_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "model_version": "lstm-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resp = await client.post(
            url, json=payload, headers=headers, timeout=10
        )
        return resp.status_code in (200, 201)
    except Exception as e:
        logger.error(f"Error posting risk score for {slope_id}: {e}")
        return False


async def score_slope(
    client: httpx.AsyncClient, slope_id: str
) -> dict:
    """Score a single slope end-to-end.

    1. Fetch last 24h readings
    2. Build feature window
    3. Run model inference
    4. Map score to risk level
    5. POST result to backend

    Returns dict with slope_id, risk_score, risk_level, timestamp.
    """
    model = get_model()
    if model is None:
        logger.warning(f"No model loaded, cannot score {slope_id}")
        return {
            "slope_id": slope_id,
            "error": "model_not_loaded",
        }

    # Fetch readings
    readings = await fetch_readings(client, slope_id)
    if not readings:
        logger.warning(f"No readings available for {slope_id}")
        return {
            "slope_id": slope_id,
            "error": "no_readings",
        }

    # Build features
    timesteps = settings.LOOKBACK_HOURS * 4
    features = build_live_features(readings, timesteps=timesteps)
    if features is None:
        logger.warning(f"Insufficient data for feature building: {slope_id}")
        return {
            "slope_id": slope_id,
            "error": "insufficient_data",
        }

    # Inference
    scores = predict(features)
    risk_score = float(scores[0])
    risk_level = _score_to_risk_level(risk_score)

    # Post to backend
    await post_risk_score(client, slope_id, risk_score, risk_level)

    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(
        f"Scored {slope_id}: score={risk_score:.4f}, level={risk_level}"
    )

    return {
        "slope_id": slope_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "timestamp": timestamp,
    }
