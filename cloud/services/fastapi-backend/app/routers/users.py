"""ILEWS backend – Users API router (admin only)."""

import random
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.schemas.users import UserCreate, UserOut, UserRoleUpdate
from app.utils.audit import write_audit_log
from app.utils.dependencies import require_role
from app.utils.response import paginated_meta, success_response
from app.utils.security import hash_password

router = APIRouter(prefix="/v1/users", tags=["users"])


def _user_dict(u: User) -> dict:
    return UserOut.model_validate(u).model_dump(mode="json")


def _generate_user_id() -> str:
    return f"USR-{random.randint(1, 9999):04d}"


# ---------- LIST users -------------------------------------------------------

@router.get("")
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_role("system_admin"))],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    total = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar() or 0

    q = select(User).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).scalars().all()
    return success_response(
        [_user_dict(u) for u in rows],
        meta=paginated_meta(page=page, per_page=per_page, total=total),
    )


# ---------- CREATE user ------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_role("system_admin"))],
):
    existing = (
        await db.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "ERR_DUPLICATE_USER")

    user = User(
        user_id=_generate_user_id(),
        email=body.email,
        name=body.name,
        role=body.role,
        organisation=body.organisation,
        phone=body.phone,
        password_hash=hash_password(body.password) if body.password else None,
        created_by=admin.email,
    )
    db.add(user)

    await write_audit_log(
        db,
        actor_id=admin.user_id,
        action="user.create",
        resource_type="user",
        resource_id=user.user_id,
        new_value={"email": body.email, "role": body.role},
    )
    await db.commit()
    await db.refresh(user)
    return success_response(_user_dict(user))


# ---------- UPDATE role ------------------------------------------------------

@router.put("/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: UserRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_role("system_admin"))],
):
    user = (
        await db.execute(select(User).where(User.user_id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_USER_NOT_FOUND")

    old_role = user.role
    user.role = body.role

    await write_audit_log(
        db,
        actor_id=admin.user_id,
        action="user.role_update",
        resource_type="user",
        resource_id=user_id,
        old_value={"role": old_role},
        new_value={"role": body.role},
    )
    await db.commit()
    await db.refresh(user)
    return success_response(_user_dict(user))


# ---------- DEACTIVATE (soft delete) -----------------------------------------

@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_role("system_admin"))],
):
    user = (
        await db.execute(select(User).where(User.user_id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_USER_NOT_FOUND")

    user.is_active = False

    await write_audit_log(
        db,
        actor_id=admin.user_id,
        action="user.deactivate",
        resource_type="user",
        resource_id=user_id,
    )
    await db.commit()
    return success_response({"deactivated": True})
