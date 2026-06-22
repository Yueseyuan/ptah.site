import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, utcnow


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StageType(str, enum.Enum):
    LICENSE = "license"
    SECURITY = "security"
    DEPENDENCY = "dependency"
    CAPABILITY = "capability"
    INTEGRATION = "integration"


class StageVerdict(str, enum.Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


class RepoClassification(str, enum.Enum):
    USE_DIRECTLY = "use_directly"
    MODIFY_FIRST = "modify_first"
    REFERENCE_ONLY = "reference_only"
    DO_NOT_USE = "do_not_use"


class RepoReview(Base, TimestampMixin):
    __tablename__ = "repo_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    repo_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    status: Mapped[ReviewStatus] = mapped_column(
        SAEnum(ReviewStatus, native_enum=False), default=ReviewStatus.PENDING, nullable=False, index=True
    )
    classification: Mapped[RepoClassification | None] = mapped_column(
        SAEnum(RepoClassification, native_enum=False), nullable=True
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewStage(Base):
    __tablename__ = "review_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repo_reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_type: Mapped[StageType] = mapped_column(
        SAEnum(StageType, native_enum=False), nullable=False
    )
    verdict: Mapped[StageVerdict] = mapped_column(
        SAEnum(StageVerdict, native_enum=False), default=StageVerdict.SKIP, nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReviewFinding(Base):
    __tablename__ = "review_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("review_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReviewReport(Base):
    __tablename__ = "review_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repo_reviews.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    classification: Mapped[RepoClassification] = mapped_column(
        SAEnum(RepoClassification, native_enum=False), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    blockers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    format: Mapped[str] = mapped_column(String(20), default="markdown", nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
