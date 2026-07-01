"""Document service — template rendering, PDF generation, and client variable extraction."""
import os
import re
from datetime import date
from typing import Optional

from app.models import AegisClient, ServiceCase


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def render_template(template_content: str, variables: dict) -> str:
    """Replace {{var}} placeholders in template_content with values from variables dict.

    Unknown placeholders are left as-is. Variable names are matched case-insensitively.
    """
    def _replace(match: re.Match) -> str:
        key = match.group(1).strip()
        # Try exact key first, then lower-cased key
        if key in variables:
            return str(variables[key])
        if key.lower() in {k.lower(): k for k in variables}:
            mapped = {k.lower(): k for k in variables}[key.lower()]
            return str(variables[mapped])
        return match.group(0)  # leave placeholder unchanged

    return re.sub(r"\{\{([^}]+)\}\}", _replace, template_content)


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def generate_pdf_from_text(title: str, content: str, output_path: str) -> str:
    """Generate a clean professional PDF and save it to output_path.

    Returns the absolute path to the generated PDF file.

    The PDF includes:
    - Header with "Cruel & Associates" firm name
    - Document title
    - Body text with automatic word-wrap
    - Footer with page numbers and generation date
    """
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak
    )
    from reportlab.platypus.frames import Frame
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    today_str = date.today().strftime("%B %d, %Y")
    page_width, page_height = LETTER

    # ── styles ──────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    firm_style = ParagraphStyle(
        "FirmName",
        parent=styles["Normal"],
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a1a2e"),
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    tagline_style = ParagraphStyle(
        "Tagline",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a1a2e"),
        alignment=TA_CENTER,
        spaceAfter=14,
        spaceBefore=6,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica",
        leading=15,
        textColor=colors.HexColor("#222222"),
        spaceAfter=8,
    )

    # ── footer callback ──────────────────────────────────────────────────────
    def _add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        footer_text = f"Page {doc.page}  •  Generated {today_str}  •  Cruel & Associates"
        canvas.drawCentredString(page_width / 2.0, 0.45 * inch, footer_text)
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.line(inch, 0.65 * inch, page_width - inch, 0.65 * inch)
        canvas.restoreState()

    # ── document ─────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )

    story = []

    # Header
    story.append(Paragraph("Cruel &amp; Associates", firm_style))
    story.append(Paragraph("Professional Services &bull; Document Preparation &bull; Credit Restoration", tagline_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a1a2e"), spaceAfter=12))

    # Title
    story.append(Paragraph(title, title_style))
    story.append(HRFlowable(width="60%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=16))

    # Body — split on newlines, treating each non-empty line as a paragraph
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            # Escape special ReportLab XML characters
            safe = (
                stripped
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            story.append(Paragraph(safe, body_style))
        else:
            story.append(Spacer(1, 6))

    doc.build(story, onFirstPage=_add_footer, onLaterPages=_add_footer)
    return os.path.abspath(output_path)


# ---------------------------------------------------------------------------
# Client template variable extraction
# ---------------------------------------------------------------------------

def get_client_template_vars(client: AegisClient, case: Optional[ServiceCase] = None) -> dict:
    """Return a flat dict of standard template variables extracted from an AegisClient.

    Optionally include variables from an associated ServiceCase.
    All keys use lowercase_underscore naming to match {{placeholder}} conventions.
    """
    full_name = f"{client.first_name or ''} {client.last_name or ''}".strip()

    vars_: dict = {
        # Identity
        "first_name": client.first_name or "",
        "last_name": client.last_name or "",
        "full_name": full_name,
        "email": client.email or "",
        "phone": client.phone or "",
        "dob": client.dob or "",
        "ssn_last4": client.ssn_last4 or "",
        # Address
        "address": client.address or "",
        "city": client.city or "",
        "state": client.state or "",
        "zip_code": client.zip_code or "",
        "full_address": ", ".join(
            part for part in [
                client.address,
                client.city,
                f"{client.state} {client.zip_code}".strip() if client.state or client.zip_code else "",
            ]
            if part
        ),
        # Meta
        "today": date.today().strftime("%B %d, %Y"),
        "today_short": date.today().strftime("%m/%d/%Y"),
        "firm_name": "Cruel & Associates",
    }

    if case is not None:
        vars_.update({
            "case_number": case.case_number or "",
            "division": case.division_slug or "",
            "case_status": case.status or "",
            "case_title": case.title or "",
            "assigned_to": case.assigned_to or "",
        })

    return vars_
