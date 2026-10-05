-- ILEWS Edge Gateway – SQLite buffer schema
-- Stores sensor readings locally for offline operation and cloud sync

CREATE TABLE IF NOT EXISTS raw_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_synced INTEGER DEFAULT 0,
    synced_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_raw_readings_unsynced
    ON raw_readings(is_synced, received_at);

CREATE INDEX IF NOT EXISTS idx_raw_readings_node
    ON raw_readings(node_id, received_at);

CREATE TABLE IF NOT EXISTS local_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_score REAL NOT NULL,
    risk_level TEXT NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    siren_activated INTEGER DEFAULT 0,
    acknowledged INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_size INTEGER NOT NULL,
    success_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
