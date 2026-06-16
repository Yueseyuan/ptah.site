from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Inquiry
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/inquiries", tags=["inquiries"])


class InquiryCreate(BaseModel):
    case_id: int
    report_id: Optional[int] = None
    bureau: str
    inquiry_type: str = "hard"
    subscriber_name: str
    inquiry_date: Optional[str] = None
    purpose: Optional[str] = None


def _out(inq: Inquiry) -> dict:
    return {
        "id": inq.id,
        "case_id": inq.case_id,
        "report_id": inq.report_id,
        "bureau": inq.bureau,
        "inquiry_type": inq.inquiry_type,
        "subscriber_name": inq.subscriber_name,
        "inquiry_date": inq.inquiry_date,
        "purpose": inq.purpose,
        "created_at": inq.created_at.isoformat() if inq.created_at else None,
    }


@router.get("/case/{case_id}")
def list_inquiries(
    case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return [
        _out(i)
        for i in db.query(Inquiry)
        .filter(Inquiry.case_id == case_id)
        .order_by(Inquiry.inquiry_date.desc())
        .all()
    ]


@router.post("/", status_code=201)
def create_inquiry(data: InquiryCreate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    inq = Inquiry(**data.model_dump())
    db.add(inq)
    db.commit()
    db.refresh(inq)
    return _out(inq)


@router.delete("/{inquiry_id}", status_code=204)
def delete_inquiry(inquiry_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    inq = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inq:
        raise HTTPException(404, "Inquiry not found")
    db.delete(inq)
    db.commit()
