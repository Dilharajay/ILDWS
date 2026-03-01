"""Time-series sensor readings (TimescaleDB hypertable)."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Numeric,
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
        CheckConstraint(
            "data_quality IN ('valid', 'suspect', 'invalid', 'missing')",
            name="ck_sensor_readings_data_quality",
        ),
        CheckConstraint(
            "source IN ('lora', 'wifi', 'cellular', 'manual', 'simulated')",
            name="ck_sensor_readings_source",
        ),
        CheckConstraint(
            "battery_voltage_v IS NULL OR battery_voltage_v BETWEEN 0 AND 15",
            name="ck_sensor_readings_battery",
        ),
        {"comment": "Convert to TimescaleDB hypertable on timestamp column"},
    )

    reading_id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_id = Column(String(20), nullable=False)
    slope_id = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    packet_id = Column(String(40))

    # Soil moisture at up to 5 depths (percentage)
    soil_moisture_d1_pct = Column(Numeric(5, 2))
    soil_moisture_d2_pct = Column(Numeric(5, 2))
    soil_moisture_d3_pct = Column(Numeric(5, 2))
    soil_moisture_d4_pct = Column(Numeric(5, 2))
    soil_moisture_d5_pct = Column(Numeric(5, 2))

    # Rainfall
    rainfall_mm = Column(Numeric(6, 2))

    # Tilt
    tilt_x_deg = Column(Numeric(7, 4))
    tilt_y_deg = Column(Numeric(7, 4))

    # Accelerometer
    accel_x_ms2 = Column(Numeric(8, 4))
    accel_y_ms2 = Column(Numeric(8, 4))
    accel_z_ms2 = Column(Numeric(8, 4))

    # Vibration
    vibration_hz = Column(Numeric(8, 3))
    vibration_amplitude = Column(Numeric(8, 4))

    # Power & connectivity
    battery_voltage_v = Column(Numeric(5, 2))
    solar_input_w = Column(Numeric(5, 2))
    rssi_dbm = Column(SmallInteger)

    # Quality
    data_quality = Column(String(20), server_default="valid")
    quality_flags = Column(JSONB)
    source = Column(String(20), server_default="lora")

    node = relationship("SensorNode", back_populates="readings", foreign_keys=[node_id],
                         primaryjoin="SensorReading.node_id == SensorNode.node_id")
