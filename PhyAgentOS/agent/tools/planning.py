"""Read-only AgentLoop tools for an active semantic planning dispatch."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.planning import AdmissionContext

_PLANNING_BINDING_FIELDS = (
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
        return "Select one ready semantic node and Tool; returns a PAOS-generated planning binding without invoking a Gateway."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "minLength": 1},
                "node_id": {"type": "string", "minLength": 1},
                "tool_id": {"type": "string", "minLength": 1},
                "arguments": {"type": "object"},
                "decision_reason": {"type": "string", "minLength": 1},
            },
            "required": ["task_id", "node_id", "tool_id", "arguments", "decision_reason"],
            "additionalProperties": False,
        }

    async def execute(self, task_id: str, node_id: str, tool_id: str, arguments: dict[str, Any], decision_reason: str) -> str:
        dispatch = self.dispatch_getter()
        if dispatch is None or dispatch.graph.task_id != task_id:
            return json.dumps({"ok": False, "error": {"type": "planning_selection", "message": "the requested task is not the active PlanGraph"}, "motion_authorized": False}, ensure_ascii=False, separators=(",", ":"))
        try:
            proposal = dispatch.prepare_selection(
                node_id=node_id, tool_id=tool_id, arguments=arguments,
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
                for field in ("task_id", "revision_id", "scene_revision")
                if field in receipt
            }
            return json.dumps(
                {
                    "ok": True,
                    "data": {"planning_binding": binding, "selection": selection},
                    "motion_authorized": False,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": {"type": "planning_selection", "message": str(exc)}, "motion_authorized": False}, ensure_ascii=False, separators=(",", ":"))


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
