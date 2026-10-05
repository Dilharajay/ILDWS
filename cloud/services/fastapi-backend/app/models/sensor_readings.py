"""Time-series sensor readings (TimescaleDB hypertable)."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        PrimaryKeyConstraint("reading_id", "timestamp"),
        CheckConstraint(
            "data_quality IN ('valid', 'suspect', 'invalid')",
            name="chk_readings_quality",
        ),
        CheckConstraint(
            "source IN ('lora', 'edge_buffer', 'manual', 'synthetic')",
            name="chk_readings_source",
        ),
    )

    reading_id = Column(BigInteger, autoincrement=True)
    node_id = Column(String(20), nullable=False)
    slope_id = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    packet_id = Column(String(40))

    soil_moisture_d1_pct = Column(Numeric(5, 2))
    soil_moisture_d2_pct = Column(Numeric(5, 2))
    soil_moisture_d3_pct = Column(Numeric(5, 2))
    soil_moisture_d4_pct = Column(Numeric(5, 2))
    soil_moisture_d5_pct = Column(Numeric(5, 2))

    rainfall_mm = Column(Numeric(6, 2))

    tilt_x_deg = Column(Numeric(7, 4))
    tilt_y_deg = Column(Numeric(7, 4))

    accel_x_ms2 = Column(Numeric(8, 4))
    accel_y_ms2 = Column(Numeric(8, 4))
    accel_z_ms2 = Column(Numeric(8, 4))

    vibration_hz = Column(Numeric(8, 3))
    vibration_amplitude = Column(Numeric(8, 4))

    battery_voltage_v = Column(Numeric(5, 2))
    solar_input_w = Column(Numeric(5, 2))
    rssi_dbm = Column(SmallInteger)

    data_quality = Column(String(20), nullable=False, server_default="valid")
    quality_flags = Column(JSONB)
    source = Column(String(20), nullable=False, server_default="lora")

    node = relationship(
        "SensorNode", back_populates="readings",
        foreign_keys=[node_id],
        primaryjoin="foreign(SensorReading.node_id) == SensorNode.node_id",
    )
