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


class UnsupportedControllerCapabilityError(LabProfileError):
    """The requested PAOS parameter is not exposed by the selected controller."""

    def __init__(self, process_type: str, unsupported: Sequence[str], reason: str | None = None):
        self.process_type = process_type
        self.unsupported = tuple(unsupported)
        self.failure_code = "unsupported_controller" if reason else "unsupported_controller_parameter"
        message = reason or f"{process_type} controller does not support: {', '.join(self.unsupported)}"
        super().__init__(message)


_PROCESS_TYPES = {"pour", "stir", "handle_rotation", "cap_unscrew", "cap_screw"}
_DIRECTIONS = {"cw", "ccw", "forward", "backward"}
_PROCESS_CAPABILITIES = {
    "pour": {
        "controller": "controllers.atomic_actions.pour_controller.PourController",
        "mapped": {"speed": "pour_speed", "direction": "pour_speed_sign"},
        "unsupported": {"axis", "magnitude", "tolerance", "hold_s"},
    },
    "stir": {
        "controller": "controllers.atomic_actions.stir_controller.StirController",
        "mapped": {"magnitude": "stir_radius", "speed": "stir_speed", "direction": "stir_speed_sign"},
        "unsupported": {"axis", "tolerance", "hold_s"},
    },
    "handle_rotation": {
        "controller": "controllers.atomic_actions.open_controller.OpenController",
        "mapped": {"magnitude": "angle", "direction": "angle_sign"},
        "unsupported": {"axis", "speed", "tolerance", "hold_s"},
    },
    "cap_unscrew": {"controller": None, "mapped": {}, "unsupported": set(),
                    "reason": "LabUtopia has no confirmed threaded-cap controller"},
    "cap_screw": {"controller": None, "mapped": {}, "unsupported": set(),
                   "reason": "LabUtopia has no confirmed threaded-cap controller"},
}


def normalize_process_parameters(
    arguments: Mapping[str, Any], profile: LabUtopiaProfile
) -> dict[str, Any]:
    """Normalize PAOS transform parameters into controller-facing values.

    This is deliberately pure and motionless.  The live worker consumes the
    returned mapping only after the normal PAOS frame/path preflight succeeds.
    """
    operation = arguments.get("operation")
    raw = arguments.get("parameters")
    params = dict(raw) if isinstance(raw, Mapping) else {}
    legacy = False
    if params.get("controller_parameters") and params.get("mapped") is not None and params.get("unsupported") == []:
        process_type = params.get("process_type")
        if process_type not in _PROCESS_TYPES:
            raise LabProfileError("parameters.process_type must name a supported LabUtopia process")
        if process_type != profile.configured_process_type:
            raise UnsupportedControllerCapabilityError(
                str(process_type), (),
                reason=f"profile is configured for {profile.configured_process_type}, not {process_type}",
            )
        return dict(params)
    if {"process_type", "mode", "axis", "magnitude", "speed", "direction", "tolerance", "hold_s"}.issubset(params):
        if params.get("process_type") not in _PROCESS_TYPES:
            raise LabProfileError("parameters.process_type must name a supported LabUtopia process")
        process_type = str(params["process_type"])
        transform = {key: params[key] for key in ("mode", "axis", "magnitude", "speed", "direction", "tolerance")}
        hold_s = float(params["hold_s"])
    elif operation == "pour_cycle":
        legacy = True
        process_type = "pour"
        transform = {
            "mode": "rotation",
            "axis": list(profile.source_pour_axis),
            "magnitude": float(params.get("tilt_rad", profile.tilt_rad)),
            "speed": float(params.get("speed", 1.0)),
            "direction": str(params.get("direction", "cw")),
            "tolerance": float(params.get("tolerance", profile.tilt_tolerance_rad)),
        }
        hold_s = float(params.get("hold_s", profile.hold_s))
    elif operation == "stir_cycle":
        legacy = True
        process_type = "stir"
        transform = {
            "mode": "rotation",
            "axis": list(params.get("axis", [0.0, 0.0, 1.0])),
            "magnitude": float(params.get("radius_m", params.get("magnitude", 0.009))),
            "speed": float(params.get("stir_speed", params.get("speed", 3.0))),
            "direction": str(params.get("direction", "ccw")),
            "tolerance": float(params.get("tolerance", profile.alignment_tolerance_m)),
        }
        hold_s = float(params.get("duration_s", params.get("hold_s", profile.hold_s)))
    elif operation == "manipulation_cycle":
        process_type = params.get("process_type")
        if process_type not in _PROCESS_TYPES:
            raise LabProfileError("parameters.process_type must name a supported LabUtopia process")
        transform = dict(params.get("transform") or {})
        hold_s = float(params.get("hold_s", profile.hold_s))
    else:
        raise LabProfileError("unsupported cycle operation")

    if process_type != profile.configured_process_type:
        raise UnsupportedControllerCapabilityError(
            process_type,
            (),
            reason=(
                f"profile is configured for {profile.configured_process_type}, "
                f"not {process_type}"
            ),
        )

    capability = _PROCESS_CAPABILITIES[process_type]
    if capability["controller"] is None:
        raise UnsupportedControllerCapabilityError(process_type, (), reason=capability["reason"])

    if transform.get("mode") not in {"rotation", "translation"}:
        raise LabProfileError("parameters.transform.mode must be rotation or translation")
    if transform["mode"] != "rotation":
        raise UnsupportedControllerCapabilityError(process_type, ["mode"])
    axis = transform.get("axis")
    if not isinstance(axis, (list, tuple)) or len(axis) != 3:
        raise LabProfileError("parameters.transform.axis must contain three numbers")
    axis_values = tuple(float(item) for item in axis)
    norm = sum(item * item for item in axis_values) ** 0.5
    magnitude = float(transform.get("magnitude", 0.0))
    speed = float(transform.get("speed", 0.0))
    tolerance = float(transform.get("tolerance", 0.0))
    direction = str(transform.get("direction", "ccw"))
    if norm <= 0 or magnitude <= 0 or speed <= 0 or tolerance <= 0 or hold_s <= 0:
        raise LabProfileError("axis, magnitude, speed, tolerance, and hold_s must be positive")
    if direction not in _DIRECTIONS:
        raise LabProfileError(f"unsupported transform direction: {direction}")
    requested = set() if legacy else set(transform) | {"hold_s"}
    unsupported = sorted(requested & set(capability["unsupported"]))
    if unsupported:
        raise UnsupportedControllerCapabilityError(process_type, unsupported)
    normalized_axis = [item / norm for item in axis_values]
    signed = -1.0 if direction in {"ccw", "backward"} else 1.0
    controller_parameters = {
        "pour": {"pour_speed": speed * signed},
        "stir": {"stir_radius": magnitude, "stir_speed": speed * signed},
        "handle_rotation": {"angle": magnitude * 180.0 / 3.141592653589793 * signed},
    }[process_type]
    return {
        "process_type": process_type,
        "mode": transform["mode"],
        "axis": normalized_axis,
        "magnitude": magnitude,
        "speed": speed,
        "direction": direction,
        "tolerance": tolerance,
        "hold_s": hold_s,
        "controller_dispatch": capability["controller"],
        "controller_parameters": controller_parameters,
        "mapped": dict(capability["mapped"]),
        "unsupported": [],
    }


def _unsupported_result(error: UnsupportedControllerCapabilityError) -> dict[str, Any]:
    return {
        "status": "unsupported",
        "outcome_known": False,
        "world_change_started": False,
        "motion_authorized": False,
        "failure_code": error.failure_code,
        "process_type": error.process_type,
        "unsupported": list(error.unsupported),
        "error": str(error),
    }


def _unsupported_operation_result(operation: Any) -> dict[str, Any]:
    return {
        "status": "unsupported",
        "outcome_known": False,
        "world_change_started": False,
        "motion_authorized": False,
        "failure_code": "unsupported_cycle_operation",
        "operation": operation,
    }


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
    """PAOS provider engine that delegates parameterized cycles to LabUtopia."""

    def __init__(self, profile: LabUtopiaProfile, *, backend: IsaacLabBackend | None = None):
        self.profile = profile
        self.backend = backend or LabUtopiaBackend(profile)

    def cycle_capability(self, operation: str) -> dict[str, Any]:
        runnable = getattr(self.backend, "runnable_operations", ("pour_cycle",))
        available = operation in self.profile.supported_operations and operation in runnable \
            and callable(getattr(self.backend, "run_cycle", None))
        configured_operation = {
            "pour": "pour_cycle",
            "stir": "stir_cycle",
            "handle_rotation": "manipulation_cycle",
            "cap_unscrew": "manipulation_cycle",
            "cap_screw": "manipulation_cycle",
        }[self.profile.configured_process_type]
        if operation != configured_operation:
            available = False
        if self.profile.configured_process_type in {"cap_unscrew", "cap_screw"}:
            available = False
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
        if operation not in {"pour_cycle", "stir_cycle", "manipulation_cycle"}:
            return _unsupported_operation_result(operation)
        try:
            prepared = self.profile.paos_input(arguments, operation=operation)
            prepared["parameters"] = normalize_process_parameters(prepared, self.profile)
            self.profile.validate_paths()
            if not _isaac_runtime_available():
                raise IsaacLabRuntimeError("isaacsim_unavailable_in_active_python")
        except UnsupportedControllerCapabilityError as exc:
            return _unsupported_result(exc)
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
        if operation not in {"pour_cycle", "stir_cycle", "manipulation_cycle"}:
            return _unsupported_operation_result(operation)
        try:
            request = deepcopy(dict(arguments))
            request["parameters"] = normalize_process_parameters(request, self.profile)
        except UnsupportedControllerCapabilityError as exc:
            return _unsupported_result(exc)
        except LabProfileError as exc:
            return {
                "status": "invalid",
                "outcome_known": False,
                "motion_authorized": False,
                "failure_code": "invalid_process_parameters",
                "error": str(exc),
            }
        if not self.cycle_capability(operation)["execution"]:
            return {"status": "unknown", "outcome_known": False, "failure_code": "isaacsim_unavailable"}
        try:
            result = self.backend.run_cycle(request, cancel)
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
    """Run one LabUtopia episode and return PAOS evidence.

    The worker dispatches generic process types to LabUtopia's existing atomic
    controllers.  Scene-specific controller/task availability is still checked
    by the live episode and is reflected in measured feedback.
    """

    def __init__(self, profile: LabUtopiaProfile):
        self.profile = profile
        self._last_video_info: dict[str, Any] = {}

    @property
    def runnable_operations(self) -> tuple[str, ...]:
        return ("pour_cycle", "stir_cycle", "manipulation_cycle")

    def run_cycle(self, arguments: Mapping[str, Any], cancel: Event) -> Mapping[str, Any]:
        if os.environ.get("OMNI_KIT_ACCEPT_EULA", "").lower() not in {"y", "yes", "1", "true"}:
            raise IsaacLabRuntimeError("OMNI_KIT_ACCEPT_EULA must be accepted before starting Isaac Sim")
        if cancel.is_set():
            return {"status": "unknown", "outcome_known": False, "world_change_started": False}

        if os.environ.get("PAOS_ISAAC_WORKER") != "1":
            return self._run_worker(arguments, cancel)

        return self._run_inprocess(arguments, cancel, Path(os.environ["PAOS_ISAAC_RESULT_PATH"]))

    def dry_run_cycle(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Resolve dispatch and parameters without importing or stepping Isaac Sim."""
        try:
            normalized = normalize_process_parameters(arguments, self.profile)
        except UnsupportedControllerCapabilityError as exc:
            return _unsupported_result(exc)
        except LabProfileError as exc:
            return {
                "status": "invalid",
                "outcome_known": False,
                "world_change_started": False,
                "motion_authorized": False,
                "failure_code": "invalid_process_parameters",
                "error": str(exc),
            }
        return {
            "status": "prepared",
            "outcome_known": False,
            "world_change_started": False,
            "motion_authorized": False,
            "process_type": normalized["process_type"],
            "controller_dispatch": normalized["controller_dispatch"],
            "parameters": normalized,
        }

    def _run_worker(self, arguments: Mapping[str, Any], cancel: Event) -> Mapping[str, Any]:
        operation = str(arguments.get("operation", "manipulation_cycle"))
        output_dir = self.profile.lab_root / "outputs" / (
            "paos-pour-cycle" if operation == "pour_cycle" else "paos-generic-cycle"
        )
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
            phase_events = _generic_phase_events([], process_completed=False, process_type="unknown")
            result = {
                "status": "unknown",
                "outcome_known": False,
                "world_change_started": False,
                "failure_owner": "isaacsim_adapter",
                "failure_code": type(exc).__name__,
                "error_detail": traceback.format_exc()[-2048:],
                "phase_events": phase_events,
                "feedback_observations": [],
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
        normalized = normalize_process_parameters(arguments, self.profile)
        process_type = normalized["process_type"]
        if process_type == "pour":
            return self._run_pour_episode(app, arguments, normalized, cancel, video_path)
        if process_type == "stir":
            return self._run_stir_episode(app, arguments, normalized, cancel, video_path)
        return self._run_rotation_episode(app, arguments, normalized, cancel, video_path)

    def _run_pour_episode(
        self,
        app: Any,
        arguments: Mapping[str, Any],
        process_parameters: Mapping[str, Any],
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
        _configure_pour_controller(controller, process_parameters)
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
                    feedback_position = state.get("feedback_object_position")
                    initial_position = np.asarray(
                        feedback_position if feedback_position is not None else state["object_position"],
                        dtype=float,
                    ).copy()
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
                    process_parameters=process_parameters,
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
                            state, initial_position, initial_quaternion, now + dt, np, Rotation, "placing",
                            process_parameters=process_parameters,
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
                    "phase_events": _phase_events(samples, pickpour_success, placement_done, self.profile),
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
                    "process_parameters": dict(process_parameters),
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

    def _run_stir_episode(
        self,
        app: Any,
        arguments: Mapping[str, Any],
        process_parameters: Mapping[str, Any],
        cancel: Event,
        video_path: Path | None = None,
    ) -> dict[str, Any]:
        """Run LabUtopia's real glass-rod pick/stir controller."""
        self._prepend_lab_root()
        import numpy as np
        import omni.usd
        from factories.controller_factory import create_controller
        from factories.robot_factory import create_robot
        from isaacsim.core.api import World
        from isaacsim.core.utils.stage import add_reference_to_stage
        from omegaconf import OmegaConf, open_dict
        from tasks.stir_task import StirTask
        from utils.object_utils import ObjectUtils

        cfg = OmegaConf.load(str(self.profile.config_path))
        with open_dict(cfg):
            cfg.usd_path = str(self.profile.scene_usd_path)
            cfg.mode = "collect"
            cfg.task_type = "stir"
            cfg.controller_type = "stirglassrod"
            cfg.max_episodes = 1
            cfg.obj_path = self.profile.source_path
            cfg.sub_obj_path = str(
                arguments.get("tool_mesh_path")
                or self.profile.source_control_path
                or f"{self.profile.source_path}/Cylinder"
            )
            cfg.target_path = self.profile.destination_path
            cfg.multi_run.run_dir = str(self.profile.lab_root / "outputs" / "paos-stir-cycle")
            if not hasattr(cfg, "task"):
                cfg.task = {}
            cfg.task.max_steps = max(int(cfg.task.get("max_steps", 2000)), 2000)
            cfg.task.obj_paths = [{"path": self.profile.source_path, "position_range": {"x": [0.25, 0.30], "y": [0.02, 0.08], "z": [0.81, 0.81]}}]

        world = World(stage_units_in_meters=1.0, physics_prim_path="/physicsScene", backend="numpy")
        robot = create_robot(cfg.robot.type, position=np.array(cfg.robot.position), usd_path=str(self.profile.robot_usd_path))
        stage = omni.usd.get_context().get_stage()
        add_reference_to_stage(usd_path=str(self.profile.scene_usd_path), prim_path="/World")
        ObjectUtils.get_instance(stage)
        task = StirTask(cfg=cfg, world=world, stage=stage, robot=robot)
        controller = create_controller(cfg.controller_type, cfg=cfg, robot=robot)
        _configure_stir_controller(controller, process_parameters)
        task.reset()
        world.play()
        samples: list[dict[str, Any]] = []
        initial_position = None
        initial_quaternion = None
        step = 0
        dt = 1.0 / 60.0
        done = False
        success = False
        video_path = video_path or (self.profile.lab_root / "outputs" / "paos-stir-cycle" / "episode.mp4")
        recorder, video_info, np = _make_recorder(video_path)
        try:
            while app.is_running() and step < int(cfg.task.max_steps):
                if cancel.is_set():
                    break
                world.step(render=True)
                state = task.step()
                if state is None:
                    step += 1
                    continue
                state = dict(state)
                state["feedback_object_position"] = state.get("glass_rod_position")
                state["stir_phase"] = getattr(getattr(controller, "stir_controller", None), "phase", None)
                state["stir_angle"] = getattr(getattr(controller, "stir_controller", None), "stir_angle", 0.0)
                state.setdefault(
                    "target_position",
                    state.get("target_beaker")
                    and task.object_utils.get_geometry_center(object_path=state["target_beaker"]),
                )
                state.setdefault("object_quaternion", np.array([0.0, 0.0, 0.0, 1.0]))
                if initial_position is None:
                    feedback_position = state.get("feedback_object_position")
                    initial_position = np.asarray(
                        feedback_position if feedback_position is not None else state["object_position"],
                        dtype=float,
                    ).copy()
                    initial_quaternion = np.asarray(state["object_quaternion"], dtype=float).copy()
                controller_phase = _stir_controller_phase(controller)
                sample = self._sample(state, initial_position, initial_quaternion, step * dt, np, _identity_rotation(), controller_phase, process_parameters=process_parameters)
                samples.append(sample)
                if recorder is not None:
                    recorder.write(state.get("camera_display"), (f"step={step} phase=stirring", f"progress={sample['transform_progress']:.3f}"))
                action, done, success = controller.step(state)
                if action is not None:
                    robot.get_articulation_controller().apply_action(action)
                if done:
                    post_state = dict(state)
                    post_state["feedback_object_position"] = task.object_utils.get_object_xform_position(
                        object_path=cfg.sub_obj_path
                    )
                    post_state["object_position"] = post_state["feedback_object_position"]
                    post_state["release_confirmed"] = (
                        getattr(controller, "gripper_control", None) is not None
                        and getattr(controller.gripper_control, "grasped_object_path", None) is None
                    )
                    post_state["return_position"] = getattr(controller, "initial_control_position", None)
                    return_position = post_state["return_position"]
                    current_position = post_state["feedback_object_position"]
                    post_state["object_support_state"] = (
                        "on_support"
                        if return_position is not None
                        and current_position is not None
                        and float(np.linalg.norm(np.asarray(current_position) - np.asarray(return_position))) <= 0.06
                        else "unknown"
                    )
                    # Controller completion is not sufficient evidence that the
                    # tool is safely stowed.  Promote return phases only when
                    # the controlled prim is measured back on its support.
                    support_observed = post_state["object_support_state"] == "on_support"
                    post_state["stow_completed"] = support_observed
                    post_state["retreat_completed"] = support_observed and post_state["release_confirmed"]
                    samples.append(self._sample(
                        post_state,
                        initial_position,
                        initial_quaternion,
                        (step + 1) * dt,
                        np,
                        _identity_rotation(),
                        "retreat",
                        process_parameters=process_parameters,
                    ))
                    break
                step += 1
        finally:
            world.stop()
            if recorder is not None:
                recorder.close()
                video_info = recorder.metadata()
            self._last_video_info = dict(video_info)
        events = _stir_phase_events(
            samples,
            process_completed=bool(done and success),
            process_type="stir",
            profile=self.profile,
        )
        return _generic_result(arguments, samples, events, process_parameters, self.profile, video_info, step)

    def _run_rotation_episode(
        self,
        app: Any,
        arguments: Mapping[str, Any],
        process_parameters: Mapping[str, Any],
        cancel: Event,
        video_path: Path | None = None,
    ) -> dict[str, Any]:
        """Run LabUtopia open/close as the shared handle/cap rotation adapter."""
        self._prepend_lab_root()
        import numpy as np
        import omni.usd
        from factories.controller_factory import create_controller
        from factories.robot_factory import create_robot
        from isaacsim.core.api import World
        from isaacsim.core.utils.stage import add_reference_to_stage
        from omegaconf import OmegaConf, open_dict
        from tasks.open_close_task import OpenCloseTask
        from utils.object_utils import ObjectUtils

        cfg = OmegaConf.load(str(self.profile.config_path))
        controller_name = "open" if process_parameters["process_type"] in {"handle_rotation", "cap_unscrew"} else "close"
        with open_dict(cfg):
            cfg.usd_path = str(self.profile.scene_usd_path)
            cfg.mode = "collect"
            cfg.task_type = "openclose"
            cfg.controller_type = controller_name
            cfg.max_episodes = 1
            cfg.multi_run.run_dir = str(self.profile.lab_root / "outputs" / "paos-rotation-cycle")
            cfg.task.max_steps = max(int(cfg.task.get("max_steps", 1200)), 1200)
            cfg.task.obj_paths = [{"path": self.profile.source_path, "position_range": {"x": [0.25, 0.30], "y": [0.02, 0.08], "z": [0.81, 0.81]}}]
            cfg.task.operate_type = str(cfg.task.get("operate_type", "door"))
            if arguments.get("handle_path"):
                cfg.handle_path = arguments["handle_path"]

        world = World(stage_units_in_meters=1.0, physics_prim_path="/physicsScene", backend="numpy")
        robot = create_robot(cfg.robot.type, position=np.array(cfg.robot.position), usd_path=str(self.profile.robot_usd_path))
        stage = omni.usd.get_context().get_stage()
        add_reference_to_stage(usd_path=str(self.profile.scene_usd_path), prim_path="/World")
        ObjectUtils.get_instance(stage)
        task = OpenCloseTask(cfg=cfg, world=world, stage=stage, robot=robot)
        controller = create_controller(controller_name, cfg=cfg, robot=robot)
        _configure_rotation_controller(controller, process_parameters)
        task.reset()
        world.play()
        samples: list[dict[str, Any]] = []
        initial_position = None
        initial_quaternion = None
        step = 0
        dt = 1.0 / 60.0
        done = False
        success = False
        video_path = video_path or (self.profile.lab_root / "outputs" / "paos-rotation-cycle" / "episode.mp4")
        recorder, video_info, np = _make_recorder(video_path)
        try:
            while app.is_running() and step < int(cfg.task.max_steps):
                if cancel.is_set():
                    break
                world.step(render=True)
                state = task.step()
                if state is None:
                    step += 1
                    continue
                state = dict(state)
                state.setdefault("target_position", state.get("object_position"))
                state.setdefault("object_quaternion", np.array([0.0, 0.0, 0.0, 1.0]))
                if initial_position is None:
                    initial_position = np.asarray(state["object_position"], dtype=float).copy()
                    initial_quaternion = np.asarray(state["object_quaternion"], dtype=float).copy()
                sample = self._sample(state, initial_position, initial_quaternion, step * dt, np, _identity_rotation(), "rotating", process_parameters=process_parameters)
                samples.append(sample)
                if recorder is not None:
                    recorder.write(state.get("camera_display"), (f"step={step} phase=rotating", f"progress={sample['transform_progress']:.3f}"))
                action, done, success = controller.step(state)
                if action is not None:
                    robot.get_articulation_controller().apply_action(action)
                if done:
                    break
                step += 1
        finally:
            world.stop()
            if recorder is not None:
                recorder.close()
                video_info = recorder.metadata()
            self._last_video_info = dict(video_info)
        events = _generic_phase_events(samples, process_completed=bool(done and success), process_type=process_parameters["process_type"])
        return _generic_result(arguments, samples, events, process_parameters, self.profile, video_info, step)

    def _prepend_lab_root(self) -> None:
        root = str(self.profile.lab_root)
        if root not in sys.path:
            sys.path.insert(0, root)

    def _sample(
        self,
        state,
        initial_position,
        initial_quaternion,
        timestamp,
        np,
        rotation_cls,
        controller_phase,
        process_parameters: Mapping[str, Any] | None = None,
    ):
        feedback_position = state.get("feedback_object_position")
        position = np.asarray(
            feedback_position if feedback_position is not None else state["object_position"],
            dtype=float,
        )
        target = np.asarray(state.get("target_position", position), dtype=float)
        process_parameters = dict(process_parameters or {})
        quat = np.asarray(state.get("object_quaternion", [0.0, 0.0, 0.0, 1.0]), dtype=float)
        source_size = np.asarray(state.get("object_size", [0.0, 0.0, 0.0]), dtype=float)
        relative = rotation_cls.from_quat(initial_quaternion).inv() * rotation_cls.from_quat(quat)
        tilt = float(relative.magnitude())
        pour_axis = np.asarray(self.profile.source_pour_axis, dtype=float)
        pour_point = position + rotation_cls.from_quat(quat).apply(pour_axis * (source_size[2] / 2.0))
        if process_parameters.get("process_type") == "stir":
            alignment = float(np.linalg.norm(position[:2] - target[:2]))
        else:
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
        transform_progress = _observed_transform_progress(state, position, initial_position, process_parameters, tilt)
        transform_error = max(0.0, float(process_parameters.get("magnitude", 0.0)) - transform_progress)
        engagement_valid = bool(grasp or controller_phase in {"pouring", "stirring", "rotating", "placing"})
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
            "engagement_valid": engagement_valid,
            "transform_progress": transform_progress,
            "transform_error": transform_error,
            "target_container_aligned": alignment <= self.profile.alignment_tolerance_m,
            "alignment_error_m": alignment,
            "source_pour_point": {"x_m": float(pour_point[0]), "y_m": float(pour_point[1]), "z_m": float(pour_point[2]), "frame_id": self.profile.frame_id},
            "feedback_object_path": self.profile.source_control_path or self.profile.source_path,
            "target_position": {"x_m": float(target[0]), "y_m": float(target[1]), "z_m": float(target[2]), "frame_id": self.profile.frame_id},
            "stir_angle_rad": float(state.get("stir_angle", 0.0) or 0.0),
            "tilt_rad": tilt,
            "object_support_state": state.get("object_support_state", "unknown"),
            "acquire_completed": bool(state.get("acquire_completed", False)),
            "transport_completed": bool(state.get("transport_completed", False)),
            "reorient_exit_completed": bool(state.get("reorient_exit_completed", False)),
            "stow_completed": bool(state.get("stow_completed", False)),
            "release_confirmed": bool(state.get("release_confirmed", False)),
            "retreat_completed": bool(state.get("retreat_completed", False)),
        }


def _configure_pour_controller(controller: Any, parameters: Mapping[str, Any]) -> None:
    """Apply PAOS speed/direction to the existing pick/pour controller."""
    active = getattr(controller, "pour_controller", None)
    if active is None:
        return
    signed_speed = float(parameters["controller_parameters"]["pour_speed"])
    original = active.forward

    def configured_forward(*args, **kwargs):
        kwargs["pour_speed"] = signed_speed
        return original(*args, **kwargs)

    active.forward = configured_forward


def _configure_stir_controller(controller: Any, parameters: Mapping[str, Any]) -> None:
    active = getattr(controller, "stir_controller", None)
    if active is None:
        return
    values = parameters["controller_parameters"]
    configure = getattr(active, "configure", None)
    if callable(configure):
        configure(
            stir_radius=values["stir_radius"],
            stir_speed=values["stir_speed"],
            duration_s=values.get("stir_duration_s", parameters.get("hold_s")),
        )
    else:
        active._stir_radius = float(values["stir_radius"])
        active._stir_speed = float(values["stir_speed"])


def _configure_rotation_controller(controller: Any, parameters: Mapping[str, Any]) -> None:
    active = getattr(controller, "open_controller", None) or getattr(controller, "close_controller", None)
    if active is None:
        return
    original = active.forward
    angle = float(parameters["controller_parameters"]["angle"])

    def configured_forward(*args, **kwargs):
        kwargs["angle"] = angle
        return original(*args, **kwargs)

    active.forward = configured_forward


def _observed_transform_progress(state, position, initial_position, parameters, tilt_rad=0.0):
    process_type = parameters.get("process_type")
    if process_type == "pour":
        return abs(float(tilt_rad))
    revolute = state.get("revolute_joint_position")
    if revolute is not None:
        try:
            values = [abs(float(value)) for value in revolute]
            return max(values, default=0.0)
        except (TypeError, ValueError):
            pass
    if process_type == "stir":
        radius = float(parameters.get("magnitude", 0.0))
        target = state.get("target_position", position)
        radial = sum((float(position[index]) - float(target[index])) ** 2 for index in (0, 1)) ** 0.5
        displacement = sum((float(position[index]) - float(initial_position[index])) ** 2 for index in range(3)) ** 0.5
        return min(radius, max(radial, displacement))
    return 0.0


def _identity_rotation():
    from scipy.spatial.transform import Rotation

    return Rotation


def _make_recorder(video_path: Path):
    import numpy as np

    try:
        import cv2
    except Exception as exc:
        return None, {"video_path": str(video_path), "video_frame_count": 0, "video_available": False, "video_error": type(exc).__name__}, np
    recorder = _EpisodeVideoRecorder(video_path, cv2, np, fps=60.0)
    return recorder, recorder.metadata(), np


def _generic_phase_events(samples, *, process_completed: bool, process_type: str):
    phases = ("acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat")
    events = [_unknown_phase_event(phase) for phase in phases]
    if not samples:
        return events

    last = float(samples[-1]["timestamp_s"])
    for phase in ("acquire", "transport", "reorient_exit", "stow", "release", "retreat"):
        key = f"{phase}_completed"
        observed = next((sample for sample in samples if sample.get(key) is True), None)
        if observed is None:
            continue
        index = phases.index(phase)
        start = float(observed.get("phase_started_at_s", observed["timestamp_s"]))
        events[index] = _event(phase, start, float(observed["timestamp_s"]), {key: True})

    process_samples = [
        sample for sample in samples
        if sample.get("process_started") is True
        or float(sample.get("transform_progress", 0.0) or 0.0) > 0.0
        or sample.get("controller_phase") in {"pouring", "stirring", "rotating"}
    ]
    if process_completed:
        process = process_samples[-1] if process_samples else samples[-1]
        started = process_samples[0] if process_samples else samples[0]
        events[2] = _event(
            "process",
            float(started["timestamp_s"]),
            float(process["timestamp_s"]),
            {
                "process_type": process_type,
                "transform_progress": float(process.get("transform_progress", 0.0) or 0.0),
            },
        )
    elif process_samples:
        events[2] = {
            "phase": "process",
            "status": "failed",
            "outcome_known": True,
            "started_at_s": float(process_samples[0]["timestamp_s"]),
            "completed_at_s": last,
            "facts": {"failure_reason": f"{process_type}_controller_not_completed"},
        }
    return events


def _stir_controller_phase(controller: Any) -> str:
    """Expose the LabUtopia controller state as PAOS lifecycle vocabulary."""
    pick = getattr(controller, "pick_controller", None)
    stir = getattr(controller, "stir_controller", None)
    place = getattr(controller, "place_controller", None)
    if pick is not None and not pick.is_done():
        return "acquiring"
    if stir is not None and not stir.is_done():
        phase = getattr(stir, "phase", None)
        return "stirring" if phase == 3 else "transporting" if phase in {0, 1, 2} else "reorient_exit"
    if place is not None and not place.is_done():
        return "stowing"
    return "retreat"


def _stir_phase_events(samples, *, process_completed: bool, process_type: str, profile: LabUtopiaProfile):
    """Build stir lifecycle events only from measured object/tool observations."""
    phases = ("acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat")
    events = [_unknown_phase_event(phase) for phase in phases]
    if not samples:
        return events

    grasp = next((sample for sample in samples if sample.get("grasp_valid") is True), None)
    aligned = next((sample for sample in samples if sample.get("grasp_valid") is True and sample.get("target_container_aligned") is True), None)
    process_samples = [
        sample for sample in samples
        if sample.get("controller_phase") == "stirring"
        and sample.get("target_container_aligned") is True
        and float(sample.get("transform_progress", 0.0) or 0.0) > 0.0
    ]
    process_started = process_samples[0] if process_samples else None
    process_end = process_samples[-1] if process_samples else None
    process_duration = (
        float(process_end["timestamp_s"]) - float(process_started["timestamp_s"])
        if process_started and process_end else 0.0
    )
    max_stir_angle = max(
        (abs(float(item.get("stir_angle_rad", 0.0) or 0.0)) for item in process_samples),
        default=0.0,
    )
    required_stir_angle = 2.0 * 3.141592653589793 * profile.stir_turns * 0.9
    process_valid = bool(
        process_completed
        and process_started
        and process_duration >= profile.stir_duration_s * 0.9
        and max(float(item.get("transform_progress", 0.0) or 0.0) for item in process_samples) >= profile.stir_radius_m * 0.5
        and max_stir_angle >= required_stir_angle
    )
    if grasp:
        events[0] = _event("acquire", 0.0, grasp["timestamp_s"], {"grasp_confirmed": True, "possession_state": "holding"})
    if aligned:
        events[1] = _event("transport", grasp["timestamp_s"] if grasp else 0.0, aligned["timestamp_s"], {"route_completed": True, "possession_state": "holding"})
    if process_valid:
        events[2] = _event("process", process_started["timestamp_s"], process_end["timestamp_s"], {"process_type": process_type, "transform_progress": max(float(item.get("transform_progress", 0.0) or 0.0) for item in process_samples), "duration_s": process_duration, "stir_angle_rad": max_stir_angle, "required_stir_angle_rad": required_stir_angle})
    elif process_started:
        events[2] = {"phase": "process", "status": "failed", "outcome_known": True, "started_at_s": float(process_started["timestamp_s"]), "completed_at_s": float(samples[-1]["timestamp_s"]), "facts": {"failure_reason": "stir_observation_not_qualified"}}

    exited = next((sample for sample in samples if sample.get("controller_phase") == "reorient_exit" and sample.get("grasp_valid") is True), None)
    if exited is None:
        exited = next((sample for sample in samples if sample.get("controller_phase") == "stowing" and sample.get("grasp_valid") is True), None)
    if exited and process_valid:
        events[3] = _event("reorient_exit", process_end["timestamp_s"], exited["timestamp_s"], {"tool_reoriented_or_exited": True, "possession_state": "holding"})
    stowed = next(
        (
            sample for sample in samples
            if sample.get("stow_completed") is True
            and sample.get("object_support_state") == "on_support"
        ),
        None,
    )
    if stowed and events[3]["status"] == "completed":
        events[4] = _event("stow", stowed["timestamp_s"] - 0.01, stowed["timestamp_s"], {"object_support_state": stowed.get("object_support_state", "on_support")})
    released = next((sample for sample in reversed(samples) if sample.get("release_confirmed") is True and sample.get("possession_state") == "empty"), None)
    if released and events[4]["status"] == "completed":
        events[5] = _event("release", released["timestamp_s"] - 0.01, released["timestamp_s"], {"release_confirmed": True, "possession_state": "empty"})
        retreated = next(
            (
                sample for sample in reversed(samples)
                if sample.get("retreat_completed") is True
                and sample.get("object_support_state") == "on_support"
            ),
            None,
        )
        if retreated:
            events[6] = _event("retreat", released["timestamp_s"], retreated["timestamp_s"], {"retreat_completed": True, "clear_of_target": True, "observation_ready": True})
    return events


def _unknown_phase_event(phase: str, timestamp: float = 0.0) -> dict[str, Any]:
    return {
        "phase": phase,
        "status": "unknown",
        "outcome_known": False,
        "started_at_s": float(timestamp),
        "completed_at_s": None,
        "facts": {},
    }


def _generic_result(arguments, samples, events, parameters, profile, video_info, step):
    process_event = next((event for event in events if event.get("phase") == "process"), {})
    required = ("acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat")
    completed = {
        event.get("phase")
        for event in events
        if event.get("status") == "completed" and event.get("outcome_known") is True
    }
    missing = [phase for phase in required if phase not in completed]
    succeeded = process_event.get("status") == "completed" and not missing
    if succeeded:
        status = "succeeded"
        failure_code = None
    elif process_event.get("status") == "failed":
        status = "failed"
        failure_code = process_event.get("facts", {}).get("failure_reason")
    elif process_event.get("status") == "completed" and process_event.get("outcome_known") is True:
        status = "failed"
        failure_code = "incomplete_cycle_phases"
    else:
        status = "unknown"
        failure_code = None
    last = samples[-1] if samples else {}
    return {
        "status": status,
        "outcome_known": status in {"succeeded", "failed"},
        "world_change_started": bool(samples),
        "entity_ref": arguments["entity_ref"],
        "destination_ref": arguments["destination_ref"],
        "return_destination_ref": arguments["return_destination_ref"],
        "phase_events": events,
        "feedback_observations": samples,
        "feedback_samples": samples,
        "feedback_source_profile": profile.source_profile(),
        "evaluation_profile": profile.evaluation_profile(),
        "process_parameters": dict(parameters),
        "possession_state": last.get("possession_state", "unknown"),
        "object_support_state": last.get("object_support_state", "unknown"),
        "new_scene_revision": f"{arguments['scene_revision']}-generic-{step}" if succeeded else None,
        "artifact_refs": [f"artifact://labutopia/paos-generic/{arguments['scene_revision']}-{step}"],
        "evidence_refs": [f"artifact://labutopia/paos-generic/{arguments['scene_revision']}-{step}"],
        "final_object_observation": samples[-1] if samples else {},
        "failure_code": failure_code,
        "incomplete_phases": missing,
        **video_info,
    }


def _phase_events(samples, pickpour_success: bool, placement_done: bool, profile: LabUtopiaProfile):
    if not samples:
        return _generic_phase_events([], process_completed=False, process_type="pour")
    last = float(samples[-1]["timestamp_s"])
    grasp = next((sample for sample in samples if sample["grasp_valid"]), None)
    aligned = next((sample for sample in samples if sample["target_container_aligned"] and sample["grasp_valid"]), None)
    window = _continuous_pour_window(samples, profile)
    returned = next((sample for sample in reversed(samples) if sample["grasp_valid"] and sample["tilt_rad"] <= profile.tilt_tolerance_rad), None)
    if not grasp:
        return _failed_events("acquire", samples, "grasp_not_confirmed")
    if not aligned:
        return _failed_events("transport", samples, "container_not_aligned")
    if not pickpour_success:
        return _append_placement_events(
            _failed_events("process", samples, "pour_controller_not_completed"),
            samples,
            placement_done,
            last,
        )
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
        if any(event.get("phase") == "stow" for event in events):
            return events
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
    failed_index += 1
    phases.extend(
        {
            "phase": pending,
            "status": "unknown",
            "outcome_known": False,
            "started_at_s": max(end, 0.001),
            "completed_at_s": None,
            "facts": {},
        }
        for pending in order[failed_index:]
    )
    return phases


def _isaac_runtime_available() -> bool:
    return importlib.util.find_spec("isaacsim") is not None
