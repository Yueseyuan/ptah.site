from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import NotaryLog, Client, AuditLog
from app.auth import get_current_user

router = APIRouter(prefix="/api/notary", tags=["notary"])

SC_MAX_FEE_PER_ACT = 5.0  # SC Code § 26-1-120


class NotaryLogCreate(BaseModel):
    client_id: int
    document_type: str
    num_acts: int = 1
    fee_per_act: float = 5.0
    travel_fee: float = 0.0
    service_fee: float = 0.0
    location: Optional[str] = None
    notarized_at: Optional[datetime] = None


class NotaryLogOut(BaseModel):
    id: int
    client_id: int
    document_type: str
    num_acts: int
    fee_per_act: float
    travel_fee: float
    service_fee: float
    location: Optional[str]
    notarized_at: Optional[datetime]
    total: float

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        data = {
            "id": obj.id,
            "client_id": obj.client_id,
            "document_type": obj.document_type,
            "num_acts": obj.num_acts,
            "fee_per_act": obj.fee_per_act,
            "travel_fee": obj.travel_fee,
            "service_fee": obj.service_fee,
            "location": obj.location,
            "notarized_at": obj.notarized_at,
            "total": (obj.num_acts * obj.fee_per_act) + obj.travel_fee + obj.service_fee,
        }
        return cls(**data)


@router.post("/log", response_model=NotaryLogOut, status_code=201)
def create_notary_log(
    payload: NotaryLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if payload.fee_per_act > SC_MAX_FEE_PER_ACT:
        raise HTTPException(
            status_code=422,
            detail=f"Notarial act fee cannot exceed ${SC_MAX_FEE_PER_ACT:.2f} per SC Code § 26-1-120",
        )

    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    log_entry = NotaryLog(
        client_id=payload.client_id,
        document_type=payload.document_type,
        num_acts=payload.num_acts,
        fee_per_act=payload.fee_per_act,
        travel_fee=payload.travel_fee,
        service_fee=payload.service_fee,
        location=payload.location,
        notarized_at=payload.notarized_at or datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    audit = AuditLog(
        user_id=current_user.id,
        action="create_notary_log",
        resource_type="notary_log",
        resource_id=log_entry.id,
        details=f"client={payload.client_id}, acts={payload.num_acts}",
    )
    db.add(audit)
    db.commit()

    return NotaryLogOut.from_orm(log_entry)


@router.get("/log", response_model=List[NotaryLogOut])
def list_notary_logs(
    client_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(NotaryLog)
    if client_id:
        q = q.filter(NotaryLog.client_id == client_id)
    logs = q.order_by(NotaryLog.notarized_at.desc()).offset(skip).limit(limit).all()
    return [NotaryLogOut.from_orm(l) for l in logs]


@router.get("/log/{log_id}", response_model=NotaryLogOut)
def get_notary_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    entry = db.query(NotaryLog).filter(NotaryLog.id == log_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Notary log not found")
    return NotaryLogOut.from_orm(entry)


@router.get("/log/{log_id}/invoice")
def generate_notary_invoice(
    log_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate and download a PDF invoice for a notary log entry."""
    from fastapi.responses import FileResponse
    from app.services.pdf_generator import generate_pdf

    entry = db.query(NotaryLog).filter(NotaryLog.id == log_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Notary log not found")

    client = db.query(Client).filter(Client.id == entry.client_id).first()

    pdf_path = generate_pdf("notary_invoice", {
        "client_id": entry.client_id,
        "first_name": client.first_name if client else "",
        "last_name": client.last_name if client else "",
        "address": client.address if client else "",
        "city": client.city if client else "",
        "state": client.state if client else "SC",
        "zip_code": client.zip_code if client else "",
        "num_acts": entry.num_acts,
        "fee_per_act": entry.fee_per_act,
        "travel_fee": entry.travel_fee,
        "service_fee": entry.service_fee,
        "invoice_number": f"NTR-{entry.id:04d}",
    })

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"notary_invoice_{entry.id}.pdf",
    )
