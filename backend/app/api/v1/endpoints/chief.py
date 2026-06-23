"""Chief orchestrator REST endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.orchestrator import OrchestratorRun
from app.models.user import User
from app.schemas.chief import ChiefRunRequest, ChiefRunResult, ChiefRunSummary, ChiefSubtaskOut
from app.services.chief import run_chief

router = APIRouter()


@router.post("/run", response_model=ChiefRunResult)
async def chief_run(
    body: ChiefRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Decompose a goal, assign agents, execute in parallel, and return merged results."""
    if not body.goal or not body.goal.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="goal must not be empty")

    result = await run_chief(goal=body.goal.strip(), db=db, triggered_by_id=current_user.id)

    subtasks = [
        ChiefSubtaskOut(
            title=s["title"],
            description=s["description"],
            agent_name=s["agent_name"],
            agent_run_id=s.get("agent_run_id"),
            output=s.get("output"),
        )
        for s in result.get("subtasks", [])
    ]

    return ChiefRunResult(
        run_id=result.get("run_id"),
        subtasks=subtasks,
        merged_output=result.get("merged_output"),
        error=result.get("error"),
    )


@router.get("/runs", response_model=list[ChiefRunSummary])
async def list_chief_runs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List past Chief orchestration runs."""
    rows = list(
        (
            await db.execute(
                select(OrchestratorRun)
                .where(OrchestratorRun.name.like("Chief:%"))
                .order_by(OrchestratorRun.id.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    return rows


@router.get("/runs/{run_id}", response_model=ChiefRunSummary)
async def get_chief_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a specific Chief run with all subtask results."""
    run = (
        await db.execute(
            select(OrchestratorRun).where(
                OrchestratorRun.id == run_id,
                OrchestratorRun.name.like("Chief:%"),
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chief run not found")
    return run
