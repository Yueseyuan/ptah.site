from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tradeline, Metro2Finding
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
def analyze_case(case_id: int, db: Session = Depends(get_db)):
    """Run Metro 2 rules engine against all tradelines for a case.

    Deletes any existing Metro2Finding rows for the case, then saves new findings.
    Returns a summary with the findings grouped by severity.
    """
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    if not tradelines:
        raise HTTPException(400, "No tradelines found for this case. Upload and parse credit reports first.")

    # Delete old findings
    db.query(Metro2Finding).filter(Metro2Finding.case_id == case_id).delete()
    db.flush()

    # Run rules
    raw_findings = run_metro2_rules(tradelines)

    # Save findings
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
def list_findings(case_id: int, db: Session = Depends(get_db)):
    """List all Metro2Finding rows for a case, ordered by severity."""
    severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    findings = db.query(Metro2Finding).filter(Metro2Finding.case_id == case_id).all()
    findings.sort(key=lambda f: severity_order.get(f.severity or "info", 3))
    return [_out(f) for f in findings]
