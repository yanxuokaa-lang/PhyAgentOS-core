"""Provider-owned holding lifecycle, independent of PAOS and simulator imports."""

from __future__ import annotations

import json
import math
from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from threading import Event, RLock
from typing import Any, Callable, Mapping, Protocol

ACTION_RECEIPT_MAX_BYTES = 262_144
_RECEIPT_TEXT_MAX_BYTES = 2_048
_RECEIPT_REF_MAX_ITEMS = 16
_TERMINAL_FIELDS = (
    "status",
    "world_change_started",
    "outcome_known",
    "new_scene_revision",
    "source_scene_revision",
    "failure_owner",
    "failure_code",
    "error_detail",
    "stop_confirmed",
    "stop_errors",
    "continuation_valid",
    "retryable_in_revision",
    "requires_replan",
    "recommended_action",
    "phase",
    "selected_arm",
    "failed_phase",
    "release_confirmed",
    "retreat_completed",
    "clear_of_target",
    "observation_ready",
    "possession_state",
    "object_support_state",
    "video_evidence_error",
    "operation_completed",
    "process_completed",
    "return_completed",
    "returned_to_safe_pose",
    "entity_ref",
    "destination_ref",
    "return_destination_ref",
)
_ATTEMPT_FIELDS = (
    "arm",
    "status",
    "failed_phase",
    "failed_waypoint_index",
    "detail",
)
_PLACEMENT_MEASUREMENT_FIELDS = ("position_error_m", "orientation_error_rad")
_PLACEMENT_TOLERANCE_FIELDS = ("target_position_m", "target_orientation_rad")
_ACQUISITION_MEASUREMENT_FIELDS = (
    "lift_displacement_m",
    "minimum_lift_m",
    "support_clearance_m",
    "support_tolerance_m",
)
_HELD_MEASUREMENT_FIELDS = (
    "aligned_hold_s", "maximum_tilt_rad", "in_container_turns",
    "in_container_duration_s", "position_error_m", "orientation_error_rad",
    "qualified_tilt_hold_s",
)

ATOMIC_CYCLE_PHASES = (
    "acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat",
)
COMPLETE_CYCLE_OPERATIONS = frozenset({"pour_cycle", "stir_cycle", "manipulation_cycle"})


class AtomicExecutor(Protocol):
    """Provider-neutral atomic operations used inside one cycle invocation."""

    def acquire(self, arguments: Mapping[str, Any], cancel: Event, **context: Any) -> Mapping[str, Any]: ...
    def transport(self, arguments: Mapping[str, Any], cancel: Event, **context: Any) -> Mapping[str, Any]: ...
    def process(self, arguments: Mapping[str, Any], cancel: Event, **context: Any) -> Mapping[str, Any]: ...
    def reorient_exit(self, arguments: Mapping[str, Any], cancel: Event, **context: Any) -> Mapping[str, Any]: ...
    def stow(self, arguments: Mapping[str, Any], cancel: Event, **context: Any) -> Mapping[str, Any]: ...
    def release(self, arguments: Mapping[str, Any], cancel: Event, **context: Any) -> Mapping[str, Any]: ...
    def retreat(self, arguments: Mapping[str, Any], cancel: Event, **context: Any) -> Mapping[str, Any]: ...


class AtomicExecutionError(ValueError):
    """The provider-neutral atomic executor returned an invalid phase result."""


def execute_atomic_cycle(
    executor: AtomicExecutor,
    arguments: Mapping[str, Any],
    cancel: Event,
    *,
    owner: str,
    invocation_id: str,
) -> dict[str, Any]:
    """Run internal atomic operations without creating nested PAOS invocations."""
    events: list[dict[str, Any]] = []
    for phase in ATOMIC_CYCLE_PHASES:
        if cancel.is_set():
            return {
                "status": "unknown", "outcome_known": False,
                "world_change_started": bool(events), "phase_events": events,
            }
        operation = getattr(executor, phase, None)
        if not callable(operation):
            raise AtomicExecutionError(f"atomic executor lacks phase operation: {phase}")
        event = operation(
            deepcopy(dict(arguments)), cancel, owner=owner, invocation_id=invocation_id,
        )
        if not isinstance(event, Mapping):
            raise AtomicExecutionError(f"atomic phase did not return a mapping: {phase}")
        normalized = deepcopy(dict(event))
        normalized["phase"] = phase
        if normalized.get("status") not in {"completed", "failed", "unknown"}:
            raise AtomicExecutionError(f"atomic phase returned invalid status: {phase}")
        events.append(normalized)
        if normalized["status"] != "completed":
            return {
                "status": normalized["status"],
                "outcome_known": normalized.get("outcome_known") is True,
                "world_change_started": True,
                "phase_events": events,
                "failed_phase": phase,
                "possession_state": normalized.get("possession_state", "uncertain"),
            }
    process_facts = events[2].get("facts", {})
    process_qualified = process_facts.get("process_measurement_qualified") is True
    all_known = all(event.get("outcome_known") is True for event in events)
    if not all_known:
        return {
            "status": "unknown", "outcome_known": False,
            "world_change_started": True, "phase_events": events,
            "failed_phase": None, "possession_state": "uncertain",
        }
    return {
        "status": "succeeded" if process_qualified else "failed",
        "outcome_known": True,
        "world_change_started": True, "phase_events": events,
        "failed_phase": None if process_qualified else "process",
        "possession_state": "empty" if process_qualified else "holding",
    }


class NoMotionAtomicExecutor:
    """Reference executor for control-flow tests; it never commands a device."""

    def __init__(self, *, fail_phase: str | None = None) -> None:
        if fail_phase is not None and fail_phase not in ATOMIC_CYCLE_PHASES:
            raise ValueError("unknown no-motion failure phase")
        self.fail_phase = fail_phase
        self.calls: list[str] = []
        self._clock_s = 0.0

    def _run(self, phase: str, cancel: Event) -> dict[str, Any]:
        self.calls.append(phase)
        started = self._clock_s
        self._clock_s += 1.0
        if cancel.is_set():
            return {"status": "unknown", "outcome_known": False,
                    "started_at_s": started, "completed_at_s": self._clock_s}
        if phase == self.fail_phase:
            return {"status": "failed", "outcome_known": True,
                    "started_at_s": started, "completed_at_s": self._clock_s,
                    "facts": {"failure_observed": True}, "possession_state": "uncertain"}
        facts: dict[str, Any] = {"phase_observed": True}
        if phase == "process":
            # A no-motion fixture cannot qualify a physical process.
            facts["process_measurement_qualified"] = False
        return {"status": "completed", "outcome_known": False,
                "started_at_s": started, "completed_at_s": self._clock_s,
                "facts": facts}

    def acquire(self, arguments, cancel, **context):
        del arguments, context
        return self._run("acquire", cancel)

    def transport(self, arguments, cancel, **context):
        del arguments, context
        return self._run("transport", cancel)

    def process(self, arguments, cancel, **context):
        del arguments, context
        return self._run("process", cancel)

    def reorient_exit(self, arguments, cancel, **context):
        del arguments, context
        return self._run("reorient_exit", cancel)

    def stow(self, arguments, cancel, **context):
        del arguments, context
        return self._run("stow", cancel)

    def release(self, arguments, cancel, **context):
        del arguments, context
        return self._run("release", cancel)

    def retreat(self, arguments, cancel, **context):
        del arguments, context
        return self._run("retreat", cancel)


def _acquisition_postcondition_is_valid(receipt: Mapping[str, Any]) -> bool:
    """Validate the measured proof required for a known empty acquire failure."""

    measurement = receipt.get("acquisition_measurement")
    if not isinstance(measurement, Mapping) or set(measurement) != set(
        _ACQUISITION_MEASUREMENT_FIELDS
    ):
        return False
    lift_displacement = float(measurement["lift_displacement_m"])
    minimum_lift = float(measurement["minimum_lift_m"])
    support_clearance = float(measurement["support_clearance_m"])
    support_tolerance = float(measurement["support_tolerance_m"])
    return (
        receipt.get("status") == "failed"
        and receipt.get("outcome_known") is True
        and receipt.get("world_change_started") is True
        and receipt.get("failure_owner") == "execution_verification"
        and receipt.get("possession_state") == "empty"
        and receipt.get("object_support_state") == "on_support"
        and minimum_lift > 0
        and support_tolerance >= 0
        and lift_displacement < minimum_lift
        and abs(support_clearance) <= support_tolerance
    )


def _json_size(value: Mapping[str, Any]) -> int:
    return len(
        json.dumps(
            value, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
    )


def _bounded_text(value: Any) -> Any:
    if not isinstance(value, str):
        return deepcopy(value)
    encoded = value.encode("utf-8")
    if len(encoded) <= _RECEIPT_TEXT_MAX_BYTES:
        return value
    return encoded[:_RECEIPT_TEXT_MAX_BYTES].decode("utf-8", errors="ignore")


def _bounded_refs(value: Any) -> list[str]:
    return _project_refs(value)[0]


def _project_refs(value: Any) -> tuple[list[str], bool]:
    if not isinstance(value, (list, tuple)):
        return [], value is not None
    refs = []
    truncated = len(value) > _RECEIPT_REF_MAX_ITEMS
    for item in value[:_RECEIPT_REF_MAX_ITEMS]:
        if not isinstance(item, str) or not item:
            truncated = True
            continue
        if len(item.encode("utf-8")) > _RECEIPT_TEXT_MAX_BYTES:
            truncated = True
            continue
        refs.append(item)
    return refs, truncated


def _project_terminal_value(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        bounded = _bounded_text(value)
        return bounded, bounded != value
    if value is None or isinstance(value, (bool, int)):
        return value, False
    if isinstance(value, float):
        return (value, False) if value == value and abs(value) != float("inf") else (None, True)
    return None, True


def _fail_closed_scene_effects(value: Mapping[str, Any]) -> dict[str, Any]:
    """Retain scene lineage but disable carry-forward when an effect record is oversized."""

    def scene_revision(key: str) -> str | None:
        revision = value.get(key)
        if not isinstance(revision, str):
            return None
        bounded = _bounded_text(revision)
        return bounded if len(revision.encode("utf-8")) <= _RECEIPT_TEXT_MAX_BYTES else None

    return {
        "schema_version": "paos-scene-effects/v1",
        "source_scene_revision": scene_revision("source_scene_revision"),
        "new_scene_revision": scene_revision("new_scene_revision"),
        "changed_entity_refs": [],
        "unaffected_entity_refs": [],
        "changed_resources": [],
        "effect_evidence_refs": _bounded_refs(value.get("effect_evidence_refs")),
        "effect_scope_complete": False,
        "carry_forward_authorized": False,
    }


def bounded_action_receipt(result: Mapping[str, Any]) -> dict[str, Any]:
    """Project one provider result into the bounded cross-process Action contract.

    Engines retain complete planner, trajectory, contact, and controller diagnostics
    in their Action artifact. The persistent provider sends only lifecycle facts,
    evidence references, conservative scene effects, and bounded arm summaries to
    the Gateway.
    """

    receipt = {}
    truncated = False
    for key in _TERMINAL_FIELDS:
        if key not in result:
            continue
        if key == "stop_errors":
            receipt[key], field_truncated = _project_refs(result[key])
        else:
            receipt[key], field_truncated = _project_terminal_value(result[key])
        truncated = truncated or field_truncated
        if field_truncated and receipt[key] is None:
            receipt.pop(key)
    receipt["artifact_refs"], refs_truncated = _project_refs(result.get("artifact_refs"))
    truncated = truncated or refs_truncated
    measurement = result.get("placement_measurement")
    if isinstance(measurement, Mapping):
        projected_measurement = {
            field: measurement[field]
            for field in _PLACEMENT_MEASUREMENT_FIELDS
            if (
                field in measurement
                and not isinstance(measurement[field], bool)
                and isinstance(measurement[field], (int, float))
                and math.isfinite(float(measurement[field]))
                and float(measurement[field]) >= 0
            )
        }
        if projected_measurement:
            receipt["placement_measurement"] = projected_measurement
    tolerance = result.get("placement_tolerance")
    if isinstance(tolerance, Mapping):
        projected_tolerance = {
            field: tolerance[field]
            for field in _PLACEMENT_TOLERANCE_FIELDS
            if (
                field in tolerance
                and not isinstance(tolerance[field], bool)
                and isinstance(tolerance[field], (int, float))
                and math.isfinite(float(tolerance[field]))
                and float(tolerance[field]) > 0
            )
        }
        if projected_tolerance:
            receipt["placement_tolerance"] = projected_tolerance
    acquisition = result.get("acquisition_measurement")
    if isinstance(acquisition, Mapping):
        projected_acquisition = {
            field: acquisition[field]
            for field in _ACQUISITION_MEASUREMENT_FIELDS
            if (
                field in acquisition
                and not isinstance(acquisition[field], bool)
                and isinstance(acquisition[field], (int, float))
                and math.isfinite(float(acquisition[field]))
            )
        }
        if projected_acquisition:
            receipt["acquisition_measurement"] = projected_acquisition
    held_measurement = result.get("measurements")
    if isinstance(held_measurement, Mapping):
        receipt["measurements"] = {
            key: held_measurement[key] for key in _HELD_MEASUREMENT_FIELDS
            if key in held_measurement and not isinstance(held_measurement[key], bool)
            and isinstance(held_measurement[key], (int, float))
            and math.isfinite(held_measurement[key]) and held_measurement[key] >= 0
        }
        if isinstance(held_measurement.get("trajectory_qualified"), bool):
            receipt["measurements"]["trajectory_qualified"] = held_measurement["trajectory_qualified"]
        if held_measurement.get("direction") in {"cw", "ccw"}:
            receipt["measurements"]["direction"] = held_measurement["direction"]
    for field in (
        "phase_events", "feedback_samples", "feedback_observations",
        "feedback_source_profile", "evaluation_profile",
    ):
        if field in result:
            value = result[field]
            if field in {"phase_events", "feedback_samples", "feedback_observations"} \
                    and not isinstance(value, (list, tuple)):
                raise ValueError(f"cycle {field} must be a sequence")
            if field in {"feedback_source_profile", "evaluation_profile"} \
                    and not isinstance(value, Mapping):
                raise ValueError(f"cycle {field} must be a mapping")
            receipt[field] = deepcopy(value)
    if any(field in receipt for field in (
        "phase_events", "feedback_samples", "feedback_observations",
        "feedback_source_profile", "evaluation_profile",
    )):
        if _json_size({key: receipt[key] for key in (
            "phase_events", "feedback_samples", "feedback_observations",
            "feedback_source_profile", "evaluation_profile",
        )
                       if key in receipt}) > ACTION_RECEIPT_MAX_BYTES // 2:
            raise ValueError("cycle feedback receipt exceeds its bounded budget")
    if (
        receipt.get("failure_code") == "acquisition_postcondition_failed"
        and not _acquisition_postcondition_is_valid(receipt)
    ):
        # A malformed physical proof cannot authorize an empty gripper state.
        # Preserve the world-change fact and force normal unknown-Action
        # reconciliation instead of trusting a partial provider receipt.
        receipt.update(
            status="unknown",
            outcome_known=False,
            failure_owner="settlement",
            failure_code="invalid_acquisition_postcondition",
            retryable_in_revision=False,
            requires_replan=True,
            recommended_action="reconcile_world",
        )
        receipt.pop("possession_state", None)
        receipt.pop("object_support_state", None)
        receipt.pop("acquisition_measurement", None)
    evidence_refs = result.get("evidence_refs", receipt["artifact_refs"])
    receipt["evidence_refs"], refs_truncated = _project_refs(evidence_refs)
    truncated = truncated or refs_truncated
    effects = result.get("scene_effects")
    if isinstance(effects, Mapping):
        try:
            receipt["scene_effects"] = deepcopy(dict(effects))
            oversized_effects = _json_size(receipt) > ACTION_RECEIPT_MAX_BYTES // 2
        except (TypeError, ValueError):
            oversized_effects = True
        if oversized_effects:
            receipt["scene_effects"] = _fail_closed_scene_effects(effects)
            truncated = True

    receipt["arm_attempts"] = []
    attempts = result.get("arm_attempts")
    attempt_count = len(attempts) if isinstance(attempts, (list, tuple)) else 0
    if isinstance(attempts, (list, tuple)):
        for attempt in attempts:
            if not isinstance(attempt, Mapping):
                continue
            projected = {}
            for key in _ATTEMPT_FIELDS:
                if key not in attempt:
                    continue
                projected[key], field_truncated = _project_terminal_value(attempt[key])
                truncated = truncated or field_truncated
                if field_truncated and projected[key] is None:
                    projected.pop(key)
            if not isinstance(projected.get("arm"), str) or not isinstance(
                projected.get("status"), str
            ):
                truncated = True
                continue
            candidate = {**receipt, "arm_attempts": [*receipt["arm_attempts"], projected]}
            if _json_size(candidate) > ACTION_RECEIPT_MAX_BYTES:
                truncated = True
                break
            receipt["arm_attempts"].append(projected)
    if len(receipt["arm_attempts"]) < attempt_count:
        truncated = True
    receipt["arm_attempt_count"] = attempt_count
    if _json_size(receipt) > ACTION_RECEIPT_MAX_BYTES:
        # All complete diagnostics remain in artifact_refs. Removing summaries is
        # conservative and does not change outcome or motion authorization facts.
        receipt["arm_attempts"] = []
        truncated = True
    if truncated:
        receipt["receipt_truncated"] = True
    if _json_size(receipt) > ACTION_RECEIPT_MAX_BYTES:
        raise ManipulationStateError("bounded Action receipt exceeds transport budget")
    return receipt


class ManipulationStateError(RuntimeError):
    pass


class PersistentManipulationProvider:
    """Serialize one physical world and retain possession across bounded Actions.

    The engine is constructed and used on a single thread, including sensor
    queries. Gateway invocation identities are supplied by the caller.
    """

    def __init__(self, engine_factory: Callable[[], Any], *, held_operations: tuple[str, ...] = ()) -> None:
        if set(held_operations) - {"pour", "stir"}:
            raise ValueError("unsupported held operation")
        self._held_operations = frozenset(held_operations)
        self._held_id: str | None = None
        self._cycle_id: str | None = None
        self._scene_revision: str | None = None
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="robotwin-world")
        self._lock = RLock()
        try:
            self._engine = self._pool.submit(engine_factory).result()
        except Exception:
            self._pool.shutdown(wait=True)
            raise
        self._state = "empty"
        self._owner: str | None = None
        self._acquire_id: str | None = None
        self._entity: str | None = None
        self._operations: dict[str, tuple[Future, Event]] = {}
        self._closed = False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            result = {"holding_state": self._state, "owner": self._owner,
                      "acquire_invocation_id": self._acquire_id, "entity_ref": self._entity}
            if self._held_operations or self._cycle_id is not None:
                result["held_invocation_ref"] = self._held_id
                if self._scene_revision is not None:
                    result["scene_revision"] = self._scene_revision
            if self._cycle_id is not None:
                result["cycle_invocation_ref"] = self._cycle_id
            return result

    def query(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._closed or self._state in {"acquiring", "placing", "operating"}:
                raise ManipulationStateError("world query unavailable during motion or shutdown")
            if operation == "prepare_cycle":
                if self._state != "empty":
                    raise ManipulationStateError("cycle preparation requires an empty provider")
                prepare_cycle = getattr(self._engine, "prepare_cycle", None)
                if not callable(prepare_cycle):
                    raise ManipulationStateError("engine does not support complete manipulation cycles")
                future = self._pool.submit(prepare_cycle, deepcopy(dict(arguments)))
                return {**dict(future.result()), **self.snapshot()}
            if operation in {"route_readiness", "bind_observed_entities", "contact_qualification"} and self._state != "empty":
                raise ManipulationStateError("new route preparation requires an empty provider")
            if operation == "prepare_held" and (not self._held_operations or self._state != "holding"):
                if not (self._cycle_id is not None and arguments.get("operation") == "place"
                        and self._state == "holding"):
                    raise ManipulationStateError("held preparation requires supported operations and known holding")
            future = self._pool.submit(self._engine.query, operation, deepcopy(dict(arguments)))
            return {**dict(future.result()), **self.snapshot()}

    def prepare_cycle(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Expose preparation only when the engine owns the full no-motion check."""
        operation = arguments.get("operation") if isinstance(arguments, Mapping) else None
        if not self.supports_cycle(operation):
            return {"status": "unavailable", "error": "complete_cycle_not_supported"}
        try:
            result = self.query("prepare_cycle", arguments)
        except Exception as exc:
            return {"status": "unavailable", "error": f"cycle_preparation_unavailable:{type(exc).__name__}"}
        if not isinstance(result, Mapping) or result.get("status") != "available":
            return {"status": "unavailable", "error": "cycle_preparation_unavailable"}
        return dict(result)

    def cycle_capability(self, operation: str) -> dict[str, Any]:
        """Return the engine's explicit deployment capability declaration."""
        declaration = getattr(self._engine, "cycle_capability", None)
        if not callable(declaration):
            return {"operation": operation}
        try:
            value = declaration(operation)
        except Exception:
            return {"operation": operation}
        if not isinstance(value, Mapping):
            return {"operation": operation}
        return dict(value)

    def supports_cycle(self, operation: str) -> bool:
        with self._lock:
            declaration = self.cycle_capability(operation)
            has_execution = (
                callable(getattr(self._engine, "execute_cycle", None))
                or callable(getattr(self._engine, "atomic_executor", None))
            )
            return (
                operation in COMPLETE_CYCLE_OPERATIONS
                and declaration.get("operation") == operation
                and all(declaration.get(key) is True for key in (
                    "preparation", "execution", "feedback", "return",
                ))
                and callable(getattr(self._engine, "prepare_cycle", None))
                and has_execution
            )

    def start(self, phase: str, invocation_id: str, owner: str, arguments: Mapping[str, Any]) -> None:
        cycle_phase = phase in COMPLETE_CYCLE_OPERATIONS
        if phase not in {"acquire", "place", *self._held_operations, *COMPLETE_CYCLE_OPERATIONS} or not invocation_id or not owner:
            raise ManipulationStateError("invalid manipulation identity")
        arguments = deepcopy(dict(arguments))
        with self._lock:
            if self._closed:
                raise ManipulationStateError("provider is closed")
            if invocation_id in self._operations:
                raise ManipulationStateError("invocation already exists; poll its result")
            if phase == "acquire":
                if self._state != "empty":
                    raise ManipulationStateError("acquire requires an empty provider")
                if not isinstance(arguments.get("entity_ref"), str) or not arguments["entity_ref"]:
                    raise ManipulationStateError("acquire requires entity_ref")
                self._owner, self._acquire_id, self._entity = owner, invocation_id, arguments["entity_ref"]
                self._cycle_id = None
            elif cycle_phase:
                if not self.supports_cycle(phase):
                    raise ManipulationStateError("engine does not support complete manipulation cycles")
                if self._state != "empty" or not isinstance(arguments.get("entity_ref"), str):
                    raise ManipulationStateError("complete cycle requires an empty provider and entity_ref")
                self._owner, self._acquire_id, self._entity = owner, None, arguments["entity_ref"]
                self._cycle_id = invocation_id
                self._held_id = None
            elif phase in self._held_operations and self._cycle_id is not None:
                raise ManipulationStateError("cycle-sourced possession can only be recovered with place")
            elif (self._state != "holding" or self._owner != owner
                  or (self._cycle_id is None and arguments.get("acquire_invocation_id") != self._acquire_id)
                  or (self._cycle_id is not None and arguments.get("cycle_invocation_id") != self._cycle_id)
                  or arguments.get("entity_ref") != self._entity):
                raise ManipulationStateError("place does not match the owned held object")
            if phase in self._held_operations or "held_invocation_ref" in arguments:
                if arguments.get("held_invocation_ref") != self._held_id or arguments.get("scene_revision") != self._scene_revision:
                    raise ManipulationStateError("held operation uses stale possession or scene")
            elif phase == "place" and self._held_operations and self._held_id != self._acquire_id:
                raise ManipulationStateError("place requires current held preparation")
            self._state = "acquiring" if phase == "acquire" or cycle_phase else "placing" if phase == "place" else "operating"
            cancel = Event()
            self._operations[invocation_id] = (
                self._pool.submit(
                    self._execute,
                    phase,
                    invocation_id,
                    owner,
                    arguments,
                    cancel,
                ),
                cancel,
            )

    def _execute(
        self,
        phase: str,
        invocation_id: str,
        owner: str,
        arguments: dict[str, Any],
        cancel: Event,
    ) -> dict[str, Any]:
        try:
            if phase in COMPLETE_CYCLE_OPERATIONS:
                execute = getattr(self._engine, "execute_cycle", None)
                if callable(execute):
                    complete_result = dict(execute(
                        phase, arguments, cancel, owner=owner, invocation_id=invocation_id,
                    ))
                else:
                    factory = getattr(self._engine, "atomic_executor", None)
                    if not callable(factory):
                        raise AtomicExecutionError("cycle engine has no execution boundary")
                    executor = factory(
                        phase, deepcopy(arguments), owner=owner, invocation_id=invocation_id,
                    )
                    complete_result = execute_atomic_cycle(
                        executor, arguments, cancel, owner=owner, invocation_id=invocation_id,
                    )
            else:
                complete_result = dict(self._engine.execute(
                    phase, arguments, cancel, owner=owner, invocation_id=invocation_id,
                ))
        except Exception as exc:
            # An exception is not evidence that nothing happened.
            result = {"status": "unknown", "outcome_known": False,
                      "failure_owner": "execution", "failure_code": type(exc).__name__}
        else:
            try:
                result = bounded_action_receipt(complete_result)
            except Exception as exc:
                # The engine already settled and may have changed the world. Keep
                # its durable evidence reachable while refusing to infer outcome.
                result = {
                    "status": "unknown",
                    "outcome_known": False,
                    "world_change_started": complete_result.get("world_change_started"),
                    "failure_owner": "infrastructure",
                    "failure_code": "action_receipt_projection_failed",
                    "error_detail": str(exc)[:_RECEIPT_TEXT_MAX_BYTES],
                    "artifact_refs": _bounded_refs(complete_result.get("artifact_refs")),
                    "evidence_refs": _bounded_refs(complete_result.get("evidence_refs")),
                    "retryable_in_revision": False,
                    "requires_replan": False,
                    "recommended_action": "stop",
                }
        with self._lock:
            status = result.get("status")
            explicit_possession = result.get("possession_state")
            if phase in self._held_operations:
                known = result.get("outcome_known") is True
                if known and explicit_possession in {"empty", "holding"}:
                    self._state = explicit_possession
                elif known and result.get("world_change_started") is False:
                    self._state = "holding"
                else:
                    self._state = "uncertain"
            elif phase in COMPLETE_CYCLE_OPERATIONS:
                known = result.get("outcome_known") is True
                if known and result.get("possession_state") in {"empty", "holding"}:
                    self._state = result["possession_state"]
                else:
                    self._state = "uncertain"
            elif explicit_possession == "empty" and (
                phase == "place"
                or (result.get("outcome_known") is True and status in {"succeeded", "failed"})
            ):
                self._state = "empty"
            elif explicit_possession == "holding" and phase == "acquire":
                self._state = "holding"
            elif status == "succeeded" and result.get("outcome_known") is True:
                self._state = "holding" if phase == "acquire" else "empty"
            elif result.get("world_change_started") is False and result.get("continuation_valid") is not False:
                self._state = "empty" if phase == "acquire" else "holding"
            else:
                self._state = "uncertain"
            if self._state == "empty":
                self._owner = self._acquire_id = self._entity = None
                self._cycle_id = None
            if phase in COMPLETE_CYCLE_OPERATIONS:
                self._held_id = invocation_id if self._state == "holding" else None
            if self._held_operations or phase in COMPLETE_CYCLE_OPERATIONS or self._cycle_id is not None:
                self._held_id = invocation_id
                if result.get("outcome_known") is not True:
                    self._scene_revision = None
                elif result.get("new_scene_revision"):
                    self._scene_revision = result["new_scene_revision"]
            measured_entity = result.get("entity_ref")
            result.update(self.snapshot())
            if ("held_invocation_ref" in arguments or phase in COMPLETE_CYCLE_OPERATIONS) and measured_entity is not None:
                result["entity_ref"] = measured_entity
            result["invocation_id"] = invocation_id
            effects = result.get("scene_effects")
            if isinstance(effects, dict) and "held_entity" in effects:
                # A historical engine receipt alone does not prove possession.
                # Publish it only when the provider's settled ownership agrees.
                held = effects["held_entity"]
                if (self._state != "holding" or result.get("outcome_known") is not True
                        or status != "succeeded" or not isinstance(held, dict)
                        or held != self.snapshot()):
                    effects.pop("held_entity")
            return result

    def poll(self, invocation_id: str) -> dict[str, Any] | None:
        with self._lock:
            operation = self._operations.get(invocation_id)
            if operation is None:
                raise ManipulationStateError("unknown provider invocation; reconcile the world")
            return deepcopy(operation[0].result()) if operation[0].done() else None

    def cancel(self, invocation_id: str) -> None:
        with self._lock:
            if invocation_id not in self._operations:
                raise ManipulationStateError("unknown provider invocation")
            self._operations[invocation_id][1].set()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for future, cancel in self._operations.values():
                if not future.done():
                    cancel.set()
            final = self._pool.submit(self._engine.close)
        try:
            final.result()
        finally:
            self._pool.shutdown(wait=True)
            with self._lock:
                if self._state != "empty":
                    self._state = "uncertain"


__all__ = [
    "ACTION_RECEIPT_MAX_BYTES",
    "ManipulationStateError",
    "PersistentManipulationProvider",
    "bounded_action_receipt",
]
