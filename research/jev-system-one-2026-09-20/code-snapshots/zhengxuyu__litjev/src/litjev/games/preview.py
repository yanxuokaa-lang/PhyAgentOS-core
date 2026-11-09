"""Local Doom preview. One random-policy worker, multiple SSE viewers, no model."""

import argparse
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from litjev.games import make_env
from litjev.games.live import LiveSession
from litjev.vision import encode_image


class RandomPreview:
    def __init__(self, env, seed):
        self.env = env
        self.seed = seed
        self.episode = 0
        self.rng = np.random.default_rng(seed)
        self.history = deque(maxlen=90)
        self.reset()

    def reset(self):
        self.frame, _ = self.env.reset(seed=self.seed + self.episode)
        self.episode += 1
        self.step = 0
        self.reward = self.total_reward = 0.0
        self.done = False
        self.action = None
        self.step_ms = 0.0

    def advance(self):
        if self.done:
            self.reset()
            return
        started = perf_counter()
        action = int(self.rng.integers(self.env.action_space.n))
        self.frame, self.reward, terminated, truncated, _ = self.env.step(action)
        self.step_ms = (perf_counter() - started) * 1000
        self.total_reward += self.reward
        self.step += 1
        self.action = self.env.unwrapped.action_names[action]
        self.done = terminated or truncated
        self.history.append(
            {
                "episode": self.episode,
                "step": self.step,
                "action": self.action,
                "step_ms": self.step_ms,
                "reward": self.reward,
            }
        )

    def snapshot(self):
        actions = self.env.unwrapped.action_names
        return {
            "policy": "uniform_random",
            "forward_calls": 0,
            "frame": encode_image(self.frame),
            "actions": actions,
            "probabilities": [1 / len(actions)] * len(actions),
            "episode": self.episode,
            "step": self.step,
            "action": self.action,
            "reward": self.reward,
            "total_reward": self.total_reward,
            "done": self.done,
            "step_ms": self.step_ms,
            "history": list(self.history),
            "recording": self.env.unwrapped.recording_path.name
            if self.env.unwrapped.recording_path
            else None,
        }


class LiveControl(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    running: bool | None = None
    fps: int | None = Field(default=None, ge=1, le=30)


def create_preview_app(seed=7, max_steps=1000, resolution="640x480", recording=None):
    @asynccontextmanager
    async def lifespan(app):
        with make_env(
            "doom", max_steps=max_steps, resolution=resolution, recording_dir=recording
        ) as env:
            session = LiveSession(RandomPreview(env, seed))
            app.state.session = session
            try:
                yield
            finally:
                session.close()

    app = FastAPI(title="LitJev Doom — Random Preview", lifespan=lifespan)

    @app.get("/", include_in_schema=False)
    def index():
        template = (Path(__file__).parents[1] / "static" / "film.html").read_text()
        return HTMLResponse(template.replace('"__LITJEV_LIVE__"', "true", 1))

    @app.get("/state")
    def state():
        return app.state.session.snapshot()

    @app.get("/events", include_in_schema=False)
    async def events(request: Request):
        return StreamingResponse(
            app.state.session.events(request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.post("/control")
    def control(settings: LiveControl):
        return app.state.session.control(settings.running, settings.fps)

    @app.post("/step")
    def step():
        try:
            return app.state.session.step()
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @app.post("/reset")
    def reset():
        return app.state.session.reset()

    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8012)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--record", type=Path, help="Write native .lmp demos under a unique run directory"
    )
    args = parser.parse_args()
    uvicorn.run(
        create_preview_app(seed=args.seed, recording=args.record),
        host="127.0.0.1",
        port=args.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
