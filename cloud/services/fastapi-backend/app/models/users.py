"""System users and authentication."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('system_admin', 'operator', 'analyst', "
            "'government_viewer', 'read_only')",
            name="chk_user_role",
        ),
    )

    user_id = Column(String(20), primary_key=True)
    email = Column(String(200), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    role = Column(String(30), nullable=False)
    organisation = Column(String(200))
    phone = Column(String(30))
    is_active = Column(Boolean, nullable=False, server_default="true")
    is_sms_alert_enabled = Column(Boolean, nullable=False, server_default="false")
    is_push_alert_enabled = Column(Boolean, nullable=False, server_default="false")
    slope_access = Column(ARRAY(String(20)))
    last_login_at = Column(DateTime(timezone=True))
    password_hash = Column(Text)
    sso_subject = Column(String(200))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100))

    audit_logs = relationship(
        "AuditLog", back_populates="user",
        foreign_keys="AuditLog.actor_id",
        primaryjoin="User.user_id == foreign(AuditLog.actor_id)",
    )
