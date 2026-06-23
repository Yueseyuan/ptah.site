from typing import Any, AsyncIterator

import httpx

from app.providers.base import CompletionResult, Message, ModelInfo


class OpenAICompatProvider:
    """Base for any provider that exposes an OpenAI-compatible /v1 API."""

    def __init__(self, name: str, base_url: str, api_key: str = "", client: httpx.AsyncClient | None = None):
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.AsyncClient(base_url=self._base_url, headers=headers, timeout=60.0)

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/v1/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[ModelInfo]:
        try:
            resp = await self._client.get("/v1/models")
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [
                ModelInfo(id=m["id"], name=m.get("id", ""), provider=self.name)
                for m in data
            ]
        except Exception:
            return []

    async def complete(self, messages: list[Message], model: str, **kwargs: Any) -> CompletionResult:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            **kwargs,
        }
        resp = await self._client.post("/v1/chat/completions", json=body)
        resp.raise_for_status()
        raw = resp.json()
        choice = raw["choices"][0]
        usage = raw.get("usage", {})
        return CompletionResult(
            content=choice["message"]["content"],
            model=raw.get("model", model),
            provider=self.name,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw=raw,
        )

    async def stream(self, messages: list[Message], model: str, **kwargs: Any) -> AsyncIterator[str]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            **kwargs,
        }
        async with self._client.stream("POST", "/v1/chat/completions", json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    import json
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0].get("delta", {})
                    if text := delta.get("content"):
                        yield text


class LlamaCppProvider(OpenAICompatProvider):
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None):
        super().__init__("llamacpp", base_url, "", client)


class LMStudioProvider(OpenAICompatProvider):
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None):
        super().__init__("lmstudio", base_url, "", client)


class LocalAIProvider(OpenAICompatProvider):
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None):
        super().__init__("localai", base_url, "", client)


class VLLMProvider(OpenAICompatProvider):
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None):
        super().__init__("vllm", base_url, "", client)


class OpenAIProvider(OpenAICompatProvider):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None):
        super().__init__("openai", "https://api.openai.com", api_key, client)
