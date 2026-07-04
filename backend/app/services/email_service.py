"""Email sending via SendGrid REST API."""
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SENDGRID_API = "https://api.sendgrid.com/v3/mail/send"


async def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: str | None = None,
    html: bool = True,
) -> dict[str, Any]:
    """Send an email via SendGrid. Returns {"ok": True} or {"ok": False, "error": ...}."""
    if not settings.sendgrid_api_key:
        return {"ok": False, "error": "SENDGRID_API_KEY not configured in .env"}

    sender = from_email or settings.sendgrid_from_email
    content_type = "text/html" if html else "text/plain"

    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": sender},
        "subject": subject,
        "content": [{"type": content_type, "value": body}],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            SENDGRID_API,
            json=payload,
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
        )

    if resp.status_code in (200, 202):
        logger.info("Email sent to %s (subject: %s)", to, subject)
        return {"ok": True, "status": resp.status_code}

    logger.error("SendGrid error %d: %s", resp.status_code, resp.text)
    return {"ok": False, "error": f"SendGrid {resp.status_code}: {resp.text[:200]}"}


async def send_campaign(
    recipients: list[str],
    subject: str,
    body: str,
    from_email: str | None = None,
) -> dict[str, Any]:
    """Send a campaign to multiple recipients (one email per address)."""
    results = {"sent": 0, "failed": 0, "errors": []}
    for addr in recipients:
        r = await send_email(addr, subject, body, from_email)
        if r["ok"]:
            results["sent"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({"to": addr, "error": r["error"]})
    return results
