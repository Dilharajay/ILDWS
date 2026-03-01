"""Landslide risk alerts."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('yellow', 'orange', 'red')",
            name="ck_alerts_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'acknowledged', 'resolved', 'expired', 'false_alarm')",
            name="ck_alerts_status",
        ),
        CheckConstraint(
            "risk_score BETWEEN 0 AND 1",
            name="ck_alerts_risk_score",
        ),
    )

    alert_id = Column(BigInteger, primary_key=True, autoincrement=True)
    slope_id = Column(
        String(20), ForeignKey("slopes.slope_id", ondelete="CASCADE"), nullable=False
    )
    score_id = Column(BigInteger, ForeignKey("risk_scores.score_id"), nullable=True)
    severity = Column(String(10), nullable=False)
    status = Column(String(20), server_default="active", nullable=False)
    risk_score = Column(Numeric(5, 4), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(String(100))
    resolved_by = Column(String(100))
    resolution_notes = Column(Text)
    metadata = Column("alert_metadata", JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    slope = relationship("Slope", back_populates="alerts")
    notifications = relationship("AlertNotification", back_populates="alert")
