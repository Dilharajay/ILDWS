"""Audit trail for system actions."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "action IN ("
            "'login', 'logout', 'create', 'update', 'delete', "
            "'acknowledge_alert', 'resolve_alert', 'export', 'config_change'"
            ")",
            name="ck_audit_logs_action",
        ),
    )

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    action = Column(String(30), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(50))
    description = Column(Text)
    previous_value = Column(JSONB)
    new_value = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(String(300))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")
