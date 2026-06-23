from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.agent import (
    Agent, AgentCapability, AgentCapabilityType,
    AgentRiskPolicy, AgentRun, AgentRunEvent, AgentRunStatus, AgentVersion,
)
from app.models.audit import AuditEventType
from app.models.user import User
from app.schemas.agent import (
    AgentCapabilityOut, AgentCreate, AgentOut, AgentRiskPolicyCreate,
    AgentRiskPolicyOut, AgentRunCreate, AgentRunOut, AgentUpdate,
    AgentVersionCreate, AgentVersionOut,
)
from app.services.audit import log_event

router = APIRouter()


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (await db.execute(select(Agent).where(Agent.name == body.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent name already exists")
    agent = Agent(**body.model_dump(), created_by_id=current_user.id)
    db.add(agent)
    await log_event(db, AuditEventType.SYSTEM_CHANGE, user_id=current_user.id, resource_type="agent", detail={"action": "create", "name": body.name})
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentOut])
async def list_agents(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Agent)
    if active_only:
        q = q.where(Agent.is_active.is_(True))
    rows = (await db.execute(q.order_by(Agent.name))).scalars().all()
    return list(rows)


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await _load_agent(db, agent_id)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: int,
    body: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = await _load_agent(db, agent_id)
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(agent, field, val)
    await log_event(db, AuditEventType.SYSTEM_CHANGE, user_id=current_user.id, resource_type="agent", resource_id=str(agent_id))
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = await _load_agent(db, agent_id)
    agent.is_active = False
    await log_event(db, AuditEventType.SYSTEM_CHANGE, user_id=current_user.id, resource_type="agent", resource_id=str(agent_id), detail={"action": "deactivate"})
    await db.commit()


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/versions", response_model=AgentVersionOut, status_code=status.HTTP_201_CREATED)
async def create_version(
    agent_id: int,
    body: AgentVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _load_agent(db, agent_id)
    if body.is_current:
        await _unset_current(db, agent_id)
    ver = AgentVersion(**body.model_dump(), agent_id=agent_id, published_by_id=current_user.id)
    db.add(ver)
    await db.commit()
    await db.refresh(ver)
    return ver


@router.get("/{agent_id}/versions", response_model=list[AgentVersionOut])
async def list_versions(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _load_agent(db, agent_id)
    rows = (await db.execute(
        select(AgentVersion).where(AgentVersion.agent_id == agent_id).order_by(AgentVersion.id.desc())
    )).scalars().all()
    return list(rows)


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/capabilities/{cap_type}", response_model=AgentCapabilityOut, status_code=status.HTTP_201_CREATED)
async def add_capability(
    agent_id: int,
    cap_type: AgentCapabilityType,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _load_agent(db, agent_id)
    existing = (await db.execute(
        select(AgentCapability).where(AgentCapability.agent_id == agent_id, AgentCapability.capability_type == cap_type)
    )).scalar_one_or_none()
    if existing:
        return existing
    cap = AgentCapability(agent_id=agent_id, capability_type=cap_type)
    db.add(cap)
    await db.commit()
    await db.refresh(cap)
    return cap


@router.get("/{agent_id}/capabilities", response_model=list[AgentCapabilityOut])
async def list_capabilities(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _load_agent(db, agent_id)
    rows = (await db.execute(
        select(AgentCapability).where(AgentCapability.agent_id == agent_id)
    )).scalars().all()
    return list(rows)


@router.delete("/{agent_id}/capabilities/{cap_type}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_capability(
    agent_id: int,
    cap_type: AgentCapabilityType,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cap = (await db.execute(
        select(AgentCapability).where(AgentCapability.agent_id == agent_id, AgentCapability.capability_type == cap_type)
    )).scalar_one_or_none()
    if cap:
        await db.delete(cap)
        await db.commit()


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/runs", response_model=AgentRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    agent_id: int,
    body: AgentRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _load_agent(db, agent_id)
    run = AgentRun(
        agent_id=agent_id,
        triggered_by_id=current_user.id,
        status=AgentRunStatus.PENDING,
        **body.model_dump(),
    )
    db.add(run)
    await log_event(db, AuditEventType.AGENT_RUN, user_id=current_user.id, resource_type="agent", resource_id=str(agent_id))
    await db.commit()
    await db.refresh(run)
    out = AgentRunOut.model_validate(run)
    out.events = []
    return out


@router.get("/{agent_id}/runs", response_model=list[AgentRunOut])
async def list_runs(
    agent_id: int,
    run_status: AgentRunStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _load_agent(db, agent_id)
    q = select(AgentRun).where(AgentRun.agent_id == agent_id)
    if run_status:
        q = q.where(AgentRun.status == run_status)
    rows = (await db.execute(q.order_by(AgentRun.id.desc()))).scalars().all()
    result = []
    for run in rows:
        out = AgentRunOut.model_validate(run)
        out.events = []
        result.append(out)
    return result


@router.get("/runs/{run_id}", response_model=AgentRunOut)
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    run = (await db.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    events = list((await db.execute(
        select(AgentRunEvent).where(AgentRunEvent.run_id == run_id).order_by(AgentRunEvent.id)
    )).scalars().all())
    out = AgentRunOut.model_validate(run)
    out.events = [AgentRunOut.model_fields["events"].annotation.__args__[0].model_validate(e) for e in events]
    return out


# ---------------------------------------------------------------------------
# Risk policies
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/risk-policies", response_model=AgentRiskPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_risk_policy(
    agent_id: int,
    body: AgentRiskPolicyCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _load_agent(db, agent_id)
    policy = AgentRiskPolicy(**body.model_dump(), agent_id=agent_id)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("/{agent_id}/risk-policies", response_model=list[AgentRiskPolicyOut])
async def list_risk_policies(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _load_agent(db, agent_id)
    rows = (await db.execute(
        select(AgentRiskPolicy).where(AgentRiskPolicy.agent_id == agent_id)
    )).scalars().all()
    return list(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_agent(db: AsyncSession, agent_id: int) -> Agent:
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


async def _unset_current(db: AsyncSession, agent_id: int) -> None:
    rows = (await db.execute(
        select(AgentVersion).where(AgentVersion.agent_id == agent_id, AgentVersion.is_current.is_(True))
    )).scalars().all()
    for v in rows:
        v.is_current = False
