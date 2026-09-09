"""Bind public preparation references to adapter-owned executable route artifacts."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from PhyAgentOS.forge.manipulation import ArmAssignment

from .route_evidence import _artifact_path
from .route_readiness import route_geometry_digest, validate_route_request


class PreparedRoutes:
    """Runtime-local cache of prepared geometry, not task or invocation state."""

    def __init__(self, client, artifact_root: Path) -> None:
        self.client = client
        self.artifact_root = artifact_root.resolve()
        self._routes: dict[tuple[str, str], dict[str, Any]] = {}

    def register(self, arguments: Mapping[str, Any], *, route_request: Mapping[str, Any], approval_ref: str | None, destination_ref: str) -> None:
        validate_route_request(route_request)
        candidate = next((item for item in route_request["candidates"] if item["candidate_ref"] == arguments["candidate_ref"]), None)
        if candidate is None or candidate["entity_ref"] != arguments["entity_ref"]:
            raise ValueError("prepared route candidate/entity mismatch")
        if route_request["scene_revision"] != arguments["scene_revision"]:
            raise ValueError("prepared route source scene mismatch")
        if not destination_ref or (approval_ref is not None and not approval_ref.startswith("artifact://")):
            raise ValueError("prepared route requires a destination and valid optional approval reference")
        assignment = ArmAssignment.model_validate(json.loads(
            _artifact_path(self.artifact_root, arguments["assignment_ref"]).read_text(encoding="utf-8")
        ))
        for field in ("assignment_ref", "entity_ref", "candidate_ref", "observation_ref", "scene_revision",
                      "calibration_ref", "candidate_set_ref", "capability_snapshot_ref"):
            if getattr(assignment, field) != arguments[field]:
                raise ValueError(f"assignment does not match preparation: {field}")
        if assignment.route_digest != route_geometry_digest(route_request):
            raise ValueError("assignment does not match the prepared complete route")
        if len(assignment.selected_arm_ids) != 1 or assignment.selected_arm_ids[0] not in {"left", "right"}:
            raise ValueError("persistent route requires one supported assigned arm")
        key = (arguments["preparation_ref"], arguments["candidate_ref"])
        value = {**deepcopy(dict(arguments)), "route_request": deepcopy(dict(route_request)),
                 "approval_ref": approval_ref, "destination_ref": destination_ref,
                 "assignment": assignment.model_dump(mode="json")}
        if key in self._routes and approval_ref is None:
            value["approval_ref"] = self._routes[key]["approval_ref"]
        if key in self._routes and self._routes[key] != value:
            raise ValueError("preparation reference already identifies different geometry")
        self._routes[key] = value

    def bind_approval(self, preparation_ref: str, candidate_ref: str, approval_ref: str) -> None:
        """Attach externally issued approval; the execution worker validates it."""
        _artifact_path(self.artifact_root, approval_ref)
        prepared = self._routes[(preparation_ref, candidate_ref)]
        if prepared["approval_ref"] not in (None, approval_ref):
            raise ValueError("preparation already binds another approval")
        prepared["approval_ref"] = approval_ref

    def __call__(self, phase: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        key = (arguments["preparation_ref"], arguments["candidate_ref"])
        if key not in self._routes:
            raise ValueError("no executable route is bound to this preparation")
        prepared = self._routes[key]
        if prepared["approval_ref"] is None:
            raise ValueError("prepared geometry has no execution approval")
        for field in ("observation_ref", "scene_revision", "frame_id", "calibration_ref", "entity_ref", "candidate_set_ref", "assignment_ref", "capability_snapshot_ref"):
            if arguments.get(field) != prepared.get(field):
                raise ValueError(f"Action changed preparation provenance: {field}")
        current = self.client.query("snapshot", {})
        result = deepcopy(prepared)
        if phase == "acquire":
            if current["scene_revision"] != prepared["scene_revision"]:
                raise ValueError("acquire preparation is stale")
        elif phase == "place":
            if arguments.get("destination_ref") != prepared["destination_ref"]:
                raise ValueError("place destination does not match prepared route")
            if current.get("acquire_invocation_id") != arguments.get("acquire_invocation_ref"):
                raise ValueError("place acquisition is not the current held object")
            result["scene_revision"] = current["scene_revision"]
        else:
            raise ValueError("unsupported preparation phase")
        return result
