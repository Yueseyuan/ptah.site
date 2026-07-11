"""Muapi.ai generation service — drop-in replacement for Higgsfield.

Muapi.ai is a Higgsfield-compatible generation API with a static API key
(no OAuth, no expiry). Get a key at muapi.ai and set MUAPI_API_KEY in .env.

Auth:      x-api-key header
Jobs:      POST https://api.muapi.ai/api/v1/{endpoint}
Poll:      GET  https://api.muapi.ai/api/v1/predictions/{request_id}/result
"""
import asyncio
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.muapi.ai/api/v1"
_POLL_INTERVAL = 5
_MAX_POLL_SEC = 360

# Muapi endpoint slugs (hyphen-separated, not underscore)
_EP_VIDEO = "seedance-2-0"
_EP_IMAGE = "nano-banana"
_EP_MUSIC = "sonilo-music"
_EP_SFX = "mirelo-text-to-audio"
_EP_TTS = "text2speech-v2"


def is_configured() -> bool:
    return bool(settings.muapi_api_key)


def _headers() -> dict[str, str]:
    return {"x-api-key": settings.muapi_api_key, "Content-Type": "application/json"}


async def _create_job(client: httpx.AsyncClient, endpoint: str, payload: dict[str, Any]) -> str:
    resp = await client.post(f"{_BASE}/{endpoint}", json=payload, headers=_headers(), timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    job_id = data.get("request_id") or data.get("id")
    if not job_id:
        raise ValueError(f"No job ID in Muapi response: {data}")
    return job_id


async def _poll_job(client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
    elapsed = 0.0
    while elapsed < _MAX_POLL_SEC:
        await asyncio.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL
        resp = await client.get(
            f"{_BASE}/predictions/{job_id}/result",
            headers=_headers(),
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "pending")
        if status in ("completed", "succeeded", "success"):
            return data
        if status in ("failed", "error"):
            raise RuntimeError(f"Muapi job {job_id} failed: {data.get('error', 'unknown')}")
        logger.debug("Muapi job %s: %s (%.0fs)", job_id, status, elapsed)
    raise TimeoutError(f"Muapi job {job_id} timed out after {_MAX_POLL_SEC}s")


def _extract_url(data: dict[str, Any]) -> str | None:
    outputs = data.get("outputs")
    if outputs and isinstance(outputs, list):
        return outputs[0]
    return data.get("url") or (data.get("output") or {}).get("url")


async def generate_video_clip(
    prompt: str,
    aspect_ratio: str = "9:16",
    duration: int = 6,
    **_kwargs: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": min(duration, 10),
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        job_id = await _create_job(client, _EP_VIDEO, payload)
        record = await _poll_job(client, job_id)
        return {"ok": True, "url": _extract_url(record), "id": job_id}


async def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    **_kwargs: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": prompt, "aspect_ratio": aspect_ratio}
    async with httpx.AsyncClient(timeout=60.0) as client:
        job_id = await _create_job(client, _EP_IMAGE, payload)
        record = await _poll_job(client, job_id)
        return {"ok": True, "url": _extract_url(record), "id": job_id}


async def generate_music(
    prompt: str,
    duration: int = 12,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": prompt, "duration": duration}
    async with httpx.AsyncClient(timeout=120.0) as client:
        job_id = await _create_job(client, _EP_MUSIC, payload)
        record = await _poll_job(client, job_id)
        return {"ok": True, "url": _extract_url(record), "id": job_id}


async def generate_sfx(prompt: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": prompt}
    async with httpx.AsyncClient(timeout=60.0) as client:
        job_id = await _create_job(client, _EP_SFX, payload)
        record = await _poll_job(client, job_id)
        return {"ok": True, "url": _extract_url(record), "id": job_id}


async def generate_voiceover(
    text: str,
    voice_id: str = "sterling",
    **_kwargs: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": text, "voice_id": voice_id}
    async with httpx.AsyncClient(timeout=60.0) as client:
        job_id = await _create_job(client, _EP_TTS, payload)
        record = await _poll_job(client, job_id)
        return {"ok": True, "url": _extract_url(record), "id": job_id}


async def check_balance() -> dict[str, Any]:
    """Muapi.ai doesn't have a balance endpoint — return configured status."""
    return {"ok": True, "provider": "muapi", "credits": None}
