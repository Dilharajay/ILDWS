"""System users and authentication."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'engineer', 'responder', 'viewer')",
            name="ck_users_role",
        ),
    )

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(20))
    role = Column(String(20), nullable=False, server_default="viewer")
    is_active = Column(Boolean, server_default="true")
    assigned_slopes = Column(ARRAY(String))
    notification_preferences = Column(JSONB, server_default='{"sms": true, "push": true, "email": true}')
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    notifications = relationship("AlertNotification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
