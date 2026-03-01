"""ILEWS backend – Risk score service layer with Redis caching."""

import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk_scores import RiskScore
from app.models.slopes import Slope
from app.schemas.risk_scores import RiskScoreCreate, RiskScoreOut

REDIS_RISK_TTL = 900  # 15 minutes


class _Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def _risk_dict(r: RiskScore) -> dict:
    return RiskScoreOut.model_validate(r).model_dump(mode="json")


async def get_current_risk(
    db: AsyncSession,
    slope_id: str,
    redis=None,
) -> dict | None:
    """Return current (latest) risk score for a slope."""
    cache_key = f"risk:{slope_id}:current"

    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    q = (
        select(RiskScore)
        .where(RiskScore.slope_id == slope_id)
        .order_by(RiskScore.timestamp.desc())
        .limit(1)
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        return None

    data = _risk_dict(row)

    if redis is not None:
        try:
            await redis.set(cache_key, json.dumps(data, cls=_Encoder), ex=REDIS_RISK_TTL)
        except Exception:
            pass

    return data


async def get_risk_history(
    db: AsyncSession,
    slope_id: str,
    start_time: datetime,
    end_time: datetime,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict], int]:
    """Return paginated risk score history for a slope."""
    base = (
        (RiskScore.slope_id == slope_id)
        & (RiskScore.timestamp >= start_time)
        & (RiskScore.timestamp <= end_time)
    )

    total = (
        await db.execute(select(func.count()).select_from(RiskScore).where(base))
    ).scalar() or 0

    q = (
        select(RiskScore)
        .where(base)
        .order_by(RiskScore.timestamp.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = (await db.execute(q)).scalars().all()
    return [_risk_dict(r) for r in rows], total


async def get_all_slopes_risk_overview(
    db: AsyncSession,
    redis=None,
) -> list[dict]:
    """Return current risk level for every slope (map overview)."""
    slopes = (await db.execute(select(Slope))).scalars().all()
    results = []

    for slope in slopes:
        risk_data = await get_current_risk(db, slope.slope_id, redis=redis)
        results.append({
            "slope_id": slope.slope_id,
            "slope_name": slope.name,
            "risk_level": risk_data["risk_level"] if risk_data else "GREEN",
            "risk_score": risk_data["risk_score"] if risk_data else 0.0,
            "latitude_centroid": float(slope.latitude_centroid) if slope.latitude_centroid else None,
            "longitude_centroid": float(slope.longitude_centroid) if slope.longitude_centroid else None,
            "computed_at": risk_data.get("timestamp") if risk_data else None,
        })

    return results


async def update_risk_score(
    db: AsyncSession,
    data: RiskScoreCreate,
    redis=None,
) -> dict:
    """Write a new risk score to DB and update Redis cache.

    If level changed to RED or ORANGE, returns a flag signalling the
    notification service should be triggered.
    """
    score = RiskScore(**data.model_dump())
    db.add(score)
    await db.commit()
    await db.refresh(score)
    result = _risk_dict(score)

    # Update Redis
    cache_key = f"risk:{data.slope_id}:current"
    if redis is not None:
        try:
            await redis.set(cache_key, json.dumps(result, cls=_Encoder), ex=REDIS_RISK_TTL)
        except Exception:
            pass

    # Publish internal event if RED/ORANGE for notification service
    if data.risk_level in ("RED", "ORANGE") and redis is not None:
        try:
            event = json.dumps({
                "slope_id": data.slope_id,
                "level": data.risk_level,
                "risk_score": float(data.risk_score),
                "timestamp": data.timestamp.isoformat(),
            })
            await redis.publish("ilews:alerts:new", event)
        except Exception:
            pass

    return result
