from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Outcome

router = APIRouter(prefix="/api/outcomes", tags=["outcomes"])


class OutcomeCreate(BaseModel):
    case_id: int
    tradeline_id: Optional[int] = None
    outcome_type: str
    description: Optional[str] = None
    bureau: Optional[str] = None
    achieved_date: Optional[str] = None
    verified: bool = False
    score_before: Optional[int] = None
    score_after: Optional[int] = None


class OutcomeUpdate(BaseModel):
    verified: Optional[bool] = None
    description: Optional[str] = None
    score_before: Optional[int] = None
    score_after: Optional[int] = None


def _out(o: Outcome) -> dict:
    return {
        "id": o.id,
        "case_id": o.case_id,
        "tradeline_id": o.tradeline_id,
        "outcome_type": o.outcome_type,
        "description": o.description,
        "bureau": o.bureau,
        "achieved_date": o.achieved_date,
        "verified": o.verified,
        "score_before": o.score_before,
        "score_after": o.score_after,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.get("/case/{case_id}")
def list_outcomes(case_id: int, db: Session = Depends(get_db)):
    return [_out(o) for o in db.query(Outcome).filter(Outcome.case_id == case_id).order_by(Outcome.created_at.desc()).all()]


@router.post("/", status_code=201)
def create_outcome(data: OutcomeCreate, db: Session = Depends(get_db)):
    o = Outcome(**data.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return _out(o)


@router.patch("/{outcome_id}")
def update_outcome(outcome_id: int, data: OutcomeUpdate, db: Session = Depends(get_db)):
    o = db.query(Outcome).filter(Outcome.id == outcome_id).first()
    if not o:
        raise HTTPException(404, "Outcome not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return _out(o)


@router.delete("/{outcome_id}", status_code=204)
def delete_outcome(outcome_id: int, db: Session = Depends(get_db)):
    o = db.query(Outcome).filter(Outcome.id == outcome_id).first()
    if not o:
        raise HTTPException(404, "Outcome not found")
    db.delete(o)
    db.commit()
