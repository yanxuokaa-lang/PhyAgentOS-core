"""Provider-neutral perception-to-manipulation binding.

This module owns the PAOS query choreography, not a sensor or simulator
implementation.  Hosts provide observation, understanding, grasp, capability,
and preparation providers through the normal Query boundary.  The resulting
binding contains only opaque references and measured geometry; it never
contains a USD Prim path or an actuator command.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from PhyAgentOS.forge.capability_runtime import (
    CAPABILITY_TOOL_SPEC,
    GRASP_PROPOSAL_TOOL_SPEC,
    OBSERVATION_TOOL_SPEC,
    SCENE_UNDERSTANDING_TOOL_SPEC,
)

from .subtask_executor import PerceptionBinding


class PerceptionBindingError(ValueError):
    """Raised when a query chain cannot produce a safe binding."""


class QueryInvoker(Protocol):
    """The minimal PAOS query port consumed by this adapter."""

    def invoke_query(self, endpoint_id: str, operation: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]: ...


class PreparationBindingProvider(Protocol):
    """Provider-owned IK/collision/workspace preparation boundary."""

    def prepare_binding(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


Selector = Callable[[Mapping[str, Any]], bool]


@dataclass(frozen=True)
class BindingRequest:
    """Semantic request supplied by the task, independent of an environment."""

    sensor_refs: tuple[str, ...]
    source_category: str
    destination_category: str
    max_age_ms: int
    process_frame: str | None = None
    source_selector: Selector | None = None
    destination_selector: Selector | None = None

    def __post_init__(self) -> None:
        if not self.sensor_refs or any(not isinstance(item, str) or not item.strip() for item in self.sensor_refs):
            raise ValueError("sensor_refs must contain at least one non-empty sensor reference")
        if not isinstance(self.source_category, str) or not self.source_category.strip():
            raise ValueError("source_category must be non-empty")
        if not isinstance(self.destination_category, str) or not self.destination_category.strip():
            raise ValueError("destination_category must be non-empty")
        if isinstance(self.max_age_ms, bool) or self.max_age_ms < 1:
            raise ValueError("max_age_ms must be positive")


class PerceptionBindingAdapter:
    """Compose PAOS Queries into a fresh, measured ``PerceptionBinding``.

    The adapter is intentionally provider-neutral.  A host may use a simulated
    RGB-D camera, a real camera, or another simulator as long as it implements
    the PAOS Query contracts.  Semantic selection is task input; object paths
    are never accepted as a binding source.
    """

    _QUERY_SPECS = {
        item["tool_id"]: item
        for item in (
            OBSERVATION_TOOL_SPEC,
            SCENE_UNDERSTANDING_TOOL_SPEC,
            GRASP_PROPOSAL_TOOL_SPEC,
            CAPABILITY_TOOL_SPEC,
        )
    }

    def __init__(
        self,
        query_invoker: QueryInvoker | Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None,
        preparation_provider: PreparationBindingProvider | Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
        request: BindingRequest,
        *,
        destination_ref_factory: Callable[[Mapping[str, Any]], str] | None = None,
    ) -> None:
        self.query_invoker = query_invoker
        self.preparation_provider = preparation_provider
        self.request = request
        self.destination_ref_factory = destination_ref_factory or self._default_destination_ref

    @property
    def ready(self) -> bool:
        """Whether all provider ports needed for a binding exist."""

        query_ready = self.query_invoker is not None and (
            callable(self.query_invoker) or callable(getattr(self.query_invoker, "invoke_query", None))
        )
        preparation_ready = self.preparation_provider is not None and (
            callable(self.preparation_provider)
            or callable(getattr(self.preparation_provider, "prepare_binding", None))
        )
        return query_ready and preparation_ready

    def with_query_invoker(self, query_invoker: QueryInvoker) -> "PerceptionBindingAdapter":
        """Return the same semantic adapter bound to a PAOS Runtime query port."""

        return PerceptionBindingAdapter(
            query_invoker,
            self.preparation_provider,
            self.request,
            destination_ref_factory=self.destination_ref_factory,
        )

    def refresh_binding(self, previous: PerceptionBinding, expected_scene_revision: str) -> PerceptionBinding:
        """Re-run the complete chain after a scene revision change."""

        binding = self.bind()
        if binding.scene_revision != expected_scene_revision:
            raise PerceptionBindingError(
                "fresh perception scene revision differs from the execution revision"
            )
        if binding.entity_ref != previous.entity_ref or binding.destination_ref != previous.destination_ref:
            raise PerceptionBindingError("fresh perception changed the semantic task binding")
        return binding

    def bind(self) -> PerceptionBinding:
        if not self.ready:
            raise PerceptionBindingError("perception binding providers are unavailable")
        observation = self._query(
            "scene.observe",
            {
                "sensor_refs": list(self.request.sensor_refs),
                "max_age_ms": self.request.max_age_ms,
            },
        )
        self._require_available(observation, "scene.observe")
        identity = self._identity(observation, self.request.max_age_ms)
        understanding = self._query(
            "scene.understand",
            {
                **identity,
                "artifacts": [item["ref"] for item in observation.get("artifacts", [])],
            },
        )
        self._require_available(understanding, "scene.understand")
        self._validate_identity(understanding, identity, "scene.understand")
        source = self._select_entity(
            understanding.get("entities", []),
            self.request.source_category,
            self.request.source_selector,
            "source",
        )
        destination = self._select_entity(
            understanding.get("entities", []),
            self.request.destination_category,
            self.request.destination_selector,
            "destination",
        )
        envelopes = understanding.get("spatial_envelopes", [])
        source_envelope = self._envelope(envelopes, source["entity_ref"])
        destination_envelope = self._envelope(envelopes, destination["entity_ref"])
        grasp = self._query(
            "grasp.propose",
            {
                **identity,
                "targets": [
                    {
                        "entity_ref": source["entity_ref"],
                        "category": source["category"],
                        "confidence": source["confidence"],
                        "spatial_envelope": source_envelope,
                    }
                ],
            },
        )
        self._require_available(grasp, "grasp.propose")
        self._validate_identity(grasp, identity, "grasp.propose")
        candidate_set_ref = self._same(grasp, "candidate_set_ref", "candidate set")
        candidates = [
            item for item in grasp.get("candidates", [])
            if isinstance(item, Mapping) and item.get("entity_ref") == source["entity_ref"]
        ]
        if len(candidates) != 1:
            raise PerceptionBindingError("grasp.propose must retain exactly one source candidate")
        candidate = dict(candidates[0])
        capability = self._query(
            "manipulation.capabilities",
            {
                "scene_revision": identity["scene_revision"],
                "observation_ref": identity["observation_ref"],
                "calibration_ref": identity["calibration_ref"],
            },
        )
        self._require_available(capability, "manipulation.capabilities")
        self._validate_identity(capability, identity, "manipulation.capabilities")
        capability_ref = self._text(capability.get("snapshot_ref"), "capability snapshot reference")
        destination_ref = self.destination_ref_factory(destination)
        if not isinstance(destination_ref, str) or not destination_ref.startswith("destination://"):
            raise PerceptionBindingError("destination_ref_factory must return destination:// reference")
        prepared = self._prepare(
            {
                **identity,
                "candidate_set_ref": candidate_set_ref,
                "candidates": [candidate],
                "destination_ref": destination_ref,
                "capability_snapshot_ref": capability_ref,
                "source_entity": dict(source),
                "destination_entity": dict(destination),
                "source_envelope": deepcopy(source_envelope),
                "destination_envelope": deepcopy(destination_envelope),
            }
        )
        self._validate_preparation_identity(prepared, identity)
        preparation_ref = self._text(prepared.get("preparation_ref"), "preparation reference")
        assignment_ref = self._text(prepared.get("assignment_ref"), "assignment reference")
        if prepared.get("candidate_ref") != candidate["candidate_ref"]:
            raise PerceptionBindingError("preparation changed the selected grasp candidate")
        if prepared.get("candidate_set_ref") != candidate_set_ref:
            raise PerceptionBindingError("preparation changed the candidate set")
        if prepared.get("destination_ref") != destination_ref:
            raise PerceptionBindingError("preparation changed the destination")
        measured_pose = self._measured_pose(source_envelope)
        measured_geometry = self._measured_geometry(source_envelope)
        confidence = min(
            float(source["confidence"]),
            float(source_envelope["confidence"]),
            float(candidate["confidence"]),
        )
        process_frame = self.request.process_frame or identity["frame_id"]
        return PerceptionBinding.model_validate({
            "entity_ref": source["entity_ref"],
            "semantic_label": source["category"],
            "category": source["category"],
            "measured_pose": measured_pose,
            "measured_geometry": measured_geometry,
            "grasp_candidate_ref": candidate_set_ref,
            "candidate_set_ref": candidate_set_ref,
            "preparation_ref": preparation_ref,
            "candidate_ref": candidate["candidate_ref"],
            "capability_snapshot_ref": capability_ref,
            "assignment_ref": assignment_ref,
            "destination_ref": destination_ref,
            "destination_pose": self._measured_pose(destination_envelope),
            "process_frame": process_frame,
            "observation_ref": identity["observation_ref"],
            "scene_revision": identity["scene_revision"],
            "frame_id": identity["frame_id"],
            "calibration_ref": identity["calibration_ref"],
            "freshness_ms": identity["freshness_ms"],
            "max_age_ms": self.request.max_age_ms,
            "confidence": confidence,
            "provenance": f"query-chain:{identity['observation_ref']}",
        })

    def _query(self, tool_id: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        spec = self._QUERY_SPECS[tool_id]
        try:
            if callable(self.query_invoker):
                value = self.query_invoker(tool_id, dict(arguments))
            else:
                value = self.query_invoker.invoke_query(
                    spec["endpoint_id"], spec["operation"], dict(arguments)
                )
        except Exception as exc:
            raise PerceptionBindingError(f"{tool_id} query failed") from exc
        if not isinstance(value, Mapping):
            raise PerceptionBindingError(f"{tool_id} query returned a non-object")
        return dict(value)

    def _prepare(self, request: Mapping[str, Any]) -> dict[str, Any]:
        try:
            if callable(self.preparation_provider):
                value = self.preparation_provider(dict(request))
            else:
                value = self.preparation_provider.prepare_binding(dict(request))
        except Exception as exc:
            raise PerceptionBindingError("manipulation preparation failed") from exc
        if not isinstance(value, Mapping):
            raise PerceptionBindingError("manipulation preparation returned no binding")
        result = dict(value.get("arguments", value))
        if value.get("status", "available") not in {"available", "prepared"}:
            raise PerceptionBindingError("manipulation preparation is unavailable")
        return result

    @staticmethod
    def _validate_preparation_identity(
        prepared: Mapping[str, Any], identity: Mapping[str, Any]
    ) -> None:
        if any(prepared.get(key) != identity[key] for key in ("observation_ref", "scene_revision", "calibration_ref")):
            raise PerceptionBindingError("preparation changed observation provenance")
        frame = prepared.get("frame")
        if not isinstance(frame, Mapping) or frame.get("frame_id") != identity["frame_id"]:
            raise PerceptionBindingError("preparation changed frame provenance")

    @staticmethod
    def _require_available(result: Mapping[str, Any], tool_id: str) -> None:
        if result.get("status") not in {"available", "empty"}:
            raise PerceptionBindingError(f"{tool_id} is unavailable or stale")
        if result.get("status") == "empty":
            raise PerceptionBindingError(f"{tool_id} returned no usable result")

    @staticmethod
    def _identity(observation: Mapping[str, Any], max_age_ms: int) -> dict[str, Any]:
        frame = observation.get("frame")
        if not isinstance(frame, Mapping):
            raise PerceptionBindingError("observation has no frame")
        identity = {
            "observation_ref": observation.get("observation_ref"),
            "scene_revision": observation.get("scene_revision"),
            "frame_id": frame.get("frame_id"),
            "calibration_ref": observation.get("calibration_ref"),
            "freshness_ms": observation.get("freshness_ms"),
            "max_age_ms": max_age_ms,
        }
        if any(not isinstance(identity[key], str) or not identity[key].strip() for key in (
            "observation_ref", "scene_revision", "frame_id", "calibration_ref"
        )):
            raise PerceptionBindingError("observation provenance is incomplete")
        if not isinstance(identity["freshness_ms"], int) or not isinstance(identity["max_age_ms"], int):
            raise PerceptionBindingError("observation freshness is incomplete")
        if identity["freshness_ms"] > identity["max_age_ms"]:
            raise PerceptionBindingError("observation is stale")
        return identity

    @staticmethod
    def _validate_identity(result: Mapping[str, Any], identity: Mapping[str, Any], tool_id: str) -> None:
        if result.get("observation_ref") != identity["observation_ref"]:
            raise PerceptionBindingError(f"{tool_id} changed observation provenance")
        if result.get("scene_revision") != identity["scene_revision"]:
            raise PerceptionBindingError(f"{tool_id} changed scene revision")
        frame = result.get("frame")
        if frame is not None and (
            not isinstance(frame, Mapping) or frame.get("frame_id") != identity["frame_id"]
        ):
            raise PerceptionBindingError(f"{tool_id} changed frame provenance")
        if result.get("calibration_ref") != identity["calibration_ref"]:
            raise PerceptionBindingError(f"{tool_id} changed calibration provenance")

    @staticmethod
    def _select_entity(
        entities: Any,
        category: str,
        selector: Selector | None,
        role: str,
    ) -> dict[str, Any]:
        if not isinstance(entities, Sequence) or isinstance(entities, (str, bytes)):
            raise PerceptionBindingError("scene understanding returned no entities")
        selected = [
            dict(item) for item in entities
            if isinstance(item, Mapping)
            and item.get("category") == category
            and (selector is None or selector(item))
        ]
        if len(selected) != 1:
            raise PerceptionBindingError(f"{role} semantic selection is ambiguous or missing")
        return selected[0]

    @staticmethod
    def _envelope(envelopes: Any, entity_ref: str) -> dict[str, Any]:
        matches = [
            dict(item) for item in envelopes
            if isinstance(item, Mapping) and item.get("entity_ref") == entity_ref
        ]
        if len(matches) != 1:
            raise PerceptionBindingError("entity must have exactly one spatial envelope")
        return matches[0]

    @staticmethod
    def _measured_pose(envelope: Mapping[str, Any]) -> dict[str, Any]:
        low, high = envelope.get("min_xyz_m"), envelope.get("max_xyz_m")
        if not isinstance(low, list) or not isinstance(high, list) or len(low) != 3 or len(high) != 3:
            raise PerceptionBindingError("spatial envelope has invalid bounds")
        return {
            "frame_id": envelope["frame_id"],
            "unit": "m",
            "position_m": [(float(a) + float(b)) / 2.0 for a, b in zip(low, high, strict=True)],
            "orientation_xyzw": None,
            "source": "spatial_envelope_center",
        }

    @staticmethod
    def _measured_geometry(envelope: Mapping[str, Any]) -> dict[str, Any]:
        low, high = envelope["min_xyz_m"], envelope["max_xyz_m"]
        return {
            "frame_id": envelope["frame_id"],
            "unit": "m",
            "size_m": [float(b) - float(a) for a, b in zip(low, high, strict=True)],
            "source": "spatial_envelope",
        }

    @staticmethod
    def _same(result: Mapping[str, Any], key: str, label: str) -> str:
        value = result.get(key)
        if not isinstance(value, str) or not value:
            raise PerceptionBindingError(f"{label} is missing")
        return value

    @staticmethod
    def _text(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PerceptionBindingError(f"{label} is missing")
        return value

    @staticmethod
    def _default_destination_ref(entity: Mapping[str, Any]) -> str:
        entity_ref = entity.get("entity_ref")
        if not isinstance(entity_ref, str) or not entity_ref.startswith("entity://"):
            raise PerceptionBindingError("destination entity reference is invalid")
        return f"destination://{entity_ref.removeprefix('entity://')}"


__all__ = [
    "BindingRequest",
    "PerceptionBindingAdapter",
    "PerceptionBindingError",
    "PreparationBindingProvider",
    "QueryInvoker",
]
