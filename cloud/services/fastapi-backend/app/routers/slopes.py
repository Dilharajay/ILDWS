"""ILEWS backend – Slopes CRUD router (/v1/slopes)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.slopes import Slope
from app.models.users import User
from app.schemas.slopes import SlopeCreate, SlopeOut, SlopeUpdate
from app.utils.audit import write_audit_log
from app.utils.dependencies import get_current_user, require_role
from app.utils.response import paginated_meta, success_response

router = APIRouter(prefix="/v1/slopes", tags=["slopes"])


# ---------- helpers ----------------------------------------------------------

def _slope_dict(s: Slope) -> dict:
    return SlopeOut.model_validate(s).model_dump(mode="json")


# ---------- LIST -------------------------------------------------------------

@router.get("")
async def list_slopes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    monitoring_status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    """List all monitored slopes (paginated)."""
    q = select(Slope)
    count_q = select(func.count()).select_from(Slope)

    if monitoring_status:
        q = q.where(Slope.monitoring_status == monitoring_status)
        count_q = count_q.where(Slope.monitoring_status == monitoring_status)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).scalars().all()

    return success_response(
        [_slope_dict(s) for s in rows],
        meta=paginated_meta(page=page, per_page=per_page, total=total),
    )


# ---------- GET ONE ----------------------------------------------------------

@router.get("/{slope_id}")
async def get_slope(
    slope_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    slope = (await db.execute(
        select(Slope).where(Slope.slope_id == slope_id)
    )).scalar_one_or_none()
    if not slope:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_SLOPE_NOT_FOUND")
    return success_response(_slope_dict(slope))


# ---------- CREATE -----------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_slope(
    body: SlopeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role("system_admin"))],
):
    existing = (await db.execute(
        select(Slope).where(Slope.slope_id == body.slope_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "ERR_DUPLICATE_SLOPE")

    slope = Slope(**body.model_dump(), created_by=user.user_id)
    db.add(slope)

    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="slope.create",
        resource_type="slope",
        resource_id=body.slope_id,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(slope)
    return success_response(_slope_dict(slope))


# ---------- UPDATE -----------------------------------------------------------

@router.put("/{slope_id}")
async def update_slope(
    slope_id: str,
    body: SlopeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role("system_admin"))],
):
    slope = (await db.execute(
        select(Slope).where(Slope.slope_id == slope_id)
    )).scalar_one_or_none()
    if not slope:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_SLOPE_NOT_FOUND")

    old = _slope_dict(slope)
    updates = body.model_dump(exclude_unset=True)
    for key, val in updates.items():
        setattr(slope, key, val)

    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="slope.update",
        resource_type="slope",
        resource_id=slope_id,
        old_value=old,
        new_value=updates,
    )
    await db.commit()
    await db.refresh(slope)
    return success_response(_slope_dict(slope))
