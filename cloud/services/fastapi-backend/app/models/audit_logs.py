"""Audit trail for system actions. Append-only."""

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
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "result IN ('success', 'failure', 'partial')",
            name="chk_audit_result",
        ),
    )

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actor_id = Column(String(100))
    actor_ip = Column(INET)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    result = Column(String(20), nullable=False)
    error_detail = Column(Text)
    request_id = Column(UUID)

    user = relationship(
        "User", back_populates="audit_logs",
        foreign_keys=[actor_id],
        primaryjoin="foreign(AuditLog.actor_id) == User.user_id",
    )
