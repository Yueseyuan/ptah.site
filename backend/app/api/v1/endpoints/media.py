from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.media_seeder import get_media_status, seed_media_agents

router = APIRouter()


@router.get("/status")
async def media_status(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    return await get_media_status(db)


@router.post("/seed")
async def media_seed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await seed_media_agents(db, current_user.id)
