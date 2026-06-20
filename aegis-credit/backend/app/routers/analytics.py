"""Cross-case analytics and reporting aggregates."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import AegisCase, AegisClient, Finding, TradelineComparison, DisputeRound, Tradeline, Outcome
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """High-level platform statistics."""
    total_cases = db.query(func.count(AegisCase.id)).scalar() or 0
    cases_by_status = dict(
        db.query(AegisCase.status, func.count(AegisCase.id))
        .group_by(AegisCase.status).all()
    )
    total_clients = db.query(func.count(AegisClient.id)).scalar() or 0
    total_findings = db.query(func.count(Finding.id)).scalar() or 0
    findings_by_severity = dict(
        db.query(Finding.severity, func.count(Finding.id))
        .group_by(Finding.severity).all()
    )
    findings_reviewed = db.query(func.count(Finding.id)).filter(Finding.status == "reviewed").scalar() or 0
    total_tradelines = db.query(func.count(Tradeline.id)).scalar() or 0
    derogatory_tradelines = db.query(func.count(Tradeline.id)).filter(Tradeline.derogatory == True).scalar() or 0
    total_outcomes = db.query(func.count(Outcome.id)).scalar() or 0
    outcomes_by_type = dict(
        db.query(Outcome.outcome_type, func.count(Outcome.id))
        .group_by(Outcome.outcome_type).all()
    )
    return {
        "total_cases": total_cases,
        "cases_by_status": cases_by_status,
        "total_clients": total_clients,
        "total_findings": total_findings,
        "findings_by_severity": findings_by_severity,
        "findings_reviewed": findings_reviewed,
        "findings_review_rate": round(findings_reviewed / total_findings * 100, 1) if total_findings else 0,
        "total_tradelines": total_tradelines,
        "derogatory_tradelines": derogatory_tradelines,
        "derogatory_rate": round(derogatory_tradelines / total_tradelines * 100, 1) if total_tradelines else 0,
        "total_outcomes": total_outcomes,
        "outcomes_by_type": outcomes_by_type,
    }


@router.get("/bureau-accuracy")
def get_bureau_accuracy(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Cross-bureau discrepancy rates."""
    discrepancies = db.query(
        TradelineComparison.discrepancy_type,
        func.count(TradelineComparison.id)
    ).group_by(TradelineComparison.discrepancy_type).all()

    by_severity = dict(
        db.query(TradelineComparison.severity, func.count(TradelineComparison.id))
        .group_by(TradelineComparison.severity).all()
    )
    return {
        "discrepancies_by_type": dict(discrepancies),
        "discrepancies_by_severity": by_severity,
        "total_discrepancies": sum(v for _, v in discrepancies),
    }


@router.get("/dispute-outcomes")
def get_dispute_outcomes(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Dispute round status breakdown and outcome win rates."""
    rounds_by_status = dict(
        db.query(DisputeRound.status, func.count(DisputeRound.id))
        .group_by(DisputeRound.status).all()
    )
    outcomes_by_type = dict(
        db.query(Outcome.outcome_type, func.count(Outcome.id))
        .filter(Outcome.outcome_type != None)
        .group_by(Outcome.outcome_type).all()
    )
    outcomes_by_bureau = dict(
        db.query(Outcome.bureau, func.count(Outcome.id))
        .filter(Outcome.bureau != None)
        .group_by(Outcome.bureau).all()
    )
    total_outcomes = sum(outcomes_by_type.values())
    wins = (outcomes_by_type.get("deleted", 0) + outcomes_by_type.get("corrected", 0) +
            outcomes_by_type.get("updated", 0))
    return {
        "dispute_rounds_by_status": rounds_by_status,
        "outcomes_by_type": outcomes_by_type,
        "outcomes_by_bureau": outcomes_by_bureau,
        "win_rate": round(wins / total_outcomes * 100, 1) if total_outcomes else 0,
        "total_outcomes": total_outcomes,
        "favorable_outcomes": wins,
    }


@router.get("/findings-trend")
def get_findings_trend(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Findings by type and status."""
    by_type = dict(
        db.query(Finding.finding_type, func.count(Finding.id))
        .group_by(Finding.finding_type).all()
    )
    by_status = dict(
        db.query(Finding.status, func.count(Finding.id))
        .group_by(Finding.status).all()
    )
    return {
        "findings_by_type": by_type,
        "findings_by_status": by_status,
    }
