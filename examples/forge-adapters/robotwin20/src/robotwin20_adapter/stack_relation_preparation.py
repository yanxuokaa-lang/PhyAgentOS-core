"""Stack-task relation route preparation composed from the existing route machinery."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from PhyAgentOS.forge.manipulation import ManipulationIntent

from .stack_relation_execution import (
    StackRelationExecutionError,
    StackRelationExecutionProvider,
)


class StackRelationPreparationError(ValueError):
    """A stack relation route could not be prepared from current evidence."""


# Relation execution carries its own binding and Coordinator intent; the
# manipulation.prepare request keeps the remaining top-level lineage fields.
_RELATION_ONLY_ARGUMENT_KEYS = ("relation_binding", "relation_query_result", "candidate_ref")

# The route contract accepted by StackRelationExecutionProvider._validate_route,
# sourced from PreparedRoutes.register's persisted route arguments.
_ROUTE_ARGUMENT_FIELDS = (
    "scene_revision", "entity_ref", "candidate_ref", "assignment_ref",
    "assignment", "route_request", "approval_ref",
)


def build_stack_relation_route_preparation(
    deployment: Any,
    *,
    prepare_inputs: Callable[[Mapping[str, Any], str], Mapping[str, Any]] | None = None,
) -> Callable[[Mapping[str, Any], str], Mapping[str, Any]]:
    """Bind stack relation route preparation to the deployment's preparation Provider.

    The injected resolver supplies Coordinator-owned intent and current Query
    evidence. Grounding projects the selected relation target before the real
    preparation provider runs and validates the prepared route against
    the relation execution contract before returning it. Preparation failures
    propagate unchanged; the closure never starts an Action or motion.
    """
    preparation_provider = deployment.preparation_provider

    def prepare_route(request: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        binding = request.get("relation_binding")
        if (
            not isinstance(binding, Mapping)
            or not binding.get("entity_ref")
            or not binding.get("destination_ref")
            or not request.get("entity_ref")
            or not request.get("scene_revision")
        ):
            raise StackRelationPreparationError("relation binding fields are missing")
        if not callable(prepare_inputs):
            raise StackRelationPreparationError("stack preparation input resolver is not configured")
        resolved = prepare_inputs(deepcopy(dict(request)), task_id)
        if not isinstance(resolved, Mapping):
            raise StackRelationPreparationError("stack preparation resolver returned no inputs")
        prepare_request = deepcopy(dict(resolved))
        intent = ManipulationIntent.model_validate(prepare_request.get("intent"))
        trusted = ManipulationIntent.model_validate(request.get("intent"))
        if intent != trusted or intent.task_id != task_id:
            raise StackRelationPreparationError("preparation intent differs from trusted relation intent")
        for key in ("entity_ref", "scene_revision", "observation_ref", "calibration_ref"):
            if getattr(intent, key) != request.get(key):
                raise StackRelationPreparationError(f"relation identity differs from intent: {key}")
        for key in ("scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref"):
            if prepare_request.get(key) != getattr(intent, key):
                raise StackRelationPreparationError(f"preparation identity differs from intent: {key}")
        if (binding["entity_ref"] != intent.entity_ref
                or prepare_request.get("frame_id") != intent.observation_frame_id
                or request.get("observation_frame_id") != intent.observation_frame_id):
            raise StackRelationPreparationError("preparation entity/frame differs from relation")
        for key in ("binding_ref", "capability_snapshot_ref", "candidates", "target_geometry_source"):
            if not prepare_request.get(key):
                raise StackRelationPreparationError(f"preparation inputs lack {key}")
        candidates = prepare_request["candidates"]
        if not isinstance(candidates, (list, tuple)) or any(
            not isinstance(candidate, Mapping)
            or candidate.get("entity_ref") != intent.entity_ref
            or not str(candidate.get("candidate_ref", "")).startswith("candidate://")
            for candidate in candidates
        ):
            raise StackRelationPreparationError("preparation requires current entity grasp candidates")
        for key in _RELATION_ONLY_ARGUMENT_KEYS:
            prepare_request.pop(key, None)
        deployment.grounding.bind_relation_target(
            prepare_request["binding_ref"], binding,
            identity={key: prepare_request[key] for key in
                      ("scene_revision", "observation_ref", "calibration_ref")},
            geometry_source=prepare_request.pop("target_geometry_source"),
        )
        prepare_request["destination_ref"] = binding["destination_ref"]
        prepared = preparation_provider.prepare(prepare_request)
        route = _contract_route(prepared)
        route["task_id"] = intent.task_id
        try:
            StackRelationExecutionProvider._validate_route(route, request, task_id)
        except StackRelationExecutionError as exc:
            raise StackRelationPreparationError(str(exc)) from exc
        return deepcopy(route)

    return prepare_route


def build_stack_relation_execution_provider_factory(*, prepare_inputs=None) -> Callable[[Any, Any], Any]:
    """Compose the stack relation execution Provider with a closed motion gate.

    P2B-1 owns route preparation only; motion qualification stays explicitly
    unsupported until a later phase opens the gate.
    """

    def factory(client: Any, deployment: Any) -> Any:
        return StackRelationExecutionProvider(
            client,
            prepare_route=build_stack_relation_route_preparation(deployment, prepare_inputs=prepare_inputs),
            motion_supported=lambda: False,
        )

    return factory


def _contract_route(prepared: Any) -> dict[str, Any]:
    """Project the persistent prepare result onto the executable route contract."""
    arguments = prepared.get("route_arguments") if isinstance(prepared, Mapping) else None
    if not isinstance(arguments, Mapping):
        raise StackRelationPreparationError("preparation produced no executable route arguments")
    try:
        for field in _ROUTE_ARGUMENT_FIELDS:
            arguments[field]
        return deepcopy(dict(arguments))
    except KeyError as exc:
        raise StackRelationPreparationError(
            f"prepared route arguments lack {exc}"
        ) from exc


__all__ = [
    "StackRelationPreparationError",
    "build_stack_relation_execution_provider_factory",
    "build_stack_relation_route_preparation",
]
