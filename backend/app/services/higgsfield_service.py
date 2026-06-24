"""Higgsfield AI video and audio generation service.

API key: get from higgsfield.ai → Dashboard → API Keys.
Set HIGGSFIELD_API_KEY in your .env file.
"""
import asyncio
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.higgsfield.ai"
_POLL_INTERVAL = 5   # seconds between status checks
_MAX_POLL_SEC = 360  # 6-minute timeout (video gen takes 1-3 min)

# Default voices
VOICE_STERLING = "dc382508-c8bd-443c-8cb2-46e57b8d2e6f"
VOICE_HARRISON = "573e5163-59b3-4926-aab1-951ef2985f81"
VOICE_ARTHUR   = "30fc8796-ceb6-4a66-b3a7-4a145ef7f346"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.higgsfield_api_key}",
        "Content-Type": "application/json",
    }


async def _poll(client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
    """Poll /v1/generations/{id} until status is completed or failed."""
    elapsed = 0.0
    while elapsed < _MAX_POLL_SEC:
        await asyncio.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL
        resp = await client.get(f"{_BASE}/v1/generations/{job_id}", headers=_headers(), timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        # Handle both top-level and results-wrapped responses
        record = data if "status" in data else (data.get("results") or [data])[0]
        status = record.get("status", "pending")
        if status == "completed":
            return record
        if status in ("failed", "error"):
            raise RuntimeError(f"Generation failed: {record.get('error', 'unknown')}")
        logger.debug("Higgsfield job %s: %s (%.0fs elapsed)", job_id, status, elapsed)
    raise TimeoutError(f"Higgsfield job {job_id} did not complete within {_MAX_POLL_SEC}s")


async def generate_video_clip(
    prompt: str,
    model: str = "cinematic_studio_video_v2",
    aspect_ratio: str = "9:16",
    duration: int = 6,
    genre: str = "auto",
    sound: str = "on",
) -> dict[str, Any]:
    """Generate a video clip. Returns {"ok": True, "url": "...", "id": "..."}."""
    if not settings.higgsfield_api_key:
        return {"ok": False, "error": "HIGGSFIELD_API_KEY not set in .env"}

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "genre": genre,
        "sound": sound,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{_BASE}/v1/generations", json=payload, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        records = data.get("results", [data])
        job_id = records[0].get("id") if records else data.get("id")
        if not job_id:
            raise ValueError(f"No job ID in response: {data}")

        record = await _poll(client, job_id)
        results = record.get("results") or {}
        url = results.get("rawUrl") or results.get("url") or record.get("rawUrl")
        return {"ok": True, "url": url, "id": job_id, "duration": results.get("durationSec")}


async def generate_voiceover(
    text: str,
    voice_id: str = VOICE_STERLING,
    voice_type: str = "preset",
    model: str = "text2speech_v2_elevenlabs",
) -> dict[str, Any]:
    """Generate a voiceover. Returns {"ok": True, "url": "...", "id": "..."}."""
    if not settings.higgsfield_api_key:
        return {"ok": False, "error": "HIGGSFIELD_API_KEY not set in .env"}

    payload: dict[str, Any] = {
        "model": model,
        "prompt": text,
        "voice_id": voice_id,
        "voice_type": voice_type,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{_BASE}/v1/generate/audio", json=payload, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        records = data.get("results", [data])
        job_id = records[0].get("id") if records else data.get("id")
        if not job_id:
            raise ValueError(f"No job ID in response: {data}")

        record = await _poll(client, job_id)
        results = record.get("results") or {}
        url = results.get("rawUrl") or results.get("url") or record.get("rawUrl")
        return {"ok": True, "url": url, "id": job_id, "duration": results.get("durationSec")}
