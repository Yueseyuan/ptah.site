from datetime import datetime

from pydantic import BaseModel, Field

from app.models.skill import SkillRunStatus


class SkillCategoryCreate(BaseModel):
    name: str
    description: str | None = None


class SkillCategoryOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class SkillCreate(BaseModel):
    name: str
    description: str | None = None
    category_id: int | None = None


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: int | None = None
    is_active: bool | None = None


class SkillOut(BaseModel):
    id: int
    name: str
    description: str | None
    category_id: int | None
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillVersionCreate(BaseModel):
    version: str
    entry_point: str | None = None
    code_config: dict | None = None
    model_provider: str | None = None
    model_id: str | None = None
    is_current: bool = False


class SkillVersionOut(BaseModel):
    id: int
    skill_id: int
    version: str
    entry_point: str | None
    code_config: dict | None
    model_provider: str | None
    model_id: str | None
    is_current: bool
    published_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillRunCreate(BaseModel):
    input: dict | None = None
    version_id: int | None = None


class SkillRunOut(BaseModel):
    id: int
    skill_id: int
    version_id: int | None
    triggered_by_id: int
    status: SkillRunStatus
    input: dict | None
    output: dict | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillRiskPolicyCreate(BaseModel):
    required_approval_level: int = Field(default=0, ge=0, le=3)
    description: str | None = None


class SkillRiskPolicyOut(BaseModel):
    id: int
    skill_id: int
    required_approval_level: int
    is_active: bool
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
