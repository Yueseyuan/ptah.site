from datetime import datetime

from pydantic import BaseModel

from app.models.context import ContextSourceType, ContextStatus, DecisionStatus, RebuildStatus


class ContextPackageCreate(BaseModel):
    name: str
    description: str | None = None
    agent_id: int | None = None
    task_type: str | None = None
    max_tokens: int = 8192


class ContextPackageUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    task_type: str | None = None
    status: ContextStatus | None = None
    max_tokens: int | None = None


class ContextPackageOut(BaseModel):
    id: int
    name: str
    description: str | None
    agent_id: int | None
    task_type: str | None
    status: ContextStatus
    token_count: int
    max_tokens: int
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContextSourceCreate(BaseModel):
    source_type: ContextSourceType
    source_id: str | None = None
    content: str | None = None
    token_count: int = 0
    priority: int = 5


class ContextSourceOut(BaseModel):
    id: int
    package_id: int
    source_type: ContextSourceType
    source_id: str | None
    content: str | None
    token_count: int
    priority: int
    is_included: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ContextRebuildRunOut(BaseModel):
    id: int
    package_id: int
    triggered_by_id: int | None
    status: RebuildStatus
    sources_scanned: int
    sources_included: int
    token_count: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectStateCreate(BaseModel):
    project_name: str
    state_type: str = "snapshot"
    data: dict = {}
    description: str | None = None


class ProjectStateOut(BaseModel):
    id: int
    project_name: str
    state_type: str
    data: dict
    description: str | None
    created_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionRecordCreate(BaseModel):
    title: str
    context: str | None = None
    decision: str | None = None
    consequences: str | None = None
    alternatives: list | None = None
    tags: list | None = None


class DecisionRecordUpdate(BaseModel):
    title: str | None = None
    status: DecisionStatus | None = None
    context: str | None = None
    decision: str | None = None
    consequences: str | None = None
    alternatives: list | None = None
    tags: list | None = None


class DecisionRecordOut(BaseModel):
    id: int
    title: str
    status: DecisionStatus
    context: str | None
    decision: str | None
    consequences: str | None
    alternatives: list | None
    tags: list | None
    created_by_id: int | None
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
