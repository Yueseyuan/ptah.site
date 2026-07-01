from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisClient, NotaryLog, ServiceCase, User

router = APIRouter(prefix="/api/notary", tags=["notary"])

_VALID_ID_TYPES = {"passport", "drivers_license", "state_id"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class NotaryLogCreate(BaseModel):
    client_id: int
    service_case_id: Optional[int] = None
    document_type: str
    signer_name: str
    signer_id_type: str
    signer_id_number: Optional[str] = None
    signer_id_expiry: Optional[str] = None
    num_signers: Optional[int] = 1
    num_witnesses: Optional[int] = 0
    notarized_at: datetime
    location: Optional[str] = None
    travel_miles: Optional[float] = None
    fee_charged: Optional[float] = None
    notes: Optional[str] = None


class NotaryLogUpdate(BaseModel):
    service_case_id: Optional[int] = None
    document_type: Optional[str] = None
    signer_name: Optional[str] = None
    signer_id_type: Optional[str] = None
    signer_id_number: Optional[str] = None
    signer_id_expiry: Optional[str] = None
    num_signers: Optional[int] = None
    num_witnesses: Optional[int] = None
    notarized_at: Optional[datetime] = None
    location: Optional[str] = None
    travel_miles: Optional[float] = None
    fee_charged: Optional[float] = None
    notes: Optional[str] = None


class NotaryLogOut(BaseModel):
    id: int
    client_id: int
    service_case_id: Optional[int]
    journal_number: Optional[str]
    document_type: Optional[str]
    signer_name: Optional[str]
    signer_id_type: Optional[str]
    signer_id_number: Optional[str]
    signer_id_expiry: Optional[str]
    num_signers: Optional[int]
    num_witnesses: Optional[int]
    notarized_at: Optional[str]
    location: Optional[str]
    travel_miles: Optional[float]
    fee_charged: Optional[float]
    notes: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _out(log: NotaryLog) -> dict:
    return {
        "id": log.id,
        "client_id": log.client_id,
        "service_case_id": log.service_case_id,
        "journal_number": log.journal_number,
        "document_type": log.document_type,
        "signer_name": log.signer_name,
        "signer_id_type": log.signer_id_type,
        "signer_id_number": log.signer_id_number,
        "signer_id_expiry": log.signer_id_expiry,
        "num_signers": log.num_signers,
        "num_witnesses": log.num_witnesses,
        "notarized_at": log.notarized_at.isoformat() if log.notarized_at else None,
        "location": log.location,
        "travel_miles": log.travel_miles,
        "fee_charged": log.fee_charged,
        "notes": log.notes,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _gen_journal_number(year: int, seq: int) -> str:
    return f"NJ-{year}-{seq:06d}"


# ---------------------------------------------------------------------------
# Routes — /daily-report must come before /logs/{id} to avoid path conflict
# ---------------------------------------------------------------------------

@router.get("/daily-report")
def daily_report(
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Return all notary log entries for a given date (defaults to today),
    ordered chronologically by notarized_at.
    The response groups entries by time (HH:MM) for easy journal review.
    """
    if date is not None:
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        report_date = datetime.utcnow().date()

    day_start = datetime(report_date.year, report_date.month, report_date.day, 0, 0, 0)
    day_end = datetime(report_date.year, report_date.month, report_date.day, 23, 59, 59)

    logs = (
        db.query(NotaryLog)
        .filter(
            NotaryLog.notarized_at >= day_start,
            NotaryLog.notarized_at <= day_end,
        )
        .order_by(NotaryLog.notarized_at.asc())
        .all()
    )

    # Group by time string HH:MM
    grouped: dict = {}
    for log in logs:
        time_key = log.notarized_at.strftime("%H:%M") if log.notarized_at else "unknown"
        grouped.setdefault(time_key, []).append(_out(log))

    return {
        "date": report_date.isoformat(),
        "total_entries": len(logs),
        "by_time": grouped,
        "entries": [_out(log) for log in logs],
    }


@router.get("/logs")
def list_notary_logs(
    client_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List notary journal logs with optional filters."""
    q = db.query(NotaryLog)
    if client_id is not None:
        q = q.filter(NotaryLog.client_id == client_id)
    if date_from is not None:
        try:
            dt_from = datetime.fromisoformat(date_from)
            q = q.filter(NotaryLog.notarized_at >= dt_from)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date_from format. Use ISO 8601.")
    if date_to is not None:
        try:
            dt_to = datetime.fromisoformat(date_to)
            q = q.filter(NotaryLog.notarized_at <= dt_to)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date_to format. Use ISO 8601.")
    return [_out(log) for log in q.order_by(NotaryLog.notarized_at.desc()).all()]


@router.post("/logs", status_code=201)
def create_notary_log(
    data: NotaryLogCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Create a new notary journal entry.
    journal_number is auto-generated as NJ-{year}-{seq:06d} where seq = total count + 1.
    """
    client = db.query(AegisClient).filter(AegisClient.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if data.service_case_id is not None:
        sc = db.query(ServiceCase).filter(ServiceCase.id == data.service_case_id).first()
        if not sc:
            raise HTTPException(status_code=404, detail="Service case not found")

    if data.signer_id_type and data.signer_id_type not in _VALID_ID_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid signer_id_type '{data.signer_id_type}'. "
                   f"Must be one of: {', '.join(sorted(_VALID_ID_TYPES))}",
        )

    log = NotaryLog(**data.model_dump())
    log.journal_number = "NJ-PENDING"
    db.add(log)
    db.flush()   # populates log.id without committing

    year = (log.created_at or datetime.utcnow()).year
    total_count = db.query(NotaryLog).count()
    log.journal_number = _gen_journal_number(year, total_count)
    db.commit()
    db.refresh(log)
    return _out(log)


@router.get("/logs/{log_id}")
def get_notary_log(
    log_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Retrieve a single notary journal entry by ID."""
    log = db.query(NotaryLog).filter(NotaryLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Notary log not found")
    return _out(log)


@router.put("/logs/{log_id}")
def update_notary_log(
    log_id: int,
    data: NotaryLogUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update a notary journal entry."""
    log = db.query(NotaryLog).filter(NotaryLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Notary log not found")

    if data.signer_id_type is not None and data.signer_id_type not in _VALID_ID_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid signer_id_type '{data.signer_id_type}'. "
                   f"Must be one of: {', '.join(sorted(_VALID_ID_TYPES))}",
        )

    if data.service_case_id is not None:
        sc = db.query(ServiceCase).filter(ServiceCase.id == data.service_case_id).first()
        if not sc:
            raise HTTPException(status_code=404, detail="Service case not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(log, field, value)

    db.commit()
    db.refresh(log)
    return _out(log)


@router.delete("/logs/{log_id}", status_code=204)
def delete_notary_log(
    log_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete a notary journal entry by ID."""
    log = db.query(NotaryLog).filter(NotaryLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Notary log not found")
    db.delete(log)
    db.commit()
