"""ILEWS backend – audit log helper for write operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    actor_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    result: str = "success",
    old_value: dict | None = None,
    new_value: dict | None = None,
    error_detail: str | None = None,
) -> None:
    """Insert a single audit log record and flush (but not commit)."""
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        old_value=old_value,
        new_value=new_value,
        error_detail=error_detail,
    )
    db.add(log)
    await db.flush()
