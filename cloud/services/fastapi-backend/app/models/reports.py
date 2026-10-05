"""Generated reports and download tracking."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Date,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY

from app.database import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "output_format IN ('pdf', 'csv', 'json')",
            name="chk_report_format",
        ),
        CheckConstraint(
            "status IN ('queued', 'generating', 'ready', 'failed')",
            name="chk_report_status",
        ),
    )

    report_id = Column(String(20), primary_key=True)
    report_type = Column(String(50), nullable=False)
    requested_by = Column(String(100), nullable=False)
    slope_ids = Column(ARRAY(String(20)))
    start_date = Column(Date)
    end_date = Column(Date)
    output_format = Column(String(10), nullable=False, server_default="pdf")
    status = Column(String(20), nullable=False, server_default="queued")
    file_path = Column(Text)
    download_url = Column(Text)
    url_expires_at = Column(DateTime(timezone=True))
    file_size_bytes = Column(BigInteger)
    error_message = Column(Text)
    generated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
