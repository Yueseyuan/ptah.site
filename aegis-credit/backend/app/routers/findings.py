import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Finding, Tradeline, TradelineComparison
from app.services.ai_service import generate_findings

router = APIRouter(prefix="/api/findings", tags=["findings"])


class FindingUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None


def _out(f: Finding) -> dict:
    return {
        "id": f.id,
        "case_id": f.case_id,
        "tradeline_id": f.tradeline_id,
        "finding_type": f.finding_type,
        "severity": f.severity,
        "title": f.title,
        "description": f.description,
        "fcra_section": f.fcra_section,
        "evidence_ids": json.loads(f.evidence_ids) if f.evidence_ids else [],
        "requires_human_review": f.requires_human_review,
        "status": f.status,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.get("/case/{case_id}")
def list_findings(case_id: int, db: Session = Depends(get_db)):
    return [_out(f) for f in db.query(Finding).filter(Finding.case_id == case_id).order_by(Finding.severity).all()]


@router.post("/case/{case_id}/generate")
def generate_case_findings(case_id: int, db: Session = Depends(get_db)):
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    comparisons = db.query(TradelineComparison).filter(TradelineComparison.case_id == case_id).all()
    if not tradelines:
        raise HTTPException(400, "No tradelines found. Upload and parse credit reports first.")

    tradelines_data = [{
        "creditor_name": t.creditor_name,
        "bureau": t.bureau,
        "account_type": t.account_type,
        "payment_status": t.payment_status,
        "balance": t.balance,
        "derogatory": t.derogatory,
        "open_date": t.open_date,
    } for t in tradelines]

    comparisons_data = [{
        "creditor_name": c.creditor_name,
        "discrepancy_type": c.discrepancy_type,
        "severity": c.severity,
        "details": c.details,
    } for c in comparisons]

    try:
        findings_data = generate_findings(tradelines_data, comparisons_data)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    db.query(Finding).filter(Finding.case_id == case_id).delete()
    new_findings = []
    for fd in findings_data:
        f = Finding(
            case_id=case_id,
            finding_type=fd.get("finding_type", "derogatory"),
            severity=fd.get("severity", "medium"),
            title=fd.get("title", "Finding"),
            description=fd.get("description", ""),
            fcra_section=fd.get("fcra_section", ""),
            requires_human_review=True,
            status="open",
        )
        db.add(f)
        new_findings.append(f)
    db.commit()
    for f in new_findings:
        db.refresh(f)
    return {"findings_generated": len(new_findings), "items": [_out(f) for f in new_findings]}


@router.patch("/{finding_id}")
def update_finding(finding_id: int, data: FindingUpdate, db: Session = Depends(get_db)):
    f = db.query(Finding).filter(Finding.id == finding_id).first()
    if not f:
        raise HTTPException(404, "Finding not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(f, k, v)
    db.commit()
    db.refresh(f)
    return _out(f)
