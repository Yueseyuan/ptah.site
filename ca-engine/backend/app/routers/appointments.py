from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Appointment, Client, Case, AuditLog
from app.auth import get_current_user

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

VALID_TYPES = {"phone", "in_person", "virtual"}
VALID_STATUSES = {"scheduled", "completed", "cancelled", "no_show"}


class AppointmentCreate(BaseModel):
    client_id: int
    case_id: Optional[int] = None
    division: str
    appointment_type: str
    scheduled_at: datetime
    duration_minutes: Optional[int] = 30
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    appointment_type: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AppointmentOut(BaseModel):
    id: int
    client_id: int
    case_id: Optional[int]
    division: str
    appointment_type: str
    scheduled_at: Optional[datetime]
    duration_minutes: int
    status: str
    notes: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AppointmentOut])
def list_appointments(
    client_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Appointment)
    if client_id:
        q = q.filter(Appointment.client_id == client_id)
    if date_from:
        q = q.filter(Appointment.scheduled_at >= date_from)
    if date_to:
        q = q.filter(Appointment.scheduled_at <= date_to)
    if status:
        q = q.filter(Appointment.status == status)
    return q.order_by(Appointment.scheduled_at).offset(skip).limit(limit).all()


@router.post("/", response_model=AppointmentOut, status_code=201)
def create_appointment(
    payload: AppointmentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if payload.appointment_type not in VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid type. Must be one of: {VALID_TYPES}")

    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if payload.case_id:
        case = db.query(Case).filter(Case.id == payload.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

    apt = Appointment(**payload.model_dump())
    db.add(apt)
    db.commit()
    db.refresh(apt)

    log = AuditLog(
        user_id=current_user.id,
        action="create_appointment",
        resource_type="appointment",
        resource_id=apt.id,
        details=f"client={payload.client_id}, type={payload.appointment_type}",
    )
    db.add(log)
    db.commit()

    background_tasks.add_task(_send_confirmation, apt.id)

    return apt


def _send_confirmation(apt_id: int):
    from app.services.automation import on_appointment_scheduled
    try:
        on_appointment_scheduled(apt_id)
    except Exception:
        pass


@router.get("/{apt_id}", response_model=AppointmentOut)
def get_appointment(
    apt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return apt


@router.patch("/{apt_id}", response_model=AppointmentOut)
def update_appointment(
    apt_id: int,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    updates = payload.model_dump(exclude_unset=True)
    if "appointment_type" in updates and updates["appointment_type"] not in VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid type: {updates['appointment_type']}")
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {updates['status']}")

    for key, val in updates.items():
        setattr(apt, key, val)

    db.commit()
    db.refresh(apt)

    log = AuditLog(
        user_id=current_user.id,
        action="update_appointment",
        resource_type="appointment",
        resource_id=apt_id,
        details=str(list(updates.keys())),
    )
    db.add(log)
    db.commit()

    return apt


@router.delete("/{apt_id}", status_code=204)
def cancel_appointment(
    apt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    apt.status = "cancelled"
    db.commit()

    log = AuditLog(
        user_id=current_user.id,
        action="cancel_appointment",
        resource_type="appointment",
        resource_id=apt_id,
    )
    db.add(log)
    db.commit()
