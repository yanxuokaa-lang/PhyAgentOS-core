"""Agent tools for explicit PAOS AgentTask lifecycle management."""

from __future__ import annotations

import inspect
import json
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.forge.binding import missing_preplan_queries
from PhyAgentOS.forge.task import (
    AgentTaskBusyError,
    AgentTaskCoordinator,
    DiscoveryRequiredError,
    TaskNotReadyForFinalizationError,
)
from PhyAgentOS.planning import PlanGraph, PlanNode
from PhyAgentOS.verification.contracts import TaskVerificationContract, utc_now


def _json(value: Any) -> str:
    """Serialize tool responses, including Pydantic records nested in envelopes.

    Forge coordinator methods return rich ``AgentTaskRecord`` instances.  Tool
    responses wrap those records in a mapping (``{"ok": True, "data": ...}``),
    so converting only the top-level value leaves the record for ``json.dumps``
    and causes the CLI to fail after the state has already been persisted.
    """

    def safe(item: Any) -> Any:
        if hasattr(item, "model_dump"):
            return safe(item.model_dump(mode="json", exclude_none=True))
        if isinstance(item, Mapping):
            return {str(key): safe(child) for key, child in item.items()}
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            return [safe(child) for child in item]
        if isinstance(item, (set, frozenset)):
            return [safe(child) for child in item]
        if isinstance(item, Enum):
            return item.value
        return item

    return json.dumps(safe(value), ensure_ascii=False, separators=(",", ":"))


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
                    "description": "Optional primary activate_skill result; omit when using Runtime-only execution",
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
            "required": ["task_description", "verification"],
            "additionalProperties": False,
        }

    async def execute(
        self,
        task_description: str,
        verification: dict[str, Any],
        activation_id: str | None = None,
        plan_graph: dict[str, Any] | None = None,
        plan_graph_ref: str | None = None,
    ) -> str:
        if task_description.strip().casefold() in {"noop", "no-op", "none"}:
            raise ValueError("AgentTask description must state an executable user task")
        try:
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
        except AgentTaskBusyError as exc:
            return _json({
                "ok": False,
                "error": {
                    "code": exc.code,
                    "task_id": exc.task_id,
                    "owner_session_key": exc.owner_session_key,
                    "message": str(exc),
                    "action": (
                        "Continue the owner session or wait for it to reach a terminal state. "
                        "forge_task_get is read-only and does not transfer task ownership."
                    ),
                },
                "motion_authorized": False,
            })
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
            "replanning. Supply semantic nodes for a model-directed recovery; PAOS compiles "
            "revision IDs and integrity metadata. A complete plan_graph remains available "
            "for coordinator-owned callers. This call only changes the planning revision and "
            "never invokes a Tool or motion. retry_of may reference only a node included in "
            "this replacement graph; use reason and evidence refs for prior-revision history."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _task_id_schema()
        schema["properties"]["reason"] = {"type": "string", "minLength": 1}
        schema["properties"]["nodes"] = {
            "type": "array",
            "minItems": 1,
            "items": PlanNode.model_json_schema(),
            "description": (
                "Full replacement semantic node list. PAOS supplies revision and digest metadata."
            ),
        }
        schema["required"].extend(["reason", "nodes"])
        return schema

    async def execute(
        self,
        task_id: str,
        reason: str,
        plan_graph: dict[str, Any] | None = None,
        plan_graph_ref: str | None = None,
        nodes: list[dict[str, Any]] | None = None,
    ) -> str:
        if nodes is not None and plan_graph is not None:
            raise ValueError("supply either nodes or plan_graph")
        if nodes is None and plan_graph is None:
            raise ValueError("semantic recovery requires replacement nodes")
        attempt_started_at = utc_now()
        task = self.coordinator.get_task(task_id)
        if nodes is not None:
            from PhyAgentOS.agent.plan_proposal import compile_task_plan

            if plan_graph_ref is not None:
                raise ValueError("PAOS supplies the plan reference for semantic nodes")
            graph = compile_task_plan(task, nodes, reason=reason)
            plan_graph = graph.model_dump(mode="json")
            plan_graph_ref = f"artifact://plans/{task_id}/{graph.revision_id}"
        self.coordinator.claim_replan_attempt(
            task_id, attempt_started_at=attempt_started_at
        )
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
            "once evidence is sufficient, submit nodes here instead of narrating a future plan. "
            "Use paos_record.evidence_refs from task-bound Query responses directly; "
            "no extra task read is needed just to recover their IDs. If evidence is insufficient, "
            "obtain the missing facts or request clarification. PlanNode.conditions must be "
            "symbolic condition-fact keys, not prose; keep natural-language constraints in "
            "obligation/evidence/input_bindings. Root discovery nodes must leave "
            "produced_evidence empty because their opaque Tool refs do not exist until "
            "the terminal result; use exact paos_record.evidence_refs on later nodes. "
            "This call does not execute Tools or motion."
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
        from PhyAgentOS.agent.planning_context import (
            PlanningContextUnavailableError,
            context_from_task,
        )

        task = self.coordinator.get_task(task_id)
        try:
            context = context_from_task(task, allow_refresh=True)
        except PlanningContextUnavailableError:
            # A scene-free graph may be materialized before discovery, but it
            # cannot claim evidence that has not been persisted by Coordinator.
            context = None
        trusted_evidence = set(context.evidence_refs) if context is not None else set()
        if context is None and missing_preplan_queries(task):
            return _json({
                "ok": False,
                "error": {
                    "code": "discovery_required",
                    "reason": "complete task-bound discovery before materializing a discovery graph",
                },
                "motion_authorized": False,
            })
        requested_evidence = tuple(evidence_refs or ())
        fabricated = sorted(set(requested_evidence) - trusted_evidence)
        if fabricated:
            raise ValueError(
                "plan evidence_refs must be exact task-bound Coordinator references; "
                "unknown or fabricated refs: " + ", ".join(fabricated)
            )
        if nodes is not None:
            from PhyAgentOS.agent.plan_proposal import compile_task_plan
            if plan_graph_ref is not None:
                raise ValueError("PAOS supplies the plan reference for semantic nodes")
            selected_evidence = requested_evidence or tuple(sorted(trusted_evidence))
            graph = compile_task_plan(
                task,
                nodes,
                reason=reason,
                initial_evidence_refs=(
                    selected_evidence if context is not None else None
                ),
                initial_condition_facts=(
                    dict(context.condition_facts) if context is not None else {}
                ),
            )
            plan_graph_ref = f"artifact://plans/{task_id}/{graph.revision_id}"
        else:
            graph = PlanGraph.model_validate(plan_graph)
        try:
            materialized = self.coordinator.materialize_plan_revision(
                task_id,
                plan_graph=graph,
                plan_graph_ref=plan_graph_ref,
                evidence_refs=(
                    selected_evidence if nodes is not None else requested_evidence
                ),
                reason=reason,
            )
        except DiscoveryRequiredError as exc:
            if exc.code == "discovery_required":
                return _json({
                    "ok": False,
                    "error": {
                        "code": exc.code,
                        "reason": str(exc),
                        "missing": list(exc.missing),
                    },
                    "motion_authorized": False,
                })
            raise
        return _json({"ok": True, "data": materialized})


class ForgeTaskContinuePlanTool(Tool):
    """Append the next dynamic-scene segment after the active graph completed."""

    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_task_continue_plan"

    @property
    def description(self) -> str:
        return (
            "Append the next semantic PlanGraph segment after every node in the active graph "
            "completed. Use this normal forward path after post-action observation and binding; "
            "it preserves task identity, does not consume replan budget, invoke a Tool, or "
            "authorize motion. Submit only the next segment using current Coordinator evidence."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _task_id_schema()
        schema["properties"].update({
            "nodes": {
                "type": "array",
                "minItems": 1,
                "items": PlanNode.model_json_schema(),
                "description": "Next scene-bound segment; PAOS supplies revision metadata.",
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string", "minLength": 1},
        })
        schema["required"].extend(["nodes", "reason"])
        return schema

    async def execute(
        self,
        task_id: str,
        nodes: list[dict[str, Any]],
        reason: str,
        evidence_refs: list[str] | None = None,
    ) -> str:
        from PhyAgentOS.agent.plan_proposal import compile_task_plan
        from PhyAgentOS.agent.planning_context import context_from_task

        submitted_ids = {
            node.get("node_id") for node in nodes if isinstance(node, dict)
        }
        missing_dependencies = sorted({
            dependency
            for node in nodes if isinstance(node, dict)
            for dependency in node.get("dependencies", ())
            if dependency not in submitted_ids
        })
        if missing_dependencies:
            raise ValueError(
                "continuation dependencies must name nodes in this submitted segment; "
                "completed prior nodes are already settled, and future nodes need a later "
                "continuation: " + ", ".join(missing_dependencies)
            )
        task = self.coordinator.get_task(task_id)
        context = context_from_task(task, allow_refresh=True)
        trusted_evidence = set(context.evidence_refs)
        requested_evidence = tuple(evidence_refs or ())
        fabricated = sorted(set(requested_evidence) - trusted_evidence)
        if fabricated:
            raise ValueError(
                "continuation evidence_refs must be exact task-bound Coordinator references; "
                "unknown or fabricated refs: " + ", ".join(fabricated)
            )
        selected_evidence = requested_evidence or tuple(sorted(trusted_evidence))
        graph = compile_task_plan(
            task,
            nodes,
            reason=reason,
            initial_evidence_refs=selected_evidence,
            initial_condition_facts=dict(context.condition_facts),
        )
        continued = self.coordinator.begin_continuation_revision(
            task_id,
            reason=reason,
            plan_graph=graph,
            plan_graph_ref=f"artifact://plans/{task_id}/{graph.revision_id}",
            evidence_refs=selected_evidence,
        )
        return _json({"ok": True, "data": continued, "motion_authorized": False})

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
        try:
            result = await self.coordinator.finalize_task(task_id)
        except TaskNotReadyForFinalizationError as exc:
            if exc.code == "task_not_ready_for_finalization":
                return _json({
                    "ok": False,
                    "error": {
                        "code": exc.code,
                        "reason": exc.reason,
                        "message": str(exc),
                    },
                    "motion_authorized": False,
                })
            raise
        return _json({"ok": True, "data": result})


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
        ForgeTaskContinuePlanTool(coordinator),
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
    "ForgeTaskContinuePlanTool",
    "ForgeTaskCreateTool",
    "ForgeTaskFinalizeTool",
    "ForgeTaskGetTool",
    "ForgeTaskMaterializePlanTool",
    "build_forge_task_tools",
]
