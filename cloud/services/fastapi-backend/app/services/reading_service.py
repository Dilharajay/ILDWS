"""ILEWS backend – Sensor readings service layer with Redis caching."""

import json
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_readings import SensorReading
from app.schemas.sensor_readings import ReadingCreate, ReadingOut

REDIS_LATEST_TTL = 900  # 15 minutes


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal values."""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def _reading_dict(r: SensorReading) -> dict:
    return ReadingOut.model_validate(r).model_dump(mode="json")


async def get_latest_reading(
    db: AsyncSession,
    node_id: str,
    redis=None,
) -> dict | None:
    """Return latest reading for a node. Tries Redis first, falls back to DB."""
    cache_key = f"node:{node_id}:latest"

    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    q = (
        select(SensorReading)
        .where(SensorReading.node_id == node_id)
        .order_by(SensorReading.timestamp.desc())
        .limit(1)
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        return None

    data = _reading_dict(row)

    if redis is not None:
        try:
            await redis.set(
                cache_key,
                json.dumps(data, cls=DecimalEncoder),
                ex=REDIS_LATEST_TTL,
            )
        except Exception:
            pass

    return data


async def get_readings_history(
    db: AsyncSession,
    node_id: str,
    start_time: datetime,
    end_time: datetime,
    resample: str = "raw",
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict], int]:
    """Return historical readings with optional resampling."""
    base_filter = (
        (SensorReading.node_id == node_id)
        & (SensorReading.timestamp >= start_time)
        & (SensorReading.timestamp <= end_time)
    )

    if resample == "raw":
        count_q = select(func.count()).select_from(SensorReading).where(base_filter)
        total = (await db.execute(count_q)).scalar() or 0

        q = (
            select(SensorReading)
            .where(base_filter)
            .order_by(SensorReading.timestamp.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        rows = (await db.execute(q)).scalars().all()
        return [_reading_dict(r) for r in rows], total

    # Resampled queries use TimescaleDB time_bucket when available;
    # fall back to date_trunc for standard PostgreSQL.
    bucket_map = {"1min": "1 minute", "15min": "15 minutes", "1h": "1 hour"}
    interval = bucket_map.get(resample)
    if not interval:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid resample interval: {resample}",
        )

    bucket_sql = text(
        f"""
        SELECT
            time_bucket('{interval}', timestamp) AS bucket,
            node_id,
            slope_id,
            AVG(soil_moisture_d1_pct) AS soil_moisture_d1_pct,
            AVG(soil_moisture_d2_pct) AS soil_moisture_d2_pct,
            AVG(soil_moisture_d3_pct) AS soil_moisture_d3_pct,
            AVG(rainfall_mm)          AS rainfall_mm,
            AVG(tilt_x_deg)           AS tilt_x_deg,
            AVG(tilt_y_deg)           AS tilt_y_deg,
            AVG(battery_voltage_v)    AS battery_voltage_v,
            AVG(rssi_dbm)             AS rssi_dbm,
            COUNT(*)                  AS sample_count
        FROM sensor_readings
        WHERE node_id = :node_id
          AND timestamp >= :start
          AND timestamp <= :end_t
        GROUP BY bucket, node_id, slope_id
        ORDER BY bucket ASC
        LIMIT :limit OFFSET :offset
        """
    )
    rows = (
        await db.execute(
            bucket_sql,
            {
                "node_id": node_id,
                "start": start_time,
                "end_t": end_time,
                "limit": per_page,
                "offset": (page - 1) * per_page,
            },
        )
    ).mappings().all()

    count_sql = text(
        f"""
        SELECT COUNT(*) FROM (
            SELECT time_bucket('{interval}', timestamp) AS bucket
            FROM sensor_readings
            WHERE node_id = :node_id
              AND timestamp >= :start
              AND timestamp <= :end_t
            GROUP BY bucket
        ) sub
        """
    )
    total = (
        await db.execute(
            count_sql,
            {"node_id": node_id, "start": start_time, "end_t": end_time},
        )
    ).scalar() or 0

    return [dict(r) for r in rows], total


async def get_latest_readings_for_slope(
    db: AsyncSession,
    slope_id: str,
) -> list[dict]:
    """Return latest reading from each node belonging to a slope."""
    # Use DISTINCT ON (node_id) ordered by timestamp desc
    q = text(
        """
        SELECT DISTINCT ON (node_id) *
        FROM sensor_readings
        WHERE slope_id = :slope_id
        ORDER BY node_id, timestamp DESC
        """
    )
    rows = (await db.execute(q, {"slope_id": slope_id})).mappings().all()
    return [dict(r) for r in rows]


async def ingest_reading(
    db: AsyncSession,
    data: ReadingCreate,
    redis=None,
) -> dict:
    """Ingest a sensor reading with deduplication check."""
    # Dedup: check if node_id + timestamp + packet_id already exists
    if data.packet_id:
        existing = (
            await db.execute(
                select(SensorReading).where(
                    SensorReading.node_id == data.node_id,
                    SensorReading.timestamp == data.timestamp,
                    SensorReading.packet_id == data.packet_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "ERR_DUPLICATE_READING",
            )

    reading = SensorReading(**data.model_dump())
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    result = _reading_dict(reading)

    # Update Redis latest cache
    if redis is not None:
        cache_key = f"node:{data.node_id}:latest"
        try:
            await redis.set(
                cache_key,
                json.dumps(result, cls=DecimalEncoder),
                ex=REDIS_LATEST_TTL,
            )
        except Exception:
            pass

    return result
