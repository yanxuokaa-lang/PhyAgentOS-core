"""Bind public preparation references to adapter-owned executable route artifacts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .route_readiness import validate_route_request


class PreparedRoutes:
    """Runtime-local cache of prepared geometry, not task or invocation state."""

    def __init__(self, client) -> None:
        self.client = client
        self._routes: dict[tuple[str, str], dict[str, Any]] = {}

    def register(self, arguments: Mapping[str, Any], *, route_request: Mapping[str, Any], approval_ref: str, destination_ref: str) -> None:
        validate_route_request(route_request)
        candidate = next((item for item in route_request["candidates"] if item["candidate_ref"] == arguments["candidate_ref"]), None)
        if candidate is None or candidate["entity_ref"] != arguments["entity_ref"]:
            raise ValueError("prepared route candidate/entity mismatch")
        if route_request["scene_revision"] != arguments["scene_revision"]:
            raise ValueError("prepared route source scene mismatch")
        if not destination_ref or not approval_ref.startswith("artifact://"):
            raise ValueError("prepared route requires destination and approval evidence")
        key = (arguments["preparation_ref"], arguments["candidate_ref"])
        value = {**deepcopy(dict(arguments)), "route_request": deepcopy(dict(route_request)),
                 "approval_ref": approval_ref, "destination_ref": destination_ref}
        if key in self._routes and self._routes[key] != value:
            raise ValueError("preparation reference already identifies different geometry")
        self._routes[key] = value

    def __call__(self, phase: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        key = (arguments["preparation_ref"], arguments["candidate_ref"])
        if key not in self._routes:
            raise ValueError("no executable route is bound to this preparation")
        prepared = self._routes[key]
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
