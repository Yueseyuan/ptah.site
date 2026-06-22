from app.providers.anthropic import AnthropicProvider
from app.providers.base import ModelInfo, ModelProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai_compat import (
    LlamaCppProvider,
    LMStudioProvider,
    LocalAIProvider,
    OpenAIProvider,
    VLLMProvider,
)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ModelProvider | None:
        return self._providers.get(name)

    def all(self) -> list[ModelProvider]:
        return list(self._providers.values())

    def names(self) -> list[str]:
        return list(self._providers.keys())


_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None


def _build_registry() -> ProviderRegistry:
    from app.config import settings

    registry = ProviderRegistry()
    registry.register(OllamaProvider(settings.ollama_base_url))
    registry.register(LlamaCppProvider(settings.llamacpp_base_url))
    registry.register(LMStudioProvider(settings.lmstudio_base_url))
    registry.register(LocalAIProvider(settings.localai_base_url))
    registry.register(VLLMProvider(settings.vllm_base_url))
    if settings.openai_api_key:
        registry.register(OpenAIProvider(settings.openai_api_key))
    if settings.anthropic_api_key:
        registry.register(AnthropicProvider(settings.anthropic_api_key))
    return registry
