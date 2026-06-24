import json
import logging
from typing import Any, AsyncIterator, Awaitable, Callable

import httpx

from app.providers.base import CompletionResult, Message, ModelInfo, ToolCall

logger = logging.getLogger(__name__)

ANTHROPIC_MODELS = [
    ModelInfo(id="claude-opus-4-8", name="Claude Opus 4.8", provider="anthropic"),
    ModelInfo(id="claude-sonnet-4-6", name="Claude Sonnet 4.6", provider="anthropic"),
    ModelInfo(id="claude-haiku-4-5-20251001", name="Claude Haiku 4.5", provider="anthropic"),
]


class AnthropicProvider:
    """Anthropic cloud API with tool-use / agentic loop support."""

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
            timeout=300.0,
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

    async def complete_with_tools(
        self,
        messages: list[Message],
        model: str,
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Awaitable[str]],
        max_iterations: int = 25,
        max_tokens: int = 8192,
    ) -> CompletionResult:
        """Run an agentic loop: complete → execute tool calls → continue until text response."""
        system = next((m.content for m in messages if m.role == "system"), None)
        raw_messages: list[dict[str, Any]] = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]

        total_in = 0
        total_out = 0

        for iteration in range(max_iterations):
            body: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": raw_messages,
                "tools": tools,
            }
            if system:
                body["system"] = system

            resp = await self._client.post("/v1/messages", json=body)
            resp.raise_for_status()
            raw = resp.json()

            usage = raw.get("usage", {})
            total_in += usage.get("input_tokens", 0)
            total_out += usage.get("output_tokens", 0)

            content_blocks: list[dict[str, Any]] = raw.get("content", [])
            stop_reason = raw.get("stop_reason")

            if stop_reason == "tool_use":
                # Add assistant's response (with tool_use blocks) to history
                raw_messages.append({"role": "assistant", "content": content_blocks})

                # Execute each tool call
                tool_results: list[dict[str, Any]] = []
                for block in content_blocks:
                    if block.get("type") == "tool_use":
                        result_text = await tool_executor(block["name"], block.get("input", {}))
                        logger.debug("Tool %s → %s", block["name"], result_text[:120])
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": result_text,
                        })

                # Feed results back
                raw_messages.append({"role": "user", "content": tool_results})
                continue

            # end_turn or max_tokens — extract text
            text = " ".join(
                b.get("text", "") for b in content_blocks if b.get("type") == "text"
            ).strip()
            return CompletionResult(
                content=text,
                model=raw.get("model", model),
                provider="anthropic",
                input_tokens=total_in,
                output_tokens=total_out,
                raw=raw,
            )

        return CompletionResult(
            content="Agent reached max iterations.",
            model=model,
            provider="anthropic",
            input_tokens=total_in,
            output_tokens=total_out,
        )

    async def stream(self, messages: list[Message], model: str, **kwargs: Any) -> AsyncIterator[str]:
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
