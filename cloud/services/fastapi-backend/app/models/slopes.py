"""Slope monitoring zones."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class Slope(Base):
    __tablename__ = "slopes"
    __table_args__ = (
        CheckConstraint(
            "monitoring_status IN ('active', 'inactive', 'archived')",
            name="chk_slopes_status",
        ),
        CheckConstraint(
            "latitude_centroid BETWEEN -90 AND 90",
            name="chk_slopes_lat",
        ),
        CheckConstraint(
            "longitude_centroid BETWEEN -180 AND 180",
            name="chk_slopes_lon",
        ),
    )

    slope_id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    location_name = Column(String(200))
    latitude_centroid = Column(Numeric(9, 6), nullable=False)
    longitude_centroid = Column(Numeric(9, 6), nullable=False)
    area_m2 = Column(Numeric(12, 2))
    zone_polygon = Column(JSONB)
    monitoring_status = Column(String(20), nullable=False, server_default="active")
    risk_threshold_red = Column(Numeric(4, 2), nullable=False, server_default="0.85")
    risk_threshold_orange = Column(Numeric(4, 2), nullable=False, server_default="0.65")
    risk_threshold_yellow = Column(Numeric(4, 2), nullable=False, server_default="0.40")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100))

    sensor_nodes = relationship("SensorNode", back_populates="slope")
    risk_scores = relationship("RiskScore", back_populates="slope")
    alerts = relationship("Alert", back_populates="slope")
