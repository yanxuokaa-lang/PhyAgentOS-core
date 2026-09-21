"""Explicit fallback composition for provider-neutral scene understanding."""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping, Protocol


class _Inference(Protocol):
    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


class SceneUnderstandingFallbackError(RuntimeError):
    """Both scene-understanding providers failed with bounded diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        provider_error_class: str = "provider_failure",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider_error_class = provider_error_class
        self.retryable = retryable


class FallbackSceneUnderstandingInference:
    """Try the local provider first and GPT fallback second.

    ``last_route`` and ``last_error`` are adapter diagnostics only; they never
    cross the provider-neutral PAOS ToolSpec boundary.
    """

    def __init__(
        self,
        primary: _Inference,
        fallback: _Inference,
        *,
        primary_name: str,
        fallback_name: str,
        fallback_exceptions: tuple[type[Exception], ...] = (Exception,),
        fallback_on_empty: bool = True,
        diagnostic_sink: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_name = primary_name
        self.fallback_name = fallback_name
        self.fallback_exceptions = fallback_exceptions
        self.fallback_on_empty = fallback_on_empty
        self.diagnostic_sink = diagnostic_sink
        self.last_route: str | None = None
        self.last_error: str | None = None
        self.last_error_class: str | None = None

    @staticmethod
    def _error_class(exc: BaseException) -> str:
        chain: list[BaseException] = []
        current: BaseException | None = exc
        while current is not None and len(chain) < 8:
            chain.append(current)
            current = current.__cause__
        names = " ".join(
            f"{type(item).__name__} {item}".lower() for item in chain
        )
        if "auth" in names or "401" in names or "403" in names:
            return "authentication"
        if "timeout" in names or "timed out" in names:
            return "timeout"
        if "connection" in names or "connecterror" in names or "http" in names:
            return "transport"
        if any(token in names for token in ("contract", "schema", "invalid output", "violated")):
            return "contract"
        return "provider_failure"

    def diagnostic_summary(self) -> dict[str, str]:
        return {
            "provider_route": self.last_route or "none",
            "provider_error_class": self.last_error_class or "none",
        }

    def _emit(self, event: Mapping[str, Any]) -> None:
        if self.diagnostic_sink is None:
            return
        try:
            self.diagnostic_sink(dict(event))
        except Exception:
            return

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None:
        started = time.perf_counter()
        primary_error_class = "provider_failure"
        try:
            result = self.primary.infer(request)
            if result is not None:
                self.last_route = self.primary_name
                self.last_error = None
                self.last_error_class = None
                self._emit({
                    "status": "available", "route": self.primary_name,
                    "observation_ref": request.get("observation_ref"),
                    "scene_revision": request.get("scene_revision"),
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                })
                return result
            if not self.fallback_on_empty:
                return None
            primary_error = "provider returned no result"
        except self.fallback_exceptions as exc:
            primary_error = type(exc).__name__
            primary_error_class = self._error_class(exc)
        try:
            result = self.fallback.infer(request)
            if result is None:
                raise SceneUnderstandingFallbackError("fallback provider returned no result")
            self.last_route = self.fallback_name
            self.last_error = primary_error
            self.last_error_class = primary_error_class
            self._emit({
                "status": "available", "route": self.fallback_name,
                "provider_error_class": primary_error_class,
                "observation_ref": request.get("observation_ref"),
                "scene_revision": request.get("scene_revision"),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            })
            return result
        except Exception as exc:
            self.last_route = None
            self.last_error = f"{primary_error}; {type(exc).__name__}"
            fallback_error_class = self._error_class(exc)
            self.last_error_class = f"{primary_error_class}+{fallback_error_class}"
            self._emit({
                "status": "error", "route": "none",
                "provider_error_class": self.last_error_class,
                "observation_ref": request.get("observation_ref"),
                "scene_revision": request.get("scene_revision"),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            })
            raise SceneUnderstandingFallbackError(
                "local and fallback scene understanding providers failed",
                provider_error_class=self.last_error_class,
                retryable=("timeout" in self.last_error_class.split("+")
                            or "transport" in self.last_error_class.split("+")),
            ) from exc

    def release(self) -> None:
        if self.last_route != self.primary_name:
            return
        release = getattr(self.primary, "release", None)
        if callable(release):
            release()

    def release_for_request(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Release the primary provider, falling back when lifecycle handoff fails.

        The semantic result may already have been produced when GPU handoff is
        attempted.  A lifecycle-specific release failure must therefore retain
        the original request and route semantics through GPT instead of leaking
        an adapter-only cleanup error to the generic scene Tool.
        """
        if self.last_route != self.primary_name:
            return None
        release = getattr(self.primary, "release", None)
        if not callable(release):
            return None
        try:
            release()
            return None
        except self.fallback_exceptions as exc:
            primary_error = type(exc).__name__
        try:
            result = self.fallback.infer(request)
            if result is None:
                raise SceneUnderstandingFallbackError("fallback provider returned no result")
            self.last_route = self.fallback_name
            self.last_error = primary_error
            return result
        except Exception as exc:
            self.last_route = None
            self.last_error = f"{primary_error}; {type(exc).__name__}"
            fallback_error_class = self._error_class(exc)
            self.last_error_class = f"provider_failure+{fallback_error_class}"
            raise SceneUnderstandingFallbackError(
                "lifecycle handoff failed and fallback scene understanding failed",
                provider_error_class=self.last_error_class,
                retryable=fallback_error_class in {"timeout", "transport"},
            ) from exc


__all__ = ["FallbackSceneUnderstandingInference", "SceneUnderstandingFallbackError"]
