"""External route-readiness worker seam for RoboTwin simulation.

The worker records planner and attached-object geometry evidence when a
RoboTwin evaluator is configured. Contact dynamics and stop control remain
unavailable here; user-level verification belongs to the PAOS Verifier.
It never calls ``play_once`` or steps the simulator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Mapping

from worker_protocol import serve

from robotwin20_adapter.route_readiness import (
    ROUTE_CHECKS,
    SIMULATION_ROUTE_READINESS_SCHEMA_VERSION,
    project_route_evidence,
    validate_route_request,
)


def _artifact_path(root: Path, request_id: str, candidate_ref: str) -> tuple[Path, str]:
    token = hashlib.sha256(f"{request_id}\n{candidate_ref}".encode("utf-8")).hexdigest()
    directory = root / "simulation-route-readiness"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{token}.json", f"artifact://simulation-route-readiness/{token}"


def _handle_factory(artifact_root: Path, worker_id: str, evaluator=None):
    if not artifact_root.is_absolute() or artifact_root.is_symlink() or not artifact_root.is_dir():
        raise ValueError("artifact root must be an existing absolute directory")
    if not isinstance(worker_id, str) or not worker_id.strip():
        raise ValueError("worker_id must be non-empty")

    def handle(request: Mapping[str, Any]) -> Mapping[str, Any]:
        validate_route_request(request)
        evidence: list[dict[str, Any]] = []
        unavailable = {
            check: "unavailable"
            for check in ROUTE_CHECKS
        }
        evaluation = None
        evaluation_error = None
        if evaluator is not None:
            try:
                with redirect_stdout(sys.stderr):
                    evaluation = evaluator(request)
            except Exception as exc:
                evaluation_error = f"{type(exc).__name__}: {exc}"
        for candidate in request["candidates"]:
            path, ref = _artifact_path(
                artifact_root, request["request_id"], candidate["candidate_ref"]
            )
            checks = dict(unavailable)
            result = None if evaluation is None else evaluation["candidates"][candidate["candidate_ref"]]
            if result is not None:
                for check in ("attached_object_collision", "complete_transport_descent_retreat", "workspace_and_joint_limits"):
                    checks[check] = result["status"]
            item = project_route_evidence(
                request,
                candidate,
                capability_status=checks,
                evidence_ref=ref,
            )
            artifact = dict(item)
            if result is not None:
                artifact["planner_evaluation"] = result
                artifact["collision_world_evidence"] = evaluation["world"]
                artifact["simulator_steps"] = evaluation["simulator_steps"]
            if evaluation_error:
                artifact["provider_error"] = evaluation_error
            encoded = (json.dumps(artifact, sort_keys=True) + "\n").encode("utf-8")
            if path.exists():
                if path.is_symlink() or path.read_bytes() != encoded:
                    raise ValueError("route evidence artifact is immutable and divergent")
            else:
                with path.open("xb") as stream:
                    stream.write(encoded)
                path.chmod(0o600)
            evidence.append(item)
        return {
            "request_id": request["request_id"],
            "schema_version": SIMULATION_ROUTE_READINESS_SCHEMA_VERSION,
            "status": "unavailable" if evaluation is None else "fail",
            "worker_id": worker_id,
            "motion_authorized": False,
            "world_change_started": False,
            "provider_available": evaluation is not None,
            "route_evidence": evidence,
            "unavailable_reasons": ([evaluation_error] if evaluation_error else []) + ([
                "attached_object_collision_worker_not_connected",
                "planner_route_worker_not_connected",
            ] if evaluation is None else []) + [
                "contact_dynamics_not_proven_without_stepping",
                "stop_controller_not_connected",
            ],
        }

    return handle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--runtime-profile", type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if bool(args.runtime_root) != bool(args.runtime_profile):
        parser.error("runtime-root and runtime-profile must be supplied together")
    evaluator = None
    if args.runtime_root:
        from robotwin_route_planner import RoboTwinRouteEvaluator
        evaluator = RoboTwinRouteEvaluator(args.runtime_root.resolve(), args.runtime_profile.resolve(), args.artifact_root.resolve())
    handle = _handle_factory(args.artifact_root.resolve(), args.worker_id, evaluator)
    if args.request or args.output:
        if not (args.request and args.output and evaluator):
            parser.error("one-shot evaluation requires request, output and runtime arguments")
        if args.output.exists():
            parser.error("output must be a new file")
        request = json.loads(args.request.read_text())
        validate_route_request(request)
        with redirect_stdout(sys.stderr):
            result = evaluator(request)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, sort_keys=True) + "\n")
        return 0
    return serve(
        "robotwin-route-readiness",
        lambda: None,
        handle,
        schema_version=SIMULATION_ROUTE_READINESS_SCHEMA_VERSION,
    )


if __name__ == "__main__":
    raise SystemExit(main())
