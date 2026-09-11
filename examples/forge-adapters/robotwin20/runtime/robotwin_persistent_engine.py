"""Persistent RoboTwin execution engine used only in the simulator environment."""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict
from pathlib import Path
from threading import Event
from typing import Any, Mapping
from uuid import uuid4

import robotwin_simulation_probe_worker as probe
from robotwin_backend import (
    RoboTwinObservationProvider,
    RoboTwinRuntimeProfile,
    RoboTwinSensorBackend,
    load_runtime_profile,
)


class _StopSignal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.event = Event()

    def exists(self) -> bool:
        return self.event.is_set() or self.path.exists()


class RoboTwinPersistentEngine:
    """Own one scene; acquire/place share the validated phase generator.

    Initial candidate provenance and current scene identity remain separate.
    Sensor queries do not step physics; the simulator retains drive targets
    while the provider waits for the next bounded Action.
    """

    def __init__(self, profile: Mapping[str, Any]) -> None:
        self.profile = dict(profile)
        self.root = Path(profile["artifact_root"]).resolve()
        self.duration = float(profile["max_duration_s"])
        if not math.isfinite(self.duration) or self.duration <= 0:
            raise ValueError("max_duration_s must be finite and positive")
        self.stop = _StopSignal(Path(profile["stop_file"]))
        runtime = load_runtime_profile(Path(profile["runtime_profile"]).resolve())
        self.backend = RoboTwinSensorBackend(RoboTwinRuntimeProfile(
            runtime_root=Path(profile["runtime_root"]), artifact_root=self.root,
            task_name=runtime["task_name"], task_config=runtime["task_config"], embodiment=runtime["embodiment"],
        ))
        self.backend.reset(seed=runtime["seed"])
        self.epoch = uuid4().hex
        self.revision = 0
        self._advance_scene()
        self.observation = RoboTwinObservationProvider(self.backend)
        self._phases = None
        self._state: dict[str, Any] = {}
        self._request = None
        self._candidate = None

    def _advance_scene(self) -> str:
        self.revision += 1
        self.backend._scene_revision = f"{self.epoch}-{self.revision}"
        return self.backend._scene_revision

    def query(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if operation == "bind_observed_entities":
            layout = probe._load_json_artifact(self.root, arguments["layout_ref"])
            if (layout["scene_revision"] != self.backend.snapshot()["scene_revision"]
                    or layout["motion_authorized"] is not False):
                raise ValueError("entity binding requires current idle scene")
            mapping = {}
            for binding in layout["bindings"]:
                if binding["entity_ref"] in {"entity://block-red-1", "entity://block-green-1", "entity://block-blue-1"}:
                    raise ValueError("observed identity must not shadow execution identity")
                actor = probe._actor_for_entity(self.backend._task, binding["execution_entity_ref"])
                if actor is not getattr(self.backend._task, binding["actor_name"], None):
                    raise ValueError("execution actor binding differs from layout")
                mapping[binding["entity_ref"]] = actor
            self.backend._task._paos_observed_entities = mapping
            return {"scene_revision": layout["scene_revision"], "motion_authorized": False}
        if operation == "snapshot":
            return dict(self.backend.snapshot())
        if operation == "observe":
            captured = asdict(self.observation.observe(arguments["sensor_ref"]))
            captured["captured_at"] = captured["captured_at"].isoformat()
            return captured
        if operation == "route_readiness":
            from robotwin_route_planner import RoboTwinRouteEvaluator
            from robotwin_route_readiness_worker import _handle_factory

            evaluator = RoboTwinRouteEvaluator(
                Path(self.profile["runtime_root"]), Path(self.profile["runtime_profile"]),
                self.root, backend=self.backend,
            )
            return dict(_handle_factory(self.root, "persistent-route-readiness", evaluator)(arguments))
        if operation == "benchmark_scene_facts" and self.profile.get("allow_benchmark_scene_facts") is True:
            from robotwin_route_input_worker import capture_scene_facts
            return capture_scene_facts(runtime_root=Path(self.profile["runtime_root"]),
                                       runtime_profile=Path(self.profile["runtime_profile"]),
                                       artifact_root=self.root, calibration_ref=arguments["calibration_ref"], backend=self.backend)
        raise ValueError(f"unsupported persistent query: {operation}")

    def _prepare(self, arguments: Mapping[str, Any]) -> None:
        request = arguments["route_request"]
        probe.validate_route_request(request)
        if request["scene_revision"] != self.backend.snapshot()["scene_revision"]:
            raise ValueError("route is not bound to the current persistent scene")
        candidate = next(c for c in request["candidates"] if c["candidate_ref"] == arguments["candidate_ref"])
        if candidate["entity_ref"] != arguments["entity_ref"]:
            raise ValueError("candidate does not match the requested entity")
        assignment = probe._load_json_artifact(self.root, arguments["assignment_ref"])
        if assignment != arguments["assignment"]:
            raise ValueError("assignment artifact changed after preparation")
        for key in ("task_id", "assignment_ref", "entity_ref", "candidate_ref", "capability_snapshot_ref"):
            if assignment.get(key) != arguments[key]:
                raise ValueError(f"assignment execution binding mismatch: {key}")
        if assignment.get("scene_revision") != request["scene_revision"] or assignment.get("route_digest") != probe.route_geometry_digest(request):
            raise ValueError("assignment does not bind the current complete route")
        arms = assignment.get("selected_arm_ids")
        if not isinstance(arms, list) or len(arms) != 1 or arms[0] not in {"left", "right"}:
            raise ValueError("persistent execution requires one assigned arm")
        probe._validate_approval(
            self.root, arguments["approval_ref"], producer_id=self.profile["producer_id"],
            producer_profile_sha256=self.profile["producer_profile_sha256"],
            request=request, candidate_ref=candidate["candidate_ref"], profile=self.profile,
        )
        policies = probe._validate_request_policies(
            self.root, request, max_duration_s=self.duration,
            robot_identity=self.profile["embodiment_binding"]["robot_identity"],
            failure_recovery="hold_and_reconcile",
        )
        policies["execution_input_digests"][arguments["approval_ref"]] = probe._sha_bytes(
            probe._artifact_path(self.root, arguments["approval_ref"]).read_bytes()
        )
        policies["execution_input_digests"][arguments["assignment_ref"]] = probe._sha_bytes(
            probe._artifact_path(self.root, arguments["assignment_ref"]).read_bytes()
        )
        inputs = probe._validate_route_input_artifacts(self.root, request, candidate)
        geometry = probe._artifact_path(self.root, candidate["attached_object"]["geometry_ref"])
        if probe._sha_bytes(geometry.read_bytes()) != candidate["attached_object"]["geometry_sha256"]:
            raise ValueError("attached geometry binding mismatch")
        task = self.backend._task
        probe.bind_scene_table(task)
        state = probe._capture_dual_arm_state(task, request["scene_revision"])
        probe.validate_dual_arm_state(state)
        task.robot.left_planner.arm_id = "left"
        task.robot.right_planner.arm_id = "right"
        self._state = {
            "_assigned_arm": arms[0], "assignment_ref": arguments["assignment_ref"],
            "world_change_started": False, "simulator_steps": 0, "planner_object_attached": False,
            "object_lifted": False, "dual_arm_state": state, "held_arm": "left",
            "_controllers": probe._build_route_controllers(task, policies["motion_capability_documents"]),
            "_controller_source_sha256": probe._guard_controller_source_binding(policies["motion_capability_documents"]),
            "_artifact_root": self.root, "_execution_input_digests": policies["execution_input_digests"],
            "action_deadline": time.monotonic() + self.duration,
        }
        collision = request["collision_world"]
        raw = probe._artifact_path(self.root, collision["artifact_ref"]).read_bytes()
        world = json.loads(raw)
        if probe._sha_bytes(raw) != collision["sha256"] or world.get("world_digest") != collision["world_digest"]:
            raise ValueError("collision world binding mismatch")
        peer = {arm: probe._capture_peer_projection(task, state, arm) for arm in ("left", "right")}
        self._state["peer_arm_projection"] = peer
        self._state["collision_world_receipt"] = probe.apply_collision_world(
            {"left": task.robot.left_planner, "right": task.robot.right_planner}, world, peer_projections=peer,
        )
        probe._label_probe_actors(task)
        probe._validate_runtime_route_input_binding(task, candidate, inputs)
        self._request, self._candidate = request, candidate
        self._phases = probe.execute_candidate_phases(
            task, request, candidate, policies, deadline=self._state["action_deadline"],
            stop_file=self.stop, execution_state=self._state,
        )

    def execute(self, phase: str, arguments: Mapping[str, Any], cancel: Event) -> dict[str, Any]:
        self.stop.event = cancel
        start_steps = self._state.get("simulator_steps", 0)
        phases = []
        advancing = False
        try:
            if self.stop.exists():
                return {"status": "cancelled", "world_change_started": False, "outcome_known": True}
            if phase == "acquire":
                self._prepare(arguments)
                start_steps = 0
            elif phase != "place" or self._phases is None:
                raise ValueError("place requires a prepared held route")
            elif arguments.get("scene_revision") != self.backend.snapshot()["scene_revision"]:
                raise ValueError("place current scene binding mismatch")
            elif arguments.get("assignment_ref") != self._state["assignment_ref"]:
                raise ValueError("place must continue the acquisition assignment")
            self._state["action_deadline"] = time.monotonic() + self.duration
            while True:
                try:
                    advancing = True
                    settled = next(self._phases)
                    phases.append(settled)
                    if phase == "acquire" and settled["phase"] == "lift":
                        break
                except StopIteration as terminal:
                    if phase == "acquire":
                        raise ValueError("route ended before lift")
                    phases_result = terminal.value
                    if phases_result is None:
                        raise ValueError("route completed without contact validation")
                    self._verify_release()
                    self._phases = None
                    break
            result = {"status": "succeeded", "world_change_started": True, "outcome_known": True,
                      "new_scene_revision": self._advance_scene(), "source_scene_revision": self._request["scene_revision"]}
        except Exception as exc:
            changed = self._state.get("simulator_steps", 0) > start_steps
            stop_errors = []
            if advancing:
                for controller in self._state.get("_controllers", {}).values():
                    try:
                        controller.stop()
                    except Exception as stop_error:
                        stop_errors.append(type(stop_error).__name__)
            result = {"status": "unknown" if changed else "failed", "world_change_started": changed,
                      "outcome_known": not changed, "failure_owner": "execution", "failure_code": type(exc).__name__,
                      "error_detail": str(exc), "stop_confirmed": not stop_errors,
                      "stop_errors": stop_errors, "continuation_valid": not advancing}
            if changed:
                result["new_scene_revision"] = self._advance_scene()
        reference = f"artifact://persistent/{self.epoch}/action-{uuid4().hex}"
        probe._json_artifact(self.root, reference, {**result, "phase": phase, "phases": phases,
                            "simulator_steps": self._state.get("simulator_steps", 0),
                            "placement_measurement": self._state.get("placement_measurement"),
                            "contacts": self._state.get("contact_trace", [])})
        result["artifact_refs"] = [reference]
        return result

    def _verify_release(self) -> None:
        import numpy as np
        import transforms3d as t3d

        placement = probe._load_json_artifact(self.root, self._candidate["placement_target"]["provenance_ref"])
        target = np.asarray(placement["world_T_object_target"], dtype=float).reshape(4, 4)
        actual = probe._actor_for_entity(self.backend._task, self._candidate["entity_ref"]).get_pose()
        position_error = float(np.linalg.norm(np.asarray(actual.p) - target[:3, 3]))
        orientation_error = probe._orientation_error_rad(actual.q, t3d.quaternions.mat2quat(target[:3, :3]))
        tolerance = placement["semantic_tolerance"]
        self._state["placement_measurement"] = {"position_error_m": position_error, "orientation_error_rad": orientation_error}
        if position_error > tolerance["target_position_m"] or orientation_error > tolerance["target_orientation_rad"]:
            raise ValueError("after-state placement verification failed")

    def close(self) -> None:
        self.stop.event.set()
        try:
            for controller in self._state.get("_controllers", {}).values():
                controller.stop()
        finally:
            # Closing the isolated simulation destroys the world, never opens a gripper.
            self.backend.close()
