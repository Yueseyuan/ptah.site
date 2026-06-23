from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.agency_seeder import get_agency_status, seed_agency_agents

router = APIRouter()


@router.get("/status")
async def agency_status(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    return await get_agency_status(db)


@router.post("/seed")
async def agency_seed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await seed_agency_agents(db, current_user.id)
