"""CL4R1T4S agent template seeder endpoints."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.user import User
from app.services.claritas_seeder import AGENT_NAMES, seed_claritas_agents

router = APIRouter()


@router.get("/status")
async def claritas_status(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Return how many CL4R1T4S templates are already installed."""
    count_result = await db.execute(
        select(func.count()).select_from(Agent).where(Agent.name.in_(AGENT_NAMES))
    )
    installed: int = count_result.scalar_one()
    return {"available": len(AGENT_NAMES), "installed": installed}


@router.post("/seed")
async def claritas_seed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Seed CL4R1T4S agent templates (idempotent — skips existing agents)."""
    return await seed_claritas_agents(db, current_user.id)
