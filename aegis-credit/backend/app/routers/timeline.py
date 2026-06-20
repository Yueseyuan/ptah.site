from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import TimelineEvent, Tradeline, Finding

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


class EventCreate(BaseModel):
    case_id: int
    event_type: str
    event_date: str
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    related_finding_id: Optional[int] = None


def _out(e: TimelineEvent) -> dict:
    return {
        "id": e.id,
        "case_id": e.case_id,
        "event_type": e.event_type,
        "event_date": e.event_date,
        "title": e.title,
        "description": e.description,
        "source": e.source,
        "related_finding_id": e.related_finding_id,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/case/{case_id}")
def list_events(case_id: int, db: Session = Depends(get_db)):
    events = db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).order_by(TimelineEvent.event_date).all()
    return [_out(e) for e in events]


@router.post("/", status_code=201)
def create_event(data: EventCreate, db: Session = Depends(get_db)):
    event = TimelineEvent(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return _out(event)


@router.post("/case/{case_id}/build")
def build_timeline(case_id: int, db: Session = Depends(get_db)):
    """Auto-build timeline from tradelines and findings."""
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    findings = db.query(Finding).filter(Finding.case_id == case_id).all()

    db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id, TimelineEvent.source == "auto").delete()

    new_events = []
    for tl in tradelines:
        if tl.open_date:
            e = TimelineEvent(
                case_id=case_id,
                event_type="account_opened",
                event_date=tl.open_date,
                title=f"Account Opened — {tl.creditor_name}",
                description=f"Bureau: {tl.bureau} | Type: {tl.account_type}",
                source="auto",
            )
            db.add(e)
            new_events.append(e)
        if tl.derogatory and tl.close_date:
            e = TimelineEvent(
                case_id=case_id,
                event_type="derogatory_reported",
                event_date=tl.close_date,
                title=f"Derogatory Mark — {tl.creditor_name}",
                description=f"Status: {tl.payment_status} | Bureau: {tl.bureau}",
                source="auto",
            )
            db.add(e)
            new_events.append(e)

    db.commit()
    return {"events_created": len(new_events)}


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    e = db.query(TimelineEvent).filter(TimelineEvent.id == event_id).first()
    if not e:
        raise HTTPException(404, "Event not found")
    db.delete(e)
    db.commit()
