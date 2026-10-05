"""Alert notification delivery tracking."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    SmallInteger,
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
            "channel IN ('sms', 'push', 'siren', 'email', 'websocket')",
            name="chk_notif_channel",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'failed')",
            name="chk_notif_status",
        ),
    )

    notification_id = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_id = Column(
        String(30), ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False
    )
    channel = Column(String(20), nullable=False)
    recipient = Column(String(200))
    status = Column(String(20), nullable=False, server_default="pending")
    attempt_count = Column(SmallInteger, nullable=False, server_default="0")
    last_attempt_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    provider_response = Column(JSONB)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    alert = relationship("Alert", back_populates="notifications")
