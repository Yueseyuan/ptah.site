"""YouTube transcription service.

Primary path: youtube-transcript-api (fetches auto-generated/manual captions — no ffmpeg).
Fallback path: yt-dlp audio download → OpenAI Whisper API (requires OpenAI provider).
"""
import asyncio
import logging
import re
import tempfile
import os
from typing import Any

logger = logging.getLogger(__name__)

_YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def extract_video_id(url: str) -> str | None:
    m = _YT_ID_RE.search(url)
    return m.group(1) if m else None


async def _transcribe_via_captions(video_id: str) -> dict[str, Any]:
    """Fetch captions using youtube-transcript-api (no ffmpeg needed)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
    except ImportError:
        return {"ok": False, "error": "youtube-transcript-api not installed"}

    def _fetch():
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Prefer manual English, then auto English, then any translated-to-English
            try:
                t = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
            except Exception:
                try:
                    t = transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
                except Exception:
                    # Fall back to first available transcript translated to English
                    t = next(iter(transcript_list)).translate("en")
            entries = t.fetch()
            text = " ".join(e["text"] for e in entries)
            return {"ok": True, "transcript": text, "method": "captions", "segments": len(entries)}
        except TranscriptsDisabled:
            return {"ok": False, "error": "Transcripts are disabled for this video"}
        except NoTranscriptFound:
            return {"ok": False, "error": "No transcript found for this video"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return await asyncio.get_event_loop().run_in_executor(None, _fetch)


async def _transcribe_via_whisper(video_id: str) -> dict[str, Any]:
    """Download audio via yt-dlp then transcribe via OpenAI Whisper API."""
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "yt-dlp not installed"}

    from app.providers.registry import get_registry
    registry = get_registry()
    openai_provider = registry.get_provider("openai")
    if not openai_provider:
        return {"ok": False, "error": "OpenAI provider not configured (needed for Whisper fallback)"}

    url = f"https://www.youtube.com/watch?v={video_id}"

    def _download_audio(out_path: str) -> bool:
        import yt_dlp
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": out_path,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, f"{video_id}.m4a")
        try:
            await asyncio.get_event_loop().run_in_executor(None, _download_audio, audio_path)
        except Exception as exc:
            return {"ok": False, "error": f"Audio download failed: {exc}"}

        # Find the downloaded file (yt-dlp may append extension)
        candidates = [f for f in os.listdir(tmpdir) if f.startswith(video_id)]
        if not candidates:
            return {"ok": False, "error": "Downloaded audio file not found"}
        audio_file = os.path.join(tmpdir, candidates[0])

        try:
            import httpx
            api_key = getattr(openai_provider, "api_key", None) or os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                return {"ok": False, "error": "OpenAI API key not available"}

            with open(audio_file, "rb") as f:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        data={"model": "whisper-1"},
                        files={"file": (os.path.basename(audio_file), f, "audio/mp4")},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return {"ok": True, "transcript": data.get("text", ""), "method": "whisper"}
        except Exception as exc:
            return {"ok": False, "error": f"Whisper transcription failed: {exc}"}


async def transcribe_youtube(url: str) -> dict[str, Any]:
    """
    Transcribe a YouTube video.

    Tries captions first (fast, no ffmpeg). Falls back to Whisper API if unavailable.

    Returns:
        ok: bool
        transcript: str (on success)
        method: "captions" | "whisper"
        video_id: str
        error: str (on failure)
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {"ok": False, "error": "Could not extract YouTube video ID from URL"}

    logger.info("Transcribing YouTube video %s", video_id)

    result = await _transcribe_via_captions(video_id)
    if result.get("ok"):
        result["video_id"] = video_id
        return result

    logger.info("Caption path failed (%s), trying Whisper fallback", result.get("error"))
    whisper_result = await _transcribe_via_whisper(video_id)
    whisper_result["video_id"] = video_id
    if not whisper_result.get("ok"):
        whisper_result["caption_error"] = result.get("error")
    return whisper_result
