"""Tool definitions and executor factory for agentic agent runs."""
import asyncio
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.services.workspace import ws_create_directory, ws_list_files, ws_read_file, ws_write_file

# ── File system tools ─────────────────────────────────────────────────────────

_FILE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": (
            "Write content to a file in the project workspace. "
            "Creates parent directories automatically. "
            "Use for ALL source files: HTML, CSS, JS/TS, Python, config, etc. "
            "Always write complete, production-ready content — never truncate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace root, e.g. 'src/index.html'",
                },
                "content": {"type": "string", "description": "Complete file content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the content of an existing file in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace root"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files in the workspace or a subdirectory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Subdirectory to list (omit for workspace root)",
                    "default": "",
                },
            },
        },
    },
    {
        "name": "create_directory",
        "description": "Create a directory (and any missing parents) in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path relative to workspace root"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_bash",
        "description": (
            "Execute a shell command in the workspace directory. "
            "Use to: run Python scripts (python script.py), install packages (pip install X), "
            "run tests (pytest), build projects (npm run build), verify output, lint code, etc. "
            "Returns combined stdout + stderr. The working directory is the workspace root."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds to wait (default: 30, max: 120)",
                    "default": 30,
                },
            },
            "required": ["command"],
        },
    },
]

# ── Web / research tools ──────────────────────────────────────────────────────

_WEB_TOOLS: list[dict[str, Any]] = [
    {
        "name": "fetch_url",
        "description": (
            "Fetch a webpage and return its content. "
            "Use mode='text' for readable text, 'html' for raw HTML (useful for cloning), "
            "'links' for a list of all hyperlinks on the page."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL to fetch (https://...)"},
                "mode": {
                    "type": "string",
                    "enum": ["text", "html", "links"],
                    "description": "text=readable content, html=raw markup, links=all hyperlinks",
                    "default": "text",
                },
            },
            "required": ["url"],
        },
    },
]

# ── Email tools ───────────────────────────────────────────────────────────────

_EMAIL_TOOLS: list[dict[str, Any]] = [
    {
        "name": "send_email",
        "description": (
            "Send an email via SendGrid. "
            "Use for newsletters, campaign emails, notifications, and follow-ups. "
            "The body can be plain text or HTML."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body (HTML or plain text)"},
                "html": {
                    "type": "boolean",
                    "description": "Set false to send as plain text",
                    "default": True,
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
]

# ── Video / audio generation tools ───────────────────────────────────────────

_MEDIA_GEN_TOOLS: list[dict[str, Any]] = [
    {
        "name": "generate_video_clip",
        "description": (
            "Generate a short video clip using Higgsfield AI cinematic model. "
            "Returns a URL to the rendered video. "
            "Use for faceless promo videos, social media ads, product showcases. "
            "Genres: auto, action, suspense, spectacle, intimate, comedy, horror, western. "
            "Aspect ratios: 9:16 (Reels/TikTok), 16:9 (YouTube), 1:1 (Feed). "
            "Duration: 3–12 seconds. Generation takes 1–3 minutes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed cinematic scene description — lighting, framing, subject, mood",
                },
                "duration": {
                    "type": "integer",
                    "description": "Clip length in seconds (3-12, default 6)",
                    "default": 6,
                },
                "genre": {
                    "type": "string",
                    "enum": ["auto", "action", "suspense", "spectacle", "intimate", "comedy", "horror", "western"],
                    "description": "Visual style genre",
                    "default": "auto",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["9:16", "16:9", "1:1"],
                    "description": "9:16 for Reels/TikTok, 16:9 for YouTube, 1:1 for feed posts",
                    "default": "9:16",
                },
                "sound": {
                    "type": "string",
                    "enum": ["on", "off"],
                    "description": "Include ambient cinematic sound",
                    "default": "on",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_voiceover",
        "description": (
            "Generate a voiceover audio file using Higgsfield TTS. "
            "Returns a URL to the MP3 audio. "
            "Available voices: Sterling (authoritative male), Harrison (warm male), "
            "Arthur (classic male), Tallulah (female), Vesper (female). "
            "Use for video narration, ad voiceovers, podcast intros."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The voiceover script text to speak",
                },
                "voice": {
                    "type": "string",
                    "enum": ["Sterling", "Harrison", "Arthur", "Tallulah", "Vesper", "Roman", "Julian"],
                    "description": "Voice character to use",
                    "default": "Sterling",
                },
            },
            "required": ["text"],
        },
    },
]

# ── Social media tools ────────────────────────────────────────────────────────

_SOCIAL_TOOLS: list[dict[str, Any]] = [
    {
        "name": "post_social",
        "description": (
            "Post content to a social media platform. "
            "Platforms: twitter, linkedin, instagram, facebook. "
            "For Instagram, image_url is required. "
            "Twitter posts are automatically truncated to 280 characters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["twitter", "linkedin", "instagram", "facebook"],
                    "description": "Target platform",
                },
                "text": {"type": "string", "description": "Post caption or tweet text"},
                "image_url": {
                    "type": "string",
                    "description": "Public URL of an image to attach (required for Instagram)",
                },
            },
            "required": ["platform", "text"],
        },
    },
]

# ── Canonical tool list (Anthropic format) ────────────────────────────────────

AGENT_TOOLS: list[dict[str, Any]] = _FILE_TOOLS + _WEB_TOOLS + _EMAIL_TOOLS + _MEDIA_GEN_TOOLS + _SOCIAL_TOOLS


def anthropic_to_ollama_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


OLLAMA_TOOLS = anthropic_to_ollama_tools(AGENT_TOOLS)

_TOOLS_SYSTEM_ADDENDUM = """
You have tools available. Use them to complete the task:

FILE TOOLS:
- write_file(path, content): create any file in the workspace
- read_file(path): read a file you already wrote
- list_files(directory=""): see what's in the workspace
- create_directory(path): create folders
- run_bash(command, timeout=30): run shell commands in workspace (python, pip, npm, pytest, etc.)

WEB TOOLS:
- fetch_url(url, mode): fetch webpage as text/html/links

EMAIL TOOLS:
- send_email(to, subject, body, html=true): send via SendGrid

VIDEO / AUDIO GENERATION:
- generate_video_clip(prompt, duration=6, genre="auto", aspect_ratio="9:16", sound="on"): generate a video clip, returns URL
- generate_voiceover(text, voice="Sterling"): generate spoken audio, returns URL

SOCIAL MEDIA TOOLS:
- post_social(platform, text, image_url=null): post to twitter/linkedin/instagram/facebook

RULES:
- Write COMPLETE files — never truncate with "..." or placeholders
- Use list_files to check progress, fetch_url to research before building
- Use run_bash to verify your code actually runs (python script.py, pytest, npm test, etc.)
- Fix any errors you find before finishing
- After all work is done, provide a brief summary of what was accomplished
"""


def make_tool_executor(workspace: Path) -> Callable[[str, dict[str, Any]], Awaitable[str]]:
    """Return an async callable that routes tool calls to the appropriate handler."""

    async def execute(name: str, args: dict[str, Any]) -> str:
        # File tools
        if name == "write_file":
            return ws_write_file(workspace, args["path"], args["content"])
        if name == "read_file":
            return ws_read_file(workspace, args["path"])
        if name == "list_files":
            return ws_list_files(workspace, args.get("directory", ""))
        if name == "create_directory":
            return ws_create_directory(workspace, args["path"])

        # Web tool
        if name == "fetch_url":
            return await _fetch_url(args["url"], args.get("mode", "text"))

        # Email tool
        if name == "send_email":
            return await _send_email(args["to"], args["subject"], args["body"], args.get("html", True))

        # Social tool
        if name == "post_social":
            return await _post_social(args["platform"], args["text"], args.get("image_url"))

        # Video / audio generation
        if name == "generate_video_clip":
            return await _generate_video_clip(
                args["prompt"],
                int(args.get("duration", 6)),
                args.get("genre", "auto"),
                args.get("aspect_ratio", "9:16"),
                args.get("sound", "on"),
            )
        if name == "generate_voiceover":
            return await _generate_voiceover(args["text"], args.get("voice", "Sterling"))

        # Bash execution
        if name == "run_bash":
            return await _run_bash(workspace, args["command"], int(args.get("timeout", 30)))

        return f"Unknown tool: {name}"

    return execute


def get_tools_system_addendum() -> str:
    return _TOOLS_SYSTEM_ADDENDUM


# ── Tool implementations ──────────────────────────────────────────────────────

async def _fetch_url(url: str, mode: str = "text") -> str:
    """Fetch a URL and return content in the requested mode."""
    try:
        import httpx
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; APEX-Agent/1.0)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        if mode == "html":
            return html[:50_000]  # cap at 50KB

        if mode == "links":
            links = re.findall(r'href=["\']([^"\']+)["\']', html)
            return "\n".join(links[:200])

        # mode == "text": strip tags and return readable content
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&[a-z]+;", "", text)
        text = re.sub(r"\s{3,}", "\n\n", text)
        return text.strip()[:20_000]

    except Exception as exc:
        return f"Error fetching {url}: {exc}"


async def _send_email(to: str, subject: str, body: str, html: bool = True) -> str:
    try:
        from app.services.email_service import send_email
        result = await send_email(to=to, subject=subject, body=body, html=html)
        if result["ok"]:
            return f"Email sent successfully to {to}"
        return f"Email failed: {result['error']}"
    except Exception as exc:
        return f"Email error: {exc}"


async def _post_social(platform: str, text: str, image_url: str | None = None) -> str:
    try:
        from app.services.social_service import post_social
        result = await post_social(platform=platform, text=text, image_url=image_url)
        if result["ok"]:
            url = result.get("url", result.get("id", ""))
            return f"Posted to {platform} successfully. {url}".strip()
        return f"Post failed ({platform}): {result['error']}"
    except Exception as exc:
        return f"Social posting error: {exc}"


_VOICE_IDS: dict[str, str] = {
    "Sterling":  "dc382508-c8bd-443c-8cb2-46e57b8d2e6f",
    "Harrison":  "573e5163-59b3-4926-aab1-951ef2985f81",
    "Arthur":    "30fc8796-ceb6-4a66-b3a7-4a145ef7f346",
    "Tallulah":  "f32c8f51-449e-4ddf-bdf7-1527e11df917",
    "Vesper":    "c3204739-4084-41a3-9dc5-c805b307ec18",
    "Roman":     "7e63ac18-5fcd-4aba-8078-a86d4e11c127",
    "Julian":    "95429266-c0ac-4137-a209-63b8812b0f23",
}


async def _generate_video_clip(
    prompt: str,
    duration: int = 6,
    genre: str = "auto",
    aspect_ratio: str = "9:16",
    sound: str = "on",
) -> str:
    try:
        from app.services.higgsfield_service import generate_video_clip
        result = await generate_video_clip(
            prompt=prompt, duration=duration, genre=genre,
            aspect_ratio=aspect_ratio, sound=sound,
        )
        if result["ok"]:
            return f"Video generated: {result['url']}"
        return f"Video generation failed: {result['error']}"
    except Exception as exc:
        return f"Video generation error: {exc}"


async def _generate_voiceover(text: str, voice: str = "Sterling") -> str:
    try:
        from app.services.higgsfield_service import generate_voiceover
        voice_id = _VOICE_IDS.get(voice, _VOICE_IDS["Sterling"])
        result = await generate_voiceover(text=text, voice_id=voice_id)
        if result["ok"]:
            dur = result.get("duration")
            dur_str = f" ({dur:.1f}s)" if dur else ""
            return f"Voiceover generated{dur_str}: {result['url']}"
        return f"Voiceover generation failed: {result['error']}"
    except Exception as exc:
        return f"Voiceover generation error: {exc}"


async def _run_bash(workspace: Path, command: str, timeout: int = 30) -> str:
    """Execute a shell command inside the workspace directory."""
    timeout = min(max(int(timeout), 5), 120)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return f"[command timed out after {timeout}s]"
        output = stdout.decode("utf-8", errors="replace").strip()
        rc = proc.returncode
        prefix = f"[exit {rc}]\n" if rc != 0 else ""
        return f"{prefix}{output}" if output else f"{prefix}[no output]"
    except Exception as exc:
        return f"[error running command: {exc}]"
