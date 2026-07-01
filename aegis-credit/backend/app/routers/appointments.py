from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Appointment, AegisClient, ServiceCase, User

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

_VALID_STATUSES = {"scheduled", "confirmed", "completed", "cancelled"}
_VALID_TYPES = {"signing", "consultation", "document_review", "intake"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AppointmentCreate(BaseModel):
    client_id: int
    service_case_id: Optional[int] = None
    division_slug: str
    appointment_type: str
    scheduled_at: datetime
    duration_minutes: Optional[int] = 60
    location: Optional[str] = None
    travel_miles: Optional[float] = None
    status: Optional[str] = "scheduled"
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    service_case_id: Optional[int] = None
    division_slug: Optional[str] = None
    appointment_type: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    travel_miles: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AppointmentOut(BaseModel):
    id: int
    client_id: int
    service_case_id: Optional[int]
    division_slug: Optional[str]
    appointment_type: Optional[str]
    scheduled_at: Optional[str]
    duration_minutes: Optional[int]
    location: Optional[str]
    travel_miles: Optional[float]
    status: Optional[str]
    notes: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _out(a: Appointment) -> dict:
    return {
        "id": a.id,
        "client_id": a.client_id,
        "service_case_id": a.service_case_id,
        "division_slug": a.division_slug,
        "appointment_type": a.appointment_type,
        "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
        "duration_minutes": a.duration_minutes,
        "location": a.location,
        "travel_miles": a.travel_miles,
        "status": a.status,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ---------------------------------------------------------------------------
# Routes — /upcoming must come before /{id} to avoid path conflict
# ---------------------------------------------------------------------------

@router.get("/upcoming")
def list_upcoming_appointments(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return all scheduled appointments in the next 7 days."""
    now = datetime.utcnow()
    cutoff = now + timedelta(days=7)
    results = (
        db.query(Appointment)
        .filter(
            Appointment.status == "scheduled",
            Appointment.scheduled_at >= now,
            Appointment.scheduled_at <= cutoff,
        )
        .order_by(Appointment.scheduled_at.asc())
        .all()
    )
    return [_out(a) for a in results]


@router.get("/")
def list_appointments(
    client_id: Optional[int] = None,
    division: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List appointments with optional filters."""
    q = db.query(Appointment)
    if client_id is not None:
        q = q.filter(Appointment.client_id == client_id)
    if division is not None:
        q = q.filter(Appointment.division_slug == division)
    if status is not None:
        q = q.filter(Appointment.status == status)
    if date_from is not None:
        try:
            dt_from = datetime.fromisoformat(date_from)
            q = q.filter(Appointment.scheduled_at >= dt_from)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date_from format. Use ISO 8601.")
    if date_to is not None:
        try:
            dt_to = datetime.fromisoformat(date_to)
            q = q.filter(Appointment.scheduled_at <= dt_to)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date_to format. Use ISO 8601.")
    return [_out(a) for a in q.order_by(Appointment.scheduled_at.asc()).all()]


@router.post("/", status_code=201)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Create a new appointment."""
    client = db.query(AegisClient).filter(AegisClient.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if data.service_case_id is not None:
        sc = db.query(ServiceCase).filter(ServiceCase.id == data.service_case_id).first()
        if not sc:
            raise HTTPException(status_code=404, detail="Service case not found")

    if data.status and data.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{data.status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    appt = Appointment(**data.model_dump())
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return _out(appt)


@router.get("/{appointment_id}")
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Retrieve a single appointment by ID."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _out(appt)


@router.put("/{appointment_id}")
def update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update an appointment."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if data.status is not None and data.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{data.status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    if data.service_case_id is not None:
        sc = db.query(ServiceCase).filter(ServiceCase.id == data.service_case_id).first()
        if not sc:
            raise HTTPException(status_code=404, detail="Service case not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(appt, field, value)

    db.commit()
    db.refresh(appt)
    return _out(appt)


@router.delete("/{appointment_id}", status_code=204)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete an appointment by ID."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    db.delete(appt)
    db.commit()
