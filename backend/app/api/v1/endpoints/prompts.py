from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.audit import AuditEventType
from app.models.prompt import (
    PromptEvaluation, PromptRiskPolicy, PromptRun, PromptRunStatus,
    PromptTemplate, PromptVersion,
)
from app.models.user import User
from app.schemas.prompt import (
    PromptEvaluationCreate, PromptEvaluationOut, PromptRiskPolicyCreate,
    PromptRiskPolicyOut, PromptRunCreate, PromptRunOut, PromptTemplateCreate,
    PromptTemplateOut, PromptTemplateUpdate, PromptVersionCreate, PromptVersionOut,
)
from app.services.audit import log_event

router = APIRouter()


# ---------------------------------------------------------------------------
# Templates CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=PromptTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(body: PromptTemplateCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if (await db.execute(select(PromptTemplate).where(PromptTemplate.name == body.name))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Prompt name already exists")
    tmpl = PromptTemplate(**body.model_dump(), created_by_id=current_user.id)
    db.add(tmpl)
    await log_event(db, AuditEventType.SYSTEM_CHANGE, user_id=current_user.id, resource_type="prompt_template")
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("", response_model=list[PromptTemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(PromptTemplate).where(PromptTemplate.is_active.is_(True)).order_by(PromptTemplate.name))).scalars().all())


@router.get("/{template_id}", response_model=PromptTemplateOut)
async def get_template(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load(db, template_id)


@router.patch("/{template_id}", response_model=PromptTemplateOut)
async def update_template(template_id: int, body: PromptTemplateUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    tmpl = await _load(db, template_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(tmpl, f, v)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_template(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    tmpl = await _load(db, template_id)
    tmpl.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

@router.post("/{template_id}/versions", response_model=PromptVersionOut, status_code=status.HTTP_201_CREATED)
async def create_version(template_id: int, body: PromptVersionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load(db, template_id)
    if body.is_current:
        for v in (await db.execute(select(PromptVersion).where(PromptVersion.template_id == template_id, PromptVersion.is_current.is_(True)))).scalars().all():
            v.is_current = False
    ver = PromptVersion(**body.model_dump(), template_id=template_id, published_by_id=current_user.id)
    db.add(ver)
    await db.commit()
    await db.refresh(ver)
    return ver


@router.get("/{template_id}/versions", response_model=list[PromptVersionOut])
async def list_versions(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, template_id)
    return list((await db.execute(select(PromptVersion).where(PromptVersion.template_id == template_id).order_by(PromptVersion.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.post("/{template_id}/runs", response_model=PromptRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(template_id: int, body: PromptRunCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load(db, template_id)
    run = PromptRun(**body.model_dump(), template_id=template_id, triggered_by_id=current_user.id, status=PromptRunStatus.PENDING)
    db.add(run)
    await log_event(db, AuditEventType.PROMPT_RUN, user_id=current_user.id, resource_type="prompt_template", resource_id=str(template_id))
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{template_id}/runs", response_model=list[PromptRunOut])
async def list_runs(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, template_id)
    return list((await db.execute(select(PromptRun).where(PromptRun.template_id == template_id).order_by(PromptRun.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------

@router.post("/{template_id}/versions/{version_id}/evaluations", response_model=PromptEvaluationOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation(template_id: int, version_id: int, body: PromptEvaluationCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load(db, template_id)
    ver = (await db.execute(select(PromptVersion).where(PromptVersion.id == version_id, PromptVersion.template_id == template_id))).scalar_one_or_none()
    if ver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    ev = PromptEvaluation(**body.model_dump(), version_id=version_id, evaluated_by_id=current_user.id)
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


@router.get("/{template_id}/versions/{version_id}/evaluations", response_model=list[PromptEvaluationOut])
async def list_evaluations(template_id: int, version_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(PromptEvaluation).where(PromptEvaluation.version_id == version_id).order_by(PromptEvaluation.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Risk policies
# ---------------------------------------------------------------------------

@router.post("/{template_id}/risk-policies", response_model=PromptRiskPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_risk_policy(template_id: int, body: PromptRiskPolicyCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, template_id)
    policy = PromptRiskPolicy(**body.model_dump(), template_id=template_id)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load(db: AsyncSession, template_id: int) -> PromptTemplate:
    tmpl = (await db.execute(select(PromptTemplate).where(PromptTemplate.id == template_id))).scalar_one_or_none()
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found")
    return tmpl
