from fastapi import APIRouter
from app.api.v1.endpoints import (
    agents, approval, audit, auth, context, health, knowledge, memory,
    models, orchestrator, prompts, repo_review, skills, tools, workflows,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(approval.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(context.router, prefix="/context", tags=["context"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(orchestrator.router, prefix="/orchestrator", tags=["orchestrator"])
api_router.include_router(repo_review.router, prefix="/repo-reviews", tags=["repo-reviews"])
