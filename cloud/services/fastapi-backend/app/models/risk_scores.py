"""Computed landslide risk scores per slope."""

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


class RiskScore(Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        CheckConstraint(
            "overall_risk BETWEEN 0 AND 1",
            name="ck_risk_scores_overall_risk",
        ),
        CheckConstraint(
            "risk_level IN ('green', 'yellow', 'orange', 'red')",
            name="ck_risk_scores_risk_level",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_risk_scores_confidence",
        ),
    )

    score_id = Column(BigInteger, primary_key=True, autoincrement=True)
    slope_id = Column(
        String(20), ForeignKey("slopes.slope_id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    overall_risk = Column(Numeric(5, 4), nullable=False)
    risk_level = Column(String(10), nullable=False)
    confidence = Column(Numeric(5, 4))

    # Component scores
    soil_moisture_risk = Column(Numeric(5, 4))
    rainfall_risk = Column(Numeric(5, 4))
    tilt_risk = Column(Numeric(5, 4))
    vibration_risk = Column(Numeric(5, 4))

    model_version = Column(String(40))
    model_input_summary = Column(JSONB)
    explanation = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    slope = relationship("Slope", back_populates="risk_scores")
