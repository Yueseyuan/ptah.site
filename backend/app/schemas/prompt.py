from datetime import datetime

from pydantic import BaseModel, Field

from app.models.prompt import PromptRunStatus, PromptType


class PromptTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    template_type: PromptType = PromptType.CHAT


class PromptTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class PromptTemplateOut(BaseModel):
    id: int
    name: str
    description: str | None
    template_type: PromptType
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptVersionCreate(BaseModel):
    version: str
    system_prompt: str | None = None
    user_template: str | None = None
    variables: list[str] | None = None
    is_current: bool = False


class PromptVersionOut(BaseModel):
    id: int
    template_id: int
    version: str
    system_prompt: str | None
    user_template: str | None
    variables: list | None
    is_current: bool
    published_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptRunCreate(BaseModel):
    variables_used: dict | None = None
    version_id: int | None = None
    model_provider: str | None = None
    model_id: str | None = None


class PromptRunOut(BaseModel):
    id: int
    template_id: int
    version_id: int | None
    triggered_by_id: int
    status: PromptRunStatus
    variables_used: dict | None
    rendered_prompt: dict | None
    output: dict | None
    error: str | None
    model_provider: str | None
    model_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptEvaluationCreate(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    notes: str | None = None
    tags: list[str] | None = None


class PromptEvaluationOut(BaseModel):
    id: int
    version_id: int
    evaluated_by_id: int
    score: float
    notes: str | None
    tags: list | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptRiskPolicyCreate(BaseModel):
    required_approval_level: int = Field(default=0, ge=0, le=3)
    description: str | None = None


class PromptRiskPolicyOut(BaseModel):
    id: int
    template_id: int
    required_approval_level: int
    is_active: bool
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
