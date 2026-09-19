"""Compose route materialization, selection and public preparation evidence."""

from __future__ import annotations

import json
import logging
import math
from copy import deepcopy
from pathlib import Path
from time import monotonic
from typing import Any, Mapping
from uuid import uuid4

from PhyAgentOS.forge.manipulation import CapabilitySnapshot, ManipulationIntent, ReplanSignal

from .arm_candidates import project_arm_assignment
from .preparation_deadline import PreparationDeadline
from .route_evidence import _artifact_path
from .route_readiness import route_geometry_digest

logger = logging.getLogger(__name__)


class PersistentPreparationProvider:
    """Prepare against the live world using adapter-owned geometry and selection.

    route_builder.build(request) returns destination_ref, base_request and candidate/arm options
    in the existing CompleteRouteSelector format. It owns frame transforms and
    destination geometry. The selector must supply complete readiness evidence;
    this composition never promotes partial planner evidence to success.
    """

    def __init__(
        self,
        *,
        client,
        route_builder,
        selector,
        prepared_routes,
        timeout_s: float = 330.0,
    ) -> None:
        if isinstance(timeout_s, bool) or not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("preparation timeout must be finite and positive")
        self.client = client
        self.route_builder = route_builder
        self.selector = selector
        self.prepared_routes = prepared_routes
        self.timeout_s = float(timeout_s)

    def prepare(
        self,
        request: Mapping[str, Any],
        *,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        measured = metrics if metrics is not None else {}
        started = monotonic()
        try:
            result = self._prepare(request, metrics=measured)
            measured["status"] = "completed"
            return result
        except Exception as exc:
            measured["status"] = "failed"
            measured["failure"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "failure_owner": "preparation",
            }
            raise
        finally:
            measured["total_s"] = monotonic() - started
            try:
                self._persist_metrics(request, measured)
            except (OSError, TypeError, ValueError) as exc:
                logger.warning("persistent preparation timing could not be written: %s", exc)

    def _prepare(
        self,
        request: Mapping[str, Any],
        *,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        deadline = PreparationDeadline.start(self.timeout_s)
        intent = ManipulationIntent.model_validate(request["intent"])
        current = self.client.query(
            "snapshot", {}, timeout_s=deadline.remaining("initial_snapshot")
        )
        if current["scene_revision"] != intent.scene_revision or current["holding_state"] != "empty":
            raise ValueError("preparation requires the current empty world")
        capability = CapabilitySnapshot.model_validate(json.loads(_artifact_path(
            self.prepared_routes.artifact_root, request["capability_snapshot_ref"]
        ).read_text(encoding="utf-8")))
        if capability.snapshot_ref != request["capability_snapshot_ref"]:
            raise ValueError("capability artifact reference mismatch")
        if any(getattr(capability, key) != getattr(intent, key) for key in
               ("scene_revision", "observation_ref", "calibration_ref")):
            raise ValueError("capability snapshot is stale")
        bundle = self.route_builder.build(
            deepcopy(dict(request)),
            deadline=deadline,
            metrics=metrics,
        )
        if bundle.get("destination_ref") != request["destination_ref"]:
            raise ValueError("materialized route destination differs from request")
        selected = self.selector.select(
            intent,
            bundle["base_request"],
            bundle["options"],
            deadline=deadline,
            metrics=metrics,
        )
        if isinstance(selected, ReplanSignal):
            return {"prepared_candidates": [], "provider_available": True,
                    "assignments": [], "destination_ref": request["destination_ref"]}
        assignment = project_arm_assignment(intent, capability, selected)
        proposed = {item["candidate_ref"]: item["entity_ref"] for item in request["candidates"]}
        if proposed.get(assignment.candidate_ref) != assignment.entity_ref:
            raise ValueError("selected route is not bound to a requested candidate")
        option = next(item for item in bundle["options"] if item["option_id"] == selected["selected_option_id"])
        route = deepcopy(bundle["base_request"])
        route["request_id"] = f"{route['request_id']}-{option['option_id']}"
        route["candidates"] = [deepcopy(option["candidate"])]
        if route_geometry_digest(route) != assignment.route_digest:
            raise ValueError("selected route geometry differs from assignment")
        finalize = getattr(self.route_builder, "finalize", None)
        finalization_started = monotonic()
        review_ref = finalize(bundle, route, deadline=deadline) if callable(finalize) else None
        metrics["finalization_s"] = monotonic() - finalization_started
        # Recheck after potentially expensive preparation; stale work is not published.
        current = self.client.query(
            "snapshot", {}, timeout_s=deadline.remaining("final_snapshot")
        )
        deadline.remaining("result_publication")
        if current["scene_revision"] != intent.scene_revision or current["holding_state"] != "empty":
            raise ValueError("world changed during preparation")
        value = assignment.model_dump(mode="json")
        parts = assignment.assignment_ref.removeprefix("artifact://").split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("assignment artifact path is invalid")
        path = self.prepared_routes.artifact_root.joinpath(*parts)
        if not path.suffix:
            path = path.with_suffix(".json")
        if self.prepared_routes.artifact_root not in path.resolve().parents:
            raise ValueError("assignment artifact path escapes owned root")
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(value, sort_keys=True) + "\n"
        if path.exists():
            if path.is_symlink() or path.read_text(encoding="utf-8") != encoded:
                raise ValueError("assignment reference already identifies another selection")
        else:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
        arguments = {key: request[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref", "candidate_set_ref", "capability_snapshot_ref")}
        arguments.update(preparation_ref=f"preparation://{intent.scene_revision}/{intent.observation_frame_id}",
                         candidate_ref=assignment.candidate_ref, entity_ref=assignment.entity_ref,
                         assignment_ref=assignment.assignment_ref)
        if review_ref is not None:
            arguments["review_request_ref"] = review_ref
        self.prepared_routes.register(arguments, route_request=route, approval_ref=None,
                                      destination_ref=request["destination_ref"])
        return {"prepared_candidates": [{"candidate_ref": assignment.candidate_ref,
                                          "entity_ref": assignment.entity_ref,
                                          "checks": {key: "pass" for key in ("kinematic", "collision", "workspace")},
                                          "evidence": [*selected["evidence_refs"], *([review_ref] if review_ref else [])], "qualification": "prepared"}],
                "provider_available": True, "assignments": [value], "destination_ref": request["destination_ref"]}

    def _persist_metrics(
        self,
        request: Mapping[str, Any],
        metrics: Mapping[str, Any],
    ) -> None:
        root = Path(self.prepared_routes.artifact_root).resolve()
        directory = root / "preparation-metrics"
        directory.mkdir(parents=True, exist_ok=True)
        intent = request.get("intent")
        identity = dict(intent) if isinstance(intent, Mapping) else {}
        payload = {
            "schema_version": "paos-persistent-preparation-timing/v1",
            "task_id": identity.get("task_id"),
            "revision_id": identity.get("revision_id"),
            "node_id": identity.get("node_id"),
            "scene_revision": request.get("scene_revision"),
            "candidate_count": len(request.get("candidates", ())),
            "metrics": deepcopy(dict(metrics)),
            "motion_authorized": False,
            "action_count": 0,
            "simulator_steps": 0,
        }
        path = directory / f"{uuid4().hex}.json"
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
