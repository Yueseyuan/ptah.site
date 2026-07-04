from datetime import datetime

from pydantic import BaseModel, Field

from app.models.memory import ContentType, MemoryLinkType


class MemoryCollectionCreate(BaseModel):
    name: str
    description: str | None = None


class MemoryCollectionOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryTagCreate(BaseModel):
    name: str
    color: str | None = None
    description: str | None = None


class MemoryTagOut(BaseModel):
    id: int
    name: str
    color: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryEntryCreate(BaseModel):
    title: str
    content: str
    content_type: ContentType = ContentType.TEXT
    collection_id: int | None = None
    source: str | None = None
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryEntryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    content_type: ContentType | None = None
    collection_id: int | None = None
    source: str | None = None
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)


class MemoryEntryOut(BaseModel):
    id: int
    collection_id: int | None
    title: str
    content: str
    content_type: ContentType
    source: str | None
    importance_score: float
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryLinkCreate(BaseModel):
    source_entry_id: int
    target_entry_id: int
    link_type: MemoryLinkType = MemoryLinkType.RELATED
    strength: float = Field(default=1.0, ge=0.0, le=1.0)


class MemoryLinkOut(BaseModel):
    id: int
    source_entry_id: int
    target_entry_id: int
    link_type: MemoryLinkType
    strength: float
    created_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryVersionCreate(BaseModel):
    content: str
    content_type: ContentType = ContentType.TEXT
    change_summary: str | None = None


class MemoryVersionOut(BaseModel):
    id: int
    entry_id: int
    content: str
    content_type: ContentType
    version_number: int
    change_summary: str | None
    created_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
