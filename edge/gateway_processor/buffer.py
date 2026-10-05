"""ILEWS Edge Gateway – SQLite buffer for offline operation."""

import os
import sqlite3
from typing import Optional

from loguru import logger

from config import settings


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get SQLite connection."""
    path = db_path or settings.SQLITE_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection = None) -> sqlite3.Connection:
    """Initialize SQLite database from schema."""
    if conn is None:
        conn = get_connection()

    schema_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "schema.sql"
    )
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    logger.info(f"SQLite buffer initialized: {settings.SQLITE_PATH}")
    return conn


def write_reading(
    conn: sqlite3.Connection, packet_json: str, node_id: str
) -> int:
    """Insert a reading into the buffer.

    Returns the row ID of the inserted record.
    """
    cursor = conn.execute(
        "INSERT INTO raw_readings (node_id, payload_json) VALUES (?, ?)",
        (node_id, packet_json),
    )
    conn.commit()
    return cursor.lastrowid


def get_unsynced(
    conn: sqlite3.Connection, limit: int = 50
) -> list[dict]:
    """Get unsynced readings ordered by received_at."""
    cursor = conn.execute(
        "SELECT id, node_id, payload_json, received_at "
        "FROM raw_readings "
        "WHERE is_synced = 0 "
        "ORDER BY received_at ASC "
        "LIMIT ?",
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]


def mark_synced(conn: sqlite3.Connection, ids: list[int]) -> int:
    """Mark records as synced. Returns count updated."""
    if not ids:
        return 0

    placeholders = ",".join("?" * len(ids))
    cursor = conn.execute(
        f"UPDATE raw_readings "
        f"SET is_synced = 1, synced_at = CURRENT_TIMESTAMP "
        f"WHERE id IN ({placeholders})",
        ids,
    )
    conn.commit()
    return cursor.rowcount


def get_pending_count(conn: sqlite3.Connection) -> int:
    """Return count of unsynced records."""
    cursor = conn.execute(
        "SELECT COUNT(*) FROM raw_readings WHERE is_synced = 0"
    )
    return cursor.fetchone()[0]


def log_sync(
    conn: sqlite3.Connection,
    batch_size: int,
    success: int,
    failed: int,
) -> None:
    """Log a sync operation."""
    conn.execute(
        "INSERT INTO sync_log (batch_size, success_count, failed_count) "
        "VALUES (?, ?, ?)",
        (batch_size, success, failed),
    )
    conn.commit()


def log_local_alert(
    conn: sqlite3.Connection,
    risk_score: float,
    risk_level: str,
    siren_activated: bool = False,
) -> int:
    """Log a local alert to SQLite."""
    cursor = conn.execute(
        "INSERT INTO local_alerts (risk_score, risk_level, siren_activated) "
        "VALUES (?, ?, ?)",
        (risk_score, risk_level, 1 if siren_activated else 0),
    )
    conn.commit()
    return cursor.lastrowid
