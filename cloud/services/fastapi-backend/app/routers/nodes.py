"""ILEWS backend – Sensor Nodes CRUD router (/v1/nodes)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.sensor_nodes import SensorNode
from app.models.slopes import Slope
from app.models.users import User
from app.schemas.nodes import NodeCreate, NodeOut, NodeUpdate
from app.utils.audit import write_audit_log
from app.utils.dependencies import get_current_user, require_role
from app.utils.response import paginated_meta, success_response

router = APIRouter(prefix="/v1/nodes", tags=["nodes"])


# ---------- helpers ----------------------------------------------------------

def _node_dict(n: SensorNode) -> dict:
    return NodeOut.model_validate(n).model_dump(mode="json")


# ---------- LIST -------------------------------------------------------------

@router.get("")
async def list_nodes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    slope_id: str | None = None,
    node_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    """List sensor nodes (excludes soft-deleted)."""
    q = select(SensorNode).where(SensorNode.is_deleted.is_(False))
    count_q = select(func.count()).select_from(SensorNode).where(
        SensorNode.is_deleted.is_(False)
    )

    if slope_id:
        q = q.where(SensorNode.slope_id == slope_id)
        count_q = count_q.where(SensorNode.slope_id == slope_id)
    if node_status:
        q = q.where(SensorNode.status == node_status)
        count_q = count_q.where(SensorNode.status == node_status)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).scalars().all()

    return success_response(
        [_node_dict(n) for n in rows],
        meta=paginated_meta(page=page, per_page=per_page, total=total),
    )


# ---------- GET ONE ----------------------------------------------------------

@router.get("/{node_id}")
async def get_node(
    node_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    node = (await db.execute(
        select(SensorNode).where(
            SensorNode.node_id == node_id,
            SensorNode.is_deleted.is_(False),
        )
    )).scalar_one_or_none()
    if not node:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_NODE_NOT_FOUND")
    return success_response(_node_dict(node))


# ---------- CREATE -----------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_node(
    body: NodeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role("system_admin"))],
):
    # Verify referenced slope exists
    slope = (await db.execute(
        select(Slope).where(Slope.slope_id == body.slope_id)
    )).scalar_one_or_none()
    if not slope:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_SLOPE_NOT_FOUND")

    existing = (await db.execute(
        select(SensorNode).where(SensorNode.node_id == body.node_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "ERR_DUPLICATE_NODE")

    node = SensorNode(**body.model_dump())
    db.add(node)

    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="node.create",
        resource_type="sensor_node",
        resource_id=body.node_id,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(node)
    return success_response(_node_dict(node))


# ---------- UPDATE -----------------------------------------------------------

@router.put("/{node_id}")
async def update_node(
    node_id: str,
    body: NodeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role("system_admin"))],
):
    node = (await db.execute(
        select(SensorNode).where(
            SensorNode.node_id == node_id,
            SensorNode.is_deleted.is_(False),
        )
    )).scalar_one_or_none()
    if not node:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_NODE_NOT_FOUND")

    old = _node_dict(node)
    updates = body.model_dump(exclude_unset=True)
    for key, val in updates.items():
        setattr(node, key, val)

    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="node.update",
        resource_type="sensor_node",
        resource_id=node_id,
        old_value=old,
        new_value=updates,
    )
    await db.commit()
    await db.refresh(node)
    return success_response(_node_dict(node))


# ---------- DELETE (soft) ----------------------------------------------------

@router.delete("/{node_id}")
async def delete_node(
    node_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role("system_admin"))],
):
    node = (await db.execute(
        select(SensorNode).where(
            SensorNode.node_id == node_id,
            SensorNode.is_deleted.is_(False),
        )
    )).scalar_one_or_none()
    if not node:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERR_NODE_NOT_FOUND")

    node.is_deleted = True

    await write_audit_log(
        db,
        actor_id=user.user_id,
        action="node.delete",
        resource_type="sensor_node",
        resource_id=node_id,
    )
    await db.commit()
    return success_response({"deleted": True})
