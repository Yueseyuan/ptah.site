from typing import Any, AsyncIterator

import httpx

from app.providers.base import CompletionResult, Message, ModelInfo


class OllamaProvider:
    """Ollama local inference server (native API)."""

    name = "ollama"

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None):
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(base_url=self._base_url, timeout=120.0)

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[ModelInfo]:
        try:
            resp = await self._client.get("/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return [
                ModelInfo(
                    id=m["name"],
                    name=m["name"],
                    provider="ollama",
                    context_length=m.get("details", {}).get("context_length"),
                )
                for m in models
            ]
        except Exception:
            return []

    async def complete(self, messages: list[Message], model: str, **kwargs: Any) -> CompletionResult:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            **kwargs,
        }
        resp = await self._client.post("/api/chat", json=body)
        resp.raise_for_status()
        raw = resp.json()
        return CompletionResult(
            content=raw["message"]["content"],
            model=raw.get("model", model),
            provider="ollama",
            raw=raw,
        )

    async def stream(self, messages: list[Message], model: str, **kwargs: Any) -> AsyncIterator[str]:
        import json
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            **kwargs,
        }
        async with self._client.stream("POST", "/api/chat", json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    chunk = json.loads(line)
                    if text := chunk.get("message", {}).get("content"):
                        yield text
                    if chunk.get("done"):
                        break
