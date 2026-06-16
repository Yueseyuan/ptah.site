import os
import json
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CreditReport, Tradeline, Inquiry, PersonalInfo
from app.services.pdf_service import extract_text_from_pdf, detect_bureau_from_text
from app.services.ai_service import extract_tradelines_from_text, extract_report_data
from app.services.audit_service import log_action
from app.config import settings

router = APIRouter(prefix="/api/reports", tags=["reports"])

BUREAUS = ["experian", "equifax", "transunion", "innovis"]
UPLOAD_BUREAUS = BUREAUS + ["all"]


def _resolve_tradeline_bureau(report_bureau: str, td: dict) -> str:
    """Trust the AI's per-account bureau identification whenever it gave one -- many
    reports are tri-merge even when the uploader didn't select "All Bureaus", and the
    AI is told to identify each account's actual bureau from the report text itself."""
    td_bureau = td.get("bureau", "")
    if td_bureau in BUREAUS:
        return td_bureau
    if report_bureau in BUREAUS:
        return report_bureau
    return "unknown"


def _out(r: CreditReport) -> dict:
    return {
        "id": r.id,
        "case_id": r.case_id,
        "bureau": r.bureau,
        "file_path": r.file_path,
        "parse_status": r.parse_status,
        "report_date": r.report_date,
        "parse_error": r.parse_error,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "has_text": bool(r.raw_text),
    }


def _save_tradelines(db: Session, case_id: int, report: CreditReport, tradelines_data: list):
    bureau = report.bureau
    for td in tradelines_data:
        tl = Tradeline(
            case_id=case_id,
            report_id=report.id,
            bureau=_resolve_tradeline_bureau(bureau, td),
            creditor_name=td.get("creditor_name", ""),
            account_number_last4=td.get("account_number_last4", ""),
            account_type=td.get("account_type", "other"),
            open_date=td.get("open_date", ""),
            close_date=td.get("close_date", ""),
            balance=td.get("balance"),
            credit_limit=td.get("credit_limit"),
            payment_status=td.get("payment_status", "unknown"),
            payment_history=td.get("payment_history", ""),
            derogatory=td.get("derogatory", False),
            high_balance=td.get("high_balance"),
            past_due_amount=td.get("past_due_amount"),
            scheduled_payment_amount=td.get("scheduled_payment_amount"),
            payment_rating=td.get("payment_rating", ""),
            compliance_condition_code=td.get("compliance_condition_code", ""),
            consumer_information_indicator=td.get("consumer_information_indicator", ""),
            dofd=td.get("dofd", ""),
            date_reported=td.get("date_reported", ""),
            remarks=td.get("remarks", ""),
            raw_source_text=td.get("raw_source_text", ""),
        )
        db.add(tl)


def _save_inquiries(db: Session, case_id: int, report_id: int, inquiries_data: list):
    for inq in inquiries_data:
        inquiry = Inquiry(
            case_id=case_id,
            report_id=report_id,
            bureau=(inq.get("bureau") or "").lower(),
            inquiry_type=inq.get("inquiry_type", "hard"),
            subscriber_name=inq.get("subscriber_name", ""),
            inquiry_date=inq.get("inquiry_date", "") or None,
            purpose=inq.get("purpose", "") or None,
        )
        db.add(inquiry)


def _save_personal_info(db: Session, case_id: int, report_id: int, pi_data: list):
    for pi in pi_data:
        aliases = pi.get("aliases", [])
        previous_addresses = pi.get("previous_addresses", [])
        previous_employers = pi.get("previous_employers", [])
        phone_numbers = pi.get("phone_numbers", [])

        # Serialize lists to JSON strings if they aren't already
        if isinstance(aliases, list):
            aliases = json.dumps(aliases)
        if isinstance(previous_addresses, list):
            previous_addresses = json.dumps(previous_addresses)
        if isinstance(previous_employers, list):
            previous_employers = json.dumps(previous_employers)
        if isinstance(phone_numbers, list):
            phone_numbers = json.dumps(phone_numbers)

        record = PersonalInfo(
            case_id=case_id,
            report_id=report_id,
            bureau=(pi.get("bureau") or "").lower(),
            current_name=pi.get("current_name", "") or None,
            aliases=aliases or None,
            current_address=pi.get("current_address", "") or None,
            previous_addresses=previous_addresses or None,
            current_employer=pi.get("current_employer", "") or None,
            previous_employers=previous_employers or None,
            phone_numbers=phone_numbers or None,
            dob=pi.get("dob", "") or None,
            ssn_last4=pi.get("ssn_last4", "") or None,
        )
        db.add(record)


@router.get("/case/{case_id}")
def list_reports(case_id: int, db: Session = Depends(get_db)):
    return [_out(r) for r in db.query(CreditReport).filter(CreditReport.case_id == case_id).all()]


@router.post("/upload")
async def upload_report(
    case_id: int = Form(...),
    bureau: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if bureau not in UPLOAD_BUREAUS:
        raise HTTPException(400, f"Bureau must be one of: {UPLOAD_BUREAUS}")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"case_{case_id}_{bureau}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    report = CreditReport(case_id=case_id, bureau=bureau, file_path=file_path, parse_status="pending")
    db.add(report)
    db.commit()
    db.refresh(report)
    try:
        raw_text = extract_text_from_pdf(file_path)
        if bureau not in UPLOAD_BUREAUS or bureau == "unknown":
            bureau = detect_bureau_from_text(raw_text)
            report.bureau = bureau
        report.raw_text = raw_text
        report.parse_status = "parsed"
        db.commit()

        # Extract all data (tradelines + inquiries + personal info)
        try:
            extracted = extract_report_data(raw_text)
            tradelines_data = extracted.get("tradelines", [])
            inquiries_data = extracted.get("inquiries", [])
            pi_data = extracted.get("personal_info", [])
        except Exception:
            # Fall back to tradelines-only extraction
            tradelines_data = extract_tradelines_from_text(raw_text)
            inquiries_data = []
            pi_data = []

        _save_tradelines(db, case_id, report, tradelines_data)
        _save_inquiries(db, case_id, report.id, inquiries_data)
        _save_personal_info(db, case_id, report.id, pi_data)

        db.commit()
        db.refresh(report)
        log_action(db, "UPLOAD", "credit_report", report.id, detail=f"Bureau: {bureau}")
    except Exception as e:
        report.parse_status = "failed"
        report.parse_error = str(e)
        db.commit()
    return _out(report)


@router.get("/{report_id}/raw-text")
def get_raw_text(report_id: int, db: Session = Depends(get_db)):
    report = db.query(CreditReport).filter(CreditReport.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    return {"raw_text": report.raw_text or ""}


@router.post("/{report_id}/reparse")
def reparse_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(CreditReport).filter(CreditReport.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if not report.raw_text:
        try:
            report.raw_text = extract_text_from_pdf(report.file_path)
        except Exception as e:
            raise HTTPException(500, f"Cannot extract text: {e}")
    try:
        # Extract all data
        try:
            extracted = extract_report_data(report.raw_text)
            tradelines_data = extracted.get("tradelines", [])
            inquiries_data = extracted.get("inquiries", [])
            pi_data = extracted.get("personal_info", [])
        except Exception:
            tradelines_data = extract_tradelines_from_text(report.raw_text)
            inquiries_data = []
            pi_data = []

        # Clear existing data for this report
        db.query(Tradeline).filter(Tradeline.report_id == report_id).delete()
        db.query(Inquiry).filter(Inquiry.report_id == report_id).delete()
        db.query(PersonalInfo).filter(PersonalInfo.report_id == report_id).delete()

        _save_tradelines(db, report.case_id, report, tradelines_data)
        _save_inquiries(db, report.case_id, report_id, inquiries_data)
        _save_personal_info(db, report.case_id, report_id, pi_data)

        report.parse_status = "parsed"
        db.commit()
    except Exception as e:
        report.parse_status = "failed"
        report.parse_error = str(e)
        db.commit()
        raise HTTPException(500, str(e))
    return _out(report)


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(CreditReport).filter(CreditReport.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    db.query(Tradeline).filter(Tradeline.report_id == report_id).delete()
    db.delete(report)
    db.commit()
