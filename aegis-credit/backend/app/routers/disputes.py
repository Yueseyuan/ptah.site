from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import DisputeRound, DisputeItem, Tradeline
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/disputes", tags=["disputes"])


class RoundCreate(BaseModel):
    case_id: int
    bureau: str
    round_number: int = 1
    sent_date: Optional[str] = None
    response_due_date: Optional[str] = None
    notes: Optional[str] = None


class RoundUpdate(BaseModel):
    status: Optional[str] = None
    sent_date: Optional[str] = None
    response_due_date: Optional[str] = None
    response_received_date: Optional[str] = None
    notes: Optional[str] = None


class ItemCreate(BaseModel):
    round_id: int
    tradeline_id: Optional[int] = None
    creditor_name: str
    account_number_last4: Optional[str] = None
    dispute_reason: str
    fcra_basis: Optional[str] = None


class ItemUpdate(BaseModel):
    status: Optional[str] = None
    resolution: Optional[str] = None


def _round_out(r: DisputeRound) -> dict:
    return {
        "id": r.id,
        "case_id": r.case_id,
        "round_number": r.round_number,
        "bureau": r.bureau,
        "sent_date": r.sent_date,
        "response_due_date": r.response_due_date,
        "response_received_date": r.response_received_date,
        "status": r.status,
        "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _item_out(i: DisputeItem) -> dict:
    return {
        "id": i.id,
        "round_id": i.round_id,
        "tradeline_id": i.tradeline_id,
        "creditor_name": i.creditor_name,
        "account_number_last4": i.account_number_last4,
        "dispute_reason": i.dispute_reason,
        "fcra_basis": i.fcra_basis,
        "resolution": i.resolution,
        "status": i.status,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


@router.get("/case/{case_id}")
def list_rounds(case_id: int, db: Session = Depends(get_db)):
    rounds = db.query(DisputeRound).filter(DisputeRound.case_id == case_id).order_by(DisputeRound.round_number).all()
    result = []
    for r in rounds:
        data = _round_out(r)
        data["items"] = [_item_out(i) for i in r.items]
        result.append(data)
    return result


@router.post("/rounds/", status_code=201)
def create_round(data: RoundCreate, db: Session = Depends(get_db)):
    r = DisputeRound(**data.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _round_out(r)


@router.patch("/rounds/{round_id}")
def update_round(round_id: int, data: RoundUpdate, db: Session = Depends(get_db)):
    r = db.query(DisputeRound).filter(DisputeRound.id == round_id).first()
    if not r:
        raise HTTPException(404, "Round not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return _round_out(r)


@router.post("/items/", status_code=201)
def create_item(data: ItemCreate, db: Session = Depends(get_db)):
    item = DisputeItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_out(item)


@router.patch("/items/{item_id}")
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db)):
    item = db.query(DisputeItem).filter(DisputeItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return _item_out(item)


_DISPUTE_REASON: dict[str, str] = {
    "charge_off": "Account incorrectly reported as charge-off — please verify and correct",
    "collection": "Collection account disputed — please validate debt and reporting accuracy",
    "90_days_late": "90-day late payment disputed — payment history inaccurate",
    "60_days_late": "60-day late payment disputed — payment history inaccurate",
    "30_days_late": "30-day late payment disputed — payment history inaccurate",
}

_FCRA_BASIS: dict[str, str] = {
    "charge_off": "FCRA §623 — inaccurate information",
    "collection": "FCRA §623 / §809(b) — debt validation",
    "90_days_late": "FCRA §623 — inaccurate payment history",
    "60_days_late": "FCRA §623 — inaccurate payment history",
    "30_days_late": "FCRA §623 — inaccurate payment history",
}


@router.post("/case/{case_id}/auto-generate")
def auto_generate_disputes(case_id: int, db: Session = Depends(get_db)):
    """Create dispute rounds + items from derogatory tradelines, one round per bureau."""
    derogatory = (
        db.query(Tradeline)
        .filter(Tradeline.case_id == case_id, Tradeline.derogatory == True)
        .all()
    )
    if not derogatory:
        raise HTTPException(400, "No derogatory tradelines found for this case.")

    by_bureau: dict[str, list[Tradeline]] = {}
    for tl in derogatory:
        bureau = tl.bureau or "unknown"
        by_bureau.setdefault(bureau, []).append(tl)

    created_rounds = 0
    created_items = 0
    for bureau, tradelines in by_bureau.items():
        existing_round = (
            db.query(DisputeRound)
            .filter(DisputeRound.case_id == case_id, DisputeRound.bureau == bureau, DisputeRound.round_number == 1)
            .first()
        )
        if not existing_round:
            existing_round = DisputeRound(case_id=case_id, bureau=bureau, round_number=1)
            db.add(existing_round)
            db.flush()
            created_rounds += 1

        existing_tradeline_ids = {
            i.tradeline_id for i in db.query(DisputeItem).filter(DisputeItem.round_id == existing_round.id).all()
            if i.tradeline_id is not None
        }
        for tl in tradelines:
            if tl.id in existing_tradeline_ids:
                continue
            status = tl.payment_status or ""
            item = DisputeItem(
                round_id=existing_round.id,
                tradeline_id=tl.id,
                creditor_name=tl.creditor_name,
                account_number_last4=tl.account_number_last4,
                dispute_reason=_DISPUTE_REASON.get(status, "Inaccurate or unverifiable information — please investigate and correct"),
                fcra_basis=_FCRA_BASIS.get(status, "FCRA §623 — furnisher duty to report accurately"),
            )
            db.add(item)
            created_items += 1

    db.commit()

    log_action(
        db,
        "AUTO_GENERATE",
        "dispute",
        resource_id=case_id,
        detail=f"Auto-generated {created_rounds} rounds and {created_items} dispute items for case {case_id}",
    )

    return {"rounds_created": created_rounds, "items_created": created_items}
