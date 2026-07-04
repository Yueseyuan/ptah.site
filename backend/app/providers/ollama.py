import json
import logging
from typing import Any, AsyncIterator, Awaitable, Callable

import httpx

from app.providers.base import CompletionResult, Message, ModelInfo, ToolCall

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Ollama local inference server with tool-use support."""

    name = "ollama"

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None):
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(base_url=self._base_url, timeout=300.0)

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

    async def complete_with_tools(
        self,
        messages: list[Message],
        model: str,
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Awaitable[str]],
        max_iterations: int = 25,
        max_tokens: int = 8192,
    ) -> CompletionResult:
        """Run an agentic loop using Ollama's OpenAI-compatible tool calling."""
        raw_messages: list[dict[str, Any]] = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        for iteration in range(max_iterations):
            body: dict[str, Any] = {
                "model": model,
                "messages": raw_messages,
                "tools": tools,
                "stream": False,
            }
            try:
                resp = await self._client.post("/api/chat", json=body)
                resp.raise_for_status()
            except Exception as exc:
                logger.warning("Ollama tool call failed (iter %d): %s — falling back to plain complete", iteration, exc)
                return await self.complete(messages, model)

            raw = resp.json()
            msg = raw.get("message", {})
            tool_calls = msg.get("tool_calls")

            if not tool_calls:
                # Final text response
                return CompletionResult(
                    content=msg.get("content", ""),
                    model=raw.get("model", model),
                    provider="ollama",
                    raw=raw,
                )

            # Add assistant message with tool calls
            raw_messages.append(msg)

            # Execute each tool and add results
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                arguments = fn.get("arguments", {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                result_text = await tool_executor(name, arguments)
                logger.debug("Tool %s → %s", name, result_text[:120])
                raw_messages.append({
                    "role": "tool",
                    "content": result_text,
                })

        return CompletionResult(
            content="Agent reached max iterations.",
            model=model,
            provider="ollama",
        )

    async def stream(self, messages: list[Message], model: str, **kwargs: Any) -> AsyncIterator[str]:
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
