"""Scheduler REST endpoints — CRUD for scheduled Chief tasks."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.scheduler import ScheduledTask
from app.models.user import User
from app.services.scheduler_service import get_next_run, register_task, unregister_task

router = APIRouter()


class ScheduleIn(BaseModel):
    type: str  # daily | weekly | interval | cron
    hour: int | None = None
    minute: int | None = None
    day: str | None = None    # e.g. "mon" for weekly
    hours: int | None = None  # for interval
    minutes: int | None = None
    expr: str | None = None   # for cron


class TaskCreate(BaseModel):
    name: str
    goal: str
    schedule: ScheduleIn
    enabled: bool = True


class TaskUpdate(BaseModel):
    name: str | None = None
    goal: str | None = None
    schedule: ScheduleIn | None = None
    enabled: bool | None = None


class TaskOut(BaseModel):
    id: int
    name: str
    goal: str
    schedule: dict
    enabled: bool
    run_count: int
    error_count: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_run_status: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


def _task_out(task: ScheduledTask) -> TaskOut:
    return TaskOut(
        id=task.id,
        name=task.name,
        goal=task.goal,
        schedule=task.schedule,
        enabled=task.enabled,
        run_count=task.run_count,
        error_count=task.error_count,
        last_run_at=task.last_run_at,
        next_run_at=get_next_run(task.id),
        last_run_status=task.last_run_status,
        created_at=task.created_at,
    )


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[TaskOut]:
    tasks = list((await db.execute(select(ScheduledTask).order_by(ScheduledTask.id))).scalars().all())
    return [_task_out(t) for t in tasks]


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    task = ScheduledTask(
        name=body.name,
        goal=body.goal,
        schedule=body.schedule.model_dump(exclude_none=True),
        enabled=body.enabled,
        created_by_id=current_user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    if task.enabled:
        register_task(task)
    return _task_out(task)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TaskOut:
    task = (await db.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _task_out(task)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TaskOut:
    task = (await db.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if body.name is not None:
        task.name = body.name
    if body.goal is not None:
        task.goal = body.goal
    if body.schedule is not None:
        task.schedule = body.schedule.model_dump(exclude_none=True)
    if body.enabled is not None:
        task.enabled = body.enabled
    await db.commit()
    await db.refresh(task)
    # Re-register (handles enable/disable)
    unregister_task(task.id)
    if task.enabled:
        register_task(task)
    return _task_out(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    task = (await db.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    unregister_task(task.id)
    await db.delete(task)
    await db.commit()


@router.post("/{task_id}/run", response_model=dict)
async def trigger_task_now(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Immediately run a scheduled task (one-off, outside its schedule)."""
    task = (await db.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    from app.services.chief import run_chief
    try:
        result = await run_chief(goal=task.goal, db=db, triggered_by_id=current_user.id)
        return {"ok": True, "run_id": result.get("run_id")}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
