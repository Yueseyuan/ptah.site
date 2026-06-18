import os
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AegisCase, AegisClient, GeneratedReport, Finding, StrategyItem, Tradeline, Outcome, DisputeRound
from app.config import settings

router = APIRouter(prefix="/api/report-generator", tags=["report_generator"])

_BUREAU_ADDRESS = {
    "experian":   "Experian\nP.O. Box 4500\nAllen, TX 75013",
    "equifax":    "Equifax Information Services LLC\nP.O. Box 740256\nAtlanta, GA 30374",
    "transunion": "TransUnion LLC\nConsumer Dispute Center\nP.O. Box 2000\nChester, PA 19016",
    "innovis":    "Innovis Consumer Assistance\nPO Box 530000\nColumbus, OH 43218",
}


def _make_dispute_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    recipient_type = (round_.recipient_type or "bureau").lower()
    is_bureau = recipient_type == "bureau"

    # Determine recipient address block
    if is_bureau and round_.bureau:
        recipient_addr = _BUREAU_ADDRESS.get(round_.bureau.lower(), round_.bureau.upper())
    elif round_.recipient_name:
        recipient_addr = round_.recipient_name
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
    else:
        recipient_addr = recipient_type.replace("_", " ").title()

    client_addr_parts = [f"{client.first_name} {client.last_name}"]
    if client.address:
        client_addr_parts.append(client.address)
    if client.city or client.state or client.zip_code:
        client_addr_parts.append(f"{client.city or ''}, {client.state or ''} {client.zip_code or ''}".strip(", "))
    client_addr = "\n".join(client_addr_parts)

    # Letter varies by recipient type
    if is_bureau:
        re_line = f"RE: Formal Dispute of Inaccurate Credit Information — Round {round_.round_number}"
        authority_line = "    Pursuant to FCRA §§ 611, 623"
        body_intro = [
            "I am writing to formally dispute the following inaccurate and/or unverifiable",
            "information appearing on my credit report. Under the Fair Credit Reporting Act",
            "(FCRA) § 611, I request that you investigate and correct or delete each item",
            "listed below within 30 days of receipt of this letter.",
        ]
        close_demands = [
            "Please investigate each item above and:",
            "  1. Correct any inaccurate information, OR",
            "  2. Delete any information that cannot be verified.",
            "",
            "Under FCRA § 611(a)(1), you must complete your investigation within 30 days",
            "(or 45 days if I provide additional information during the investigation period).",
            "Please send written notice of the results of your investigation to the address",
            "above, including a copy of my updated credit report if any changes are made.",
        ]
        compliance = "FCRA §§ 611, 623"
    elif recipient_type == "collection_agency":
        re_line = f"RE: Debt Validation Request — Round {round_.round_number}"
        authority_line = "    Pursuant to FDCPA § 809(b) and FCRA § 623"
        body_intro = [
            "I am writing to formally request validation of the debt(s) listed below, pursuant",
            "to the Fair Debt Collection Practices Act (FDCPA) § 809(b). You are hereby",
            "notified to cease collection activities until you have provided proper validation.",
            "Additionally, I dispute the accuracy of the information reported to credit bureaus",
            "under FCRA § 623.",
        ]
        close_demands = [
            "Please provide the following within 30 days:",
            "  1. Proof that your agency is licensed to collect debt in my state.",
            "  2. The name and address of the original creditor.",
            "  3. A copy of the original signed agreement.",
            "  4. Verification that the statute of limitations has not expired.",
            "  5. Proof of the amount claimed, including all fees and interest.",
            "",
            "If you cannot validate this debt, you must cease all collection activities",
            "and instruct all credit reporting agencies to delete the account.",
        ]
        compliance = "FDCPA § 809(b), FCRA § 623"
    else:  # creditor or debt_buyer
        re_line = f"RE: Dispute of Inaccurate Account Information — Round {round_.round_number}"
        authority_line = "    Pursuant to FCRA § 623"
        body_intro = [
            "I am writing to formally dispute inaccurate information you have reported to",
            "credit reporting agencies regarding my account(s). Under FCRA § 623, furnishers",
            "of information have a duty to report accurate data and must investigate disputes",
            "and correct any inaccuracies within 30 days.",
        ]
        close_demands = [
            "Please investigate each item above and:",
            "  1. Correct any inaccurate information with all credit reporting agencies, OR",
            "  2. Delete the account from all credit reports if the information cannot be verified.",
            "",
            "Under FCRA § 623(b), you must complete your investigation within 30 days and",
            "report the results to the credit reporting agencies. Please send written",
            "confirmation of the correction(s) to the address above.",
        ]
        compliance = "FCRA § 623"

    lines = [
        client_addr,
        "",
        today,
        "",
        recipient_addr,
        "",
        re_line,
        authority_line,
        "",
        "To Whom It May Concern:",
        "",
    ] + body_intro + [
        "",
        "─" * 65,
        "DISPUTED ACCOUNTS",
        "─" * 65,
    ]

    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "(account number not available)"
        lines += [
            "",
            f"Item {i}: {item.creditor_name}",
            f"  Account: {acct}",
            f"  Dispute Reason: {item.dispute_reason}",
            f"  Legal Basis: {item.fcra_basis or compliance}",
        ]

    lines += [
        "",
        "─" * 65,
        "",
    ] + close_demands + [
        "",
        "If you need additional documentation, please contact me at the address above.",
        "I reserve all rights and remedies available under applicable law.",
        "",
        "Sincerely,",
        "",
        "",
        f"{client.first_name} {client.last_name}",
        "",
        "─" * 65,
        "COMPLIANCE NOTICE: This letter is for dispute purposes only. It does not",
        "constitute legal advice. Consult a qualified attorney for legal guidance.",
        "─" * 65,
    ]
    return "\n".join(lines)


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


@router.get("/dispute-letter/{round_id}")
def download_dispute_letter(round_id: int, db: Session = Depends(get_db)):
    """Generate and download a dispute letter for a specific round."""
    round_ = db.query(DisputeRound).filter(DisputeRound.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Dispute round not found")
    if not round_.items:
        raise HTTPException(400, "This round has no dispute items — add items before downloading the letter.")
    case = db.query(AegisCase).filter(AegisCase.id == round_.case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")

    today = datetime.now().strftime("%B %d, %Y")
    content = _make_dispute_letter(round_, client, today)
    filename = f"dispute_letter_{round_.bureau}_round{round_.round_number}_{datetime.now().strftime('%Y%m%d')}.txt"
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
