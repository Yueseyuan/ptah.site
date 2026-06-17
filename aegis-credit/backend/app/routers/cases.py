import random
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import AegisCase, AegisClient
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/cases", tags=["cases"])


def gen_case_number() -> str:
    suffix = "".join(random.choices(string.digits, k=6))
    return f"AEG-{suffix}"


class CaseCreate(BaseModel):
    client_id: int
    goal: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    goal: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


def _out(c: AegisCase) -> dict:
    return {
        "id": c.id,
        "client_id": c.client_id,
        "case_number": c.case_number,
        "status": c.status,
        "goal": c.goal,
        "notes": c.notes,
        "assigned_to": c.assigned_to,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("/")
def list_cases(client_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(AegisCase)
    if client_id is not None:
        q = q.filter(AegisCase.client_id == client_id)
    return [_out(c) for c in q.order_by(AegisCase.id.desc()).all()]


@router.post("/", status_code=201)
def create_case(data: CaseCreate, db: Session = Depends(get_db)):
    case = AegisCase(**data.model_dump(), case_number=gen_case_number())
    db.add(case)
    db.commit()
    db.refresh(case)
    return _out(case)


@router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    return _out(case)


@router.patch("/{case_id}")
def update_case(case_id: int, data: CaseUpdate, db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(case, k, v)
    db.commit()
    db.refresh(case)
    return _out(case)


@router.get("/{case_id}/summary")
def case_summary(case_id: int, db: Session = Depends(get_db)):
    from app.models import CreditReport, Tradeline, Finding, DisputeRound, Outcome
    from datetime import date
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    reports = db.query(CreditReport).filter(CreditReport.case_id == case_id).count()
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).count()
    derogatory = db.query(Tradeline).filter(Tradeline.case_id == case_id, Tradeline.derogatory == True).count()
    findings = db.query(Finding).filter(Finding.case_id == case_id).count()
    high_findings = db.query(Finding).filter(Finding.case_id == case_id, Finding.severity == "high").count()
    open_high = db.query(Finding).filter(Finding.case_id == case_id, Finding.severity == "high", Finding.status == "open").count()
    rounds = db.query(DisputeRound).filter(DisputeRound.case_id == case_id).count()
    today_str = date.today().isoformat()
    overdue = db.query(DisputeRound).filter(
        DisputeRound.case_id == case_id,
        DisputeRound.response_due_date < today_str,
        DisputeRound.status.notin_(["response_received", "closed"]),
    ).count()
    outcomes = db.query(Outcome).filter(Outcome.case_id == case_id).count()
    return {
        "case": _out(case),
        "reports_uploaded": reports,
        "tradelines_total": tradelines,
        "tradelines_derogatory": derogatory,
        "findings_total": findings,
        "findings_high": high_findings,
        "open_high_findings": open_high,
        "dispute_rounds": rounds,
        "overdue_disputes": overdue,
        "outcomes": outcomes,
    }


@router.get("/{case_id}/export")
def export_case(case_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Export a complete case snapshot as JSON."""
    from app.models import Tradeline, Finding, DisputeRound, DisputeItem, Outcome, TimelineEvent, Inquiry, PersonalInfo
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    findings = db.query(Finding).filter(Finding.case_id == case_id).all()
    rounds = db.query(DisputeRound).filter(DisputeRound.case_id == case_id).all()
    outcomes = db.query(Outcome).filter(Outcome.case_id == case_id).all()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).order_by(TimelineEvent.event_date).all()
    inquiries = db.query(Inquiry).filter(Inquiry.case_id == case_id).all()
    pi_records = db.query(PersonalInfo).filter(PersonalInfo.case_id == case_id).all()

    return {
        "exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "system": "Aegis Credit Intelligence — For human review only. Not legal advice.",
        "case": {
            "id": case.id,
            "case_number": case.case_number,
            "status": case.status,
            "goal": case.goal,
            "notes": case.notes,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        },
        "client": {
            "id": client.id if client else None,
            "name": f"{client.first_name} {client.last_name}" if client else None,
            "state": client.state if client else None,
        } if client else None,
        "tradelines_count": len(tradelines),
        "tradelines": [
            {"bureau": t.bureau, "creditor_name": t.creditor_name, "account_type": t.account_type,
             "payment_status": t.payment_status, "balance": t.balance, "derogatory": t.derogatory}
            for t in tradelines
        ],
        "findings_count": len(findings),
        "findings": [
            {"severity": f.severity, "title": f.title, "description": f.description,
             "fcra_section": f.fcra_section, "status": f.status, "finding_type": f.finding_type}
            for f in findings
        ],
        "dispute_rounds": len(rounds),
        "outcomes": [
            {"bureau": o.bureau, "creditor_name": o.creditor_name,
             "outcome_type": o.outcome_type, "notes": o.notes}
            for o in outcomes
        ],
        "timeline_events": len(timeline),
        "inquiries_count": len(inquiries),
        "personal_info_records": len(pi_records),
    }


@router.get("/{case_id}/applicable-laws")
def get_applicable_laws(case_id: int, db: Session = Depends(get_db)):
    from app.models import AegisClient, StateLaw
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    state = client.state if client else None
    if not state:
        return {"state": None, "laws": []}
    laws = db.query(StateLaw).filter(
        StateLaw.state == state,
        StateLaw.superseded == False,
    ).all()
    return {
        "state": state,
        "laws": [
            {
                "id": law.id,
                "statute": law.statute,
                "citation": law.citation,
                "topic": law.topic,
                "summary": law.summary,
                "effective_date": law.effective_date,
                "effective_as_of": getattr(law, "effective_as_of", None),
            }
            for law in laws
        ],
    }


@router.post("/{case_id}/analyze-all")
def analyze_all(case_id: int, db: Session = Depends(get_db)):
    """Run all analysis engines for a case: collection, court, PI, inquiry, Metro 2."""
    from app.models import Tradeline, Finding, PersonalInfo, Inquiry, CourtRecord, Metro2Finding
    from app.services.collection_service import analyze_collection_accounts
    from app.services.court_service import analyze_court_records
    from app.services.pi_service import run_pi_analysis
    from app.services.inquiry_service import run_inquiry_analysis
    from app.services.metro2_service import run_metro2_rules

    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    tl_dicts = [{"id": t.id, "bureau": t.bureau, "creditor_name": t.creditor_name, "account_number_last4": t.account_number_last4,
                 "account_type": t.account_type, "balance": t.balance, "payment_status": t.payment_status, "dofd": t.dofd, "derogatory": t.derogatory}
                for t in tradelines]
    results = {}

    # Collection analysis
    try:
        db.query(Finding).filter(Finding.case_id == case_id, Finding.finding_type == "collection").delete()
        raw = analyze_collection_accounts(tl_dicts)
        for fd in raw:
            db.add(Finding(case_id=case_id, finding_type="collection", severity=fd["severity"],
                           title=f"{fd['rule_code']}: {fd['rule_name']}", description=fd["description"],
                           fcra_section=fd.get("fcra_section", ""), requires_human_review=True, status="open"))
        results["collection"] = len(raw)
    except Exception as e:
        results["collection_error"] = str(e)

    # Court analysis
    try:
        court_records = db.query(CourtRecord).filter(CourtRecord.case_id == case_id).all()
        cr_dicts = [{"id": r.id, "record_type": r.record_type, "disposition": r.disposition, "court_name": r.court_name}
                    for r in court_records]
        db.query(Finding).filter(Finding.case_id == case_id, Finding.finding_type == "court").delete()
        raw_ct = analyze_court_records(cr_dicts, tl_dicts)
        for fd in raw_ct:
            db.add(Finding(case_id=case_id, finding_type="court", severity=fd["severity"],
                           title=f"{fd['rule_code']}: {fd['rule_name']}", description=fd["description"],
                           fcra_section=fd.get("fcra_section", ""), requires_human_review=True, status="open"))
        results["court"] = len(raw_ct)
    except Exception as e:
        results["court_error"] = str(e)

    # PI analysis
    try:
        pi_records = db.query(PersonalInfo).filter(PersonalInfo.case_id == case_id).all()
        pi_dicts = [{"id": r.id, "bureau": r.bureau, "current_name": r.current_name, "aliases": r.aliases,
                     "current_address": r.current_address, "previous_addresses": r.previous_addresses,
                     "dob": r.dob, "ssn_last4": r.ssn_last4}
                    for r in pi_records]
        db.query(Finding).filter(Finding.case_id == case_id, Finding.finding_type == "personal_info").delete()
        raw_pi = run_pi_analysis(pi_dicts)
        for fd in raw_pi:
            db.add(Finding(case_id=case_id, finding_type="personal_info", severity=fd["severity"],
                           title=f"{fd['rule_code']}: {fd['rule_name']}", description=fd["description"],
                           fcra_section=fd.get("fcra_section", ""), requires_human_review=True, status="open"))
        results["personal_info"] = len(raw_pi)
    except Exception as e:
        results["personal_info_error"] = str(e)

    # Inquiry analysis
    try:
        inq_records = db.query(Inquiry).filter(Inquiry.case_id == case_id).all()
        inq_dicts = [{"id": i.id, "bureau": i.bureau, "inquiry_type": i.inquiry_type,
                      "subscriber_name": i.subscriber_name, "inquiry_date": i.inquiry_date}
                     for i in inq_records]
        db.query(Finding).filter(Finding.case_id == case_id, Finding.finding_type == "inquiry").delete()
        raw_inq = run_inquiry_analysis(inq_dicts)
        for fd in raw_inq:
            db.add(Finding(case_id=case_id, finding_type="inquiry", severity=fd["severity"],
                           title=f"{fd['rule_code']}: {fd['rule_name']}", description=fd["description"],
                           fcra_section=fd.get("fcra_section", ""), requires_human_review=True, status="open"))
        results["inquiry"] = len(raw_inq)
    except Exception as e:
        results["inquiry_error"] = str(e)

    # Metro 2 analysis (uses Metro2Finding model)
    try:
        db.query(Metro2Finding).filter(Metro2Finding.case_id == case_id).delete()
        raw_m2 = run_metro2_rules(tradelines)
        for fd in raw_m2:
            db.add(Metro2Finding(case_id=case_id, tradeline_id=fd.get("tradeline_id"),
                                 rule_code=fd.get("rule_code", ""), rule_name=fd.get("rule_name", ""),
                                 severity=fd.get("severity", "medium"), description=fd.get("description", ""),
                                 fcra_section=fd.get("fcra_section", "")))
        results["metro2"] = len(raw_m2)
    except Exception as e:
        results["metro2_error"] = str(e)

    db.commit()
    results["total_findings"] = sum(v for k, v in results.items() if isinstance(v, int))
    return results
