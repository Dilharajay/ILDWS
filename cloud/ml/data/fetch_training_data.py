"""ILEWS ML Pipeline – Fetch training data from TimescaleDB."""

import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

from config import settings


def fetch_training_data(
    slope_id: str,
    start_date: str,
    end_date: str,
    resample_minutes: int = 15,
) -> pd.DataFrame:
    """Fetch sensor readings for a slope from TimescaleDB.

    Args:
        slope_id: Slope identifier.
        start_date: ISO format start date (e.g., '2025-01-01').
        end_date: ISO format end date.
        resample_minutes: Resample interval in minutes (default 15).

    Returns:
        DataFrame with sensor columns, indexed by timestamp.
    """
    engine = create_engine(settings.DATABASE_URL_SYNC)

    query = text("""
        SELECT
            timestamp,
            node_id,
            soil_moisture_1_pct,
            soil_moisture_2_pct,
            soil_moisture_3_pct,
            soil_moisture_4_pct,
            soil_moisture_5_pct,
            rainfall_mm,
            tilt_x_deg,
            tilt_y_deg,
            acceleration_x,
            acceleration_y,
            acceleration_z,
            vibration_frequency_hz,
            vibration_amplitude,
            battery_voltage,
            signal_strength_dbm
        FROM sensor_readings sr
        JOIN sensor_nodes sn ON sr.node_id = sn.node_id
        WHERE sn.slope_id = :slope_id
          AND sr.timestamp >= :start_date
          AND sr.timestamp < :end_date
        ORDER BY sr.timestamp ASC
    """)

    logger.info(
        f"Fetching data for slope {slope_id} "
        f"from {start_date} to {end_date}"
    )

    df = pd.read_sql(
        query,
        engine,
        params={
            "slope_id": slope_id,
            "start_date": start_date,
            "end_date": end_date,
        },
        parse_dates=["timestamp"],
    )

    if df.empty:
        logger.warning(f"No data found for slope {slope_id}")
        return df

    # Set timestamp as index
    df.set_index("timestamp", inplace=True)

    # Resample to regular intervals (mean aggregation per node)
    if resample_minutes > 0:
        df = (
            df.groupby("node_id")
            .resample(f"{resample_minutes}min")
            .mean(numeric_only=True)
            .reset_index(level="node_id")
        )
        # Forward-fill small gaps (up to 1 hour)
        df = df.groupby("node_id").apply(
            lambda g: g.ffill(limit=4), include_groups=False
        )

    logger.info(
        f"Fetched {len(df)} records for slope {slope_id} "
        f"({df.index.min()} to {df.index.max()})"
    )

    return df


def fetch_labeled_events(slope_id: str) -> pd.DataFrame:
    """Fetch labeled landslide events for a slope.

    Returns DataFrame with columns: event_start, event_end, severity.
    Used for creating binary labels for training.
    """
    engine = create_engine(settings.DATABASE_URL_SYNC)

    query = text("""
        SELECT event_start, event_end, severity
        FROM landslide_events
        WHERE slope_id = :slope_id
        ORDER BY event_start ASC
    """)

    return pd.read_sql(
        query, engine, params={"slope_id": slope_id},
        parse_dates=["event_start", "event_end"],
    )
