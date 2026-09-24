"""Bounded model-facing context projections for long Agent turns.

This module never mutates AgentTask, Gateway, or Session state.  It builds a
temporary request view from those owners immediately before each model call.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from PhyAgentOS.agent.planning_facts import response_facts
from PhyAgentOS.forge.binding import missing_preplan_queries

TERMINAL_EXECUTION_STATUSES = {"succeeded", "failed", "cancelled", "stopped", "unknown"}

_TASK_COMMON = {
    "forge_task_get",
    "forge_task_cancel",
    "forge_task_request_clarification",
}
_DISCOVERY = {
    "forge_tool_context",
    "forge_tool_query",
}


def _discovery_complete(task: Any) -> bool:
    """Expose planning submission only after durable discovery results exist."""
    return not missing_preplan_queries(task)


def _discovery_record_succeeded(record: Any) -> bool:
    """Treat provider-level non-success responses as incomplete discovery."""
    if getattr(record, "status", None) != "succeeded":
        return False
    response = getattr(record, "response", None)
    if not isinstance(response, dict):
        # Preserve compatibility with legacy persisted records that predate
        # response projection; the Coordinator still owns final admission.
        return True
    status = response_facts(response).get("status")
    return status not in {"unavailable", "invalid", "stale", "empty", "failed", "unknown"}
_PLANNING = {
    "forge_task_finalize",
    "forge_plan_activate",
    "forge_plan_ready",
    "forge_plan_select",
    "forge_tool_context",
    "forge_tool_query",
    "forge_tool_start_action",
    "forge_tool_start_session",
}


def _active_graph_completed(task: Any) -> bool:
    revision = getattr(task, "active_revision", None)
    graph = getattr(revision, "plan_graph", None) if revision is not None else None
    if graph is None:
        return False
    nodes = tuple(getattr(graph, "nodes", ()))
    settlements = {
        getattr(item, "node_id", None): getattr(item, "status", None)
        for item in getattr(revision, "node_settlements", ())
    }
    return bool(nodes) and all(
        settlements.get(getattr(node, "node_id", None)) == "completed" for node in nodes
    )


def _has_reconcilable_action(task: Any) -> bool:
    """Keep read-only recovery available for a persisted uncertain invocation."""
    settled_statuses = {"succeeded", "failed", "cancelled", "stopped"}
    return any(
        getattr(record, "semantics", None) == "action"
        and isinstance(getattr(record, "invocation_id", None), str)
        and bool(record.invocation_id)
        and getattr(record, "status", None) not in settled_statuses
        for record in getattr(task, "execution_records", ())
    )


_ACTION_RECONCILIATION = {
    "forge_tool_action_status",
    "forge_tool_action_result",
    "forge_tool_cancel_action",
}
_SESSION_RECONCILIATION = {
    "forge_tool_session_status",
    "forge_tool_session_result",
    "forge_tool_stop_session",
}

_REFERENCE_KEYS = {
    "task_id",
    "revision_id",
    "record_id",
    "node_id",
    "obligation_id",
    "tool_id",
    "status",
    "semantics",
    "ownership",
    "caller_id",
    "skill_binding_id",
    "runtime_binding_id",
    "planning_binding_id",
    "tool_spec_sha256",
    "node_digest",
    "input_binding_digest",
    "invocation_id",
    "attempt_id",
    "observation_ref",
    "scene_revision",
    "new_scene_revision",
    "calibration_ref",
    "binding_ref",
    "capability_snapshot_ref",
    "assignment_ref",
    "candidate_set_ref",
    "preparation_ref",
    "candidate_ref",
    "entity_ref",
    "entity_refs",
    "destination_ref",
    "acquire_invocation_ref",
    "evidence_refs",
    "decision_trace_ref",
    "planning_binding",
    "motion_authorized",
    "world_changed",
    "world_change_started",
    "outcome_known",
    "ready",
    "binding_error",
    "freshness_ms",
    "max_age_ms",
    "frame",
    "frame_id",
    "unit",
    "error",
    "code",
    "message",
    "type",
}
_FULL_VALUE_KEYS = {
    "candidate_tool_ids",
    "frozen_tool_input_schemas",
    "input_schema",
    "missing_runtime_arguments",
    "output_schema",
    "planning_binding",
    "node_diagnostics",
    "condition_facts",
    "preconditions",
    "required_evidence",
    "produced_evidence",
    "expected_effects",
    "failure_classes",
    "idempotency",
    "resources",
    "required_tool_arguments",
    "scene_write",
}
_SEMANTIC_KEYS = {
    "entities",
    "relations",
    "spatial_envelopes",
    "ambiguities",
    "metric_localization",
    "object_geometry",
    "segmentation",
    "condition_facts",
    "resources_in_use",
    "post_release_evidence",
    "capability_outcome_summary",
    "ready_nodes",
    "node_diagnostics",
    "artifacts",
    "targets",
    "geometry",
    "pose",
    "position",
    "center",
    "extent",
    "bbox",
    "confidence",
    "category",
    "attributes",
    "tool",
    "description",
    "endpoint_id",
    "operation",
    "input_schema",
    "output_schema",
    "preconditions",
    "required_evidence",
    "produced_evidence",
    "expected_effects",
    "failure_classes",
    "idempotency",
    "resources",
    "scene_write",
}

_SCHEMA_KEYS = {
    "type",
    "required",
    "properties",
    "items",
    "enum",
    "const",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "uniqueItems",
    "additionalProperties",
    "pattern",
}


class PromptBudgetExceededError(RuntimeError):
    """The temporary model request still exceeds the configured hard window."""


@dataclass(frozen=True)
class PromptRequestView:
    messages: list[dict[str, Any]]
    visible_tool_names: tuple[str, ...]
    phase: str
    compacted: bool


def visible_tool_names(all_names: Iterable[str], task: Any | None) -> tuple[str, ...]:
    """Select Forge wrappers by lifecycle phase without changing execution access.

    Non-Forge tools retain their existing availability.  Registry admission and
    Gateway checks remain authoritative even when a wrapper is model-visible.
    """

    names = tuple(all_names)
    generic = {name for name in names if not name.startswith("forge_")}
    if task is None:
        allowed = generic | {"forge_task_create", "forge_tool_context", "forge_tool_query"}
        return tuple(name for name in names if name in allowed)

    status = _task_status(task)
    if getattr(task, "terminal", False):
        allowed = generic | {"forge_task_create", "forge_task_get", "forge_tool_context"}
        if _has_reconcilable_action(task):
            allowed |= {"forge_tool_action_status", "forge_tool_action_result"}
        return tuple(name for name in names if name in allowed)

    if (
        status == "cancelling"
        or getattr(task, "cancellation_requested", False)
        or getattr(task, "pause_requested", False)
    ):
        allowed = generic | _TASK_COMMON | _ACTION_RECONCILIATION | _SESSION_RECONCILIATION
        return tuple(name for name in names if name in allowed)

    records = tuple(getattr(task, "execution_records", ()))
    in_flight = [
        record
        for record in records
        if getattr(record, "status", None) not in TERMINAL_EXECUTION_STATUSES
    ]
    if in_flight:
        latest = in_flight[-1]
        reconciliation = (
            _SESSION_RECONCILIATION
            if getattr(latest, "semantics", None) == "session"
            else _ACTION_RECONCILIATION
        )
        allowed = generic | _TASK_COMMON | reconciliation
        return tuple(name for name in names if name in allowed)

    revision = getattr(task, "active_revision", None)
    graph = getattr(revision, "plan_graph", None) if revision is not None else None
    if graph is None:
        allowed = generic | _TASK_COMMON | _DISCOVERY
        if _discovery_complete(task):
            allowed.add("forge_task_materialize_plan")
    elif status == "awaiting_replan":
        allowed = (
            generic
            | _TASK_COMMON
            | {
                "forge_task_begin_revision",
                "forge_tool_context",
                "forge_tool_query",
            }
        )
    elif status == "waiting_for_user":
        allowed = generic | _TASK_COMMON | {"forge_tool_context"}
    else:
        allowed = (
            generic | _TASK_COMMON | _PLANNING | _ACTION_RECONCILIATION | _SESSION_RECONCILIATION
        )
        if _active_graph_completed(task):
            allowed.add("forge_task_continue_plan")
    return tuple(name for name in names if name in allowed)


def _safe_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _safe_json(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, dict):
        return {str(key): _safe_json(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_json(child) for child in value]
    enum_value = getattr(value, "value", None)
    return enum_value if isinstance(enum_value, (str, int, float, bool)) else value


def _task_status(task: Any) -> Any:
    status = getattr(task, "status", None)
    return getattr(status, "value", status)


def _reference_projection(value: Any, *, keep_semantics: bool = True) -> Any:
    """Retain execution identities and bounded semantic evidence from JSON data."""

    value = _safe_json(value)
    if isinstance(value, dict):
        projected: dict[str, Any] = {}
        for key, child in value.items():
            if key in _FULL_VALUE_KEYS:
                projected[key] = _safe_json(child)
                continue
            if (
                key in _REFERENCE_KEYS
                or key.endswith("_ref")
                or key.endswith("_refs")
                or "_T_" in key
                or key.endswith("_pose")
                or keep_semantics
                and key in _SEMANTIC_KEYS
            ):
                projected[key] = _reference_projection(child, keep_semantics=keep_semantics)
            elif key in {"data", "context", "paos_record", "result", "response"}:
                nested = _reference_projection(child, keep_semantics=keep_semantics)
                if nested not in ({}, [], None):
                    projected[key] = nested
        return projected
    if isinstance(value, list):
        return [_reference_projection(child, keep_semantics=keep_semantics) for child in value]
    return value


def _schema_projection(value: Any) -> Any:
    """Keep invocation shape while dropping prose and provider extensions."""

    value = _safe_json(value)
    if isinstance(value, dict):
        projected: dict[str, Any] = {}
        for key, child in value.items():
            if key == "properties" and isinstance(child, dict):
                projected[key] = {
                    str(property_name): _schema_projection(property_schema)
                    for property_name, property_schema in child.items()
                }
            elif key in _SCHEMA_KEYS:
                projected[key] = _schema_projection(child)
        return projected
    if isinstance(value, list):
        return [_schema_projection(child) for child in value]
    return value


def _context_result_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Project one ToolSpec without duplicating the model-visible wrapper schema."""

    data = payload.get("data")
    if not isinstance(data, dict):
        return _reference_projection(payload)
    tool = data.get("tool")
    context = data.get("context")
    projected_tool: dict[str, Any] = {}
    if isinstance(tool, dict):
        for key in ("tool_id", "implementation_id", "endpoint_id", "operation", "semantics"):
            if key in tool:
                projected_tool[key] = tool[key]
        if isinstance(tool.get("planning"), dict):
            projected_tool["planning"] = _reference_projection(tool["planning"])
        for key in ("input_schema", "output_schema"):
            if key in tool:
                projected_tool[key] = _schema_projection(tool[key])
    projected_context = {}
    if isinstance(context, dict):
        for key in (
            "ready",
            "binding_error",
            "motion_authorized",
            "tool_id",
            "runtime_profile",
            "runtime_instance_id",
        ):
            if key in context:
                projected_context[key] = _reference_projection(context[key])
    result: dict[str, Any] = {"data": {"tool": projected_tool, "context": projected_context}}
    paos_record = payload.get("paos_record")
    if paos_record is not None:
        result["paos_record"] = _reference_projection(paos_record)
    for key in ("ok", "error", "status"):
        if key in payload:
            result[key] = _reference_projection(payload[key])
    return result


def _task_result_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep task-read lifecycle facts; the injected task projection owns the rest."""

    data = payload.get("data")
    if not isinstance(data, dict):
        return _reference_projection(payload)
    projected_data: dict[str, Any] = {}
    for key in (
        "task_id",
        "status",
        "terminal",
        "active_revision_id",
        "active_revision_number",
        "revision_id",
        "plan_graph_ref",
        "invocation_id",
        "destination_ref",
        "plan_materialized",
        "motion_authorized",
        "verdict",
        "before_snapshot_ref",
        "after_snapshot_ref",
        "evidence_bundle_ref",
        "evidence_bundle_id",
        "evidence_errors",
        "error",
    ):
        if key in data:
            projected_data[key] = _reference_projection(data[key])
    for key in ("ok", "error", "status"):
        if key in payload:
            projected_data[key] = _reference_projection(payload[key])
    return {"data": projected_data}


def compact_tool_result(tool_name: str, content: str) -> str:
    """Create a deterministic non-authoritative prompt summary of a Tool result."""

    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return content
    if tool_name == "forge_plan_ready" and isinstance(payload, dict) and "source_page" in payload:
        # This is already a bounded catalog, not an unabridged producer payload.
        # Earlier pages remain necessary to match identities across source arrays.
        return content
    if tool_name == "forge_tool_context" and isinstance(payload, dict):
        projection = _context_result_projection(payload)
    elif tool_name.startswith("forge_task_") and isinstance(payload, dict):
        projection = _task_result_projection(payload)
    else:
        projection = _reference_projection(payload)
    return json.dumps(
        {
            "version": "agent_tool_result_summary_v1",
            "tool_name": tool_name,
            "authority": "read_only_prompt_projection",
            "source_of_truth": "AgentTaskCoordinator_and_Forge_Gateway",
            "result": projection,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _task_binding_projection(binding: Any) -> Any:
    """Keep binding facts while leaving Tool schemas to live Tool context."""
    payload = _safe_json(binding)
    if not isinstance(payload, dict):
        return payload
    payload.pop("input_schema", None)
    for tool in payload.get("required_tools", ()):
        if isinstance(tool, dict):
            tool.pop("input_schema", None)
    return payload


def task_prompt_projection(task: Any | None) -> dict[str, Any] | None:
    """Project current persisted task state for model orientation between calls."""

    if task is None:
        return None
    revision = getattr(task, "active_revision", None)
    graph = getattr(revision, "plan_graph", None) if revision is not None else None
    nodes = []
    if graph is not None:
        for node in getattr(graph, "nodes", ()):
            nodes.append(
                {
                    "node_id": getattr(node, "node_id", None),
                    "obligation_id": getattr(node, "obligation_id", None),
                    "capability": getattr(node, "capability", None),
                    "dependencies": list(getattr(node, "dependencies", ())),
                    "conditions": list(getattr(node, "conditions", ())),
                    "required_evidence": list(getattr(node, "required_evidence", ())),
                    "produced_evidence": list(getattr(node, "produced_evidence", ())),
                    "resources": _safe_json(getattr(node, "resources", ())),
                    "effects": list(getattr(node, "effects", ())),
                    "input_bindings": _safe_json(getattr(node, "input_bindings", {})),
                    "retry_of": getattr(node, "retry_of", None),
                }
            )

    execution_records = list(getattr(task, "execution_records", ()))
    latest_by_tool: dict[str, int] = {}
    for index, record in enumerate(execution_records):
        tool_id = getattr(record, "tool_id", None)
        if isinstance(tool_id, str):
            latest_by_tool[tool_id] = index

    records = []
    for index, record in enumerate(execution_records):
        tool_id = getattr(record, "tool_id", None)
        keep_semantics = isinstance(tool_id, str) and latest_by_tool.get(tool_id) == index
        records.append(
            {
                "record_id": getattr(record, "record_id", None),
                "revision_id": getattr(record, "revision_id", None),
                "tool_id": tool_id,
                "semantics": getattr(record, "semantics", None),
                "status": getattr(record, "status", None),
                "skill_binding_id": getattr(record, "skill_binding_id", None),
                "runtime_binding_id": getattr(record, "runtime_binding_id", None),
                "skill_use_ids": list(getattr(record, "skill_use_ids", ())),
                "tool_spec_sha256": getattr(record, "tool_spec_sha256", None),
                "caller_id": getattr(record, "caller_id", None),
                "node_id": getattr(record, "node_id", None),
                "node_digest": getattr(record, "node_digest", None),
                "obligation_id": getattr(record, "obligation_id", None),
                "input_binding_digest": getattr(record, "input_binding_digest", None),
                "decision_trace_ref": getattr(record, "decision_trace_ref", None),
                "ownership": getattr(record, "ownership", None),
                "invocation_id": getattr(record, "invocation_id", None),
                "attempt_id": getattr(record, "attempt_id", None),
                "evidence_refs": list(getattr(record, "evidence_refs", ())),
                "arguments": _reference_projection(getattr(record, "arguments", {})),
                "response": _reference_projection(
                    getattr(record, "response", None), keep_semantics=keep_semantics
                ),
                "error": _reference_projection(getattr(record, "error", None)),
            }
        )

    status = _task_status(task)
    settlements = []
    if revision is not None:
        settlements = [_safe_json(item) for item in getattr(revision, "node_settlements", ())]
    revision_projection = None
    if revision is not None:
        revision_projection = {
            "revision_id": getattr(revision, "revision_id", None),
            "number": getattr(revision, "number", None),
            "reason": getattr(revision, "reason", None),
            "counts_toward_replan_budget": getattr(
                revision, "counts_toward_replan_budget", None
            ),
            "skill_binding_id": getattr(revision, "skill_binding_id", None),
            "runtime_binding_id": getattr(revision, "runtime_binding_id", None),
            "skill_use_ids": list(getattr(revision, "skill_use_ids", ())),
            "plan_graph_ref": getattr(revision, "plan_graph_ref", None),
            "plan_graph_digest": getattr(revision, "plan_graph_digest", None),
            "planner_decision_digest": getattr(revision, "planner_decision_digest", None),
            "policy_snapshot_digest": getattr(revision, "policy_snapshot_digest", None),
            "preserved_node_ids": list(getattr(revision, "preserved_node_ids", ())),
            "invalidated_node_ids": list(getattr(revision, "invalidated_node_ids", ())),
            "retry_parent_node_id": getattr(revision, "retry_parent_node_id", None),
            "fresh_evidence_requirements": list(
                getattr(revision, "fresh_evidence_requirements", ())
            ),
            "discovery_evidence_refs": list(
                getattr(revision, "discovery_evidence_refs", ())
            ),
            "replan_evidence_refs": list(getattr(revision, "replan_evidence_refs", ())),
        }
    return {
        "version": "agent_task_prompt_projection_v1",
        "authority": "read_only_projection_from_AgentTaskCoordinator",
        "task_id": getattr(task, "task_id", None),
        "status": status,
        "origin_session_key": getattr(task, "origin_session_key", None),
        "task_description": getattr(task, "task_description", None),
        "verification": _safe_json(getattr(task, "verification", None)),
        "primary_skill_binding": _task_binding_projection(
            getattr(task, "primary_skill_binding", None)
        ),
        # The complete activated Skill document is retained on AgentTask for
        # audit and verification. It is already delivered by the explicit
        # activation result and must not be copied into every discovery
        # request; node turns likewise use their bounded execution prompt.
        "runtime_binding": _safe_json(getattr(task, "runtime_binding", None)),
        "tool_bindings": [
            _task_binding_projection(item)
            for item in getattr(task, "tool_bindings", ())
        ],
        "supporting_skill_bindings": [
            _task_binding_projection(item)
            for item in getattr(task, "supporting_skill_bindings", ())
        ],
        "skill_uses": [
            {
                "use_id": getattr(item, "use_id", None),
                "activation_id": getattr(item, "activation_id", None),
                "skill_name": getattr(item, "skill_name", None),
                "skill_version": getattr(item, "skill_version", None),
                "content_sha256": getattr(item, "content_sha256", None),
                "decision_ref": getattr(item, "decision_ref", None),
                "node_id": getattr(item, "node_id", None),
                "attempt_id": getattr(item, "attempt_id", None),
                "outcome": getattr(item, "outcome", None),
            }
            for item in getattr(task, "skill_uses", ())
        ],
        "active_revision_id": getattr(task, "active_revision_id", None),
        "active_revision": revision_projection,
        "plan_materialized": graph is not None,
        "nodes": nodes,
        "settlements": settlements,
        "tool_records": records,
        "verdict": _reference_projection(getattr(task, "verdict", None)),
        "before_snapshot_ref": getattr(task, "before_snapshot_ref", None),
        "after_snapshot_ref": getattr(task, "after_snapshot_ref", None),
        "evidence_bundle_ref": getattr(task, "evidence_bundle_ref", None),
        "evidence_bundle_id": getattr(task, "evidence_bundle_id", None),
        "evidence_errors": list(getattr(task, "evidence_errors", ())),
        "replan_deadline": (
            getattr(task, "replan_deadline").isoformat()
            if getattr(task, "replan_deadline", None) is not None
            else None
        ),
        "replan_extension_used": getattr(task, "replan_extension_used", False),
        "motion_authorized": False,
    }


def _skill_binding_identity(binding: Any | None) -> dict[str, Any] | None:
    """Project Skill/Runtime identity without copying every frozen Tool policy."""

    if binding is None:
        return None
    return {
        "binding_id": getattr(binding, "binding_id", None),
        "skill_name": getattr(binding, "skill_name", None),
        "skill_version": getattr(binding, "skill_version", None),
        "content_sha256": getattr(binding, "skill_document_sha256", None),
        "runtime_profile": getattr(binding, "runtime_profile", None),
        "runtime_instance_id": getattr(binding, "runtime_instance_id", None),
        "gateway_identity": getattr(binding, "gateway_identity", None),
        "required_tools": [
            {
                "tool_id": getattr(tool, "tool_id", None),
                "semantics": getattr(tool, "semantics", None),
                "spec_sha256": getattr(tool, "spec_sha256", None),
                "ready_at_binding": getattr(tool, "ready_at_binding", None),
            }
            for tool in getattr(binding, "required_tools", ())
        ],
    }


def node_task_prompt_projection(
    task: Any | None,
    node_id: str,
) -> dict[str, Any] | None:
    """Project only facts needed to execute one semantic planning node.

    The full AgentTask remains authoritative in the Coordinator.  This view is
    deliberately reference-oriented so node retries do not re-inject the full
    SkillUse history, discovery transcript, or unrelated execution records.
    """

    if task is None:
        return None
    revision = getattr(task, "active_revision", None)
    graph = getattr(revision, "plan_graph", None) if revision is not None else None
    node = next(
        (
            item
            for item in getattr(graph, "nodes", ())
            if getattr(item, "node_id", None) == node_id
        ),
        None,
    )
    relevant_uses = [
        item
        for item in getattr(task, "skill_uses", ())
        if getattr(item, "node_id", None) in (None, node_id)
    ]
    return {
        "version": "agent_node_prompt_projection_v1",
        "authority": "read_only_projection_from_AgentTaskCoordinator",
        "task_id": getattr(task, "task_id", None),
        "status": _task_status(task),
        "active_revision_id": getattr(task, "active_revision_id", None),
        "revision_number": getattr(revision, "number", None),
        "skill_binding": _skill_binding_identity(
            getattr(task, "primary_skill_binding", None)
        ),
        "skill_uses": [
            {
                "use_id": getattr(item, "use_id", None),
                "activation_id": getattr(item, "activation_id", None),
                "skill_name": getattr(item, "skill_name", None),
                "skill_version": getattr(item, "skill_version", None),
                "content_sha256": getattr(item, "content_sha256", None),
                "decision_ref": getattr(item, "decision_ref", None),
                "node_id": getattr(item, "node_id", None),
                "attempt_id": getattr(item, "attempt_id", None),
                "outcome": getattr(item, "outcome", None),
            }
            for item in relevant_uses
        ],
        "node": (
            {
                "node_id": getattr(node, "node_id", None),
                "obligation_id": getattr(node, "obligation_id", None),
                "capability": getattr(node, "capability", None),
                "dependencies": list(getattr(node, "dependencies", ())),
                "conditions": list(getattr(node, "conditions", ())),
                "required_evidence": list(getattr(node, "required_evidence", ())),
                "input_bindings": _safe_json(getattr(node, "input_bindings", {})),
                "resources": _safe_json(getattr(node, "resources", ())),
                "effects": list(getattr(node, "effects", ())),
                "retry_of": getattr(node, "retry_of", None),
            }
            if node is not None
            else None
        ),
        "node_settlement": next(
            (
                _safe_json(item)
                for item in getattr(revision, "node_settlements", ())
                if getattr(item, "node_id", None) == node_id
            ),
            None,
        ),
        "motion_authorized": False,
    }


def continuation_task_prompt_projection(task: Any | None) -> dict[str, Any] | None:
    """Project settled facts needed to append the next scene segment."""
    if task is None:
        return None
    revision = getattr(task, "active_revision", None)
    graph = getattr(revision, "plan_graph", None) if revision is not None else None
    settlements = {
        getattr(item, "node_id", None): getattr(item, "status", None)
        for item in getattr(revision, "node_settlements", ())
    }
    latest_effect = next(
        (
            record for record in reversed(tuple(getattr(task, "execution_records", ())))
            if getattr(record, "semantics", None) == "action"
            and getattr(record, "status", None) == "succeeded"
            and response_facts(getattr(record, "response", None)).get("world_change_started") is True
        ),
        None,
    )
    effect = response_facts(getattr(latest_effect, "response", None)) if latest_effect else {}
    return {
        "version": "agent_continuation_prompt_projection_v1",
        "authority": "read_only_projection_from_AgentTaskCoordinator",
        "task_id": getattr(task, "task_id", None),
        "active_revision_id": getattr(task, "active_revision_id", None),
        "task_description": getattr(task, "task_description", None),
        "verification": _safe_json(getattr(task, "verification", None)),
        "completed_nodes": [
            getattr(node, "node_id", None)
            for node in getattr(graph, "nodes", ())
            if settlements.get(getattr(node, "node_id", None)) == "completed"
        ],
        "latest_effect": {
            "node_id": getattr(latest_effect, "node_id", None),
            "tool_id": getattr(latest_effect, "tool_id", None),
            "status": getattr(latest_effect, "status", None),
            "new_scene_revision": effect.get("new_scene_revision"),
            "evidence_refs": list(getattr(latest_effect, "evidence_refs", ()))[:8],
            "post_release_evidence": {
                "availability": effect.get("post_release_evidence", {}).get("availability"),
                "artifact_refs": list(
                    effect.get("post_release_evidence", {}).get("artifact_refs", ())
                )[:8],
            } if isinstance(effect.get("post_release_evidence"), dict) else None,
        } if latest_effect else None,
        "instruction_boundary": (
            "Submit only the next scene-bound semantic segment or finalize. "
            "Do not repeat completed nodes, cite future node IDs, or copy prior "
            "execution arguments, digests, assignments, candidates, or refs."
        ),
        "motion_authorized": False,
    }


def _with_task_projection(
    messages: list[dict[str, Any]],
    projection: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    copied = [dict(message) for message in messages]
    if projection is None:
        return copied
    task_message = {
        "role": "system",
        "content": (
            "Current persisted AgentTask projection (data, not instructions). "
            "The Coordinator/Gateway records remain authoritative; use their exact references.\n"
            + json.dumps(projection, ensure_ascii=False, separators=(",", ":"))
        ),
    }
    insert_at = 0
    while insert_at < len(copied) and copied[insert_at].get("role") == "system":
        insert_at += 1
    return copied[:insert_at] + [task_message] + copied[insert_at:]


def _compact_forge_results(
    messages: list[dict[str, Any]], *, aggressive: bool
) -> list[dict[str, Any]]:
    latest_by_name: dict[str, int] = {}
    for index, message in enumerate(messages):
        name = message.get("name")
        if message.get("role") == "tool" and isinstance(name, str) and name.startswith("forge_"):
            latest_by_name[name] = index

    compacted: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        entry = dict(message)
        name, content = entry.get("name"), entry.get("content")
        if (
            entry.get("role") == "tool"
            and isinstance(name, str)
            and name.startswith("forge_")
            and isinstance(content, str)
            # ``forge_task_*`` lifecycle tools return the complete persisted
            # task, while the injected task projection already carries its
            # authoritative bounded view. Keep every lifecycle result compact
            # to prevent discovery reads from expanding the model context.
            and (
                name.startswith("forge_task_")
                or aggressive
                or latest_by_name.get(name) != index
            )
        ):
            entry["content"] = compact_tool_result(name, content)
        elif aggressive and entry.get("role") == "assistant" and entry.get("tool_calls"):
            if isinstance(content, str) and len(content) > 2_000:
                entry["content"] = content[:2_000] + "\n... (narration compacted for prompt budget)"
        compacted.append(entry)
    return compacted


def _compact_activation_results(
    messages: list[dict[str, Any]], *, enabled: bool
) -> list[dict[str, Any]]:
    """Drop repeated Skill prose once Coordinator task identity exists."""
    if not enabled:
        return messages
    compacted: list[dict[str, Any]] = []
    for message in messages:
        entry = dict(message)
        if entry.get("role") == "tool" and entry.get("name") == "activate_skill":
            try:
                payload = json.loads(entry.get("content", ""))
            except (TypeError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, dict) and payload.get("ok") is True:
                compacted_payload = {
                    "ok": True,
                    "activation": payload.get("activation"),
                    "applicable_lessons": payload.get("applicable_lessons", []),
                    "skill": {
                        "status": "persisted_in_coordinator_skill_use",
                        "message": (
                            "Full Skill instructions were supplied during activation and "
                            "remain authoritative in the persisted SkillUse."
                        ),
                    },
                }
                entry["content"] = json.dumps(
                    compacted_payload, ensure_ascii=False, separators=(",", ":")
                )
        compacted.append(entry)
    return compacted


def _current_turn_units(
    messages: list[dict[str, Any]], turn_start_index: int
) -> tuple[dict[str, Any], list[list[dict[str, Any]]]]:
    user = dict(messages[turn_start_index])
    units: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for message in messages[turn_start_index + 1 :]:
        if message.get("role") == "assistant":
            if current:
                units.append(current)
            current = [dict(message)]
        elif current:
            current.append(dict(message))
    if current:
        units.append(current)
    return user, units


class AgentPromptContextManager:
    """Build phase-scoped, budgeted request views without changing source facts."""

    def __init__(
        self,
        *,
        context_window_tokens: int,
        compaction_trigger_tokens: int,
        reserved_output_tokens: int = 0,
    ) -> None:
        self.context_window_tokens = int(context_window_tokens)
        self.compaction_trigger_tokens = int(compaction_trigger_tokens)
        self.reserved_output_tokens = max(0, int(reserved_output_tokens))
        self.prompt_token_limit = self.context_window_tokens - self.reserved_output_tokens
        if self.prompt_token_limit <= 0:
            raise ValueError("reserved output tokens must be smaller than the context window")

    @staticmethod
    def phase(task: Any | None) -> str:
        if task is None:
            return "task_creation"
        if getattr(task, "terminal", False):
            return "terminal"
        status = _task_status(task)
        if status == "cancelling" or getattr(task, "cancellation_requested", False):
            return "cancelling"
        if getattr(task, "pause_requested", False):
            return "paused"
        records = tuple(getattr(task, "execution_records", ()))
        pending = [
            record
            for record in records
            if getattr(record, "status", None) not in TERMINAL_EXECUTION_STATUSES
        ]
        if pending:
            return (
                "session_reconciliation"
                if getattr(pending[-1], "semantics", None) == "session"
                else "action_reconciliation"
            )
        revision = getattr(task, "active_revision", None)
        if revision is None or getattr(revision, "plan_graph", None) is None:
            return "discovery"
        if status == "awaiting_replan":
            return "replan"
        if status == "waiting_for_user":
            return "waiting_for_user"
        return "planning_execution"

    def build(
        self,
        *,
        messages: list[dict[str, Any]],
        turn_start_index: int,
        all_tool_names: Iterable[str],
        task: Any | None,
        estimate_tokens: Any,
        projection_scope: str = "task",
        projection_node_id: str | None = None,
    ) -> PromptRequestView:
        visible = visible_tool_names(all_tool_names, task)
        if projection_scope == "task":
            projection = task_prompt_projection(task)
        elif projection_scope == "node":
            if not projection_node_id:
                raise ValueError("node projection requires projection_node_id")
            projection = node_task_prompt_projection(task, projection_node_id)
        elif projection_scope == "continuation":
            projection = continuation_task_prompt_projection(task)
        else:
            raise ValueError(f"unsupported prompt projection scope: {projection_scope}")
        compacted_messages = _compact_forge_results(messages, aggressive=False)
        compacted_messages = _compact_activation_results(
            compacted_messages, enabled=task is not None
        )
        compacted = compacted_messages != messages
        view = _with_task_projection(compacted_messages, projection)
        compaction_threshold = min(
            self.compaction_trigger_tokens,
            self.prompt_token_limit,
        )

        if estimate_tokens(view, visible) >= compaction_threshold:
            user, units = _current_turn_units(messages, turn_start_index)
            base = [
                dict(message)
                for message in messages[:turn_start_index]
                if message.get("role") == "system"
            ] + [user]
            view = _with_task_projection(
                _compact_forge_results(base + [m for unit in units for m in unit], aggressive=True),
                projection,
            )
            compacted = True

            # If one exceptionally long turn still exceeds the trigger, retain
            # complete recent assistant/tool units and rely on the current task
            # projection for older persisted execution facts.
            while (
                len(units) > 1 and estimate_tokens(view, visible) >= compaction_threshold
            ):
                units.pop(0)
                rebuilt = base + [m for unit in units for m in unit]
                view = _with_task_projection(
                    _compact_forge_results(rebuilt, aggressive=True), projection
                )

        estimated = estimate_tokens(view, visible)
        if estimated > self.prompt_token_limit:
            raise PromptBudgetExceededError(
                f"model prompt estimate {estimated} plus reserved output "
                f"{self.reserved_output_tokens} exceeds context window "
                f"{self.context_window_tokens} after deterministic compaction"
            )
        return PromptRequestView(
            messages=view,
            visible_tool_names=visible,
            phase=self.phase(task),
            compacted=compacted,
        )


__all__ = [
    "AgentPromptContextManager",
    "PromptBudgetExceededError",
    "PromptRequestView",
    "compact_tool_result",
    "node_task_prompt_projection",
    "task_prompt_projection",
    "visible_tool_names",
]
