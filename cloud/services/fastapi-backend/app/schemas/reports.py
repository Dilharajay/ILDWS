"""ILEWS backend – Pydantic schemas for reports."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ReportGenerate(BaseModel):
    """Payload for generating a report."""

    report_type: str = Field(
        ...,
        pattern="^(daily_summary|weekly_summary|monthly_summary"
                "|incident_report|raw_data_export)$",
    )
    slope_ids: list[str] | None = None
    start_date: date
    end_date: date
    format: str = Field("pdf", pattern="^(pdf|csv|json)$")
    email_to: list[str] | None = None


class ReportOut(BaseModel):
    """Public report response object."""

    model_config = {"from_attributes": True}

    report_id: str
    report_type: str
    requested_by: str
    slope_ids: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    output_format: str = "pdf"
    status: str = "queued"
    download_url: str | None = None
    url_expires_at: datetime | None = None
    file_size_bytes: int | None = None
    error_message: str | None = None
    generated_at: datetime | None = None
    created_at: datetime | None = None
