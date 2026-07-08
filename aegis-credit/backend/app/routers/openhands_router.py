"""OpenHands agent integration — trigger autonomous document/analysis tasks."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.config import settings
from app.dependencies import get_current_user, require_staff
from app.models import User

router = APIRouter(prefix="/api/openhands", tags=["openhands"])


class OpenHandsTaskRequest(BaseModel):
    task: str                        # natural-language task description
    context: Optional[str] = None   # additional context (case data, client info, etc.)
    mode: Optional[str] = "document"  # document | analysis | research


def _oh_headers() -> dict:
    if not settings.OPENHANDS_API_KEY:
        raise HTTPException(
            503,
            "OpenHands is not configured. Set OPENHANDS_API_KEY in environment variables. "
            "Get your key at app.all-hands.dev",
        )
    return {
        "Authorization": f"Bearer {settings.OPENHANDS_API_KEY}",
        "Content-Type": "application/json",
    }


def _build_prompt(data: OpenHandsTaskRequest) -> str:
    prompt = data.task
    if data.context:
        prompt += f"\n\nContext:\n{data.context}"
    if data.mode == "document":
        prompt += "\n\nPlease produce a complete, professional document as the output."
    elif data.mode == "analysis":
        prompt += "\n\nPlease produce a structured analysis report as the output."
    return prompt


@router.post("/task")
def create_openhands_task(
    data: OpenHandsTaskRequest,
    _staff: User = Depends(require_staff),
):
    """Dispatch a task to the OpenHands AI agent. Returns a conversation_id for polling."""
    headers = _oh_headers()
    payload = {
        "initial_message": _build_prompt(data),
        "runtime_ids": [],
    }
    try:
        resp = httpx.post(
            f"{settings.OPENHANDS_BASE_URL}/app-conversations",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        return {
            "conversation_id": result.get("conversation_id") or result.get("id"),
            "status": "running",
            "poll_url": f"/api/openhands/task/{result.get('conversation_id') or result.get('id')}",
        }
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, f"OpenHands error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Could not reach OpenHands: {e}")


@router.get("/task/{conversation_id}")
def get_openhands_task(
    conversation_id: str,
    _staff: User = Depends(require_staff),
):
    """Poll the status and result of an OpenHands task."""
    headers = _oh_headers()
    try:
        resp = httpx.get(
            f"{settings.OPENHANDS_BASE_URL}/app-conversations/{conversation_id}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "conversation_id": conversation_id,
            "status": data.get("status", "unknown"),
            "result": data.get("final_action") or data.get("last_message") or data,
        }
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, f"OpenHands error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Could not reach OpenHands: {e}")
