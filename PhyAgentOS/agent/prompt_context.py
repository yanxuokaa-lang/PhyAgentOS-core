"""Bounded model-facing context projections for long Agent turns.

This module never mutates AgentTask, Gateway, or Session state.  It builds a
temporary request view from those owners immediately before each model call.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from PhyAgentOS.forge.binding import required_preplan_queries

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
    required = required_preplan_queries(task)
    if not required:
        return True
    revision = getattr(task, "active_revision", None)
    records = getattr(revision, "execution_records", ()) if revision is not None else ()
    completed = {
        getattr(record, "tool_id", None)
        for record in records
        if getattr(record, "status", None) == "succeeded"
    }
    return required.issubset(completed)
_PLANNING = {
    "forge_task_begin_revision",
    "forge_task_finalize",
    "forge_plan_activate",
    "forge_plan_ready",
    "forge_plan_select",
    "forge_tool_context",
    "forge_tool_query",
    "forge_tool_start_action",
    "forge_tool_start_session",
}
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
    "input_schema",
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


def compact_tool_result(tool_name: str, content: str) -> str:
    """Create a deterministic non-authoritative prompt summary of a Tool result."""

    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return content
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
        "primary_skill_binding": _safe_json(getattr(task, "primary_skill_binding", None)),
        "primary_skill_instructions": getattr(task, "primary_skill_instructions", None),
        "runtime_binding": _safe_json(getattr(task, "runtime_binding", None)),
        "tool_bindings": _safe_json(getattr(task, "tool_bindings", ())),
        "supporting_skill_bindings": _safe_json(
            getattr(task, "supporting_skill_bindings", ())
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
            and (aggressive or latest_by_name.get(name) != index)
        ):
            entry["content"] = compact_tool_result(name, content)
        elif aggressive and entry.get("role") == "assistant" and entry.get("tool_calls"):
            if isinstance(content, str) and len(content) > 2_000:
                entry["content"] = content[:2_000] + "\n... (narration compacted for prompt budget)"
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
    ) -> PromptRequestView:
        visible = visible_tool_names(all_tool_names, task)
        projection = task_prompt_projection(task)
        compacted_messages = _compact_forge_results(messages, aggressive=False)
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
    "task_prompt_projection",
    "visible_tool_names",
]
