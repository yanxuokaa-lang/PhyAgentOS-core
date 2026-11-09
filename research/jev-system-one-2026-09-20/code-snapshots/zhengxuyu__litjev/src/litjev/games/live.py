"""Single producer + bounded latest-state stream, adapted from PR #2's session design.

Readers never advance the game; slow readers skip snapshots instead of accumulating
screenshots. No condition lock is held across an SSE yield.
"""

import asyncio
import json
from threading import Condition, Thread
from time import perf_counter


class LiveSession:
    def __init__(self, preview):
        self.preview = preview
        self.condition = Condition()
        self.running = False
        self.closed = False
        self.fps = 9
        self.error = None
        self.version = 0
        self.latest = {}
        self._publish()
        self.worker = Thread(target=self._run, name="doom-preview", daemon=True)
        self.worker.start()

    def _publish(self):
        self.version += 1
        self.latest = {
            **self.preview.snapshot(),
            "version": self.version,
            "running": self.running,
            "fps": self.fps,
            "error": self.error,
        }

    def snapshot(self):
        with self.condition:
            return self.latest

    def control(self, running=None, fps=None):
        with self.condition:
            if running is not None:
                self.running = running
            if fps is not None:
                self.fps = fps
            self._publish()
            self.condition.notify_all()
            return self.latest

    def reset(self):
        with self.condition:
            self.preview.reset()
            self.error = None
            self._publish()
            return self.latest

    def step(self):
        with self.condition:
            if self.running:
                raise ValueError("Pause the background loop before single stepping")
            self.preview.advance()
            self._publish()
            return self.latest

    def _run(self):
        with self.condition:
            while not self.closed:
                self.condition.wait_for(lambda: self.running or self.closed)
                if self.closed:
                    return
                started = perf_counter()
                try:
                    self.preview.advance()
                    self._publish()
                except Exception as error:  # noqa: BLE001 — report worker failure to every viewer
                    self.error = f"{type(error).__name__}: {error}"
                    self.running = False
                    self.version += 1
                    self.latest = {
                        **self.latest,
                        "version": self.version,
                        "running": False,
                        "error": self.error,
                    }
                self.condition.wait(timeout=max(0, 1 / self.fps - (perf_counter() - started)))

    async def events(self, request):
        seen = -1
        heartbeat = perf_counter()
        while not self.closed and not await request.is_disconnected():
            payload = self.snapshot()
            if payload["version"] != seen:
                seen = payload["version"]
                yield f"id: {seen}\ndata: {json.dumps(payload, allow_nan=False)}\n\n"
                heartbeat = perf_counter()
            elif perf_counter() - heartbeat >= 5:
                yield ": keep-alive\n\n"
                heartbeat = perf_counter()
            await asyncio.sleep(0.05)

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()
        self.worker.join(timeout=20)
        if self.worker.is_alive():
            raise RuntimeError(
                "Doom worker did not stop; environment must not be closed concurrently"
            )
