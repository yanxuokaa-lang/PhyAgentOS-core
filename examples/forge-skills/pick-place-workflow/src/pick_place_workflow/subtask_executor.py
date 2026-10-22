"""PAOS subtask orchestration for observation-bound held manipulation.

The executor is deliberately below the AgentLoop model boundary.  It runs a
finite sequence of already-governed Tool calls, keeps their receipts, and
returns one aggregate result for the parent semantic subtask.  It does not
create tasks, revisions, SQLite records, or simulator commands.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from PhyAgentOS.forge.capability_runtime import ActionAdmission, CapabilityRuntime
from PhyAgentOS.planning import NodeSettlement
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ENTITY_REF = re.compile(r"^entity://[^/]+$")
_DESTINATION_REF = re.compile(r"^(?:destination|container)://\S+$")
_OBSERVATION_REF = re.compile(r"^observation://\S+$")
_ARTIFACT_REF = re.compile(r"^artifact://\S+$")
_CANDIDATE_REF = re.compile(r"^candidate-set://\S+$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]+$")

SubtaskOperation = Literal["relocate", "pour", "stir"]
SubtaskStatus = Literal["completed", "failed", "outcome_unknown", "cancelled"]


class SubtaskExecutionError(ValueError):
    """The subtask contract or an internal Tool result is not admissible."""


class SubtaskContextResolver(Protocol):
    """Resolve a persisted PAOS caller into Coordinator-owned execution facts."""

    def __call__(self, caller_id: str) -> Mapping[str, Any]: ...


class SubtaskInvoker(Protocol):
    """Existing PAOS Tool transport exposed as one bounded call."""

    def invoke(self, tool_id: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]: ...


class PerceptionBinding(BaseModel):
    """Measured target binding produced by observation/understanding tools.

    Prim paths are intentionally absent.  An adapter may privately resolve an
    opaque entity reference to a provider object after this binding is checked.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_ref: str
    semantic_label: str = Field(min_length=1)
    category: str = Field(min_length=1)
    destination_semantic_label: str = Field(min_length=1)
    destination_category: str = Field(min_length=1)
    measured_pose: Mapping[str, Any]
    measured_geometry: Mapping[str, Any]
    grasp_candidate: Mapping[str, Any]
    grasp_candidate_ref: str
    candidate_set_ref: str
    candidate_ref: str
    capability_snapshot_ref: str
    binding_ref: str
    destination_ref: str
    destination_pose: Mapping[str, Any]
    process_frame: str = Field(min_length=1)
    observation_ref: str
    scene_revision: str = Field(min_length=1)
    frame_id: str = Field(min_length=1)
    calibration_ref: str
    freshness_ms: int = Field(ge=0)
    max_age_ms: int = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: str = Field(min_length=1)

    @field_validator("entity_ref")
    @classmethod
    def entity_reference(cls, value: str) -> str:
        if _ENTITY_REF.fullmatch(value) is None:
            raise ValueError("entity_ref must be an opaque entity:// reference")
        return value

    @field_validator("destination_ref")
    @classmethod
    def destination_reference(cls, value: str) -> str:
        if _DESTINATION_REF.fullmatch(value) is None:
            raise ValueError("destination_ref must be an opaque destination reference")
        return value

    @field_validator("observation_ref")
    @classmethod
    def observation_reference(cls, value: str) -> str:
        if _OBSERVATION_REF.fullmatch(value) is None:
            raise ValueError("observation_ref must use observation://")
        return value

    @field_validator("calibration_ref")
    @classmethod
    def calibration_reference(cls, value: str) -> str:
        if _ARTIFACT_REF.fullmatch(value) is None:
            raise ValueError("calibration_ref must use artifact://")
        return value

    @field_validator("grasp_candidate_ref")
    @classmethod
    def candidate_reference(cls, value: str) -> str:
        if _CANDIDATE_REF.fullmatch(value) is None:
            raise ValueError("grasp_candidate_ref must use candidate-set://")
        return value

    @field_validator("candidate_set_ref")
    @classmethod
    def candidate_set_reference(cls, value: str) -> str:
        if _CANDIDATE_REF.fullmatch(value) is None:
            raise ValueError("candidate_set_ref must use candidate-set://")
        return value

    @field_validator("candidate_ref")
    @classmethod
    def candidate_item_reference(cls, value: str) -> str:
        if not value.startswith("candidate://"):
            raise ValueError("candidate_ref must use candidate://")
        return value

    @field_validator("capability_snapshot_ref")
    @classmethod
    def artifact_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if _ARTIFACT_REF.fullmatch(value) is None:
            raise ValueError("capability and assignment references must use artifact://")
        return value

    @field_validator("binding_ref")
    @classmethod
    def binding_reference(cls, value: str) -> str:
        if _ARTIFACT_REF.fullmatch(value) is None:
            raise ValueError("binding_ref must use artifact://")
        return value

    @model_validator(mode="after")
    def fresh_and_finite(self) -> "PerceptionBinding":
        if self.freshness_ms > self.max_age_ms:
            raise ValueError("perception binding is stale")
        if self.grasp_candidate_ref != self.candidate_set_ref:
            raise ValueError("grasp_candidate_ref must match candidate_set_ref")
        try:
            json.dumps(self.grasp_candidate, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("grasp candidate must contain finite JSON values") from exc
        for value in (self.measured_pose, self.measured_geometry, self.destination_pose):
            try:
                json.dumps(value, ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise ValueError("perception binding contains non-finite geometry") from exc
        return self


class SubtaskToolCall(BaseModel):
    """One internal call; it is not an Agent-facing PlanNode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_id: str
    phase: Literal["acquire", "prepare", "process", "place"]
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tool_id")
    @classmethod
    def tool_identity(cls, value: str) -> str:
        if _SAFE_ID.fullmatch(value) is None:
            raise ValueError("internal Tool identity is invalid")
        return value

    @field_validator("arguments")
    @classmethod
    def finite_arguments(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("internal Tool arguments must contain finite JSON values") from exc
        return value


def default_subtask_calls(operation: SubtaskOperation) -> tuple[SubtaskToolCall, ...]:
    """Return the PAOS held-object sequence without provider-specific details."""
    process_tool = "object.pour" if operation == "pour" else "tool.stir"
    if operation == "relocate":
        return (
            SubtaskToolCall(tool_id="manipulation.prepare", phase="prepare"),
            SubtaskToolCall(tool_id="object.acquire", phase="acquire"),
            SubtaskToolCall(tool_id="object.place", phase="place"),
        )
    return (
        SubtaskToolCall(tool_id="manipulation.prepare", phase="prepare"),
        SubtaskToolCall(tool_id="object.acquire", phase="acquire"),
        SubtaskToolCall(tool_id="manipulation.prepare_held", phase="prepare", arguments={"operation": operation}),
        SubtaskToolCall(tool_id=process_tool, phase="process", arguments={"operation": operation}),
        SubtaskToolCall(tool_id="manipulation.prepare_held", phase="prepare", arguments={"operation": "place"}),
        SubtaskToolCall(tool_id="object.place", phase="place"),
    )


class SubtaskSpec(BaseModel):
    """One Agent-facing semantic subtask with a finite internal Tool sequence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subtask_id: str
    operation: SubtaskOperation
    binding: PerceptionBinding
    depends_on: tuple[str, ...] = ()
    parameters: dict[str, Any] = Field(default_factory=dict)
    # Semantic fields are supplied by the plan; trusted execution identity is
    # added later by the PAOS selection builder.
    semantic_intent: dict[str, Any] | None = None
    trusted_intent: dict[str, Any] | None = None
    tool_sequence: tuple[SubtaskToolCall, ...] = ()
    return_destination_ref: str | None = None

    @field_validator("subtask_id")
    @classmethod
    def subtask_identity(cls, value: str) -> str:
        if _SAFE_ID.fullmatch(value) is None:
            raise ValueError("subtask_id is invalid")
        return value

    @field_validator("depends_on")
    @classmethod
    def unique_dependencies(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(_SAFE_ID.fullmatch(item or "") is None for item in value):
            raise ValueError("subtask dependencies must be path-safe identifiers")
        if len(value) != len(set(value)):
            raise ValueError("subtask dependencies must be unique")
        return value

    @field_validator("parameters")
    @classmethod
    def finite_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("subtask parameters must contain finite JSON values") from exc
        return value

    @field_validator("semantic_intent")
    @classmethod
    def validate_semantic_intent(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        allowed = {"goal", "success_criteria", "allowed_arms", "coordination_mode", "constraints"}
        unexpected = set(value) - allowed
        if unexpected:
            raise ValueError("subtask intent contains unsupported fields")
        required = {"goal", "success_criteria", "allowed_arms", "coordination_mode"}
        if required - set(value):
            raise ValueError("subtask intent is missing required semantic fields")
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("subtask intent must contain finite JSON values") from exc
        return value

    @model_validator(mode="after")
    def sequence_shape(self) -> "SubtaskSpec":
        calls = self.tool_sequence or default_subtask_calls(self.operation)
        expected_calls = default_subtask_calls(self.operation)
        if calls != expected_calls:
            raise ValueError("tool_sequence must follow the governed acquire/prepare/process/place sequence")
        if not calls:
            raise ValueError("subtask requires at least one internal Tool")
        if calls[0].tool_id != "manipulation.prepare" or calls[0].phase != "prepare":
            raise ValueError("subtask must begin with manipulation.prepare")
        if calls[-1].tool_id != "object.place" or calls[-1].phase != "place":
            raise ValueError("subtask must end with object.place")
        if self.operation in {"pour", "stir"}:
            expected = "object.pour" if self.operation == "pour" else "tool.stir"
            if not any(call.tool_id == expected and call.phase == "process" for call in calls):
                raise ValueError(f"{self.operation} subtask requires {expected}")
        try:
            json.dumps(self.parameters, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("subtask parameters must contain finite JSON values") from exc
        if self.return_destination_ref is not None and _DESTINATION_REF.fullmatch(self.return_destination_ref) is None:
            raise ValueError("return_destination_ref must use destination:// or container://")
        object.__setattr__(self, "tool_sequence", calls)
        return self

    def calls(self) -> tuple[SubtaskToolCall, ...]:
        return self.tool_sequence


class ToolReceipt(BaseModel):
    """Immutable-in-practice internal Tool fact projected by the executor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence_index: int = Field(ge=0)
    tool_id: str
    phase: str
    invocation_id: str | None = None
    attempt_id: str | None = None
    status: str
    outcome_known: bool
    response: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None


class SubtaskExecutionResult(BaseModel):
    """One aggregate result returned to the AgentLoop at the subtask boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subtask_id: str
    status: SubtaskStatus
    outcome_known: bool
    completed_tool_ids: tuple[str, ...] = ()
    receipts: tuple[ToolReceipt, ...] = ()
    failed_phase: str | None = None
    failure_code: str | None = None
    possession_state: Literal["empty", "holding", "uncertain"] = "uncertain"
    scene_revision: str | None = None
    recommended_action: str

    def to_node_settlement(
        self,
        *,
        task_id: str,
        revision_id: str,
        invocation_id: str | None = None,
        source_tool_id: str = "manipulation.execute_subtask",
        evidence_refs: tuple[str, ...] = (),
    ) -> NodeSettlement:
        if self.status == "completed":
            settlement_status = "completed"
        elif self.status == "outcome_unknown":
            settlement_status = "outcome_unknown"
        elif self.status == "cancelled" and not self.receipts:
            settlement_status = "cancelled_before_start"
        else:
            settlement_status = "failed"
        return NodeSettlement(
            task_id=task_id,
            revision_id=revision_id,
            node_id=self.subtask_id,
            invocation_id=invocation_id,
            status=settlement_status,
            evidence_refs=tuple(dict.fromkeys((*evidence_refs, *self._receipt_refs()))),
            scene_revision=self.scene_revision,
            failure_code=self.failure_code,
            source_tool_id=source_tool_id,
            world_change_started=any(
                receipt.response.get("world_change_started") is True for receipt in self.receipts
            ),
            outcome_known=self.outcome_known,
            requires_replan=self.status == "outcome_unknown",
            recommended_action=self.recommended_action,
        )

    def _receipt_refs(self) -> tuple[str, ...]:
        refs: list[str] = []
        for receipt in self.receipts:
            for ref in receipt.response.get("evidence_refs", ()):
                if isinstance(ref, str) and ref.startswith("artifact://"):
                    refs.append(ref)
        return tuple(refs)


@dataclass(frozen=True)
class SubtaskExecutionContext:
    """Non-authoritative execution context carried between internal calls."""

    possession_state: str = "empty"
    scene_revision: str | None = None
    acquire_invocation_ref: str | None = None
    last_response: Mapping[str, Any] | None = None
    trusted_intent: Mapping[str, Any] | None = None
    prepared_arguments: Mapping[str, Any] | None = None


def _persist_assignment_artifact(store: Any, response: Mapping[str, Any]) -> None:
    if store is None:
        return
    assignments = response.get("assignments")
    route_arguments = response.get("route_arguments")
    if not isinstance(assignments, list) or len(assignments) != 1:
        raise SubtaskExecutionError("preparation did not return one assignment to persist")
    assignment = assignments[0]
    if not isinstance(assignment, Mapping):
        raise SubtaskExecutionError("preparation assignment is not an object")
    assignment_ref = assignment.get("assignment_ref")
    if not isinstance(assignment_ref, str) or not assignment_ref.startswith("artifact://"):
        raise SubtaskExecutionError("preparation assignment has no canonical reference")
    if not isinstance(route_arguments, Mapping):
        raise SubtaskExecutionError("preparation did not return approved route arguments")
    store.put(assignment_ref, {
        "assignment": dict(assignment),
        "preparation_ref": response.get("preparation_ref"),
        "route_arguments": dict(route_arguments),
    })


class SubtaskExecutor:
    """Execute one finite subtask without opening another Agent model turn."""

    def __init__(
        self,
        invoker: SubtaskInvoker | Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
        *,
        cancel_requested: Callable[[], bool] | None = None,
        assignment_store=None,
    ) -> None:
        self._invoker = invoker
        self._cancel_requested = cancel_requested or (lambda: False)
        self._assignment_store = assignment_store

    def execute(self, spec: SubtaskSpec) -> SubtaskExecutionResult:
        receipts: list[ToolReceipt] = []
        completed: list[str] = []
        context = SubtaskExecutionContext(
            scene_revision=spec.binding.scene_revision,
            trusted_intent=spec.trusted_intent,
        )
        for index, call in enumerate(spec.calls()):
            if self._cancel_requested():
                return self._result(spec, receipts, completed, context, "cancelled", False, call.phase, "cancelled_before_next_tool")
            arguments = self._arguments(spec, call, context)
            try:
                raw = self._invoke(call.tool_id, arguments)
                if not isinstance(raw, Mapping):
                    raise SubtaskExecutionError("internal Tool returned a non-object result")
                response = dict(raw)
                status, known = self._status(call, response)
                receipt = ToolReceipt(
                    sequence_index=index,
                    tool_id=call.tool_id,
                    phase=call.phase,
                    invocation_id=self._text(response.get("invocation_id")),
                    attempt_id=self._text(response.get("attempt_id")),
                    status=status,
                    outcome_known=known,
                    response=response,
                    error=response.get("error") if isinstance(response.get("error"), dict) else None,
                )
            except Exception as exc:
                receipt = ToolReceipt(
                    sequence_index=index,
                    tool_id=call.tool_id,
                    phase=call.phase,
                    status="unknown",
                    outcome_known=False,
                    error={"code": "internal_tool_error", "message": str(exc)},
                )
                receipts.append(receipt)
                return self._result(
                    spec, receipts, completed, context, "outcome_unknown", False,
                    call.phase, "reconcile_before_retry",
                )
            receipts.append(receipt)
            try:
                if call.tool_id == "manipulation.prepare" and status == "available":
                    prepared_arguments = self._prepared_arguments(spec, response, context)
                    if context.trusted_intent is not None:
                        self._persist_assignment(response)
                elif call.phase == "prepare" and status == "available":
                    prepared = response.get("arguments")
                    prepared_arguments = (
                        dict(prepared) if isinstance(prepared, Mapping)
                        else context.prepared_arguments
                    )
                else:
                    prepared_arguments = context.prepared_arguments
            except Exception:
                return self._result(
                    spec, receipts, completed, context, "failed", True,
                    call.phase, "subtask_failed",
                )
            context = SubtaskExecutionContext(
                possession_state=self._possession(response, context.possession_state),
                scene_revision=self._scene_revision(response, context.scene_revision),
                last_response=response,
                trusted_intent=context.trusted_intent,
                prepared_arguments=prepared_arguments,
            )
            if not known or status == "unknown":
                return self._result(spec, receipts, completed, context, "outcome_unknown", False, call.phase, "reconcile_before_retry")
            if status in {"failed", "cancelled", "stopped"}:
                final_status: SubtaskStatus = "cancelled" if status == "cancelled" else "failed"
                return self._result(spec, receipts, completed, context, final_status, True, call.phase, "subtask_failed")
            if status not in {"succeeded", "available"}:
                return self._result(spec, receipts, completed, context, "failed", True, call.phase, "subtask_failed")
            completed.append(call.tool_id)
        return self._result(spec, receipts, completed, context, "completed", True, None, "continue_next_subtask")

    def _invoke(self, tool_id: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if callable(self._invoker):
            return self._invoker(tool_id, arguments)
        return self._invoker.invoke(tool_id, arguments)

    def _persist_assignment(self, response: Mapping[str, Any]) -> None:
        _persist_assignment_artifact(self._assignment_store, response)

    @staticmethod
    def _prepared_arguments(
        spec: SubtaskSpec,
        response: Mapping[str, Any],
        context: SubtaskExecutionContext,
    ) -> dict[str, Any]:
        """Use the same preparation contract in synchronous and Runtime paths."""
        return RuntimeSubtaskDriver._prepared_arguments(spec, response, context)

    @staticmethod
    def _arguments(spec: SubtaskSpec, call: SubtaskToolCall, context: SubtaskExecutionContext) -> dict[str, Any]:
        binding = spec.binding.model_dump(mode="json")
        binding.pop("max_age_ms", None)
        if call.tool_id == "manipulation.prepare":
            request = {
                key: binding[key]
                for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref",
                            "freshness_ms", "max_age_ms", "candidate_set_ref", "capability_snapshot_ref",
                            "destination_ref", "binding_ref")
                if binding.get(key) is not None
            }
            request["candidates"] = [dict(binding["grasp_candidate"])]
            request["perception_binding"] = dict(binding)
            request["process_type"] = spec.operation
            if context.trusted_intent is not None:
                request["intent"] = dict(context.trusted_intent)
            return request
        if context.prepared_arguments is not None:
            binding.update(context.prepared_arguments)
        binding.update(spec.parameters)
        binding.update(call.arguments)
        binding.setdefault("entity_ref", spec.binding.entity_ref)
        binding.setdefault("destination_ref", spec.binding.destination_ref)
        binding.setdefault("scene_revision", context.scene_revision or spec.binding.scene_revision)
        if spec.return_destination_ref is not None:
            binding.setdefault("return_destination_ref", spec.return_destination_ref)
        return binding

    @staticmethod
    def _runtime_arguments(spec: SubtaskSpec, call: SubtaskToolCall, context: SubtaskExecutionContext) -> dict[str, Any]:
        """Project a binding into the exact existing Runtime Tool input surface."""
        binding = spec.binding.model_dump(mode="json")
        common = {
            key: binding[key]
            for key in ("entity_ref", "destination_ref", "observation_ref", "scene_revision",
                        "frame_id", "calibration_ref", "capability_snapshot_ref",
                        "freshness_ms", "max_age_ms")
        }
        common["scene_revision"] = context.scene_revision or spec.binding.scene_revision
        if call.tool_id == "manipulation.prepare":
            request = {
                key: binding[key]
                for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref",
                            "freshness_ms", "max_age_ms", "candidate_set_ref", "capability_snapshot_ref",
                            "destination_ref", "binding_ref")
            }
            request["candidates"] = [dict(binding["grasp_candidate"])]
            request["perception_binding"] = dict(binding)
            request["process_type"] = spec.operation
            if context.trusted_intent is not None:
                request["intent"] = dict(context.trusted_intent)
            return request
        if context.prepared_arguments is not None:
            common.update(context.prepared_arguments)
        previous = context.last_response or {}
        previous_invocation = previous.get("invocation_id")
        if call.tool_id in {"object.acquire", "object.place"}:
            common.update({
                key: context.prepared_arguments[key]
                for key in ("candidate_set_ref", "preparation_ref", "candidate_ref", "assignment_ref")
                if context.prepared_arguments is not None and key in context.prepared_arguments
            })
        if context.acquire_invocation_ref:
            common["acquire_invocation_ref"] = context.acquire_invocation_ref
        if isinstance(previous_invocation, str) and previous_invocation:
            common.setdefault("acquire_invocation_ref", previous.get("acquire_invocation_ref", previous_invocation))
            common["held_invocation_ref"] = previous_invocation
        if call.tool_id == "object.acquire":
            return {
                **common,
            }
        common.update(call.arguments)
        if call.tool_id == "manipulation.prepare_held":
            common["parameters"] = dict(spec.parameters) if call.arguments.get("operation") != "place" else {}
            common["operation"] = call.arguments["operation"]
        return common

    @staticmethod
    def _status(call: SubtaskToolCall, response: Mapping[str, Any]) -> tuple[str, bool]:
        status = response.get("status")
        if not isinstance(status, str):
            raise SubtaskExecutionError(f"{call.tool_id} result lacks status")
        if call.phase == "prepare" and status == "available":
            return status, True
        known = response.get("outcome_known")
        if not isinstance(known, bool):
            raise SubtaskExecutionError(f"{call.tool_id} result lacks outcome_known")
        return status, known

    @staticmethod
    def _possession(response: Mapping[str, Any], current: str) -> str:
        value = response.get("possession_state")
        return value if value in {"empty", "holding", "uncertain"} else current

    @staticmethod
    def _scene_revision(response: Mapping[str, Any], current: str | None) -> str | None:
        for key in ("new_scene_revision", "scene_revision", "current_scene_revision"):
            value = response.get(key)
            if isinstance(value, str) and value:
                return value
        return current

    @staticmethod
    def _text(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _result(
        spec: SubtaskSpec,
        receipts: list[ToolReceipt],
        completed: list[str],
        context: SubtaskExecutionContext,
        status: SubtaskStatus,
        known: bool,
        failed_phase: str | None,
        recommended_action: str,
    ) -> SubtaskExecutionResult:
        failure_code = None if status == "completed" else (
            "subtask_outcome_unknown" if status == "outcome_unknown" else
            "subtask_cancelled" if status == "cancelled" else "subtask_failed"
        )
        return SubtaskExecutionResult(
            subtask_id=spec.subtask_id,
            status=status,
            outcome_known=known,
            completed_tool_ids=tuple(completed),
            receipts=tuple(receipts),
            failed_phase=failed_phase,
            failure_code=failure_code,
            possession_state=(context.possession_state if context.possession_state in {"empty", "holding", "uncertain"} else "uncertain"),
            scene_revision=context.scene_revision,
            recommended_action=recommended_action,
        )


class RuntimeSubtaskDriver:
    """Non-blocking ActionDriver over the existing CapabilityRuntime.

    The driver advances at most one internal Tool lifecycle step per ``poll``.
    It never calls a provider or simulator directly and keeps the outer Action
    invocation as the sole Agent-facing lifecycle.
    """

    def __init__(
        self,
        runtime: CapabilityRuntime,
        spec: SubtaskSpec,
        caller_id: str,
        refresh_binding: Callable[[PerceptionBinding, str], PerceptionBinding] | None = None,
        assignment_store=None,
    ) -> None:
        self.runtime = runtime
        self.spec = spec
        self.caller_id = caller_id
        self.refresh_binding = refresh_binding
        self.assignment_store = assignment_store
        self.index = 0
        self.active_invocation: str | None = None
        self.active_tool: SubtaskToolCall | None = None
        self.context = SubtaskExecutionContext(
            scene_revision=spec.binding.scene_revision,
            trusted_intent=spec.trusted_intent,
        )
        self.receipts: list[ToolReceipt] = []
        self.completed: list[str] = []
        self.next_arguments: dict[str, Any] | None = None
        self.cancel_requested = False
        self.terminal: dict[str, Any] | None = None

    def poll(self) -> Mapping[str, Any] | None:
        if self.terminal is not None:
            return self.terminal
        if self.cancel_requested and self.active_invocation is None:
            return self._finish("cancelled", False, "cancelled_before_next_tool", "cancelled")
        calls = self.spec.calls()
        if self.active_invocation is not None:
            result = self.runtime.invocation_result(self.active_invocation)
            if result.get("status") == "pending":
                return None
            return self._consume(self.active_tool, result)
        if self.index >= len(calls):
            return self._finish("completed", True, None, "continue_next_subtask")
        call = calls[self.index]
        if self.context.scene_revision != self.spec.binding.scene_revision:
            if self.refresh_binding is None:
                return self._finish(
                    "outcome_unknown", False, call.phase, "refresh_perception_before_motion",
                    error="scene_revision_changed_without_fresh_perception",
                )
            try:
                refreshed = self.refresh_binding(self.spec.binding, self.context.scene_revision or "")
                refreshed = PerceptionBinding.model_validate(refreshed)
                self._validate_refresh_binding(
                    refreshed, self.spec.binding, self.context.scene_revision,
                )
                self.spec = self.spec.model_copy(update={"binding": refreshed})
            except Exception as exc:
                return self._finish(
                    "outcome_unknown", False, call.phase, "refresh_perception_before_motion",
                    error=str(exc),
                )
        arguments = self.next_arguments or SubtaskExecutor._runtime_arguments(self.spec, call, self.context)
        try:
            if call.phase == "prepare":
                tool_spec = self.runtime.get_tool(call.tool_id)
                result = self.runtime.invoke_query(
                    tool_spec["endpoint_id"], tool_spec["operation"], arguments,
                )
                return self._consume(call, result)
            started = self.runtime.start_action(call.tool_id, arguments, caller_id=self.caller_id)
            self.active_invocation = started["invocation_id"]
            self.active_tool = call
            return None
        except Exception as exc:
            return self._finish("outcome_unknown", False, call.phase, "reconcile_before_retry", error=str(exc))

    def cancel(self) -> None:
        self.cancel_requested = True
        if self.active_invocation is not None:
            self.runtime.cancel_invocation(self.active_invocation)

    def stop(self) -> None:
        self.cancel()

    def _consume(self, call: SubtaskToolCall | None, raw: Mapping[str, Any]) -> Mapping[str, Any]:
        if call is None:
            return self._finish("outcome_unknown", False, None, "reconcile_before_retry", error="missing_active_tool")
        status = raw.get("status")
        response = dict(raw.get("result", raw)) if isinstance(raw.get("result", raw), Mapping) else dict(raw)
        response.setdefault("status", status)
        response.setdefault("invocation_id", raw.get("invocation_id"))
        response.setdefault("attempt_id", raw.get("attempt_id"))
        known = response.get("outcome_known") is True
        if call.phase == "prepare" and status == "available":
            known = True
        receipt = ToolReceipt(
            sequence_index=self.index, tool_id=call.tool_id, phase=call.phase,
            invocation_id=self._text(raw.get("invocation_id") or response.get("invocation_id")),
            attempt_id=self._text(raw.get("attempt_id") or response.get("attempt_id")),
            status=str(status or "unknown"), outcome_known=known, response=response,
            error=response.get("error") if isinstance(response.get("error"), dict) else None,
        )
        self.receipts.append(receipt)
        self.active_invocation = None
        self.active_tool = None
        try:
            prepared_arguments = (
                self._prepared_arguments(self.spec, response, self.context)
                if call.tool_id == "manipulation.prepare" and status == "available"
                else self.context.prepared_arguments
            )
            if call.tool_id == "manipulation.prepare" and status == "available" and self.context.trusted_intent is not None:
                self._persist_assignment(response)
        except Exception as exc:
            return self._finish(
                "outcome_unknown", False, call.phase, "reconcile_before_retry", error=str(exc)
            )
        self.context = SubtaskExecutionContext(
            possession_state=SubtaskExecutor._possession(response, self.context.possession_state),
            scene_revision=SubtaskExecutor._scene_revision(response, self.context.scene_revision),
            acquire_invocation_ref=(
                self._text(raw.get("invocation_id") or response.get("invocation_id"))
                if call.phase == "acquire" else self.context.acquire_invocation_ref
            ),
            last_response=response,
            trusted_intent=self.context.trusted_intent,
            prepared_arguments=prepared_arguments,
        )
        if self.cancel_requested:
            if status == "cancelled" and known:
                return self._finish("cancelled", True, call.phase, "subtask_cancelled")
            if status in {"failed", "stopped"} and known:
                return self._finish("cancelled", True, call.phase, "subtask_cancelled")
            return self._finish("outcome_unknown", False, call.phase, "reconcile_before_retry")
        if not known or status == "unknown":
            return self._finish("outcome_unknown", False, call.phase, "reconcile_before_retry")
        if status in {"failed", "cancelled", "stopped"}:
            final = "cancelled" if status == "cancelled" else "failed"
            return self._finish(final, True, call.phase, "subtask_failed")
        if status not in {"succeeded", "available"}:
            return self._finish("failed", True, call.phase, "subtask_failed")
        if call.tool_id == "manipulation.prepare":
            self.next_arguments = None
        elif call.phase == "prepare":
            prepared = response.get("arguments")
            if not isinstance(prepared, Mapping):
                return self._finish("outcome_unknown", False, call.phase, "reconcile_before_retry", error="prepare_missing_arguments")
            self.next_arguments = dict(prepared)
        else:
            self.next_arguments = None
        self.completed.append(call.tool_id)
        self.index += 1
        return None

    @staticmethod
    def _prepared_arguments(
        spec: SubtaskSpec,
        response: Mapping[str, Any],
        context: SubtaskExecutionContext,
    ) -> dict[str, Any]:
        binding = spec.binding
        if response.get("motion_authorized") is not False:
            raise SubtaskExecutionError("manipulation.prepare must remain no-motion")
        if any(response.get(key) != expected for key, expected in (
            ("observation_ref", binding.observation_ref),
            ("scene_revision", binding.scene_revision),
            ("candidate_set_ref", binding.candidate_set_ref),
            ("calibration_ref", binding.calibration_ref),
        )):
            raise SubtaskExecutionError("manipulation.prepare changed observation provenance")
        frame = response.get("frame")
        if not isinstance(frame, Mapping) or frame.get("frame_id") != binding.frame_id:
            raise SubtaskExecutionError("manipulation.prepare changed frame provenance")
        prepared = response.get("prepared_candidates")
        selected = [
            item for item in prepared if isinstance(item, Mapping)
            and item.get("candidate_ref") == binding.candidate_ref
            and item.get("entity_ref") == binding.entity_ref
            and item.get("qualification") == "prepared"
        ] if isinstance(prepared, list) else []
        if len(selected) != 1:
            raise SubtaskExecutionError("manipulation.prepare did not qualify the selected candidate")
        checks = selected[0].get("checks")
        if not isinstance(checks, Mapping) or any(
            checks.get(key) != "pass" for key in ("kinematic", "collision", "workspace")
        ):
            raise SubtaskExecutionError("manipulation.prepare candidate checks are incomplete")
        preparation_ref = response.get("preparation_ref")
        if not isinstance(preparation_ref, str) or not preparation_ref.startswith("preparation://"):
            raise SubtaskExecutionError("manipulation.prepare returned no preparation reference")
        result = {
            "candidate_set_ref": binding.candidate_set_ref,
            "preparation_ref": preparation_ref,
            "candidate_ref": binding.candidate_ref,
            "entity_ref": binding.entity_ref,
            "capability_snapshot_ref": binding.capability_snapshot_ref,
        }
        intent = context.trusted_intent
        if intent is not None:
            assignments = response.get("assignments")
            if not isinstance(assignments, list) or len(assignments) != 1:
                raise SubtaskExecutionError("manipulation.prepare returned no unique task assignment")
            assignment = assignments[0]
            if not isinstance(assignment, Mapping) or any(
                assignment.get(key) != intent.get(key)
                for key in ("task_id", "revision_id", "node_id", "node_digest", "entity_ref",
                            "observation_ref", "scene_revision", "calibration_ref", "candidate_set_ref")
            ) or assignment.get("candidate_ref") != binding.candidate_ref:
                raise SubtaskExecutionError("manipulation.prepare assignment differs from trusted intent")
            if assignment.get("capability_snapshot_ref") != binding.capability_snapshot_ref:
                raise SubtaskExecutionError("manipulation.prepare assignment changed capability provenance")
            if response.get("destination_ref") != binding.destination_ref:
                raise SubtaskExecutionError("manipulation.prepare assignment changed destination")
            result["assignment_ref"] = assignment.get("assignment_ref")
            if not isinstance(result["assignment_ref"], str) or not result["assignment_ref"].startswith("artifact://"):
                raise SubtaskExecutionError("manipulation.prepare returned an invalid assignment reference")
        return result

    def _persist_assignment(self, response: Mapping[str, Any]) -> None:
        _persist_assignment_artifact(self.assignment_store, response)

    def _finish(self, status: str, known: bool, failed_phase: str | None, action: str, *, error: str | None = None) -> Mapping[str, Any]:
        result = SubtaskExecutor._result(
            self.spec, self.receipts, self.completed, self.context,
            status, known, failed_phase, action,
        ).model_dump(mode="json")
        if error is not None:
            result["error"] = {"code": "runtime_subtask_driver_error", "message": error}
        evidence_refs = list(result.get("evidence_refs", []))
        for receipt in self.receipts:
            for ref in receipt.response.get("evidence_refs", ()):
                if isinstance(ref, str) and ref.startswith("artifact://") and ref not in evidence_refs:
                    evidence_refs.append(ref)
        runtime_status = {"completed": "succeeded", "outcome_unknown": "unknown"}.get(status, status)
        summary = {
            "version": "capability_outcome_summary_v1",
            "status": runtime_status,
            "failure_owner": "execution" if runtime_status != "succeeded" else "none",
            "failure_code": result.get("failure_code"),
            "world_change_started": any(item.response.get("world_change_started") is True for item in self.receipts),
            "outcome_known": known,
            "evidence_availability": "complete" if evidence_refs and known and runtime_status == "succeeded" else "partial" if evidence_refs else "none",
            "artifact_refs": evidence_refs,
            "retryable_in_revision": False,
            "requires_replan": runtime_status == "unknown",
            "recommended_action": action,
            "phase": failed_phase or "none",
        }
        self.terminal = {
            "status": runtime_status,
            "outcome_known": known,
            "subtask_result": result,
            "capability_outcome_summary": summary,
            "possession_state": result["possession_state"],
            "new_scene_revision": result["scene_revision"],
            "evidence_refs": evidence_refs,
            "world_change_started": any(item.response.get("world_change_started") is True for item in self.receipts),
        }
        return self.terminal

    @staticmethod
    def _text(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _validate_refresh_binding(
        refreshed: PerceptionBinding,
        previous: PerceptionBinding,
        expected_revision: str | None,
    ) -> None:
        """Reject a new revision carrying old motion candidate artifacts."""
        if (
            refreshed.entity_ref != previous.entity_ref
            or refreshed.destination_ref != previous.destination_ref
            or refreshed.scene_revision != expected_revision
            or refreshed.calibration_ref != previous.calibration_ref
            or refreshed.frame_id != previous.frame_id
            or refreshed.binding_ref == previous.binding_ref
        ):
            raise ValueError(
                "refreshed perception changed subtask identity, frame, revision, or calibration binding"
            )
        if refreshed.observation_ref == previous.observation_ref:
            raise ValueError("refreshed perception must provide a new observation reference")
        for field_name in ("candidate_set_ref", "candidate_ref"):
            if getattr(refreshed, field_name) == getattr(previous, field_name):
                raise ValueError(f"refreshed perception reused stale {field_name}")


class SubtaskActionEndpoint:
    """Action endpoint that delegates all internal execution to CapabilityRuntime."""

    def __init__(
        self,
        runtime: CapabilityRuntime,
        refresh_binding: Callable[[PerceptionBinding, str], PerceptionBinding] | None = None,
        resolve_context: SubtaskContextResolver | None = None,
        assignment_store=None,
    ) -> None:
        self.runtime = runtime
        self.refresh_binding = refresh_binding
        self.resolve_context = resolve_context
        self.assignment_store = assignment_store

    def admit(self, arguments: Mapping[str, Any]) -> ActionAdmission:
        raise ValueError("subtask Action requires a task-owned caller")

    def admit_for_caller(self, arguments: Mapping[str, Any], *, caller_id: str) -> ActionAdmission:
        spec_payload = dict(arguments)
        trusted_intent = spec_payload.pop("intent", None)
        semantic = spec_payload.pop("semantic_intent", None)
        if isinstance(trusted_intent, Mapping):
            spec_payload["trusted_intent"] = dict(trusted_intent)
            spec_payload["semantic_intent"] = semantic or {
                key: trusted_intent[key]
                for key in ("goal", "success_criteria", "allowed_arms", "coordination_mode", "constraints")
                if key in trusted_intent
            }
        spec = SubtaskSpec.model_validate(spec_payload)
        if not isinstance(caller_id, str) or not caller_id.startswith("paos:"):
            raise ValueError("subtask Action caller must be bound to a PAOS task")
        if not callable(self.resolve_context):
            raise ValueError("subtask Action requires a Coordinator context resolver")
        context = self.resolve_context(caller_id)
        if not isinstance(context, Mapping):
            raise ValueError("Coordinator context resolver returned a non-object")
        required = (
            "task_id", "revision_id", "node_id", "node_digest", "obligation_id",
            "input_binding_digest", "decision_trace_ref", "planning_binding", "intent",
        )
        if any(key not in context for key in required):
            raise ValueError("Coordinator context is incomplete for subtask admission")
        if context["node_id"] != spec.subtask_id:
            raise ValueError("subtask id does not match the Coordinator PlanNode")
        planning_binding = context["planning_binding"]
        if not isinstance(planning_binding, Mapping):
            raise ValueError("Coordinator context has no planning binding")
        for key in (
            "revision_id", "node_id", "node_digest", "obligation_id",
            "input_binding_digest", "decision_trace_ref",
        ):
            if planning_binding.get(key) != context.get(key):
                raise ValueError(f"Coordinator planning binding {key} does not match the caller")
        intent = context["intent"]
        if not isinstance(intent, Mapping):
            raise ValueError("Coordinator context has no trusted manipulation intent")
        if intent.get("motion_authorized") is not False:
            raise ValueError("Coordinator manipulation intent must remain no-motion")
        for key in ("task_id", "revision_id", "node_id", "node_digest"):
            if intent.get(key) != context[key]:
                raise ValueError(f"Coordinator manipulation intent {key} does not match the caller")
        binding = spec.binding
        for key, expected in (
            ("entity_ref", binding.entity_ref),
            ("observation_ref", binding.observation_ref),
            ("scene_revision", binding.scene_revision),
            ("observation_frame_id", binding.frame_id),
            ("calibration_ref", binding.calibration_ref),
            ("candidate_set_ref", binding.candidate_set_ref),
        ):
            if intent.get(key) != expected:
                raise ValueError(f"Coordinator intent {key} does not match the perception binding")
        if isinstance(trusted_intent, Mapping) and dict(trusted_intent) != dict(intent):
            raise ValueError("subtask Action must carry the persisted Coordinator intent")
        if trusted_intent is None and all(
            key in intent for key in ("goal", "success_criteria", "allowed_arms", "coordination_mode")
        ):
            raise ValueError("subtask Action must carry the persisted Coordinator intent")
        if spec.semantic_intent is not None:
            for key in ("goal", "success_criteria", "allowed_arms", "coordination_mode", "constraints"):
                expected = spec.semantic_intent.get(key, [] if key in {"success_criteria", "allowed_arms", "constraints"} else None)
                if intent.get(key) != expected:
                    raise ValueError(f"subtask semantic intent {key} does not match the Coordinator intent")

        def start(_invocation_id: str, _attempt_id: str) -> ActionAdmission:
            driver = RuntimeSubtaskDriver(
                self.runtime,
                spec,
                caller_id,
                self.refresh_binding,
                self.assignment_store,
            )
            return ActionAdmission(
                terminal_result={"status": "unknown", "outcome_known": False},
                driver=driver,
            )

        return ActionAdmission(start=start, terminal_result={"status": "unknown", "outcome_known": False})


SUBTASK_TOOL_SPEC: dict[str, Any] = {
    "tool_id": "manipulation.execute_subtask",
    "endpoint_id": "subtask_execution",
    "operation": "execute",
    "semantics": "action",
    "description": "Execute one observation-bound manipulation subtask through its internal PAOS Tool sequence.",
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "capabilities": ["manipulation.execute_subtask"],
        "input_binding_keys": ["subtask_id", "operation", "binding", "parameters", "tool_sequence"],
        "trusted_argument_builder": "manipulation_intent_v2",
        "scene_write_behavior": "new_revision",
        "idempotency": "at_most_once",
    },
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["subtask_id", "operation", "binding", "parameters", "tool_sequence", "intent"],
        "properties": {
            "subtask_id": {"type": "string", "minLength": 1},
            "operation": {"enum": ["relocate", "pour", "stir"]},
            "depends_on": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "binding": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "entity_ref", "semantic_label", "category", "destination_semantic_label",
                    "destination_category", "measured_pose",
                    "measured_geometry", "grasp_candidate", "grasp_candidate_ref", "candidate_set_ref",
                    "candidate_ref", "capability_snapshot_ref", "binding_ref", "destination_ref",
                    "destination_pose", "process_frame", "observation_ref", "scene_revision",
                    "frame_id", "calibration_ref", "freshness_ms", "max_age_ms",
                    "confidence", "provenance",
                ],
                "properties": {
                    "entity_ref": {"type": "string", "pattern": r"^entity://[^/]+$"},
                    "semantic_label": {"type": "string", "minLength": 1},
                    "category": {"type": "string", "minLength": 1},
                    "destination_semantic_label": {"type": "string", "minLength": 1},
                    "destination_category": {"type": "string", "minLength": 1},
                    "measured_pose": {"type": "object"},
                    "measured_geometry": {"type": "object"},
                    "grasp_candidate": {"type": "object"},
                    "grasp_candidate_ref": {"type": "string", "pattern": r"^candidate-set://\S+$"},
                    "candidate_set_ref": {"type": "string", "pattern": r"^candidate-set://\S+$"},
                    "candidate_ref": {"type": "string", "pattern": r"^candidate://\S+$"},
                    "capability_snapshot_ref": {"type": "string", "pattern": r"^artifact://\S+$"},
                    "binding_ref": {"type": "string", "pattern": r"^artifact://\S+$"},
                    "destination_ref": {"type": "string", "pattern": r"^(?:destination|container)://\S+$"},
                    "destination_pose": {"type": "object"},
                    "process_frame": {"type": "string", "minLength": 1},
                    "observation_ref": {"type": "string", "pattern": r"^observation://\S+$"},
                    "scene_revision": {"type": "string", "minLength": 1},
                    "frame_id": {"type": "string", "minLength": 1},
                    "calibration_ref": {"type": "string", "pattern": r"^artifact://\S+$"},
                    "freshness_ms": {"type": "integer", "minimum": 0},
                    "max_age_ms": {"type": "integer", "exclusiveMinimum": 0},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "provenance": {"type": "string", "minLength": 1},
                },
            },
            "parameters": {"type": "object"},
            "tool_sequence": {"type": "array", "minItems": 2, "items": {"type": "object"}},
            "intent": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "version", "task_id", "revision_id", "node_id", "node_digest",
                    "entity_ref", "goal", "success_criteria", "allowed_arms",
                    "coordination_mode", "observation_ref", "scene_revision",
                    "observation_frame_id", "calibration_ref", "candidate_set_ref",
                    "motion_authorized",
                ],
                "properties": {
                    "version": {"const": "manipulation_intent_v2"},
                    "task_id": {"type": "string", "minLength": 1},
                    "revision_id": {"type": "string", "minLength": 1},
                    "node_id": {"type": "string", "minLength": 1},
                    "node_digest": {"type": "string", "pattern": r"^[0-9a-f]{64}$"},
                    "entity_ref": {"type": "string", "pattern": r"^entity://\S+$"},
                    "goal": {"type": "string", "minLength": 1},
                    "success_criteria": {"type": "array", "items": {"type": "string"}},
                    "allowed_arms": {"type": "array", "items": {"type": "string"}},
                    "coordination_mode": {"enum": ["single_arm", "alternative_arm", "bimanual"]},
                    "observation_ref": {"type": "string", "pattern": r"^observation://\S+$"},
                    "scene_revision": {"type": "string", "minLength": 1},
                    "observation_frame_id": {"type": "string", "minLength": 1},
                    "calibration_ref": {"type": "string", "pattern": r"^artifact://\S+$"},
                    "candidate_set_ref": {"type": "string", "pattern": r"^candidate-set://\S+$"},
                    "constraints": {"type": "array", "items": {"type": "string"}},
                    "motion_authorized": {"const": False},
                },
            },
            "return_destination_ref": {"type": ["string", "null"], "minLength": 1},
        },
    },
    "output_schema": {
        "type": "object",
        "required": ["invocation_id", "attempt_id", "status", "result"],
        "properties": {
            "invocation_id": {"type": "string", "minLength": 1},
            "attempt_id": {"type": "string", "minLength": 1},
            "status": {"enum": ["succeeded", "failed", "cancelled", "stopped", "unknown"]},
            "result": {"type": "object"},
        },
    },
}


__all__ = [
    "PerceptionBinding", "SubtaskExecutionContext", "SubtaskExecutionError",
    "SubtaskExecutionResult", "SubtaskExecutor", "SubtaskInvoker", "SubtaskSpec",
    "SubtaskToolCall", "SUBTASK_TOOL_SPEC", "ToolReceipt", "default_subtask_calls",
    "RuntimeSubtaskDriver", "SubtaskActionEndpoint",
    "SubtaskContextResolver",
]
