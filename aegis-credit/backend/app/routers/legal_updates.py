"""Legal Update Approval Workflow router."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import LegalUpdate, FederalLaw, AgencyGuidance, StateLaw, CaseLaw

router = APIRouter(prefix="/api/legal-updates", tags=["legal_updates"])


def _out(u: LegalUpdate) -> dict:
    return {
        "id": u.id,
        "update_type": u.update_type,
        "title": u.title,
        "source_url": u.source_url,
        "summary": u.summary,
        "proposed_changes": u.proposed_changes,
        "status": u.status,
        "submitted_by": u.submitted_by,
        "reviewed_by": u.reviewed_by,
        "reviewed_at": u.reviewed_at.isoformat() if u.reviewed_at else None,
        "review_notes": u.review_notes,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


class LegalUpdateCreate(BaseModel):
    update_type: str
    title: str
    source_url: Optional[str] = None
    summary: Optional[str] = None
    proposed_changes: Optional[str] = None
    submitted_by: Optional[str] = None


class RejectRequest(BaseModel):
    notes: Optional[str] = None


@router.get("/")
def list_legal_updates(db: Session = Depends(get_db)):
    updates = db.query(LegalUpdate).order_by(LegalUpdate.id.desc()).all()
    return [_out(u) for u in updates]


@router.post("/", status_code=201)
def submit_legal_update(data: LegalUpdateCreate, db: Session = Depends(get_db)):
    update = LegalUpdate(**data.model_dump())
    db.add(update)
    db.commit()
    db.refresh(update)
    return _out(update)


@router.get("/{update_id}")
def get_legal_update(update_id: int, db: Session = Depends(get_db)):
    update = db.query(LegalUpdate).filter(LegalUpdate.id == update_id).first()
    if not update:
        raise HTTPException(404, "Update not found")
    return _out(update)


@router.post("/{update_id}/approve")
def approve_legal_update(update_id: int, db: Session = Depends(get_db)):
    update = db.query(LegalUpdate).filter(LegalUpdate.id == update_id).first()
    if not update:
        raise HTTPException(404, "Update not found")
    if update.status != "pending":
        raise HTTPException(400, f"Update is already {update.status}")

    import json

    # Parse proposed_changes and create the appropriate record
    try:
        changes = json.loads(update.proposed_changes or "{}")
    except Exception:
        changes = {}

    if update.update_type == "federal":
        record = FederalLaw(**{k: v for k, v in changes.items() if hasattr(FederalLaw, k)})
        db.add(record)
    elif update.update_type == "guidance":
        record = AgencyGuidance(**{k: v for k, v in changes.items() if hasattr(AgencyGuidance, k)})
        db.add(record)
    elif update.update_type == "state":
        record = StateLaw(**{k: v for k, v in changes.items() if hasattr(StateLaw, k)})
        db.add(record)
    elif update.update_type == "case_law":
        record = CaseLaw(**{k: v for k, v in changes.items() if hasattr(CaseLaw, k)})
        db.add(record)

    update.status = "approved"
    update.reviewed_by = "system"
    update.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(update)
    return _out(update)


@router.post("/{update_id}/reject")
def reject_legal_update(update_id: int, data: RejectRequest = None, db: Session = Depends(get_db)):
    update = db.query(LegalUpdate).filter(LegalUpdate.id == update_id).first()
    if not update:
        raise HTTPException(404, "Update not found")
    if update.status != "pending":
        raise HTTPException(400, f"Update is already {update.status}")

    update.status = "rejected"
    update.reviewed_by = "system"
    update.reviewed_at = datetime.utcnow()
    if data and data.notes:
        update.review_notes = data.notes
    db.commit()
    db.refresh(update)
    return _out(update)
