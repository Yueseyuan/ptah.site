from datetime import datetime

from pydantic import BaseModel, Field

from app.models.approval import ApprovalStatus


class ApprovalRequestCreate(BaseModel):
    level: int = Field(ge=0, le=3)
    action_type: str
    resource_type: str | None = None
    resource_id: str | None = None
    payload: dict | None = None
    reason: str | None = None


class ApprovalDecisionOut(BaseModel):
    id: int
    request_id: int
    verdict: str
    decided_by_id: int
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalRequestOut(BaseModel):
    id: int
    level: int
    status: ApprovalStatus
    requester_id: int
    action_type: str
    resource_type: str | None
    resource_id: str | None
    payload: dict | None
    reason: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    decision: ApprovalDecisionOut | None = None

    model_config = {"from_attributes": True}


class ApprovalRequestList(BaseModel):
    items: list[ApprovalRequestOut]
    total: int
    page: int
    limit: int


class DecideIn(BaseModel):
    note: str | None = None


class RiskPolicyCreate(BaseModel):
    resource_type: str
    action_type: str
    required_level: int = Field(ge=0, le=3)
    description: str | None = None


class RiskPolicyOut(BaseModel):
    id: int
    resource_type: str
    action_type: str
    required_level: int
    is_active: bool
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActionPolicyCreate(BaseModel):
    name: str
    resource_type: str
    action_type: str
    timeout_minutes: int = Field(default=60, ge=1)
    description: str | None = None


class ActionPolicyOut(BaseModel):
    id: int
    name: str
    resource_type: str
    action_type: str
    timeout_minutes: int
    is_active: bool
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
