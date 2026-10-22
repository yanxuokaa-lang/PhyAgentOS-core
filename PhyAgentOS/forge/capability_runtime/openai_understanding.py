"""Deployment-owned OpenAI Responses scene-understanding provider.

This module owns only the provider protocol and request translation.  It does
not know an environment, simulator, object name, or actuator.  A deployment
supplies the PAOS artifact resolver, endpoint/model settings, and optionally a
client factory for testing or an OpenAI-compatible gateway.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlparse

from ..artifacts import ArtifactContent, ArtifactResolver


class OpenAIUnderstandingError(RuntimeError):
    """Bounded provider failure; no model response text is exposed to PAOS."""

    def __init__(self, message: str, *, code: str = "provider_failure", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.provider_error_code = code
        self.provider_error_class = "provider_failure"
        self.retryable = retryable


class ResponsesClient(Protocol):
    responses: Any


@dataclass(frozen=True)
class OpenAIUnderstandingConfig:
    api_base: str
    model: str
    api_key_env: str = "OPENAI_API_KEY"
    reasoning_effort: str | None = None
    timeout_seconds: float = 60.0
    max_output_tokens: int = 1024

    def validate(self) -> None:
        parsed = urlparse(self.api_base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("api_base must be an absolute HTTP(S) URL")
        if not self.model.strip() or not self.api_key_env.strip():
            raise ValueError("model and api_key_env must be non-empty")
        if self.timeout_seconds <= 0 or self.max_output_tokens <= 0:
            raise ValueError("timeout_seconds and max_output_tokens must be positive")


SCENE_UNDERSTANDING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["entities", "relations", "spatial_envelopes", "ambiguities"],
    "properties": {
        "entities": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["entity_ref", "category", "confidence", "provenance"],
            "properties": {"entity_ref": {"type": "string"}, "category": {"type": "string"},
                           "confidence": {"type": "number"}, "provenance": {"type": "array", "items": {"type": "string"}}}}},
        "relations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["relation_ref", "subject_ref", "predicate", "object_ref", "confidence", "provenance"],
            "properties": {"relation_ref": {"type": "string"}, "subject_ref": {"type": "string"},
                           "predicate": {"type": "string"}, "object_ref": {"type": "string"},
                           "confidence": {"type": "number"}, "provenance": {"type": "array", "items": {"type": "string"}}}}},
        "spatial_envelopes": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["entity_ref", "frame_id", "unit", "min_xyz_m", "max_xyz_m", "confidence", "provenance"],
            "properties": {"entity_ref": {"type": "string"}, "frame_id": {"type": "string"}, "unit": {"type": "string"},
                           "min_xyz_m": {"type": "array", "items": {"type": "number"}},
                           "max_xyz_m": {"type": "array", "items": {"type": "number"}},
                           "confidence": {"type": "number"}, "provenance": {"type": "array", "items": {"type": "string"}}}}},
        "ambiguities": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["code", "message", "entity_refs"],
            "properties": {"code": {"type": "string"}, "message": {"type": "string"},
                           "entity_refs": {"type": "array", "items": {"type": "string"}}}}},
    },
}


def _default_client_factory(**kwargs: Any) -> ResponsesClient:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise OpenAIUnderstandingError("OpenAI SDK is not installed", code="sdk_unavailable") from exc
    return OpenAI(**kwargs)


class OpenAIResponsesSceneUnderstandingProvider:
    """Adapt an OpenAI-compatible GPT Responses API to ``scene.understand``."""

    def __init__(
        self,
        resolver: ArtifactResolver,
        config: OpenAIUnderstandingConfig,
        *,
        client_factory: Callable[..., ResponsesClient] | None = None,
    ) -> None:
        if not callable(getattr(resolver, "resolve", None)):
            raise TypeError("resolver must expose resolve(ref)")
        config.validate()
        self.resolver = resolver
        self.config = config
        self.client_factory = client_factory or _default_client_factory
        self._last_error = "none"

    def readiness_summary(self) -> dict[str, Any]:
        return {"ready": True, "provider_state": "configured", "provider_route": "openai-responses",
                "model": self.config.model, "last_error": self._last_error}

    def diagnostic_summary(self) -> dict[str, str]:
        return {"provider_route": "openai-responses", "provider_error_code": self._last_error}

    def understand(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(request, Mapping):
            raise OpenAIUnderstandingError("understanding request must be an object", code="invalid_request")
        refs = [item if isinstance(item, str) else item.get("ref") for item in request.get("artifacts", ())]
        refs = list(dict.fromkeys(ref for ref in refs if isinstance(ref, str)))
        if not refs:
            raise OpenAIUnderstandingError("understanding request has no artifacts", code="missing_artifacts")
        images: list[tuple[str, ArtifactContent]] = []
        for ref in refs:
            content = self.resolver.resolve(ref)
            if content is None:
                raise OpenAIUnderstandingError("observation artifact is unavailable", code="artifact_unavailable")
            if content.media_type.startswith("image/"):
                images.append((ref, content))
        if not images:
            raise OpenAIUnderstandingError("no image artifact is available", code="image_unavailable")
        api_key = os.environ.get(self.config.api_key_env)
        if not api_key:
            self._last_error = "missing_api_key"
            raise OpenAIUnderstandingError("configured model credential is unavailable", code="missing_api_key")
        payload: dict[str, Any] = {
            "model": self.config.model,
            "instructions": (
                "Return only JSON matching the schema. Infer visible semantic entities and relations from RGB. "
                "Do not infer metric pose, depth, IK, collision, task success, or motion authorization. "
                "Use the supplied artifact refs as provenance."
            ),
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": "Identify visible objects and semantic relations."},
                *[{"type": "input_image", "image_url": self._data_url(content), "detail": "high"}
                  for _, content in images],
            ]}],
            "text": {"format": {"type": "json_schema", "name": "scene_understanding",
                                  "strict": True, "schema": SCENE_UNDERSTANDING_SCHEMA}},
            "max_output_tokens": self.config.max_output_tokens,
            "store": False,
        }
        if self.config.reasoning_effort is not None:
            payload["reasoning"] = {"effort": self.config.reasoning_effort}
        client = None
        try:
            client = self.client_factory(api_key=api_key, base_url=self.config.api_base,
                                         timeout=self.config.timeout_seconds, max_retries=0)
            response = client.responses.create(**payload)
            raw = getattr(response, "output_text", None)
            if not isinstance(raw, str) or not raw.strip():
                raise OpenAIUnderstandingError("model returned no structured output", code="empty_output")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise OpenAIUnderstandingError("model output is not an object", code="invalid_output")
            if result.get("spatial_envelopes"):
                raise OpenAIUnderstandingError(
                    "RGB semantic inference cannot provide metric spatial envelopes",
                    code="unsupported_metric_claim",
                )
            provenance = [ref for ref, _ in images]
            for field in ("entities", "relations", "spatial_envelopes"):
                for item in result.get(field, ()):
                    if isinstance(item, dict) and not item.get("provenance"):
                        item["provenance"] = list(provenance)
            self._last_error = "none"
            return result
        except OpenAIUnderstandingError:
            raise
        except json.JSONDecodeError as exc:
            self._last_error = "invalid_output"
            raise OpenAIUnderstandingError("model output was not valid JSON", code="invalid_output") from exc
        except Exception as exc:
            self._last_error = type(exc).__name__
            raise OpenAIUnderstandingError("OpenAI Responses request failed", code="provider_failure", retryable=True) from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    @staticmethod
    def _data_url(content: ArtifactContent) -> str:
        return f"data:{content.media_type};base64,{base64.b64encode(content.data).decode('ascii')}"


__all__ = ["OpenAIResponsesSceneUnderstandingProvider", "OpenAIUnderstandingConfig", "OpenAIUnderstandingError",
           "SCENE_UNDERSTANDING_SCHEMA"]
