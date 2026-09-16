"""Concurrency-safe sleep and wake control for an operator-owned vLLM server."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from threading import Condition, Timer
from typing import Any, Callable, Iterator, Mapping, Protocol

import httpx

from .qwen3_vl_vllm_scene_understanding import Qwen3VLVLLMInferenceError


class Qwen3VLVLLMLifecycleError(Qwen3VLVLLMInferenceError):
    """The local engine lifecycle is unavailable or internally inconsistent."""


class _Response(Protocol):
    def raise_for_status(self) -> None: ...
    def json(self) -> Any: ...


class _ControlClient(Protocol):
    def get(self, path: str) -> _Response: ...
    def post(self, path: str, *, params: Mapping[str, Any] | None = None) -> _Response: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class Qwen3VLVLLMLifecycleConfig:
    control_api_base: str = "http://127.0.0.1:8012"
    idle_timeout_s: float = 60.0
    control_timeout_s: float = 5.0
    sleep_level: int = 1

    def validate(self) -> None:
        if not self.control_api_base.startswith(("http://", "https://")):
            raise ValueError("control_api_base must be an absolute HTTP(S) URL")
        if self.idle_timeout_s <= 0 or self.control_timeout_s <= 0:
            raise ValueError("vLLM lifecycle timeouts must be positive")
        if self.sleep_level not in {1, 2}:
            raise ValueError("vLLM sleep_level must be 1 or 2")


class Qwen3VLVLLMLifecycleManager:
    """Wake before inference and sleep only after the last request becomes idle."""

    def __init__(
        self,
        config: Qwen3VLVLLMLifecycleConfig,
        *,
        client_factory: Callable[..., _ControlClient] | None = None,
    ) -> None:
        config.validate()
        self.config = config
        factory = client_factory or httpx.Client
        self._client = factory(
            base_url=config.control_api_base.rstrip("/"),
            timeout=config.control_timeout_s,
        )
        self._condition = Condition()
        self._active_requests = 0
        self._transitioning = False
        self._closed = False
        self._idle_timer: Timer | None = None
        self.last_state: str = "unknown"
        self.last_error: str | None = None
        with self._condition:
            self._schedule_idle_timer_locked()

    @property
    def active_requests(self) -> int:
        with self._condition:
            return self._active_requests

    @contextmanager
    def request(self) -> Iterator[None]:
        self._enter_request()
        try:
            yield
        finally:
            self._leave_request()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._cancel_timer_locked()
            while self._transitioning:
                self._condition.wait()
        self._client.close()

    def sleep_for_handoff(self) -> None:
        """Synchronously release GPU residency before another provider starts."""

        with self._condition:
            self._cancel_timer_locked()
            while self._transitioning:
                self._condition.wait()
            if self._closed:
                raise Qwen3VLVLLMLifecycleError("qwen vLLM lifecycle manager is closed")
            if self._active_requests != 0:
                raise Qwen3VLVLLMLifecycleError(
                    "qwen vLLM cannot sleep while requests are active"
                )
            self._transitioning = True
        retry_idle = False
        try:
            self._sleep_and_verify()
        except Qwen3VLVLLMLifecycleError as exc:
            self.last_state = "error"
            self.last_error = type(exc).__name__
            retry_idle = True
            raise
        except Exception as exc:
            self.last_state = "error"
            self.last_error = type(exc).__name__
            retry_idle = True
            raise Qwen3VLVLLMLifecycleError(
                "qwen vLLM lifecycle handoff failed"
            ) from exc
        finally:
            with self._condition:
                self._transitioning = False
                if retry_idle and not self._closed and self._active_requests == 0:
                    self._schedule_idle_timer_locked()
                self._condition.notify_all()

    def _enter_request(self) -> None:
        with self._condition:
            if self._closed:
                raise Qwen3VLVLLMLifecycleError("qwen vLLM lifecycle manager is closed")
            self._cancel_timer_locked()
            while self._transitioning:
                self._condition.wait()
            self._active_requests += 1
            self._transitioning = True
        try:
            sleeping = self._is_sleeping()
            if sleeping:
                response = self._client.post("/wake_up")
                response.raise_for_status()
                if self._is_sleeping():
                    raise Qwen3VLVLLMLifecycleError(
                        "qwen vLLM remained asleep after wake_up"
                    )
            self.last_state = "awake"
            self.last_error = None
        except Qwen3VLVLLMLifecycleError:
            self._abort_entry()
            raise
        except Exception as exc:
            self._abort_entry()
            raise Qwen3VLVLLMLifecycleError(
                "qwen vLLM lifecycle wake/status check failed"
            ) from exc
        with self._condition:
            self._transitioning = False
            self._condition.notify_all()

    def _abort_entry(self) -> None:
        with self._condition:
            self._active_requests -= 1
            self._transitioning = False
            self.last_state = "error"
            self.last_error = "wake_or_status_failed"
            if not self._closed and self._active_requests == 0:
                self._schedule_idle_timer_locked()
            self._condition.notify_all()

    def _leave_request(self) -> None:
        with self._condition:
            self._active_requests -= 1
            if self._active_requests < 0:
                self._active_requests = 0
                raise RuntimeError("vLLM lifecycle request counter underflow")
            if self._active_requests == 0 and not self._closed:
                self._schedule_idle_timer_locked()

    def _sleep_if_idle(self) -> None:
        with self._condition:
            if self._closed or self._active_requests != 0 or self._transitioning:
                return
            self._idle_timer = None
            self._transitioning = True
        retry_idle = False
        try:
            self._sleep_and_verify()
        except Exception as exc:
            self.last_state = "error"
            self.last_error = type(exc).__name__
            retry_idle = True
        finally:
            with self._condition:
                self._transitioning = False
                if retry_idle and not self._closed and self._active_requests == 0:
                    self._schedule_idle_timer_locked()
                self._condition.notify_all()

    def _sleep_and_verify(self) -> None:
        if not self._is_sleeping():
            response = self._client.post(
                "/sleep", params={"level": self.config.sleep_level}
            )
            response.raise_for_status()
        if not self._is_sleeping():
            raise Qwen3VLVLLMLifecycleError(
                "qwen vLLM remained awake after sleep"
            )
        self.last_state = "sleeping"
        self.last_error = None

    def _is_sleeping(self) -> bool:
        response = self._client.get("/is_sleeping")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, bool):
            return payload
        if isinstance(payload, Mapping) and isinstance(payload.get("is_sleeping"), bool):
            return payload["is_sleeping"]
        raise Qwen3VLVLLMLifecycleError(
            "qwen vLLM is_sleeping returned an invalid payload"
        )

    def _cancel_timer_locked(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None

    def _schedule_idle_timer_locked(self) -> None:
        self._cancel_timer_locked()
        timer = Timer(self.config.idle_timeout_s, self._sleep_if_idle)
        timer.daemon = True
        self._idle_timer = timer
        timer.start()


class LifecycleManagedSceneUnderstandingInference:
    """Apply lifecycle management around exactly one local provider request."""

    def __init__(self, provider: Any, lifecycle: Qwen3VLVLLMLifecycleManager) -> None:
        self.provider = provider
        self.lifecycle = lifecycle

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None:
        with self.lifecycle.request():
            return self.provider.infer(request)

    def release(self) -> None:
        self.lifecycle.sleep_for_handoff()


__all__ = [
    "LifecycleManagedSceneUnderstandingInference",
    "Qwen3VLVLLMLifecycleConfig",
    "Qwen3VLVLLMLifecycleError",
    "Qwen3VLVLLMLifecycleManager",
]
