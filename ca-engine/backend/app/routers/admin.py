from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import AuditLog, User, Case, Client, Document, Invoice, Appointment
from app.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[str]

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/audit-log", response_model=List[AuditLogOut])
def get_audit_log(
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    q = db.query(AuditLog)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    return q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.get("/dashboard")
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Return summary statistics for the admin dashboard."""
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)

    total_clients = db.query(Client).count()
    active_cases = db.query(Case).filter(Case.status == "active").count()
    pending_signatures = db.query(Document).filter(Document.status == "pending_signature").count()
    total_invoiced = db.query(Invoice).with_entities(
        db.query(Invoice.amount).scalar_subquery()
    ).scalar() or 0

    # Simpler aggregation
    from sqlalchemy import func
    invoiced_result = db.query(func.sum(Invoice.amount)).scalar() or 0.0
    collected_result = db.query(func.sum(Invoice.paid)).scalar() or 0.0
    pending_invoice_count = db.query(Invoice).filter(Invoice.status == "pending").count()

    new_cases_this_week = db.query(Case).filter(Case.created_at >= week_ago).count()
    upcoming_appointments = db.query(Appointment).filter(
        Appointment.status == "scheduled",
        Appointment.scheduled_at >= datetime.utcnow(),
    ).count()

    case_by_division = (
        db.query(Case.division, func.count(Case.id))
        .group_by(Case.division)
        .all()
    )

    return {
        "total_clients": total_clients,
        "active_cases": active_cases,
        "new_cases_this_week": new_cases_this_week,
        "pending_signatures": pending_signatures,
        "upcoming_appointments": upcoming_appointments,
        "invoiced_total": round(invoiced_result, 2),
        "collected_total": round(collected_result, 2),
        "pending_invoices": pending_invoice_count,
        "cases_by_division": {div: count for div, count in case_by_division},
    }


@router.get("/scheduler/status")
def scheduler_status(current_user=Depends(require_admin)):
    """Return current scheduler job status."""
    from app.services.automation import get_scheduler

    scheduler = get_scheduler()
    if not scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    return {"running": True, "jobs": jobs}
