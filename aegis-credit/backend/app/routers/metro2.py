from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Tradeline, Metro2Finding, Finding, DisputeRound, DisputeItem, User
from app.dependencies import get_current_user
from app.services.metro2_service import run_metro2_rules

router = APIRouter(prefix="/api/metro2", tags=["metro2"])


def _out(f: Metro2Finding) -> dict:
    return {
        "id": f.id,
        "case_id": f.case_id,
        "tradeline_id": f.tradeline_id,
        "rule_code": f.rule_code,
        "rule_name": f.rule_name,
        "severity": f.severity,
        "description": f.description,
        "fcra_section": f.fcra_section,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.post("/case/{case_id}/analyze")
def analyze_case(case_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Run Metro 2 rules engine against all tradelines for a case.

    Deletes any existing Metro2Finding rows for the case, then saves new findings.
    Returns a summary with the findings grouped by severity.
    """
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    if not tradelines:
        raise HTTPException(400, "No tradelines found for this case. Upload and parse credit reports first.")

    try:
        db.query(Metro2Finding).filter(Metro2Finding.case_id == case_id).delete()
        raw_findings = run_metro2_rules(tradelines)
        saved = []
        for fd in raw_findings:
            finding = Metro2Finding(
                case_id=case_id,
                tradeline_id=fd.get("tradeline_id"),
                rule_code=fd.get("rule_code", ""),
                rule_name=fd.get("rule_name", ""),
                severity=fd.get("severity", "medium"),
                description=fd.get("description", ""),
                fcra_section=fd.get("fcra_section", ""),
            )
            db.add(finding)
            saved.append(finding)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(500, "Metro 2 analysis failed. Database rolled back.")

    for f in saved:
        db.refresh(f)

    # Build severity summary
    severity_counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for f in saved:
        key = f.severity if f.severity in severity_counts else "info"
        severity_counts[key] += 1

    return {
        "tradelines_analyzed": len(tradelines),
        "findings_generated": len(saved),
        "severity_summary": severity_counts,
        "items": [_out(f) for f in saved],
    }


@router.get("/case/{case_id}")
def list_findings(case_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """List all Metro2Finding rows for a case, ordered by severity."""
    severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    findings = db.query(Metro2Finding).filter(Metro2Finding.case_id == case_id).all()
    findings.sort(key=lambda f: severity_order.get(f.severity or "info", 3))
    return [_out(f) for f in findings]


class Metro2ToDisputeRequest(BaseModel):
    round_id: int
    dispute_reason: Optional[str] = None


@router.post("/findings/{metro2_finding_id}/to-dispute")
def metro2_finding_to_dispute(
    metro2_finding_id: int,
    body: Metro2ToDisputeRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Promote a Metro 2 finding to a regular Finding and create a DisputeItem in the given round."""
    m2f = db.query(Metro2Finding).filter(Metro2Finding.id == metro2_finding_id).first()
    if not m2f:
        raise HTTPException(404, "Metro 2 finding not found")

    round_ = db.query(DisputeRound).filter(DisputeRound.id == body.round_id).first()
    if not round_:
        raise HTTPException(404, "Dispute round not found")

    tradeline = (
        db.query(Tradeline).filter(Tradeline.id == m2f.tradeline_id).first()
        if m2f.tradeline_id else None
    )

    finding = Finding(
        case_id=m2f.case_id,
        tradeline_id=m2f.tradeline_id,
        finding_type="metro2",
        severity=m2f.severity,
        title=m2f.rule_name,
        description=m2f.description,
        fcra_section=m2f.fcra_section,
        requires_human_review=True,
        status="open",
    )
    db.add(finding)
    db.flush()

    reason = body.dispute_reason or m2f.description or m2f.rule_name
    item = DisputeItem(
        round_id=body.round_id,
        tradeline_id=m2f.tradeline_id,
        creditor_name=tradeline.creditor_name if tradeline else "Metro 2 Violation",
        account_number_last4=tradeline.account_number_last4 if tradeline else "",
        dispute_reason=reason[:500],
        fcra_basis=m2f.fcra_section or "",
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(finding)
    db.refresh(item)

    return {
        "finding_id": finding.id,
        "dispute_item_id": item.id,
        "round_id": body.round_id,
        "round_number": round_.round_number,
        "message": f"'{m2f.rule_name}' added to Round #{round_.round_number}",
    }
