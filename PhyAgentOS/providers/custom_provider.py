"""Direct OpenAI-compatible provider — bypasses LiteLLM."""

from __future__ import annotations

import asyncio
import logging
import uuid
from time import monotonic
from typing import Any

import httpx
import json_repair
from openai import AsyncOpenAI

from PhyAgentOS.providers.base import (
    LLMProvider,
    LLMResponse,
    ModelRequestTiming,
    ToolCallRequest,
)

logger = logging.getLogger(__name__)


class CustomProvider(LLMProvider):

    def __init__(
        self,
        api_key: str = "no-key",
        api_base: str = "http://localhost:8000/v1",
        default_model: str = "default",
        timeout_s: float = 180.0,
        stream_responses: bool = False,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.stream_responses = stream_responses
        # Use httpx client with trust_env=False to avoid picking up system SOCKS proxy
        # that uses the unsupported 'socks://' scheme (httpx only supports socks5://).
        http_client = httpx.AsyncClient(
            trust_env=False,
            timeout=httpx.Timeout(float(timeout_s), connect=15.0),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
        )
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
            default_headers={"x-session-affinity": uuid.uuid4().hex},
            http_client=http_client,
        )

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
                   model: str | None = None, max_tokens: int = 4096, temperature: float = 0.7,
                   reasoning_effort: str | None = None,
                   tool_choice: str | dict[str, Any] | None = None) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._sanitize_empty_content(messages),
            "max_tokens": max(1, max_tokens),
            "temperature": temperature,
        }
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        if tools:
            kwargs.update(tools=tools, tool_choice=tool_choice or "auto")
        started = monotonic()
        stream = None
        headers_received = None
        first_event_at = None
        try:
            if not self.stream_responses:
                return self._parse(await self._client.chat.completions.create(**kwargs))
            started = monotonic()
            stream = await self._client.chat.completions.create(
                **kwargs,
                stream=True,
                stream_options={"include_usage": True},
            )
            headers_received = monotonic()
            content: list[str] = []
            reasoning: list[str] = []
            tool_parts: dict[int, dict[str, Any]] = {}
            finish_reason = "stop"
            usage: dict[str, int] = {}
            first_event_at: float | None = None
            async for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }
                for choice in getattr(chunk, "choices", ()):
                    delta = choice.delta
                    meaningful = False
                    if getattr(delta, "content", None):
                        content.append(delta.content)
                        meaningful = True
                    reasoning_delta = getattr(delta, "reasoning_content", None)
                    if reasoning_delta:
                        reasoning.append(reasoning_delta)
                        meaningful = True
                    for tool_delta in getattr(delta, "tool_calls", None) or ():
                        meaningful = True
                        index = int(tool_delta.index)
                        part = tool_parts.setdefault(
                            index,
                            {"id": "", "name": "", "arguments": ""},
                        )
                        if tool_delta.id:
                            part["id"] += tool_delta.id
                        function = getattr(tool_delta, "function", None)
                        if function is not None:
                            if function.name:
                                part["name"] += function.name
                            if function.arguments:
                                part["arguments"] += function.arguments
                    if meaningful and first_event_at is None:
                        first_event_at = monotonic()
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
            completed = monotonic()
            tool_calls = [
                ToolCallRequest(
                    id=part["id"] or uuid.uuid4().hex,
                    name=part["name"],
                    arguments=(
                        json_repair.loads(part["arguments"])
                        if isinstance(part["arguments"], str)
                        else part["arguments"]
                    ),
                )
                for _, part in sorted(tool_parts.items())
            ]
            return LLMResponse(
                content="".join(content) or None,
                tool_calls=tool_calls,
                finish_reason=finish_reason or "stop",
                usage=usage,
                reasoning_content="".join(reasoning) or None,
                timing=ModelRequestTiming(
                    request_to_headers_s=headers_received - started,
                    time_to_first_token_s=(
                        first_event_at - started if first_event_at is not None else None
                    ),
                    complete_response_s=completed - started,
                    observation_mode="streaming",
                ),
            )
        except asyncio.CancelledError:
            logger.info(
                "Model request interrupted: headers_s=%s first_token_s=%s elapsed_s=%.3f",
                headers_received - started if headers_received is not None else None,
                first_event_at - started if first_event_at is not None else None,
                monotonic() - started,
            )
            raise
        except Exception as e:
            return LLMResponse(
                content=f"Error: {e}", finish_reason="error",
                timing=ModelRequestTiming(
                    request_to_headers_s=headers_received - started if headers_received is not None else None,
                    time_to_first_token_s=first_event_at - started if first_event_at is not None else None,
                    complete_response_s=monotonic() - started,
                    observation_mode="streaming" if self.stream_responses else "non_streaming",
                ),
            )
        finally:
            if stream is not None:
                await stream.close()

    def _parse(self, response: Any) -> LLMResponse:
        choice = response.choices[0]
        msg = choice.message
        tool_calls = [
            ToolCallRequest(id=tc.id, name=tc.function.name,
                            arguments=json_repair.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments)
            for tc in (msg.tool_calls or [])
        ]
        u = response.usage
        return LLMResponse(
            content=msg.content, tool_calls=tool_calls, finish_reason=choice.finish_reason or "stop",
            usage={"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens, "total_tokens": u.total_tokens} if u else {},
            reasoning_content=getattr(msg, "reasoning_content", None) or None,
        )

    def get_default_model(self) -> str:
        return self.default_model
