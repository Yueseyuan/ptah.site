"""Dify proxy — keeps API key server-side, streams Dify chatflow responses."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any

from app.config import settings
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/dify", tags=["dify"])


class DifyChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = ""
    user: Optional[str] = "portal-user"
    inputs: Optional[dict] = {}
    response_mode: Optional[str] = "blocking"


class DifyWorkflowRequest(BaseModel):
    inputs: dict
    user: Optional[str] = "staff-user"
    response_mode: Optional[str] = "blocking"


def _dify_headers() -> dict:
    if not settings.DIFY_API_KEY:
        raise HTTPException(503, "Dify is not configured. Set DIFY_API_KEY in environment variables.")
    return {
        "Authorization": f"Bearer {settings.DIFY_API_KEY}",
        "Content-Type": "application/json",
    }


@router.get("/config")
def dify_config():
    """Return public Dify config for frontend embed widgets. No auth required."""
    return {
        "receptionist_token": settings.DIFY_RECEPTIONIST_TOKEN,
        "base_url": settings.DIFY_BASE_URL,
        "configured": bool(settings.DIFY_API_KEY),
    }


@router.post("/chat")
def dify_chat(
    data: DifyChatRequest,
    _user: User = Depends(get_current_user),
):
    """Proxy a chat message to Dify, return the response."""
    headers = _dify_headers()
    payload = {
        "inputs": data.inputs or {},
        "query": data.query,
        "response_mode": "blocking",
        "conversation_id": data.conversation_id or "",
        "user": data.user or "staff",
    }
    try:
        resp = httpx.post(
            f"{settings.DIFY_BASE_URL}/chat-messages",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, f"Dify error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Could not reach Dify: {e}")


@router.post("/workflow")
def dify_workflow(
    data: DifyWorkflowRequest,
    _user: User = Depends(get_current_user),
):
    """Run a Dify workflow and return the result."""
    headers = _dify_headers()
    payload = {
        "inputs": data.inputs,
        "response_mode": "blocking",
        "user": data.user or "staff",
    }
    try:
        resp = httpx.post(
            f"{settings.DIFY_BASE_URL}/workflows/run",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, f"Dify workflow error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Could not reach Dify: {e}")
