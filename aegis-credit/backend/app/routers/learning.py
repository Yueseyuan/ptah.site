from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import LearningEntry

router = APIRouter(prefix="/api/learning", tags=["learning"])


class LearningCreate(BaseModel):
    bureau: Optional[str] = None
    creditor_name: Optional[str] = None
    tactic_used: str
    fcra_basis: Optional[str] = None
    outcome: str  # success, partial, failure
    notes: Optional[str] = None


def _out(e: LearningEntry) -> dict:
    return {
        "id": e.id,
        "bureau": e.bureau,
        "creditor_name": e.creditor_name,
        "tactic_used": e.tactic_used,
        "fcra_basis": e.fcra_basis,
        "outcome": e.outcome,
        "notes": e.notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/")
def list_entries(bureau: Optional[str] = None, outcome: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(LearningEntry)
    if bureau:
        q = q.filter(LearningEntry.bureau == bureau)
    if outcome:
        q = q.filter(LearningEntry.outcome == outcome)
    return [_out(e) for e in q.order_by(LearningEntry.created_at.desc()).all()]


@router.post("/", status_code=201)
def create_entry(data: LearningCreate, db: Session = Depends(get_db)):
    entry = LearningEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _out(entry)


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    e = db.query(LearningEntry).filter(LearningEntry.id == entry_id).first()
    if not e:
        raise HTTPException(404, "Entry not found")
    db.delete(e)
    db.commit()
