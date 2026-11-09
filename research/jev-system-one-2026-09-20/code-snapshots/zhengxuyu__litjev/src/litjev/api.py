"""Jev-compatible standard endpoint and a separate LitJev diagnostics extension."""

from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from threading import Lock
from time import perf_counter

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from litjev.decision import DecisionResponse
from litjev.prompting import state_text
from litjev.schema import SystemOneRequest
from litjev.vision import MAX_BASE64_LENGTH, VisualState, decode_image


class DebugRequest(SystemOneRequest):
    image: str | None = Field(default=None, max_length=MAX_BASE64_LENGTH)


def create_app(engine_factory):
    app = FastAPI(title="LitJev System One")
    get_engine = lru_cache(maxsize=1)(engine_factory)
    load_lock = Lock()
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def playground():
        return FileResponse(static_dir / "index.html")

    @app.get("/film", include_in_schema=False)
    def film_playground():
        return FileResponse(static_dir / "film.html")

    @app.get("/example", include_in_schema=False)
    def example():
        return FileResponse(static_dir / "example.json")

    def evaluate(request, image=None):
        try:
            started = perf_counter()
            schema = request.to_schema()
            state = request.state
            if image is not None:
                state = VisualState(state_text(state), decode_image(image))
            # Validate schemas and images before loading weights.
            with load_lock:
                engine = get_engine()
            if request.model not in {"litjev", engine.model_id}:
                raise ValueError(
                    "Requested model is not loaded; use 'litjev' or the loaded model ID"
                )
            ready = perf_counter()
            evaluation = engine.evaluate(state, schema)
            finished = perf_counter()
            result = asdict(evaluation)
            result["diagnostics"]["timing"] = {
                "model_setup_seconds": ready - started,
                "decision_seconds": finished - ready,
                "total_seconds": finished - started,
            }
            return result
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.get("/health")
    def health():
        return {"status": "ok", "model_loaded": get_engine.cache_info().currsize > 0}

    @app.post("/v1/systemone", response_model=DecisionResponse)
    def systemone(request: SystemOneRequest):
        return evaluate(request)["result"]

    @app.post("/v1/systemone/debug")
    def systemone_debug(request: DebugRequest):
        return evaluate(request, request.image)

    return app
