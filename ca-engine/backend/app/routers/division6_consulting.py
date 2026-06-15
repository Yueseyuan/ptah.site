import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import ConsultingEngagement, ConsultingDocument
from app.auth import get_current_user

router = APIRouter(prefix="/api/consulting", tags=["Business Consulting"])

YEAR = datetime.utcnow().year
HOURLY_RATE = 150.0
PACKAGE_RATE = 500.0


def _generate_engagement_number(db: Session) -> str:
    count = db.query(ConsultingEngagement).count()
    return f"BC-{YEAR}-{count + 1:04d}"


class EngagementCreate(BaseModel):
    client_id: int
    engagement_type: str = "hourly"
    business_stage: Optional[str] = ""
    business_type: Optional[str] = ""
    goals: Optional[List[str]] = []
    session_datetime: Optional[datetime] = None
    notes: Optional[str] = ""


class EngagementStatusUpdate(BaseModel):
    status: str


class SessionNotesUpdate(BaseModel):
    session_notes: str
    action_items: Optional[List[str]] = []
    recommended_services: Optional[List[str]] = []


class ConsultingDocCreate(BaseModel):
    doc_type: str
    ai_generated: bool = False


@router.get("/engagements", summary="List consulting engagements")
def list_engagements(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(ConsultingEngagement)
    if client_id:
        q = q.filter(ConsultingEngagement.client_id == client_id)
    if status:
        q = q.filter(ConsultingEngagement.status == status)
    return q.order_by(ConsultingEngagement.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/engagements", status_code=201, summary="Create consulting engagement")
def create_engagement(
    payload: EngagementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    engagement_number = _generate_engagement_number(db)
    total_fee = PACKAGE_RATE if payload.engagement_type == "package" else HOURLY_RATE
    engagement = ConsultingEngagement(
        client_id=payload.client_id,
        engagement_number=engagement_number,
        engagement_type=payload.engagement_type,
        business_stage=payload.business_stage,
        business_type=payload.business_type,
        goals=json.dumps(payload.goals or []),
        session_datetime=payload.session_datetime,
        action_items=json.dumps([]),
        recommended_services=json.dumps([]),
        total_fee=total_fee,
        notes=payload.notes,
    )
    db.add(engagement)
    db.commit()
    db.refresh(engagement)
    return engagement


@router.get("/engagements/{engagement_id}", summary="Get consulting engagement")
def get_engagement(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    e = db.query(ConsultingEngagement).filter(ConsultingEngagement.id == engagement_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return {
        "id": e.id,
        "client_id": e.client_id,
        "engagement_number": e.engagement_number,
        "status": e.status,
        "engagement_type": e.engagement_type,
        "business_stage": e.business_stage,
        "business_type": e.business_type,
        "goals": json.loads(e.goals or "[]"),
        "session_datetime": e.session_datetime,
        "session_notes": e.session_notes,
        "action_items": json.loads(e.action_items or "[]"),
        "recommended_services": json.loads(e.recommended_services or "[]"),
        "total_fee": e.total_fee,
        "notes": e.notes,
        "created_at": e.created_at,
        "consulting_documents": e.consulting_documents,
    }


@router.patch("/engagements/{engagement_id}/status", summary="Update engagement status")
def update_engagement_status(
    engagement_id: int,
    payload: EngagementStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    e = db.query(ConsultingEngagement).filter(ConsultingEngagement.id == engagement_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Engagement not found")
    e.status = payload.status
    db.commit()
    db.refresh(e)
    return e


@router.patch("/engagements/{engagement_id}/notes", summary="Update session notes")
def update_session_notes(
    engagement_id: int,
    payload: SessionNotesUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    e = db.query(ConsultingEngagement).filter(ConsultingEngagement.id == engagement_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Engagement not found")
    e.session_notes = payload.session_notes
    e.action_items = json.dumps(payload.action_items or [])
    e.recommended_services = json.dumps(payload.recommended_services or [])
    e.status = "completed"
    db.commit()
    db.refresh(e)
    return e


@router.get("/engagements/{engagement_id}/documents", summary="List consulting docs")
def list_consulting_docs(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    e = db.query(ConsultingEngagement).filter(ConsultingEngagement.id == engagement_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return db.query(ConsultingDocument).filter(
        ConsultingDocument.engagement_id == engagement_id
    ).order_by(ConsultingDocument.created_at.desc()).all()
