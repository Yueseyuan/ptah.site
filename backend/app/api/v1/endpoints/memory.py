from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.memory import (
    ContentType, MemoryCollection, MemoryEntry, MemoryEntryTag,
    MemoryLink, MemoryTag, MemoryVersion,
)
from app.models.user import User
from app.schemas.memory import (
    MemoryCollectionCreate, MemoryCollectionOut,
    MemoryEntryCreate, MemoryEntryOut, MemoryEntryUpdate,
    MemoryLinkCreate, MemoryLinkOut,
    MemoryTagCreate, MemoryTagOut,
    MemoryVersionCreate, MemoryVersionOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

@router.post("/collections", response_model=MemoryCollectionOut, status_code=status.HTTP_201_CREATED)
async def create_collection(body: MemoryCollectionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if (await db.execute(select(MemoryCollection).where(MemoryCollection.name == body.name))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Collection name already exists")
    col = MemoryCollection(**body.model_dump(), created_by_id=current_user.id)
    db.add(col)
    await db.commit()
    await db.refresh(col)
    return col


@router.get("/collections", response_model=list[MemoryCollectionOut])
async def list_collections(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(MemoryCollection).where(MemoryCollection.is_active.is_(True)).order_by(MemoryCollection.name))).scalars().all())


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

@router.post("/tags", response_model=MemoryTagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(body: MemoryTagCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    if (await db.execute(select(MemoryTag).where(MemoryTag.name == body.name))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag name already exists")
    tag = MemoryTag(**body.model_dump())
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.get("/tags", response_model=list[MemoryTagOut])
async def list_tags(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(MemoryTag).order_by(MemoryTag.name))).scalars().all())


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------

@router.post("/entries", response_model=MemoryEntryOut, status_code=status.HTTP_201_CREATED)
async def create_entry(body: MemoryEntryCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = MemoryEntry(**body.model_dump(), created_by_id=current_user.id)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/entries", response_model=list[MemoryEntryOut])
async def list_entries(
    collection_id: int | None = Query(None),
    content_type: ContentType | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(MemoryEntry).where(MemoryEntry.is_active.is_(True))
    if collection_id is not None:
        stmt = stmt.where(MemoryEntry.collection_id == collection_id)
    if content_type is not None:
        stmt = stmt.where(MemoryEntry.content_type == content_type)
    if q:
        stmt = stmt.where(or_(MemoryEntry.title.ilike(f"%{q}%"), MemoryEntry.content.ilike(f"%{q}%")))
    stmt = stmt.order_by(MemoryEntry.importance_score.desc(), MemoryEntry.id.desc())
    return list((await db.execute(stmt)).scalars().all())


@router.get("/entries/{entry_id}", response_model=MemoryEntryOut)
async def get_entry(entry_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load_entry(db, entry_id)


@router.patch("/entries/{entry_id}", response_model=MemoryEntryOut)
async def update_entry(entry_id: int, body: MemoryEntryUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    entry = await _load_entry(db, entry_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(entry, f, v)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_entry(entry_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    entry = await _load_entry(db, entry_id)
    entry.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Entry Tags (attach / detach)
# ---------------------------------------------------------------------------

@router.post("/entries/{entry_id}/tags/{tag_id}", status_code=status.HTTP_201_CREATED)
async def attach_tag(entry_id: int, tag_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_entry(db, entry_id)
    tag = (await db.execute(select(MemoryTag).where(MemoryTag.id == tag_id))).scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    existing = (await db.execute(select(MemoryEntryTag).where(MemoryEntryTag.entry_id == entry_id, MemoryEntryTag.tag_id == tag_id))).scalar_one_or_none()
    if existing:
        return {"entry_id": entry_id, "tag_id": tag_id}
    et = MemoryEntryTag(entry_id=entry_id, tag_id=tag_id)
    db.add(et)
    await db.commit()
    return {"entry_id": entry_id, "tag_id": tag_id}


@router.delete("/entries/{entry_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_tag(entry_id: int, tag_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    et = (await db.execute(select(MemoryEntryTag).where(MemoryEntryTag.entry_id == entry_id, MemoryEntryTag.tag_id == tag_id))).scalar_one_or_none()
    if et is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag association not found")
    await db.delete(et)
    await db.commit()


@router.get("/entries/{entry_id}/tags", response_model=list[MemoryTagOut])
async def list_entry_tags(entry_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_entry(db, entry_id)
    ets = (await db.execute(select(MemoryEntryTag).where(MemoryEntryTag.entry_id == entry_id))).scalars().all()
    tag_ids = [et.tag_id for et in ets]
    if not tag_ids:
        return []
    tags = (await db.execute(select(MemoryTag).where(MemoryTag.id.in_(tag_ids)))).scalars().all()
    return list(tags)


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

@router.post("/entries/{entry_id}/versions", response_model=MemoryVersionOut, status_code=status.HTTP_201_CREATED)
async def create_version(entry_id: int, body: MemoryVersionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load_entry(db, entry_id)
    last = (await db.execute(
        select(MemoryVersion).where(MemoryVersion.entry_id == entry_id).order_by(MemoryVersion.version_number.desc()).limit(1)
    )).scalar_one_or_none()
    next_num = (last.version_number + 1) if last else 1
    ver = MemoryVersion(**body.model_dump(), entry_id=entry_id, version_number=next_num, created_by_id=current_user.id)
    db.add(ver)
    await db.commit()
    await db.refresh(ver)
    return ver


@router.get("/entries/{entry_id}/versions", response_model=list[MemoryVersionOut])
async def list_versions(entry_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_entry(db, entry_id)
    return list((await db.execute(select(MemoryVersion).where(MemoryVersion.entry_id == entry_id).order_by(MemoryVersion.version_number.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

@router.post("/links", response_model=MemoryLinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(body: MemoryLinkCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load_entry(db, body.source_entry_id)
    await _load_entry(db, body.target_entry_id)
    link = MemoryLink(**body.model_dump(), created_by_id=current_user.id)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.get("/links", response_model=list[MemoryLinkOut])
async def list_links(entry_id: int = Query(...), db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(MemoryLink).where(
        or_(MemoryLink.source_entry_id == entry_id, MemoryLink.target_entry_id == entry_id)
    ).order_by(MemoryLink.id.desc())
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/search", response_model=list[MemoryEntryOut])
async def search_entries(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(MemoryEntry).where(
        MemoryEntry.is_active.is_(True),
        or_(MemoryEntry.title.ilike(f"%{q}%"), MemoryEntry.content.ilike(f"%{q}%")),
    ).order_by(MemoryEntry.importance_score.desc()).limit(50)
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_entry(db: AsyncSession, entry_id: int) -> MemoryEntry:
    entry = (await db.execute(select(MemoryEntry).where(MemoryEntry.id == entry_id))).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory entry not found")
    return entry
