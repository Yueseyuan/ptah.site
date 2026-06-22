from datetime import datetime

from pydantic import BaseModel, Field

from app.models.orchestrator import BranchStatus, MergeStrategy, OrchestratorRunStatus, TaskStatus


class OrchestratorTaskCreate(BaseModel):
    title: str
    description: str | None = None
    task_type: str
    priority: int = Field(default=5, ge=1, le=10)
    input: dict | None = None
    required_capabilities: list[str] | None = None


class OrchestratorTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=10)
    output: dict | None = None
    error: str | None = None


class OrchestratorTaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    task_type: str
    priority: int
    status: TaskStatus
    input: dict | None
    output: dict | None
    error: str | None
    required_capabilities: list | None
    created_by_id: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskAssignmentCreate(BaseModel):
    agent_id: int
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    is_primary: bool = True


class TaskAssignmentOut(BaseModel):
    id: int
    task_id: int
    agent_id: int
    assigned_by_id: int | None
    score: float
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskDependencyCreate(BaseModel):
    depends_on_task_id: int


class TaskDependencyOut(BaseModel):
    id: int
    task_id: int
    depends_on_task_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrchestratorRunCreate(BaseModel):
    name: str
    input: dict | None = None


class OrchestratorRunOut(BaseModel):
    id: int
    name: str
    status: OrchestratorRunStatus
    input: dict | None
    output: dict | None
    error: str | None
    triggered_by_id: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrchestratorDecisionCreate(BaseModel):
    task_id: int | None = None
    decision_type: str
    rationale: str | None = None
    data: dict | None = None


class OrchestratorDecisionOut(BaseModel):
    id: int
    run_id: int
    task_id: int | None
    decision_type: str
    rationale: str | None
    data: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrchestratorPlanCreate(BaseModel):
    steps: list = []
    rationale: str | None = None


class OrchestratorPlanOut(BaseModel):
    id: int
    run_id: int
    steps: list
    rationale: str | None
    is_approved: bool
    approved_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskBranchCreate(BaseModel):
    name: str
    description: str | None = None
    merge_strategy: MergeStrategy = MergeStrategy.FIRST_SUCCESS


class TaskBranchOut(BaseModel):
    id: int
    task_id: int
    name: str
    description: str | None
    merge_strategy: MergeStrategy
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BranchRunCreate(BaseModel):
    agent_id: int | None = None


class BranchRunOut(BaseModel):
    id: int
    branch_id: int
    agent_id: int | None
    status: BranchStatus
    output: dict | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResultMergeCreate(BaseModel):
    merged_output: dict | None = None
    strategy_used: MergeStrategy
    branch_run_ids: list[int] | None = None
    notes: str | None = None


class ResultMergeOut(BaseModel):
    id: int
    branch_id: int
    merged_output: dict | None
    strategy_used: MergeStrategy
    branch_run_ids: list | None
    notes: str | None
    created_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
