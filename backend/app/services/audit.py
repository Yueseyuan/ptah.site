from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEventType, AuditLog


async def log_event(
    db: AsyncSession,
    event_type: AuditEventType,
    *,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
