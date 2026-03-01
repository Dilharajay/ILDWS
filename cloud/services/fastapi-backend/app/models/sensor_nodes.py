"""IoT sensor nodes deployed on slopes."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class SensorNode(Base):
    __tablename__ = "sensor_nodes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance', 'decommissioned')",
            name="ck_sensor_nodes_status",
        ),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name="ck_sensor_nodes_latitude",
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="ck_sensor_nodes_longitude",
        ),
    )

    node_id = Column(String(20), primary_key=True)
    slope_id = Column(
        String(20), ForeignKey("slopes.slope_id", ondelete="RESTRICT"), nullable=False
    )
    name = Column(String(100))
    latitude = Column(Numeric(9, 6), nullable=False)
    longitude = Column(Numeric(9, 6), nullable=False)
    depth_config = Column(ARRAY(Numeric), server_default="{0.5,1.0,2.0}")
    coordinate_source = Column(String(100))
    survey_reference = Column(String(100))
    firmware_version = Column(String(20))
    installed_date = Column(Date)
    status = Column(String(20), server_default="active")
    is_deleted = Column(Boolean, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    slope = relationship("Slope", back_populates="sensor_nodes")
    readings = relationship("SensorReading", back_populates="node")
