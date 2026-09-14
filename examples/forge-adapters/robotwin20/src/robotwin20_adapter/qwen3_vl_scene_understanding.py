"""Local Qwen3-VL semantic provider for the RoboTwin adapter.

The model is deliberately isolated behind the same ``infer(request)`` seam as
the GPT provider.  It sees only the current RGB artifact and returns semantic
claims.  It never supplies metric geometry, simulator identity, or motion
authorization.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .openai_scene_understanding import ArtifactPayload, ArtifactResolver


class Qwen3VLInferenceError(RuntimeError):
    """A bounded local-provider failure safe to project as a Query failure."""


class QwenWorkerClient(Protocol):
    def request(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def release(self) -> None: ...


@dataclass(frozen=True)
class Qwen3VLConfig:
    model_path: str
    max_output_tokens: int = 512
    device: str = "cuda:0"

    def validate(self) -> None:
        path = Path(self.model_path)
        if not path.is_absolute() or not path.is_dir():
            raise ValueError("model_path must be an existing absolute directory")
        if not (path / "config.json").is_file():
            raise ValueError("model_path is missing config.json")
        if isinstance(self.max_output_tokens, bool) or self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if not self.device.strip():
            raise ValueError("device must be non-empty")


class Qwen3VLSceneUnderstandingInference:
    """Call one sequential Qwen worker and project only semantic claims."""

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
        config: Qwen3VLConfig,
        worker: QwenWorkerClient,
    ) -> None:
        if not callable(getattr(resolver, "resolve", None)) and not callable(resolver):
            raise TypeError("artifact resolver must expose resolve(ref) or be callable")
        if not callable(getattr(worker, "request", None)):
            raise TypeError("qwen worker must expose request(payload)")
        config.validate()
        self.resolver = resolver
        self.config = config
        self.worker = worker

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(request, Mapping):
            raise Qwen3VLInferenceError("scene understanding request must be an object")
        if set(request) - self._REQUEST_KEYS:
            raise Qwen3VLInferenceError("scene understanding request contains unknown fields")
        artifacts = request.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise Qwen3VLInferenceError("scene understanding request has no artifacts")
        image_ref, image = self._resolve_image(artifacts)
        request_id = os.urandom(16).hex()
        try:
            reply = self.worker.request(
                {
                    "request_id": request_id,
                    "operation": "understand_scene",
                    "observation_ref": request.get("observation_ref"),
                    "scene_revision": request.get("scene_revision"),
                    "frame_id": request.get("frame_id"),
                    "rgb_artifact_ref": image_ref,
                    "rgb_path": str(image.path) if image.path is not None else None,
                    "max_output_tokens": self.config.max_output_tokens,
                }
            )
            if not isinstance(reply, Mapping) or reply.get("request_id") != request_id:
                raise Qwen3VLInferenceError("qwen worker response identity mismatch")
            if reply.get("status") != "available":
                raise Qwen3VLInferenceError("qwen worker reported unavailable")
            return _project_claims(reply.get("result"), image_ref)
        except Qwen3VLInferenceError:
            raise
        except Exception as exc:
            raise Qwen3VLInferenceError("qwen scene understanding request failed") from exc
        finally:
            try:
                self.worker.release()
            except Exception as exc:
                raise Qwen3VLInferenceError("qwen worker release failed") from exc

    def _resolve_image(self, refs: list[Any]) -> tuple[str, ArtifactPayload]:
        resolve = getattr(self.resolver, "resolve", None)
        for ref in refs:
            if not isinstance(ref, str):
                continue
            try:
                payload = resolve(ref) if callable(resolve) else self.resolver(ref)
            except Exception as exc:
                raise Qwen3VLInferenceError("observation artifact resolution failed") from exc
            if payload is not None:
                if not isinstance(payload, ArtifactPayload):
                    raise Qwen3VLInferenceError("artifact resolver returned an invalid payload")
                return ref, payload
        raise Qwen3VLInferenceError("no image artifact was available for scene understanding")


def _project_claims(value: Any, image_ref: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise Qwen3VLInferenceError("qwen output must be an object")
    required = {"entities", "relations", "spatial_envelopes", "ambiguities"}
    if set(value) != required:
        raise Qwen3VLInferenceError("qwen output violated the provider contract")
    if any(not isinstance(value[key], list) for key in required):
        raise Qwen3VLInferenceError("qwen output arrays are invalid")
    entities = []
    refs: set[str] = set()
    for item in value["entities"]:
        if not isinstance(item, Mapping):
            raise Qwen3VLInferenceError("qwen entity is invalid")
        if set(item) != {"entity_ref", "category", "confidence"}:
            raise Qwen3VLInferenceError("qwen entity fields are invalid")
        ref, category, confidence = item["entity_ref"], item["category"], item["confidence"]
        if not isinstance(ref, str) or not ref.startswith("entity://") or ref in refs:
            raise Qwen3VLInferenceError("qwen entity reference is invalid")
        if not isinstance(category, str) or not category.strip():
            raise Qwen3VLInferenceError("qwen entity category is invalid")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise Qwen3VLInferenceError("qwen entity confidence is invalid")
        refs.add(ref)
        entities.append({**dict(item), "provenance": [image_ref]})
    relations = []
    for item in value["relations"]:
        if not isinstance(item, Mapping) or set(item) != {
            "relation_ref", "subject_ref", "predicate", "object_ref", "confidence"
        }:
            raise Qwen3VLInferenceError("qwen relation fields are invalid")
        if any(not isinstance(item.get(key), str) for key in ("relation_ref", "subject_ref", "predicate", "object_ref")):
            raise Qwen3VLInferenceError("qwen relation values are invalid")
        if item["subject_ref"] not in refs or item["object_ref"] not in refs:
            raise Qwen3VLInferenceError("qwen relation references unknown entity")
        confidence = item["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise Qwen3VLInferenceError("qwen relation confidence is invalid")
        relations.append({**dict(item), "provenance": [image_ref]})
    ambiguities = []
    for item in value["ambiguities"]:
        if not isinstance(item, Mapping) or set(item) != {"code", "message", "entity_refs"}:
            raise Qwen3VLInferenceError("qwen ambiguity fields are invalid")
        if not isinstance(item["code"], str) or not isinstance(item["message"], str):
            raise Qwen3VLInferenceError("qwen ambiguity values are invalid")
        if not isinstance(item["entity_refs"], list) or any(ref not in refs for ref in item["entity_refs"]):
            raise Qwen3VLInferenceError("qwen ambiguity references unknown entity")
        ambiguities.append(dict(item))
    if value["spatial_envelopes"]:
        raise Qwen3VLInferenceError("qwen must not emit metric spatial envelopes")
    return {
        "entities": entities,
        "relations": relations,
        "spatial_envelopes": [],
        "ambiguities": ambiguities,
        "provider_available": True,
    }


__all__ = ["Qwen3VLConfig", "Qwen3VLInferenceError", "Qwen3VLSceneUnderstandingInference"]
