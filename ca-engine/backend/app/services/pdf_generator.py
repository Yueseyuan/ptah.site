import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

NAVY = colors.HexColor("#0d2244")
GOLD = colors.HexColor("#c49a1a")
LIGHT_GRAY = colors.HexColor("#f5f5f5")

COMPANY_NAME = "Cruel & Associates"
COMPANY_TAGLINE = "Administrative Services | Document Preparation | Community Reentry"
COMPANY_PHONE = "(864) 990-1301"
COMPANY_EMAIL = "yueseyuan.cruel@cruelandassociates.site"
COMPANY_WEBSITE = "www.cruelandassociates.site"
COMPANY_ADDRESS = "South Carolina"

OUTPUT_DIR = Path("generated_docs")
OUTPUT_DIR.mkdir(exist_ok=True)


def _base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CompanyName",
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="CompanyTagline",
        fontSize=9,
        fontName="Helvetica",
        textColor=GOLD,
        alignment=TA_CENTER,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="CompanyContact",
        fontSize=8,
        fontName="Helvetica",
        textColor=colors.gray,
        alignment=TA_CENTER,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="DocTitle",
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceBefore=8,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="SectionHead",
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Body",
        fontSize=10,
        fontName="Helvetica",
        leading=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Disclosure",
        fontSize=8,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#555555"),
        leading=11,
        borderPad=4,
        spaceBefore=12,
    ))
    styles.add(ParagraphStyle(
        name="SmallRight",
        fontSize=8,
        fontName="Helvetica",
        alignment=TA_RIGHT,
        textColor=colors.gray,
    ))
    return styles


def _header_elements(styles, title: str, date_str: str = "") -> list:
    from datetime import date
    date_display = date_str or date.today().strftime("%B %d, %Y")
    elems = [
        Paragraph(COMPANY_NAME, styles["CompanyName"]),
        Paragraph(COMPANY_TAGLINE, styles["CompanyTagline"]),
        Paragraph(
            f"{COMPANY_PHONE} &nbsp;|&nbsp; {COMPANY_EMAIL} &nbsp;|&nbsp; {COMPANY_WEBSITE}",
            styles["CompanyContact"],
        ),
        HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=6),
        Paragraph(title, styles["DocTitle"]),
        Paragraph(f"Date: {date_display}", styles["SmallRight"]),
        Spacer(1, 8),
    ]
    return elems


def _disclosure_element(styles) -> Paragraph:
    text = (
        "<b>NON-ATTORNEY DISCLOSURE:</b> Cruel &amp; Associates is not a law firm and does not "
        "provide legal advice or legal representation. We are not attorneys. All services are "
        "administrative document preparation only. For legal advice, please consult a licensed "
        "attorney. This document does not constitute legal counsel."
    )
    return Paragraph(text, styles["Disclosure"])


def _sig_block_rows(label: str, include_date: bool = True) -> list:
    rows = [
        ["Signature:", ""],
        ["Printed Name:", ""],
        ["Title:", ""],
    ]
    if include_date:
        rows.append(["Date:", ""])
    rows.append([f"— {label} —", ""])
    return rows


def _sig_table(label: str, include_date: bool = True):
    rows = _sig_block_rows(label, include_date)
    t = Table(rows, colWidths=[1.5 * inch, 4 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (1, 0), (1, -2), 0.5, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
    ]))
    return t


def docx_to_pdf(docx_path: str) -> Optional[str]:
    """Convert DOCX to PDF using LibreOffice headless. Returns PDF path or None."""
    pdf_path = docx_path.replace(".docx", ".pdf")
    try:
        result = subprocess.run(
            [
                "libreoffice", "--headless", "--convert-to", "pdf",
                "--outdir", str(Path(docx_path).parent),
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and Path(pdf_path).exists():
            return pdf_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def generate_pdf(document_type: str, data: dict, output_path: Optional[str] = None) -> str:
    """Generate a PDF directly via ReportLab for common document types."""
    from datetime import datetime

    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        client_id = data.get("client_id", "unknown")
        output_path = str(OUTPUT_DIR / f"{document_type}_{client_id}_{ts}.pdf")

    dispatch = {
        "invoice": _pdf_invoice,
        "notary_invoice": _pdf_notary_invoice,
        "receipt": _pdf_receipt,
        "consultation_report": _pdf_consultation_report,
    }

    fn = dispatch.get(document_type, _pdf_generic)
    fn(data, output_path)
    return output_path


def _pdf_invoice(data: dict, out: str):
    styles = _base_styles()
    doc = SimpleDocTemplate(out, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75 * inch, bottomMargin=inch)
    elems = _header_elements(styles, "INVOICE")

    client_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    invoice_num = data.get("invoice_number", data.get("invoice_id", "INV-001"))
    due_date = data.get("due_date", "Upon Receipt")

    info_rows = [
        ["Bill To:", client_name],
        ["", data.get("address", "")],
        ["", f"{data.get('city', '')}, {data.get('state', 'SC')} {data.get('zip_code', '')}"],
        ["Invoice #:", str(invoice_num)],
        ["Due Date:", str(due_date)],
        ["Division:", data.get("division", "").replace("_", " ").title()],
    ]
    info_table = Table(info_rows, colWidths=[1.2 * inch, 4.5 * inch])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(info_table)
    elems.append(Spacer(1, 12))

    line_items = data.get("line_items", [
        {"description": data.get("service_description", "Administrative Services"), "amount": data.get("amount", 0)}
    ])
    item_rows = [["Description", "Amount"]]
    for item in line_items:
        item_rows.append([
            item.get("description", ""),
            f"${item.get('amount', 0):,.2f}",
        ])

    total = data.get("amount", sum(i.get("amount", 0) for i in line_items))
    paid = data.get("paid", 0.0)
    balance = total - paid

    item_rows.append(["", ""])
    item_rows.append(["Subtotal:", f"${total:,.2f}"])
    if paid:
        item_rows.append(["Paid:", f"-${paid:,.2f}"])
    item_rows.append(["Balance Due:", f"${balance:,.2f}"])

    item_table = Table(item_rows, colWidths=[4.5 * inch, 1.5 * inch])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, GOLD),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, GOLD),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -4), [colors.white, LIGHT_GRAY]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(item_table)
    elems.append(Spacer(1, 16))

    notes = data.get("notes", "")
    if notes:
        elems.append(Paragraph("Notes:", styles["SectionHead"]))
        elems.append(Paragraph(notes, styles["Body"]))

    elems.append(Spacer(1, 24))
    elems.append(Paragraph(
        "Payment is due upon receipt unless otherwise agreed. Thank you for choosing Cruel &amp; Associates.",
        styles["Body"],
    ))

    doc.build(elems)


def _pdf_notary_invoice(data: dict, out: str):
    num_acts = int(data.get("num_acts", 1))
    fee_per_act = float(data.get("fee_per_act", 5.0))
    travel_fee = float(data.get("travel_fee", 0.0))
    service_fee = float(data.get("service_fee", 0.0))

    notary_total = num_acts * fee_per_act
    grand_total = notary_total + travel_fee + service_fee

    line_items = [
        {"description": f"Notarial Acts ({num_acts} × ${fee_per_act:.2f}) — SC § 26-1-120", "amount": notary_total},
    ]
    if travel_fee:
        line_items.append({"description": "Travel Fee", "amount": travel_fee})
    if service_fee:
        line_items.append({"description": "Signing Agent Service Fee", "amount": service_fee})

    data = {**data, "line_items": line_items, "amount": grand_total,
            "service_description": "Notary Services"}
    _pdf_invoice(data, out)


def _pdf_receipt(data: dict, out: str):
    data = {**data, "invoice_number": data.get("receipt_number", "REC-001"),
            "paid": data.get("amount", 0), "due_date": "PAID"}
    _pdf_invoice(data, out)


def _pdf_consultation_report(data: dict, out: str):
    styles = _base_styles()
    doc = SimpleDocTemplate(out, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75 * inch, bottomMargin=inch)
    elems = _header_elements(styles, "CONSULTATION REPORT")

    client_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    elems.append(Paragraph(f"Client: {client_name}", styles["Body"]))
    elems.append(Paragraph(f"Division: {data.get('division', '').replace('_', ' ').title()}", styles["Body"]))
    elems.append(Spacer(1, 8))

    for section in ["summary", "recommendations", "next_steps", "action_items"]:
        content = data.get(section, "")
        if content:
            elems.append(Paragraph(section.replace("_", " ").title(), styles["SectionHead"]))
            elems.append(Paragraph(str(content), styles["Body"]))

    elems.append(Spacer(1, 20))
    elems.append(_sig_table("Consultant — Cruel & Associates"))
    elems.append(Spacer(1, 12))
    elems.append(_sig_table("Client"))
    elems.append(Spacer(1, 16))
    elems.append(_disclosure_element(styles))

    doc.build(elems)


def _pdf_generic(data: dict, out: str):
    styles = _base_styles()
    doc = SimpleDocTemplate(out, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75 * inch, bottomMargin=inch)
    title = data.get("title", data.get("document_type", "Document")).replace("_", " ").title()
    elems = _header_elements(styles, title.upper())

    client_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    if client_name:
        elems.append(Paragraph(f"Client: {client_name}", styles["Body"]))

    for key in ["content", "body", "description", "summary"]:
        if data.get(key):
            elems.append(Paragraph(str(data[key]), styles["Body"]))

    elems.append(Spacer(1, 20))
    elems.append(_disclosure_element(styles))

    doc.build(elems)
