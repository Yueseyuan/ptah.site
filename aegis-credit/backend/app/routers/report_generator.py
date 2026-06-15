import os
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AegisCase, AegisClient, GeneratedReport, Finding, StrategyItem, Tradeline, Outcome
from app.config import settings

router = APIRouter(prefix="/api/report-generator", tags=["report_generator"])


def _make_text_report(case: AegisCase, client: AegisClient, findings: list, tradelines: list, strategy: list) -> str:
    lines = [
        "=" * 70,
        "AEGIS CREDIT INVESTIGATOR — CASE SUMMARY REPORT",
        "=" * 70,
        "",
        "COMPLIANCE NOTICE: This report is for investigator and client review only.",
        "No finding constitutes legal advice, a proven violation, or a guarantee",
        "of any outcome. All findings require human review before any action.",
        "",
        f"Case Number: {case.case_number}",
        f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Client: {client.first_name} {client.last_name}",
        f"Status: {case.status}",
        f"Goal: {case.goal or 'Not specified'}",
        "",
        "─" * 70,
        f"TRADELINE SUMMARY ({len(tradelines)} accounts)",
        "─" * 70,
    ]
    bureaus = {}
    for tl in tradelines:
        b = tl.bureau or "unknown"
        bureaus.setdefault(b, []).append(tl)
    for bureau, tls in bureaus.items():
        lines.append(f"\n{bureau.upper()}:")
        for tl in tls:
            flag = "[DEROGATORY] " if tl.derogatory else ""
            lines.append(f"  {flag}{tl.creditor_name} ({tl.account_type}) — Status: {tl.payment_status}"
                         f"{' — Balance: $' + str(tl.balance) if tl.balance else ''}")

    lines += ["", "─" * 70, f"FINDINGS ({len(findings)} total)", "─" * 70]
    for f in findings:
        lines.append(f"\n[{f.severity.upper()}] {f.title}")
        lines.append(f"  Type: {f.finding_type} | FCRA: {f.fcra_section or 'N/A'}")
        lines.append(f"  {f.description}")
        lines.append(f"  *** REQUIRES HUMAN REVIEW BEFORE ANY ACTION ***")

    lines += ["", "─" * 70, f"RECOMMENDED STRATEGY ({len(strategy)} items)", "─" * 70]
    for s in strategy:
        lines.append(f"\nP{s.priority} — {s.title} [{s.strategy_type}]")
        lines.append(f"  Timeline: {s.estimated_timeline or 'TBD'}")
        if s.description:
            lines.append(f"  {s.description}")
        try:
            actions = json.loads(s.action_items) if s.action_items else []
            for a in actions:
                lines.append(f"    • {a}")
        except Exception:
            pass

    lines += ["", "=" * 70, "END OF REPORT — Aegis Credit Investigator", "=" * 70]
    return "\n".join(lines)


@router.post("/case/{case_id}/generate")
def generate_report(case_id: int, report_type: str = "summary", db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")

    findings = db.query(Finding).filter(Finding.case_id == case_id).all()
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    strategy = db.query(StrategyItem).filter(StrategyItem.case_id == case_id).order_by(StrategyItem.priority).all()

    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    filename = f"aegis_report_{case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_path = os.path.join(settings.REPORTS_DIR, filename)

    content = _make_text_report(case, client, findings, tradelines, strategy)
    with open(file_path, "w") as f:
        f.write(content)

    record = GeneratedReport(case_id=case_id, report_type=report_type, file_path=file_path)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "case_id": record.case_id,
        "report_type": record.report_type,
        "file_path": record.file_path,
        "generated_at": record.generated_at.isoformat() if record.generated_at else None,
    }


@router.get("/case/{case_id}")
def list_reports(case_id: int, db: Session = Depends(get_db)):
    reports = db.query(GeneratedReport).filter(GeneratedReport.case_id == case_id).all()
    return [{
        "id": r.id,
        "case_id": r.case_id,
        "report_type": r.report_type,
        "file_path": r.file_path,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
    } for r in reports]


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not r:
        raise HTTPException(404, "Report not found")
    if not os.path.exists(r.file_path):
        raise HTTPException(404, "Report file not found on disk")
    return FileResponse(r.file_path, filename=os.path.basename(r.file_path))
