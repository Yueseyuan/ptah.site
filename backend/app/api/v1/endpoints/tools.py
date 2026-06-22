from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.audit import AuditEventType
from app.models.tool import (
    ToolDefinition, ToolPermission, ToolRiskPolicy, ToolRun, ToolRunStatus, ToolVersion,
)
from app.models.user import User
from app.schemas.tool import (
    ToolCreate, ToolOut, ToolPermissionCreate, ToolPermissionOut,
    ToolRiskPolicyCreate, ToolRiskPolicyOut, ToolRunCreate, ToolRunOut,
    ToolUpdate, ToolVersionCreate, ToolVersionOut,
)
from app.services.audit import log_event

router = APIRouter()


# ---------------------------------------------------------------------------
# Tools CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=ToolOut, status_code=status.HTTP_201_CREATED)
async def create_tool(body: ToolCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if (await db.execute(select(ToolDefinition).where(ToolDefinition.name == body.name))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tool name already exists")
    tool = ToolDefinition(**body.model_dump(), created_by_id=current_user.id)
    db.add(tool)
    await log_event(db, AuditEventType.SYSTEM_CHANGE, user_id=current_user.id, resource_type="tool")
    await db.commit()
    await db.refresh(tool)
    return tool


@router.get("", response_model=list[ToolOut])
async def list_tools(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(ToolDefinition).where(ToolDefinition.is_active.is_(True)).order_by(ToolDefinition.name))).scalars().all())


@router.get("/{tool_id}", response_model=ToolOut)
async def get_tool(tool_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load(db, tool_id)


@router.patch("/{tool_id}", response_model=ToolOut)
async def update_tool(tool_id: int, body: ToolUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    tool = await _load(db, tool_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(tool, f, v)
    await db.commit()
    await db.refresh(tool)
    return tool


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_tool(tool_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    tool = await _load(db, tool_id)
    tool.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

@router.post("/{tool_id}/versions", response_model=ToolVersionOut, status_code=status.HTTP_201_CREATED)
async def create_version(tool_id: int, body: ToolVersionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load(db, tool_id)
    if body.is_current:
        for v in (await db.execute(select(ToolVersion).where(ToolVersion.tool_id == tool_id, ToolVersion.is_current.is_(True)))).scalars().all():
            v.is_current = False
    ver = ToolVersion(**body.model_dump(), tool_id=tool_id, published_by_id=current_user.id)
    db.add(ver)
    await db.commit()
    await db.refresh(ver)
    return ver


@router.get("/{tool_id}/versions", response_model=list[ToolVersionOut])
async def list_versions(tool_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, tool_id)
    return list((await db.execute(select(ToolVersion).where(ToolVersion.tool_id == tool_id).order_by(ToolVersion.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.post("/{tool_id}/runs", response_model=ToolRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(tool_id: int, body: ToolRunCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load(db, tool_id)
    run = ToolRun(**body.model_dump(), tool_id=tool_id, triggered_by_id=current_user.id, status=ToolRunStatus.PENDING)
    db.add(run)
    await log_event(db, AuditEventType.TOOL_RUN, user_id=current_user.id, resource_type="tool", resource_id=str(tool_id))
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{tool_id}/runs", response_model=list[ToolRunOut])
async def list_runs(tool_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, tool_id)
    return list((await db.execute(select(ToolRun).where(ToolRun.tool_id == tool_id).order_by(ToolRun.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@router.post("/{tool_id}/permissions", response_model=ToolPermissionOut, status_code=status.HTTP_201_CREATED)
async def grant_permission(tool_id: int, body: ToolPermissionCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, tool_id)
    perm = ToolPermission(**body.model_dump(), tool_id=tool_id)
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return perm


@router.get("/{tool_id}/permissions", response_model=list[ToolPermissionOut])
async def list_permissions(tool_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, tool_id)
    return list((await db.execute(select(ToolPermission).where(ToolPermission.tool_id == tool_id))).scalars().all())


# ---------------------------------------------------------------------------
# Risk policies
# ---------------------------------------------------------------------------

@router.post("/{tool_id}/risk-policies", response_model=ToolRiskPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_risk_policy(tool_id: int, body: ToolRiskPolicyCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load(db, tool_id)
    policy = ToolRiskPolicy(**body.model_dump(), tool_id=tool_id)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load(db: AsyncSession, tool_id: int) -> ToolDefinition:
    tool = (await db.execute(select(ToolDefinition).where(ToolDefinition.id == tool_id))).scalar_one_or_none()
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return tool
