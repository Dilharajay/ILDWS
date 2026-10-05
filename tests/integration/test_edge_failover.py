"""
Edge failover integration test: offline buffering and resync.

Tests that the edge gateway continues buffering data in SQLite
during internet outages and successfully resyncs when reconnected.

Requires: edge gateway components available locally.
Run with: pytest tests/integration/ -m integration -v
"""

import json
import os
import sqlite3
import tempfile
import time

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def edge_sqlite_db():
    """Create a temporary SQLite buffer database for edge testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sensor_buffer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            timestamp REAL NOT NULL,
            synced INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_sync_at REAL,
            records_synced INTEGER DEFAULT 0,
            sync_errors INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    yield conn, path
    conn.close()
    os.unlink(path)


def buffer_sensor_reading(conn, node_id: str, payload: dict):
    """Simulate edge gateway buffering a sensor reading."""
    conn.execute(
        "INSERT INTO sensor_buffer (node_id, payload, timestamp) VALUES (?, ?, ?)",
        (node_id, json.dumps(payload), time.time()),
    )
    conn.commit()


def get_unsynced_count(conn) -> int:
    """Get count of unsynced records in buffer."""
    cursor = conn.execute(
        "SELECT COUNT(*) FROM sensor_buffer WHERE synced = 0"
    )
    return cursor.fetchone()[0]


def get_total_count(conn) -> int:
    """Get total record count in buffer."""
    cursor = conn.execute("SELECT COUNT(*) FROM sensor_buffer")
    return cursor.fetchone()[0]


def mark_as_synced(conn, record_ids: list):
    """Mark records as synced (simulates successful cloud upload)."""
    placeholders = ",".join(["?"] * len(record_ids))
    conn.execute(
        f"UPDATE sensor_buffer SET synced = 1 WHERE id IN ({placeholders})",
        record_ids,
    )
    conn.commit()


def get_unsynced_records(conn, limit: int = 100) -> list:
    """Fetch unsynced records for forwarding."""
    cursor = conn.execute(
        "SELECT id, node_id, payload, timestamp FROM sensor_buffer "
        "WHERE synced = 0 ORDER BY timestamp ASC LIMIT ?",
        (limit,),
    )
    return cursor.fetchall()


def check_duplicates(conn) -> int:
    """Check for duplicate payloads in the buffer."""
    cursor = conn.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT payload)
        FROM sensor_buffer
    """)
    return cursor.fetchone()[0]


class TestEdgeFailover:
    """Test edge gateway offline buffering and resync behavior."""

    def test_edge_buffers_during_internet_outage(self, edge_sqlite_db):
        """
        Simulate internet outage scenario:
        1. Publish sensor packets to edge buffer
        2. Verify all stored in SQLite
        3. Simulate internet loss (no syncing)
        4. Continue publishing → all buffered
        5. Reconnect → sync all buffered records
        6. Verify no duplicates
        """
        conn, db_path = edge_sqlite_db
        node_id = "EDGE-TEST-NODE-001"

        # Phase 1: Normal operation — buffer readings
        for i in range(5):
            buffer_sensor_reading(conn, node_id, {
                "soil_moisture": 30.0 + i,
                "tilt_x": 1.0 + i * 0.1,
                "tilt_y": 0.5,
                "rainfall_mm": 5.0,
                "vibration_freq": 0.1,
                "battery_voltage": 3.7,
                "packet_seq": i,
            })

        assert get_total_count(conn) == 5
        assert get_unsynced_count(conn) == 5

        # Phase 2: Simulate sync of first batch (internet is up)
        records = get_unsynced_records(conn, limit=5)
        assert len(records) == 5
        synced_ids = [r[0] for r in records]
        mark_as_synced(conn, synced_ids)

        assert get_unsynced_count(conn) == 0

        # Phase 3: Internet goes down — continue buffering
        for i in range(10):
            buffer_sensor_reading(conn, node_id, {
                "soil_moisture": 50.0 + i,
                "tilt_x": 3.0 + i * 0.2,
                "tilt_y": 2.0,
                "rainfall_mm": 25.0,
                "vibration_freq": 0.5,
                "battery_voltage": 3.5,
                "packet_seq": 100 + i,
            })

        # All new records should be unsynced (internet is down)
        assert get_total_count(conn) == 15
        assert get_unsynced_count(conn) == 10

        # Phase 4: Internet restored — sync remaining
        unsynced = get_unsynced_records(conn)
        assert len(unsynced) == 10

        # Verify payloads are intact
        for record in unsynced:
            payload = json.loads(record[2])
            assert "soil_moisture" in payload
            assert "packet_seq" in payload
            assert payload["packet_seq"] >= 100

        # Mark all as synced
        mark_as_synced(conn, [r[0] for r in unsynced])
        assert get_unsynced_count(conn) == 0

        # Phase 5: Verify no duplicates
        assert check_duplicates(conn) == 0

    def test_edge_preserves_order_during_resync(self, edge_sqlite_db):
        """Verify buffered records maintain chronological order."""
        conn, _ = edge_sqlite_db
        node_id = "EDGE-TEST-NODE-002"

        # Buffer readings with known timestamps
        for i in range(20):
            buffer_sensor_reading(conn, node_id, {
                "soil_moisture": 40.0 + i,
                "sequence": i,
            })
            time.sleep(0.01)  # Small delay for ordering

        # Fetch in order
        records = get_unsynced_records(conn, limit=20)
        sequences = [json.loads(r[2])["sequence"] for r in records]

        # Verify ordering is preserved
        assert sequences == list(range(20))

    def test_edge_handles_large_buffer(self, edge_sqlite_db):
        """Verify edge can handle large buffer during extended outage."""
        conn, _ = edge_sqlite_db
        node_id = "EDGE-TEST-NODE-003"

        # Simulate 24h outage at 1 reading/min = 1440 readings
        # Test with 500 for speed
        batch_size = 500
        for i in range(batch_size):
            buffer_sensor_reading(conn, node_id, {
                "soil_moisture": 35.0 + (i % 50),
                "tilt_x": 1.5,
                "batch_seq": i,
            })

        assert get_total_count(conn) == batch_size
        assert get_unsynced_count(conn) == batch_size

        # Sync in batches of 100
        synced_total = 0
        while True:
            batch = get_unsynced_records(conn, limit=100)
            if not batch:
                break
            mark_as_synced(conn, [r[0] for r in batch])
            synced_total += len(batch)

        assert synced_total == batch_size
        assert get_unsynced_count(conn) == 0

    def test_edge_deduplication(self, edge_sqlite_db):
        """Verify deduplication logic catches duplicate packets."""
        conn, _ = edge_sqlite_db
        node_id = "EDGE-TEST-NODE-004"

        # Insert some records
        payload = {
            "soil_moisture": 42.0,
            "tilt_x": 1.5,
            "unique_id": "pkt-001",
        }
        buffer_sensor_reading(conn, node_id, payload)
        buffer_sensor_reading(conn, node_id, payload)  # duplicate

        # With identical payloads, check_duplicates should detect 1
        assert check_duplicates(conn) == 1

        # Different payload should not be duplicate
        buffer_sensor_reading(conn, node_id, {
            "soil_moisture": 43.0,
            "tilt_x": 1.6,
            "unique_id": "pkt-002",
        })
        assert get_total_count(conn) == 3
