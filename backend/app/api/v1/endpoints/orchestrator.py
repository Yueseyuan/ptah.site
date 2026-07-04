from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.orchestrator import (
    BranchRun, MergeStrategy, OrchestratorDecision, OrchestratorPlan,
    OrchestratorRun, OrchestratorRunStatus, OrchestratorTask,
    ResultMerge, TaskAssignment, TaskBranch, TaskDependency, TaskStatus,
)
from app.models.user import User
from app.schemas.orchestrator import (
    BranchRunCreate, BranchRunOut, OrchestratorDecisionCreate, OrchestratorDecisionOut,
    OrchestratorPlanCreate, OrchestratorPlanOut, OrchestratorRunCreate, OrchestratorRunOut,
    OrchestratorTaskCreate, OrchestratorTaskOut, OrchestratorTaskUpdate,
    ResultMergeCreate, ResultMergeOut,
    TaskAssignmentCreate, TaskAssignmentOut, TaskBranchCreate, TaskBranchOut,
    TaskDependencyCreate, TaskDependencyOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@router.post("/tasks", response_model=OrchestratorTaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(body: OrchestratorTaskCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = OrchestratorTask(**body.model_dump(), created_by_id=current_user.id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/tasks", response_model=list[OrchestratorTaskOut])
async def list_tasks(
    status_filter: TaskStatus | None = Query(None, alias="status"),
    task_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(OrchestratorTask).order_by(OrchestratorTask.priority.desc(), OrchestratorTask.id.desc())
    if status_filter:
        stmt = stmt.where(OrchestratorTask.status == status_filter)
    if task_type:
        stmt = stmt.where(OrchestratorTask.task_type == task_type)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/tasks/{task_id}", response_model=OrchestratorTaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load_task(db, task_id)


@router.patch("/tasks/{task_id}", response_model=OrchestratorTaskOut)
async def update_task(task_id: int, body: OrchestratorTaskUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    task = await _load_task(db, task_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(task, f, v)
    await db.commit()
    await db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Task Assignments
# ---------------------------------------------------------------------------

@router.post("/tasks/{task_id}/assignments", response_model=TaskAssignmentOut, status_code=status.HTTP_201_CREATED)
async def assign_task(task_id: int, body: TaskAssignmentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load_task(db, task_id)
    assignment = TaskAssignment(**body.model_dump(), task_id=task_id, assigned_by_id=current_user.id)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.get("/tasks/{task_id}/assignments", response_model=list[TaskAssignmentOut])
async def list_assignments(task_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_task(db, task_id)
    return list((await db.execute(select(TaskAssignment).where(TaskAssignment.task_id == task_id))).scalars().all())


# ---------------------------------------------------------------------------
# Task Dependencies
# ---------------------------------------------------------------------------

@router.post("/tasks/{task_id}/dependencies", response_model=TaskDependencyOut, status_code=status.HTTP_201_CREATED)
async def add_dependency(task_id: int, body: TaskDependencyCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_task(db, task_id)
    await _load_task(db, body.depends_on_task_id)
    dep = TaskDependency(task_id=task_id, depends_on_task_id=body.depends_on_task_id)
    db.add(dep)
    await db.commit()
    await db.refresh(dep)
    return dep


@router.get("/tasks/{task_id}/dependencies", response_model=list[TaskDependencyOut])
async def list_dependencies(task_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_task(db, task_id)
    return list((await db.execute(select(TaskDependency).where(TaskDependency.task_id == task_id))).scalars().all())


# ---------------------------------------------------------------------------
# Task Branches
# ---------------------------------------------------------------------------

@router.post("/tasks/{task_id}/branches", response_model=TaskBranchOut, status_code=status.HTTP_201_CREATED)
async def create_branch(task_id: int, body: TaskBranchCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load_task(db, task_id)
    branch = TaskBranch(**body.model_dump(), task_id=task_id, created_by_id=current_user.id)
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch


@router.get("/tasks/{task_id}/branches", response_model=list[TaskBranchOut])
async def list_branches(task_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_task(db, task_id)
    return list((await db.execute(select(TaskBranch).where(TaskBranch.task_id == task_id, TaskBranch.is_active.is_(True)))).scalars().all())


# ---------------------------------------------------------------------------
# Branch Runs
# ---------------------------------------------------------------------------

@router.post("/branches/{branch_id}/runs", response_model=BranchRunOut, status_code=status.HTTP_201_CREATED)
async def create_branch_run(branch_id: int, body: BranchRunCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    branch = (await db.execute(select(TaskBranch).where(TaskBranch.id == branch_id))).scalar_one_or_none()
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    run = BranchRun(**body.model_dump(), branch_id=branch_id)
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/branches/{branch_id}/runs", response_model=list[BranchRunOut])
async def list_branch_runs(branch_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    branch = (await db.execute(select(TaskBranch).where(TaskBranch.id == branch_id))).scalar_one_or_none()
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return list((await db.execute(select(BranchRun).where(BranchRun.branch_id == branch_id).order_by(BranchRun.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Result Merges
# ---------------------------------------------------------------------------

@router.post("/branches/{branch_id}/merges", response_model=ResultMergeOut, status_code=status.HTTP_201_CREATED)
async def create_merge(branch_id: int, body: ResultMergeCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    branch = (await db.execute(select(TaskBranch).where(TaskBranch.id == branch_id))).scalar_one_or_none()
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    merge = ResultMerge(**body.model_dump(), branch_id=branch_id, created_by_id=current_user.id)
    db.add(merge)
    await db.commit()
    await db.refresh(merge)
    return merge


# ---------------------------------------------------------------------------
# Orchestrator Runs
# ---------------------------------------------------------------------------

@router.post("/runs", response_model=OrchestratorRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(body: OrchestratorRunCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = OrchestratorRun(**body.model_dump(), triggered_by_id=current_user.id, status=OrchestratorRunStatus.PENDING)
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/runs", response_model=list[OrchestratorRunOut])
async def list_runs(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(OrchestratorRun).order_by(OrchestratorRun.id.desc()))).scalars().all())


@router.get("/runs/{run_id}", response_model=OrchestratorRunOut)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load_run(db, run_id)


# ---------------------------------------------------------------------------
# Orchestrator Decisions
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/decisions", response_model=OrchestratorDecisionOut, status_code=status.HTTP_201_CREATED)
async def create_decision(run_id: int, body: OrchestratorDecisionCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_run(db, run_id)
    decision = OrchestratorDecision(**body.model_dump(), run_id=run_id)
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return decision


@router.get("/runs/{run_id}/decisions", response_model=list[OrchestratorDecisionOut])
async def list_decisions(run_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_run(db, run_id)
    return list((await db.execute(select(OrchestratorDecision).where(OrchestratorDecision.run_id == run_id).order_by(OrchestratorDecision.id))).scalars().all())


# ---------------------------------------------------------------------------
# Orchestrator Plans
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/plans", response_model=OrchestratorPlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(run_id: int, body: OrchestratorPlanCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await _load_run(db, run_id)
    plan = OrchestratorPlan(**body.model_dump(), run_id=run_id)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/runs/{run_id}/plans/{plan_id}/approve", response_model=OrchestratorPlanOut)
async def approve_plan(run_id: int, plan_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = (await db.execute(select(OrchestratorPlan).where(OrchestratorPlan.id == plan_id, OrchestratorPlan.run_id == run_id))).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    plan.is_approved = True
    plan.approved_by_id = current_user.id
    await db.commit()
    await db.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_task(db: AsyncSession, task_id: int) -> OrchestratorTask:
    task = (await db.execute(select(OrchestratorTask).where(OrchestratorTask.id == task_id))).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _load_run(db: AsyncSession, run_id: int) -> OrchestratorRun:
    run = (await db.execute(select(OrchestratorRun).where(OrchestratorRun.id == run_id))).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestrator run not found")
    return run
