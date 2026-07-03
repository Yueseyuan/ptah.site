"""Simple SMTP email sender. Falls back to logging if SMTP is not configured."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

BRAND = "Cruel &amp; Associates"
BRAND_PLAIN = "Cruel & Associates"
CONTACT = "(864) 318-9951 · yueseyuan.cruel@cruelandassociates.site"
PORTAL_URL = "https://cruelandassociates.site/portal"

HEADER = f"""
<div style="font-family:system-ui,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px">
  <div style="font-size:20px;font-weight:800;color:#c9a84c;letter-spacing:1px;margin-bottom:24px">
    {BRAND}
  </div>
"""

FOOTER = f"""
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:28px 0">
  <p style="color:#9ca3af;font-size:12px;line-height:1.6">
    {BRAND_PLAIN} · Consumer Rights Consulting<br>{CONTACT}
  </p>
</div>
"""


def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _send(to_email: str, subject: str, html: str, plain: str) -> None:
    if not _smtp_configured():
        print(f"[EMAIL] SMTP not configured. Would send '{subject}' to {to_email}")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        print(f"[EMAIL] Sent '{subject}' to {to_email}")
    except Exception as exc:
        print(f"[EMAIL] Failed to send '{subject}' to {to_email}: {exc}")


def _btn(url: str, label: str) -> str:
    return (
        f'<div style="text-align:center;margin:28px 0">'
        f'<a href="{url}" style="background:#0a2540;color:#fff;padding:14px 36px;'
        f'border-radius:8px;font-size:15px;font-weight:600;text-decoration:none;'
        f'display:inline-block">{label}</a></div>'
    )


# ── Welcome ───────────────────────────────────────────────────────────────────

def send_welcome_email(to_email: str, first_name: str, case_number: str) -> None:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    subject = "Welcome to Your Cruel & Associates Client Portal"
    html = HEADER + f"""
      <p style="color:#374151;font-size:15px;line-height:1.6">{greeting}</p>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        Your client portal account has been created. Your case number is
        <strong>{case_number}</strong>.
      </p>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        <strong>Next steps to get started:</strong>
      </p>
      <ol style="color:#374151;font-size:14px;line-height:2;padding-left:20px">
        <li>Upload all three credit reports (Experian, Equifax &amp; TransUnion)</li>
        <li>Upload a government-issued photo ID</li>
        <li>Upload proof of address (utility bill, bank statement, etc.)</li>
      </ol>
      <p style="color:#374151;font-size:14px;line-height:1.6">
        We'll review your documents and get your dispute process started. You can
        track your case status, download letters, and message us through your portal at any time.
      </p>
      {_btn(f"{PORTAL_URL}/documents", "Upload My Documents")}
      <p style="color:#6b7280;font-size:13px;line-height:1.6">
        Questions? Reply to this email or call us at (864) 318-9951.
      </p>
    """ + FOOTER
    plain = (
        f"{greeting}\n\nYour portal account is active. Case number: {case_number}\n\n"
        f"Next steps:\n1. Upload all 3 credit reports\n2. Upload a photo ID\n"
        f"3. Upload proof of address\n\nPortal: {PORTAL_URL}/documents\n\n"
        f"{BRAND_PLAIN} · {CONTACT}"
    )
    _send(to_email, subject, html, plain)


# ── Document uploaded (admin alert) ──────────────────────────────────────────

def send_document_uploaded_admin_alert(
    admin_email: str,
    client_name: str,
    client_email: str,
    doc_type: str,
    filename: str,
    case_number: str,
) -> None:
    doc_label = doc_type.replace("_", " ").title()
    subject = f"New Document Uploaded — {client_name} ({case_number})"
    html = HEADER + f"""
      <p style="color:#374151;font-size:15px;line-height:1.6">
        A client has uploaded a new document that needs your review.
      </p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;margin:16px 0">
        <tr style="border-bottom:1px solid #e5e7eb">
          <td style="padding:8px 0;color:#6b7280;width:140px">Client</td>
          <td style="padding:8px 0;font-weight:600">{client_name}</td>
        </tr>
        <tr style="border-bottom:1px solid #e5e7eb">
          <td style="padding:8px 0;color:#6b7280">Email</td>
          <td style="padding:8px 0">{client_email}</td>
        </tr>
        <tr style="border-bottom:1px solid #e5e7eb">
          <td style="padding:8px 0;color:#6b7280">Case</td>
          <td style="padding:8px 0">{case_number}</td>
        </tr>
        <tr style="border-bottom:1px solid #e5e7eb">
          <td style="padding:8px 0;color:#6b7280">Document Type</td>
          <td style="padding:8px 0">{doc_label}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#6b7280">File</td>
          <td style="padding:8px 0">{filename}</td>
        </tr>
      </table>
      {_btn("https://cruelandassociates.site/admin/portal", "Review in Admin Portal")}
    """ + FOOTER
    plain = (
        f"New document uploaded:\n"
        f"Client: {client_name} ({client_email})\n"
        f"Case: {case_number}\n"
        f"Type: {doc_label}\n"
        f"File: {filename}\n\n"
        f"Review: https://cruelandassociates.site/admin/portal\n\n"
        f"{BRAND_PLAIN}"
    )
    _send(admin_email, subject, html, plain)


# ── Document reviewed (client alert) ─────────────────────────────────────────

def send_document_reviewed_email(to_email: str, first_name: str, doc_type: str, filename: str) -> None:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    doc_label = doc_type.replace("_", " ").title()
    subject = "Your Document Has Been Reviewed — Cruel & Associates"
    html = HEADER + f"""
      <p style="color:#374151;font-size:15px;line-height:1.6">{greeting}</p>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        We've reviewed the following document you uploaded:
      </p>
      <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px 18px;margin:20px 0">
        <span style="color:#166534;font-size:14px">
          ✓ <strong>{doc_label}</strong> — {filename}
        </span>
      </div>
      <p style="color:#374151;font-size:14px;line-height:1.6">
        Your case is progressing. Check your portal for updates on your case status
        and any additional documents we may need.
      </p>
      {_btn(f"{PORTAL_URL}/documents", "View My Documents")}
      <p style="color:#6b7280;font-size:13px">
        Questions? Call us at (864) 318-9951 or reply to this email.
      </p>
    """ + FOOTER
    plain = (
        f"{greeting}\n\nWe've reviewed your {doc_label} ({filename}).\n\n"
        f"Check your portal for case updates: {PORTAL_URL}/documents\n\n"
        f"{BRAND_PLAIN} · {CONTACT}"
    )
    _send(to_email, subject, html, plain)


# ── Case status update (client alert) ────────────────────────────────────────

_STATUS_MESSAGES = {
    "pending":      ("Your case is in our queue", "We'll begin review shortly."),
    "docs_needed":  ("Action Required: Documents Needed", "Please log in to your portal and upload the requested documents so we can continue processing your case."),
    "under_review": ("Your Case Is Under Review", "Our team is actively reviewing your credit reports and preparing your dispute strategy."),
    "active":       ("Your Disputes Are Active", "We have begun submitting dispute letters on your behalf. You can track progress and download letters from your portal."),
    "completed":    ("Your Case Is Complete", "We have completed all dispute rounds for your case. Log in to download your final letters and review outcomes."),
}

def send_case_status_update_email(
    to_email: str, first_name: str, portal_status: str, case_number: str
) -> None:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    headline, body_msg = _STATUS_MESSAGES.get(
        portal_status,
        ("Your Case Has Been Updated", "Log in to your portal to see the latest status.")
    )
    status_label = {
        "pending":      "Pending Review",
        "docs_needed":  "Documents Needed",
        "under_review": "Under Review",
        "active":       "Active — Disputes in Progress",
        "completed":    "Completed",
    }.get(portal_status, portal_status.replace("_", " ").title())

    subject = f"Case Update: {status_label} — Cruel & Associates"
    html = HEADER + f"""
      <p style="color:#374151;font-size:15px;line-height:1.6">{greeting}</p>
      <p style="color:#374151;font-size:18px;font-weight:700;color:#0a2540">{headline}</p>
      <p style="color:#374151;font-size:15px;line-height:1.6">{body_msg}</p>
      <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 18px;margin:20px 0">
        <span style="color:#374151;font-size:14px">
          Case <strong>{case_number}</strong> &nbsp;·&nbsp;
          Status: <strong>{status_label}</strong>
        </span>
      </div>
      {_btn(f"{PORTAL_URL}/dashboard", "View My Portal")}
      <p style="color:#6b7280;font-size:13px">
        Questions? Call (864) 318-9951 or reply to this email.
      </p>
    """ + FOOTER
    plain = (
        f"{greeting}\n\n{headline}\n\n{body_msg}\n\n"
        f"Case: {case_number} · Status: {status_label}\n\n"
        f"Portal: {PORTAL_URL}/dashboard\n\n{BRAND_PLAIN} · {CONTACT}"
    )
    _send(to_email, subject, html, plain)


# ── Password reset ────────────────────────────────────────────────────────────

def send_password_reset_email(to_email: str, reset_url: str, first_name: str = "") -> None:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    subject = "Reset Your Cruel & Associates Portal Password"
    html = HEADER + f"""
      <p style="color:#374151;font-size:15px;line-height:1.6">{greeting}</p>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        We received a request to reset your client portal password.
        Click the button below — this link expires in <strong>1 hour</strong>.
      </p>
      {_btn(reset_url, "Reset My Password")}
      <p style="color:#6b7280;font-size:13px">
        If you didn't request this, you can safely ignore this email.
      </p>
    """ + FOOTER
    plain = (
        f"{greeting}\n\nReset your portal password:\n{reset_url}\n\n"
        f"Link expires in 1 hour. If you didn't request this, ignore this email.\n\n"
        f"{BRAND_PLAIN} · {CONTACT}"
    )
    _send(to_email, subject, html, plain)


# ── Billing: subscription confirmed ──────────────────────────────────────────

def send_subscription_confirmed_email(to_email: str, first_name: str, next_billing: str) -> None:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    subject = "You're Subscribed — Cruel & Associates"
    html = HEADER + f"""
      <p style="color:#374151;font-size:15px;line-height:1.6">{greeting}</p>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        Your <strong>Monthly Consulting Retainer</strong> is now active. Here's what's included:
      </p>
      <ul style="color:#374151;font-size:14px;line-height:2;padding-left:20px">
        <li>Credit bureau dispute letters</li>
        <li>Bureau response analysis</li>
        <li>CFPB complaint preparation</li>
        <li>Method of verification requests</li>
        <li>Affidavit of Truth preparation</li>
        <li>Debt collector FDCPA letters</li>
        <li>Failure to investigate escalation</li>
        <li>Ongoing FCRA/FDCPA advisory</li>
      </ul>
      <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px 18px;margin:20px 0">
        <span style="color:#166534;font-size:14px">
          ✓ <strong>$149/month</strong> &nbsp;·&nbsp; Next billing date: <strong>{next_billing}</strong>
        </span>
      </div>
      {_btn(f"{PORTAL_URL}/dashboard", "Go to My Portal")}
      <p style="color:#6b7280;font-size:13px;line-height:1.6">
        To manage or cancel your subscription, visit the
        <a href="{PORTAL_URL}/billing" style="color:#0a2540">Billing page</a> in your portal.
      </p>
    """ + FOOTER
    plain = (
        f"{greeting}\n\nYour Monthly Consulting Retainer ($149/month) is now active.\n"
        f"Next billing date: {next_billing}\n\n"
        f"Manage your subscription: {PORTAL_URL}/billing\n\n"
        f"{BRAND_PLAIN} · {CONTACT}"
    )
    _send(to_email, subject, html, plain)


# ── Billing: payment failed ───────────────────────────────────────────────────

def send_payment_failed_email(to_email: str, first_name: str) -> None:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    subject = "Action Required: Payment Failed — Cruel & Associates"
    html = HEADER + f"""
      <p style="color:#374151;font-size:15px;line-height:1.6">{greeting}</p>
      <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px 18px;margin:20px 0">
        <span style="color:#991b1b;font-size:14px;font-weight:600">
          ⚠ Your recent payment of $149 could not be processed.
        </span>
      </div>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        Your subscription is now past due. Please update your payment method to keep
        your account active and avoid interruption to your services.
      </p>
      {_btn(f"{PORTAL_URL}/billing", "Update Payment Method")}
      <p style="color:#6b7280;font-size:13px;line-height:1.6">
        If you need assistance, reply to this email or call us at (864) 318-9951.
      </p>
    """ + FOOTER
    plain = (
        f"{greeting}\n\nYour recent payment of $149 could not be processed.\n"
        f"Please update your payment method to keep your account active:\n"
        f"{PORTAL_URL}/billing\n\n"
        f"Need help? Call (864) 318-9951.\n\n{BRAND_PLAIN} · {CONTACT}"
    )
    _send(to_email, subject, html, plain)


# ── Billing: subscription cancelled ──────────────────────────────────────────

def send_subscription_cancelled_email(to_email: str, first_name: str, end_date: str) -> None:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    subject = "Subscription Cancelled — Cruel & Associates"
    html = HEADER + f"""
      <p style="color:#374151;font-size:15px;line-height:1.6">{greeting}</p>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        Your Monthly Consulting Retainer has been cancelled. You'll continue to have
        access to your portal and services through <strong>{end_date}</strong>.
      </p>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        If you cancelled by mistake or change your mind, you can resubscribe at any time
        from your portal.
      </p>
      {_btn(f"{PORTAL_URL}/billing", "Resubscribe")}
      <p style="color:#6b7280;font-size:13px;line-height:1.6">
        Thank you for being a client. We hope to work with you again.
        If you have any questions, reply to this email or call (864) 318-9951.
      </p>
    """ + FOOTER
    plain = (
        f"{greeting}\n\nYour Monthly Consulting Retainer has been cancelled.\n"
        f"Access continues through {end_date}.\n\n"
        f"Resubscribe anytime: {PORTAL_URL}/billing\n\n"
        f"{BRAND_PLAIN} · {CONTACT}"
    )
    _send(to_email, subject, html, plain)
