"""APScheduler-based task scheduler — runs Chief goals on a cron/interval schedule."""
import logging
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.models.scheduler import ScheduledTask

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def _make_trigger(schedule: dict[str, Any]):
    """Convert a schedule dict to an APScheduler trigger."""
    stype = schedule.get("type", "daily")

    if stype == "interval":
        hours = int(schedule.get("hours", 1))
        minutes = int(schedule.get("minutes", 0))
        return IntervalTrigger(hours=hours, minutes=minutes)

    if stype == "daily":
        hour = int(schedule.get("hour", 9))
        minute = int(schedule.get("minute", 0))
        return CronTrigger(hour=hour, minute=minute)

    if stype == "weekly":
        day = schedule.get("day", "mon")
        hour = int(schedule.get("hour", 9))
        minute = int(schedule.get("minute", 0))
        return CronTrigger(day_of_week=day, hour=hour, minute=minute)

    if stype == "cron":
        expr = schedule.get("expr", "0 9 * * *")
        parts = expr.strip().split()
        if len(parts) == 5:
            minute, hour, day, month, dow = parts
            return CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow)

    # fallback: daily at 9am UTC
    return CronTrigger(hour=9, minute=0)


def _job_id(task_id: int) -> str:
    return f"scheduled_task_{task_id}"


async def _run_task(task_id: int, goal: str, created_by_id: int) -> None:
    """Execute a scheduled Chief run and update task metadata."""
    from app.database import AsyncSessionLocal
    from app.services.chief import run_chief

    logger.info("Running scheduled task %d: %s", task_id, goal[:80])
    status = "completed"
    try:
        async with AsyncSessionLocal() as db:
            await run_chief(goal=goal, db=db, triggered_by_id=created_by_id)
    except Exception as exc:
        logger.error("Scheduled task %d failed: %s", task_id, exc)
        status = "failed"

    # Update run metadata
    try:
        from sqlalchemy import select
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            task = (await db.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))).scalar_one_or_none()
            if task:
                task.last_run_at = datetime.now(timezone.utc)
                task.last_run_status = status
                task.run_count = (task.run_count or 0) + 1
                if status == "failed":
                    task.error_count = (task.error_count or 0) + 1
                await db.commit()
    except Exception as exc:
        logger.error("Failed to update task %d metadata: %s", task_id, exc)


def register_task(task: ScheduledTask) -> None:
    """Add (or replace) a task in the scheduler."""
    sched = get_scheduler()
    job_id = _job_id(task.id)

    # Remove existing job if any
    if sched.get_job(job_id):
        sched.remove_job(job_id)

    if not task.enabled:
        return

    trigger = _make_trigger(task.schedule)
    sched.add_job(
        _run_task,
        trigger=trigger,
        id=job_id,
        args=[task.id, task.goal, task.created_by_id],
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled task %d (%s) registered with trigger %s", task.id, task.name, task.schedule)


def unregister_task(task_id: int) -> None:
    sched = get_scheduler()
    job_id = _job_id(task_id)
    if sched.get_job(job_id):
        sched.remove_job(job_id)


def get_next_run(task_id: int) -> datetime | None:
    sched = get_scheduler()
    job = sched.get_job(_job_id(task_id))
    if job and job.next_run_time:
        return job.next_run_time
    return None


async def start_scheduler() -> None:
    """Start APScheduler and load all enabled tasks from the database."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal

    sched = get_scheduler()
    sched.start()

    async with AsyncSessionLocal() as db:
        tasks = list((await db.execute(select(ScheduledTask).where(ScheduledTask.enabled.is_(True)))).scalars().all())

    for task in tasks:
        register_task(task)

    logger.info("Scheduler started with %d active task(s)", len(tasks))


async def stop_scheduler() -> None:
    sched = get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)
        logger.info("Scheduler stopped")
