import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Case, Client, AuditLog
from app.auth import get_current_user

router = APIRouter(prefix="/api/cases", tags=["cases"])

VALID_DIVISIONS = {"notary", "credit", "reentry", "document_prep", "asset_recovery", "business"}
VALID_STATUSES = {"active", "documents_ready", "pending_signature", "signed", "archived", "on_hold", "closed"}


class CaseCreate(BaseModel):
    client_id: int
    division: str
    intake_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    intake_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class CaseOut(BaseModel):
    id: int
    client_id: int
    division: str
    status: str
    intake_data: Optional[str]
    ai_analysis: Optional[str]
    notes: Optional[str]
    assigned_to: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[CaseOut])
def list_cases(
    client_id: Optional[int] = Query(None),
    division: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Case)
    if client_id:
        q = q.filter(Case.client_id == client_id)
    if division:
        q = q.filter(Case.division == division)
    if status:
        q = q.filter(Case.status == status)
    return q.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=CaseOut, status_code=201)
def create_case(
    payload: CaseCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if payload.division not in VALID_DIVISIONS:
        raise HTTPException(status_code=422, detail=f"Invalid division. Must be one of: {VALID_DIVISIONS}")

    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    case = Case(
        client_id=payload.client_id,
        division=payload.division,
        intake_data=json.dumps(payload.intake_data or {}),
        notes=payload.notes,
        assigned_to=payload.assigned_to,
        status="active",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    log = AuditLog(
        user_id=current_user.id,
        action="create_case",
        resource_type="case",
        resource_id=case.id,
        details=f"division={payload.division}",
    )
    db.add(log)
    db.commit()

    # Trigger full intake automation in background
    background_tasks.add_task(_run_intake_automation, case.id)

    return case


def _run_intake_automation(case_id: int):
    from app.services.automation import on_intake_complete
    try:
        on_intake_complete(case_id)
    except Exception:
        pass


@router.get("/{case_id}", response_model=CaseOut)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    payload: CaseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.services.automation import can_transition

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if payload.status and payload.status != case.status:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Invalid status: {payload.status}")
        if not can_transition(case.status, payload.status):
            raise HTTPException(
                status_code=422,
                detail=f"Cannot transition from '{case.status}' to '{payload.status}'",
            )
        case.status = payload.status

    if payload.intake_data is not None:
        existing = json.loads(case.intake_data or "{}")
        existing.update(payload.intake_data)
        case.intake_data = json.dumps(existing)

    if payload.notes is not None:
        case.notes = payload.notes

    if payload.assigned_to is not None:
        case.assigned_to = payload.assigned_to

    db.commit()
    db.refresh(case)

    log = AuditLog(
        user_id=current_user.id,
        action="update_case",
        resource_type="case",
        resource_id=case_id,
        details=str(payload.model_dump(exclude_unset=True)),
    )
    db.add(log)
    db.commit()

    return case


@router.post("/{case_id}/analyze", response_model=dict)
def analyze_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Re-run AI analysis on a case."""
    from app.services.ai_service import generate_intake_summary

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    intake_data = json.loads(case.intake_data or "{}")
    summary = generate_intake_summary(case.division, intake_data)
    case.ai_analysis = json.dumps(summary)
    db.commit()

    return summary


@router.get("/{case_id}/intake", response_model=dict)
def get_intake_data(
    case_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return json.loads(case.intake_data or "{}")
