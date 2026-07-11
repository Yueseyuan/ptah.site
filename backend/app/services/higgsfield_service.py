"""Higgsfield AI video / audio generation service.

Auth: run `hf auth login` once on any machine that has the CLI, copy the
written credentials.json to this server, and point HIGGSFIELD_CREDENTIALS_PATH
at it.  The service auto-refreshes the access token using the stored refresh
token, so the one-time login is all that's needed.

CLI install (one-time, on any machine):
    curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh
    hf auth login          # browser OAuth flow
    cat ~/.config/higgsfield/credentials.json   # copy this to the server
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://fnf.higgsfield.ai/agents"
_REFRESH_URL = "https://fnf.higgsfield.ai/v1/cli/refresh"
_POLL_INTERVAL = 5    # seconds between polls
_MAX_POLL_SEC = 360   # 6-minute ceiling

# Default voice IDs (from `hf voices list`)
VOICE_STERLING  = "dc382508-c8bd-443c-8cb2-46e57b8d2e6f"
VOICE_HARRISON  = "573e5163-59b3-4926-aab1-951ef2985f81"
VOICE_ARTHUR    = "30fc8796-ceb6-4a66-b3a7-4a145ef7f346"
VOICE_TALLULAH  = "f32c8f51-449e-4ddf-bdf7-1527e11df917"
VOICE_VESPER    = "c3204739-4084-41a3-9dc5-c805b307ec18"
VOICE_ROMAN     = "7e63ac18-5fcd-4aba-8078-a86d4e11c127"
VOICE_JULIAN    = "95429266-c0ac-4137-a209-63b8812b0f23"

# In-memory token cache (access_token, expires_at_unix)
_token_cache: dict[str, Any] = {}


def _creds_path() -> Path | None:
    raw = settings.higgsfield_credentials_path
    if raw:
        return Path(raw).expanduser()
    default = Path.home() / ".config" / "higgsfield" / "credentials.json"
    return default if default.exists() else None


def _load_credentials() -> dict[str, Any]:
    path = _creds_path()
    if not path or not path.exists():
        raise FileNotFoundError(
            "Higgsfield credentials not found. "
            "Run `hf auth login` and set HIGGSFIELD_CREDENTIALS_PATH."
        )
    return json.loads(path.read_text())


async def _access_token() -> str:
    """Return a valid access token, refreshing if within 60s of expiry.

    credentials.json may omit expires_at (CLI v0.2.3 doesn't write it).
    In that case we use the cached token until a 401 forces a refresh,
    or always refresh on first call to stay safe.
    """
    global _token_cache

    # Simplest path: a raw token set via HIGGSFIELD_ACCESS_TOKEN env var
    if settings.higgsfield_access_token:
        return settings.higgsfield_access_token

    now = time.time()
    cached_expires = _token_cache.get("expires_at", 0)
    # If we have a cached token with a known expiry, use it while still valid
    if _token_cache.get("access_token") and cached_expires and now < cached_expires - 60:
        return _token_cache["access_token"]
    # If cached with no expiry info, return as-is (trust until 401)
    if _token_cache.get("access_token") and not cached_expires:
        return _token_cache["access_token"]

    creds = _load_credentials()
    expires_at = creds.get("expires_at", 0)
    # No expiry in file — use token directly, cache it, skip refresh
    if creds.get("access_token") and not expires_at:
        _token_cache = creds
        return creds["access_token"]
    # Known expiry and still valid
    if creds.get("access_token") and now < expires_at - 60:
        _token_cache = creds
        return creds["access_token"]

    # Refresh — fall back to existing token if refresh endpoint fails
    if not creds.get("refresh_token"):
        if creds.get("access_token"):
            _token_cache = creds
            return creds["access_token"]
        raise RuntimeError("Higgsfield credentials expired and no refresh_token available.")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _REFRESH_URL,
                json={"refresh_token": creds["refresh_token"]},
            )
            resp.raise_for_status()
            new_creds = {**creds, **resp.json()}
            path = _creds_path()
            if path:
                path.write_text(json.dumps(new_creds, indent=2))
            _token_cache = new_creds
            logger.debug("Higgsfield token refreshed")
            return new_creds["access_token"]
    except Exception as exc:
        logger.warning("Higgsfield token refresh failed (%s); using existing access_token", exc)
        if creds.get("access_token"):
            # Set a short TTL so the cache re-reads credentials.json after 5 minutes,
            # picking up any token written by `higgsfield auth login` in the meantime.
            _token_cache = {**creds, "expires_at": time.time() + 300}
            return creds["access_token"]
        raise


async def _headers() -> dict[str, str]:
    token = await _access_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _create_job(client: httpx.AsyncClient, payload: dict[str, Any]) -> str:
    resp = await client.post(f"{_BASE}/jobs", json=payload, headers=await _headers(), timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    records = data.get("results", [data])
    job_id = records[0].get("id") if records else data.get("id")
    if not job_id:
        raise ValueError(f"No job ID in Higgsfield response: {data}")
    return job_id


async def _poll_job(client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
    """Poll /agents/jobs/poll until completed or failed."""
    elapsed = 0.0
    while elapsed < _MAX_POLL_SEC:
        await asyncio.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL
        resp = await client.get(
            f"{_BASE}/jobs/poll",
            params={"job_id": job_id},
            headers=await _headers(),
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        record = data if "status" in data else (data.get("results") or [data])[0]
        status = record.get("status", "pending")
        if status == "completed":
            return record
        if status in ("failed", "error"):
            raise RuntimeError(f"Higgsfield job {job_id} failed: {record.get('error', 'unknown')}")
        logger.debug("Higgsfield job %s: %s (%.0fs)", job_id, status, elapsed)
    raise TimeoutError(f"Higgsfield job {job_id} timed out after {_MAX_POLL_SEC}s")


def _extract_url(record: dict[str, Any]) -> str | None:
    results = record.get("results") or {}
    return results.get("rawUrl") or results.get("url") or record.get("rawUrl")


async def generate_video_clip(
    prompt: str,
    model: str = "cinematic_studio_video_v2",
    aspect_ratio: str = "9:16",
    duration: int = 6,
    genre: str = "auto",
    sound: str = "on",
    batch_size: int = 1,
) -> dict[str, Any]:
    """Generate a video clip. Returns {"ok": True, "url": "...", "id": "..."}."""
    try:
        await _access_token()
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc)}

    payload: dict[str, Any] = {
        "model": model,
        "params": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "genre": genre,
            "sound": sound,
        },
    }
    if batch_size > 1:
        payload["batch_size"] = min(batch_size, 20)

    async with httpx.AsyncClient(timeout=60.0) as client:
        job_id = await _create_job(client, payload)
        record = await _poll_job(client, job_id)
        return {"ok": True, "url": _extract_url(record), "id": job_id}


async def generate_image(
    prompt: str,
    model: str = "nano_banana_2",
    aspect_ratio: str = "1:1",
    resolution: str = "1k",
) -> dict[str, Any]:
    """Generate an image. Returns {"ok": True, "url": "...", "id": "..."}."""
    try:
        await _access_token()
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc)}

    payload: dict[str, Any] = {
        "model": model,
        "params": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        job_id = await _create_job(client, payload)
        record = await _poll_job(client, job_id)
        return {"ok": True, "url": _extract_url(record), "id": job_id}


async def generate_music(
    prompt: str,
    duration: int = 12,
) -> dict[str, Any]:
    """Generate background music with Sonilo. Returns {"ok": True, "url": "...", "id": "..."}."""
    try:
        await _access_token()
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc)}

    payload: dict[str, Any] = {
        "model": "sonilo_music",
        "params": {
            "prompt": prompt,
            "duration": duration,
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        job_id = await _create_job(client, payload)
        record = await _poll_job(client, job_id)
        results = record.get("results") or {}
        return {
            "ok": True,
            "url": _extract_url(record),
            "id": job_id,
            "duration": results.get("durationSec"),
        }


async def generate_sfx(
    prompt: str,
) -> dict[str, Any]:
    """Generate a sound effect with Mirelo. Returns {"ok": True, "url": "...", "id": "..."}."""
    try:
        await _access_token()
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc)}

    payload: dict[str, Any] = {
        "model": "mirelo_text_to_audio",
        "params": {
            "prompt": prompt,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        job_id = await _create_job(client, payload)
        record = await _poll_job(client, job_id)
        results = record.get("results") or {}
        return {
            "ok": True,
            "url": _extract_url(record),
            "id": job_id,
            "duration": results.get("durationSec"),
        }


async def generate_voiceover(
    text: str,
    voice_id: str = VOICE_STERLING,
    voice_type: str = "preset",
    tts_model: str = "elevenlabs",
) -> dict[str, Any]:
    """Generate a voiceover MP3. Returns {"ok": True, "url": "...", "id": "..."}."""
    try:
        await _access_token()
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc)}

    payload: dict[str, Any] = {
        "model": "text2speech_v2",
        "params": {
            "prompt": text,
            "voice_id": voice_id,
            "voice_type": voice_type,
            "model": tts_model,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        job_id = await _create_job(client, payload)
        record = await _poll_job(client, job_id)
        results = record.get("results") or {}
        return {
            "ok": True,
            "url": _extract_url(record),
            "id": job_id,
            "duration": results.get("durationSec"),
        }


async def check_balance() -> dict[str, Any]:
    """Return current Higgsfield credit balance."""
    try:
        headers = await _headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{_BASE}/balance", headers=headers)
            resp.raise_for_status()
            return {"ok": True, **resp.json()}
    except Exception as exc:
        logger.warning("Higgsfield balance check failed: %s", exc)
        return {"ok": False, "error": str(exc)}
