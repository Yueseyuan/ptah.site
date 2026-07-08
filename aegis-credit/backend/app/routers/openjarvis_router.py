"""OpenJarvis voice/AI sidecar — routes to local jarvis serve instance."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.config import settings
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/voice", tags=["openjarvis"])


class VoiceChatMessage(BaseModel):
    role: str
    content: str


class VoiceChatRequest(BaseModel):
    messages: List[VoiceChatMessage]
    model: Optional[str] = "claude-haiku-4-5-20251001"
    max_tokens: Optional[int] = 512


@router.get("/status")
def jarvis_status():
    """Check if the OpenJarvis sidecar is reachable."""
    try:
        resp = httpx.get(f"{settings.OPENJARVIS_URL}/health", timeout=3)
        return {"status": "online", "url": settings.OPENJARVIS_URL}
    except Exception:
        return {
            "status": "offline",
            "url": settings.OPENJARVIS_URL,
            "hint": "Start OpenJarvis with: pip install OpenJarvis && jarvis serve --port 8765",
        }


@router.post("/chat")
def voice_chat(
    data: VoiceChatRequest,
    _user: User = Depends(get_current_user),
):
    """Send a chat message to OpenJarvis (OpenAI-compatible endpoint)."""
    try:
        resp = httpx.post(
            f"{settings.OPENJARVIS_URL}/v1/chat/completions",
            json={
                "model": data.model,
                "messages": [{"role": m.role, "content": m.content} for m in data.messages],
                "max_tokens": data.max_tokens,
            },
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        # Extract text from OpenAI-compatible response
        text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"message": text, "raw": result}
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, f"OpenJarvis error: {e.response.text}")
    except httpx.RequestError:
        raise HTTPException(
            503,
            f"OpenJarvis is not running. Start it with: jarvis serve --port 8765"
            f" (pip install OpenJarvis). Configured URL: {settings.OPENJARVIS_URL}",
        )
