"""Landslide risk alerts."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "level IN ('YELLOW', 'ORANGE', 'RED')",
            name="chk_alert_level",
        ),
        CheckConstraint(
            "source IN ('ml_inference', 'edge_local', 'manual_override', 'scheduled_test')",
            name="chk_alert_source",
        ),
        CheckConstraint(
            "status IN ('active', 'acknowledged', 'resolved', 'false_alarm')",
            name="chk_alert_status",
        ),
        CheckConstraint(
            "risk_score BETWEEN 0 AND 1",
            name="chk_alerts_risk_score",
        ),
    )

    alert_id = Column(String(30), primary_key=True)
    slope_id = Column(
        String(20), ForeignKey("slopes.slope_id"), nullable=False
    )
    trigger_score_id = Column(BigInteger, nullable=True)
    level = Column(String(10), nullable=False)
    risk_score = Column(Numeric(4, 3), nullable=False)
    source = Column(String(30), nullable=False, server_default="ml_inference")
    status = Column(String(20), nullable=False, server_default="active")
    triggered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledged_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    false_alarm_confirmed = Column(Boolean, server_default="false")
    false_alarm_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    slope = relationship("Slope", back_populates="alerts")
    notifications = relationship("AlertNotification", back_populates="alert")
