"""
Full automation layer: APScheduler jobs, workflow triggers, email notifications,
auto-document generation on intake, and workflow state machine.
"""
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# ── Division → default documents auto-generated on intake ─────────────────────

DIVISION_AUTO_DOCS = {
    "notary": ["notary_service_agreement"],
    "credit": ["credit_services_agreement"],
    "reentry": ["reentry_service_agreement", "non_attorney_disclosure"],
    "document_prep": ["consultation_report"],
    "asset_recovery": ["asset_research_report"],
    "business": ["llc_checklist"],
}

# ── Workflow state machine ────────────────────────────────────────────────────

WORKFLOW_TRANSITIONS = {
    "active": ["documents_ready", "on_hold", "closed"],
    "documents_ready": ["pending_signature", "closed"],
    "pending_signature": ["signed", "documents_ready"],
    "signed": ["archived", "closed"],
    "archived": [],
    "on_hold": ["active", "closed"],
    "closed": [],
}


def can_transition(current_status: str, new_status: str) -> bool:
    return new_status in WORKFLOW_TRANSITIONS.get(current_status, [])


# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(
    to: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
    html_body: Optional[str] = None,
) -> bool:
    if not all([settings.SMTP_USER, settings.SMTP_PASS]):
        logger.warning("SMTP not configured — email not sent to %s", to)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        if attachments:
            for path in attachments:
                p = Path(path)
                if p.exists():
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(p.read_bytes())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{p.name}"')
                    msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, to, msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_html_email(to: str, subject: str, template_name: str, context: Dict[str, Any]) -> bool:
    """Send a styled HTML email using an inline template."""
    html = _render_email_template(template_name, context)
    plain = context.get("plain_text", subject)
    return send_email(to, subject, plain, html_body=html)


def _render_email_template(template_name: str, ctx: Dict[str, Any]) -> str:
    templates = {
        "intake_confirm": _email_intake_confirm,
        "documents_ready": _email_documents_ready,
        "signature_request": _email_signature_request,
        "appointment_confirm": _email_appointment_confirm,
        "follow_up": _email_follow_up,
        "invoice": _email_invoice,
    }
    fn = templates.get(template_name, _email_generic)
    return fn(ctx)


def _email_base(title: str, body_html: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 30px auto; background: white; border-radius: 8px; overflow: hidden; }}
    .header {{ background: #0d2244; color: white; padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; color: white; }}
    .header p {{ margin: 4px 0 0; font-size: 12px; color: #c49a1a; }}
    .body {{ padding: 28px 32px; color: #333; line-height: 1.6; }}
    .body h2 {{ color: #0d2244; }}
    .footer {{ background: #f9f9f9; padding: 16px 32px; font-size: 11px; color: #888; text-align: center; border-top: 1px solid #eee; }}
    .btn {{ display: inline-block; background: #c49a1a; color: white; padding: 12px 28px; border-radius: 4px; text-decoration: none; margin-top: 16px; font-weight: bold; }}
    .divider {{ border: none; border-top: 2px solid #c49a1a; margin: 20px 0; }}
    .disclosure {{ font-size: 10px; color: #999; font-style: italic; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Cruel &amp; Associates</h1>
      <p>Administrative Services | Document Preparation | Community Reentry</p>
    </div>
    <div class="body">
      <h2>{title}</h2>
      <hr class="divider">
      {body_html}
      <p class="disclosure">
        Cruel &amp; Associates is not a law firm and does not provide legal advice or legal representation.
        All services are administrative document preparation only.
      </p>
    </div>
    <div class="footer">
      {settings.COMPANY_PHONE} | {settings.COMPANY_EMAIL} | {settings.COMPANY_WEBSITE}<br>
      South Carolina | &copy; {datetime.now().year} Cruel &amp; Associates
    </div>
  </div>
</body>
</html>
"""


def _email_intake_confirm(ctx: Dict) -> str:
    name = ctx.get("client_name", "Valued Client")
    division = ctx.get("division", "").replace("_", " ").title()
    case_id = ctx.get("case_id", "")
    return _email_base(
        "Intake Confirmation",
        f"""
        <p>Dear {name},</p>
        <p>Thank you for choosing <strong>Cruel &amp; Associates</strong>. We have received your intake
        information for our <strong>{division}</strong> services.</p>
        <p><strong>Case Reference:</strong> #{case_id}</p>
        <p>Our team will review your information and reach out within 1-2 business days to discuss
        next steps. In the meantime, please gather any relevant documents we may have requested.</p>
        <p>If you have any immediate questions, please contact us at {settings.COMPANY_PHONE}.</p>
        <p>Best regards,<br><strong>Cruel &amp; Associates</strong></p>
        """,
    )


def _email_documents_ready(ctx: Dict) -> str:
    name = ctx.get("client_name", "Valued Client")
    docs = ctx.get("documents", [])
    doc_list = "".join(f"<li>{d}</li>" for d in docs) if docs else "<li>Your prepared documents</li>"
    return _email_base(
        "Your Documents Are Ready",
        f"""
        <p>Dear {name},</p>
        <p>Great news! Your administrative documents have been prepared and are ready for your review.</p>
        <p><strong>Documents Ready:</strong></p>
        <ul>{doc_list}</ul>
        <p>Please review the attached documents carefully. If you need any revisions or have questions,
        reply to this email or call us at {settings.COMPANY_PHONE}.</p>
        <p>Best regards,<br><strong>Cruel &amp; Associates</strong></p>
        """,
    )


def _email_signature_request(ctx: Dict) -> str:
    name = ctx.get("client_name", "Valued Client")
    sign_url = ctx.get("sign_url", "")
    expires = ctx.get("expires", "7 days")
    body = f"""
        <p>Dear {name},</p>
        <p>Your documents are ready for electronic signature. Please review and sign at your earliest
        convenience — the signing link expires in <strong>{expires}</strong>.</p>
    """
    if sign_url:
        body += f'<p><a href="{sign_url}" class="btn">Sign Documents Now</a></p>'
    body += f"""
        <p>If you prefer to sign in person or have any questions, please contact us at
        {settings.COMPANY_PHONE}.</p>
        <p>Best regards,<br><strong>Cruel &amp; Associates</strong></p>
    """
    return _email_base("Documents Ready for Signature", body)


def _email_appointment_confirm(ctx: Dict) -> str:
    name = ctx.get("client_name", "Valued Client")
    scheduled_at = ctx.get("scheduled_at", "")
    apt_type = ctx.get("appointment_type", "consultation").title()
    division = ctx.get("division", "").replace("_", " ").title()
    duration = ctx.get("duration_minutes", 30)
    return _email_base(
        "Appointment Confirmed",
        f"""
        <p>Dear {name},</p>
        <p>Your appointment has been confirmed with Cruel &amp; Associates.</p>
        <table style="border-collapse:collapse; width:100%; margin:12px 0;">
          <tr><td style="padding:6px 0; font-weight:bold; width:40%">Type:</td><td>{apt_type}</td></tr>
          <tr><td style="padding:6px 0; font-weight:bold;">Division:</td><td>{division}</td></tr>
          <tr><td style="padding:6px 0; font-weight:bold;">Date &amp; Time:</td><td>{scheduled_at}</td></tr>
          <tr><td style="padding:6px 0; font-weight:bold;">Duration:</td><td>{duration} minutes</td></tr>
        </table>
        <p>Please arrive a few minutes early or be ready for your call. If you need to reschedule,
        contact us at least 24 hours in advance at {settings.COMPANY_PHONE}.</p>
        <p>Best regards,<br><strong>Cruel &amp; Associates</strong></p>
        """,
    )


def _email_follow_up(ctx: Dict) -> str:
    name = ctx.get("client_name", "Valued Client")
    status = ctx.get("case_status", "In Progress")
    steps = ctx.get("next_steps", [])
    steps_html = "".join(f"<li>{s}</li>" for s in steps) if steps else ""
    body = f"""
        <p>Dear {name},</p>
        <p>We wanted to follow up on your case with Cruel &amp; Associates.</p>
        <p><strong>Current Status:</strong> {status}</p>
    """
    if steps_html:
        body += f"<p><strong>Next Steps:</strong></p><ul>{steps_html}</ul>"
    body += f"""
        <p>Please don't hesitate to reach out if you have any questions or need assistance.</p>
        <p>Best regards,<br><strong>Cruel &amp; Associates</strong></p>
    """
    return _email_base("Case Status Update", body)


def _email_invoice(ctx: Dict) -> str:
    name = ctx.get("client_name", "Valued Client")
    amount = ctx.get("amount", 0)
    invoice_id = ctx.get("invoice_id", "")
    due_date = ctx.get("due_date", "Upon Receipt")
    return _email_base(
        "Invoice",
        f"""
        <p>Dear {name},</p>
        <p>Please find your invoice from Cruel &amp; Associates attached to this email.</p>
        <table style="border-collapse:collapse; margin:12px 0;">
          <tr><td style="padding:6px 12px 6px 0; font-weight:bold;">Invoice #:</td><td>INV-{invoice_id}</td></tr>
          <tr><td style="padding:6px 12px 6px 0; font-weight:bold;">Amount Due:</td><td>${amount:,.2f}</td></tr>
          <tr><td style="padding:6px 12px 6px 0; font-weight:bold;">Due Date:</td><td>{due_date}</td></tr>
        </table>
        <p>If you have any questions about this invoice, please contact us at {settings.COMPANY_PHONE}.</p>
        <p>Thank you for your business!</p>
        <p>Best regards,<br><strong>Cruel &amp; Associates</strong></p>
        """,
    )


def _email_generic(ctx: Dict) -> str:
    return _email_base(
        ctx.get("title", "Update from Cruel & Associates"),
        ctx.get("body_html", f"<p>{ctx.get('body', '')}</p>"),
    )


# ── Workflow triggers ─────────────────────────────────────────────────────────

def on_intake_complete(case_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Triggered after a new case intake is saved.
    1. Run AI analysis on intake data
    2. Auto-generate division default documents
    3. Send confirmation email to client
    """
    from app.models import Case, Client, Document
    from app.services.doc_generator import generate as gen_doc
    from app.services.ai_service import generate_intake_summary

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    results = {"case_id": case_id, "documents": [], "email_sent": False, "ai_analysis": None}

    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return results

        client = db.query(Client).filter(Client.id == case.client_id).first()
        intake_data = json.loads(case.intake_data or "{}")

        # AI analysis
        try:
            summary = generate_intake_summary(case.division, intake_data)
            case.ai_analysis = json.dumps(summary)
            db.commit()
            results["ai_analysis"] = summary
        except Exception as e:
            logger.warning("AI analysis failed for case %s: %s", case_id, e)

        # Auto-generate default documents
        doc_types = DIVISION_AUTO_DOCS.get(case.division, [])
        for doc_type in doc_types:
            try:
                doc_data = {
                    "client_id": client.id,
                    "first_name": client.first_name,
                    "last_name": client.last_name,
                    "email": client.email,
                    "phone": client.phone,
                    "address": client.address,
                    "city": client.city,
                    "state": client.state,
                    "zip_code": client.zip_code,
                    "dob": client.dob,
                    "ssn_last4": client.ssn_last4,
                    **intake_data,
                }
                file_path = gen_doc(doc_type, doc_data)
                paths = file_path if isinstance(file_path, list) else [file_path]
                for path in paths:
                    doc = Document(
                        case_id=case_id,
                        document_type=doc_type,
                        label=doc_type.replace("_", " ").title(),
                        file_path=path,
                        status="draft",
                    )
                    db.add(doc)
                results["documents"].append(doc_type)
            except Exception as e:
                logger.error("Doc gen failed for %s on case %s: %s", doc_type, case_id, e)

        db.commit()

        # Send confirmation email
        if client and client.email:
            results["email_sent"] = send_html_email(
                to=client.email,
                subject="Intake Confirmation — Cruel & Associates",
                template_name="intake_confirm",
                context={
                    "client_name": f"{client.first_name} {client.last_name}",
                    "division": case.division,
                    "case_id": case_id,
                },
            )

    finally:
        if close_db:
            db.close()

    return results


def on_documents_ready(case_id: int, document_ids: List[int], db: Optional[Session] = None) -> bool:
    """Notify client that documents are ready for review."""
    from app.models import Case, Client, Document

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return False
        client = db.query(Client).filter(Client.id == case.client_id).first()
        if not client or not client.email:
            return False

        docs = db.query(Document).filter(Document.id.in_(document_ids)).all()
        doc_labels = [d.label or d.document_type for d in docs]
        attachments = [d.pdf_path or d.file_path for d in docs if (d.pdf_path or d.file_path)]

        case.status = "documents_ready"
        db.commit()

        return send_html_email(
            to=client.email,
            subject="Your Documents Are Ready — Cruel & Associates",
            template_name="documents_ready",
            context={
                "client_name": f"{client.first_name} {client.last_name}",
                "documents": doc_labels,
            },
        )
    finally:
        if close_db:
            db.close()


def on_appointment_scheduled(appointment_id: int, db: Optional[Session] = None) -> bool:
    """Send appointment confirmation email."""
    from app.models import Appointment, Client

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not apt:
            return False
        client = db.query(Client).filter(Client.id == apt.client_id).first()
        if not client or not client.email:
            return False

        scheduled_str = apt.scheduled_at.strftime("%A, %B %d, %Y at %I:%M %p") if apt.scheduled_at else "TBD"

        return send_html_email(
            to=client.email,
            subject="Appointment Confirmed — Cruel & Associates",
            template_name="appointment_confirm",
            context={
                "client_name": f"{client.first_name} {client.last_name}",
                "scheduled_at": scheduled_str,
                "appointment_type": apt.appointment_type,
                "division": apt.division,
                "duration_minutes": apt.duration_minutes,
            },
        )
    finally:
        if close_db:
            db.close()


def on_invoice_created(invoice_id: int, db: Optional[Session] = None) -> bool:
    """Email invoice to client."""
    from app.models import Invoice, Client
    from app.services.pdf_generator import generate_pdf

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return False
        client = db.query(Client).filter(Client.id == invoice.client_id).first()
        if not client or not client.email:
            return False

        pdf_path = generate_pdf("invoice", {
            "client_id": client.id,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "address": client.address,
            "city": client.city,
            "state": client.state,
            "zip_code": client.zip_code,
            "invoice_id": invoice.id,
            "amount": invoice.amount,
            "paid": invoice.paid,
            "due_date": invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "Upon Receipt",
            "notes": invoice.notes,
        })

        return send_html_email(
            to=client.email,
            subject=f"Invoice INV-{invoice.id} — Cruel & Associates",
            template_name="invoice",
            context={
                "client_name": f"{client.first_name} {client.last_name}",
                "amount": invoice.amount,
                "invoice_id": invoice.id,
                "due_date": invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "Upon Receipt",
            },
        )
    finally:
        if close_db:
            db.close()


# ── Scheduled jobs ────────────────────────────────────────────────────────────

def job_appointment_reminders():
    """Send 24-hour appointment reminders."""
    from app.models import Appointment, Client

    db = SessionLocal()
    try:
        window_start = datetime.utcnow() + timedelta(hours=23)
        window_end = datetime.utcnow() + timedelta(hours=25)
        upcoming = (
            db.query(Appointment)
            .filter(
                Appointment.status == "scheduled",
                Appointment.scheduled_at >= window_start,
                Appointment.scheduled_at <= window_end,
            )
            .all()
        )
        for apt in upcoming:
            client = db.query(Client).filter(Client.id == apt.client_id).first()
            if client and client.email:
                scheduled_str = apt.scheduled_at.strftime("%A, %B %d, %Y at %I:%M %p")
                send_html_email(
                    to=client.email,
                    subject="Appointment Reminder — Tomorrow — Cruel & Associates",
                    template_name="appointment_confirm",
                    context={
                        "client_name": f"{client.first_name} {client.last_name}",
                        "scheduled_at": scheduled_str,
                        "appointment_type": apt.appointment_type,
                        "division": apt.division,
                        "duration_minutes": apt.duration_minutes,
                    },
                )
        logger.info("Sent %d appointment reminders", len(upcoming))
    except Exception as e:
        logger.error("Appointment reminders job failed: %s", e)
    finally:
        db.close()


def job_follow_up_stale_cases():
    """Follow up on cases with no activity in 7 days."""
    from app.models import Case, Client

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        stale = (
            db.query(Case)
            .filter(
                Case.status == "active",
                Case.updated_at <= cutoff,
            )
            .all()
        )
        for case in stale:
            client = db.query(Client).filter(Client.id == case.client_id).first()
            if client and client.email:
                send_html_email(
                    to=client.email,
                    subject="Checking In — Cruel & Associates",
                    template_name="follow_up",
                    context={
                        "client_name": f"{client.first_name} {client.last_name}",
                        "case_status": case.status.replace("_", " ").title(),
                        "next_steps": ["Please contact our office if you have any questions or updates."],
                    },
                )
        logger.info("Sent %d stale case follow-ups", len(stale))
    except Exception as e:
        logger.error("Stale case follow-up job failed: %s", e)
    finally:
        db.close()


def job_invoice_reminders():
    """Send reminders for overdue invoices."""
    from app.models import Invoice, Client

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        overdue = (
            db.query(Invoice)
            .filter(
                Invoice.status == "pending",
                Invoice.due_date <= now,
                Invoice.paid < Invoice.amount,
            )
            .all()
        )
        for invoice in overdue:
            client = db.query(Client).filter(Client.id == invoice.client_id).first()
            if client and client.email:
                balance = (invoice.amount or 0) - (invoice.paid or 0)
                send_html_email(
                    to=client.email,
                    subject=f"Payment Reminder — INV-{invoice.id} — Cruel & Associates",
                    template_name="invoice",
                    context={
                        "client_name": f"{client.first_name} {client.last_name}",
                        "amount": balance,
                        "invoice_id": invoice.id,
                        "due_date": "OVERDUE",
                    },
                )
        logger.info("Sent %d invoice reminders", len(overdue))
    except Exception as e:
        logger.error("Invoice reminder job failed: %s", e)
    finally:
        db.close()


def job_daily_digest():
    """Send daily digest to admin email."""
    from app.models import Case, Client, Appointment, Invoice

    db = SessionLocal()
    try:
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)

        new_cases = db.query(Case).filter(Case.created_at >= datetime.combine(today, datetime.min.time())).count()
        active_cases = db.query(Case).filter(Case.status == "active").count()
        todays_apts = db.query(Appointment).filter(
            Appointment.scheduled_at >= datetime.combine(today, datetime.min.time()),
            Appointment.scheduled_at < datetime.combine(tomorrow, datetime.min.time()),
        ).count()
        pending_invoices = db.query(Invoice).filter(Invoice.status == "pending").count()

        subject = f"Daily Digest — {today.strftime('%B %d, %Y')} — Cruel & Associates"
        body = (
            f"Daily Summary for {today.strftime('%B %d, %Y')}\n\n"
            f"New Cases Today: {new_cases}\n"
            f"Active Cases Total: {active_cases}\n"
            f"Appointments Today: {todays_apts}\n"
            f"Pending Invoices: {pending_invoices}\n\n"
            f"Log in to the CA Engine dashboard for full details."
        )

        if settings.SMTP_USER:
            send_email(settings.SMTP_USER, subject, body)

        logger.info("Daily digest sent")
    except Exception as e:
        logger.error("Daily digest job failed: %s", e)
    finally:
        db.close()


# ── Scheduler ────────────────────────────────────────────────────────────────

_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="America/New_York")
    return _scheduler


def start_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        return

    # Appointment reminders: hourly
    scheduler.add_job(
        job_appointment_reminders,
        trigger=IntervalTrigger(hours=1),
        id="appointment_reminders",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Stale case follow-ups: daily at 10am ET
    scheduler.add_job(
        job_follow_up_stale_cases,
        trigger=CronTrigger(hour=10, minute=0, timezone="America/New_York"),
        id="stale_case_followup",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Invoice reminders: daily at 9am ET
    scheduler.add_job(
        job_invoice_reminders,
        trigger=CronTrigger(hour=9, minute=0, timezone="America/New_York"),
        id="invoice_reminders",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Daily digest: 8am ET
    scheduler.add_job(
        job_daily_digest,
        trigger=CronTrigger(hour=8, minute=0, timezone="America/New_York"),
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.start()
    logger.info("Automation scheduler started")


def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Automation scheduler stopped")
