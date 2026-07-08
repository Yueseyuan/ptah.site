"""Communication channel adapters — Telegram, Discord, Slack, generic webhooks, WhatsApp, Email.

Telegram: full bidirectional bot (receive messages → run Chief → reply).
WhatsApp: Meta Cloud API bidirectional (receive messages → run Chief → reply).
Email: SMTP send + IMAP polling receive → run Chief → reply.
Discord/Slack/Generic: outbound-only webhook notifications.
"""
import asyncio
import email as email_lib
import hashlib
import imaplib
import logging
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


# ── Telegram ──────────────────────────────────────────────────────────────────

async def telegram_send(bot_token: str, chat_id: str | int, text: str) -> bool:
    """Send a text message to a Telegram chat."""
    url = _TELEGRAM_API.format(token=bot_token, method="sendMessage")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
            data = resp.json()
            if not data.get("ok"):
                logger.warning("Telegram sendMessage failed: %s", data)
                return False
            return True
    except Exception as exc:
        logger.error("Telegram send error: %s", exc)
        return False


async def telegram_send_typing(bot_token: str, chat_id: str | int) -> None:
    url = _TELEGRAM_API.format(token=bot_token, method="sendChatAction")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json={"chat_id": chat_id, "action": "typing"})
    except Exception:
        pass


async def telegram_set_webhook(bot_token: str, webhook_url: str, secret_token: str) -> dict[str, Any]:
    """Register a webhook URL with Telegram's Bot API."""
    url = _TELEGRAM_API.format(token=bot_token, method="setWebhook")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={
                "url": webhook_url,
                "secret_token": secret_token,
                "allowed_updates": ["message", "edited_message"],
                "drop_pending_updates": True,
            })
            return resp.json()
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


async def telegram_delete_webhook(bot_token: str) -> dict[str, Any]:
    url = _TELEGRAM_API.format(token=bot_token, method="deleteWebhook")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"drop_pending_updates": False})
            return resp.json()
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


async def telegram_get_me(bot_token: str) -> dict[str, Any]:
    url = _TELEGRAM_API.format(token=bot_token, method="getMe")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            return resp.json()
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


# ── Discord / Slack / Generic webhooks ───────────────────────────────────────

async def webhook_send(webhook_url: str, message: str, channel_type: str = "generic_webhook") -> bool:
    """POST a message to a Discord, Slack, or generic webhook URL."""
    if channel_type == "discord_webhook":
        payload = {"content": message[:2000]}
    elif channel_type == "slack_webhook":
        payload = {"text": message}
    else:
        payload = {"text": message, "message": message}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(webhook_url, json=payload)
            # Discord returns 204; Slack returns "ok"
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error("Webhook send error (%s): %s", channel_type, exc)
        return False


# ── Unified send ─────────────────────────────────────────────────────────────

async def send_to_channel(channel_config: dict[str, Any], channel_type: str, message: str) -> bool:
    """Route a message to the appropriate adapter."""
    if channel_type == "telegram":
        token = channel_config.get("bot_token", "")
        chat_id = channel_config.get("default_chat_id", "")
        if not token or not chat_id:
            logger.warning("Telegram channel missing bot_token or default_chat_id")
            return False
        return await telegram_send(token, chat_id, message)

    if channel_type in ("discord_webhook", "slack_webhook", "generic_webhook"):
        webhook_url = channel_config.get("webhook_url", "")
        if not webhook_url:
            return False
        return await webhook_send(webhook_url, message, channel_type)

    if channel_type == "whatsapp":
        return await whatsapp_send(
            phone_number_id=channel_config.get("phone_number_id", ""),
            access_token=channel_config.get("access_token", ""),
            to=channel_config.get("default_to", ""),
            text=message,
        )

    if channel_type == "email":
        return await email_send(
            smtp_host=channel_config.get("smtp_host", ""),
            smtp_port=int(channel_config.get("smtp_port", 587)),
            smtp_user=channel_config.get("smtp_user", ""),
            smtp_password=channel_config.get("smtp_password", ""),
            from_email=channel_config.get("from_email", channel_config.get("smtp_user", "")),
            to_email=channel_config.get("default_to", ""),
            subject="APEX AI",
            body=message,
        )

    logger.warning("Unknown channel type: %s", channel_type)
    return False


# ── WhatsApp Cloud API ────────────────────────────────────────────────────────

_WHATSAPP_API = "https://graph.facebook.com/v20.0/{phone_number_id}/messages"


async def whatsapp_send(
    phone_number_id: str, access_token: str, to: str, text: str
) -> bool:
    if not phone_number_id or not access_token or not to:
        logger.warning("WhatsApp channel missing phone_number_id, access_token, or default_to")
        return False
    url = _WHATSAPP_API.format(phone_number_id=phone_number_id)
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:4096]},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning("WhatsApp send failed %d: %s", resp.status_code, resp.text[:200])
                return False
            return True
    except Exception as exc:
        logger.error("WhatsApp send error: %s", exc)
        return False


async def handle_whatsapp_update(body: dict[str, Any], channel_id: int) -> None:
    """Process an inbound WhatsApp message → Chief → reply."""
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return
        msg = messages[0]
        from_number = msg.get("from", "")
        text = (msg.get("text") or {}).get("body", "").strip()
        if not text:
            return
    except (IndexError, KeyError):
        return

    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.channel import Channel
    from app.services.chief import run_chief

    async with AsyncSessionLocal() as db:
        ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()

    if not ch or not ch.enabled:
        return

    phone_number_id = ch.config.get("phone_number_id", "")
    access_token = ch.config.get("access_token", "")
    if not phone_number_id or not access_token:
        return

    try:
        async with AsyncSessionLocal() as db:
            result = await run_chief(goal=text, db=db, triggered_by_id=ch.created_by_id)
    except Exception as exc:
        logger.error("Chief failed for WhatsApp message: %s", exc)
        await whatsapp_send(phone_number_id, access_token, from_number, f"⚠️ Error: {exc}")
        return

    output = result.get("merged_output") or "✅ Task completed."
    for chunk in _split_message(output, 4000):
        await whatsapp_send(phone_number_id, access_token, from_number, chunk)


# ── Email (SMTP send + IMAP polling) ─────────────────────────────────────────

async def email_send(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    if not smtp_host or not smtp_user or not smtp_password or not to_email:
        logger.warning("Email channel missing SMTP config or recipient")
        return False

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or smtp_user
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email or smtp_user, to_email, msg.as_string())

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send)
        return True
    except Exception as exc:
        logger.error("Email send error: %s", exc)
        return False


async def poll_email_channel(channel_id: int) -> None:
    """Poll IMAP for unseen emails → run Chief → reply. Called by APScheduler."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.channel import Channel
    from app.services.chief import run_chief

    async with AsyncSessionLocal() as db:
        ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()

    if not ch or not ch.enabled:
        return

    cfg = ch.config
    imap_host = cfg.get("imap_host", "")
    imap_port = int(cfg.get("imap_port", 993))
    smtp_user = cfg.get("smtp_user", "")
    smtp_password = cfg.get("smtp_password", "")
    from_email = cfg.get("from_email", smtp_user)
    smtp_host = cfg.get("smtp_host", "")
    smtp_port = int(cfg.get("smtp_port", 587))

    if not imap_host or not smtp_user or not smtp_password:
        return

    def _fetch_unseen() -> list[tuple[str, str, str]]:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(smtp_user, smtp_password)
        mail.select("inbox")
        _, uids = mail.search(None, "UNSEEN")
        results = []
        for uid in (uids[0] or b"").split():
            _, data = mail.fetch(uid, "(RFC822)")
            raw = data[0][1] if data and data[0] else None
            if not raw:
                continue
            parsed = email_lib.message_from_bytes(raw)
            subject = parsed.get("Subject", "")
            sender = parsed.get("From", "")
            body = ""
            if parsed.is_multipart():
                for part in parsed.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = parsed.get_payload(decode=True).decode("utf-8", errors="replace")
            mail.store(uid, "+FLAGS", "\\Seen")
            results.append((sender, subject, body.strip()))
        mail.close()
        mail.logout()
        return results

    try:
        emails = await asyncio.get_event_loop().run_in_executor(None, _fetch_unseen)
    except Exception as exc:
        logger.error("IMAP poll error (channel %d): %s", channel_id, exc)
        return

    for sender, subject, body in emails:
        if not body:
            continue
        goal = f"Email from {sender} — Subject: {subject}\n\n{body}"
        try:
            async with AsyncSessionLocal() as db:
                result = await run_chief(goal=goal, db=db, triggered_by_id=ch.created_by_id)
        except Exception as exc:
            logger.error("Chief failed for email: %s", exc)
            continue

        reply_body = result.get("merged_output") or "✅ Task completed."
        await email_send(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            from_email=from_email,
            to_email=sender,
            subject=f"Re: {subject}",
            body=reply_body,
        )


# ── Webhook ingress (Telegram → Chief) ───────────────────────────────────────

def make_telegram_secret_token(bot_token: str) -> str:
    """Derive a stable 32-hex secret from the bot token (for use as Telegram's secret_token)."""
    return hashlib.sha256(bot_token.encode()).hexdigest()[:32]


async def handle_telegram_update(update: dict[str, Any], channel_id: int) -> None:
    """Process an incoming Telegram update: extract message → Chief → reply."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.channel import Channel
    from app.services.chief import run_chief

    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    if not chat_id or not text or text.startswith("/"):
        # Ignore commands and non-text messages silently
        if text.startswith("/start"):
            async with AsyncSessionLocal() as db:
                ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
                if ch and ch.enabled:
                    token = ch.config.get("bot_token", "")
                    if token:
                        await telegram_send(token, chat_id, "👋 *APEX AI* connected. Send me a goal and I'll get to work.")
        return

    # Check allowed chat IDs if configured
    async with AsyncSessionLocal() as db:
        ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()

    if not ch or not ch.enabled:
        return

    allowed = ch.config.get("allowed_chat_ids", [])
    if allowed and str(chat_id) not in [str(i) for i in allowed]:
        logger.warning("Telegram update from unauthorized chat_id %s", chat_id)
        return

    bot_token = ch.config.get("bot_token", "")
    if not bot_token:
        return

    # Show typing indicator while Chief runs
    await telegram_send_typing(bot_token, chat_id)

    try:
        async with AsyncSessionLocal() as db:
            result = await run_chief(goal=text, db=db, triggered_by_id=ch.created_by_id)
    except Exception as exc:
        logger.error("Chief failed for Telegram message: %s", exc)
        await telegram_send(bot_token, chat_id, f"⚠️ Error: {exc}")
        return

    # Format response
    output = result.get("merged_output") or ""
    if not output and result.get("subtasks"):
        output = "\n\n".join(
            f"**{s['title']}**\n{s.get('output', '')}" for s in result["subtasks"] if s.get("output")
        )
    if not output:
        output = "✅ Task completed."

    # Telegram message limit is 4096 chars
    for chunk in _split_message(output, 4000):
        await telegram_send(bot_token, chat_id, chunk)


async def start_email_polling() -> None:
    """Register APScheduler interval jobs for all enabled email channels. Called at startup."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.channel import Channel
    from app.services.scheduler_service import get_scheduler

    async with AsyncSessionLocal() as db:
        channels = list(
            (await db.execute(
                select(Channel).where(Channel.channel_type == "email", Channel.enabled.is_(True))
            )).scalars().all()
        )

    scheduler = get_scheduler()
    for ch in channels:
        interval_minutes = max(1, int(ch.config.get("poll_interval_minutes", 5)))
        job_id = f"email_poll_{ch.id}"
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                poll_email_channel,
                "interval",
                minutes=interval_minutes,
                id=job_id,
                args=[ch.id],
                replace_existing=True,
            )
            logger.info("Scheduled email polling for channel %d every %d min", ch.id, interval_minutes)


def _split_message(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks
