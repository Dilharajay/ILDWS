"""ML model version registry."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    func,
)

from app.database import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    __table_args__ = (
        CheckConstraint(
            "deployment_status IN ('trained', 'staging', 'production', "
            "'archived', 'rejected')",
            name="chk_model_status",
        ),
    )

    registry_id = Column(Integer, primary_key=True, autoincrement=True)
    model_version = Column(String(30), unique=True, nullable=False)
    mlflow_run_id = Column(String(100))
    model_type = Column(String(50), nullable=False)
    training_start = Column(Date, nullable=False)
    training_end = Column(Date, nullable=False)
    training_samples = Column(Integer)
    auc_roc = Column(Numeric(5, 4))
    precision_score = Column(Numeric(5, 4))
    recall_score = Column(Numeric(5, 4))
    f1_score = Column(Numeric(5, 4))
    false_alarm_rate_pct = Column(Numeric(5, 2))
    lead_time_avg_min = Column(Numeric(7, 2))
    lead_time_min_min = Column(Numeric(7, 2))
    deployment_status = Column(String(20), nullable=False, server_default="trained")
    deployed_at = Column(DateTime(timezone=True))
    deployed_by = Column(String(100))
    archived_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
