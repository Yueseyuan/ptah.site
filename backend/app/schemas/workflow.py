from datetime import datetime

from pydantic import BaseModel

from app.models.workflow import StepStatus, StepType, WorkflowRunStatus, WorkflowStatus


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    config: dict | None = None


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: WorkflowStatus | None = None
    config: dict | None = None


class WorkflowOut(BaseModel):
    id: int
    name: str
    description: str | None
    status: WorkflowStatus
    config: dict | None
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowStepCreate(BaseModel):
    name: str
    step_type: StepType
    order_index: int = 0
    config: dict | None = None
    resource_id: int | None = None
    depends_on_step_ids: list[int] | None = None


class WorkflowStepOut(BaseModel):
    id: int
    workflow_id: int
    name: str
    step_type: StepType
    order_index: int
    config: dict | None
    resource_id: int | None
    depends_on_step_ids: list | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunCreate(BaseModel):
    input: dict | None = None


class WorkflowRunOut(BaseModel):
    id: int
    workflow_id: int
    triggered_by_id: int | None
    status: WorkflowRunStatus
    input: dict | None
    output: dict | None
    error: str | None
    current_step_id: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunEventOut(BaseModel):
    id: int
    run_id: int
    step_id: int | None
    event_type: str
    status: StepStatus
    data: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
