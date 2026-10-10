"""Provider-owned holding lifecycle, independent of PAOS and simulator imports."""

from __future__ import annotations

import json
from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from threading import Event, RLock
from typing import Any, Callable, Mapping

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
    "video_evidence_error",
)
_ATTEMPT_FIELDS = (
    "arm",
    "status",
    "failed_phase",
    "failed_waypoint_index",
    "detail",
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

    def __init__(self, engine_factory: Callable[[], Any]) -> None:
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
            return {"holding_state": self._state, "owner": self._owner,
                    "acquire_invocation_id": self._acquire_id, "entity_ref": self._entity}

    def query(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._closed or self._state in {"acquiring", "placing"}:
                raise ManipulationStateError("world query unavailable during motion or shutdown")
            if operation in {"route_readiness", "bind_observed_entities", "contact_qualification"} and self._state != "empty":
                raise ManipulationStateError("new route preparation requires an empty provider")
            future = self._pool.submit(self._engine.query, operation, deepcopy(dict(arguments)))
            return {**dict(future.result()), **self.snapshot()}

    def start(self, phase: str, invocation_id: str, owner: str, arguments: Mapping[str, Any]) -> None:
        if phase not in {"acquire", "place"} or not invocation_id or not owner:
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
            elif (self._state != "holding" or self._owner != owner
                  or arguments.get("acquire_invocation_id") != self._acquire_id
                  or arguments.get("entity_ref") != self._entity):
                raise ManipulationStateError("place does not match the owned held object")
            self._state = "acquiring" if phase == "acquire" else "placing"
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
            complete_result = dict(
                self._engine.execute(
                    phase,
                    arguments,
                    cancel,
                    owner=owner,
                    invocation_id=invocation_id,
                )
            )
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
            if explicit_possession == "empty" and phase == "place":
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
            result.update(self.snapshot())
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
