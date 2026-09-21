"""Read-only AgentLoop tools for an active semantic planning dispatch."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch, PlanningDispatchError
from PhyAgentOS.agent.planning_loop import (
    NodeContextProvider,
    PlanningLoopError,
    node_source_page,
    project_consumer_arguments,
    resolve_node_argument_sources,
)
from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.planning import AdmissionContext

_PLANNING_BINDING_FIELDS = (
    "revision_id",
    "node_id",
    "node_digest",
    "obligation_id",
    "input_binding_digest",
    "decision_trace_ref",
)

if TYPE_CHECKING:
    from PhyAgentOS.forge.task import AgentTaskCoordinator


class ForgePlanReadyTool(Tool):
    """Expose ready semantic nodes without executing a Tool or changing state."""

    def __init__(self, dispatch: AgentComposedDispatch, coordinator: "AgentTaskCoordinator | None" = None) -> None:
        self.dispatch = dispatch
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_plan_ready"

    @property
    def description(self) -> str:
        return (
            "Read the ready semantic nodes and frozen planning Tool candidates for the "
            "active agent-composed PlanGraph. Optionally browse a node's authorized source "
            "record by explicit source_path and page offset; arrays use integer indexes. "
            "This performs no execution or motion."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object", "additionalProperties": False,
            "properties": {
                "node_id": {"type": "string"},
                "source_record_id": {"type": "string"},
                "source_path": _path_schema(allow_empty=True),
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
        }

    async def execute(self, node_id: str | None = None, source_record_id: str | None = None,
                      source_path: list | None = None, offset: int = 0, limit: int = 20) -> str:
        if source_record_id is not None:
            try:
                if self.coordinator is None or not node_id:
                    raise PlanningLoopError("source browsing requires a node and Coordinator")
                task = self.coordinator.get_task(self.dispatch.graph.task_id)
                if task.active_revision_id != self.dispatch.graph.revision_id:
                    raise PlanningLoopError("source browsing requires the active revision")
                context = NodeContextProvider(lambda _: task).build(
                    task.task_id, node_id, scene_revision=self.dispatch.current_scene_revision,
                )
                page = node_source_page(context, source_record_id, source_path or [], offset=offset, limit=limit)
                return json.dumps({"ok": True, "source_page": page, "motion_authorized": False}, ensure_ascii=False)
            except PlanningLoopError as exc:
                return json.dumps({"ok": False, "error": {"code": "invalid_argument_source", "message": str(exc)}, "motion_authorized": False})
        return json.dumps(self.dispatch.describe(), ensure_ascii=False, separators=(",", ":"))


def _path_schema(*, allow_empty: bool = False) -> dict[str, Any]:
    return {
        "type": "array", "minItems": 0 if allow_empty else 1,
        "items": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "integer", "minimum": 0}]},
    }


def _merge_projection_compatible_sources(
    context: Any,
    *,
    literals: Mapping[str, Any],
    argument_sources: Mapping[str, Any] | None,
    projection_source: Mapping[str, Any] | None,
    projection_plan: Any,
) -> dict[str, Any]:
    """Normalize legacy top-level sources into one projection-owned input.

    Projection plans own the consumer shape.  A model may still include the
    older source map while transitioning between prompt/tool versions, but it
    is safe only when every mapping points at the same authorized record and a
    declared top-level projection field.  Nested consumer output and semantic
    identity remain projection-owned and therefore cannot be overridden.
    """

    if not isinstance(projection_source, Mapping):
        raise PlanningLoopError(
            "consumer projection requires projection_source with one understanding record"
        )
    source_record_id = projection_source.get("record_id")
    if not isinstance(source_record_id, str) or not source_record_id:
        raise PlanningLoopError("consumer projection source record_id must be non-empty")
    merged = dict(literals)
    if not argument_sources:
        return merged
    if not isinstance(argument_sources, Mapping):
        raise PlanningLoopError("consumer projection argument_sources must be an object")

    top_level_fields = set(getattr(projection_plan, "top_level_fields", ()))
    for argument_name, selector in argument_sources.items():
        if not isinstance(selector, Mapping):
            raise PlanningLoopError("consumer projection source selector must be an object")
        if selector.get("record_id") != source_record_id:
            raise PlanningLoopError(
                "projection_source and argument_sources must use the same authorized record"
            )
        target_path = selector.get("target_path", [argument_name])
        if (
            not isinstance(target_path, (list, tuple))
            or len(target_path) != 1
            or not isinstance(target_path[0], str)
            or target_path[0] not in top_level_fields
        ):
            raise PlanningLoopError(
                "projection consumer accepts only declared top-level source fields; "
                "do not source nested targets or entity identity"
            )

    resolved = resolve_node_argument_sources(context, {}, argument_sources)
    for field in top_level_fields:
        if field not in resolved:
            continue
        if field in merged and merged[field] != resolved[field]:
            raise PlanningLoopError(
                f"projection top-level field {field!r} conflicts with its authorized source"
            )
        merged[field] = resolved[field]
    return merged


class ForgePlanSelectTool(Tool):
    """Create a Coordinator-owned binding for one ready semantic node."""

    def __init__(self, coordinator: "AgentTaskCoordinator", dispatch_getter: Callable[[], AgentComposedDispatch | None]) -> None:
        self.coordinator = coordinator
        self.dispatch_getter = dispatch_getter

    @property
    def name(self) -> str:
        return "forge_plan_select"

    @property
    def description(self) -> str:
        return (
            "Select one ready semantic node and Tool; returns a PAOS-generated planning "
            "binding plus the final Tool arguments without invoking a Gateway. For a Tool "
            "with a declared argument projection, pass projection_source only; a legacy "
            "argument_sources map is accepted only for compatible top-level fields from "
            "that same record. Pass the returned binding and selection unchanged."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "minLength": 1},
                "node_id": {"type": "string", "minLength": 1},
                "tool_id": {"type": "string", "minLength": 1},
                "arguments": {"type": "object"},
                "argument_sources": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "record_id": {"type": "string", "minLength": 1},
                            "path": _path_schema(),
                            "target_path": {
                                **_path_schema(),
                                "description": "Destination fields/indexes, e.g. ['targets',0,'category']; omitted means the source map key is the literal top-level argument name. Do not use this for a ToolSpec projection consumer's nested output.",
                            },
                        },
                        "required": ["record_id", "path"],
                        "additionalProperties": False,
                    },
                },
                "projection_source": {
                    "type": "object",
                    "description": "For a ToolSpec projection, the one authorized understanding record. Do not manually source targets or geometry fields.",
                    "properties": {"record_id": {"type": "string", "minLength": 1}},
                    "required": ["record_id"],
                    "additionalProperties": False,
                },
                "decision_reason": {"type": "string", "minLength": 1},
            },
            "required": ["task_id", "node_id", "tool_id", "arguments", "decision_reason"],
            "additionalProperties": False,
        }

    async def execute(
        self,
        task_id: str,
        node_id: str,
        tool_id: str,
        arguments: dict[str, Any],
        decision_reason: str,
        argument_sources: dict[str, Any] | None = None,
        projection_source: dict[str, Any] | None = None,
    ) -> str:
        dispatch = self.dispatch_getter()
        if dispatch is None or dispatch.graph.task_id != task_id:
            error = PlanningDispatchError(
                "the requested task is not the active PlanGraph",
                code="inactive_plan_graph",
                failure_owner="agent_state",
                retryable_in_revision=False,
                recommended_action="activate_current_task_plan",
            ).as_dict()
            current = self._persist_rejection(task_id, None, node_id, tool_id, error)
            if current is not None:
                error["task_status"] = current.status.value
            return self._error_response(error)
        pending_loader = getattr(self.coordinator, "pending_planning_selection", None)
        pending = (
            pending_loader(
                task_id,
                node_id,
                scene_revision=dispatch.current_scene_revision,
            )
            if callable(pending_loader)
            else None
        )
        if pending is not None and pending.get("tool_id") == tool_id:
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "planning_binding": pending["planning_binding"],
                        "selection": {
                            "task_id": pending["task_id"],
                            "revision_id": pending["revision_id"],
                            "scene_revision": pending["scene_revision"],
                            "tool_id": pending["tool_id"],
                            "execution_tool": pending["execution_tool"],
                            "arguments": {},
                            "use_selected_arguments": True,
                        },
                        "resumed_selection": True,
                    },
                    "motion_authorized": False,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        try:
            final_arguments = arguments
            projection, projection_plan = dispatch.argument_projection(tool_id)
            if projection is not None:
                node = next(
                    item for item in dispatch.graph.nodes if item.node_id == node_id
                )
                bound_entity = node.input_bindings.get("entity_ref")
                if isinstance(bound_entity, str):
                    supplied_entity = final_arguments.get("entity_ref")
                    if supplied_entity is not None and supplied_entity != bound_entity:
                        raise PlanningDispatchError(
                            "projection entity_ref conflicts with the Coordinator-owned node binding",
                            code="semantic_binding_mismatch",
                            failure_owner="agent_arguments",
                            retryable_in_revision=False,
                            requires_replan=True,
                            missing_fields=("entity_ref",),
                            recommended_action="use_the_exact_node_entity_ref",
                        )
                    # The Coordinator-owned binding is the only source of
                    # identity for a uniquely scene-bound projection node.
                    final_arguments = {**final_arguments, "entity_ref": bound_entity}
                try:
                    task = self.coordinator.get_task(task_id)
                    context = NodeContextProvider(lambda _task_id: task).build(
                        task_id,
                        node_id,
                        scene_revision=dispatch.current_scene_revision,
                    )
                    final_arguments = _merge_projection_compatible_sources(
                        context,
                        literals=final_arguments,
                        argument_sources=argument_sources,
                        projection_source=projection_source,
                        projection_plan=projection_plan,
                    )
                    final_arguments = project_consumer_arguments(
                        context,
                        projection=projection,
                        projection_plan=projection_plan,
                        literals=final_arguments,
                        source_record_id=(
                            projection_source.get("record_id")
                            if isinstance(projection_source, dict)
                            else None
                        ),
                    )
                except PlanningLoopError as exc:
                    raise PlanningDispatchError(
                        str(exc),
                        code="consumer_projection_invalid",
                        failure_owner="agent_arguments",
                        retryable_in_revision=False,
                        requires_replan=True,
                        recommended_action="use_one_understanding_record_for_projection_and_top_level_fields",
                    ) from exc
            else:
                if projection_source:
                    raise PlanningDispatchError(
                        "projection_source was supplied for a Tool without a declared projection",
                        code="consumer_projection_invalid",
                        failure_owner="agent_arguments",
                        retryable_in_revision=False,
                        requires_replan=True,
                        recommended_action="use_argument_sources_for_this_consumer",
                    )
                if argument_sources:
                    task = self.coordinator.get_task(task_id)
                    context = NodeContextProvider(lambda _task_id: task).build(
                        task_id,
                        node_id,
                        scene_revision=dispatch.current_scene_revision,
                    )
                    final_arguments = resolve_node_argument_sources(
                        context,
                        arguments,
                        argument_sources,
                    )
            proposal = dispatch.prepare_selection(
                node_id=node_id, tool_id=tool_id, arguments=final_arguments,
                decision_reason=decision_reason,
            )
            receipt = self.coordinator.persist_planning_selection(proposal)
            binding = {
                field: receipt[field]
                for field in _PLANNING_BINDING_FIELDS
                if field in receipt
            }
            missing = sorted(set(_PLANNING_BINDING_FIELDS) - set(binding))
            if missing:
                raise ValueError(
                    "Coordinator selection receipt omitted planning binding fields: "
                    + ", ".join(missing)
                )
            selection = {
                field: receipt[field]
                for field in ("task_id", "revision_id", "scene_revision", "tool_arguments")
                if field in receipt
            }
            if argument_sources or projection_source:
                selection["tool_arguments"] = {}
                selection["use_selected_arguments"] = True
            return json.dumps(
                {
                    "ok": True,
                    "data": {"planning_binding": binding, "selection": selection},
                    "motion_authorized": False,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except PlanningDispatchError as exc:
            error = exc.as_dict()
            current = self._persist_rejection(
                task_id, dispatch.graph.revision_id, node_id, tool_id, error
            )
            if current is not None:
                error["task_status"] = current.status.value
                if current.status.value == "failed":
                    error["recommended_action"] = "inspect_task_and_create_new_task_if_appropriate"
            return self._error_response(error)
        except Exception as exc:
            error = PlanningDispatchError(
                str(exc),
                code="planning_selection_internal_error",
                failure_owner="coordinator",
                retryable_in_revision=False,
                recommended_action="read_authoritative_task_state",
            ).as_dict()
            current = self._persist_rejection(
                task_id, dispatch.graph.revision_id, node_id, tool_id, error
            )
            if current is not None:
                error["task_status"] = current.status.value
            return self._error_response(error)

    def _persist_rejection(
        self,
        task_id: str,
        revision_id: str | None,
        node_id: str,
        tool_id: str,
        error: dict[str, Any],
    ) -> Any | None:
        try:
            current = self.coordinator.record_planning_selection_rejection(
                task_id,
                revision_id=revision_id,
                node_id=node_id,
                tool_id=tool_id,
                error=error,
            )
            error["rejection_persisted"] = True
            return current
        except Exception as exc:
            error["rejection_persisted"] = False
            error["persistence_error"] = {
                "type": type(exc).__name__,
                "code": "planning_selection_rejection_not_persisted",
                "failure_owner": "coordinator",
                "message": str(exc) or type(exc).__name__,
                "recommended_action": "read_authoritative_task_state",
            }
            return None

    @staticmethod
    def _error_response(error: dict[str, Any]) -> str:
        return json.dumps(
            {"ok": False, "error": error, "motion_authorized": False},
            ensure_ascii=False,
            separators=(",", ":"),
        )


class ForgePlanActivateTool(Tool):
    """Attach a task's frozen graph to the AgentLoop admission bridge."""

    def __init__(
        self,
        coordinator: "AgentTaskCoordinator",
        setter: Callable[[AgentComposedDispatch | None], None],
        context_provider: Callable[[str], AdmissionContext] | None,
    ) -> None:
        self.coordinator = coordinator
        self.setter = setter
        self.context_provider = context_provider

    @property
    def name(self) -> str:
        return "forge_plan_activate"

    @property
    def description(self) -> str:
        return "Activate the current AgentTask PlanGraph using trusted runtime context for read-only ready-node and Tool admission checks."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "minLength": 1},
            },
            "required": ["task_id"],
            "additionalProperties": False,
        }

    async def execute(
        self,
        task_id: str,
    ) -> str:
        try:
            if self.context_provider is None:
                raise RuntimeError("trusted planning context provider is not configured")
            task = self.coordinator.get_task(task_id)
            dispatch = AgentComposedDispatch.from_task(
                task,
                context_provider=self.context_provider,
            )
            self.setter(dispatch)
            return json.dumps(dispatch.describe(), ensure_ascii=False, separators=(",", ":"))
        except Exception as exc:
            # Never leave a previous task's admission context active after a
            # failed activation attempt.
            self.setter(None)
            return json.dumps(
                {"ok": False, "error": {"type": "planning_activation", "message": str(exc)}, "motion_authorized": False},
                ensure_ascii=False,
                separators=(",", ":"),
            )


__all__ = ["ForgePlanActivateTool", "ForgePlanReadyTool", "ForgePlanSelectTool"]
