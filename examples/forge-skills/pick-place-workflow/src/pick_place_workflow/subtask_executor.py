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
    measured_pose: Mapping[str, Any]
    measured_geometry: Mapping[str, Any]
    grasp_candidate_ref: str
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

    @model_validator(mode="after")
    def fresh_and_finite(self) -> "PerceptionBinding":
        if self.freshness_ms > self.max_age_ms:
            raise ValueError("perception binding is stale")
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
            SubtaskToolCall(tool_id="object.acquire", phase="acquire"),
            SubtaskToolCall(tool_id="object.place", phase="place"),
        )
    return (
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

    @model_validator(mode="after")
    def sequence_shape(self) -> "SubtaskSpec":
        calls = self.tool_sequence or default_subtask_calls(self.operation)
        expected_calls = default_subtask_calls(self.operation)
        if calls != expected_calls:
            raise ValueError("tool_sequence must follow the governed acquire/prepare/process/place sequence")
        if not calls:
            raise ValueError("subtask requires at least one internal Tool")
        if calls[0].tool_id != "object.acquire" or calls[0].phase != "acquire":
            raise ValueError("subtask must begin with object.acquire")
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
        return self

    def calls(self) -> tuple[SubtaskToolCall, ...]:
        return self.tool_sequence or default_subtask_calls(self.operation)


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
    last_response: Mapping[str, Any] | None = None


class SubtaskExecutor:
    """Execute one finite subtask without opening another Agent model turn."""

    def __init__(
        self,
        invoker: SubtaskInvoker | Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
        *,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> None:
        self._invoker = invoker
        self._cancel_requested = cancel_requested or (lambda: False)

    def execute(self, spec: SubtaskSpec) -> SubtaskExecutionResult:
        receipts: list[ToolReceipt] = []
        completed: list[str] = []
        context = SubtaskExecutionContext(scene_revision=spec.binding.scene_revision)
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
            context = SubtaskExecutionContext(
                possession_state=self._possession(response, context.possession_state),
                scene_revision=self._scene_revision(response, context.scene_revision),
                last_response=response,
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

    @staticmethod
    def _arguments(spec: SubtaskSpec, call: SubtaskToolCall, context: SubtaskExecutionContext) -> dict[str, Any]:
        binding = spec.binding.model_dump(mode="json")
        binding.pop("max_age_ms", None)
        binding.update(spec.parameters)
        binding.update(call.arguments)
        binding.setdefault("entity_ref", spec.binding.entity_ref)
        binding.setdefault("destination_ref", spec.binding.destination_ref)
        binding.setdefault("scene_revision", context.scene_revision or spec.binding.scene_revision)
        if spec.return_destination_ref is not None:
            binding.setdefault("return_destination_ref", spec.return_destination_ref)
        return binding

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


SUBTASK_TOOL_SPEC: dict[str, Any] = {
    "tool_id": "manipulation.execute_subtask",
    "endpoint_id": "subtask_execution",
    "operation": "execute",
    "semantics": "action",
    "description": "Execute one observation-bound manipulation subtask through its internal PAOS Tool sequence.",
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "capabilities": ["manipulation.execute_subtask"],
        "input_binding_keys": ["entity_ref", "destination_ref", "scene_revision", "observation_ref", "calibration_ref"],
        "scene_write_behavior": "new_revision",
        "idempotency": "at_most_once",
    },
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["subtask_id", "operation", "binding", "parameters", "tool_sequence"],
        "properties": {
            "subtask_id": {"type": "string", "minLength": 1},
            "operation": {"enum": ["relocate", "pour", "stir"]},
            "binding": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "entity_ref", "semantic_label", "category", "measured_pose",
                    "measured_geometry", "grasp_candidate_ref", "destination_ref",
                    "destination_pose", "process_frame", "observation_ref", "scene_revision",
                    "frame_id", "calibration_ref", "freshness_ms", "max_age_ms",
                    "confidence", "provenance",
                ],
                "properties": {
                    "entity_ref": {"type": "string", "pattern": r"^entity://[^/]+$"},
                    "semantic_label": {"type": "string", "minLength": 1},
                    "category": {"type": "string", "minLength": 1},
                    "measured_pose": {"type": "object"},
                    "measured_geometry": {"type": "object"},
                    "grasp_candidate_ref": {"type": "string", "pattern": r"^candidate-set://\S+$"},
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
            "return_destination_ref": {"type": "string", "minLength": 1},
        },
    },
}


__all__ = [
    "PerceptionBinding", "SubtaskExecutionContext", "SubtaskExecutionError",
    "SubtaskExecutionResult", "SubtaskExecutor", "SubtaskInvoker", "SubtaskSpec",
    "SubtaskToolCall", "SUBTASK_TOOL_SPEC", "ToolReceipt", "default_subtask_calls",
]
