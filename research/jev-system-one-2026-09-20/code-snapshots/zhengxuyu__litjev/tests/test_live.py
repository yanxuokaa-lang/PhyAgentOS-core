import asyncio
import json
from time import monotonic, sleep

from litjev.games.live import LiveSession


class Preview:
    def __init__(self):
        self.steps = 0

    def snapshot(self):
        return {"step": self.steps}

    def advance(self):
        self.steps += 1


def test_sse_watchers_share_latest_state_and_never_step_game():
    class Connected:
        async def is_disconnected(self):
            return False

    async def scenario():
        preview = Preview()
        session = LiveSession(preview)
        first, second = session.events(Connected()), session.events(Connected())
        try:
            a, b = await anext(first), await anext(second)
            assert a == b and preview.steps == 0
            session.step()  # Must not block: neither suspended SSE yield holds the lock.
            a, b = await anext(first), await anext(second)
            assert a == b and preview.steps == 1
            payload = json.loads(a.split("data: ", 1)[1])
            assert payload["step"] == 1 and payload["version"] == 2
        finally:
            await first.aclose()
            await second.aclose()
            session.close()
        assert not session.worker.is_alive()

    asyncio.run(scenario())


def test_worker_error_is_published_and_stops_loop():
    class Broken(Preview):
        def advance(self):
            raise RuntimeError("test failure")

    session = LiveSession(Broken())
    try:
        session.control(running=True)
        deadline = monotonic() + 2
        while session.snapshot()["error"] is None and monotonic() < deadline:
            sleep(0.01)
        result = session.snapshot()
        assert result["error"] == "RuntimeError: test failure"
        assert result["running"] is False
    finally:
        session.close()
