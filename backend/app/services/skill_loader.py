"""Fetch and cache SKILL.md files from the skills.sh public registry.

Agents can declare a list of skill slugs in their AgentVersion.config["skills"].
At run time the executor calls load_skills_content() to prepend the combined
skill context to the agent's system prompt.
"""
import hashlib
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_CACHE_DIR = Path.home() / ".apex" / "skill_cache"

# Try slug/SKILL.md then slug bare (some skills redirect)
_URL_TEMPLATES = [
    "https://skills.sh/{slug}/SKILL.md",
    "https://skills.sh/{slug}",
]


def _cache_path(slug: str) -> Path:
    key = hashlib.sha256(slug.encode()).hexdigest()[:16]
    return _CACHE_DIR / f"{key}.md"


async def fetch_skill(slug_or_url: str, *, bust_cache: bool = False) -> str:
    """Return the SKILL.md content for *slug_or_url*, caching to disk.

    If *slug_or_url* looks like a full URL it is fetched directly.
    Otherwise it is treated as a skills.sh slug.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(slug_or_url)

    if not bust_cache and cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    urls = (
        [slug_or_url]
        if slug_or_url.startswith("http")
        else [t.format(slug=slug_or_url) for t in _URL_TEMPLATES]
    )

    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for url in urls:
            try:
                r = await client.get(url)
                if r.status_code == 200 and r.text.strip():
                    content = r.text
                    cache_file.write_text(content, encoding="utf-8")
                    return content
            except Exception as exc:
                last_exc = exc

    raise RuntimeError(
        f"Could not fetch skill '{slug_or_url}': {last_exc or 'all URLs returned empty'}"
    )


async def load_skills_content(slugs: list[str]) -> str:
    """Fetch multiple skills and return them as a single concatenated block."""
    parts: list[str] = []
    for slug in slugs:
        try:
            content = await fetch_skill(slug)
            parts.append(f"<!-- SKILL: {slug} -->\n{content.strip()}")
        except Exception as exc:
            logger.warning("Skipping skill '%s': %s", slug, exc)
    return "\n\n---\n\n".join(parts)


def list_cached_skills() -> list[str]:
    """Return slugs (actually cache-key filenames) present on disk."""
    if not _CACHE_DIR.exists():
        return []
    return [p.stem for p in _CACHE_DIR.glob("*.md")]


def clear_skill_cache() -> int:
    """Delete all cached SKILL.md files. Returns the count removed."""
    if not _CACHE_DIR.exists():
        return 0
    removed = 0
    for p in _CACHE_DIR.glob("*.md"):
        p.unlink()
        removed += 1
    return removed
