"""ILEWS backend – Sensor Readings API router."""

import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.users import User
from app.schemas.sensor_readings import ReadingCreate, ReadingOut
from app.services import reading_service
from app.utils.dependencies import get_current_user, require_role
from app.utils.response import paginated_meta, success_response

router = APIRouter(tags=["readings"])


# ---------- helpers ----------------------------------------------------------

async def _get_redis():
    """Yield a Redis connection, or None if unavailable."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        yield r
        await r.aclose()
    except Exception:
        yield None


# ---------- GET latest reading for a node ------------------------------------

@router.get("/v1/nodes/{node_id}/readings/latest")
async def get_latest_reading(
    node_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    redis = None
    try:
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        pass

    data = await reading_service.get_latest_reading(db, node_id, redis=redis)

    if redis:
        await redis.aclose()

    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_NO_READINGS")
    return success_response(data)


# ---------- GET historical readings ------------------------------------------

@router.get("/v1/nodes/{node_id}/readings")
async def get_readings_history(
    node_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    resample: str = Query("raw", pattern="^(raw|1min|15min|1h)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    rows, total = await reading_service.get_readings_history(
        db, node_id, start_time, end_time,
        resample=resample, page=page, per_page=per_page,
    )
    return success_response(
        rows,
        meta=paginated_meta(page=page, per_page=per_page, total=total),
    )


# ---------- GET export -------------------------------------------------------

@router.get("/v1/nodes/{node_id}/readings/export")
async def export_readings(
    node_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator",
    ))],
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    format: str = Query("csv", pattern="^(csv|json)$"),
):
    rows, _ = await reading_service.get_readings_history(
        db, node_id, start_time, end_time, resample="raw", page=1, per_page=100_000,
    )

    if format == "json":
        import json
        content = json.dumps(rows, default=str)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={node_id}_readings.json"
            },
        )

    # CSV
    if not rows:
        csv_content = ""
    else:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        csv_content = output.getvalue()

    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={node_id}_readings.csv"
        },
    )


# ---------- GET latest readings for a slope ----------------------------------

@router.get("/v1/slopes/{slope_id}/readings/latest")
async def get_slope_latest_readings(
    slope_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    data = await reading_service.get_latest_readings_for_slope(db, slope_id)
    return success_response(data)


# ---------- POST internal ingest (service-to-service) ------------------------

@router.post(
    "/v1/internal/readings",
    status_code=status.HTTP_201_CREATED,
)
async def ingest_reading(
    body: ReadingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_service_api_key: str = Header(...),
):
    """Internal endpoint for ETL service. Auth via service API key header."""
    if x_service_api_key != settings.SERVICE_API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "ERR_INVALID_API_KEY")

    redis = None
    try:
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        pass

    data = await reading_service.ingest_reading(db, body, redis=redis)

    if redis:
        await redis.aclose()

    return success_response(data)
