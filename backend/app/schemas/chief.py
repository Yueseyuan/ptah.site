from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.orchestrator import OrchestratorRunStatus


class ChiefRunRequest(BaseModel):
    goal: str


class ChiefSubtaskOut(BaseModel):
    title: str
    description: str
    agent_name: str
    agent_run_id: int | None
    output: str | None


class WorkspaceFileOut(BaseModel):
    path: str
    size: int


class ChiefRunResult(BaseModel):
    run_id: int | None
    subtasks: list[ChiefSubtaskOut]
    merged_output: str | None
    workspace_files: list[WorkspaceFileOut] = []
    error: str | None = None


class ChiefRunSummary(BaseModel):
    id: int
    name: str
    status: OrchestratorRunStatus
    input: dict[str, Any] | None
    output: dict[str, Any] | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
