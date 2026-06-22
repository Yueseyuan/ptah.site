"""Simple SMTP email sender. Falls back to logging the URL if SMTP is not configured."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_password_reset_email(to_email: str, reset_url: str, first_name: str = "") -> None:
    subject = "Reset Your Cruel & Associates Portal Password"
    greeting = f"Hi {first_name}," if first_name else "Hi,"

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px">
      <div style="font-size:20px;font-weight:800;color:#c9a84c;letter-spacing:1px;margin-bottom:8px">
        CRUEL &amp; ASSOCIATES
      </div>
      <p style="color:#374151;font-size:15px;line-height:1.6">{greeting}</p>
      <p style="color:#374151;font-size:15px;line-height:1.6">
        We received a request to reset the password for your client portal account.
        Click the button below to choose a new password. This link expires in <strong>1 hour</strong>.
      </p>
      <div style="text-align:center;margin:32px 0">
        <a href="{reset_url}" style="background:#0a2540;color:#fff;padding:14px 36px;border-radius:8px;
           font-size:15px;font-weight:600;text-decoration:none;display:inline-block">
          Reset My Password
        </a>
      </div>
      <p style="color:#6b7280;font-size:13px;line-height:1.6">
        If you did not request a password reset, you can safely ignore this email.
        Your password will not change until you click the link above.
      </p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
      <p style="color:#9ca3af;font-size:12px">
        Cruel &amp; Associates · Consumer Rights Consulting<br>
        (864) 318-9951 · yueseyuan.cruel@cruelandassociates.site
      </p>
    </div>
    """

    plain = (
        f"{greeting}\n\n"
        f"Reset your Cruel & Associates portal password by visiting:\n{reset_url}\n\n"
        f"This link expires in 1 hour. If you did not request this, ignore this email.\n\n"
        f"Cruel & Associates · (864) 318-9951"
    )

    if not _smtp_configured():
        print(f"[PASSWORD RESET] SMTP not configured. Reset URL for {to_email}: {reset_url}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=ctx)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
