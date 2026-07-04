from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.audit import AuditEventType
from app.models.repo_review import (
    RepoClassification, RepoReview, ReviewFinding, ReviewReport,
    ReviewStage, ReviewStatus, StageType,
)
from app.models.user import User
from app.schemas.repo_review import (
    RepoReviewCreate, RepoReviewOut, ReviewFindingCreate, ReviewFindingOut,
    ReviewReportCreate, ReviewReportOut, ReviewStageCreate, ReviewStageOut,
    ReviewStatusUpdate,
)
from app.services.audit import log_event

router = APIRouter()

# Stage ordering for the 5-stage pipeline
_STAGE_ORDER = [
    StageType.LICENSE,
    StageType.SECURITY,
    StageType.DEPENDENCY,
    StageType.CAPABILITY,
    StageType.INTEGRATION,
]


# ---------------------------------------------------------------------------
# Reviews CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=RepoReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(body: RepoReviewCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    review = RepoReview(
        repo_url=body.repo_url,
        repo_name=body.repo_name,
        branch=body.branch,
        metadata_=body.metadata_,
        triggered_by_id=current_user.id,
    )
    db.add(review)
    await log_event(db, AuditEventType.SYSTEM_CHANGE, user_id=current_user.id, resource_type="repo_review")
    await db.commit()
    await db.refresh(review)
    return review


@router.get("", response_model=list[RepoReviewOut])
async def list_reviews(
    status_filter: ReviewStatus | None = Query(None, alias="status"),
    classification: RepoClassification | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(RepoReview).order_by(RepoReview.id.desc())
    if status_filter:
        stmt = stmt.where(RepoReview.status == status_filter)
    if classification:
        stmt = stmt.where(RepoReview.classification == classification)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{review_id}", response_model=RepoReviewOut)
async def get_review(review_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load(db, review_id)


@router.patch("/{review_id}/status", response_model=RepoReviewOut)
async def update_status(review_id: int, body: ReviewStatusUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    review = await _load(db, review_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(review, f, v)
    await db.commit()
    await db.refresh(review)
    return review


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

@router.post("/{review_id}/stages", response_model=ReviewStageOut, status_code=status.HTTP_201_CREATED)
async def create_stage(review_id: int, body: ReviewStageCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, review_id)
    stage = ReviewStage(**body.model_dump(), review_id=review_id)
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return stage


@router.get("/{review_id}/stages", response_model=list[ReviewStageOut])
async def list_stages(review_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, review_id)
    stages = list((await db.execute(select(ReviewStage).where(ReviewStage.review_id == review_id))).scalars().all())
    stages.sort(key=lambda s: _STAGE_ORDER.index(s.stage_type) if s.stage_type in _STAGE_ORDER else 99)
    return stages


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@router.post("/{review_id}/stages/{stage_id}/findings", response_model=ReviewFindingOut, status_code=status.HTTP_201_CREATED)
async def create_finding(review_id: int, stage_id: int, body: ReviewFindingCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, review_id)
    stage = (await db.execute(select(ReviewStage).where(ReviewStage.id == stage_id, ReviewStage.review_id == review_id))).scalar_one_or_none()
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found")
    finding = ReviewFinding(**body.model_dump(), stage_id=stage_id)
    db.add(finding)
    await db.commit()
    await db.refresh(finding)
    return finding


@router.get("/{review_id}/stages/{stage_id}/findings", response_model=list[ReviewFindingOut])
async def list_findings(review_id: int, stage_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, review_id)
    stage = (await db.execute(select(ReviewStage).where(ReviewStage.id == stage_id, ReviewStage.review_id == review_id))).scalar_one_or_none()
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found")
    return list((await db.execute(select(ReviewFinding).where(ReviewFinding.stage_id == stage_id).order_by(ReviewFinding.id))).scalars().all())


@router.get("/{review_id}/findings", response_model=list[ReviewFindingOut])
async def list_all_findings(
    review_id: int,
    severity: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _load(db, review_id)
    stage_ids_row = (await db.execute(select(ReviewStage.id).where(ReviewStage.review_id == review_id))).scalars().all()
    if not stage_ids_row:
        return []
    stmt = select(ReviewFinding).where(ReviewFinding.stage_id.in_(list(stage_ids_row)))
    if severity:
        stmt = stmt.where(ReviewFinding.severity == severity)
    stmt = stmt.order_by(ReviewFinding.id)
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Report (generate / get)
# ---------------------------------------------------------------------------

@router.post("/{review_id}/report", response_model=ReviewReportOut, status_code=status.HTTP_201_CREATED)
async def generate_report(review_id: int, body: ReviewReportCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    review = await _load(db, review_id)
    existing = (await db.execute(select(ReviewReport).where(ReviewReport.review_id == review_id))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report already generated for this review")
    # Update review classification and score
    review.classification = body.classification
    review.overall_score = body.overall_score
    review.summary = body.executive_summary
    report = ReviewReport(**body.model_dump(), review_id=review_id, generated_by_id=current_user.id)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/{review_id}/report", response_model=ReviewReportOut)
async def get_report(review_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, review_id)
    report = (await db.execute(select(ReviewReport).where(ReviewReport.review_id == review_id))).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not yet generated")
    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load(db: AsyncSession, review_id: int) -> RepoReview:
    review = (await db.execute(select(RepoReview).where(RepoReview.id == review_id))).scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review
