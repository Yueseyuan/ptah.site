from datetime import datetime

from pydantic import BaseModel, Field

from app.models.repo_review import RepoClassification, ReviewStatus, StageType, StageVerdict


class RepoReviewCreate(BaseModel):
    repo_url: str
    repo_name: str
    branch: str = "main"
    metadata_: dict | None = Field(default=None, alias="metadata")

    model_config = {"populate_by_name": True}


class RepoReviewOut(BaseModel):
    id: int
    repo_url: str
    repo_name: str
    branch: str
    status: ReviewStatus
    classification: RepoClassification | None
    overall_score: float | None
    summary: str | None
    triggered_by_id: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewStageCreate(BaseModel):
    stage_type: StageType
    verdict: StageVerdict = StageVerdict.SKIP
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    findings: list | None = None
    notes: str | None = None
    duration_ms: int | None = None


class ReviewStageOut(BaseModel):
    id: int
    review_id: int
    stage_type: StageType
    verdict: StageVerdict
    score: float | None
    findings: list | None
    notes: str | None
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewFindingCreate(BaseModel):
    severity: str
    category: str
    title: str
    description: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    remediation: str | None = None


class ReviewFindingOut(BaseModel):
    id: int
    stage_id: int
    severity: str
    category: str
    title: str
    description: str | None
    file_path: str | None
    line_number: int | None
    remediation: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewReportCreate(BaseModel):
    classification: RepoClassification
    overall_score: float = Field(ge=0.0, le=1.0)
    executive_summary: str | None = None
    stage_scores: dict = {}
    recommendations: list | None = None
    blockers: list | None = None
    format: str = "markdown"
    content: str | None = None


class ReviewReportOut(BaseModel):
    id: int
    review_id: int
    classification: RepoClassification
    overall_score: float
    executive_summary: str | None
    stage_scores: dict
    recommendations: list | None
    blockers: list | None
    format: str
    content: str | None
    generated_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewStatusUpdate(BaseModel):
    status: ReviewStatus
    classification: RepoClassification | None = None
    overall_score: float | None = Field(default=None, ge=0.0, le=1.0)
    summary: str | None = None
