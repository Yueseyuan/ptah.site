from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User
from app.providers.base import ModelInfo
from app.providers.registry import get_registry

router = APIRouter()


class ProviderStatus(BaseModel):
    name: str
    healthy: bool
    model_count: int


class ProviderDetail(BaseModel):
    name: str
    healthy: bool
    models: list[ModelInfo]

    model_config = {"from_attributes": True}


@router.get("/providers", response_model=list[ProviderStatus])
async def list_providers(_: User = Depends(get_current_user)):
    registry = get_registry()
    results = []
    for provider in registry.all():
        healthy = await provider.health()
        models = await provider.list_models() if healthy else []
        results.append(ProviderStatus(name=provider.name, healthy=healthy, model_count=len(models)))
    return results


@router.get("/providers/{provider_name}", response_model=ProviderDetail)
async def get_provider(provider_name: str, _: User = Depends(get_current_user)):
    registry = get_registry()
    provider = registry.get(provider_name)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provider '{provider_name}' not found")
    healthy = await provider.health()
    models = await provider.list_models() if healthy else []
    return ProviderDetail(name=provider.name, healthy=healthy, models=models)


@router.get("", response_model=list[ModelInfo])
async def list_all_models(_: User = Depends(get_current_user)):
    registry = get_registry()
    all_models: list[ModelInfo] = []
    for provider in registry.all():
        if await provider.health():
            all_models.extend(await provider.list_models())
    return all_models
