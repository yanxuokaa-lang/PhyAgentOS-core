"""Coordinator-bound relation Action seam; providers own execution mechanics."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from PhyAgentOS.forge.capability_runtime import ActionAdmission, CapabilityRuntime

from .relation_target import bind_relation_target_candidate


class RelationExecutionProvider(Protocol):
    """Admit one relation execution using provider-owned geometry and routes."""

    def admit(
        self, request: Mapping[str, Any], *, invocation_id: str, attempt_id: str
    ) -> ActionAdmission | None: ...


class RelationContextResolver(Protocol):
    """Resolve a PAOS caller to the current Coordinator-owned node facts."""

    def __call__(self, caller_id: str) -> Mapping[str, Any]: ...


RELATION_ESTABLISH_TOOL_SPEC: dict[str, Any] = {
    "tool_id": "relation.establish",
    "endpoint_id": "relation_establish",
    "operation": "establish",
    "semantics": "action",
    "description": "Establish one current-scene spatial relation through a qualified Provider.",
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "capabilities": ["relation.establish"],
        "input_binding_keys": [
            "entity_ref", "goal_relation", "relation_target_ref", "scene_revision",
            "observation_ref", "observation_frame_id", "calibration_ref",
        ],
        "trusted_argument_builder": "manipulation_intent_v2",
        "argument_source_requirements": [
            {
                "when": {"goal_relation": "on"},
                "keys": ["relation_query_result"],
                "source_tool_id": "relation.target",
                "source_paths": {
                    "relation_query_result": ["response", "data"],
                },
            },
        ],
        "scene_write_behavior": "new_revision",
        "idempotency": "at_most_once",
    },
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "entity_ref", "goal_relation", "relation_target_ref", "scene_revision",
            "observation_ref", "observation_frame_id", "calibration_ref",
            "relation_query_result", "candidate_ref", "intent",
        ],
        "properties": {
            "entity_ref": {"type": "string", "pattern": "^entity://[^/]+$"},
            "goal_relation": {"type": "string", "minLength": 1},
            "relation_target_ref": {"type": "string", "pattern": "^(entity|surface)://[^/]+$"},
            "scene_revision": {"type": "string", "minLength": 1},
            "observation_ref": {"type": "string", "pattern": "^observation://[^/]+/[^/]+$"},
            "observation_frame_id": {"type": "string", "minLength": 1},
            "calibration_ref": {"type": "string", "pattern": "^artifact://\\S+$"},
            "relation_query_result": {"type": "object"},
            "candidate_ref": {"type": "string", "pattern": "^relation-target://\\S+$"},
            "intent": {"type": "object"},
        },
    },
}


class RelationEstablishActionEndpoint:
    """Validate Coordinator binding, then defer execution to a Provider."""

    def __init__(
        self,
        provider: RelationExecutionProvider,
        resolve_context: RelationContextResolver,
    ) -> None:
        self.provider = provider
        self.resolve_context = resolve_context

    def admit(self, arguments: Mapping[str, Any]) -> ActionAdmission:
        raise ValueError("relation Action requires a task-owned caller")

    def admit_for_caller(
        self, arguments: Mapping[str, Any], *, caller_id: str
    ) -> ActionAdmission:
        if not isinstance(caller_id, str) or not caller_id.startswith("paos:"):
            raise ValueError("relation Action caller must be bound to a PAOS task")
        context = self.resolve_context(caller_id)
        if not isinstance(context, Mapping):
            raise ValueError("Coordinator context resolver returned a non-object")
        required = (
            "task_id", "revision_id", "node_id", "node_digest",
            "input_binding_digest", "planning_binding", "intent",
        )
        if any(key not in context for key in required):
            raise ValueError("Coordinator context is incomplete for relation Action")
        request = dict(arguments)
        intent = context["intent"]
        planning_binding = context["planning_binding"]
        if not isinstance(intent, Mapping) or not isinstance(planning_binding, Mapping):
            raise ValueError("Coordinator context lacks trusted relation intent or binding")
        if intent.get("motion_authorized") is not False:
            raise ValueError("Coordinator relation intent must remain no-motion")
        identity = {
            "entity_ref": planning_binding.get("entity_ref"),
            "goal_relation": planning_binding.get("goal_relation"),
            "relation_target_ref": planning_binding.get("relation_target_ref"),
            "scene_revision": planning_binding.get("scene_revision"),
            "observation_ref": planning_binding.get("observation_ref"),
            "observation_frame_id": planning_binding.get("observation_frame_id"),
            "calibration_ref": planning_binding.get("calibration_ref"),
        }
        if any(not isinstance(value, str) or not value for value in identity.values()):
            raise ValueError("Coordinator relation binding is incomplete")
        if intent.get("calibration_ref") not in (None, identity["calibration_ref"]):
            raise ValueError("Coordinator intent calibration does not match the relation node")
        if request.get("intent") != intent:
            raise ValueError("relation Action must carry the persisted Coordinator intent")
        for key, expected in identity.items():
            request_value = request.get(key)
            if request_value != expected:
                raise ValueError(f"relation Action {key} does not match the Coordinator node")
        query_result = request.get("relation_query_result")
        if not isinstance(query_result, Mapping):
            raise ValueError("relation Action requires the current relation Query result")
        expected_query = {
            key: identity[key]
            for key in (
                "entity_ref", "goal_relation", "relation_target_ref", "observation_ref",
                "scene_revision", "calibration_ref",
            )
        }
        expected_query["frame_id"] = identity["observation_frame_id"]
        try:
            request["relation_binding"] = bind_relation_target_candidate(
                query_result,
                candidate_ref=request.get("candidate_ref"),
                expected=expected_query,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"relation geometry does not match the current observation: {exc}") from exc

        def start(invocation_id: str, attempt_id: str) -> ActionAdmission:
            try:
                admission = self.provider.admit(
                    request, invocation_id=invocation_id, attempt_id=attempt_id
                )
            except Exception as exc:
                return ActionAdmission(terminal_result={
                    "status": "unknown",
                    "outcome_known": False,
                    "error": {"code": "relation_provider_error", "message": str(exc)},
                })
            if not isinstance(admission, ActionAdmission):
                return ActionAdmission(terminal_result={
                    "status": "unknown",
                    "outcome_known": False,
                    "error": {"code": "invalid_relation_provider_admission"},
                })
            return admission

        return ActionAdmission(start=start, terminal_result={"status": "unknown", "outcome_known": False})


def register_relation_establish_tool(
    runtime: CapabilityRuntime,
    provider: RelationExecutionProvider,
    resolve_context: RelationContextResolver,
    tool_context_provider: Callable[[str], Any],
) -> None:
    """Register the relation Action on the existing Runtime lifecycle."""
    if not callable(resolve_context) or not callable(tool_context_provider):
        raise ValueError("relation Action context providers must be callable")
    runtime.register_tool(
        RELATION_ESTABLISH_TOOL_SPEC,
        RelationEstablishActionEndpoint(provider, resolve_context),
        context_provider=lambda: tool_context_provider("relation.establish"),
    )


__all__ = [
    "RELATION_ESTABLISH_TOOL_SPEC", "RelationContextResolver",
    "RelationEstablishActionEndpoint", "RelationExecutionProvider",
    "register_relation_establish_tool",
]
