from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Tradeline

router = APIRouter(prefix="/api/tradelines", tags=["tradelines"])


class TradelineCreate(BaseModel):
    case_id: int
    report_id: Optional[int] = None
    bureau: str
    creditor_name: str
    account_number_last4: Optional[str] = None
    account_type: str = "other"
    open_date: Optional[str] = None
    close_date: Optional[str] = None
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    payment_status: str = "unknown"
    derogatory: bool = False
    # Metro 2 / extended fields
    high_balance: Optional[float] = None
    past_due_amount: Optional[float] = None
    scheduled_payment_amount: Optional[float] = None
    payment_rating: Optional[str] = None
    compliance_condition_code: Optional[str] = None
    consumer_information_indicator: Optional[str] = None
    dofd: Optional[str] = None
    date_reported: Optional[str] = None
    remarks: Optional[str] = None
    raw_source_text: Optional[str] = None


class TradelineUpdate(BaseModel):
    creditor_name: Optional[str] = None
    account_type: Optional[str] = None
    payment_status: Optional[str] = None
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    derogatory: Optional[bool] = None
    dispute_status: Optional[str] = None


def _out(t: Tradeline) -> dict:
    return {
        "id": t.id,
        "case_id": t.case_id,
        "report_id": t.report_id,
        "bureau": t.bureau,
        "creditor_name": t.creditor_name,
        "account_number_last4": t.account_number_last4,
        "account_type": t.account_type,
        "open_date": t.open_date,
        "close_date": t.close_date,
        "balance": t.balance,
        "credit_limit": t.credit_limit,
        "payment_status": t.payment_status,
        "payment_history": t.payment_history,
        "derogatory": t.derogatory,
        "dispute_status": t.dispute_status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.post("/manual", status_code=201)
def create_tradeline_manual(data: TradelineCreate, db: Session = Depends(get_db)):
    t = Tradeline(**data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return _out(t)


@router.delete("/{tradeline_id}", status_code=204)
def delete_tradeline(tradeline_id: int, db: Session = Depends(get_db)):
    t = db.query(Tradeline).filter(Tradeline.id == tradeline_id).first()
    if not t:
        raise HTTPException(404, "Tradeline not found")
    db.delete(t)
    db.commit()


@router.get("/case/{case_id}")
def list_tradelines(case_id: int, bureau: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Tradeline).filter(Tradeline.case_id == case_id)
    if bureau:
        q = q.filter(Tradeline.bureau == bureau)
    return [_out(t) for t in q.order_by(Tradeline.bureau, Tradeline.creditor_name).all()]


@router.get("/{tradeline_id}")
def get_tradeline(tradeline_id: int, db: Session = Depends(get_db)):
    t = db.query(Tradeline).filter(Tradeline.id == tradeline_id).first()
    if not t:
        raise HTTPException(404, "Tradeline not found")
    return _out(t)


@router.patch("/{tradeline_id}")
def update_tradeline(tradeline_id: int, data: TradelineUpdate, db: Session = Depends(get_db)):
    t = db.query(Tradeline).filter(Tradeline.id == tradeline_id).first()
    if not t:
        raise HTTPException(404, "Tradeline not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return _out(t)
