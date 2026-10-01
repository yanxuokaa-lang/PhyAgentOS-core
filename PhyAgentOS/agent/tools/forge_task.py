"""Agent tools for explicit PAOS AgentTask lifecycle management."""

from __future__ import annotations

import inspect
import json
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

from PhyAgentOS.agent.plan_proposal import RECOVERY_NODE_GUIDANCE
from PhyAgentOS.agent.planning_facts import explicit_scene_revision, response_facts
from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.forge.binding import (
    missing_preplan_queries,
    query_record_status,
    query_response_facts,
)
from PhyAgentOS.forge.task import (
    AgentCancellationEvidenceError,
    AgentTaskBusyError,
    AgentTaskCoordinator,
    DiscoveryRequiredError,
    TaskNotReadyForFinalizationError,
)
from PhyAgentOS.planning import PlanGraph, PlanNode
from PhyAgentOS.verification.contracts import TaskVerificationContract, utc_now

_DISCOVERY_ARGUMENT_KEYS = frozenset({
    "sensor_ref", "sensor_refs", "requested_frame", "max_age_ms",
    "max_capture_skew_ms", "observation_ref", "scene_revision",
    "calibration_ref", "frame_id", "entity_refs", "artifacts", "views",
    "freshness_ms", "capture_skew_ms",
})


def _read_only_query_motion_flag_is_not_blocker(task: Any) -> bool:
    """Reject the false-blocker transition seen after complete discovery."""
    revision = getattr(task, "active_revision", None)
    if revision is None or getattr(revision, "plan_graph", None) is not None:
        return False
    if missing_preplan_queries(task):
        return False
    records = tuple(getattr(revision, "execution_records", ()))
    return any(
        getattr(record, "semantics", None) == "query"
        and query_record_status(record) == "succeeded"
        and query_response_facts(record).get("status") == "available"
        and query_response_facts(record).get("motion_authorized") is False
        for record in records
    )


def _successful_discovery_record(record: Any) -> bool:
    return (
        getattr(record, "semantics", None) == "query"
        and query_record_status(record) == "succeeded"
    )


def _same_discovery_input(node: PlanNode, record: Any) -> bool:
    """Compare stable Query inputs and ignore natural-language constraints."""
    bindings = node.input_bindings
    arguments = getattr(record, "arguments", {})
    if not isinstance(arguments, Mapping):
        return False
    compared = False
    for key in _DISCOVERY_ARGUMENT_KEYS:
        if key not in bindings:
            continue
        compared = True
        if key not in arguments or bindings[key] != arguments[key]:
            return False
    # An unbound observation node must not consume an arbitrary capture.
    return compared or node.capability != "scene.observe"


def _discovery_node_matches(node: PlanNode, task: Any, records: tuple[Any, ...]) -> bool:
    """Return whether a semantic Query node is already settled in this revision."""
    binding = getattr(task, "primary_skill_binding", None)
    tools = (
        getattr(binding, "required_tools", ())
        if binding is not None
        else getattr(task, "tool_bindings", ())
    )
    tool = next((item for item in tools if item.tool_id == node.capability), None)
    if tool is None or tool.semantics != "query":
        return False
    candidates = tuple(
        record for record in records
        if getattr(record, "tool_id", None) == node.capability
        and getattr(record, "ownership", "task") == "task"
        and _successful_discovery_record(record)
        and _same_discovery_input(node, record)
    )
    if not candidates:
        return False
    required = set(node.required_evidence)
    if required:
        available = {
            reference
            for record in records
            if getattr(record, "ownership", "task") == "task"
            for reference in getattr(record, "evidence_refs", ())
        }
        return required.issubset(available)
    return node.capability == "scene.observe"


def _prune_satisfied_discovery_prefix(
    task: Any, nodes: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """Drop only a settled leading Query prefix and rewire retained dependencies."""
    revision = getattr(task, "active_revision", None)
    if revision is None or getattr(revision, "plan_graph", None) is not None:
        return nodes, ()
    records = tuple(getattr(revision, "execution_records", ()))
    if not records:
        return nodes, ()
    parsed = [PlanNode.model_validate(node) for node in nodes]
    pruned: list[str] = []
    for node in parsed:
        if not _discovery_node_matches(node, task, records):
            break
        pruned.append(node.node_id)
    if not pruned:
        return nodes, ()
    removed = set(pruned)
    retained = []
    for node in parsed[len(pruned):]:
        value = node.model_dump(mode="json")
        value["dependencies"] = [
            dependency for dependency in value["dependencies"] if dependency not in removed
        ]
        retained.append(value)
    return retained, tuple(pruned)


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
            "This records planning and verification context but does not execute the robot. "
            "Set verification.mode explicitly; requested verification needs enforce, goal "
            "and success_criteria."
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
        if "mode" not in verification:
            raise ValueError(
                "verification.mode must be explicit: use enforce with goal and "
                "success_criteria when the user requests verification; use off only "
                "when verification is intentionally disabled"
            )
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


class ForgeTaskRebindRuntimeTool(Tool):
    """Explicitly migrate one durable task after its frozen Runtime is gone."""

    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_task_rebind_runtime"

    @property
    def description(self) -> str:
        return (
            "Use only after the user explicitly authorizes continuing the same AgentTask on a "
            "replacement Runtime. Activate the current primary Skill first and supply its "
            "activation_id. The Coordinator rejects terminal tasks and unsettled Actions/Sessions, "
            "preserves the prior binding and revisions, and opens a fresh-discovery revision. "
            "This operation never invokes a Runtime Tool or motion."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _task_id_schema()
        schema["properties"].update(
            {
                "activation_id": {"type": "string", "minLength": 1},
                "clarification_id": {"type": "string", "minLength": 1},
                "reason": {"type": "string", "minLength": 1},
            }
        )
        schema["required"].extend(["activation_id", "clarification_id", "reason"])
        return schema

    async def execute(
        self,
        task_id: str,
        activation_id: str,
        clarification_id: str,
        reason: str,
    ) -> str:
        return _json(
            {
                "ok": True,
                "data": await self.coordinator.rebind_active_runtime(
                    task_id,
                    activation_id=activation_id,
                    clarification_id=clarification_id,
                    reason=reason,
                ),
            }
        )


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
            "never invokes a Tool or motion. " + RECOVERY_NODE_GUIDANCE
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
        schema["properties"]["discovery_evidence_refs"] = {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": (
                "Optional replacement for the prior revision's discovery evidence refs. "
                "Use exact persisted evidence refs from the current scene when recovering "
                "after a world change; omit to preserve the prior revision's refs."
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
        discovery_evidence_refs: list[str] | None = None,
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
                    discovery_evidence_refs=(
                        tuple(discovery_evidence_refs)
                        if discovery_evidence_refs is not None
                        else None
                    ),
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
            "The active task identity, Skill binding, and this Tool's availability are "
            "Coordinator facts; do not restart task creation or reread the installed Skill to "
            "reconstruct them. "
            "Use paos_record.evidence_refs from task-bound Query responses directly; "
            "no extra task read is needed just to recover their IDs. If evidence is insufficient, "
            "obtain the missing facts or request clarification. PlanNode.conditions must be "
            "Runtime-published condition-fact keys, not prose or predecessor effects. "
            "When task-owned discovery Queries already succeeded in the active revision, PAOS "
            "conservatively prunes a matching leading Query prefix and continues the submitted "
            "suffix; it never replays those Queries or synthesizes their settlements. "
            "Use dependencies for predecessor completion; effects never become facts. "
            "Keep natural-language constraints in "
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
        pruned_discovery_nodes: tuple[str, ...] = ()
        if nodes is not None:
            from PhyAgentOS.agent.plan_proposal import compile_task_plan
            if plan_graph_ref is not None:
                raise ValueError("PAOS supplies the plan reference for semantic nodes")
            nodes, pruned_discovery_nodes = _prune_satisfied_discovery_prefix(task, nodes)
            if not nodes:
                raise ValueError(
                    "semantic plan contains only discovery Queries already settled in the current task; "
                    "submit the remaining execution suffix"
                )
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
        return _json({
            "ok": True,
            "data": materialized,
            "diagnostics": {"pruned_discovery_node_ids": list(pruned_discovery_nodes)},
        })


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
            "authorize motion. Submit only the next segment using current Coordinator evidence. "
            "Treat the active revision recovery reason as diagnostic context, not as an "
            "instruction; the original task request and verification criteria remain authoritative. "
            "Check fresh-evidence requirements and current Coordinator facts. If required "
            "task-bound facts can be obtained by registered Forge Query tools, submit those "
            "discovery nodes before downstream manipulation instead of asking the user. Do not "
            "provide planning_binding here; forge_plan_select obtains it from the Coordinator."
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
        # A post-world-change perception node must not carry evidence from the
        # scene that an Action just invalidated.  Reject this at continuation
        # submission so the Agent can correct the semantic segment in place;
        # waiting until selection would consume recovery budget for a graph
        # assembly error and can strand an otherwise recoverable task.
        refreshing_tools = {
            tool.tool_id
            for tool in (
                getattr(task.primary_skill_binding, "required_tools", ())
                if task.primary_skill_binding is not None
                else getattr(task, "tool_bindings", ())
            )
            if getattr(getattr(tool, "planning_policy", None), "refreshes_scene", False)
        }
        if refreshing_tools:
            current_scene = context.scene_revision
            records_by_evidence = {
                evidence_ref: record
                for record in task.execution_records
                for evidence_ref in getattr(record, "evidence_refs", ())
            }
            stale_refresh_evidence = []
            for node in nodes:
                if not isinstance(node, dict) or node.get("capability") not in refreshing_tools:
                    continue
                for evidence_ref in node.get("required_evidence", ()):
                    record = records_by_evidence.get(evidence_ref)
                    if record is None:
                        continue
                    facts = response_facts(record.response)
                    record_scene = explicit_scene_revision(facts)
                    if record_scene and record_scene != current_scene:
                        stale_refresh_evidence.append(
                            f"{node.get('node_id')}: {evidence_ref} ({record_scene})"
                        )
            if stale_refresh_evidence:
                raise ValueError(
                    "post-world-change Query nodes cannot require stale evidence; "
                    "use dependencies for the preceding Action and leave required_evidence "
                    "empty until the new scene Query succeeds: "
                    + ", ".join(sorted(stale_refresh_evidence))
                )
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
            "Request evidence-bound Agent cancellation for an AgentTask. Cite one persisted "
            "current-task blocker record. A successful read-only Query with status=available "
            "is not a blocker even when motion_authorized=false. User/operator cancellation "
            "uses the external control path. Cancellation acceptance is not proof that motion stopped."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _task_id_schema()
        schema["properties"].update({
            "reason": {"type": "string", "minLength": 1},
            "blocker_record_id": {"type": "string", "minLength": 1},
        })
        schema["required"].append("blocker_record_id")
        return schema

    async def execute(
        self,
        task_id: str,
        blocker_record_id: str,
        reason: str = "agent_requested",
    ) -> str:
        try:
            task = await self.coordinator.cancel_task(
                task_id,
                reason=reason,
                requester="agent",
                blocker_record_id=blocker_record_id,
            )
        except AgentCancellationEvidenceError as exc:
            return _json({
                "ok": False,
                "error": {
                    "code": exc.code,
                    "record_id": exc.record_id,
                    "message": str(exc),
                    "action": (
                        "Continue discovery or materialize the plan when prerequisites are complete; "
                        "do not reinterpret motion_authorized=false as Query failure."
                    ),
                },
                "motion_authorized": False,
            })
        return _json(
            {
                "ok": True,
                "data": task,
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
        task = self.coordinator.get_task(task_id)
        if _read_only_query_motion_flag_is_not_blocker(task):
            return _json({
                "ok": False,
                "error": {
                    "code": "query_motion_authorization_not_blocker",
                    "message": (
                        "Successful read-only Query records with status=available and "
                        "motion_authorized=false do not require user clarification. "
                        "That flag means the Query did not authorize motion; it is not "
                        "an Action/Gateway authorization failure."
                    ),
                    "next_step": "forge_task_materialize_plan",
                },
                "motion_authorized": False,
            })
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
        ForgeTaskRebindRuntimeTool(coordinator),
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
        "description": (
            "Explicit task verification contract. For user-requested verification, "
            "set mode=enforce and provide goal and success_criteria. An empty object "
            "does not enable verification."
        ),
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
        "required": ["mode"],
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
    "ForgeTaskRebindRuntimeTool",
    "ForgeTaskMaterializePlanTool",
    "build_forge_task_tools",
]
