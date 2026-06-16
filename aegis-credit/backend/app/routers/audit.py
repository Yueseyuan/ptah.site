from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditLog
from app.dependencies import get_current_user, require_admin
from app.models import User

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _out(a: AuditLog) -> dict:
    return {
        "id": a.id,
        "username": a.username,
        "action": a.action,
        "resource_type": a.resource_type,
        "resource_id": a.resource_id,
        "detail": a.detail,
        "ip_address": a.ip_address,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/case/{case_id}")
def list_case_audit(case_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == "case", AuditLog.resource_id == case_id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
    return [_out(a) for a in logs]


@router.get("/")
def list_all_audit(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(500).all()
    return [_out(a) for a in logs]
