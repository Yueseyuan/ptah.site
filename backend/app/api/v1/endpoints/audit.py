from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.models.audit import AuditEventType, AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogList, AuditLogOut

router = APIRouter()


@router.get("", response_model=AuditLogList)
async def list_audit_logs(
    event_type: AuditEventType | None = Query(None),
    user_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    base = select(AuditLog)
    if event_type is not None:
        base = base.where(AuditLog.event_type == event_type)
    if user_id is not None:
        base = base.where(AuditLog.user_id == user_id)

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    items_result = await db.execute(
        base.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    items = list(items_result.scalars().all())

    return AuditLogList(items=items, total=total, page=page, limit=limit)
