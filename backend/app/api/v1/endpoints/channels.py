"""Communication channels endpoints — Telegram, Discord, Slack, generic webhooks, WhatsApp, Email."""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.channel import Channel
from app.models.user import User
from app.services.channel_service import (
    handle_telegram_update,
    handle_whatsapp_update,
    make_telegram_secret_token,
    send_to_channel,
    telegram_delete_webhook,
    telegram_get_me,
    telegram_set_webhook,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Schemas ───────────────────────────────────────────────────────────────────

CHANNEL_TYPES = ["telegram", "discord_webhook", "slack_webhook", "generic_webhook", "whatsapp", "email"]


class ChannelCreate(BaseModel):
    name: str
    channel_type: str
    config: dict[str, Any] = {}
    enabled: bool = True


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None


class ChannelOut(BaseModel):
    id: int
    name: str
    channel_type: str
    config: dict[str, Any]
    enabled: bool
    created_at: str

    model_config = {"from_attributes": True}

    def model_post_init(self, _context: Any) -> None:
        masked = dict(self.config)
        if "bot_token" in masked:
            token = masked["bot_token"]
            masked["bot_token"] = token[:8] + "…" + token[-4:] if len(token) > 12 else "***"
        if "access_token" in masked:
            token = masked["access_token"]
            masked["access_token"] = token[:6] + "…" if len(token) > 6 else "***"
        if "smtp_password" in masked:
            masked["smtp_password"] = "***"
        self.config = masked


class SendMessageBody(BaseModel):
    message: str
    chat_id: Optional[str] = None


class SetWebhookBody(BaseModel):
    webhook_url: str


class TestResult(BaseModel):
    ok: bool
    detail: Optional[str] = None


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ChannelOut])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[ChannelOut]:
    channels = (await db.execute(select(Channel).order_by(Channel.created_at.desc()))).scalars().all()
    return [ChannelOut.model_validate(c) for c in channels]


@router.post("/", response_model=ChannelOut, status_code=status.HTTP_201_CREATED)
async def create_channel(
    body: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelOut:
    if body.channel_type not in CHANNEL_TYPES:
        raise HTTPException(400, f"channel_type must be one of: {', '.join(CHANNEL_TYPES)}")
    ch = Channel(
        name=body.name,
        channel_type=body.channel_type,
        config=body.config,
        enabled=body.enabled,
        created_by_id=current_user.id,
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return ChannelOut.model_validate(ch)


@router.get("/{channel_id}", response_model=ChannelOut)
async def get_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ChannelOut:
    ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if not ch:
        raise HTTPException(404, "Channel not found")
    return ChannelOut.model_validate(ch)


@router.patch("/{channel_id}", response_model=ChannelOut)
async def update_channel(
    channel_id: int,
    body: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ChannelOut:
    ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if not ch:
        raise HTTPException(404, "Channel not found")
    if body.name is not None:
        ch.name = body.name
    if body.config is not None:
        ch.config = body.config
    if body.enabled is not None:
        ch.enabled = body.enabled
    await db.commit()
    await db.refresh(ch)
    return ChannelOut.model_validate(ch)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if not ch:
        raise HTTPException(404, "Channel not found")
    # If Telegram, remove the webhook
    if ch.channel_type == "telegram":
        token = ch.config.get("bot_token", "")
        if token:
            await telegram_delete_webhook(token)
    await db.delete(ch)
    await db.commit()


# ── Actions ───────────────────────────────────────────────────────────────────

@router.post("/{channel_id}/send", response_model=TestResult)
async def send_message(
    channel_id: int,
    body: SendMessageBody,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> TestResult:
    """Send a message through this channel."""
    ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if not ch:
        raise HTTPException(404, "Channel not found")

    config = dict(ch.config)
    if body.chat_id and ch.channel_type == "telegram":
        config = {**config, "default_chat_id": body.chat_id}

    ok = await send_to_channel(config, ch.channel_type, body.message)
    return TestResult(ok=ok, detail="Sent" if ok else "Send failed — check config")


@router.post("/{channel_id}/test", response_model=TestResult)
async def test_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> TestResult:
    """Send a test message through this channel."""
    ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if not ch:
        raise HTTPException(404, "Channel not found")

    if ch.channel_type == "telegram":
        token = ch.config.get("bot_token", "")
        if not token:
            return TestResult(ok=False, detail="bot_token not configured")
        result = await telegram_get_me(token)
        if result.get("ok"):
            bot_name = result["result"].get("username", "bot")
            return TestResult(ok=True, detail=f"Bot @{bot_name} is reachable")
        return TestResult(ok=False, detail=result.get("description", "Bot unreachable"))

    # For webhook types, send a test message
    ok = await send_to_channel(ch.config, ch.channel_type, "🔔 APEX AI test message")
    return TestResult(ok=ok, detail="Test sent" if ok else "Send failed")


@router.post("/{channel_id}/set-webhook", response_model=TestResult)
async def set_telegram_webhook(
    channel_id: int,
    body: SetWebhookBody,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> TestResult:
    """Register a Telegram webhook URL with the Bot API."""
    ch = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if not ch:
        raise HTTPException(404, "Channel not found")
    if ch.channel_type != "telegram":
        raise HTTPException(400, "This endpoint is only for Telegram channels")

    token = ch.config.get("bot_token", "")
    if not token:
        raise HTTPException(400, "bot_token not configured")

    secret = make_telegram_secret_token(token)
    result = await telegram_set_webhook(token, body.webhook_url, secret)
    if result.get("ok"):
        return TestResult(ok=True, detail=f"Webhook registered at {body.webhook_url}")
    return TestResult(ok=False, detail=result.get("description", "setWebhook failed"))


# ── Telegram public webhook (called by Telegram, no auth) ─────────────────────

@router.post("/telegram/webhook", include_in_schema=False)
async def telegram_webhook_handler(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
) -> dict:
    """
    Receives Telegram updates. Telegram includes X-Telegram-Bot-Api-Secret-Token
    matching the secret we set during setWebhook — we use it to identify the channel.
    """
    update = await request.json()

    if not x_telegram_bot_api_secret_token:
        logger.warning("Telegram webhook called without secret token")
        return {"ok": True}

    # Find the channel whose bot_token hashes to this secret
    all_channels = (
        await db.execute(select(Channel).where(Channel.channel_type == "telegram", Channel.enabled.is_(True)))
    ).scalars().all()

    matched_channel = None
    for ch in all_channels:
        token = ch.config.get("bot_token", "")
        if token and make_telegram_secret_token(token) == x_telegram_bot_api_secret_token:
            matched_channel = ch
            break

    if not matched_channel:
        logger.warning("Telegram webhook: no matching channel for secret token")
        return {"ok": True}

    # Process in background so Telegram doesn't timeout waiting
    import asyncio
    asyncio.create_task(handle_telegram_update(update, matched_channel.id))

    return {"ok": True}


# ── WhatsApp public webhooks (called by Meta, no auth) ───────────────────────

@router.get("/whatsapp/webhook", include_in_schema=False)
async def whatsapp_webhook_verify(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Meta sends a GET to verify the webhook endpoint — returns hub.challenge on match."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    verify_token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode != "subscribe" or not verify_token:
        raise HTTPException(status_code=400, detail="Invalid hub params")

    all_channels = (
        await db.execute(
            select(Channel).where(Channel.channel_type == "whatsapp", Channel.enabled.is_(True))
        )
    ).scalars().all()

    for ch in all_channels:
        if ch.config.get("verify_token") == verify_token:
            return PlainTextResponse(challenge)

    raise HTTPException(status_code=403, detail="verify_token does not match any channel")


@router.post("/whatsapp/webhook", include_in_schema=False)
async def whatsapp_webhook_handler(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Receive inbound WhatsApp Cloud API messages and route to Chief."""
    body = await request.json()

    try:
        phone_number_id = (
            body.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("metadata", {})
            .get("phone_number_id", "")
        )
    except (IndexError, KeyError, TypeError):
        return {"ok": True}

    all_channels = (
        await db.execute(
            select(Channel).where(Channel.channel_type == "whatsapp", Channel.enabled.is_(True))
        )
    ).scalars().all()

    matched_channel = None
    for ch in all_channels:
        if ch.config.get("phone_number_id") == phone_number_id:
            matched_channel = ch
            break

    if not matched_channel:
        logger.warning("WhatsApp webhook: no matching channel for phone_number_id %s", phone_number_id)
        return {"ok": True}

    import asyncio
    asyncio.create_task(handle_whatsapp_update(body, matched_channel.id))
    return {"ok": True}
