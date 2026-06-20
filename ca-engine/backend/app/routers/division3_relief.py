import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import ReliefCase, CriminalRecord
from app.auth import get_current_user

router = APIRouter(prefix="/api/relief", tags=["Criminal Relief"])

YEAR = datetime.utcnow().year

ATTORNEY_KEYWORDS = {
    "felony", "murder", "rape", "robbery", "assault", "homicide",
    "trafficking", "violent", "federal", "active_probation", "active probation",
}


def _generate_case_number(db: Session) -> str:
    count = db.query(ReliefCase).count()
    return f"CR-{YEAR}-{count + 1:04d}"


def _needs_attorney_assessment(service_tier: str, notes: str) -> bool:
    """Simple heuristic: flag for attorney if tier is premium or notes suggest serious offenses."""
    if service_tier == "premium":
        return True
    text = (notes or "").lower()
    return any(kw in text for kw in ATTORNEY_KEYWORDS)


class ReliefCaseCreate(BaseModel):
    client_id: int
    service_tier: str = "standard"
    target_employer: str = ""
    target_landlord: str = ""
    notes: str = ""


class ReliefCaseStatusUpdate(BaseModel):
    status: str


class CriminalRecordCreate(BaseModel):
    offense_type: str
    offense_date: Optional[str] = ""
    jurisdiction: Optional[str] = ""
    court_name: Optional[str] = ""
    disposition: Optional[str] = ""
    sentence: Optional[str] = ""
    release_date: Optional[str] = ""
    probation_end: Optional[str] = ""
    rehabilitation_notes: Optional[str] = ""


@router.get("/cases", summary="List relief cases")
def list_relief_cases(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(ReliefCase)
    if client_id:
        q = q.filter(ReliefCase.client_id == client_id)
    if status:
        q = q.filter(ReliefCase.status == status)
    return q.order_by(ReliefCase.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/cases", status_code=201, summary="Create relief case")
def create_relief_case(
    payload: ReliefCaseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case_number = _generate_case_number(db)
    needs_attorney = _needs_attorney_assessment(payload.service_tier, payload.notes)
    referral_reason = (
        "Case flagged for attorney review based on service tier or offense indicators."
        if needs_attorney else None
    )
    case = ReliefCase(
        client_id=payload.client_id,
        case_number=case_number,
        service_tier=payload.service_tier,
        needs_attorney=needs_attorney,
        referral_reason=referral_reason,
        target_employer=payload.target_employer,
        target_landlord=payload.target_landlord,
        notes=payload.notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases/{case_id}", summary="Get relief case with records")
def get_relief_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(ReliefCase).filter(ReliefCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Relief case not found")
    return {
        "id": case.id,
        "client_id": case.client_id,
        "case_number": case.case_number,
        "status": case.status,
        "service_tier": case.service_tier,
        "needs_attorney": case.needs_attorney,
        "referral_reason": case.referral_reason,
        "referral_sent": case.referral_sent,
        "target_employer": case.target_employer,
        "target_landlord": case.target_landlord,
        "notes": case.notes,
        "created_at": case.created_at,
        "criminal_records": case.criminal_records,
    }


@router.patch("/cases/{case_id}/status", summary="Update relief case status")
def update_relief_case_status(
    case_id: int,
    payload: ReliefCaseStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(ReliefCase).filter(ReliefCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Relief case not found")
    case.status = payload.status
    db.commit()
    db.refresh(case)
    return case


@router.post("/cases/{case_id}/records", status_code=201, summary="Add criminal record")
def add_criminal_record(
    case_id: int,
    payload: CriminalRecordCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(ReliefCase).filter(ReliefCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Relief case not found")
    record = CriminalRecord(
        relief_case_id=case_id,
        offense_type=payload.offense_type,
        offense_date=payload.offense_date,
        jurisdiction=payload.jurisdiction,
        court_name=payload.court_name,
        disposition=payload.disposition,
        sentence=payload.sentence,
        release_date=payload.release_date,
        probation_end=payload.probation_end,
        rehabilitation_notes=payload.rehabilitation_notes,
    )
    db.add(record)

    # Re-run attorney assessment after each record added
    offense_text = f"{payload.offense_type} {payload.disposition} {payload.sentence}".lower()
    if any(kw in offense_text for kw in ATTORNEY_KEYWORDS):
        case.needs_attorney = True
        if not case.referral_reason:
            case.referral_reason = "Criminal record indicates attorney referral required."

    db.commit()
    db.refresh(record)
    return record


@router.get("/cases/{case_id}/records", summary="List records for a relief case")
def list_criminal_records(
    case_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(ReliefCase).filter(ReliefCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Relief case not found")
    return db.query(CriminalRecord).filter(
        CriminalRecord.relief_case_id == case_id
    ).order_by(CriminalRecord.created_at.desc()).all()
