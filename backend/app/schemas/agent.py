from datetime import datetime

from pydantic import BaseModel, Field

from app.models.agent import AgentCapabilityType, AgentRunStatus


class AgentCreate(BaseModel):
    name: str
    description: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class AgentOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentVersionCreate(BaseModel):
    version: str
    system_prompt: str | None = None
    model_provider: str | None = None
    model_id: str | None = None
    config: dict | None = None
    is_current: bool = False


class AgentVersionOut(BaseModel):
    id: int
    agent_id: int
    version: str
    system_prompt: str | None
    model_provider: str | None
    model_id: str | None
    config: dict | None
    is_current: bool
    published_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentCapabilityOut(BaseModel):
    id: int
    agent_id: int
    capability_type: AgentCapabilityType

    model_config = {"from_attributes": True}


class AgentRunCreate(BaseModel):
    input: dict | None = None
    model_provider: str | None = None
    model_id: str | None = None
    version_id: int | None = None


class AgentRunEventOut(BaseModel):
    id: int
    run_id: int
    event_type: str
    data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunOut(BaseModel):
    id: int
    agent_id: int
    version_id: int | None
    triggered_by_id: int
    status: AgentRunStatus
    input: dict | None
    output: dict | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    model_provider: str | None
    model_id: str | None
    created_at: datetime
    events: list[AgentRunEventOut] = []

    model_config = {"from_attributes": True}


class AgentRiskPolicyCreate(BaseModel):
    capability_type: AgentCapabilityType | None = None
    required_approval_level: int = Field(default=0, ge=0, le=3)
    description: str | None = None


class AgentRiskPolicyOut(BaseModel):
    id: int
    agent_id: int
    capability_type: AgentCapabilityType | None
    required_approval_level: int
    is_active: bool
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
