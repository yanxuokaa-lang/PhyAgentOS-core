"""Agent tools for explicit PAOS AgentTask lifecycle management."""

from __future__ import annotations

import inspect
import json
from typing import Any

from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.forge.task import AgentTaskCoordinator
from PhyAgentOS.planning import PlanGraph, PlanNode
from PhyAgentOS.verification.contracts import TaskVerificationContract


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", exclude_none=True)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class ForgeTaskCreateTool(Tool):
    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator
        self.session_key: str | None = None

    def set_context(self, session_key: str) -> None:
        self.session_key = session_key

    @property
    def name(self) -> str:
        return "forge_task_create"

    @property
    def description(self) -> str:
        return (
            "Create the single active AgentTask before a task-bound Forge Tool sequence. "
            "This records planning and verification context but does not execute the robot."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "minLength": 1},
                "activation_id": {
                    "type": "string",
                    "pattern": "^activation_[a-z0-9]+$",
                    "description": "Primary activate_skill result from this session turn",
                },
                "verification": _verification_schema(),
                "plan_graph": {
                    "type": "object",
                    "description": "Concrete Agent-composed semantic DAG for this revision.",
                },
                "plan_graph_ref": {
                    "type": "string",
                    "pattern": "^artifact://.+",
                    "description": "Immutable artifact reference for the concrete PlanGraph.",
                },
            },
            "required": ["task_description", "activation_id", "verification"],
            "additionalProperties": False,
        }

    async def execute(
        self,
        task_description: str,
        activation_id: str,
        verification: dict[str, Any],
        plan_graph: dict[str, Any] | None = None,
        plan_graph_ref: str | None = None,
    ) -> str:
        task = self.coordinator.create_task(
            task_description=task_description,
            activation_id=activation_id,
            verification=TaskVerificationContract.model_validate(verification),
            origin_session_key=self.session_key,
            plan_graph=(PlanGraph.model_validate(plan_graph) if plan_graph is not None else None),
            plan_graph_ref=plan_graph_ref,
        )
        if inspect.isawaitable(task):
            task = await task
        return _json({"ok": True, "data": task})


class ForgeTaskGetTool(Tool):
    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_task_get"

    @property
    def description(self) -> str:
        return "Read persisted AgentTask, PlanRevision, Tool execution, evidence and verdict state."

    @property
    def parameters(self) -> dict[str, Any]:
        return _task_id_schema()

    async def execute(self, task_id: str) -> str:
        return _json({"ok": True, "data": self.coordinator.get_task(task_id)})


class ForgeTaskBeginRevisionTool(Tool):
    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_task_begin_revision"

    @property
    def description(self) -> str:
        return (
            "Append a new immutable PlanRevision to the same task after verification requests "
            "replanning."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _task_id_schema()
        schema["properties"]["reason"] = {"type": "string", "minLength": 1}
        schema["properties"]["plan_graph"] = {
            "type": "object",
            "description": "Replacement concrete semantic DAG for the new revision.",
        }
        schema["properties"]["plan_graph_ref"] = {
            "type": "string",
            "pattern": "^artifact://.+",
        }
        schema["required"].append("reason")
        return schema

    async def execute(
        self,
        task_id: str,
        reason: str,
        plan_graph: dict[str, Any] | None = None,
        plan_graph_ref: str | None = None,
    ) -> str:
        return _json(
            {
                "ok": True,
                "data": self.coordinator.begin_revision(
                    task_id,
                    reason=reason,
                    plan_graph=(PlanGraph.model_validate(plan_graph) if plan_graph is not None else None),
                    plan_graph_ref=plan_graph_ref,
                ),
            }
        )


class ForgeTaskMaterializePlanTool(Tool):
    """Materialize an Agent-selected graph when the task started without one."""

    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_task_materialize_plan"

    @property
    def description(self) -> str:
        return (
            "Attach an Agent-selected semantic PlanGraph to an existing task. "
            "Choose observation/understanding Tools first only when the task needs them; "
            "this call does not execute Tools or motion."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _task_id_schema()
        schema["properties"].update({
            "plan_graph": {"type": "object", "description": "Task-conditioned semantic DAG."},
            "nodes": {"type": "array", "minItems": 1, "items": PlanNode.model_json_schema(),
                      "description": "Agent-selected semantic nodes. PAOS supplies graph IDs and integrity metadata."},
            "plan_graph_ref": {"type": "string", "pattern": "^artifact://.+"},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string", "minLength": 1},
        })
        schema["description"] = "Supply nodes, or a complete plan_graph with plan_graph_ref, but not both."
        return schema

    async def execute(
        self,
        task_id: str,
        plan_graph: dict[str, Any] | None = None,
        plan_graph_ref: str | None = None,
        evidence_refs: list[str] | None = None,
        reason: str = "Agent selected a task-conditioned semantic DAG",
        nodes: list[dict[str, Any]] | None = None,
    ) -> str:
        if (nodes is None) == (plan_graph is None):
            raise ValueError("supply either nodes or plan_graph")
        if nodes is not None:
            from PhyAgentOS.agent.plan_proposal import compile_task_plan

            if plan_graph_ref is not None:
                raise ValueError("PAOS supplies the plan reference for semantic nodes")
            graph = compile_task_plan(self.coordinator.get_task(task_id), nodes, reason=reason)
            plan_graph_ref = f"artifact://plans/{task_id}/{graph.revision_id}"
        else:
            graph = PlanGraph.model_validate(plan_graph)
        return _json({
            "ok": True,
            "data": self.coordinator.materialize_plan_revision(
                task_id,
                plan_graph=graph,
                plan_graph_ref=plan_graph_ref,
                evidence_refs=tuple(evidence_refs or ()),
                reason=reason,
            ),
        })

class ForgeTaskFinalizeTool(Tool):
    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_task_finalize"

    @property
    def description(self) -> str:
        return (
            "Finalize a task after every bound Action is terminal. PAOS aggregates Tool facts "
            "and judges the user-level verification contract."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return _task_id_schema()

    async def execute(self, task_id: str) -> str:
        return _json(
            {"ok": True, "data": await self.coordinator.finalize_task(task_id)}
        )


class ForgeTaskCancelTool(Tool):
    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_task_cancel"

    @property
    def description(self) -> str:
        return (
            "Request cancellation for every non-terminal Action bound to an AgentTask. "
            "Cancellation acceptance is not proof that motion stopped."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _task_id_schema()
        schema["properties"]["reason"] = {"type": "string", "minLength": 1}
        return schema

    async def execute(self, task_id: str, reason: str = "agent_requested") -> str:
        return _json(
            {
                "ok": True,
                "data": await self.coordinator.cancel_task(task_id, reason=reason),
            }
        )


class ForgeTaskClarificationTool(Tool):
    """Pause a task on a structured user question instead of plain text."""

    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_task_request_clarification"

    @property
    def description(self) -> str:
        return (
            "Pause an AgentTask while asking the user a required clarification. "
            "The task remains persisted and can resume after the user answers."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _task_id_schema()
        schema["properties"].update({
            "question": {"type": "string", "minLength": 1},
            "node_id": {"type": "string", "minLength": 1},
        })
        schema["required"] += ["question"]
        return schema

    async def execute(self, task_id: str, question: str, node_id: str | None = None) -> str:
        return _json({
            "ok": True,
            "data": self.coordinator.request_clarification(
                task_id,
                question=question,
                node_id=node_id,
            ),
        })


def build_forge_task_tools(coordinator: AgentTaskCoordinator) -> list[Tool]:
    return [
        ForgeTaskCreateTool(coordinator),
        ForgeTaskGetTool(coordinator),
        ForgeTaskBeginRevisionTool(coordinator),
        ForgeTaskMaterializePlanTool(coordinator),
        ForgeTaskFinalizeTool(coordinator),
        ForgeTaskCancelTool(coordinator),
        ForgeTaskClarificationTool(coordinator),
    ]


def _task_id_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"task_id": {"type": "string", "minLength": 1}},
        "required": ["task_id"],
        "additionalProperties": False,
    }


def _verification_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["off", "audit", "enforce", "recovery"],
            },
            "goal": {"type": "string"},
            "success_criteria": {"type": "array", "items": {"type": "string"}},
            "constraints": {"type": "array", "items": {"type": "string"}},
            "evidence_policy": {
                "type": "object",
                "properties": {
                    "profile": {"type": "string"},
                    "required_kinds": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "required_sources": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "minimum_association": {
                        "type": "string",
                        "enum": ["best_effort", "authoritative"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    }


__all__ = [
    "ForgeTaskBeginRevisionTool",
    "ForgeTaskCancelTool",
    "ForgeTaskClarificationTool",
    "ForgeTaskCreateTool",
    "ForgeTaskFinalizeTool",
    "ForgeTaskGetTool",
    "ForgeTaskMaterializePlanTool",
    "build_forge_task_tools",
]
