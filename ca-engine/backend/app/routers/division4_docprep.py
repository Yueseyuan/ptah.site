import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import DocPrepOrder, HKPInstrument
from app.auth import get_current_user

router = APIRouter(prefix="/api/docprep", tags=["Document Prep"])

YEAR = datetime.utcnow().year


def _generate_order_number(db: Session) -> str:
    count = db.query(DocPrepOrder).count()
    return f"DP-{YEAR}-{count + 1:04d}"


class DocPrepOrderCreate(BaseModel):
    client_id: int
    doc_category: str = "general"
    doc_types: List[str] = []
    intake_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = ""


class DocPrepOrderStatusUpdate(BaseModel):
    status: str


class HKPInstrumentCreate(BaseModel):
    instrument_type: str
    member_name: str
    member_address: str
    instrument_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    term_months: Optional[int] = None
    maturity_date: Optional[str] = ""
    collateral_description: Optional[str] = ""
    profit_sharing_terms: Optional[str] = ""
    inheritance_transfer: bool = False
    beneficiary_name: Optional[str] = ""


@router.get("/orders", summary="List doc prep orders")
def list_orders(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(DocPrepOrder)
    if client_id:
        q = q.filter(DocPrepOrder.client_id == client_id)
    if status:
        q = q.filter(DocPrepOrder.status == status)
    return q.order_by(DocPrepOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/orders", status_code=201, summary="Create doc prep order")
def create_order(
    payload: DocPrepOrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order_number = _generate_order_number(db)
    total_fee = max(50.0, len(payload.doc_types) * 35.0)
    order = DocPrepOrder(
        client_id=payload.client_id,
        order_number=order_number,
        doc_category=payload.doc_category,
        doc_types=json.dumps(payload.doc_types),
        intake_data=json.dumps(payload.intake_data or {}),
        total_fee=total_fee,
        notes=payload.notes,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders/{order_id}", summary="Get doc prep order")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = db.query(DocPrepOrder).filter(DocPrepOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": order.id,
        "client_id": order.client_id,
        "order_number": order.order_number,
        "status": order.status,
        "doc_category": order.doc_category,
        "doc_types": json.loads(order.doc_types or "[]"),
        "intake_data": json.loads(order.intake_data or "{}"),
        "total_fee": order.total_fee,
        "notes": order.notes,
        "created_at": order.created_at,
        "hkp_instruments": order.hkp_instruments,
    }


@router.patch("/orders/{order_id}/status", summary="Update order status")
def update_order_status(
    order_id: int,
    payload: DocPrepOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = db.query(DocPrepOrder).filter(DocPrepOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/hkp", status_code=201, summary="Create HKP instrument")
def create_hkp_instrument(
    order_id: int,
    payload: HKPInstrumentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = db.query(DocPrepOrder).filter(DocPrepOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    signatory_title = "Chief Loan Officer" if payload.instrument_type == "loc" else "Netjer-Tepi"

    instrument = HKPInstrument(
        order_id=order_id,
        instrument_type=payload.instrument_type,
        member_name=payload.member_name,
        member_address=payload.member_address,
        instrument_amount=payload.instrument_amount,
        interest_rate=payload.interest_rate,
        term_months=payload.term_months,
        maturity_date=payload.maturity_date,
        collateral_description=payload.collateral_description,
        profit_sharing_terms=payload.profit_sharing_terms,
        inheritance_transfer=payload.inheritance_transfer,
        beneficiary_name=payload.beneficiary_name,
        signatory_title=signatory_title,
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    return instrument
