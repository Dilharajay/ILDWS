"""Computed landslide risk scores per slope (TimescaleDB hypertable)."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        PrimaryKeyConstraint("score_id", "timestamp"),
        CheckConstraint(
            "risk_score BETWEEN 0 AND 1",
            name="chk_score_range",
        ),
        CheckConstraint(
            "risk_level IN ('GREEN', 'YELLOW', 'ORANGE', 'RED')",
            name="chk_risk_level",
        ),
        CheckConstraint(
            "inference_source IN ('cloud', 'edge')",
            name="chk_score_source",
        ),
    )

    score_id = Column(BigInteger, autoincrement=True)
    slope_id = Column(
        String(20), ForeignKey("slopes.slope_id"), nullable=False
    )
    timestamp = Column(DateTime(timezone=True), nullable=False)
    risk_score = Column(Numeric(4, 3), nullable=False)
    risk_level = Column(String(10), nullable=False)
    model_version = Column(String(30), nullable=False)
    inference_source = Column(String(20), nullable=False, server_default="cloud")
    feature_window_start = Column(DateTime(timezone=True))
    feature_window_end = Column(DateTime(timezone=True))
    contributing_nodes = Column(ARRAY(String(20)))
    model_confidence = Column(Numeric(4, 3))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    slope = relationship("Slope", back_populates="risk_scores")
