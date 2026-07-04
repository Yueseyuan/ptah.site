"""Case monitoring endpoints — daily digest and alert list."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisCase, ServiceCase, ServiceDocument, User

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/digest/latest")
def get_latest_digest(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(ServiceDocument)
        .filter(ServiceDocument.document_type == "Daily Digest")
        .order_by(ServiceDocument.created_at.desc())
        .first()
    )
    if not doc:
        return None
    return {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.post("/digest/generate", status_code=201)
def trigger_digest(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually generate a fresh morning digest."""
    from app.jobs.monitor_job import generate_morning_digest
    doc_id = generate_morning_digest()
    if doc_id is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Digest generation failed. Check server logs.")
    doc = db.query(ServiceDocument).filter(ServiceDocument.id == doc_id).first()
    return {
        "document_id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.get("/alerts")
def get_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a live list of cases that need attention."""
    now = _utcnow()
    seven = now - timedelta(days=7)
    thirty = now - timedelta(days=30)

    stale_credit = (
        db.query(AegisCase)
        .filter(
            AegisCase.status == "active",
            (AegisCase.updated_at < seven) | (AegisCase.updated_at.is_(None)),
            AegisCase.created_at < seven,
        )
        .order_by(AegisCase.updated_at.asc().nullsfirst())
        .limit(20)
        .all()
    )

    stale_service = (
        db.query(ServiceCase)
        .filter(
            ServiceCase.status == "active",
            (ServiceCase.updated_at < seven) | (ServiceCase.updated_at.is_(None)),
            ServiceCase.created_at < seven,
        )
        .order_by(ServiceCase.updated_at.asc().nullsfirst())
        .limit(20)
        .all()
    )

    at_risk = (
        db.query(AegisCase)
        .filter(
            AegisCase.status == "active",
            AegisCase.created_at < thirty,
            (AegisCase.updated_at < thirty) | (AegisCase.updated_at.is_(None)),
        )
        .all()
    )

    new_this_week_credit = (
        db.query(AegisCase)
        .filter(AegisCase.created_at >= seven)
        .count()
    )
    new_this_week_service = (
        db.query(ServiceCase)
        .filter(ServiceCase.created_at >= seven)
        .count()
    )

    return {
        "generated_at": now.isoformat(),
        "new_this_week": {"credit": new_this_week_credit, "service": new_this_week_service},
        "stale_credit": [
            {"id": c.id, "case_number": c.case_number, "status": c.status,
             "last_activity": (c.updated_at or c.created_at).isoformat() if (c.updated_at or c.created_at) else None}
            for c in stale_credit
        ],
        "stale_service": [
            {"id": c.id, "case_number": c.case_number, "division": c.division_slug, "status": c.status,
             "last_activity": (c.updated_at or c.created_at).isoformat() if (c.updated_at or c.created_at) else None}
            for c in stale_service
        ],
        "at_risk": [
            {"id": c.id, "case_number": c.case_number,
             "last_activity": (c.updated_at or c.created_at).isoformat() if (c.updated_at or c.created_at) else None}
            for c in at_risk
        ],
    }
