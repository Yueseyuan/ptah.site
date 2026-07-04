"""RSS feed management endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.rss_feed import RssFeed
from app.models.user import User
from app.services.rss_service import register_rss_feed, unregister_rss_feed, fetch_feed_items

router = APIRouter()


class RssFeedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=5)
    goal_template: str = Field(
        default="Research and summarize this article: {title}\n\nURL: {link}\n\nSummary: {summary}",
    )
    poll_interval_minutes: int = Field(default=60, ge=5, le=10080)
    enabled: bool = True


class RssFeedUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    goal_template: Optional[str] = None
    poll_interval_minutes: Optional[int] = Field(default=None, ge=5, le=10080)
    enabled: Optional[bool] = None


class RssFeedOut(BaseModel):
    id: int
    name: str
    url: str
    goal_template: str
    poll_interval_minutes: int
    enabled: bool
    last_checked_at: Optional[datetime]
    last_item_guid: Optional[str]
    run_count: int
    error_count: int
    last_error: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PreviewItem(BaseModel):
    guid: str
    title: str
    link: str
    summary: str


@router.get("/", response_model=list[RssFeedOut])
async def list_feeds(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[RssFeedOut]:
    feeds = (await db.execute(select(RssFeed).order_by(RssFeed.created_at.desc()))).scalars().all()
    return [RssFeedOut.model_validate(f) for f in feeds]


@router.post("/", response_model=RssFeedOut, status_code=status.HTTP_201_CREATED)
async def create_feed(
    body: RssFeedCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RssFeedOut:
    feed = RssFeed(
        name=body.name,
        url=body.url,
        goal_template=body.goal_template,
        poll_interval_minutes=body.poll_interval_minutes,
        enabled=body.enabled,
        created_by_id=current_user.id,
    )
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    if feed.enabled:
        register_rss_feed(feed)
    return RssFeedOut.model_validate(feed)


@router.get("/{feed_id}", response_model=RssFeedOut)
async def get_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RssFeedOut:
    feed = (await db.execute(select(RssFeed).where(RssFeed.id == feed_id))).scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return RssFeedOut.model_validate(feed)


@router.patch("/{feed_id}", response_model=RssFeedOut)
async def update_feed(
    feed_id: int,
    body: RssFeedUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RssFeedOut:
    feed = (await db.execute(select(RssFeed).where(RssFeed.id == feed_id))).scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    if body.name is not None:
        feed.name = body.name
    if body.url is not None:
        feed.url = body.url
    if body.goal_template is not None:
        feed.goal_template = body.goal_template
    if body.poll_interval_minutes is not None:
        feed.poll_interval_minutes = body.poll_interval_minutes
    if body.enabled is not None:
        feed.enabled = body.enabled

    await db.commit()
    await db.refresh(feed)
    register_rss_feed(feed)  # re-registers or removes job based on enabled state
    return RssFeedOut.model_validate(feed)


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    feed = (await db.execute(select(RssFeed).where(RssFeed.id == feed_id))).scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    unregister_rss_feed(feed_id)
    await db.delete(feed)
    await db.commit()


@router.post("/{feed_id}/check-now", response_model=RssFeedOut)
async def check_feed_now(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RssFeedOut:
    """Trigger an immediate poll of this feed (ignores schedule)."""
    feed = (await db.execute(select(RssFeed).where(RssFeed.id == feed_id))).scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    from app.services.rss_service import _check_rss_feed
    await _check_rss_feed(feed_id)

    await db.refresh(feed)
    return RssFeedOut.model_validate(feed)


@router.get("/{feed_id}/preview", response_model=list[PreviewItem])
async def preview_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[PreviewItem]:
    """Fetch and return the latest items from the feed without triggering Chief."""
    feed = (await db.execute(select(RssFeed).where(RssFeed.id == feed_id))).scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    items = await fetch_feed_items(feed.url)
    return [PreviewItem(**item) for item in items[:10]]
