from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.context import (
    ContextPackage, ContextRebuildRun, ContextSource,
    DecisionRecord, ProjectState, RebuildStatus,
)
from app.models.user import User
from app.schemas.context import (
    ContextPackageCreate, ContextPackageOut, ContextPackageUpdate,
    ContextRebuildRunOut, ContextSourceCreate, ContextSourceOut,
    DecisionRecordCreate, DecisionRecordOut, DecisionRecordUpdate,
    ProjectStateCreate, ProjectStateOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------

@router.post("/packages", response_model=ContextPackageOut, status_code=status.HTTP_201_CREATED)
async def create_package(body: ContextPackageCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    pkg = ContextPackage(**body.model_dump(), created_by_id=current_user.id)
    db.add(pkg)
    await db.commit()
    await db.refresh(pkg)
    return pkg


@router.get("/packages", response_model=list[ContextPackageOut])
async def list_packages(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(ContextPackage).where(ContextPackage.is_active.is_(True)).order_by(ContextPackage.id.desc()))).scalars().all())


@router.get("/packages/{package_id}", response_model=ContextPackageOut)
async def get_package(package_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load_package(db, package_id)


@router.patch("/packages/{package_id}", response_model=ContextPackageOut)
async def update_package(package_id: int, body: ContextPackageUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    pkg = await _load_package(db, package_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(pkg, f, v)
    await db.commit()
    await db.refresh(pkg)
    return pkg


@router.delete("/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_package(package_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    pkg = await _load_package(db, package_id)
    pkg.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@router.post("/packages/{package_id}/sources", response_model=ContextSourceOut, status_code=status.HTTP_201_CREATED)
async def add_source(package_id: int, body: ContextSourceCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_package(db, package_id)
    src = ContextSource(**body.model_dump(), package_id=package_id)
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return src


@router.get("/packages/{package_id}/sources", response_model=list[ContextSourceOut])
async def list_sources(package_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_package(db, package_id)
    return list((await db.execute(select(ContextSource).where(ContextSource.package_id == package_id).order_by(ContextSource.priority.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Rebuild Runs
# ---------------------------------------------------------------------------

@router.post("/packages/{package_id}/rebuild", response_model=ContextRebuildRunOut, status_code=status.HTTP_201_CREATED)
async def trigger_rebuild(package_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    pkg = await _load_package(db, package_id)
    run = ContextRebuildRun(package_id=package_id, triggered_by_id=current_user.id, status=RebuildStatus.PENDING)
    db.add(run)
    pkg.status = "building"
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/packages/{package_id}/rebuilds", response_model=list[ContextRebuildRunOut])
async def list_rebuilds(package_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_package(db, package_id)
    return list((await db.execute(select(ContextRebuildRun).where(ContextRebuildRun.package_id == package_id).order_by(ContextRebuildRun.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Project States
# ---------------------------------------------------------------------------

@router.post("/states", response_model=ProjectStateOut, status_code=status.HTTP_201_CREATED)
async def create_state(body: ProjectStateCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    state = ProjectState(**body.model_dump(), created_by_id=current_user.id)
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return state


@router.get("/states", response_model=list[ProjectStateOut])
async def list_states(
    project_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(ProjectState).order_by(ProjectState.id.desc())
    if project_name:
        stmt = stmt.where(ProjectState.project_name == project_name)
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Decision Records
# ---------------------------------------------------------------------------

@router.post("/decisions", response_model=DecisionRecordOut, status_code=status.HTTP_201_CREATED)
async def create_decision(body: DecisionRecordCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rec = DecisionRecord(**body.model_dump(), created_by_id=current_user.id)
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


@router.get("/decisions", response_model=list[DecisionRecordOut])
async def list_decisions(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(DecisionRecord).order_by(DecisionRecord.id.desc()))).scalars().all())


@router.get("/decisions/{decision_id}", response_model=DecisionRecordOut)
async def get_decision(decision_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load_decision(db, decision_id)


@router.patch("/decisions/{decision_id}", response_model=DecisionRecordOut)
async def update_decision(decision_id: int, body: DecisionRecordUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rec = await _load_decision(db, decision_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(rec, f, v)
    rec.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(rec)
    return rec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_package(db: AsyncSession, package_id: int) -> ContextPackage:
    pkg = (await db.execute(select(ContextPackage).where(ContextPackage.id == package_id))).scalar_one_or_none()
    if pkg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context package not found")
    return pkg


async def _load_decision(db: AsyncSession, decision_id: int) -> DecisionRecord:
    rec = (await db.execute(select(DecisionRecord).where(DecisionRecord.id == decision_id))).scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision record not found")
    return rec
