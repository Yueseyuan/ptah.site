from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import CourtRecord

router = APIRouter(prefix="/api/court-records", tags=["court_records"])


class CourtRecordCreate(BaseModel):
    client_id: int
    case_id: Optional[int] = None
    record_type: str = "criminal"
    court_name: Optional[str] = None
    jurisdiction: Optional[str] = None
    docket_number: Optional[str] = None
    offense_date: Optional[str] = None
    disposition: Optional[str] = None
    disposition_date: Optional[str] = None
    expungement_eligible: bool = False
    notes: Optional[str] = None


def _out(r: CourtRecord) -> dict:
    return {
        "id": r.id,
        "client_id": r.client_id,
        "case_id": r.case_id,
        "record_type": r.record_type,
        "court_name": r.court_name,
        "jurisdiction": r.jurisdiction,
        "docket_number": r.docket_number,
        "offense_date": r.offense_date,
        "disposition": r.disposition,
        "disposition_date": r.disposition_date,
        "expungement_eligible": r.expungement_eligible,
        "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/case/{case_id}")
def list_by_case(case_id: int, db: Session = Depends(get_db)):
    return [_out(r) for r in db.query(CourtRecord).filter(CourtRecord.case_id == case_id).all()]


@router.get("/client/{client_id}")
def list_by_client(client_id: int, db: Session = Depends(get_db)):
    return [_out(r) for r in db.query(CourtRecord).filter(CourtRecord.client_id == client_id).all()]


@router.post("/", status_code=201)
def create_record(data: CourtRecordCreate, db: Session = Depends(get_db)):
    record = CourtRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return _out(record)


@router.patch("/{record_id}")
def update_record(record_id: int, data: CourtRecordCreate, db: Session = Depends(get_db)):
    r = db.query(CourtRecord).filter(CourtRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return _out(r)


@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    r = db.query(CourtRecord).filter(CourtRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Record not found")
    db.delete(r)
    db.commit()
