"""Compose one Coordinator relation Action over the persistent RoboTwin worker."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from math import isfinite
from threading import Lock
from typing import Any

from PhyAgentOS.forge.capability_runtime import ActionAdmission, ActionDriver


class StackRelationExecutionError(ValueError):
    """The relation cannot be executed from current qualified route evidence."""


class StackRelationExecutionProvider:
    """Run one relation as a bounded acquire/place Action over the existing worker.

    ``prepare_route`` is Adapter-owned and must return the complete arguments
    accepted by the persistent acquire/place worker, including its current-scene
    route, assignment and route-bound approval. This provider owns only the
    composition of those existing phase drivers into the relation Action.
    """

    def __init__(
        self,
        client: Any,
        *,
        prepare_route: Callable[[Mapping[str, Any], str], Mapping[str, Any]],
        motion_supported: Callable[[], bool],
    ) -> None:
        if not callable(prepare_route) or not callable(motion_supported):
            raise ValueError("relation route preparation and capability ports are required")
        self.client = client
        self.prepare_route = prepare_route
        self.motion_supported = motion_supported

    def admit(
        self,
        request: Mapping[str, Any],
        *,
        invocation_id: str,
        attempt_id: str,
    ) -> ActionAdmission:
        intent = request.get("intent")
        binding = request.get("relation_binding")
        if not isinstance(intent, Mapping) or not isinstance(binding, Mapping):
            return _terminal("relation_execution_binding_missing", known=True)
        task_id = intent.get("task_id")
        if not isinstance(task_id, str) or not task_id or not invocation_id or not attempt_id:
            return _terminal("relation_execution_identity_invalid", known=True)
        if self.motion_supported() is not True:
            return _terminal("stack_relation_motion_unqualified", known=True)

        try:
            route = deepcopy(dict(self.prepare_route(deepcopy(dict(request)), task_id)))
            self._validate_route(route, request, task_id)
            current = self.client.query("snapshot", {})
            if current.get("scene_revision") != route["scene_revision"]:
                raise StackRelationExecutionError("prepared relation route is stale")
            acquire_id = f"{invocation_id}:acquire"
            owner = f"paos:{task_id}"
            driver = self.client.start("acquire", acquire_id, owner, route)
        except Exception as exc:
            return _terminal(
                "stack_relation_preparation_failed",
                known=True,
                detail=f"{type(exc).__name__}: {exc}"[:1000],
            )
        return ActionAdmission(
            driver=_StackRelationDriver(
                self.client,
                route=route,
                acquire_driver=driver,
                acquire_id=acquire_id,
                place_id=f"{invocation_id}:place",
                owner=owner,
                attempt_id=attempt_id,
            )
        )

    @staticmethod
    def _validate_route(route: Mapping[str, Any], request: Mapping[str, Any], task_id: str) -> None:
        required = {
            "scene_revision", "entity_ref", "candidate_ref", "assignment_ref",
            "assignment", "route_request", "approval_ref",
        }
        if required - set(route):
            raise StackRelationExecutionError("prepared relation route is incomplete")
        relation = request["relation_binding"]
        assignment = route["assignment"]
        route_request = route["route_request"]
        if not isinstance(assignment, Mapping) or not isinstance(route_request, Mapping):
            raise StackRelationExecutionError("prepared route lacks assignment or route request")
        if route["entity_ref"] != request.get("entity_ref") or route["entity_ref"] != relation.get("entity_ref"):
            raise StackRelationExecutionError("prepared route entity differs from relation binding")
        if route_request.get("scene_revision") != request.get("scene_revision"):
            raise StackRelationExecutionError("prepared route scene differs from relation binding")
        if assignment.get("task_id") != task_id or assignment.get("entity_ref") != route["entity_ref"]:
            raise StackRelationExecutionError("prepared assignment is not owned by this task/entity")
        if assignment.get("assignment_ref") != route["assignment_ref"]:
            raise StackRelationExecutionError("prepared assignment reference mismatch")
        if assignment.get("candidate_ref") != route["candidate_ref"]:
            raise StackRelationExecutionError("prepared candidate differs from assignment")
        if not isinstance(route.get("approval_ref"), str) or not route["approval_ref"].startswith("artifact://"):
            raise StackRelationExecutionError("prepared route has no execution approval")
        if route_request.get("destination_ref") != relation.get("destination_ref"):
            raise StackRelationExecutionError("prepared destination differs from current relation target")
        candidates = route_request.get("candidates")
        if not isinstance(candidates, (list, tuple)) or not any(
            isinstance(candidate, Mapping)
            and candidate.get("candidate_ref") == route["candidate_ref"]
            and candidate.get("entity_ref") == route["entity_ref"]
            for candidate in candidates
        ):
            raise StackRelationExecutionError("prepared route does not contain the assigned candidate")


class _StackRelationDriver(ActionDriver):
    def __init__(self, client, *, route, acquire_driver, acquire_id, place_id, owner, attempt_id):
        self.client = client
        self.route = route
        self.current = acquire_driver
        self.acquire_id = acquire_id
        self.place_id = place_id
        self.owner = owner
        self.attempt_id = attempt_id
        self.phase = "acquire"
        self.terminal = False
        self.cancel_requested = False
        self._transition_lock = Lock()

    def poll(self) -> Mapping[str, Any] | None:
        if self.terminal:
            return None
        try:
            result = self.current.poll()
        except Exception as exc:
            self.terminal = True
            return _unknown(
                f"worker_poll_uncertain:{type(exc).__name__}",
                receipts=[getattr(self, "acquire_receipt", {})],
            )
        if result is None:
            return None
        if not isinstance(result, Mapping):
            self.terminal = True
            return _unknown("invalid_worker_result")
        receipt = dict(result)
        if self.phase == "acquire":
            with self._transition_lock:
                if self.cancel_requested:
                    self.terminal = True
                    return _unknown("cancelled_during_acquire", receipts=[receipt])
                if receipt.get("status") != "succeeded" or receipt.get("outcome_known") is not True:
                    self.terminal = True
                    return _phase_failure(receipt, "acquire")
                if receipt.get("possession_state") != "holding":
                    self.terminal = True
                    return _unknown("acquire_possession_unconfirmed", receipts=[receipt])
                next_scene = receipt.get("new_scene_revision")
                if not isinstance(next_scene, str) or not next_scene:
                    self.terminal = True
                    return _unknown("acquire_scene_revision_missing", receipts=[receipt])
                place_arguments = deepcopy(self.route)
                place_arguments.update(
                    scene_revision=next_scene,
                    acquire_invocation_id=self.acquire_id,
                    attempt_id=self.attempt_id,
                )
                try:
                    self.current = self.client.start(
                        "place", self.place_id, self.owner, place_arguments
                    )
                except Exception as exc:
                    self.terminal = True
                    return _unknown(f"place_start_uncertain:{type(exc).__name__}", receipts=[receipt])
                self.phase = "place"
                self.acquire_receipt = receipt
                return None

        self.terminal = True
        return self._settle_place(receipt)

    def _settle_place(self, receipt: dict[str, Any]) -> dict[str, Any]:
        receipts = [getattr(self, "acquire_receipt", {}), receipt]
        if receipt.get("status") != "succeeded" or receipt.get("outcome_known") is not True:
            return _phase_failure(receipt, "place", receipts=receipts)
        measurement = receipt.get("placement_measurement")
        position_error = measurement.get("position_error_m") if isinstance(measurement, Mapping) else None
        orientation_error = measurement.get("orientation_error_rad") if isinstance(measurement, Mapping) else None
        if (
            not isinstance(measurement, Mapping)
            or isinstance(position_error, bool)
            or not isinstance(position_error, (int, float))
            or not isfinite(position_error)
            or position_error < 0
            or isinstance(orientation_error, bool)
            or not isinstance(orientation_error, (int, float))
            or not isfinite(orientation_error)
            or orientation_error < 0
            or not isinstance(receipt.get("new_scene_revision"), str)
            or not receipt["new_scene_revision"]
            or receipt["new_scene_revision"] == receipts[0].get("new_scene_revision")
            or receipt.get("release_confirmed") is not True
            or receipt.get("retreat_completed") is not True
            or receipt.get("clear_of_target") is not True
            or receipt.get("possession_state") != "empty"
        ):
            return _unknown("relation_postcondition_not_measured", receipts=receipts)
        evidence_refs = [
            ref
            for item in receipts
            for refs in [item.get("evidence_refs")]
            if isinstance(refs, (list, tuple))
            for ref in refs
            if isinstance(ref, str) and ref.startswith("artifact://")
        ]
        if not evidence_refs:
            return _unknown("relation_postcondition_evidence_missing", receipts=receipts)
        return {
            "status": "succeeded",
            "outcome_known": True,
            "world_change_started": True,
            "possession_state": "empty",
            "new_scene_revision": receipt.get("new_scene_revision"),
            "placement_measurement": dict(measurement),
            "release_confirmed": True,
            "retreat_completed": True,
            "clear_of_target": True,
            "evidence_refs": evidence_refs,
            "phase_receipts": receipts,
        }

    def cancel(self) -> None:
        with self._transition_lock:
            self.cancel_requested = True
            self.current.cancel()

    def stop(self) -> None:
        self.cancel()


def _terminal(code: str, *, known: bool, detail: str | None = None) -> ActionAdmission:
    error = {"code": code}
    if detail:
        error["message"] = detail
    return ActionAdmission(terminal_result={
        "status": "failed" if known else "unknown",
        "outcome_known": known,
        "world_change_started": False,
        "error": error,
        "retryable_in_revision": False,
        "recommended_action": "reconcile_world" if not known else "fix_runtime_contract",
    })


def _unknown(code: str, *, receipts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "status": "unknown", "outcome_known": False, "world_change_started": True,
        "failure_owner": "execution", "failure_code": code,
        "recommended_action": "reconcile_world", "requires_replan": False,
        "phase_receipts": receipts or [],
    }


def _phase_failure(
    result: dict[str, Any], phase: str, *, receipts: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    known = result.get("outcome_known") is True
    return {
        "status": result.get("status") if result.get("status") in {"failed", "cancelled"} else "unknown",
        "outcome_known": known,
        "world_change_started": result.get("world_change_started", True),
        "failure_owner": result.get("failure_owner", "execution"),
        "failure_code": result.get("failure_code", f"{phase}_failed"),
        "possession_state": result.get("possession_state", "uncertain"),
        "object_support_state": result.get("object_support_state", "unknown"),
        "recommended_action": result.get("recommended_action", "reconcile_world"),
        "requires_replan": result.get("requires_replan", False),
        "phase_receipts": receipts or [result],
    }


__all__ = ["StackRelationExecutionError", "StackRelationExecutionProvider"]
