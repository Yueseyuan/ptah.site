from datetime import datetime

from pydantic import BaseModel, Field

from app.models.tool import ToolRunStatus, ToolType


class ToolCreate(BaseModel):
    name: str
    description: str | None = None
    tool_type: ToolType = ToolType.FUNCTION


class ToolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ToolOut(BaseModel):
    id: int
    name: str
    description: str | None
    tool_type: ToolType
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolVersionCreate(BaseModel):
    version: str
    parameters_schema: dict | None = None
    handler_config: dict | None = None
    is_current: bool = False


class ToolVersionOut(BaseModel):
    id: int
    tool_id: int
    version: str
    parameters_schema: dict | None
    handler_config: dict | None
    is_current: bool
    published_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolRunCreate(BaseModel):
    input: dict | None = None
    version_id: int | None = None


class ToolRunOut(BaseModel):
    id: int
    tool_id: int
    version_id: int | None
    triggered_by_id: int
    status: ToolRunStatus
    input: dict | None
    output: dict | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolPermissionCreate(BaseModel):
    user_id: int | None = None
    is_public: bool = False


class ToolPermissionOut(BaseModel):
    id: int
    tool_id: int
    user_id: int | None
    is_public: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolRiskPolicyCreate(BaseModel):
    required_approval_level: int = Field(default=0, ge=0, le=3)
    description: str | None = None


class ToolRiskPolicyOut(BaseModel):
    id: int
    tool_id: int
    required_approval_level: int
    is_active: bool
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
