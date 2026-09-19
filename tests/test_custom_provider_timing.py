from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from PhyAgentOS.providers.base import GenerationSettings
from PhyAgentOS.providers.custom_provider import CustomProvider


class Stream:
    def __init__(self, *, hang=False):
        self.hang = hang
        self.closed = False

    async def close(self):
        self.closed = True

    async def __aiter__(self):
        for arguments in ('{"value":', '42}'):
            yield SimpleNamespace(
                usage=None,
                choices=[SimpleNamespace(
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[SimpleNamespace(
                            index=0, id="call-1" if arguments.startswith('{') else None,
                            function=SimpleNamespace(
                                name="choose" if arguments.startswith('{') else None,
                                arguments=arguments,
                            ),
                        )],
                    ), finish_reason=None,
                )],
            )
        if self.hang:
            await asyncio.Event().wait()


def test_streaming_reassembles_tool_arguments_and_records_timings():
    async def exercise():
        provider = CustomProvider(stream_responses=True)
        stream = Stream()
        create = AsyncMock(return_value=stream)
        provider._client.chat.completions.create = create
        try:
            response = await provider.chat_with_retry([{"role": "user", "content": "choose"}])
            assert response.tool_calls[0].arguments == {"value": 42}
            assert response.tool_calls[0].name == "choose"
            timing = response.timing
            assert 0 <= timing.request_to_headers_s <= timing.time_to_first_token_s <= timing.complete_response_s
            assert timing.observation_mode == "streaming"
            assert stream.closed
        finally:
            await provider._client.close()
    asyncio.run(exercise())


def test_streaming_timeout_closes_stream_and_logs_observed_first_event(caplog):
    async def exercise():
        provider = CustomProvider(stream_responses=True)
        provider.generation = GenerationSettings(request_timeout_s=0.1)
        stream = Stream(hang=True)
        create = AsyncMock(return_value=stream)
        provider._client.chat.completions.create = create
        try:
            with caplog.at_level("INFO"):
                response = await provider.chat_with_retry([{"role": "user", "content": "choose"}])
            assert response.finish_reason == "error"
            assert "timed out" in response.content
            assert create.await_count == 1
            assert stream.closed
            assert "Model request interrupted:" in caplog.text
            assert "first_token_s=None" not in caplog.text
        finally:
            await provider._client.close()
    asyncio.run(exercise())


def test_non_streaming_remains_compatible_and_marks_unobserved_phases():
    async def exercise():
        provider = CustomProvider()
        create = AsyncMock(return_value=SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="ready", tool_calls=[]), finish_reason="stop"
            )], usage=None,
        ))
        provider._client.chat.completions.create = create
        try:
            response = await provider.chat_with_retry([{"role": "user", "content": "ready?"}])
            assert response.content == "ready"
            assert "stream" not in create.call_args.kwargs
            assert response.timing.request_to_headers_s is None
            assert response.timing.time_to_first_token_s is None
            assert response.timing.complete_response_s >= 0
        finally:
            await provider._client.close()
    asyncio.run(exercise())
