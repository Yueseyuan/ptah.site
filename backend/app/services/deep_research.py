"""Deep Research engine — Think → Search → Fetch → Synthesize.

Uses Jina AI (r.jina.ai / s.jina.ai) for search and reading — no API key required.
"""
import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.providers.base import Message

logger = logging.getLogger(__name__)

_JINA_SEARCH = "https://s.jina.ai/"
_JINA_READ = "https://r.jina.ai/"
_MAX_SOURCE_CHARS = 6000
_MAX_SOURCES = 9
_HEADERS = {
    "Accept": "text/markdown",
    "User-Agent": "Mozilla/5.0 (compatible; APEX-Research/1.0)",
}

_THINK_SYSTEM = (
    "You are a research strategist. Given a research question, break it into 3-5 focused "
    "sub-questions that together fully answer the original question. Each sub-question should "
    "be independently searchable and address a distinct aspect.\n\n"
    "Return ONLY valid JSON — no markdown, no explanation:\n"
    '{"sub_questions": ["...", "...", "..."]}'
)

_SYNTHESIZE_SYSTEM = (
    "You are a senior research analyst. You have gathered content from multiple web sources "
    "to answer a research question. Write a comprehensive, well-structured research report.\n\n"
    "Requirements:\n"
    "- Use clear Markdown headings and sections\n"
    "- Cite sources inline as [Source N] where N is the source number\n"
    "- Be specific and factual — only claim what the sources support\n"
    "- Include a ## Sources section at the end listing all URLs with their numbers\n"
    "- Write in professional but readable prose\n"
    "- Be thorough — minimum 400 words"
)


async def _get_provider_and_model():
    from app.providers.registry import get_registry
    from app.services.chief import _get_provider_and_model as _chief_picker
    registry = get_registry()
    return await _chief_picker(registry)


async def _think(question: str) -> list[str]:
    """Break the research question into focused sub-questions via LLM."""
    provider, model_id = await _get_provider_and_model()
    if not provider:
        return [question]

    try:
        result = await provider.complete(
            [
                Message(role="system", content=_THINK_SYSTEM),
                Message(role="user", content=f"Research question: {question}"),
            ],
            model=model_id,
        )
        data = json.loads(result.content)
        sub_qs = data.get("sub_questions", [])
        if sub_qs and isinstance(sub_qs, list):
            return [str(q) for q in sub_qs[:5]]
    except Exception as exc:
        logger.warning("Deep research think phase failed: %s", exc)

    return [question]


async def _search(query: str) -> str:
    """Search via Jina and return markdown results."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(f"{_JINA_SEARCH}{query}", headers=_HEADERS)
            resp.raise_for_status()
            return resp.text[:8000]
    except Exception as exc:
        logger.warning("Jina search failed for %r: %s", query, exc)
        return ""


async def _fetch(url: str) -> str:
    """Fetch a URL via Jina Reader and return clean markdown."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(f"{_JINA_READ}{url}", headers=_HEADERS)
            resp.raise_for_status()
            return resp.text[:_MAX_SOURCE_CHARS]
    except Exception as exc:
        logger.warning("Jina read failed for %r: %s", url, exc)
        return ""


def _extract_urls(markdown: str) -> list[str]:
    """Extract unique, non-Jina URLs from Jina search result markdown."""
    raw = re.findall(r'https?://[^\s\)\]"\'<>]+', markdown)
    seen: set[str] = set()
    result: list[str] = []
    for url in raw:
        clean = url.rstrip(".,;)")
        if "jina.ai" in clean:
            continue
        if clean not in seen:
            seen.add(clean)
            result.append(clean)
        if len(result) >= 3:
            break
    return result


async def _synthesize(question: str, sources: list[dict[str, str]]) -> str:
    """LLM synthesizes all sources into a cited Markdown report."""
    provider, model_id = await _get_provider_and_model()
    if not provider:
        return "No LLM provider available to synthesize the report."

    filled = [s for s in sources if s.get("content", "").strip()]
    if not filled:
        return "No source content could be retrieved. Try a more specific question."

    source_block = "\n\n---\n\n".join(
        f"[Source {i + 1}] URL: {s['url']}\n\n{s['content']}"
        for i, s in enumerate(filled)
    )

    try:
        result = await provider.complete(
            [
                Message(role="system", content=_SYNTHESIZE_SYSTEM),
                Message(
                    role="user",
                    content=(
                        f"Research question: {question}\n\n"
                        f"Sources:\n\n{source_block}"
                    ),
                ),
            ],
            model=model_id,
        )
        return result.content
    except Exception as exc:
        logger.error("Deep research synthesize failed: %s", exc)
        return f"Synthesis failed: {exc}"


async def run_deep_research(question: str) -> dict[str, Any]:
    """
    Full Think → Search → Fetch → Synthesize pipeline.

    Returns:
        report: full Markdown research report with citations
        sources: list of source URLs used
        sub_questions: the sub-questions generated in the Think phase
    """
    logger.info("Deep research starting: %r", question[:80])

    # 1. Think
    sub_questions = await _think(question)
    logger.info("Sub-questions generated: %s", sub_questions)

    # 2. Search — parallel
    search_results = await asyncio.gather(*[_search(q) for q in sub_questions])

    # 3. Deduplicate and collect URLs
    all_urls: list[str] = []
    seen_urls: set[str] = set()
    for text in search_results:
        for url in _extract_urls(text):
            if url not in seen_urls:
                seen_urls.add(url)
                all_urls.append(url)
        if len(all_urls) >= _MAX_SOURCES:
            break

    logger.info("Fetching %d source URLs", len(all_urls))

    # 4. Fetch — parallel
    page_contents = await asyncio.gather(*[_fetch(url) for url in all_urls[:_MAX_SOURCES]])

    sources = [
        {"url": url, "content": content}
        for url, content in zip(all_urls, page_contents)
    ]

    # 5. Synthesize
    report = await _synthesize(question, sources)

    return {
        "report": report,
        "sources": [s["url"] for s in sources if s.get("content", "").strip()],
        "sub_questions": sub_questions,
    }
