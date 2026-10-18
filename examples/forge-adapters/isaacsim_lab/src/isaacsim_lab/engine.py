"""LabUtopia-backed PAOS cycle engine.

Isaac Sim is imported only inside the execution method.  The PAOS process can
therefore inspect and prepare a lab route in a normal Python environment while
the actual motion remains owned by the LabUtopia simulator process.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback
from copy import deepcopy
from pathlib import Path
from threading import Event
from typing import Any, Mapping, Protocol, Sequence

from .profile import LabProfileError, LabUtopiaProfile


class IsaacLabRuntimeError(RuntimeError):
    """The requested Isaac Sim execution cannot be started or observed."""


class _EpisodeVideoRecorder:
    """Best-effort recorder for one episode's rendered camera observations."""

    def __init__(self, path: Path, cv2_module: Any, np_module: Any, *, fps: float = 60.0):
        self.path = path
        self._cv2 = cv2_module
        self._np = np_module
        self._fps = fps
        self._writer = None
        self._frame_count = 0
        self._error: str | None = None
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, camera_display: Any, overlay: Sequence[str] = ()) -> None:
        if not isinstance(camera_display, Mapping):
            return
        try:
            frame = _compose_camera_frame(camera_display, self._cv2, self._np)
            if frame is None:
                return
            for index, line in enumerate(overlay):
                self._cv2.putText(
                    frame,
                    str(line),
                    (8, 20 + index * 18),
                    self._cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (255, 255, 255),
                    1,
                    self._cv2.LINE_AA,
                )
            if self._writer is None:
                height, width = frame.shape[:2]
                fourcc = self._cv2.VideoWriter_fourcc(*"mp4v")
                self._writer = self._cv2.VideoWriter(
                    str(self.path), fourcc, self._fps, (int(width), int(height))
                )
                if not self._writer.isOpened():
                    self._error = "video_writer_not_opened"
                    self._writer.release()
                    self._writer = None
                    return
            self._writer.write(frame)
            self._frame_count += 1
        except Exception as exc:  # video is observation evidence, never a motion gate
            self._error = type(exc).__name__

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    def metadata(self) -> dict[str, Any]:
        available = bool(self._frame_count and self.path.is_file() and self.path.stat().st_size > 0)
        result = {
            "video_path": str(self.path),
            "video_frame_count": self._frame_count,
            "video_available": available,
        }
        if self._error:
            result["video_error"] = self._error
        return result


def _compose_camera_frame(camera_display: Mapping[str, Any], cv2_module: Any, np_module: Any):
    frames = []
    for image_data in camera_display.values():
        image = np_module.asarray(image_data)
        if image.ndim != 3:
            continue
        if image.shape[0] in (1, 3, 4) and image.shape[-1] not in (1, 3, 4):
            image = image.transpose(1, 2, 0)
        if image.shape[-1] == 1:
            image = cv2_module.cvtColor(image, cv2_module.COLOR_GRAY2BGR)
        elif image.shape[-1] == 4:
            image = cv2_module.cvtColor(image, cv2_module.COLOR_RGBA2BGR)
        elif image.shape[-1] == 3:
            image = cv2_module.cvtColor(image, cv2_module.COLOR_RGB2BGR)
        else:
            continue
        frames.append(np_module.ascontiguousarray(image))
    if not frames:
        return None
    height = min(frame.shape[0] for frame in frames)
    normalized = []
    for frame in frames:
        if frame.shape[0] != height:
            width = max(1, round(frame.shape[1] * height / frame.shape[0]))
            frame = cv2_module.resize(frame, (width, height))
        normalized.append(frame)
    return np_module.hstack(normalized)


class IsaacLabBackend(Protocol):
    def run_cycle(self, arguments: Mapping[str, Any], cancel: Event) -> Mapping[str, Any]: ...


class IsaacSimLabEngine:
    """PAOS provider engine that delegates one pour invocation to LabUtopia."""

    def __init__(self, profile: LabUtopiaProfile, *, backend: IsaacLabBackend | None = None):
        self.profile = profile
        self.backend = backend or LabUtopiaBackend(profile)

    def cycle_capability(self, operation: str) -> dict[str, Any]:
        available = operation == "pour_cycle" and callable(getattr(self.backend, "run_cycle", None))
        if available:
            try:
                self.profile.validate_paths()
                available = _isaac_runtime_available()
            except LabProfileError:
                available = False
        return {
            "operation": operation,
            "preparation": available,
            "execution": available,
            "feedback": available,
            "return": available,
            "dry_run": False,
            "provider": "labutopia_isaacsim",
            "motion_authorized": bool(available),
        }

    def prepare_cycle(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        operation = arguments.get("operation") if isinstance(arguments, Mapping) else None
        if operation != "pour_cycle":
            return {"status": "unavailable", "motion_authorized": False, "error": "unsupported_cycle_operation"}
        try:
            self.profile.validate_paths()
            if not _isaac_runtime_available():
                raise IsaacLabRuntimeError("isaacsim_unavailable_in_active_python")
            prepared = self.profile.paos_input(arguments, operation=operation)
        except (LabProfileError, IsaacLabRuntimeError) as exc:
            return {"status": "unavailable", "motion_authorized": False, "error": str(exc)}
        return {
            "status": "available",
            "motion_authorized": False,
            "entity_ref": prepared["entity_ref"],
            "arguments": deepcopy(prepared),
            "provider": "labutopia_isaacsim",
        }

    def execute_cycle(
        self,
        operation: str,
        arguments: Mapping[str, Any],
        cancel: Event,
        **context: Any,
    ) -> dict[str, Any]:
        del context
        if operation != "pour_cycle":
            return {"status": "unknown", "outcome_known": False, "failure_code": "unsupported_cycle_operation"}
        if not self.cycle_capability(operation)["execution"]:
            return {"status": "unknown", "outcome_known": False, "failure_code": "isaacsim_unavailable"}
        try:
            result = self.backend.run_cycle(deepcopy(dict(arguments)), cancel)
        except Exception as exc:
            return {
                "status": "unknown",
                "outcome_known": False,
                "world_change_started": True,
                "failure_owner": "isaacsim_adapter",
                "failure_code": type(exc).__name__,
            }
        if not isinstance(result, Mapping):
            raise IsaacLabRuntimeError("Isaac backend returned a non-mapping result")
        return dict(result)


class LabUtopiaBackend:
    """Run one LabUtopia pick/pour episode and return PAOS evidence."""

    def __init__(self, profile: LabUtopiaProfile):
        self.profile = profile
        self._last_video_info: dict[str, Any] = {}

    def run_cycle(self, arguments: Mapping[str, Any], cancel: Event) -> Mapping[str, Any]:
        if os.environ.get("OMNI_KIT_ACCEPT_EULA", "").lower() not in {"y", "yes", "1", "true"}:
            raise IsaacLabRuntimeError("OMNI_KIT_ACCEPT_EULA must be accepted before starting Isaac Sim")
        if cancel.is_set():
            return {"status": "unknown", "outcome_known": False, "world_change_started": False}

        if os.environ.get("PAOS_ISAAC_WORKER") != "1":
            return self._run_worker(arguments, cancel)

        return self._run_inprocess(arguments, cancel, Path(os.environ["PAOS_ISAAC_RESULT_PATH"]))

    def _run_worker(self, arguments: Mapping[str, Any], cancel: Event) -> Mapping[str, Any]:
        output_dir = self.profile.lab_root / "outputs" / "paos-pour-cycle"
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = f"{os.getpid()}-{time.monotonic_ns()}"
        input_path = output_dir / f"input-{suffix}.json"
        result_path = output_dir / f"result-{suffix}.json"
        input_path.write_text(json.dumps(dict(arguments), ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ)
        env.update({
            "PAOS_ISAAC_WORKER": "1",
            "PAOS_ISAAC_PROFILE": str(self.profile_path),
            "PAOS_ISAAC_INPUT_PATH": str(input_path),
            "PAOS_ISAAC_RESULT_PATH": str(result_path),
        })
        process = subprocess.Popen(
            [sys.executable, "-m", "isaacsim_lab.worker"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        while process.poll() is None:
            if cancel.is_set():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return {"status": "unknown", "outcome_known": False, "world_change_started": True,
                        "failure_owner": "isaacsim_adapter", "failure_code": "cancelled_worker",
                        "video_path": str(result_path.with_suffix(".mp4")),
                        "video_frame_count": 0,
                        "video_available": result_path.with_suffix(".mp4").is_file()}
            time.sleep(0.1)
        if not result_path.is_file():
            return {"status": "unknown", "outcome_known": False, "world_change_started": True,
                    "failure_owner": "isaacsim_adapter", "failure_code": "worker_no_result",
                    "error_detail": "Isaac worker exited without a result artifact",
                    "video_path": str(result_path.with_suffix(".mp4")),
                    "video_frame_count": 0,
                    "video_available": result_path.with_suffix(".mp4").is_file()}
        try:
            return json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {"status": "unknown", "outcome_known": False, "world_change_started": True,
                    "failure_owner": "isaacsim_adapter", "failure_code": type(exc).__name__,
                    "video_path": str(result_path.with_suffix(".mp4")),
                    "video_frame_count": 0,
                    "video_available": result_path.with_suffix(".mp4").is_file()}

    @property
    def profile_path(self) -> Path:
        """Return the profile path used by the worker environment."""
        value = getattr(self.profile, "profile_path", None)
        if isinstance(value, Path):
            return value
        raise IsaacLabRuntimeError("LabUtopiaProfile must retain its source profile path for worker execution")

    def _run_inprocess(self, arguments: Mapping[str, Any], cancel: Event, result_path: Path) -> Mapping[str, Any]:
        from isaacsim import SimulationApp

        self._last_video_info = {}
        app = SimulationApp({"headless": self.profile.headless})
        try:
            result = self._run_episode(app, arguments, cancel, result_path.with_suffix(".mp4"))
        except Exception as exc:
            result = {
                "status": "unknown",
                "outcome_known": False,
                "world_change_started": False,
                "failure_owner": "isaacsim_adapter",
                "failure_code": type(exc).__name__,
                "error_detail": traceback.format_exc()[-2048:],
            }
            result.update(self._last_video_info)
        finally:
            result_path.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            app.close()
        return result

    def _run_episode(
        self,
        app: Any,
        arguments: Mapping[str, Any],
        cancel: Event,
        video_path: Path | None = None,
    ) -> dict[str, Any]:
        self._prepend_lab_root()
        import numpy as np
        import omni.usd
        from controllers.atomic_actions.place_controller import PlaceController
        from factories.controller_factory import create_controller
        from factories.robot_factory import create_robot
        from isaacsim.core.api import World
        from isaacsim.core.utils.stage import add_reference_to_stage
        from omegaconf import OmegaConf, open_dict
        from scipy.spatial.transform import Rotation
        from tasks.pickpour_task import PickPourTask
        from utils.object_utils import ObjectUtils

        cfg = OmegaConf.load(str(self.profile.config_path))
        with open_dict(cfg):
            cfg.usd_path = str(self.profile.scene_usd_path)
            cfg.mode = "collect"
            cfg.task_type = "pickpour"
            cfg.controller_type = "pickpour"
            cfg.max_episodes = 1
            cfg.target_path = self.profile.destination_path
            cfg.multi_run.run_dir = str(self.profile.lab_root / "outputs" / "paos-pour-cycle")
            cfg.task.max_steps = max(int(cfg.task.max_steps), 1800)
            cfg.task.obj_paths = [{
                "path": self.profile.source_path,
                "position_range": {
                    "x": [0.25, 0.30], "y": [0.02, 0.08], "z": [0.81, 0.81],
                },
            }]

        world = World(stage_units_in_meters=1.0, physics_prim_path="/physicsScene", backend="numpy")
        robot = create_robot(
            cfg.robot.type,
            position=np.array(cfg.robot.position),
            usd_path=str(self.profile.robot_usd_path),
        )
        stage = omni.usd.get_context().get_stage()
        add_reference_to_stage(usd_path=str(self.profile.scene_usd_path), prim_path="/World")
        ObjectUtils.get_instance(stage)
        task = PickPourTask(cfg=cfg, world=world, stage=stage, robot=robot)
        controller = create_controller(cfg.controller_type, cfg=cfg, robot=robot)
        task.reset()
        world.play()

        initial_position = None
        initial_quaternion = None
        samples: list[dict[str, Any]] = []
        placement = None
        placement_started = False
        pickpour_success = False
        placement_done = False
        step = 0
        dt = 1.0 / 60.0
        video_path = video_path or (self.profile.lab_root / "outputs" / "paos-pour-cycle" / "episode.mp4")
        try:
            import cv2
        except Exception as exc:  # rendering remains usable even if codec support is absent
            recorder = None
            video_info = {
                "video_path": str(video_path),
                "video_frame_count": 0,
                "video_available": False,
                "video_error": type(exc).__name__,
            }
        else:
            recorder = _EpisodeVideoRecorder(video_path, cv2, np, fps=60.0)
            video_info = recorder.metadata()

        cancelled = False
        result = None
        try:
            while app.is_running() and step < int(cfg.task.max_steps):
                if cancel.is_set():
                    cancelled = True
                    break
                world.step(render=True)
                state = task.step()
                if state is None:
                    step += 1
                    continue
                if initial_position is None:
                    initial_position = np.asarray(state["object_position"], dtype=float).copy()
                    initial_quaternion = np.asarray(state["object_quaternion"], dtype=float).copy()
                now = step * dt
                controller_phase = (
                    "placing" if placement_started
                    else getattr(getattr(controller, "current_phase", None), "value", "unknown")
                )
                sample = self._sample(
                    state,
                    initial_position,
                    initial_quaternion,
                    now,
                    np,
                    Rotation,
                    controller_phase,
                )
                samples.append(sample)
                if recorder is not None:
                    recorder.write(
                        state.get("camera_display"),
                        (
                            f"step={step} phase={controller_phase}",
                            f"possession={sample['possession_state']} gripper={sample['gripper_state']}",
                            f"tilt={sample['tilt_rad']:.3f} align={sample['alignment_error_m']:.3f}m",
                        ),
                    )

                if not placement_started:
                    if controller_phase == "pouring":
                        state = dict(state)
                        state["target_position"] = _pour_controller_target(state, self.profile, np, Rotation)
                    action, done, success = controller.step(state)
                    if action is not None:
                        robot.get_articulation_controller().apply_action(action)
                    if done and success:
                        pickpour_success = True
                        placement_started = True
                        placement = PlaceController(
                            name="paos_place_controller",
                            cspace_controller=controller.rmp_controller,
                            gripper=robot.gripper,
                        )
                        placement.reset()
                else:
                    action = placement.forward(
                        place_position=initial_position,
                        current_joint_positions=state["joint_positions"],
                        gripper_control=controller.gripper_control,
                        gripper_position=state["gripper_position"],
                    )
                    if action is not None:
                        robot.get_articulation_controller().apply_action(action)
                    if placement.is_done():
                        placement_done = True
                        samples.append(self._sample(
                            state, initial_position, initial_quaternion, now + dt, np, Rotation, "placing"
                        ))
                        break
                step += 1

            if cancelled:
                result = {
                    "status": "unknown",
                    "outcome_known": False,
                    "world_change_started": bool(samples),
                    "entity_ref": arguments["entity_ref"],
                    "destination_ref": arguments["destination_ref"],
                    "return_destination_ref": arguments["return_destination_ref"],
                    "feedback_observations": samples,
                    "feedback_source_profile": self.profile.source_profile(),
                    "evaluation_profile": self.profile.evaluation_profile(),
                }
            else:
                final = samples[-1] if samples else {}
                events = _phase_events(samples, pickpour_success, placement_done, self.profile)
                succeeded = _episode_succeeded(pickpour_success, placement_done, events)
                result = {
                    "status": "succeeded" if succeeded else "failed" if samples else "unknown",
                    "outcome_known": bool(samples),
                    "world_change_started": bool(samples),
                    "entity_ref": arguments["entity_ref"],
                    "destination_ref": arguments["destination_ref"],
                    "return_destination_ref": arguments["return_destination_ref"],
                    "phase_events": events,
                    "feedback_observations": samples,
                    "feedback_source_profile": self.profile.source_profile(),
                    "evaluation_profile": self.profile.evaluation_profile(),
                    "possession_state": "empty" if succeeded else "uncertain",
                    "object_support_state": "on_support" if succeeded else "unknown",
                    "new_scene_revision": f"{arguments['scene_revision']}-pour-{step}" if succeeded else None,
                    "artifact_refs": [f"artifact://labutopia/paos-pour/{arguments['scene_revision']}-{step}"],
                    "evidence_refs": [f"artifact://labutopia/paos-pour/{arguments['scene_revision']}-{step}"],
                    "final_object_observation": final,
                }
        finally:
            try:
                world.stop()
            finally:
                if recorder is not None:
                    recorder.close()
                    video_info = recorder.metadata()
                self._last_video_info = dict(video_info)

        if result is None:
            raise IsaacLabRuntimeError("Isaac episode ended without a result")
        result.update(video_info)
        return result

    def _prepend_lab_root(self) -> None:
        root = str(self.profile.lab_root)
        if root not in sys.path:
            sys.path.insert(0, root)

    def _sample(self, state, initial_position, initial_quaternion, timestamp, np, rotation_cls, controller_phase):
        position = np.asarray(state["object_position"], dtype=float)
        target = np.asarray(state["target_position"], dtype=float)
        quat = np.asarray(state["object_quaternion"], dtype=float)
        source_size = np.asarray(state["object_size"], dtype=float)
        relative = rotation_cls.from_quat(initial_quaternion).inv() * rotation_cls.from_quat(quat)
        tilt = float(relative.magnitude())
        pour_axis = np.asarray(self.profile.source_pour_axis, dtype=float)
        pour_point = position + rotation_cls.from_quat(quat).apply(pour_axis * (source_size[2] / 2.0))
        alignment = float(np.linalg.norm(pour_point[:2] - target[:2]))
        joint_positions = np.asarray(state.get("joint_positions", []), dtype=float).reshape(-1)
        gripper_joints = joint_positions[-2:] if joint_positions.size >= 2 else np.asarray([], dtype=float)
        gripper_opening = float(np.max(np.abs(gripper_joints))) if gripper_joints.size else None
        gripper_state = (
            "unknown" if gripper_opening is None or not np.isfinite(gripper_opening)
            else "closed" if gripper_opening <= self.profile.gripper_closed_max_m
            else "open"
        )
        gripper_position = np.asarray(state.get("gripper_position", []), dtype=float).reshape(-1)
        object_gripper_distance = None
        if gripper_position.size >= 3 and np.all(np.isfinite(gripper_position)):
            object_gripper_distance = float(np.linalg.norm(position - gripper_position[:3]))
        object_lifted = bool(position[2] > initial_position[2] + self.profile.object_lift_threshold_m)
        grasp = bool(
            gripper_state == "closed"
            and object_lifted
            and object_gripper_distance is not None
            and object_gripper_distance <= self.profile.grasp_distance_tolerance_m
        )
        return {
            "timestamp_s": float(timestamp),
            "frame_id": self.profile.frame_id,
            "calibration_ref": self.profile.calibration_ref,
            "container_frame_id": self.profile.container_frame_id,
            "grasp_state": "holding" if grasp else "empty",
            "possession_state": "holding" if grasp else "empty",
            "controller_phase": controller_phase,
            "gripper_state": gripper_state,
            "gripper_opening_m": gripper_opening,
            "object_lifted": object_lifted,
            "object_gripper_distance_m": object_gripper_distance,
            "feedback_valid": True,
            "grasp_valid": grasp,
            "target_container_aligned": alignment <= self.profile.alignment_tolerance_m,
            "alignment_error_m": alignment,
            "source_pour_point": {"x_m": float(pour_point[0]), "y_m": float(pour_point[1]), "z_m": float(pour_point[2]), "frame_id": self.profile.frame_id},
            "tilt_rad": tilt,
        }


def _phase_events(samples, pickpour_success: bool, placement_done: bool, profile: LabUtopiaProfile):
    if not samples:
        return []
    last = float(samples[-1]["timestamp_s"])
    grasp = next((sample for sample in samples if sample["grasp_valid"]), None)
    aligned = next((sample for sample in samples if sample["target_container_aligned"] and sample["grasp_valid"]), None)
    window = _continuous_pour_window(samples, profile)
    returned = next((sample for sample in reversed(samples) if sample["grasp_valid"] and sample["tilt_rad"] <= profile.tilt_tolerance_rad), None)
    if not grasp or not pickpour_success:
        return _failed_events("acquire", samples, "grasp_not_confirmed")
    if not aligned:
        return _failed_events("transport", samples, "container_not_aligned")
    if window is None:
        return _append_placement_events(
            _failed_events("process", samples, "continuous_pour_window_not_observed"),
            samples,
            placement_done,
            last,
        )
    window_start, window_end = window
    process_end = returned or samples[-1]
    events = [
        _event("acquire", 0.0, grasp["timestamp_s"], {"grasp_confirmed": True, "possession_state": "holding"}),
        _event("transport", grasp["timestamp_s"], aligned["timestamp_s"], {"route_completed": True, "possession_state": "holding"}),
        _event("process", window_start, window_end, {"possession_state": "holding", "continuous_window_s": window_end - window_start}),
        _event("reorient_exit", process_end["timestamp_s"], max(last, process_end["timestamp_s"] + 0.01), {"tool_reoriented_or_exited": True, "possession_state": "holding"}),
    ]
    return _append_placement_events(events, samples, placement_done, process_end["timestamp_s"])


def _continuous_pour_window(samples, profile):
    """Find one uninterrupted grasp/alignment/tilt window of the required duration."""
    start = None
    previous = None
    for sample in samples:
        qualifies = (
            sample["grasp_valid"]
            and sample["target_container_aligned"]
            and profile.tilt_rad - profile.tilt_tolerance_rad <= sample["tilt_rad"] <= profile.maximum_tilt_rad
        )
        timestamp = float(sample["timestamp_s"])
        if not qualifies or (previous is not None and timestamp - previous > profile.max_sample_gap_s):
            start = None
            previous = None
            continue
        if start is None:
            start = timestamp
        previous = timestamp
        if timestamp - start >= profile.hold_s:
            return start, timestamp
    return None


def diagnose_pour_observations(observations: Sequence[Mapping[str, Any]], profile: LabUtopiaProfile) -> dict[str, Any]:
    """Summarize the measured pour bottleneck without starting a simulator."""
    samples = [item for item in observations if isinstance(item, Mapping)]
    lower = profile.tilt_rad - profile.tilt_tolerance_rad
    upper = profile.maximum_tilt_rad
    grasp_aligned = [item for item in samples if item.get("grasp_valid") is True and item.get("target_container_aligned") is True]
    joint = [
        item for item in grasp_aligned
        if _number(item.get("tilt_rad")) is not None and lower <= float(item["tilt_rad"]) <= upper
    ]
    max_grasp_tilt = max(
        (_number(item.get("tilt_rad")) for item in samples if item.get("grasp_valid") is True and _number(item.get("tilt_rad")) is not None),
        default=None,
    )
    max_grasp_aligned_tilt = max(
        (_number(item.get("tilt_rad")) for item in grasp_aligned if _number(item.get("tilt_rad")) is not None),
        default=None,
    )
    window = _continuous_pour_window(samples, profile) if samples else None
    if not samples:
        bottleneck = "no_feedback"
    elif not joint and max_grasp_aligned_tilt is not None and max_grasp_aligned_tilt < lower:
        bottleneck = "alignment_lost_before_target_tilt"
    elif joint and window is None:
        bottleneck = "continuous_hold_insufficient"
    elif window is not None:
        bottleneck = "qualified_window"
    else:
        bottleneck = "feedback_did_not_qualify"
    return {
        "observation_count": len(samples),
        "joint_sample_count": len(joint),
        "target_tilt_lower_rad": lower,
        "maximum_tilt_rad": upper,
        "hold_s": profile.hold_s,
        "max_grasp_tilt_rad": max_grasp_tilt,
        "max_grasp_aligned_tilt_rad": max_grasp_aligned_tilt,
        "continuous_window": list(window) if window is not None else None,
        "bottleneck": bottleneck,
    }


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _pour_controller_target(state, profile, np, rotation_cls):
    """Compensate the provider controller target for the measured mouth offset."""
    target = np.asarray(state["target_position"], dtype=float).copy()
    quat = np.asarray(state["object_quaternion"], dtype=float)
    size = np.asarray(state["object_size"], dtype=float)
    mouth_offset = rotation_cls.from_quat(quat).apply(np.asarray(profile.source_pour_axis) * (size[2] / 2.0))
    return target - mouth_offset


def _append_placement_events(events, samples, placement_done, process_end):
    if not placement_done:
        events.append({"phase": "stow", "status": "unknown", "outcome_known": False, "started_at_s": float(samples[-1]["timestamp_s"]), "facts": {}})
        return events
    base = max(float(samples[-1]["timestamp_s"]), process_end + 0.01)
    events.extend([
        _event("stow", base, base + 0.01, {"object_support_state": "on_support"}),
        _event("release", base + 0.01, base + 0.02, {"release_confirmed": True, "possession_state": "empty"}),
        _event("retreat", base + 0.02, base + 0.03, {"retreat_completed": True, "clear_of_target": True, "observation_ready": True}),
    ])
    return events


def _episode_succeeded(pickpour_success, placement_done, events):
    required = ("acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat")
    completed = {event.get("phase") for event in events if event.get("status") == "completed" and event.get("outcome_known") is True}
    return bool(pickpour_success and placement_done and set(required).issubset(completed))


def _event(phase, start, end, facts):
    return {"phase": phase, "status": "completed", "outcome_known": True,
            "started_at_s": float(start), "completed_at_s": float(max(end, start + 0.001)), "facts": facts}


def _failed_events(phase, samples, reason):
    end = float(samples[-1]["timestamp_s"])
    phases = []
    order = ("acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat")
    failed_index = order.index(phase)
    for index, item in enumerate(order[:failed_index]):
        phases.append(_event(item, float(index) * 0.01, float(index + 1) * 0.01, {"phase_observed": True}))
    phases.append({"phase": phase, "status": "failed", "outcome_known": True,
                   "started_at_s": 0.0 if not phases else phases[-1]["completed_at_s"],
                   "completed_at_s": max(end, 0.001), "facts": {"failure_observed": True, "failure_reason": reason}})
    return phases


def _isaac_runtime_available() -> bool:
    return importlib.util.find_spec("isaacsim") is not None
