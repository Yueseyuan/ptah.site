from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.audit import AuditEventType
from app.models.workflow import (
    Workflow, WorkflowRun, WorkflowRunEvent, WorkflowRunStatus,
    WorkflowStep, WorkflowStatus,
)
from app.models.user import User
from app.schemas.workflow import (
    WorkflowCreate, WorkflowOut, WorkflowRunCreate, WorkflowRunEventOut,
    WorkflowRunOut, WorkflowStepCreate, WorkflowStepOut, WorkflowUpdate,
)
from app.services.audit import log_event

router = APIRouter()


# ---------------------------------------------------------------------------
# Workflows CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
async def create_workflow(body: WorkflowCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    wf = Workflow(**body.model_dump(), created_by_id=current_user.id)
    db.add(wf)
    await log_event(db, AuditEventType.SYSTEM_CHANGE, user_id=current_user.id, resource_type="workflow")
    await db.commit()
    await db.refresh(wf)
    return wf


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(Workflow).where(Workflow.is_active.is_(True)).order_by(Workflow.id.desc()))).scalars().all())


@router.get("/{workflow_id}", response_model=WorkflowOut)
async def get_workflow(workflow_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load_workflow(db, workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(workflow_id: int, body: WorkflowUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    wf = await _load_workflow(db, workflow_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(wf, f, v)
    await db.commit()
    await db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_workflow(workflow_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    wf = await _load_workflow(db, workflow_id)
    wf.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

@router.post("/{workflow_id}/steps", response_model=WorkflowStepOut, status_code=status.HTTP_201_CREATED)
async def create_step(workflow_id: int, body: WorkflowStepCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_workflow(db, workflow_id)
    # Shift existing steps if order_index collision
    existing = (await db.execute(select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id, WorkflowStep.order_index == body.order_index))).scalar_one_or_none()
    if existing:
        steps_to_shift = (await db.execute(
            select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id, WorkflowStep.order_index >= body.order_index).order_by(WorkflowStep.order_index.desc())
        )).scalars().all()
        for s in steps_to_shift:
            s.order_index += 1
    step = WorkflowStep(**body.model_dump(), workflow_id=workflow_id)
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


@router.get("/{workflow_id}/steps", response_model=list[WorkflowStepOut])
async def list_steps(workflow_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_workflow(db, workflow_id)
    return list((await db.execute(select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id, WorkflowStep.is_active.is_(True)).order_by(WorkflowStep.order_index))).scalars().all())


@router.delete("/{workflow_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_step(workflow_id: int, step_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    step = (await db.execute(select(WorkflowStep).where(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id))).scalar_one_or_none()
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    step.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.post("/{workflow_id}/runs", response_model=WorkflowRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(workflow_id: int, body: WorkflowRunCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load_workflow(db, workflow_id)
    run = WorkflowRun(**body.model_dump(), workflow_id=workflow_id, triggered_by_id=current_user.id, status=WorkflowRunStatus.PENDING)
    db.add(run)
    await log_event(db, AuditEventType.WORKFLOW_RUN, user_id=current_user.id, resource_type="workflow", resource_id=str(workflow_id))
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{workflow_id}/runs", response_model=list[WorkflowRunOut])
async def list_runs(workflow_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_workflow(db, workflow_id)
    return list((await db.execute(select(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id).order_by(WorkflowRun.id.desc()))).scalars().all())


@router.get("/{workflow_id}/runs/{run_id}", response_model=WorkflowRunOut)
async def get_run(workflow_id: int, run_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    run = (await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id, WorkflowRun.workflow_id == workflow_id))).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/{workflow_id}/runs/{run_id}/events", response_model=list[WorkflowRunEventOut])
async def list_run_events(workflow_id: int, run_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    run = (await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id, WorkflowRun.workflow_id == workflow_id))).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return list((await db.execute(select(WorkflowRunEvent).where(WorkflowRunEvent.run_id == run_id).order_by(WorkflowRunEvent.id))).scalars().all())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_workflow(db: AsyncSession, workflow_id: int) -> Workflow:
    wf = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
    if wf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return wf
