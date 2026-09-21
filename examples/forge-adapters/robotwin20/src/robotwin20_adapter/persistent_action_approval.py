"""Route-bound approval for one monitored persistent simulation Action."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .route_readiness import route_geometry_digest, validate_route_request

PERSISTENT_ACTION_APPROVAL_SCHEMA_VERSION = (
    "paos-robotwin20-persistent-simulation-action-approval/v1"
)
RUNTIME_MONITORED_ACTION_MODE = "runtime_monitored"
DISABLED_ACTION_MODE = "disabled"
DEFERRED_EXECUTION_CHECKS = ("contact_dynamics", "stop_control")


class PersistentActionApprovalError(ValueError):
    """A persistent simulation Action approval is missing or mismatched."""


def _artifact_path(root: Path, artifact_ref: str, *, create_parent: bool = False) -> Path:
    if not isinstance(artifact_ref, str) or not artifact_ref.startswith("artifact://"):
        raise PersistentActionApprovalError("persistent Action approval reference is invalid")
    parts = artifact_ref.removeprefix("artifact://").split("/")
    if len(parts) < 2 or any(part in {"", ".", ".."} for part in parts):
        raise PersistentActionApprovalError("persistent Action approval path is unsafe")
    path = root.joinpath(*parts).with_suffix(".json").resolve()
    resolved_root = root.resolve()
    if resolved_root not in path.parents:
        raise PersistentActionApprovalError("persistent Action approval escapes artifact root")
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _validate_readiness_evidence_refs(root: Path, value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise PersistentActionApprovalError(
            "persistent Action approval readiness evidence is invalid"
        )
    for artifact_ref in value:
        _artifact_path(root, artifact_ref)
    return list(value)


def _validate_authorized_at(value: Any) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise PersistentActionApprovalError(
            "persistent Action approval timestamp is invalid"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PersistentActionApprovalError(
            "persistent Action approval timestamp is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PersistentActionApprovalError(
            "persistent Action approval timestamp must include a timezone"
        )
    return value


class PersistentSimulationActionApprover:
    """Issue an approval only for the explicitly enabled simulation profile."""

    def __init__(self, artifact_root: Path, *, task_name: str, mode: str) -> None:
        if mode != RUNTIME_MONITORED_ACTION_MODE:
            raise PersistentActionApprovalError(
                "persistent simulation Action approval requires runtime_monitored mode"
            )
        if not isinstance(task_name, str) or not task_name:
            raise PersistentActionApprovalError("persistent simulation task_name is invalid")
        self.artifact_root = artifact_root.resolve()
        self.task_name = task_name
        self.mode = mode

    def issue(
        self,
        route_request: Mapping[str, Any],
        *,
        candidate_ref: str,
        assignment: Mapping[str, Any],
        readiness_evidence_refs: list[str],
    ) -> str:
        validate_route_request(route_request)
        candidate = next(
            (
                item
                for item in route_request["candidates"]
                if item["candidate_ref"] == candidate_ref
            ),
            None,
        )
        if candidate is None:
            raise PersistentActionApprovalError(
                "persistent Action approval candidate is not in the route"
            )
        if (
            assignment.get("candidate_ref") != candidate_ref
            or assignment.get("entity_ref") != candidate["entity_ref"]
            or assignment.get("scene_revision") != route_request["scene_revision"]
            or assignment.get("route_digest") != route_geometry_digest(route_request)
            or assignment.get("motion_authorized") is not False
        ):
            raise PersistentActionApprovalError(
                "persistent Action approval assignment does not bind the route"
            )
        readiness_evidence_refs = _validate_readiness_evidence_refs(
            self.artifact_root, readiness_evidence_refs
        )
        artifact_ref = f"artifact://persistent-action-approvals/{uuid4().hex}"
        payload = {
            "schema_version": PERSISTENT_ACTION_APPROVAL_SCHEMA_VERSION,
            "decision": "approved_persistent_simulation_action",
            "simulation_only": True,
            "motion_authorized": True,
            "authorization_mode": self.mode,
            "task_name": self.task_name,
            "scene_revision": route_request["scene_revision"],
            "request_id": route_request["request_id"],
            "candidate_ref": candidate_ref,
            "entity_ref": candidate["entity_ref"],
            "route_geometry_digest": route_geometry_digest(route_request),
            "assignment_ref": assignment["assignment_ref"],
            "assignment_digest": assignment["assignment_digest"],
            "required_execution_checks": list(DEFERRED_EXECUTION_CHECKS),
            "readiness_evidence_refs": list(readiness_evidence_refs),
            "authorized_at": datetime.now(timezone.utc).isoformat(),
        }
        path = _artifact_path(self.artifact_root, artifact_ref, create_parent=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, sort_keys=True) + "\n")
        return artifact_ref


def validate_persistent_action_approval(
    artifact_root: Path,
    artifact_ref: str,
    *,
    task_name: str,
    mode: str,
    route_request: Mapping[str, Any],
    candidate_ref: str,
    assignment: Mapping[str, Any],
) -> dict[str, Any]:
    """Revalidate the route-bound approval immediately before Action setup."""

    if mode != RUNTIME_MONITORED_ACTION_MODE:
        raise PersistentActionApprovalError("persistent simulation Action mode is disabled")
    validate_route_request(route_request)
    path = _artifact_path(artifact_root.resolve(), artifact_ref)
    try:
        approval = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PersistentActionApprovalError(
            "persistent Action approval artifact is unavailable"
        ) from exc
    if isinstance(approval, dict):
        _validate_readiness_evidence_refs(
            artifact_root.resolve(), approval.get("readiness_evidence_refs")
        )
        _validate_authorized_at(approval.get("authorized_at"))
    required = {
        "schema_version",
        "decision",
        "simulation_only",
        "motion_authorized",
        "authorization_mode",
        "task_name",
        "scene_revision",
        "request_id",
        "candidate_ref",
        "entity_ref",
        "route_geometry_digest",
        "assignment_ref",
        "assignment_digest",
        "required_execution_checks",
        "readiness_evidence_refs",
        "authorized_at",
    }
    candidate = next(
        (
            item
            for item in route_request["candidates"]
            if item["candidate_ref"] == candidate_ref
        ),
        None,
    )
    if (
        not isinstance(approval, dict)
        or set(approval) != required
        or approval.get("schema_version") != PERSISTENT_ACTION_APPROVAL_SCHEMA_VERSION
        or approval.get("decision") != "approved_persistent_simulation_action"
        or approval.get("simulation_only") is not True
        or approval.get("motion_authorized") is not True
        or approval.get("authorization_mode") != mode
        or approval.get("task_name") != task_name
        or approval.get("scene_revision") != route_request["scene_revision"]
        or approval.get("request_id") != route_request["request_id"]
        or approval.get("candidate_ref") != candidate_ref
        or candidate is None
        or approval.get("entity_ref") != candidate["entity_ref"]
        or approval.get("route_geometry_digest") != route_geometry_digest(route_request)
        or approval.get("assignment_ref") != assignment.get("assignment_ref")
        or approval.get("assignment_digest") != assignment.get("assignment_digest")
        or approval.get("required_execution_checks") != list(DEFERRED_EXECUTION_CHECKS)
    ):
        raise PersistentActionApprovalError(
            "persistent Action approval does not bind the current route"
        )
    return approval


__all__ = [
    "DEFERRED_EXECUTION_CHECKS",
    "DISABLED_ACTION_MODE",
    "PERSISTENT_ACTION_APPROVAL_SCHEMA_VERSION",
    "PersistentActionApprovalError",
    "PersistentSimulationActionApprover",
    "RUNTIME_MONITORED_ACTION_MODE",
    "validate_persistent_action_approval",
]
