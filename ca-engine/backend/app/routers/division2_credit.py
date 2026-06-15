import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import CreditCase, DisputeItem
from app.auth import get_current_user

router = APIRouter(prefix="/api/credit", tags=["Credit Restoration"])

YEAR = datetime.utcnow().year


def _generate_case_number(db: Session) -> str:
    count = db.query(CreditCase).count()
    return f"CC-{YEAR}-{count + 1:04d}"


class CreditCaseCreate(BaseModel):
    client_id: int
    starting_score_eq: Optional[int] = None
    starting_score_ex: Optional[int] = None
    starting_score_tu: Optional[int] = None
    notes: Optional[str] = ""


class CreditCaseStatusUpdate(BaseModel):
    status: str


class DisputeItemCreate(BaseModel):
    bureau: str
    creditor_name: str
    account_last4: Optional[str] = ""
    item_type: str
    dispute_reason: str
    fcra_basis: Optional[str] = ""
    priority: int = 2


class DisputeItemUpdate(BaseModel):
    status: Optional[str] = None
    resolution: Optional[str] = None
    letter_sent_at: Optional[datetime] = None
    response_due_at: Optional[datetime] = None
    bureau_response_at: Optional[datetime] = None
    priority: Optional[int] = None


@router.get("/cases", summary="List credit cases")
def list_credit_cases(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(CreditCase)
    if client_id:
        q = q.filter(CreditCase.client_id == client_id)
    if status:
        q = q.filter(CreditCase.status == status)
    return q.order_by(CreditCase.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/cases", status_code=201, summary="Create credit case")
def create_credit_case(
    payload: CreditCaseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case_number = _generate_case_number(db)
    case = CreditCase(
        client_id=payload.client_id,
        case_number=case_number,
        starting_score_eq=payload.starting_score_eq,
        starting_score_ex=payload.starting_score_ex,
        starting_score_tu=payload.starting_score_tu,
        current_score_eq=payload.starting_score_eq,
        current_score_ex=payload.starting_score_ex,
        current_score_tu=payload.starting_score_tu,
        notes=payload.notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases/{case_id}", summary="Get credit case with disputes")
def get_credit_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(CreditCase).filter(CreditCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Credit case not found")
    return {
        "id": case.id,
        "client_id": case.client_id,
        "case_number": case.case_number,
        "status": case.status,
        "starting_score_eq": case.starting_score_eq,
        "starting_score_ex": case.starting_score_ex,
        "starting_score_tu": case.starting_score_tu,
        "current_score_eq": case.current_score_eq,
        "current_score_ex": case.current_score_ex,
        "current_score_tu": case.current_score_tu,
        "total_negative_items": case.total_negative_items,
        "items_removed": case.items_removed,
        "items_in_dispute": case.items_in_dispute,
        "first_work_completed": case.first_work_completed,
        "notes": case.notes,
        "created_at": case.created_at,
        "dispute_items": case.dispute_items,
    }


@router.patch("/cases/{case_id}/status", summary="Update credit case status")
def update_credit_case_status(
    case_id: int,
    payload: CreditCaseStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(CreditCase).filter(CreditCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Credit case not found")
    case.status = payload.status
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases/{case_id}/disputes", summary="List dispute items for a case")
def list_dispute_items(
    case_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(CreditCase).filter(CreditCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Credit case not found")
    return db.query(DisputeItem).filter(
        DisputeItem.credit_case_id == case_id
    ).order_by(DisputeItem.priority.asc(), DisputeItem.created_at.desc()).all()


@router.post("/cases/{case_id}/disputes", status_code=201, summary="Add dispute item")
def add_dispute_item(
    case_id: int,
    payload: DisputeItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(CreditCase).filter(CreditCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Credit case not found")
    item = DisputeItem(
        credit_case_id=case_id,
        bureau=payload.bureau,
        creditor_name=payload.creditor_name,
        account_last4=payload.account_last4,
        item_type=payload.item_type,
        dispute_reason=payload.dispute_reason,
        fcra_basis=payload.fcra_basis,
        priority=payload.priority,
    )
    db.add(item)
    case.total_negative_items = (case.total_negative_items or 0) + 1
    case.items_in_dispute = (case.items_in_dispute or 0) + 1
    db.commit()
    db.refresh(item)
    return item


@router.patch("/disputes/{item_id}", summary="Update dispute item")
def update_dispute_item(
    item_id: int,
    payload: DisputeItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(DisputeItem).filter(DisputeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Dispute item not found")

    old_status = item.status

    if payload.status is not None:
        item.status = payload.status
    if payload.resolution is not None:
        item.resolution = payload.resolution
    if payload.letter_sent_at is not None:
        item.letter_sent_at = payload.letter_sent_at
    if payload.response_due_at is not None:
        item.response_due_at = payload.response_due_at
    if payload.bureau_response_at is not None:
        item.bureau_response_at = payload.bureau_response_at
    if payload.priority is not None:
        item.priority = payload.priority

    if payload.status in ("removed", "resolved") and old_status not in ("removed", "resolved"):
        case = db.query(CreditCase).filter(CreditCase.id == item.credit_case_id).first()
        if case:
            case.items_removed = (case.items_removed or 0) + 1
            case.items_in_dispute = max(0, (case.items_in_dispute or 0) - 1)

    db.commit()
    db.refresh(item)
    return item
