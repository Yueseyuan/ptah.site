"""Collection Account Review Engine router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tradeline, Finding
from app.services.collection_service import analyze_collection_accounts

router = APIRouter(prefix="/api/collection-review", tags=["collection_review"])


def _finding_out(f: Finding) -> dict:
    import json
    return {
        "id": f.id,
        "case_id": f.case_id,
        "finding_type": f.finding_type,
        "severity": f.severity,
        "title": f.title,
        "description": f.description,
        "rule_code": f.fcra_section,  # stored in title prefix
        "status": f.status,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.get("/case/{case_id}")
def list_collection_findings(case_id: int, db: Session = Depends(get_db)):
    """List saved collection findings for a case."""
    findings = (
        db.query(Finding)
        .filter(Finding.case_id == case_id, Finding.finding_type == "collection")
        .all()
    )
    return [_finding_out(f) for f in findings]


@router.post("/case/{case_id}/analyze")
def analyze_case_collections(case_id: int, db: Session = Depends(get_db)):
    """Run collection analysis, save findings, return summary."""
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    if not tradelines:
        return {"tradelines_analyzed": 0, "findings_generated": 0, "findings": []}

    tradeline_dicts = [
        {
            "id": t.id,
            "bureau": t.bureau,
            "creditor_name": t.creditor_name,
            "account_number_last4": t.account_number_last4,
            "account_type": t.account_type,
            "balance": t.balance,
            "payment_status": t.payment_status,
            "dofd": t.dofd,
            "derogatory": t.derogatory,
        }
        for t in tradelines
    ]

    raw_findings = analyze_collection_accounts(tradeline_dicts)

    # Delete old collection findings for this case
    db.query(Finding).filter(
        Finding.case_id == case_id,
        Finding.finding_type == "collection",
    ).delete()
    db.flush()

    saved = []
    for fd in raw_findings:
        f = Finding(
            case_id=case_id,
            finding_type="collection",
            severity=fd["severity"],
            title=f"{fd['rule_code']}: {fd['rule_name']}",
            description=fd["description"],
            fcra_section=fd.get("fcra_section", ""),
            requires_human_review=True,
            status="open",
        )
        db.add(f)
        db.flush()
        saved.append({
            "id": f.id,
            "rule_code": fd["rule_code"],
            "rule_name": fd["rule_name"],
            "severity": fd["severity"],
            "description": fd["description"],
            "fcra_section": fd.get("fcra_section", ""),
            "tradeline_ids": fd.get("tradeline_ids", []),
            "bureaus_affected": fd.get("bureaus_affected", []),
        })

    db.commit()

    return {
        "tradelines_analyzed": len(tradelines),
        "findings_generated": len(saved),
        "findings": saved,
    }
