from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.media_seeder import get_media_status, seed_media_agents

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class VideoGenerateRequest(BaseModel):
    prompt: str
    duration: int = Field(default=6, ge=3, le=12)
    genre: Literal["auto", "action", "suspense", "spectacle", "intimate", "comedy", "horror", "western"] = "auto"
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    sound: Literal["on", "off"] = "on"
    batch_size: int = Field(default=1, ge=1, le=20)
    post_to: list[Literal["twitter", "instagram", "facebook", "linkedin"]] = []
    post_caption: str = ""


class VoiceoverRequest(BaseModel):
    text: str
    voice: Literal["Sterling", "Harrison", "Arthur", "Tallulah", "Vesper", "Roman", "Julian"] = "Sterling"


# ── Existing endpoints ────────────────────────────────────────────────────────

@router.get("/status")
async def media_status(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    return await get_media_status(db)


@router.post("/seed")
async def media_seed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await seed_media_agents(db, current_user.id)


# ── Higgsfield endpoints ──────────────────────────────────────────────────────

@router.get("/balance")
async def higgsfield_balance(
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Check current Higgsfield credit balance."""
    from app.services.higgsfield_service import check_balance
    return await check_balance()


@router.post("/generate/video")
async def generate_video(
    req: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    _current_user: User = Depends(get_current_user),
) -> dict:
    """
    Generate a video clip with Higgsfield and optionally post it to social platforms.

    Generation runs synchronously (1-3 min). For fire-and-forget, wire this into
    a background task queue or call from an agent using the generate_video_clip tool.
    """
    from app.services.higgsfield_service import generate_video_clip
    result = await generate_video_clip(
        prompt=req.prompt,
        aspect_ratio=req.aspect_ratio,
        duration=req.duration,
        genre=req.genre,
        sound=req.sound,
        batch_size=req.batch_size,
    )
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result["error"])

    # Optionally post to social platforms in the background
    if req.post_to and result.get("url"):
        background_tasks.add_task(
            _post_to_socials,
            platforms=req.post_to,
            caption=req.post_caption,
            video_url=result["url"],
        )

    return result


@router.post("/generate/voiceover")
async def generate_voiceover(
    req: VoiceoverRequest,
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Generate a voiceover audio file with Higgsfield TTS."""
    from app.services.higgsfield_service import VOICE_STERLING, VOICE_HARRISON, VOICE_ARTHUR, VOICE_TALLULAH, VOICE_VESPER, VOICE_ROMAN, VOICE_JULIAN, generate_voiceover as _gen

    voice_map = {
        "Sterling": VOICE_STERLING,
        "Harrison": VOICE_HARRISON,
        "Arthur":   VOICE_ARTHUR,
        "Tallulah": VOICE_TALLULAH,
        "Vesper":   VOICE_VESPER,
        "Roman":    VOICE_ROMAN,
        "Julian":   VOICE_JULIAN,
    }
    result = await _gen(text=req.text, voice_id=voice_map[req.voice])
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _post_to_socials(platforms: list[str], caption: str, video_url: str) -> None:
    import asyncio
    from app.services.social_service import post_social
    await asyncio.gather(
        *[post_social(p, caption, image_url=video_url) for p in platforms],
        return_exceptions=True,
    )
