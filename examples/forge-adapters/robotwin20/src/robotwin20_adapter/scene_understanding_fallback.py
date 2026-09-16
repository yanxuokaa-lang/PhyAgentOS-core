"""Explicit fallback composition for provider-neutral scene understanding."""

from __future__ import annotations

from typing import Any, Mapping, Protocol


class _Inference(Protocol):
    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


class SceneUnderstandingFallbackError(RuntimeError):
    """Both scene-understanding providers failed."""


class FallbackSceneUnderstandingInference:
    """Try the local provider first and GPT fallback second.

    ``last_route`` and ``last_error`` are adapter diagnostics only; they never
    cross the provider-neutral PAOS ToolSpec boundary.
    """

    def __init__(self, primary: _Inference, fallback: _Inference, *, primary_name: str, fallback_name: str) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_name = primary_name
        self.fallback_name = fallback_name
        self.last_route: str | None = None
        self.last_error: str | None = None

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None:
        try:
            result = self.primary.infer(request)
            if result is not None:
                self.last_route = self.primary_name
                self.last_error = None
                return result
            primary_error = "provider returned no result"
        except Exception as exc:
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
            raise SceneUnderstandingFallbackError("local and fallback scene understanding providers failed") from exc


__all__ = ["FallbackSceneUnderstandingInference", "SceneUnderstandingFallbackError"]
