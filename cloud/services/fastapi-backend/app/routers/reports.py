"""ILEWS backend – Reports API router."""

import random
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.reports import Report
from app.models.users import User
from app.schemas.reports import ReportGenerate, ReportOut
from app.utils.dependencies import require_role
from app.utils.response import success_response

router = APIRouter(prefix="/v1/reports", tags=["reports"])


def _report_dict(r: Report) -> dict:
    return ReportOut.model_validate(r).model_dump(mode="json")


def _generate_report_id() -> str:
    year = datetime.now(timezone.utc).year
    seq = random.randint(1, 99999)
    return f"RPT-{year}-{seq:05d}"


# ---------- POST generate report ---------------------------------------------

@router.post("/generate", status_code=202)
async def generate_report(
    body: ReportGenerate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator", "analyst",
    ))],
):
    """Queue a new report for generation."""
    report = Report(
        report_id=_generate_report_id(),
        report_type=body.report_type,
        requested_by=user.email,
        slope_ids=body.slope_ids,
        start_date=body.start_date,
        end_date=body.end_date,
        output_format=body.format,
        status="queued",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return success_response(_report_dict(report))


# ---------- GET report status / download -------------------------------------

@router.get("/{report_id}")
async def get_report(
    report_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(require_role(
        "system_admin", "slope_manager", "operator", "analyst",
    ))],
):
    report = (
        await db.execute(select(Report).where(Report.report_id == report_id))
    ).scalar_one_or_none()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_REPORT_NOT_FOUND")
    return success_response(_report_dict(report))
