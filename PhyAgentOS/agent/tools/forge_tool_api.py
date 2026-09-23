"""Governed Agent wrappers for the Forge Gateway Tool API."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable
from uuid import uuid4

from PhyAgentOS.agent.argument_sources import (
    ArgumentSourceError,
    argument_path_schema,
    resolve_argument_sources,
)
from PhyAgentOS.agent.planning_facts import response_facts
from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskError
from PhyAgentOS.forge.tool_client import (
    ForgeToolAPIError,
    ForgeToolAPITimeoutError,
    ForgeToolClient,
)

# Scene understanding is a synchronous, model-backed Query.  The previous
# caller-selected 30-second deadline was shorter than the configured GPT
# provider timeout and repeatedly converted slow-but-valid responses into an
# ``unknown`` transport result.  Keep this policy at the Agent Tool boundary
# so PAOS planning remains provider-neutral and Action/Session deadlines are
# unchanged.
_SCENE_UNDERSTAND_TIMEOUT_MS = 180_000

# These are identity and provenance inputs owned by the current scene
# observation. Resolve them from its receipt instead of asking the model to
# retype opaque references between standard discovery Queries.
_OBSERVATION_BOUND_QUERY_ARGUMENTS: dict[str, dict[str, dict[str, Any]]] = {
    "manipulation.capabilities": {
        "scene_revision": {"path": ["response", "data", "scene_revision"]},
        "observation_ref": {"path": ["response", "data", "observation_ref"]},
        "calibration_ref": {"path": ["response", "data", "calibration_ref"]},
    },
    "scene.understand": {
        "observation_ref": {"path": ["response", "data", "observation_ref"]},
        "scene_revision": {"path": ["response", "data", "scene_revision"]},
        "frame_id": {"path": ["response", "data", "frame", "frame_id"]},
        "calibration_ref": {"path": ["response", "data", "calibration_ref"]},
        "freshness_ms": {"path": ["response", "data", "freshness_ms"]},
        "artifacts": {
            "path": ["response", "data", "artifacts"],
            "map_field": "ref",
        },
    },
}


def _effective_query_timeout_ms(tool_id: str, timeout_ms: int | None) -> int | None:
    if tool_id != "scene.understand":
        return timeout_ms
    if timeout_ms is None:
        return _SCENE_UNDERSTAND_TIMEOUT_MS
    return max(timeout_ms, _SCENE_UNDERSTAND_TIMEOUT_MS)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


async def _call(operation: Callable[[], Awaitable[dict[str, Any]]]) -> str:
    try:
        return _json(await operation())
    except ForgeToolAPIError as exc:
        error: dict[str, Any] = {
            "type": "timeout" if isinstance(exc, ForgeToolAPITimeoutError) else "gateway_tool_api",
            "message": str(exc),
        }
        for name in ("status_code", "error_code", "retryable"):
            value = getattr(exc, name)
            if value is not None:
                error["code" if name == "error_code" else name] = value
        payload_data = exc.payload.get("data") if isinstance(exc.payload, dict) else None
        if isinstance(payload_data, dict):
            for identity in ("invocation_id", "attempt_id"):
                if isinstance(payload_data.get(identity), str):
                    error[identity] = payload_data[identity]
        if isinstance(exc, ForgeToolAPITimeoutError):
            timeout_s = getattr(exc, "timeout_s", None)
            reason = str(exc)
            if isinstance(timeout_s, (int, float)) and timeout_s > 0:
                reason = f"{reason} (timeout_budget_s={timeout_s:g})"
            error.update(
                {
                    "message": reason,
                    "code": "gateway_timeout",
                    "status": "timeout",
                    "reason": reason,
                    # The user-facing status is timeout; the internal
                    # accounting remains uncertain until a remote result can
                    # be reconciled, so no success is inferred.
                    "remote_state": "unconfirmed",
                    "stopped": False,
                }
            )
        return _json({"ok": False, "error": error})
    except AgentTaskError as exc:
        return _json({"ok": False, "error": {"type": "agent_task", "message": str(exc)}})
    except RuntimeError as exc:
        return _json({"ok": False, "error": {"type": "runtime", "message": str(exc)}})


class ForgeToolContextTool(Tool):
    def __init__(self, client: ForgeToolClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "forge_tool_context"

    @property
    def description(self) -> str:
        return "Read a Forge ToolSpec and its live readiness/context before invocation."

    @property
    def parameters(self) -> dict[str, Any]:
        return _single_schema("tool_id")

    async def execute(self, tool_id: str) -> str:
        async def describe() -> dict[str, Any]:
            spec, context = await asyncio.gather(
                self.client.get_tool(tool_id), self.client.get_tool_context(tool_id)
            )
            return {"ok": True, "data": {"tool": spec["data"], "context": context["data"]}}

        return await _call(describe)


class ForgeToolQueryTool(Tool):
    def __init__(self, client: ForgeToolClient, coordinator: AgentTaskCoordinator) -> None:
        self.client = client
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_tool_query"

    @property
    def description(self) -> str:
        return (
            "Invoke a Gateway-declared read-only Query. Supply task_id while executing an "
            "AgentTask so the result is audited; omit it only for unbound diagnostics. "
            "Task-bound responses include coordinator-owned paos_record with record_id and "
            "evidence_refs for plan submission; data remains the Gateway result. PAOS "
            "automatically copies scene identity and provenance fields for "
            "scene.understand and manipulation.capabilities from this task's latest "
            "successful scene.observe; omit those fields from arguments. For other "
            "follow-up Query inputs, use argument_sources to copy exact fields from a "
            "successful Query record in this task's active revision instead of retyping them. Each "
            "entry names record_id, an explicit path such as ['response','scene_revision'], "
            "and optional target_path. For scene.understand, copy observation_ref, "
            "scene_revision, frame.frame_id to frame_id, calibration_ref, freshness_ms, "
            "and artifacts from the same scene.observe record; set artifact source "
            "map_field to 'ref' to pass the required string references. Supply "
            "max_age_ms as a literal."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return _invoke_schema(
            task_required=False,
            include_timeout=True,
            include_argument_sources=True,
        )

    async def execute(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        task_id: str | None = None,
        timeout_ms: int | None = None,
        planning_binding: dict[str, Any] | None = None,
        use_selected_arguments: bool = False,
        argument_sources: dict[str, Any] | None = None,
    ) -> str:
        if argument_sources and not task_id:
            return _json({
                "ok": False,
                "error": {
                    "type": "agent_task",
                    "message": "argument_sources require task_id",
                },
            })
        if use_selected_arguments and argument_sources:
            return _json({
                "ok": False,
                "error": {
                    "type": "agent_arguments",
                    "message": "argument_sources cannot be combined with use_selected_arguments",
                },
            })
        if (planning_binding is not None or use_selected_arguments) and not task_id:
            return _json(
                {
                    "ok": False,
                    "error": {
                        "type": "agent_task",
                        "message": "planning_binding requires task_id",
                    },
                }
            )
        effective_timeout_ms = _effective_query_timeout_ms(tool_id, timeout_ms)
        if task_id:
            async def invoke():
                resolved_arguments = arguments
                resolved_binding = planning_binding
                task = self.coordinator.get_task(task_id)
                sources = _task_query_source_records(task)
                if (
                    tool_id in _OBSERVATION_BOUND_QUERY_ARGUMENTS
                    and not use_selected_arguments
                    and planning_binding is None
                ):
                    try:
                        resolved_arguments = _resolve_observation_bound_query_arguments(
                            tool_id,
                            task,
                            arguments,
                        )
                    except ArgumentSourceError as exc:
                        raise AgentTaskError(str(exc)) from exc
                remaining_sources = argument_sources
                if remaining_sources and tool_id in _OBSERVATION_BOUND_QUERY_ARGUMENTS:
                    bound_fields = _OBSERVATION_BOUND_QUERY_ARGUMENTS[tool_id]
                    remaining_sources = {
                        name: selector
                        for name, selector in remaining_sources.items()
                        if name not in bound_fields
                    }
                if remaining_sources:
                    try:
                        resolved_arguments = resolve_argument_sources(
                            sources,
                            resolved_arguments,
                            remaining_sources,
                        )
                    except ArgumentSourceError as exc:
                        raise AgentTaskError(str(exc)) from exc
                if use_selected_arguments:
                    binding = self.coordinator.selected_execution_binding(
                        task_id, tool_id, "query", planning_binding
                    )
                    resolved_binding = binding.model_dump(mode="json")
                    resolved_arguments = self.coordinator.selected_execution_arguments(
                        task_id, tool_id, "query", {}, resolved_binding
                    )
                return await self.coordinator.invoke_query(
                    task_id, tool_id,
                    resolved_arguments,
                    timeout_ms=effective_timeout_ms,
                    planning_binding=resolved_binding,
                )
            return await _call(invoke)
        return await _call(
            lambda: self.client.invoke_query_tool(
                tool_id,
                arguments,
                caller_id=f"paos:diagnostic:{uuid4().hex[:20]}",
                timeout_ms=effective_timeout_ms,
            )
        )


class ForgeToolStartActionTool(Tool):
    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_tool_start_action"

    @property
    def description(self) -> str:
        return "Start a task-bound Forge Action; admission is not completion or task success."

    @property
    def parameters(self) -> dict[str, Any]:
        return _invoke_schema(task_required=True, include_timeout=True)

    async def execute(
        self,
        task_id: str,
        tool_id: str,
        arguments: dict[str, Any],
        timeout_ms: int | None = None,
        planning_binding: dict[str, Any] | None = None,
        use_selected_arguments: bool = False,
    ) -> str:
        async def start():
            resolved_arguments = arguments
            resolved_binding = planning_binding
            # Actions always consume the Coordinator's unique pending selection.
            binding = self.coordinator.selected_execution_binding(
                task_id, tool_id, "action", planning_binding
            )
            resolved_binding = binding.model_dump(mode="json")
            resolved_arguments = self.coordinator.selected_execution_arguments(
                task_id, tool_id, "action", {}, resolved_binding
            )
            return await self.coordinator.start_action(
                task_id, tool_id,
                resolved_arguments,
                timeout_ms=timeout_ms,
                planning_binding=resolved_binding,
            )
        return await _call(start)


class _ActionReadTool(Tool):
    operation = ""

    def __init__(self, client: ForgeToolClient, coordinator: AgentTaskCoordinator) -> None:
        self.client = client
        self.coordinator = coordinator

    @property
    def parameters(self) -> dict[str, Any]:
        return _owned_invocation_schema()

    async def execute(self, task_id: str, invocation_id: str) -> str:
        async def read() -> dict[str, Any]:
            # Reject cross-task identifiers before disclosing Gateway state.
            self.coordinator.require_action_invocation(task_id, invocation_id)
            if self.operation == "status":
                response = await self.client.invocation_status(invocation_id)
            else:
                response = await self.client.invocation_result(invocation_id)
            self.coordinator.observe_action(
                task_id,
                invocation_id,
                response,
                reconcile_settlement=self.operation == "result",
            )
            return response

        return await _call(read)


class ForgeToolActionStatusTool(_ActionReadTool):
    operation = "status"

    @property
    def name(self) -> str:
        return "forge_tool_action_status"

    @property
    def description(self) -> str:
        return (
            "Read and persist Action progress without settling the planning node; "
            "the result endpoint owns terminal settlement facts."
        )


class ForgeToolActionResultTool(_ActionReadTool):
    operation = "result"

    @property
    def name(self) -> str:
        return "forge_tool_action_result"

    @property
    def description(self) -> str:
        return "Read and persist this task's Action result; pending and unknown are not success."


class ForgeToolCancelActionTool(Tool):
    def __init__(self, client: ForgeToolClient, coordinator: AgentTaskCoordinator) -> None:
        self.client = client
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_tool_cancel_action"

    @property
    def description(self) -> str:
        return "Request cancellation of this task's Action; then poll until terminal or unknown."

    @property
    def parameters(self) -> dict[str, Any]:
        return _owned_invocation_schema()

    async def execute(self, task_id: str, invocation_id: str) -> str:
        async def cancel() -> dict[str, Any]:
            # Ownership is checked before the control request is sent.
            self.coordinator.require_action_invocation(task_id, invocation_id)
            response = await self.client.cancel_invocation(invocation_id)
            self.coordinator.record_cancel_response(task_id, invocation_id, response)
            return response

        return await _call(cancel)


class ForgeToolStartSessionTool(Tool):
    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_tool_start_session"

    @property
    def description(self) -> str:
        return "Start a first-class, no-deadline Forge Session with explicit ownership."

    @property
    def parameters(self) -> dict[str, Any]:
        schema = _invoke_schema(task_required=True, include_timeout=False)
        schema["properties"]["ownership"] = {"type": "string", "enum": ["task", "shared"]}
        schema["required"].append("ownership")
        return schema

    async def execute(
        self,
        task_id: str,
        tool_id: str,
        arguments: dict[str, Any],
        ownership: str,
        planning_binding: dict[str, Any] | None = None,
        use_selected_arguments: bool = False,
    ) -> str:
        async def start():
            resolved_arguments = arguments
            resolved_binding = planning_binding
            binding = self.coordinator.selected_execution_binding(
                task_id, tool_id, "session", planning_binding
            )
            resolved_binding = binding.model_dump(mode="json")
            resolved_arguments = self.coordinator.selected_execution_arguments(
                task_id, tool_id, "session", {}, resolved_binding
            )
            return await self.coordinator.start_session(
                task_id, tool_id,
                resolved_arguments,
                ownership=ownership,  # type: ignore[arg-type]
                planning_binding=resolved_binding,
            )
        return await _call(start)


class _SessionReadTool(Tool):
    operation = ""

    def __init__(self, client: ForgeToolClient, coordinator: AgentTaskCoordinator) -> None:
        self.client = client
        self.coordinator = coordinator

    @property
    def parameters(self) -> dict[str, Any]:
        return _owned_invocation_schema()

    async def execute(self, task_id: str, invocation_id: str) -> str:
        async def read() -> dict[str, Any]:
            # Reject cross-task identifiers before disclosing Gateway state.
            self.coordinator.require_session_invocation(task_id, invocation_id)
            response = (
                await self.client.invocation_status(invocation_id)
                if self.operation == "status"
                else await self.client.invocation_result(invocation_id)
            )
            self.coordinator.observe_session(
                task_id,
                invocation_id,
                response,
                reconcile_settlement=self.operation == "result",
            )
            return response

        return await _call(read)


class ForgeToolSessionStatusTool(_SessionReadTool):
    operation = "status"

    @property
    def name(self) -> str:
        return "forge_tool_session_status"

    @property
    def description(self) -> str:
        return (
            "Read and persist Session progress without settling the planning node; "
            "the result endpoint owns terminal settlement facts."
        )


class ForgeToolSessionResultTool(_SessionReadTool):
    operation = "result"

    @property
    def name(self) -> str:
        return "forge_tool_session_result"

    @property
    def description(self) -> str:
        return "Read the result of a terminal task-referenced Forge Session."


class ForgeToolStopSessionTool(Tool):
    def __init__(self, coordinator: AgentTaskCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def name(self) -> str:
        return "forge_tool_stop_session"

    @property
    def description(self) -> str:
        return "Request stop for a task-owned Session; shared/runtime Sessions are protected."

    @property
    def parameters(self) -> dict[str, Any]:
        return _owned_invocation_schema()

    async def execute(self, task_id: str, invocation_id: str) -> str:
        return await _call(lambda: self.coordinator.stop_session(task_id, invocation_id))


def build_forge_tool_api_tools(
    client: ForgeToolClient,
    *,
    invocation_ids: Any | None = None,
    coordinator: AgentTaskCoordinator | None = None,
) -> list[Tool]:
    """Build Query/Action/Session wrappers; all mutation requires a Coordinator."""
    del invocation_ids
    if coordinator is None:
        return [ForgeToolContextTool(client)]
    return [
        ForgeToolContextTool(client),
        ForgeToolQueryTool(client, coordinator),
        ForgeToolStartActionTool(coordinator),
        ForgeToolActionStatusTool(client, coordinator),
        ForgeToolActionResultTool(client, coordinator),
        ForgeToolCancelActionTool(client, coordinator),
        ForgeToolStartSessionTool(coordinator),
        ForgeToolSessionStatusTool(client, coordinator),
        ForgeToolSessionResultTool(client, coordinator),
        ForgeToolStopSessionTool(coordinator),
    ]


def _single_schema(name: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {name: {"type": "string", "minLength": 1}},
        "required": [name],
        "additionalProperties": False,
    }


def _owned_invocation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "minLength": 1},
            "invocation_id": {"type": "string", "minLength": 1},
        },
        "required": ["task_id", "invocation_id"],
        "additionalProperties": False,
    }


def _invoke_schema(
    *,
    task_required: bool,
    include_timeout: bool,
    include_argument_sources: bool = False,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "task_id": {"type": "string", "minLength": 1},
        "tool_id": {"type": "string", "minLength": 1},
        "arguments": {"type": "object"},
        "use_selected_arguments": {
            "type": "boolean",
            "description": "Use exact persisted selection arguments; pass arguments={}. The Coordinator resolves the current task/node selection and its binding.",
        },
        "planning_binding": {
            "type": "object",
            "properties": {
                "revision_id": {"type": "string", "minLength": 1},
                "node_id": {"type": "string", "minLength": 1},
                "node_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "obligation_id": {"type": "string", "minLength": 1},
                "input_binding_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "decision_trace_ref": {"type": "string", "pattern": "^artifact://.+"},
            },
            "required": [
                "node_id", "node_digest", "obligation_id",
                "input_binding_digest", "decision_trace_ref",
            ],
            "additionalProperties": False,
        },
    }
    required = ["tool_id", "arguments"]
    if task_required:
        required.insert(0, "task_id")
    if include_timeout:
        properties["timeout_ms"] = {"type": "integer", "minimum": 1}
    if include_argument_sources:
        properties["argument_sources"] = {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "record_id": {"type": "string", "minLength": 1},
                    "path": argument_path_schema(),
                    "target_path": argument_path_schema(),
                    "map_field": {"type": "string", "minLength": 1},
                },
                "required": ["record_id", "path"],
                "additionalProperties": False,
            },
        }
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _task_query_source_records(task: Any) -> dict[str, tuple[dict[str, Any], dict[str, Any] | None]]:
    """Expose latest successful Query records from this task's active revision."""

    latest_by_tool: dict[str, Any] = {}
    for record in task.execution_records:
        if (
            record.revision_id == task.active_revision_id
            and record.semantics == "query"
        ):
            latest_by_tool[record.tool_id] = record

    excluded_statuses = {"unavailable", "invalid", "stale", "empty", "failed", "unknown"}
    sources: dict[str, tuple[dict[str, Any], dict[str, Any] | None]] = {}
    for record in latest_by_tool.values():
        if record.status != "succeeded" or not isinstance(record.response, dict):
            continue
        if response_facts(record.response).get("status") in excluded_statuses:
            continue
        sources[record.record_id] = (record.arguments, record.response)
    return sources


def _resolve_observation_bound_query_arguments(
    tool_id: str,
    task: Any,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Project canonical scene inputs from the active revision's observation."""

    bindings = _OBSERVATION_BOUND_QUERY_ARGUMENTS[tool_id]
    sources = _task_query_source_records(task)
    observation_record = next(
        (
            record
            for record in reversed(task.execution_records)
            if record.tool_id == "scene.observe"
            and record.semantics == "query"
            and record.revision_id == task.active_revision_id
            and record.record_id in sources
        ),
        None,
    )
    if observation_record is None:
        raise ArgumentSourceError(
            f"{tool_id} requires a successful scene.observe Query in the active revision"
        )

    literals = {key: value for key, value in arguments.items() if key not in bindings}
    selectors = {
        name: {"record_id": observation_record.record_id, **selector}
        for name, selector in bindings.items()
    }
    return resolve_argument_sources(sources, literals, selectors)


__all__ = [
    "ForgeToolActionResultTool",
    "ForgeToolActionStatusTool",
    "ForgeToolCancelActionTool",
    "ForgeToolContextTool",
    "ForgeToolQueryTool",
    "ForgeToolSessionResultTool",
    "ForgeToolSessionStatusTool",
    "ForgeToolStartActionTool",
    "ForgeToolStartSessionTool",
    "ForgeToolStopSessionTool",
    "build_forge_tool_api_tools",
]
