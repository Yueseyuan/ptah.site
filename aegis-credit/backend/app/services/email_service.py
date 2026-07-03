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
