"""Read-only AgentLoop tools for an active semantic planning dispatch."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch, PlanningDispatchError
from PhyAgentOS.agent.planning_loop import (
    NodeContextProvider,
    PlanningLoopError,
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

    def __init__(self, dispatch: AgentComposedDispatch) -> None:
        self.dispatch = dispatch

    @property
    def name(self) -> str:
        return "forge_plan_ready"

    @property
    def description(self) -> str:
        return (
            "Read the ready semantic nodes and frozen planning Tool candidates for the "
            "active agent-composed PlanGraph. This performs no execution or motion."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    async def execute(self) -> str:
        return json.dumps(self.dispatch.describe(), ensure_ascii=False, separators=(",", ":"))


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
            "binding plus the final Tool arguments without invoking a Gateway. Pass both "
            "unchanged to the selected Forge Tool wrapper."
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
                            "path": {
                                "type": "array",
                                "items": {"type": "string", "minLength": 1},
                                "minItems": 1,
                            },
                        },
                        "required": ["record_id", "path"],
                        "additionalProperties": False,
                    },
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
        try:
            final_arguments = arguments
            if argument_sources:
                try:
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
                except PlanningLoopError as exc:
                    raise PlanningDispatchError(
                        str(exc),
                        code="invalid_argument_source",
                        failure_owner="agent_arguments",
                        recommended_action=(
                            "select_a_catalogued_source_from_bounded_node_context"
                        ),
                    ) from exc
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
            if argument_sources:
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
