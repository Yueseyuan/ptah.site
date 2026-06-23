from typing import Any, AsyncIterator

import httpx

from app.providers.base import CompletionResult, Message, ModelInfo

ANTHROPIC_MODELS = [
    ModelInfo(id="claude-opus-4-8", name="Claude Opus 4.8", provider="anthropic"),
    ModelInfo(id="claude-sonnet-4-6", name="Claude Sonnet 4.6", provider="anthropic"),
    ModelInfo(id="claude-haiku-4-5-20251001", name="Claude Haiku 4.5", provider="anthropic"),
]


class AnthropicProvider:
    """Anthropic cloud API."""

    name = "anthropic"

    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com", client: httpx.AsyncClient | None = None):
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=120.0,
        )

    async def health(self) -> bool:
        return bool(self._api_key)

    async def list_models(self) -> list[ModelInfo]:
        return ANTHROPIC_MODELS

    async def complete(self, messages: list[Message], model: str, **kwargs: Any) -> CompletionResult:
        system = next((m.content for m in messages if m.role == "system"), None)
        user_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": kwargs.pop("max_tokens", 1024),
            "messages": user_msgs,
            **kwargs,
        }
        if system:
            body["system"] = system
        resp = await self._client.post("/v1/messages", json=body)
        resp.raise_for_status()
        raw = resp.json()
        usage = raw.get("usage", {})
        return CompletionResult(
            content=raw["content"][0]["text"],
            model=raw.get("model", model),
            provider="anthropic",
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            raw=raw,
        )

    async def stream(self, messages: list[Message], model: str, **kwargs: Any) -> AsyncIterator[str]:
        import json
        system = next((m.content for m in messages if m.role == "system"), None)
        user_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": kwargs.pop("max_tokens", 1024),
            "messages": user_msgs,
            "stream": True,
            **kwargs,
        }
        if system:
            body["system"] = system
        async with self._client.stream("POST", "/v1/messages", json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    chunk = json.loads(line[6:])
                    if chunk.get("type") == "content_block_delta":
                        if text := chunk.get("delta", {}).get("text"):
                            yield text
