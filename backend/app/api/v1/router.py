from fastapi import APIRouter
from app.api.v1.endpoints import agents, approval, audit, auth, health, models

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(approval.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
