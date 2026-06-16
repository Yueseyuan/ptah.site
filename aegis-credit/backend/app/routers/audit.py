"""Audit log router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog
from app.dependencies import get_current_user, require_admin
from app.models import User

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _out(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("/case/{case_id}")
def list_case_audit(
    case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List audit logs for a specific case (resource_type=case, resource_id=case_id)."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == "case", AuditLog.resource_id == case_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    return [_out(log) for log in logs]


@router.get("/")
def list_recent_audit(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List the 500 most recent audit log entries (admin only)."""
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(500)
        .all()
    )
    return [_out(log) for log in logs]
