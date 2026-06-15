import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tradeline, TradelineComparison
from app.services.ai_service import run_cross_bureau_comparison

router = APIRouter(prefix="/api/comparison", tags=["comparison"])


def _out(c: TradelineComparison) -> dict:
    return {
        "id": c.id,
        "case_id": c.case_id,
        "creditor_name": c.creditor_name,
        "account_number_last4": c.account_number_last4,
        "discrepancy_type": c.discrepancy_type,
        "bureaus_affected": json.loads(c.bureaus_affected) if c.bureaus_affected else [],
        "details": c.details,
        "severity": c.severity,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/case/{case_id}")
def list_comparisons(case_id: int, db: Session = Depends(get_db)):
    return [_out(c) for c in db.query(TradelineComparison).filter(TradelineComparison.case_id == case_id).all()]


@router.post("/case/{case_id}/run")
def run_comparison(case_id: int, db: Session = Depends(get_db)):
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    if not tradelines:
        raise HTTPException(400, "No tradelines found for this case. Upload credit reports first.")

    tradelines_by_bureau: dict[str, list[dict]] = {}
    for tl in tradelines:
        bureau = tl.bureau or "unknown"
        if bureau not in tradelines_by_bureau:
            tradelines_by_bureau[bureau] = []
        tradelines_by_bureau[bureau].append({
            "id": tl.id,
            "creditor_name": tl.creditor_name,
            "account_number_last4": tl.account_number_last4,
            "balance": tl.balance,
            "payment_status": tl.payment_status,
            "derogatory": tl.derogatory,
        })

    discrepancies = run_cross_bureau_comparison(tradelines_by_bureau)
    db.query(TradelineComparison).filter(TradelineComparison.case_id == case_id).delete()
    new_comparisons = []
    for d in discrepancies:
        comp = TradelineComparison(
            case_id=case_id,
            creditor_name=d.get("creditor_name", ""),
            account_number_last4=d.get("account_number_last4", ""),
            discrepancy_type=d.get("discrepancy_type", "other"),
            bureaus_affected=json.dumps(d.get("bureaus_affected", [])),
            details=d.get("details", ""),
            severity=d.get("severity", "medium"),
        )
        db.add(comp)
        new_comparisons.append(comp)
    db.commit()
    for c in new_comparisons:
        db.refresh(c)
    return {"comparisons_found": len(new_comparisons), "items": [_out(c) for c in new_comparisons]}
