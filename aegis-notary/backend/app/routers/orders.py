from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_notary
from app.models import NotaryProfile, SigningOrder

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderCreate(BaseModel):
    borrower_name: str
    property_address: str
    loan_number: str = ""
    borrower_phone: str = ""
    borrower_email: str = ""
    closing_date: str = ""
    signing_type: str = "purchase"
    notes: str = ""
    fee: Optional[float] = None
    external_ref: str = ""


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    closing_date: Optional[str] = None
    fee: Optional[float] = None
    notary_id: Optional[int] = None


def _order_dict(o: SigningOrder) -> dict:
    return {
        "id": o.id,
        "loan_number": o.loan_number,
        "borrower_name": o.borrower_name,
        "borrower_phone": o.borrower_phone,
        "borrower_email": o.borrower_email,
        "property_address": o.property_address,
        "closing_date": o.closing_date,
        "signing_type": o.signing_type,
        "status": o.status,
        "notes": o.notes,
        "notary_id": o.notary_id,
        "fee": o.fee,
        "external_ref": o.external_ref,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


@router.get("")
def list_orders(
    status: Optional[str] = None,
    _: NotaryProfile = Depends(get_current_notary),
    db: Session = Depends(get_db),
):
    q = db.query(SigningOrder)
    if status:
        q = q.filter(SigningOrder.status == status)
    return [_order_dict(o) for o in q.order_by(SigningOrder.id.desc()).limit(100).all()]


@router.post("", status_code=201)
def create_order(
    body: OrderCreate,
    notary: NotaryProfile = Depends(get_current_notary),
    db: Session = Depends(get_db),
):
    order = SigningOrder(
        borrower_name=body.borrower_name,
        property_address=body.property_address,
        loan_number=body.loan_number or None,
        borrower_phone=body.borrower_phone or None,
        borrower_email=body.borrower_email or None,
        closing_date=body.closing_date or None,
        signing_type=body.signing_type,
        notes=body.notes or None,
        fee=body.fee,
        external_ref=body.external_ref or None,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _order_dict(order)


@router.get("/mine")
def my_orders(
    notary: NotaryProfile = Depends(get_current_notary),
    db: Session = Depends(get_db),
):
    orders = db.query(SigningOrder).filter(
        SigningOrder.notary_id == notary.id
    ).order_by(SigningOrder.id.desc()).limit(100).all()
    return [_order_dict(o) for o in orders]


@router.get("/{order_id}")
def get_order(
    order_id: int,
    _: NotaryProfile = Depends(get_current_notary),
    db: Session = Depends(get_db),
):
    order = db.query(SigningOrder).filter(SigningOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return _order_dict(order)


@router.patch("/{order_id}")
def update_order(
    order_id: int,
    body: OrderUpdate,
    _: NotaryProfile = Depends(get_current_notary),
    db: Session = Depends(get_db),
):
    order = db.query(SigningOrder).filter(SigningOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if body.status is not None:
        order.status = body.status
    if body.notes is not None:
        order.notes = body.notes
    if body.closing_date is not None:
        order.closing_date = body.closing_date
    if body.fee is not None:
        order.fee = body.fee
    if body.notary_id is not None:
        order.notary_id = body.notary_id
    db.commit()
    db.refresh(order)
    return _order_dict(order)
