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
            "monitoring_status IN ('active', 'inactive', 'decommissioned')",
            name="ck_slopes_monitoring_status",
        ),
        CheckConstraint(
            "risk_threshold_red BETWEEN 0 AND 1",
            name="ck_slopes_risk_threshold_red",
        ),
        CheckConstraint(
            "risk_threshold_orange BETWEEN 0 AND 1",
            name="ck_slopes_risk_threshold_orange",
        ),
        CheckConstraint(
            "risk_threshold_yellow BETWEEN 0 AND 1",
            name="ck_slopes_risk_threshold_yellow",
        ),
        CheckConstraint(
            "risk_threshold_red > risk_threshold_orange "
            "AND risk_threshold_orange > risk_threshold_yellow",
            name="ck_slopes_threshold_order",
        ),
        CheckConstraint(
            "latitude_centroid BETWEEN -90 AND 90",
            name="ck_slopes_latitude",
        ),
        CheckConstraint(
            "longitude_centroid BETWEEN -180 AND 180",
            name="ck_slopes_longitude",
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
    monitoring_status = Column(String(20), server_default="active")
    risk_threshold_red = Column(Numeric(4, 2), server_default="0.85")
    risk_threshold_orange = Column(Numeric(4, 2), server_default="0.65")
    risk_threshold_yellow = Column(Numeric(4, 2), server_default="0.40")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100))

    sensor_nodes = relationship("SensorNode", back_populates="slope")
    risk_scores = relationship("RiskScore", back_populates="slope")
    alerts = relationship("Alert", back_populates="slope")
