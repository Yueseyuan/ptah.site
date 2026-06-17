import random
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import AegisCase

router = APIRouter(prefix="/api/cases", tags=["cases"])


def gen_case_number() -> str:
    suffix = "".join(random.choices(string.digits, k=6))
    return f"AEG-{suffix}"


class CaseCreate(BaseModel):
    client_id: int
    goal: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    goal: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


def _out(c: AegisCase) -> dict:
    return {
        "id": c.id,
        "client_id": c.client_id,
        "case_number": c.case_number,
        "status": c.status,
        "goal": c.goal,
        "notes": c.notes,
        "assigned_to": c.assigned_to,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("/")
def list_cases(db: Session = Depends(get_db)):
    return [_out(c) for c in db.query(AegisCase).order_by(AegisCase.id.desc()).all()]


@router.post("/", status_code=201)
def create_case(data: CaseCreate, db: Session = Depends(get_db)):
    case = AegisCase(**data.model_dump(), case_number=gen_case_number())
    db.add(case)
    db.commit()
    db.refresh(case)
    return _out(case)


@router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    return _out(case)


@router.patch("/{case_id}")
def update_case(case_id: int, data: CaseUpdate, db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(case, k, v)
    db.commit()
    db.refresh(case)
    return _out(case)


@router.get("/{case_id}/summary")
def case_summary(case_id: int, db: Session = Depends(get_db)):
    from app.models import CreditReport, Tradeline, Finding, DisputeRound, Outcome
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    reports = db.query(CreditReport).filter(CreditReport.case_id == case_id).count()
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).count()
    derogatory = db.query(Tradeline).filter(Tradeline.case_id == case_id, Tradeline.derogatory == True).count()
    findings = db.query(Finding).filter(Finding.case_id == case_id).count()
    high_findings = db.query(Finding).filter(Finding.case_id == case_id, Finding.severity == "high").count()
    rounds = db.query(DisputeRound).filter(DisputeRound.case_id == case_id).count()
    outcomes = db.query(Outcome).filter(Outcome.case_id == case_id).count()
    return {
        "case": _out(case),
        "reports_uploaded": reports,
        "tradelines_total": tradelines,
        "tradelines_derogatory": derogatory,
        "findings_total": findings,
        "findings_high": high_findings,
        "dispute_rounds": rounds,
        "outcomes": outcomes,
    }


@router.get("/{case_id}/applicable-laws")
def get_applicable_laws(case_id: int, db: Session = Depends(get_db)):
    from app.models import AegisClient, StateLaw
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    state = client.state if client else None
    if not state:
        return {"state": None, "laws": []}
    laws = db.query(StateLaw).filter(
        StateLaw.state == state,
        StateLaw.superseded == False,
    ).all()
    return {
        "state": state,
        "laws": [
            {
                "id": law.id,
                "statute": law.statute,
                "citation": law.citation,
                "topic": law.topic,
                "summary": law.summary,
                "effective_date": law.effective_date,
                "effective_as_of": getattr(law, "effective_as_of", None),
            }
            for law in laws
        ],
    }
