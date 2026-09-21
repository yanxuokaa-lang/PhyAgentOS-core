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
from robotwin_blocks_ranking_adapter import BlocksRankingRgbTaskAdapter, task_adapter

from robotwin20_adapter.persistent_action_approval import (
    DEFERRED_EXECUTION_CHECKS,
    RUNTIME_MONITORED_ACTION_MODE,
    validate_persistent_action_approval,
)

_RESERVED_EXECUTION_ACTORS = {
    entity_ref: actor_name
    for entity_ref, actor_name, _target_token in BlocksRankingRgbTaskAdapter.entities
}


class BindingPoseUnavailableError(ValueError):
    """The binding lacks the captured execution pose required for drift checks."""


class BindingPoseChangedError(ValueError):
    """An execution actor differs from its captured Runtime pose."""


class _StopSignal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.event = Event()

    def exists(self) -> bool:
        return self.event.is_set() or self.path.exists()


class PersistentVideoError(RuntimeError):
    """A physical phase settled but its required task video did not."""


class _TaskVideoArchive:
    """Accumulate all Action video for one PAOS task owner."""

    def __init__(self, root: Path, epoch: str, settings: Mapping[str, Any]) -> None:
        if set(settings) != {"enabled", "fps", "stride_steps"}:
            raise ValueError("persistent video settings are invalid")
        enabled = settings["enabled"]
        fps = settings["fps"]
        stride = settings["stride_steps"]
        if not isinstance(enabled, bool):
            raise ValueError("persistent video enabled must be boolean")
        if isinstance(fps, bool) or not isinstance(fps, (int, float)) or fps <= 0:
            raise ValueError("persistent video fps must be positive")
        if isinstance(stride, bool) or not isinstance(stride, int) or stride <= 0:
            raise ValueError("persistent video stride_steps must be a positive integer")
        self.root = root
        self.epoch = epoch
        self.enabled = enabled
        self.fps = float(fps)
        self.stride_steps = stride
        self.owner: str | None = None
        self.session_id: str | None = None
        self.segments: list[dict[str, dict[str, str]]] = []
        self.actions: list[dict[str, Any]] = []
        self.recorder: Any = None
        self.segment_prefix: str | None = None
        self.active: dict[str, Any] | None = None
        self.archives: dict[str, tuple[str, list, list]] = {}
        self.incomplete_owners: set[str] = set()
        self.latest_refs: dict[str, tuple[str, ...]] = {}

    def start_action(
        self,
        task: Any,
        *,
        owner: str,
        invocation_id: str,
        phase: str,
        simulator_steps: int,
    ) -> None:
        if not self.enabled:
            return
        if owner in self.incomplete_owners:
            raise PersistentVideoError("task video has an unrecorded execution segment")
        if self.recorder is not None:
            raise PersistentVideoError("persistent task video already has an active Action")
        if self.owner != owner:
            self.owner = owner
            self.session_id, self.segments, self.actions = self.archives.setdefault(
                owner, (uuid4().hex, [], [])
            )
        sequence = len(self.actions) + 1
        self.segment_prefix = (
            f"artifact://persistent/{self.epoch}/task-video-{self.session_id}/"
            f"segments/action-{sequence:04d}"
        )
        output_dir = probe._artifact_path(
            self.root,
            self.segment_prefix + "/video/head-camera.mp4",
            create_parent=True,
        ).parent
        self.recorder = probe._ProbeVideoRecorder(
            output_dir, fps=self.fps, stride_steps=self.stride_steps
        )
        self.active = {
            "sequence": sequence,
            "invocation_id": invocation_id,
            "phase": phase,
        }
        try:
            self.recorder.capture(task, simulator_steps, force=True)
        except Exception:
            self.incomplete_owners.add(owner)
            self.discard_active()
            raise

    def finish_action(
        self,
        task: Any,
        *,
        status: str,
        simulator_steps: int,
    ) -> tuple[str, ...]:
        if not self.enabled:
            return ()
        recorder, prefix, active = self.recorder, self.segment_prefix, self.active
        if recorder is None or prefix is None or active is None or self.session_id is None:
            return ()
        self.recorder = self.segment_prefix = self.active = None
        try:
            recorder.capture(task, simulator_steps, force=True)
            segment = recorder.finish(self.root, prefix)
        except Exception:
            self.incomplete_owners.add(self.owner)
            recorder.discard()
            raise
        self.segments.append(segment)
        self.actions.append({**active, "status": status, "simulator_steps": simulator_steps})
        cumulative_prefix = (
            f"artifact://persistent/{self.epoch}/task-video-{self.session_id}/"
            f"cumulative/action-{active['sequence']:04d}"
        )
        videos, metadata = probe.concatenate_probe_videos(
            self.root, self.segments, cumulative_prefix, fps=self.fps
        )
        manifest = probe._json_artifact(
            self.root,
            cumulative_prefix + "/manifest",
            {
                "schema_version": "paos-robotwin20-task-video/v1",
                "owner": self.owner,
                "session_id": self.session_id,
                "action_count": len(self.actions),
                "actions": list(self.actions),
                "views": videos,
                "video_metadata": metadata,
                "fps": self.fps,
                "stride_steps": self.stride_steps,
            },
        )
        refs = (
            manifest["artifact_ref"],
            videos["head_camera"]["artifact_ref"],
            videos["observer_camera"]["artifact_ref"],
        )
        if self.owner is not None:
            self.latest_refs[self.owner] = refs
        return refs

    def result(self, owner: str) -> dict[str, Any]:
        archive = self.archives.get(owner)
        if archive is None:
            return {"availability": "none", "action_count": 0, "artifact_refs": []}
        session_id, _segments, actions = archive
        refs = self.latest_refs.get(owner, ())
        return {
            "availability": "complete" if refs else "incomplete",
            "session_id": session_id,
            "action_count": len(actions),
            "actions": list(actions),
            "artifact_refs": list(refs),
        }

    def discard_active(self) -> None:
        recorder = self.recorder
        self.recorder = self.segment_prefix = self.active = None
        if recorder is not None:
            recorder.discard()


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
        self.runtime_profile = runtime
        self.task_adapter = task_adapter(runtime["task_name"])
        self._goal_facts_ref: str | None = None
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
        self.video = _TaskVideoArchive(
            self.root,
            self.epoch,
            profile.get(
                "video", {"enabled": False, "fps": 25.0, "stride_steps": 4}
            ),
        )

    def _advance_scene(self) -> str:
        self.revision += 1
        self.backend._scene_revision = f"{self.epoch}-{self.revision}"
        return self.backend._scene_revision

    def query(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if operation == "oracle_grasp_candidates":
            if set(arguments) != {
                "request", "provider_T_contact_center", "binding_ref"
            }:
                raise ValueError("oracle grasp query fields are invalid")
            request = arguments["request"]
            if not isinstance(request, dict):
                raise ValueError("oracle grasp request must be an object")
            calibration = probe._load_json_artifact(
                self.root, request["calibration_ref"]
            )
            value = self.task_adapter.oracle_grasp_candidates(
                self.backend._task,
                request,
                calibration=calibration,
                provider_to_contact_flat=arguments["provider_T_contact_center"],
                scene_revision=self.backend.snapshot()["scene_revision"],
            )
            evidence = value.pop("oracle_evidence")
            reference = (
                f"artifact://persistent/{self.epoch}/oracle-grasps/{uuid4().hex}"
            )
            artifact = probe._json_artifact(
                self.root,
                reference,
                {
                    "schema_version": "paos-robotwin20-oracle-grasp-evidence/v1",
                    "task_name": self.task_adapter.task_name,
                    "scene_revision": request["scene_revision"],
                    "observation_ref": request["observation_ref"],
                    "calibration_ref": request["calibration_ref"],
                    "binding_ref": arguments["binding_ref"],
                    "geometry_source": value["geometry_source"],
                    "template_evidence": evidence,
                    "motion_authorized": False,
                },
            )
            return {**value, "oracle_evidence_ref": artifact["artifact_ref"]}
        if operation == "task_goal_facts":
            if arguments:
                raise ValueError("task goal facts do not accept arguments")
            value = self.task_adapter.goal_facts(
                self.backend._task, seed=self.runtime_profile["seed"]
            )
            if self._goal_facts_ref is None:
                reference = f"artifact://persistent/{self.epoch}/task-goals"
                artifact = probe._json_artifact(self.root, reference, value)
                self._goal_facts_ref = artifact["artifact_ref"]
            return {
                "status": "available",
                **value,
                "goal_ref": self._goal_facts_ref,
                "evidence_refs": [self._goal_facts_ref],
            }
        if operation == "benchmark_result":
            task_id = arguments.get("task_id")
            if set(arguments) != {"task_id"} or not isinstance(task_id, str) or not task_id:
                raise ValueError("benchmark result requires one task_id")
            value = self.task_adapter.benchmark_result(
                self.backend._task,
                seed=self.runtime_profile["seed"],
                scene_revision=self.backend.snapshot()["scene_revision"],
            )
            value["task_id"] = task_id
            value["task_video"] = self.video.result(f"paos:{task_id}")
            reference = (
                f"artifact://persistent/{self.epoch}/benchmark-results/{uuid4().hex}"
            )
            artifact = probe._json_artifact(self.root, reference, value)
            return {**value, "artifact_ref": artifact["artifact_ref"]}
        if operation == "bind_observed_entities":
            binding_record = probe._load_json_artifact(self.root, arguments["binding_ref"])
            if (binding_record["scene_revision"] != self.backend.snapshot()["scene_revision"]
                    or binding_record["motion_authorized"] is not False):
                raise ValueError("entity binding requires current idle scene")
            bindings = binding_record["bindings"]
            observed_refs = [binding["entity_ref"] for binding in bindings]
            execution_refs = [binding["execution_entity_ref"] for binding in bindings]
            if len(set(observed_refs)) != len(observed_refs) or len(set(execution_refs)) != len(execution_refs):
                raise ValueError("entity binding correspondence must be one-to-one")
            mapping = {}
            observed_bindings = {}
            captured_objects = binding_record.get("scene_facts", {}).get("objects", [])
            for binding in bindings:
                expected_actor_name = _RESERVED_EXECUTION_ACTORS.get(binding["entity_ref"])
                if expected_actor_name is not None and (
                    binding["execution_entity_ref"] != binding["entity_ref"]
                    or binding["actor_name"] != expected_actor_name
                ):
                    raise ValueError("reserved observed identity differs from execution identity")
                actor = (
                    getattr(self.backend._task, expected_actor_name, None)
                    if expected_actor_name is not None
                    else probe._actor_for_entity(
                        self.backend._task, binding["execution_entity_ref"]
                    )
                )
                if actor is not getattr(self.backend._task, binding["actor_name"], None):
                    raise ValueError("execution actor binding differs from observation")
                import numpy as np

                captured = [item for item in captured_objects
                            if item.get("entity_ref") == binding["execution_entity_ref"]
                            and item.get("actor_name") == binding["actor_name"]]
                if len(captured) != 1:
                    raise BindingPoseUnavailableError("binding requires one captured execution actor pose")
                try:
                    expected = np.asarray(captured[0]["world_T_object"], dtype=float).reshape(4, 4)
                except (KeyError, TypeError, ValueError) as exc:
                    raise BindingPoseUnavailableError("captured execution actor pose is invalid") from exc
                if not np.isfinite(expected).all():
                    raise BindingPoseUnavailableError("captured execution actor pose is invalid")
                if not np.allclose(actor.get_pose().to_transformation_matrix(), expected, atol=1e-6, rtol=0):
                    raise BindingPoseChangedError("execution actor moved since binding")
                mapping[binding["entity_ref"]] = actor
                observed_bindings[binding["entity_ref"]] = {
                    "captured_pose": expected.tolist(),
                    "model": binding_record["objects"][binding["entity_ref"]],
                }
            self.backend._task._paos_observed_entities = mapping
            self.backend._task._paos_observed_bindings = observed_bindings
            return {"scene_revision": binding_record["scene_revision"], "motion_authorized": False}
        if operation == "snapshot":
            return {**dict(self.backend.snapshot()), "scene_validity": "action_driven"}
        if operation == "observe":
            captured = asdict(self.observation.observe(arguments["sensor_ref"]))
            captured["captured_at"] = captured["captured_at"].isoformat()
            return captured
        if operation in {"route_readiness", "contact_qualification"}:
            from robotwin_route_planner import RoboTwinRouteEvaluator
            from robotwin_route_readiness_worker import _handle_factory

            from robotwin20_adapter.preparation_deadline import PreparationDeadline

            evaluator = RoboTwinRouteEvaluator(
                Path(self.profile["runtime_root"]), Path(self.profile["runtime_profile"]),
                self.root, backend=self.backend,
                contact_arms=arguments["allowed_arms"] if operation == "contact_qualification" else None,
                deadline=PreparationDeadline.start(arguments["timeout_s"]) if operation == "contact_qualification" else None,
            )
            if operation == "contact_qualification":
                probe.validate_route_request(arguments["route_request"])
                return evaluator(arguments["route_request"])
            deferred = (
                DEFERRED_EXECUTION_CHECKS
                if self.profile.get("simulation_action_mode")
                == RUNTIME_MONITORED_ACTION_MODE
                else ()
            )
            return dict(
                _handle_factory(
                    self.root,
                    "persistent-route-readiness",
                    evaluator,
                    deferred_execution_checks=deferred,
                )(arguments)
            )
        if operation in {"benchmark_scene_facts", "execution_scene_facts"} and self.profile.get("allow_benchmark_scene_facts") is True:
            from robotwin_route_input_worker import capture_scene_facts
            return capture_scene_facts(runtime_root=Path(self.profile["runtime_root"]),
                                       runtime_profile=Path(self.profile["runtime_profile"]),
                                       artifact_root=self.root, calibration_ref=arguments["calibration_ref"], backend=self.backend,
                                       include_targets=operation == "benchmark_scene_facts")
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
        validate_persistent_action_approval(
            self.root,
            arguments["approval_ref"],
            task_name=self.task_adapter.task_name,
            mode=self.profile.get("simulation_action_mode", "disabled"),
            route_request=request,
            candidate_ref=candidate["candidate_ref"],
            assignment=assignment,
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
        world_source = probe._load_json_artifact(self.root, request["collision_world"]["artifact_ref"])
        scene_source = probe._load_json_artifact(self.root, world_source["source_scene_facts_ref"])
        if (("observed_collision" in world_source
             or candidate["attached_object"].get("object_frame_id", "").startswith(
                 "observed-envelope/"
             ))
                and scene_source.get("geometry_source") != "observation"):
            raise ValueError("observed route requires observed collision geometry")
        if scene_source.get("geometry_source") == "observation":
            task._paos_observed_support = scene_source.get("support_surface")
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
        from robotwin_observed_collision import configure_observed_collision
        configure_observed_collision(task, world, self.root)
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

    def execute(
        self,
        phase: str,
        arguments: Mapping[str, Any],
        cancel: Event,
        *,
        owner: str,
        invocation_id: str,
    ) -> dict[str, Any]:
        self.stop.event = cancel
        start_steps = self._state.get("simulator_steps", 0)
        phases = []
        advancing = False
        video_refs: tuple[str, ...] = ()
        physical_phase_completed = False
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
            self.video.start_action(
                self.backend._task,
                owner=owner,
                invocation_id=invocation_id,
                phase=phase,
                simulator_steps=int(self._state.get("simulator_steps", 0)),
            )
            self._state["video_recorder"] = self.video.recorder
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
            physical_phase_completed = True
            try:
                video_refs = self.video.finish_action(
                    self.backend._task,
                    status="succeeded",
                    simulator_steps=int(self._state.get("simulator_steps", 0)),
                )
            except Exception as exc:
                raise PersistentVideoError(str(exc)) from exc
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
            evidence_failure = isinstance(exc, PersistentVideoError) and physical_phase_completed
            result = {"status": "failed" if evidence_failure else "unknown" if changed else "failed", "world_change_started": changed,
                      "outcome_known": True if evidence_failure else not changed,
                      "failure_owner": "evidence" if evidence_failure else "execution", "failure_code": type(exc).__name__,
                      "error_detail": str(exc), "stop_confirmed": not stop_errors,
                      "stop_errors": stop_errors, "continuation_valid": not advancing}
            if not evidence_failure:
                try:
                    video_refs = self.video.finish_action(
                        self.backend._task,
                        status=result["status"],
                        simulator_steps=int(self._state.get("simulator_steps", 0)),
                    )
                except Exception as video_error:
                    self.video.discard_active()
                    result["video_evidence_error"] = type(video_error).__name__
            if changed:
                result["new_scene_revision"] = self._advance_scene()
        self._state.pop("video_recorder", None)
        reference = f"artifact://persistent/{self.epoch}/action-{uuid4().hex}"
        probe._json_artifact(self.root, reference, {**result, "phase": phase, "phases": phases,
                            "simulator_steps": self._state.get("simulator_steps", 0),
                            "placement_measurement": self._state.get("placement_measurement"),
                            "contacts": self._state.get("contact_trace", []),
                            "task_video_refs": list(video_refs)})
        result["artifact_refs"] = [reference, *video_refs]
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
        self.video.discard_active()
        try:
            for controller in self._state.get("_controllers", {}).values():
                controller.stop()
        finally:
            # Closing the isolated simulation destroys the world, never opens a gripper.
            self.backend.close()
