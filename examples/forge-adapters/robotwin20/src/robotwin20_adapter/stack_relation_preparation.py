"""Stack-task relation route preparation composed from the existing route machinery."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from .stack_relation_execution import (
    StackRelationExecutionError,
    StackRelationExecutionProvider,
)


class StackRelationPreparationError(ValueError):
    """A stack relation route could not be prepared from current evidence."""


# Relation execution carries its own binding and Coordinator intent; the
# manipulation.prepare request keeps the remaining top-level lineage fields.
_RELATION_ONLY_ARGUMENT_KEYS = ("relation_binding", "intent")

# The route contract accepted by StackRelationExecutionProvider._validate_route,
# sourced from PreparedRoutes.register's persisted route arguments.
_ROUTE_ARGUMENT_FIELDS = (
    "scene_revision", "entity_ref", "candidate_ref", "assignment_ref",
    "assignment", "route_request", "approval_ref",
)


def build_stack_relation_route_preparation(
    deployment: Any,
) -> Callable[[Mapping[str, Any], str], Mapping[str, Any]]:
    """Bind stack relation route preparation to the deployment's preparation Provider.

    The returned ``prepare_route(request, task_id)`` maps the relation request
    onto the existing manipulation.prepare request, overrides the destination
    with the current relation binding, and validates the prepared route against
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
        prepare_request = deepcopy(dict(request))
        for key in _RELATION_ONLY_ARGUMENT_KEYS:
            prepare_request.pop(key, None)
        prepare_request["destination_ref"] = binding["destination_ref"]
        prepared = preparation_provider.prepare(prepare_request)
        route = _contract_route(prepared)
        try:
            StackRelationExecutionProvider._validate_route(route, request, task_id)
        except StackRelationExecutionError as exc:
            raise StackRelationPreparationError(str(exc)) from exc
        return deepcopy(route)

    return prepare_route


def build_stack_relation_execution_provider_factory() -> Callable[[Any, Any], Any]:
    """Compose the stack relation execution Provider with a closed motion gate.

    P2B-1 owns route preparation only; motion qualification stays explicitly
    unsupported until a later phase opens the gate.
    """

    def factory(client: Any, deployment: Any) -> Any:
        return StackRelationExecutionProvider(
            client,
            prepare_route=build_stack_relation_route_preparation(deployment),
            motion_supported=lambda: False,
        )

    return factory


def _contract_route(prepared: Any) -> dict[str, Any]:
    """Project the persistent prepare result onto the executable route contract."""
    arguments = prepared.get("route_arguments") if isinstance(prepared, Mapping) else None
    if not isinstance(arguments, Mapping):
        raise StackRelationPreparationError("preparation produced no executable route arguments")
    try:
        return {field: arguments[field] for field in _ROUTE_ARGUMENT_FIELDS}
    except KeyError as exc:
        raise StackRelationPreparationError(
            f"prepared route arguments lack {exc}"
        ) from exc


__all__ = [
    "StackRelationPreparationError",
    "build_stack_relation_execution_provider_factory",
    "build_stack_relation_route_preparation",
]
