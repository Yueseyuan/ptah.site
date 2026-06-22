from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol, runtime_checkable


@dataclass
class Message:
    role: str   # "system" | "user" | "assistant"
    content: str


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    context_length: int | None = None
    description: str | None = None


@dataclass
class CompletionResult:
    content: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ModelProvider(Protocol):
    name: str

    async def health(self) -> bool: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def complete(self, messages: list[Message], model: str, **kwargs: Any) -> CompletionResult: ...
    async def stream(self, messages: list[Message], model: str, **kwargs: Any) -> AsyncIterator[str]: ...
