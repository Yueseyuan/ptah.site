"""Communication channel adapters — Telegram, Discord, Slack, generic webhooks.

Telegram: full bidirectional bot (receive messages → run Chief → reply).
Discord/Slack/Generic: outbound-only webhook notifications.
"""
import hashlib
import logging
import secrets
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

    logger.warning("Unknown channel type: %s", channel_type)
    return False


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


def _split_message(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks
