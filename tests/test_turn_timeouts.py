from __future__ import annotations

import asyncio

from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.bus.events import InboundMessage, OutboundMessage
from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.providers.base import GenerationSettings, LLMProvider, LLMResponse


class _HangingProvider(LLMProvider):
    _CHAT_RETRY_DELAYS = ()

    async def chat(self, *args, **kwargs) -> LLMResponse:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    def get_default_model(self) -> str:
        return "test-model"


def test_provider_attempt_timeout_is_bounded_without_network() -> None:
    async def exercise() -> None:
        provider = _HangingProvider()
        provider.generation = GenerationSettings(request_timeout_s=0.01)

        response = await asyncio.wait_for(
            provider.chat_with_retry(messages=[{"role": "user", "content": "hi"}]),
            timeout=0.5,
        )

        assert response.finish_reason == "error"
        assert "timed out" in (response.content or "")

    asyncio.run(exercise())


def test_dispatch_emits_started_and_timeout_events_for_hanging_turn() -> None:
    async def exercise() -> None:
        bus = MessageBus()
        loop = object.__new__(AgentLoop)
        loop.bus = bus
        loop._processing_lock = asyncio.Lock()
        loop.turn_timeout_s = 0.01

        async def hang(_msg):
            await asyncio.Event().wait()

        loop._process_message = hang
        msg = InboundMessage(
            channel="cli",
            sender_id="user",
            chat_id="direct",
            content="test",
            metadata={"turn_id": "turn-1"},
        )

        await loop._dispatch(msg)
        started = await asyncio.wait_for(bus.consume_outbound(), timeout=0.2)
        timed_out = await asyncio.wait_for(bus.consume_outbound(), timeout=0.2)

        assert started.metadata["event_type"] == "turn_started"
        assert timed_out.metadata["event_type"] == "turn_timeout"
        assert timed_out.metadata["turn_id"] == "turn-1"
        assert "timed out" in timed_out.content

    asyncio.run(exercise())


def test_dispatch_emits_cancelled_event_when_active_turn_is_cancelled() -> None:
    async def exercise() -> None:
        bus = MessageBus()
        loop = object.__new__(AgentLoop)
        loop.bus = bus
        loop._processing_lock = asyncio.Lock()
        loop.turn_timeout_s = 10.0

        async def hang(_msg):
            await asyncio.Event().wait()

        loop._process_message = hang
        msg = InboundMessage(
            channel="cli",
            sender_id="user",
            chat_id="direct",
            content="test",
            metadata={"turn_id": "turn-2"},
        )

        task = asyncio.create_task(loop._dispatch(msg))
        started = await asyncio.wait_for(bus.consume_outbound(), timeout=0.2)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        cancelled = await asyncio.wait_for(bus.consume_outbound(), timeout=0.2)

        assert started.metadata["event_type"] == "turn_started"
        assert cancelled.metadata["event_type"] == "turn_cancelled"
        assert cancelled.metadata["turn_id"] == "turn-2"

    asyncio.run(exercise())


def test_queued_turn_starts_after_previous_turn_times_out() -> None:
    async def exercise() -> None:
        bus = MessageBus()
        loop = object.__new__(AgentLoop)
        loop.bus = bus
        loop._processing_lock = asyncio.Lock()
        loop.turn_timeout_s = 0.01

        async def process(msg):
            if msg.content == "first":
                await asyncio.Event().wait()
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="second completed",
                metadata={**msg.metadata, "event_type": "turn_completed"},
            )

        loop._process_message = process
        first = InboundMessage(
            channel="cli",
            sender_id="user",
            chat_id="direct",
            content="first",
            metadata={"turn_id": "turn-first"},
        )
        second = InboundMessage(
            channel="cli",
            sender_id="user",
            chat_id="direct",
            content="second",
            metadata={"turn_id": "turn-second"},
        )

        await asyncio.gather(loop._dispatch(first), loop._dispatch(second))
        events = [
            await asyncio.wait_for(bus.consume_outbound(), timeout=0.2)
            for _ in range(4)
        ]

        assert [event.metadata["event_type"] for event in events] == [
            "turn_started",
            "turn_timeout",
            "turn_started",
            "turn_completed",
        ]
        assert events[-1].content == "second completed"

    asyncio.run(exercise())
