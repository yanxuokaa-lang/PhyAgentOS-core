"""Qwen3-VL-4B-Instruct vLLM scene-understanding adapter.

The vLLM server is operator-owned and long-lived.  This module only calls its
OpenAI-compatible chat-completions endpoint and projects the response through
the same semantic-only seam as the other scene-understanding providers.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlparse

import httpx

from .openai_scene_understanding import (
    SCENE_SEMANTIC_AMBIGUITY_CODES,
    ArtifactPayload,
    ArtifactResolver,
)

_VLLM_SCENE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["entities", "relations", "ambiguities"],
    "properties": {
        "entities": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["local_id", "category", "attributes", "confidence"],
            "properties": {"local_id": {"type": "string", "pattern": "^e[1-9][0-9]*$"},
                           "category": {"type": "string", "minLength": 1},
                           "attributes": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                               "required": ["name", "value", "confidence"],
                               "properties": {"name": {"type": "string"}, "value": {"type": ["string", "number", "boolean"]},
                                              "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}},
                           "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}},
        "relations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["subject_id", "predicate", "object_id", "relation_space", "confidence"],
            "properties": {"subject_id": {"type": "string"}, "predicate": {"type": "string"},
                           "object_id": {"type": "string"}, "relation_space": {"type": "string"},
                           "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}},
        "ambiguities": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["code", "message", "entity_ids"],
            "properties": {"code": {"type": "string", "enum": list(SCENE_SEMANTIC_AMBIGUITY_CODES)}, "message": {"type": "string"},
                           "entity_ids": {"type": "array", "items": {"type": "string"}}}}},
    },
}


class Qwen3VLVLLMInferenceError(RuntimeError):
    """Bounded local vLLM failure safe to route to the configured fallback."""


class Qwen3VLVLLMContractError(Qwen3VLVLLMInferenceError):
    """The local model returned an invalid semantic scene contract."""


class ChatCompletionsClient(Protocol):
    chat: Any


DiagnosticSink = Callable[[Mapping[str, Any]], None]


@dataclass(frozen=True)
class Qwen3VLVLLMConfig:
    api_base: str = "http://127.0.0.1:8012/v1"
    model: str = "qwen3-vl-4b-awq"
    api_key_env: str = ""
    timeout_seconds: float = 30.0
    max_output_tokens: int = 768

    def validate(self) -> None:
        parsed = urlparse(self.api_base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("api_base must be an absolute HTTP(S) URL")
        if not self.model.strip():
            raise ValueError("model must be non-empty")
        if self.timeout_seconds <= 0 or self.max_output_tokens <= 0:
            raise ValueError("timeout_seconds and max_output_tokens must be positive")


def _default_client_factory(**kwargs: Any) -> ChatCompletionsClient:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - deployment-only dependency
        raise Qwen3VLVLLMInferenceError("OpenAI SDK is not installed in the vLLM adapter environment") from exc
    return OpenAI(http_client=httpx.Client(trust_env=False), **kwargs)


class Qwen3VLVLLMSceneUnderstandingInference:
    """Call a persistent Qwen vLLM endpoint and return semantic claims only."""

    _REQUEST_KEYS = frozenset(
        {
            "observation_ref", "scene_revision", "frame_id", "calibration_ref",
            "freshness_ms", "max_age_ms", "artifacts",
        }
    )

    def __init__(
        self,
        resolver: ArtifactResolver | Callable[[str], ArtifactPayload | None],
        *,
        config: Qwen3VLVLLMConfig | None = None,
        client_factory: Callable[..., ChatCompletionsClient] | None = None,
        diagnostic_sink: DiagnosticSink | None = None,
    ) -> None:
        if not callable(getattr(resolver, "resolve", None)) and not callable(resolver):
            raise TypeError("artifact resolver must expose resolve(ref) or be callable")
        self.resolver = resolver
        self.config = config or Qwen3VLVLLMConfig()
        self.config.validate()
        self.client_factory = client_factory or _default_client_factory
        self.diagnostic_sink = diagnostic_sink
        self._last_error_class = "none"

    def diagnostic_summary(self) -> dict[str, str]:
        return {
            "provider_route": "qwen3-vl-4b-vllm",
            "provider_error_class": self._last_error_class,
        }

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(request, Mapping):
            raise Qwen3VLVLLMInferenceError("scene understanding request must be an object")
        if set(request) - self._REQUEST_KEYS:
            raise Qwen3VLVLLMInferenceError("scene understanding request contains unknown fields")
        artifacts = request.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise Qwen3VLVLLMInferenceError("scene understanding request has no artifacts")
        image_ref, image = self._resolve_image(artifacts)
        started = time.perf_counter()
        api_key = os.environ.get(self.config.api_key_env, "EMPTY") if self.config.api_key_env else "EMPTY"
        client = None
        try:
            client = self.client_factory(
                api_key=api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout_seconds,
            )
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._prompt(request)},
                            {
                                "type": "image_url",
                                "image_url": {"url": self._data_url(image)},
                            },
                        ],
                    }
                ],
                temperature=0,
                top_p=1,
                max_tokens=self.config.max_output_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "scene_understanding",
                        "strict": True,
                        "schema": _VLLM_SCENE_SCHEMA,
                    },
                },
            )
            content = self._content(response)
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                raise Qwen3VLVLLMInferenceError("qwen vLLM output was not valid JSON") from exc
            projected = _project_vllm_claims(parsed, image_ref)
            self._emit_diagnostic(
                {
                    "status": "available",
                    "provider": "qwen3-vl-vllm",
                    "model": self.config.model,
                    "route": "primary",
                    "observation_ref": request.get("observation_ref"),
                    "scene_revision": request.get("scene_revision"),
                    "frame_id": request.get("frame_id"),
                    "image_ref": image_ref,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "raw": parsed,
                    "projected": projected,
                }
            )
            self._last_error_class = "none"
            return projected
        except Qwen3VLVLLMInferenceError:
            self._last_error_class = "contract"
            self._emit_diagnostic(
                {
                    "status": "error",
                    "provider": "qwen3-vl-vllm",
                    "model": self.config.model,
                    "route": "primary",
                    "observation_ref": request.get("observation_ref"),
                    "scene_revision": request.get("scene_revision"),
                    "frame_id": request.get("frame_id"),
                    "image_ref": image_ref,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": "qwen_vllm_inference_error",
                }
            )
            raise
        except Exception as exc:
            self._last_error_class = "provider_failure"
            self._emit_diagnostic(
                {
                    "status": "error",
                    "provider": "qwen3-vl-vllm",
                    "model": self.config.model,
                    "route": "primary",
                    "observation_ref": request.get("observation_ref"),
                    "scene_revision": request.get("scene_revision"),
                    "frame_id": request.get("frame_id"),
                    "image_ref": image_ref,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": type(exc).__name__,
                }
            )
            raise Qwen3VLVLLMInferenceError("qwen vLLM scene understanding request failed") from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    def _resolve_image(self, refs: list[Any]) -> tuple[str, ArtifactPayload]:
        resolve = getattr(self.resolver, "resolve", None)
        for ref in refs:
            if not isinstance(ref, str):
                continue
            try:
                payload = resolve(ref) if callable(resolve) else self.resolver(ref)
            except Exception as exc:
                raise Qwen3VLVLLMInferenceError("observation artifact resolution failed") from exc
            if payload is not None:
                if not isinstance(payload, ArtifactPayload):
                    raise Qwen3VLVLLMInferenceError("artifact resolver returned an invalid payload")
                return ref, payload
        raise Qwen3VLVLLMInferenceError("no image artifact was available for scene understanding")

    @staticmethod
    def _data_url(image: ArtifactPayload) -> str:
        return f"data:{image.media_type};base64,{base64.b64encode(image.data).decode('ascii')}"

    def _emit_diagnostic(self, event: Mapping[str, Any]) -> None:
        if self.diagnostic_sink is None:
            return
        try:
            self.diagnostic_sink(dict(event))
        except Exception:
            # Optional diagnostics must never change the provider contract.
            return

    @staticmethod
    def _prompt(request: Mapping[str, Any]) -> str:
        return (
            "Inspect the entire RGB image and return an open-world semantic scene graph using "
            "exactly the requested JSON schema. List every clearly visible entity, including "
            "salient objects and large or low-contrast physical structures such as visible "
            "surfaces, shelves, trays, containers, hooks, rails, or articulated parts. A broad "
            "uniform background may still be a physical structure; do not discard it as void. "
            "Report visible directional, topology, containment, contact/support, attachment, "
            "occlusion, and visible-state relations. Report on/support only when contact is "
            "visually evident, not from color or relative image position alone. Use confidence "
            "in [0,1] and include identifying attributes such as color in the category and "
            "attributes. Do not infer metric depth, coordinates, plane equations, simulator "
            "truth, task success, IK, or motion authorization. Preserve semantic uncertainty "
            "in ambiguities. Do not return empty entities when visible entities are present. "
            "All provenance is assigned by the adapter."
        )

    @staticmethod
    def _content(response: Any) -> str:
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError, TypeError) as exc:
            raise Qwen3VLVLLMInferenceError("qwen vLLM response did not contain chat content") from exc
        if not isinstance(content, str) or not content.strip():
            raise Qwen3VLVLLMInferenceError("qwen vLLM response content was empty")
        return content


def _project_vllm_claims(value: Any, image_ref: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"entities", "relations", "ambiguities"}:
        raise Qwen3VLVLLMInferenceError("qwen vLLM output violated the provider contract")
    entities = []
    id_map: dict[str, str] = {}
    for item in value["entities"]:
        if not isinstance(item, Mapping) or set(item) != {"local_id", "category", "attributes", "confidence"}:
            raise Qwen3VLVLLMInferenceError("qwen vLLM entity fields are invalid")
        local_id = item["local_id"]
        if not isinstance(local_id, str) or local_id in id_map:
            raise Qwen3VLVLLMInferenceError("qwen vLLM entity identity is invalid")
        ref = f"entity://{local_id}"
        id_map[local_id] = ref
        category, confidence = _public_entity_category(item)
        entities.append({"entity_ref": ref, "category": category, "confidence": confidence, "provenance": [image_ref]})
    relations = []
    for item in value["relations"]:
        if not isinstance(item, Mapping) or set(item) != {"subject_id", "predicate", "object_id", "relation_space", "confidence"}:
            raise Qwen3VLVLLMInferenceError("qwen vLLM relation fields are invalid")
        subject, obj = id_map.get(item["subject_id"]), id_map.get(item["object_id"])
        if subject is None or obj is None or subject == obj:
            raise Qwen3VLVLLMInferenceError("qwen vLLM relation references unknown entity")
        relations.append({"relation_ref": f"relation://{item['subject_id']}-{item['predicate']}-{item['object_id']}",
                          "subject_ref": subject, "predicate": item["predicate"], "object_ref": obj,
                          "confidence": item["confidence"], "provenance": [image_ref]})
    ambiguities = []
    for item in value["ambiguities"]:
        if not isinstance(item, Mapping) or set(item) != {"code", "message", "entity_ids"}:
            raise Qwen3VLVLLMInferenceError("qwen vLLM ambiguity fields are invalid")
        if item["code"] not in SCENE_SEMANTIC_AMBIGUITY_CODES:
            raise Qwen3VLVLLMContractError("qwen vLLM ambiguity code violated the semantic contract")
        refs = [id_map[ref] for ref in item["entity_ids"] if ref in id_map]
        ambiguities.append({"code": item["code"], "message": item["message"], "entity_refs": refs})
    return {"entities": entities, "relations": relations, "spatial_envelopes": [], "ambiguities": ambiguities, "provider_available": True}


def _public_entity_category(item: Mapping[str, Any]) -> tuple[str, float]:
    """Fold a visible color into the public natural-language category.

    The public scene entity contract intentionally has no provider-specific
    ``attributes`` field, while downstream localization consumes ``category``
    as its text query. Preserve the model's color evidence at that boundary and
    lower the entity confidence when the color claim is less certain.
    """
    category = " ".join(str(item["category"]).split())
    confidence = float(item["confidence"])
    for attribute in item["attributes"]:
        if not isinstance(attribute, Mapping) or set(attribute) != {"name", "value", "confidence"}:
            raise Qwen3VLVLLMInferenceError("qwen vLLM entity attribute fields are invalid")
        if str(attribute["name"]).strip().casefold() != "color":
            continue
        value = attribute["value"]
        if not isinstance(value, str) or not value.strip():
            continue
        color = " ".join(value.split())
        normalized_category = f" {category.casefold()} "
        normalized_color = f" {color.casefold()} "
        if normalized_color not in normalized_category:
            category = f"{color} {category}"
        confidence = min(confidence, float(attribute["confidence"]))
        break
    return category, confidence


__all__ = [
    "Qwen3VLVLLMConfig",
    "Qwen3VLVLLMInferenceError",
    "Qwen3VLVLLMSceneUnderstandingInference",
]
