"""Periodic snapshots of sensor node hardware health (TimescaleDB hypertable)."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
)

from app.database import Base


class NodeHealthSnapshot(Base):
    __tablename__ = "node_health_snapshots"
    __table_args__ = (
        PrimaryKeyConstraint("snapshot_id", "timestamp"),
        CheckConstraint(
            "connectivity_status IN ('online', 'offline', 'degraded')",
            name="chk_health_conn",
        ),
    )

    snapshot_id = Column(BigInteger, autoincrement=True)
    node_id = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    connectivity_status = Column(String(20), nullable=False)
    battery_voltage_v = Column(Numeric(5, 2))
    battery_pct = Column(SmallInteger)
    solar_input_w = Column(Numeric(5, 2))
    enclosure_temp_c = Column(Numeric(5, 2))
    packet_success_1h = Column(SmallInteger)
    packet_total_1h = Column(SmallInteger)
    rssi_dbm_avg = Column(SmallInteger)
    firmware_version = Column(String(20))
