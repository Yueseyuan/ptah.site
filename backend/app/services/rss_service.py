"""RSS/Atom feed polling service.

Fetches feeds on a configurable interval and triggers Chief for each new item.
Uses stdlib xml.etree.ElementTree — no extra dependencies.
"""
import logging
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from app.models.rss_feed import RssFeed

logger = logging.getLogger(__name__)

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def _rss_job_id(feed_id: int) -> str:
    return f"rss_feed_{feed_id}"


def _parse_feed(xml_text: str) -> list[dict[str, str]]:
    """Parse RSS 2.0 or Atom 1.0 XML → list of {guid, title, link, summary}."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("RSS parse error: %s", exc)
        return []

    items: list[dict[str, str]] = []

    # Atom 1.0
    if root.tag == "{http://www.w3.org/2005/Atom}feed" or "Atom" in root.tag:
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
            title_el = entry.find("{http://www.w3.org/2005/Atom}title")
            summary_el = entry.find("{http://www.w3.org/2005/Atom}summary") or entry.find(
                "{http://www.w3.org/2005/Atom}content"
            )
            id_el = entry.find("{http://www.w3.org/2005/Atom}id")
            items.append(
                {
                    "guid": (id_el.text or link) if id_el is not None else link,
                    "title": title_el.text or "" if title_el is not None else "",
                    "link": link,
                    "summary": (summary_el.text or "") if summary_el is not None else "",
                }
            )
        return items

    # RSS 2.0
    channel = root.find("channel")
    if channel is None:
        return []
    for item in channel.findall("item"):
        guid_el = item.find("guid")
        link_el = item.find("link")
        link = link_el.text or "" if link_el is not None else ""
        guid = (guid_el.text or link) if guid_el is not None else link
        title_el = item.find("title")
        desc_el = item.find("description")
        items.append(
            {
                "guid": guid,
                "title": title_el.text or "" if title_el is not None else "",
                "link": link,
                "summary": desc_el.text or "" if desc_el is not None else "",
            }
        )
    return items


async def fetch_feed_items(url: str) -> list[dict[str, str]]:
    """Fetch and parse a feed URL. Returns newest-first items."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "APEX-RSS/1.0"})
            resp.raise_for_status()
            return _parse_feed(resp.text)
    except Exception as exc:
        logger.warning("Failed to fetch feed %s: %s", url, exc)
        return []


async def _check_rss_feed(feed_id: int) -> None:
    """Check a feed for new items and trigger Chief for each one."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.services.chief import run_chief

    async with AsyncSessionLocal() as db:
        feed: RssFeed | None = (
            await db.execute(select(RssFeed).where(RssFeed.id == feed_id))
        ).scalar_one_or_none()
        if not feed or not feed.enabled:
            return

        items = await fetch_feed_items(feed.url)
        if not items:
            feed.last_checked_at = datetime.now(timezone.utc)
            feed.last_error = "Feed returned no items or failed to parse"
            await db.commit()
            return

        # Find new items (those with guids we haven't seen yet)
        last_guid = feed.last_item_guid
        new_items: list[dict[str, str]] = []
        for item in items:
            if item["guid"] == last_guid:
                break
            new_items.append(item)

        feed.last_checked_at = datetime.now(timezone.utc)
        feed.last_item_guid = items[0]["guid"]  # mark newest as seen
        feed.last_error = None
        await db.commit()

    if not new_items:
        logger.debug("No new items for feed %d (%s)", feed_id, feed.name)
        return

    logger.info("Feed %d: %d new item(s)", feed_id, len(new_items))

    for item in new_items:
        goal = feed.goal_template.format(
            title=item.get("title", ""),
            link=item.get("link", ""),
            summary=(item.get("summary") or "")[:500],
        )
        try:
            async with AsyncSessionLocal() as db:
                await run_chief(goal=goal, db=db, triggered_by_id=feed.created_by_id)
            async with AsyncSessionLocal() as db:
                f = (await db.execute(select(RssFeed).where(RssFeed.id == feed_id))).scalar_one_or_none()
                if f:
                    f.run_count = (f.run_count or 0) + 1
                    await db.commit()
        except Exception as exc:
            logger.error("Chief failed for feed %d item %r: %s", feed_id, item["title"], exc)
            async with AsyncSessionLocal() as db:
                f = (await db.execute(select(RssFeed).where(RssFeed.id == feed_id))).scalar_one_or_none()
                if f:
                    f.error_count = (f.error_count or 0) + 1
                    f.last_error = str(exc)[:500]
                    await db.commit()


def register_rss_feed(feed: RssFeed) -> None:
    """Register (or replace) an RSS polling job in APScheduler."""
    from app.services.scheduler_service import get_scheduler
    from apscheduler.triggers.interval import IntervalTrigger

    sched = get_scheduler()
    job_id = _rss_job_id(feed.id)

    if sched.get_job(job_id):
        sched.remove_job(job_id)

    if not feed.enabled:
        return

    minutes = max(5, feed.poll_interval_minutes)
    sched.add_job(
        _check_rss_feed,
        trigger=IntervalTrigger(minutes=minutes),
        id=job_id,
        args=[feed.id],
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("RSS feed %d (%s) registered — polling every %dm", feed.id, feed.name, minutes)


def unregister_rss_feed(feed_id: int) -> None:
    from app.services.scheduler_service import get_scheduler

    sched = get_scheduler()
    job_id = _rss_job_id(feed_id)
    if sched.get_job(job_id):
        sched.remove_job(job_id)


async def start_rss_polling() -> None:
    """Load all enabled RSS feeds from DB and register their polling jobs."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        feeds = list(
            (await db.execute(select(RssFeed).where(RssFeed.enabled.is_(True)))).scalars().all()
        )

    for feed in feeds:
        register_rss_feed(feed)

    logger.info("RSS polling started with %d active feed(s)", len(feeds))
