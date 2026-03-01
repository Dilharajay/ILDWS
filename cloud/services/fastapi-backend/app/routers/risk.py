"""ILEWS backend – Risk Scores API router."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.users import User
from app.services import risk_service
from app.utils.dependencies import get_current_user
from app.utils.response import paginated_meta, success_response

router = APIRouter(prefix="/v1/slopes", tags=["risk"])


# ---------- GET risk overview for all slopes (must be before /{slope_id}) ---

@router.get("/risk/overview")
async def get_risk_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    redis = None
    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        pass

    data = await risk_service.get_all_slopes_risk_overview(db, redis=redis)

    if redis:
        await redis.aclose()

    return success_response(data)


# ---------- GET current risk for a slope ------------------------------------

@router.get("/{slope_id}/risk")
async def get_current_risk(
    slope_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    redis = None
    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        pass

    data = await risk_service.get_current_risk(db, slope_id, redis=redis)

    if redis:
        await redis.aclose()

    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_NO_RISK_DATA")
    return success_response(data)


# ---------- GET risk history ------------------------------------------------

@router.get("/{slope_id}/risk/history")
async def get_risk_history(
    slope_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    rows, total = await risk_service.get_risk_history(
        db, slope_id, start_time, end_time, page=page, per_page=per_page,
    )
    return success_response(
        rows,
        meta=paginated_meta(page=page, per_page=per_page, total=total),
    )
