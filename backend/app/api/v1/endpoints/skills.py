from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.audit import AuditEventType
from app.models.skill import Skill, SkillCategory, SkillRiskPolicy, SkillRun, SkillRunStatus, SkillVersion
from app.models.user import User
from app.schemas.skill import (
    SkillCategoryCreate, SkillCategoryOut, SkillCreate, SkillOut,
    SkillRiskPolicyCreate, SkillRiskPolicyOut, SkillRunCreate, SkillRunOut,
    SkillUpdate, SkillVersionCreate, SkillVersionOut,
)
from app.services.audit import log_event

router = APIRouter()


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@router.post("/categories", response_model=SkillCategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(body: SkillCategoryCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    cat = SkillCategory(**body.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.get("/categories", response_model=list[SkillCategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(SkillCategory).order_by(SkillCategory.name))).scalars().all())


# ---------------------------------------------------------------------------
# Skills CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
async def create_skill(body: SkillCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if (await db.execute(select(Skill).where(Skill.name == body.name))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Skill name already exists")
    skill = Skill(**body.model_dump(), created_by_id=current_user.id)
    db.add(skill)
    await log_event(db, AuditEventType.SYSTEM_CHANGE, user_id=current_user.id, resource_type="skill", detail={"action": "create"})
    await db.commit()
    await db.refresh(skill)
    return skill


@router.get("", response_model=list[SkillOut])
async def list_skills(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(Skill).where(Skill.is_active.is_(True)).order_by(Skill.name))).scalars().all())


@router.get("/{skill_id}", response_model=SkillOut)
async def get_skill(skill_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load(db, skill_id)


@router.patch("/{skill_id}", response_model=SkillOut)
async def update_skill(skill_id: int, body: SkillUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    skill = await _load(db, skill_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(skill, f, v)
    await db.commit()
    await db.refresh(skill)
    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_skill(skill_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    skill = await _load(db, skill_id)
    skill.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

@router.post("/{skill_id}/versions", response_model=SkillVersionOut, status_code=status.HTTP_201_CREATED)
async def create_version(skill_id: int, body: SkillVersionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load(db, skill_id)
    if body.is_current:
        for v in (await db.execute(select(SkillVersion).where(SkillVersion.skill_id == skill_id, SkillVersion.is_current.is_(True)))).scalars().all():
            v.is_current = False
    ver = SkillVersion(**body.model_dump(), skill_id=skill_id, published_by_id=current_user.id)
    db.add(ver)
    await db.commit()
    await db.refresh(ver)
    return ver


@router.get("/{skill_id}/versions", response_model=list[SkillVersionOut])
async def list_versions(skill_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, skill_id)
    return list((await db.execute(select(SkillVersion).where(SkillVersion.skill_id == skill_id).order_by(SkillVersion.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.post("/{skill_id}/runs", response_model=SkillRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(skill_id: int, body: SkillRunCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load(db, skill_id)
    run = SkillRun(**body.model_dump(), skill_id=skill_id, triggered_by_id=current_user.id, status=SkillRunStatus.PENDING)
    db.add(run)
    await log_event(db, AuditEventType.SKILL_RUN, user_id=current_user.id, resource_type="skill", resource_id=str(skill_id))
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{skill_id}/runs", response_model=list[SkillRunOut])
async def list_runs(skill_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, skill_id)
    return list((await db.execute(select(SkillRun).where(SkillRun.skill_id == skill_id).order_by(SkillRun.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Risk policies
# ---------------------------------------------------------------------------

@router.post("/{skill_id}/risk-policies", response_model=SkillRiskPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_risk_policy(skill_id: int, body: SkillRiskPolicyCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, skill_id)
    policy = SkillRiskPolicy(**body.model_dump(), skill_id=skill_id)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load(db: AsyncSession, skill_id: int) -> Skill:
    skill = (await db.execute(select(Skill).where(Skill.id == skill_id))).scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill
