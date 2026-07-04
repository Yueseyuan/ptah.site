"""YouTube transcription endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.youtube_transcript import transcribe_youtube

router = APIRouter()


class TranscribeRequest(BaseModel):
    url: str


class TranscribeResult(BaseModel):
    ok: bool
    transcript: str | None = None
    method: str | None = None
    video_id: str | None = None
    error: str | None = None


@router.post("/transcribe", response_model=TranscribeResult)
async def youtube_transcribe(
    body: TranscribeRequest,
    _current_user: User = Depends(get_current_user),
) -> TranscribeResult:
    """
    Transcribe a YouTube video.

    Fetches captions (auto-generated or manual) first.
    Falls back to yt-dlp + OpenAI Whisper API when captions aren't available.
    """
    if not body.url.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="url is required")

    result = await transcribe_youtube(body.url.strip())
    return TranscribeResult(**result)
