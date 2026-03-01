"""Alert notification delivery tracking."""

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


class AlertNotification(Base):
    __tablename__ = "alert_notifications"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('sms', 'push', 'email', 'webhook', 'dashboard')",
            name="ck_alert_notifications_channel",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'failed', 'retrying')",
            name="ck_alert_notifications_status",
        ),
    )

    notification_id = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_id = Column(
        BigInteger, ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), server_default="pending", nullable=False)
    recipient_address = Column(String(200), nullable=False)
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    failure_reason = Column(Text)
    retry_count = Column(BigInteger, server_default="0")
    provider_message_id = Column(String(100))
    provider_response = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    alert = relationship("Alert", back_populates="notifications")
    user = relationship("User", back_populates="notifications")
