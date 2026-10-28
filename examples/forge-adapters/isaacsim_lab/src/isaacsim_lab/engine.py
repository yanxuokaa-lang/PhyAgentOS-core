"""LabUtopia-backed PAOS cycle engine.

Isaac Sim is imported only inside the execution method.  The PAOS process can
therefore inspect and prepare a lab route in a normal Python environment while
the actual motion remains owned by the LabUtopia simulator process.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import traceback
from copy import deepcopy
from pathlib import Path
from threading import Event, RLock
from typing import Any, Mapping, Protocol, Sequence

from .observation import (
    FilesystemObservationArtifactWriter,
    IsaacCameraMetadataProvider,
    IsaacCameraObservationSource,
)
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
    maximum_tilt = float(params.get("maximum_tilt_rad", profile.maximum_tilt_rad))
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
            "magnitude": float(params.get("radius_m", params.get("magnitude", profile.stir_radius_m))),
            "speed": float(params.get("stir_speed", params.get("speed", 3.0))),
            "direction": str(params.get("direction", "ccw")),
            "tolerance": float(params.get("tolerance", profile.alignment_tolerance_m)),
        }
        hold_s = float(params.get("duration_s", params.get("hold_s", profile.hold_s)))
        maximum_tilt = profile.maximum_tilt_rad
    elif operation == "manipulation_cycle":
        process_type = params.get("process_type")
        if process_type not in _PROCESS_TYPES:
            raise LabProfileError("parameters.process_type must name a supported LabUtopia process")
        transform = dict(params.get("transform") or {})
        hold_s = float(params.get("hold_s", profile.hold_s))
        maximum_tilt = profile.maximum_tilt_rad
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
        "maximum_tilt_rad": maximum_tilt,
        "radius_m": float(params.get("radius_m", magnitude)) if process_type == "stir" else None,
        "depth_m": float(params.get("depth_m", profile.stir_depth_m)) if process_type == "stir" else None,
        "turns": float(params.get("turns", profile.stir_turns)) if process_type == "stir" else None,
        "duration_s": float(params.get("duration_s", hold_s)) if process_type == "stir" else None,
        "controller_dispatch": capability["controller"],
        "controller_parameters": controller_parameters,
        "mapped": dict(capability["mapped"]),
        "unsupported": [],
    }


def _validate_cycle_target(arguments: Mapping[str, Any], process_type: str) -> dict[str, Any]:
    """Validate the perception target at the adapter boundary, without motion."""
    try:
        from pick_place_workflow.manipulation_target import validate_manipulation_target
    except ModuleNotFoundError as exc:
        raise LabProfileError("PAOS manipulation target contract is unavailable") from exc
    try:
        return validate_manipulation_target(
            arguments.get("manipulation_target"), arguments, process_type=process_type
        )
    except ValueError as exc:
        raise LabProfileError(str(exc)) from exc


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

    def __init__(
        self,
        profile: LabUtopiaProfile,
        *,
        backend: IsaacLabBackend | None = None,
        observation_artifact_root: str | Path | None = None,
    ):
        self.profile = profile
        self.backend = backend or LabUtopiaBackend(
            profile, observation_artifact_root=observation_artifact_root
        )

    @property
    def observation_ready(self) -> bool:
        return bool(getattr(self.backend, "observation_ready", False))

    def observe(self, request: Mapping[str, Any]) -> dict[str, Any]:
        observe = getattr(self.backend, "observe", None)
        if not callable(observe):
            return {"status": "unavailable", "failure_code": "observation_not_supported"}
        result = observe(request)
        return dict(result) if isinstance(result, Mapping) else {
            "status": "unavailable", "failure_code": "invalid_observation_result"
        }

    def bind_observed_entities(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return dict(self.backend.bind_observed_entities(request))

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
        eula_accepted = os.environ.get("OMNI_KIT_ACCEPT_EULA", "").lower() in {"y", "yes", "1", "true"}
        execution_available = available and eula_accepted
        return {
            "operation": operation,
            "preparation": available,
            "execution": execution_available,
            "feedback": available,
            "return": available,
            "dry_run": False,
            "provider": "labutopia_isaacsim",
            "motion_authorized": bool(execution_available),
            "unavailable_reason": None if execution_available else (
                "OMNI_KIT_ACCEPT_EULA_not_accepted" if available else "isaacsim_runtime_or_scene_unavailable"
            ),
        }

    def prepare_cycle(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        operation = arguments.get("operation") if isinstance(arguments, Mapping) else None
        if operation not in {"pour_cycle", "stir_cycle", "manipulation_cycle"}:
            return _unsupported_operation_result(operation)
        current_revision = self._current_scene_revision()
        if current_revision is None:
            return {"status": "unavailable", "motion_authorized": False,
                    "failure_code": "live_scene_revision_unavailable"}
        if arguments.get("scene_revision") != current_revision:
            return {"status": "invalid", "motion_authorized": False,
                    "failure_code": "stale_scene_revision"}
        try:
            prepared = self.profile.paos_input(
                arguments,
                operation=operation,
                perception_binding=arguments.get("binding"),
            )
            prepared["parameters"] = normalize_process_parameters(prepared, self.profile)
            if prepared["parameters"]["process_type"] in {"pour", "stir"}:
                _validate_cycle_target(prepared, prepared["parameters"]["process_type"])
            self.profile.validate_paths()
            if not _isaac_runtime_available():
                raise IsaacLabRuntimeError("isaacsim_unavailable_in_active_python")
        except UnsupportedControllerCapabilityError as exc:
            return _unsupported_result(exc)
        except LabProfileError as exc:
            return {"status": "invalid", "motion_authorized": False, "failure_code": "invalid_preparation", "error": str(exc)}
        except IsaacLabRuntimeError as exc:
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
        current_revision = self._current_scene_revision()
        if current_revision is None:
            return {"status": "unavailable", "outcome_known": False, "world_change_started": False,
                    "motion_authorized": False, "failure_code": "live_scene_revision_unavailable"}
        if arguments.get("scene_revision") != current_revision:
            return {"status": "invalid", "outcome_known": False, "world_change_started": False,
                    "motion_authorized": False, "failure_code": "stale_scene_revision"}
        try:
            request = deepcopy(dict(arguments))
            request["parameters"] = normalize_process_parameters(request, self.profile)
            if request["parameters"]["process_type"] in {"pour", "stir"}:
                _validate_cycle_target(request, request["parameters"]["process_type"])
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
        except IsaacLabRuntimeError as exc:
            return {"status": "unavailable", "outcome_known": False, "world_change_started": False,
                    "motion_authorized": False, "failure_code": "live_scene_revision_unavailable",
                    "error": str(exc)}
        if not self.cycle_capability(operation)["execution"]:
            return {"status": "unknown", "outcome_known": False, "world_change_started": False,
                    "motion_authorized": False,
                    "failure_code": self.cycle_capability(operation).get("unavailable_reason", "isaacsim_unavailable")}
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

    def prepare_manipulation(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Qualify one measured route without motion through the backend port."""
        prepare = getattr(self.backend, "prepare_manipulation", None)
        if not callable(prepare):
            return {
                "status": "unavailable", "motion_authorized": False,
                "failure_code": "phase_preparation_not_supported",
            }
        result = prepare(deepcopy(dict(arguments)))
        return dict(result) if isinstance(result, Mapping) else {
            "status": "unavailable", "motion_authorized": False,
            "failure_code": "invalid_phase_preparation_result",
        }

    def prepare_held(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Request a current held route through the same backend boundary."""
        prepare = getattr(self.backend, "prepare_held", None)
        if not callable(prepare):
            return {"status": "unavailable", "motion_authorized": False,
                    "failure_code": "held_preparation_not_supported"}
        result = prepare(deepcopy(dict(arguments)))
        return dict(result) if isinstance(result, Mapping) else {
            "status": "unavailable", "motion_authorized": False,
            "failure_code": "invalid_held_preparation_result",
        }

    def close(self) -> None:
        close = getattr(self.backend, "close", None)
        if callable(close):
            close()

    def execute_phase(
        self, phase: str, arguments: Mapping[str, Any], cancel: Event, **context: Any
    ) -> dict[str, Any]:
        """Run one bounded manipulation phase through a phase-capable backend."""
        del context
        if phase not in {"acquire", "pour", "stir", "place"}:
            return {"status": "unsupported", "outcome_known": False,
                    "world_change_started": False, "failure_code": "unsupported_manipulation_phase"}
        execute = getattr(self.backend, "execute_phase", None)
        if not callable(execute):
            return {"status": "unavailable", "outcome_known": False,
                    "world_change_started": False, "failure_code": "phase_execution_not_supported"}
        if cancel.is_set():
            return {"status": "cancelled", "outcome_known": True,
                    "world_change_started": False, "motion_authorized": False}
        result = execute(phase, deepcopy(dict(arguments)), cancel)
        return dict(result) if isinstance(result, Mapping) else {
            "status": "unknown", "outcome_known": False, "world_change_started": True,
            "failure_code": "invalid_phase_execution_result",
        }

    def _current_scene_revision(self) -> str | None:
        resolver = getattr(self.backend, "current_scene_revision", None)
        if not callable(resolver):
            return None
        value = resolver()
        return value if isinstance(value, str) and value.strip() else None


class LabUtopiaBackend:
    """Run one LabUtopia episode and return PAOS evidence.

    The worker dispatches generic process types to LabUtopia's existing atomic
    controllers.  Scene-specific controller/task availability is still checked
    by the live episode and is reflected in measured feedback.
    """

    def __init__(
        self,
        profile: LabUtopiaProfile,
        *,
        observation_artifact_root: str | Path | None = None,
    ):
        self.profile = profile
        self.observation_artifact_root = (
            Path(observation_artifact_root).expanduser().resolve()
            if observation_artifact_root is not None
            else None
        )
        self._last_video_info: dict[str, Any] = {}
        self._worker_session = None
        self._worker_lock = RLock()

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

    def prepare_manipulation(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if os.environ.get("OMNI_KIT_ACCEPT_EULA", "").lower() not in {"y", "yes", "1", "true"}:
            return {"status": "unavailable", "motion_authorized": False,
                    "failure_code": "OMNI_KIT_ACCEPT_EULA_not_accepted"}
        try:
            with self._worker_lock:
                if self._worker_session is None:
                    from .worker_session import IsaacWorkerSession
                    self._worker_session = IsaacWorkerSession(
                        self.profile_path,
                        python_executable=self.profile.worker_python_path,
                        observation_artifact_root=self.observation_artifact_root,
                    )
                session = self._worker_session
            return session.request("prepare_manipulation", arguments)
        except Exception as exc:
            return {"status": "unavailable", "motion_authorized": False,
                    "failure_code": type(exc).__name__, "error_detail": str(exc)[:512]}

    def execute_phase(
        self, phase: str, arguments: Mapping[str, Any], cancel: Event
    ) -> Mapping[str, Any]:
        if phase not in {"acquire", "pour", "stir", "place"}:
            return {"status": "unsupported", "outcome_known": False,
                    "world_change_started": False, "failure_code": "unsupported_manipulation_phase"}
        if os.environ.get("OMNI_KIT_ACCEPT_EULA", "").lower() not in {"y", "yes", "1", "true"}:
            return {"status": "unavailable", "outcome_known": False,
                    "world_change_started": False, "motion_authorized": False,
                    "failure_code": "OMNI_KIT_ACCEPT_EULA_not_accepted"}
        request = deepcopy(dict(arguments))
        request["operation"] = phase
        try:
            with self._worker_lock:
                if self._worker_session is None:
                    from .worker_session import IsaacWorkerSession
                    self._worker_session = IsaacWorkerSession(
                        self.profile_path,
                        python_executable=self.profile.worker_python_path,
                        observation_artifact_root=self.observation_artifact_root,
                    )
                session = self._worker_session
            return session.request("execute_phase", request, cancel=cancel)
        except Exception as exc:
            return {"status": "unknown", "outcome_known": False,
                    "world_change_started": True, "failure_code": type(exc).__name__,
                    "error_detail": str(exc)[:512]}

    def prepare_held(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        # The session readiness RPC receives the explicit held operation,
        # latest invocation and prior route; it must qualify a fresh route.
        return self.prepare_manipulation(arguments)

    def bind_observed_entities(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        with self._worker_lock:
            session = self._worker_session
        if session is None:
            return {"status": "unavailable", "failure_code": "observation_required", "motion_authorized": False}
        return session.request("bind_observed_entities", request)

    def bind_observed_entities_in_session(self, session: Any, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .execution_identity import bind_observed_entities
        from .phase_motion import PhaseMotionError

        try:
            return bind_observed_entities(self._phase_motion(session), request)
        except (PhaseMotionError, ValueError) as exc:
            return {"status": "unavailable", "motion_authorized": False,
                    "failure_code": getattr(exc, "code", "visual_measurement_failed"),
                    "error_detail": str(exc)}

    def prepare_manipulation_in_session(
        self, session: Any, arguments: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Qualify the current scene through the session's measured motion model."""
        from .phase_motion import PhaseMotionError, preparation_result

        try:
            model = self._phase_motion(session)
            route, evidence = model.prepare(arguments)
            return preparation_result(arguments, route, evidence)
        except (PhaseMotionError, KeyError, TypeError, ValueError) as exc:
            return {"status": "unavailable", "motion_authorized": False,
                    "failure_code": getattr(exc, "code", "invalid_phase_preparation"),
                    "error": str(exc)}

    def _phase_motion(self, session):
        from .phase_motion import IsaacPhaseMotion, PhaseMotionError

        if getattr(self.profile, "motion_config_path", None) is None:
            raise PhaseMotionError("motion_configuration_unavailable", "profile requires a measured phase motion configuration")
        model = session.resolve("phase_motion")
        if model is None:
            self._ensure_session_scene(session)
            model = IsaacPhaseMotion(session, self.profile, self.observation_artifact_root)
            session.register("phase_motion", model)
        return model

    def execute_phase_in_session(
        self, session: Any, arguments: Mapping[str, Any], cancel: Event
    ) -> Mapping[str, Any]:
        """Execute the admitted phase without using the legacy cycle runner."""
        from .phase_motion import PhaseMotionError, PhaseMotionPreconditionError

        try:
            model = self._phase_motion(session)
        except PhaseMotionError as exc:
            return {"status": "unavailable", "outcome_known": True,
                    "world_change_started": False, "motion_authorized": False,
                    "failure_code": exc.code, "operation": arguments.get("operation")}
        try:
            return model.execute(arguments, cancel)
        except PhaseMotionPreconditionError as exc:
            return {"status": "failed", "outcome_known": True,
                    "world_change_started": False, "operation_completed": False,
                    "failure_owner": "isaacsim_adapter", "failure_code": exc.code,
                    "error_detail": str(exc)[:512]}
        except Exception as exc:
            return {"status": "unknown", "outcome_known": False,
                    "world_change_started": True, "failure_owner": "isaacsim_adapter",
                    "failure_code": getattr(exc, "code", type(exc).__name__),
                    "error_detail": str(exc)[:512]}

    def close(self) -> None:
        with self._worker_lock:
            session = self._worker_session
            self._worker_session = None
        if session is not None:
            session.close()

    @property
    def observation_ready(self) -> bool:
        return False

    def observe(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if os.environ.get("OMNI_KIT_ACCEPT_EULA", "").lower() not in {"y", "yes", "1", "true"}:
            return {"status": "unavailable", "failure_code": "OMNI_KIT_ACCEPT_EULA_not_accepted"}
        try:
            with self._worker_lock:
                if self._worker_session is None:
                    from .worker_session import IsaacWorkerSession

                    self._worker_session = IsaacWorkerSession(
                        self.profile_path,
                        python_executable=self.profile.worker_python_path,
                        observation_artifact_root=self.observation_artifact_root,
                    )
                session = self._worker_session
            return session.observe(request)
        except Exception as exc:
            return {
                "status": "unavailable",
                "failure_code": type(exc).__name__,
                "error_detail": str(exc)[:512],
            }

    def current_scene_revision(self) -> str | None:
        with self._worker_lock:
            session = self._worker_session
        if session is None:
            return None
        try:
            result = session.scene_revision()
        except Exception:
            return None
        revision = result.get("scene_revision") if result.get("status") == "available" else None
        return revision if isinstance(revision, str) and revision.strip() else None

    def dry_run_cycle(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Resolve dispatch and parameters without importing or stepping Isaac Sim."""
        try:
            normalized = normalize_process_parameters(arguments, self.profile)
            if normalized["process_type"] in {"pour", "stir"}:
                target = _validate_cycle_target(arguments, normalized["process_type"])
            else:
                target = None
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
            "manipulation_target": {
                "status": "available",
                "motion_authorized": False,
                "entity_prim_path": target["entity_prim_path"],
                "destination_prim_path": target["destination_prim_path"],
            } if target is not None else None,
        }

    def _run_worker(self, arguments: Mapping[str, Any], cancel: Event) -> Mapping[str, Any]:
        try:
            with self._worker_lock:
                if self._worker_session is None:
                    from .worker_session import IsaacWorkerSession

                    self._worker_session = IsaacWorkerSession(
                        self.profile_path,
                        python_executable=self.profile.worker_python_path,
                        observation_artifact_root=self.observation_artifact_root,
                    )
                session = self._worker_session
            return session.request("execute_cycle", arguments, cancel=cancel)
        except Exception as exc:
            return {
                "status": "unknown",
                "outcome_known": False,
                "world_change_started": True,
                "failure_owner": "isaacsim_adapter",
                "failure_code": type(exc).__name__,
                "error_detail": str(exc)[:512],
            }

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
                "world_change_started": True,
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

    def _run_session_cycle(self, session: Any, arguments: Mapping[str, Any], cancel: Event, video_path: Path) -> dict[str, Any]:
        self._last_video_info = {}
        try:
            result = self._run_episode(session.app, arguments, cancel, video_path, session=session)
        except UnsupportedControllerCapabilityError as exc:
            result = _unsupported_result(exc)
        except Exception as exc:
            result = {
                "status": "unknown",
                "outcome_known": False,
                "world_change_started": True,
                "failure_owner": "isaacsim_adapter",
                "failure_code": type(exc).__name__,
                "error_detail": traceback.format_exc()[-2048:],
                "phase_events": _generic_phase_events([], process_completed=False, process_type="unknown"),
                "feedback_observations": [],
            }
        result.update(self._last_video_info)
        return result

    def observe_in_session(self, session: Any, request: Mapping[str, Any]) -> dict[str, Any]:
        """Initialize the shared scene, then capture through a registered source."""
        self._ensure_session_scene(session)
        source = session.resolve("observation_source")
        capture = getattr(source, "capture", None)
        if callable(capture):
            scene = session.resolve("lab_scene_resources")
            if scene is not None:
                # Annotator graphs require a playing timeline. World.render
                # disables physics while updating the app; restore the caller's
                # timeline state even if rendering or capture fails.
                world = scene["world"]
                was_playing = world.is_playing()
                try:
                    if not was_playing:
                        world.play()
                    for _ in range(getattr(self.profile, "camera_render_frames", 4)):
                        world.render()
                    result = capture(request)
                finally:
                    if not was_playing:
                        world.pause()
            else:
                result = capture(request)
            if isinstance(result, Mapping):
                captures = session.resolve("observation_captures")
                if captures is None:
                    captures = {}
                    session.register("observation_captures", captures)
                for view in result.get("views", [result]):
                    if view.get("calibration_ref"):
                        captures[view["calibration_ref"]] = deepcopy(dict(view))
                return {"status": "available", **dict(result)}
        return {
            "status": "unavailable",
            "outcome_known": False,
            "motion_authorized": False,
            "failure_code": "session_camera_registry_unavailable",
        }

    def _ensure_session_scene(self, session: Any) -> None:
        if session.resolve("observation_source") is not None:
            return
        scene = session.resolve("lab_scene_resources")
        if scene is None and not _isaac_runtime_available():
            return
        self._prepend_lab_root()
        from omegaconf import OmegaConf

        cfg = _observation_scene_config(
            OmegaConf.load(str(self.profile.config_path)),
            label_inspection_prim_path=self.profile.label_inspection_prim_path,
            label_inspection_focal_length_mm=self.profile.label_inspection_focal_length_mm,
        )
        if scene is None:
            import numpy as np
            import omni.usd
            from factories.robot_factory import create_robot
            from isaacsim.core.api import World
            from isaacsim.core.utils.stage import add_reference_to_stage
            from utils.object_utils import ObjectUtils

            scene = _get_session_scene_resources(
                session,
                profile=self.profile,
                world_factory=lambda: World(
                    stage_units_in_meters=1.0, physics_prim_path=self.profile.physics_scene_path, backend="numpy",
                    physics_dt=self.profile.physics_dt_s, rendering_dt=self.profile.control_dt_s
                ),
                robot_factory=lambda: create_robot(
                    cfg.robot.type,
                    position=np.array(getattr(cfg.robot, "position", getattr(cfg.robot, "base_position", [0.0, 0.0, 0.0]))),
                    orientation=np.array(getattr(
                        cfg.robot, "orientation",
                        getattr(cfg.robot, "base_orientation_wxyz", [1.0, 0.0, 0.0, 0.0]),
                    )),
                    usd_path=str(self.profile.robot_usd_path),
                ),
                stage_provider=lambda: omni.usd.get_context().get_stage(),
                add_reference_to_stage=add_reference_to_stage,
                object_utils=ObjectUtils,
            )
        if not scene["robot_initialized"]:
            scene["robot"].initialize()
            initial_arm = getattr(cfg.robot, "initial_joint_positions", None)
            initial_gripper = getattr(cfg.robot, "initial_gripper_positions", None)
            if initial_arm is not None or initial_gripper is not None:
                _apply_initial_robot_state(scene["robot"], initial_arm, initial_gripper)
                _refresh_initial_robot_state(scene["world"])
            scene["robot_initialized"] = True
        if getattr(cfg, "preview_light", None) is not None:
            from pxr import Gf, UsdLux

            # Match the original passive preview entry point's illumination.
            light = UsdLux.DomeLight.Define(scene["stage"], cfg.preview_light.prim_path)
            light.CreateIntensityAttr(cfg.preview_light.intensity)
            light.CreateColorAttr(Gf.Vec3f(*cfg.preview_light.color))
        session.initialize_scene_revision(self.profile.scene_revision)
        self._register_session_observation_source(session, cfg, scene["stage"])

    def ensure_action_scene(self, session: Any) -> None:
        """Initialize the worker-owned scene/revision before validating an action."""
        self._ensure_session_scene(session)

    def scene_revision_in_session(self, session: Any) -> dict[str, Any]:
        revision = session.current_scene_revision()
        if revision is None:
            return {"status": "unavailable", "failure_code": "scene_not_initialized"}
        return {"status": "available", "scene_revision": revision}

    def _register_session_observation_source(
        self, session: Any, cfg: Any, stage: Any
    ) -> None:
        if session.resolve("observation_source") is not None:
            return
        camera_configs = getattr(cfg, "cameras", None)
        if not camera_configs:
            return

        import numpy as np
        from isaacsim.sensors.camera import Camera

        cameras: dict[str, Any] = {}
        frame_ids: dict[str, str] = {}
        for camera_config in camera_configs:
            name = str(camera_config.name)
            prim_path = str(camera_config.prim_path)
            sensor_ref = f"sensor://{name}"
            if sensor_ref in cameras:
                raise IsaacLabRuntimeError(f"duplicate configured sensor name: {name}")
            camera_kwargs = {
                "prim_path": prim_path,
                "name": name,
                # Read-only renders do not advance the simulation clock.
                "frequency": -1,
                "resolution": tuple(camera_config.resolution),
            }
            if stage.GetPrimAtPath(prim_path).IsValid():
                camera = Camera(**camera_kwargs)
            else:
                if getattr(camera_config, "require_existing", False):
                    raise IsaacLabRuntimeError(f"authored observation camera is missing: {prim_path}")
                translation = np.asarray(camera_config.translation)
                orientation = np.asarray(camera_config.orientation)
                target_path = getattr(camera_config, "look_at_prim_path", None)
                if target_path:
                    target_prim = stage.GetPrimAtPath(str(target_path))
                    if not target_prim.IsValid():
                        raise IsaacLabRuntimeError(f"label inspection target is missing: {target_path}")
                    eye_attr = target_prim.GetAttribute("lab:wrist_inspection_eye_m")
                    target_attr = target_prim.GetAttribute("lab:wrist_inspection_target_m")
                    if not eye_attr or not target_attr:
                        raise IsaacLabRuntimeError(
                            f"label inspection pose is missing on target prim: {target_path}"
                        )
                    translation = np.asarray(eye_attr.Get(), dtype=float)
                    target = np.asarray(target_attr.Get(), dtype=float)
                    direction = target - translation
                    direction /= np.linalg.norm(direction)
                    back = -direction
                    right = np.cross(np.array([0.0, 0.0, 1.0]), back)
                    if np.linalg.norm(right) < 1e-6:
                        right = np.cross(np.array([0.0, 1.0, 0.0]), back)
                    right /= np.linalg.norm(right)
                    up = np.cross(back, right)
                    from scipy.spatial.transform import Rotation

                    orientation_xyzw = Rotation.from_matrix(
                        np.column_stack((right, up, back))
                    ).as_quat()
                    orientation = orientation_xyzw[[3, 0, 1, 2]]
                camera = Camera(
                    **camera_kwargs, translation=translation
                )
                camera.set_local_pose(
                    orientation=orientation, camera_axes="usd"
                )
                camera.set_focal_length(float(camera_config.focal_length))
            clipping = getattr(camera_config, "clipping_range", (0.1, 10.0))
            camera.set_clipping_range(
                near_distance=float(clipping[0]), far_distance=float(clipping[1])
            )
            camera.initialize()
            camera.add_distance_to_image_plane_to_frame()
            camera.add_pointcloud_to_frame()
            cameras[sensor_ref] = camera
            frame_ids[sensor_ref] = name

        if not cameras:
            return
        writer = FilesystemObservationArtifactWriter(
            self.observation_artifact_root
            or self.profile.lab_root / "outputs" / "paos-observation-artifacts",
            namespace="labutopia",
        )
        metadata = IsaacCameraMetadataProvider(
            cameras,
            lambda sensor_ref: frame_ids.get(sensor_ref),
            lambda sensor_ref: session.current_scene_revision() if sensor_ref in frame_ids else None,
            writer,
        )
        source = IsaacCameraObservationSource(
            cameras, metadata, writer, modalities=("rgb", "depth", "point_cloud")
        )
        session.register("camera_registry", cameras)
        session.register("observation_source", source)

    def close_session(self, session: Any) -> None:
        """Drop session-scoped backend references before SimulationApp shutdown."""
        del session
        self._last_video_info = {}

    def _run_episode(
        self,
        app: Any,
        arguments: Mapping[str, Any],
        cancel: Event,
        video_path: Path | None = None,
        *,
        session: Any | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_process_parameters(arguments, self.profile)
        process_type = normalized["process_type"]
        if process_type == "pour":
            return self._run_pour_episode(app, arguments, normalized, cancel, video_path, session=session)
        if process_type == "stir":
            return self._run_stir_episode(app, arguments, normalized, cancel, video_path, session=session)
        if session is not None:
            raise UnsupportedControllerCapabilityError(
                str(process_type), (),
                reason="worker-owned scene reuse is currently supported only for pour and stir tasks",
            )
        return self._run_rotation_episode(app, arguments, normalized, cancel, video_path)

    def _run_pour_episode(
        self,
        app: Any,
        arguments: Mapping[str, Any],
        process_parameters: Mapping[str, Any],
        cancel: Event,
        video_path: Path | None = None,
        *,
        session: Any | None = None,
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

        target = _target_in_world(_validate_cycle_target(arguments, "pour"))
        source_path = target["entity_prim_path"]
        destination_path = target["destination_prim_path"]

        cfg = OmegaConf.load(str(self.profile.config_path))
        with open_dict(cfg):
            cfg.usd_path = str(self.profile.scene_usd_path)
            cfg.mode = "collect"
            cfg.task_type = "pickpour"
            cfg.controller_type = "pickpour"
            cfg.max_episodes = 1
            cfg.target_path = destination_path
            cfg.multi_run.run_dir = str(self.profile.lab_root / "outputs" / "paos-pour-cycle")
            cfg.task.max_steps = max(int(cfg.task.max_steps), 1800)
            cfg.task.obj_paths = [{
                "path": source_path,
                "position_range": {
                    "x": [0.25, 0.30], "y": [0.02, 0.08], "z": [0.81, 0.81],
                },
            }]

        scene = _get_session_scene_resources(
            session,
            profile=self.profile,
            world_factory=lambda: World(
                stage_units_in_meters=1.0, physics_prim_path=self.profile.physics_scene_path, backend="numpy",
                    physics_dt=self.profile.physics_dt_s, rendering_dt=self.profile.control_dt_s
            ),
            robot_factory=lambda: create_robot(
                cfg.robot.type,
                position=np.array(getattr(cfg.robot, "position", getattr(cfg.robot, "base_position", [0.0, 0.0, 0.0]))),
                orientation=np.array(getattr(
                    cfg.robot, "orientation",
                    getattr(cfg.robot, "base_orientation_wxyz", [1.0, 0.0, 0.0, 0.0]),
                )),
                usd_path=str(self.profile.robot_usd_path),
            ),
            stage_provider=lambda: omni.usd.get_context().get_stage(),
            add_reference_to_stage=add_reference_to_stage,
            object_utils=ObjectUtils,
        )
        world, robot, stage = scene["world"], scene["robot"], scene["stage"]
        task = _create_session_owned_task(
            world, robot, PickPourTask, scene_state=scene,
            initial_joint_positions=getattr(cfg.robot, "initial_joint_positions", None),
            initial_gripper_positions=getattr(cfg.robot, "initial_gripper_positions", None),
            cfg=cfg, stage=stage
        )
        controller = create_controller(cfg.controller_type, cfg=cfg, robot=robot)
        _configure_pour_controller(controller, process_parameters)
        _configure_target_controllers(controller, target, "pour")
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
                state = dict(state)
                state["target_position"] = np.asarray(target["destination_pose"]["position_m"], dtype=float)
                state["grasp_object_path"] = target.get("tool_prim_path") or source_path
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
                        state["target_position"] = _pour_controller_target(
                            state, self.profile, np, Rotation, target.get("process_frame")
                        )
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
                        place_position=np.asarray(target["return_pose"]["position_m"], dtype=float),
                        current_joint_positions=state["joint_positions"],
                        gripper_control=controller.gripper_control,
                        end_effector_orientation=np.asarray(
                            target["return_pose"]["orientation_xyzw"], dtype=float
                        ),
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
                    "phase_events": _phase_events(samples, pickpour_success, placement_done, self.profile, process_parameters),
                    "feedback_observations": samples,
                    "feedback_source_profile": self.profile.source_profile(),
                    "evaluation_profile": self.profile.evaluation_profile(),
                }
            else:
                final = samples[-1] if samples else {}
                events = _phase_events(samples, pickpour_success, placement_done, self.profile, process_parameters)
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
        *,
        session: Any | None = None,
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

        target = _target_in_world(_validate_cycle_target(arguments, "stir"))
        source_path = target["entity_prim_path"]
        tool_path = target.get("tool_prim_path")
        destination_path = target["destination_prim_path"]

        cfg = OmegaConf.load(str(self.profile.config_path))
        with open_dict(cfg):
            cfg.usd_path = str(self.profile.scene_usd_path)
            cfg.mode = "collect"
            cfg.task_type = "stir"
            cfg.controller_type = "stirglassrod"
            cfg.max_episodes = 1
            cfg.obj_path = source_path
            cfg.sub_obj_path = str(
                arguments.get("tool_mesh_path")
                or tool_path
            )
            cfg.target_path = destination_path
            cfg.multi_run.run_dir = str(self.profile.lab_root / "outputs" / "paos-stir-cycle")
            if not hasattr(cfg, "task"):
                cfg.task = {}
            cfg.task.max_steps = max(int(cfg.task.get("max_steps", 2000)), 2000)
            cfg.task.obj_paths = [{"path": source_path, "position_range": {"x": [0.25, 0.30], "y": [0.02, 0.08], "z": [0.81, 0.81]}}]

        scene = _get_session_scene_resources(
            session,
            profile=self.profile,
            world_factory=lambda: World(
                stage_units_in_meters=1.0, physics_prim_path=self.profile.physics_scene_path, backend="numpy",
                    physics_dt=self.profile.physics_dt_s, rendering_dt=self.profile.control_dt_s
            ),
            robot_factory=lambda: create_robot(
                cfg.robot.type,
                position=np.array(getattr(cfg.robot, "position", getattr(cfg.robot, "base_position", [0.0, 0.0, 0.0]))),
                orientation=np.array(getattr(
                    cfg.robot, "orientation",
                    getattr(cfg.robot, "base_orientation_wxyz", [1.0, 0.0, 0.0, 0.0]),
                )),
                usd_path=str(self.profile.robot_usd_path)
            ),
            stage_provider=lambda: omni.usd.get_context().get_stage(),
            add_reference_to_stage=add_reference_to_stage,
            object_utils=ObjectUtils,
        )
        world, robot, stage = scene["world"], scene["robot"], scene["stage"]
        task = _create_session_owned_task(
            world, robot, StirTask, scene_state=scene,
            initial_joint_positions=getattr(cfg.robot, "initial_joint_positions", None),
            initial_gripper_positions=getattr(cfg.robot, "initial_gripper_positions", None),
            cfg=cfg, stage=stage
        )
        controller = create_controller(cfg.controller_type, cfg=cfg, robot=robot)
        _configure_stir_controller(controller, process_parameters)
        _configure_target_controllers(controller, target, "stir")
        controller.initial_control_position = np.asarray(target["return_pose"]["position_m"], dtype=float)
        world.play()
        samples: list[dict[str, Any]] = []
        initial_position = None
        initial_quaternion = None
        step = 0
        dt = 1.0 / 60.0
        done = False
        success = False
        stir_tip_offset = None
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
                state["target_position"] = np.asarray(target["destination_pose"]["position_m"], dtype=float)
                state["grasp_object_path"] = tool_path
                state["feedback_object_position"] = state.get("glass_rod_position")
                state["stir_phase"] = getattr(getattr(controller, "stir_controller", None), "phase", None)
                state["stir_angle"] = getattr(getattr(controller, "stir_controller", None), "stir_angle", 0.0)
                state["grasped_object_path"] = getattr(
                    getattr(controller, "gripper_control", None), "grasped_object_path", None
                )
                state["tool_prim_path"] = cfg.sub_obj_path
                state["destination_prim_path"] = destination_path
                state["tool_tip_frame_id"] = target["tool_frame"]["frame_id"]
                state["tool_tip_position"] = _usd_geometry_endpoint(
                    task.object_utils, cfg.sub_obj_path, target["tool_frame"]["tip_axis_local"]
                )
                state["tool_tip_coordinates"] = _usd_point_in_container_frame(
                    stage,
                    destination_path,
                    state.get("target_position"),
                    state["tool_tip_position"],
                    target["tool_frame"]["frame_id"],
                )
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
                controller_state = state
                if controller_phase == "stirring":
                    if stir_tip_offset is None:
                        stir_tip_offset = _stir_tip_offset(
                            state.get("tool_tip_position"), state.get("gripper_position"), np
                        )
                    if stir_tip_offset is not None:
                        controller_state = dict(state)
                        controller_state["target_position"] = _stir_controller_target(
                            state["target_position"], stir_tip_offset, np,
                        )
                        state["stir_tip_offset"] = stir_tip_offset
                action, done, success = controller.step(controller_state)
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
            process_parameters=process_parameters,
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

        world = World(stage_units_in_meters=1.0, physics_prim_path=self.profile.physics_scene_path, backend="numpy",
                    physics_dt=self.profile.physics_dt_s, rendering_dt=self.profile.control_dt_s)
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
            tool_tip_position = state.get("tool_tip_position")
            container_quaternion = state.get("container_quaternion")
            tip_coordinates = state.get("tool_tip_coordinates")
            if tip_coordinates is None and tool_tip_position is not None and container_quaternion is not None:
                tip_world = np.asarray(tool_tip_position, dtype=float).reshape(3)
                container_quat = np.asarray(container_quaternion, dtype=float).reshape(4)
                relative_tip = rotation_cls.from_quat(container_quat).inv().apply(tip_world - target)
                tip_coordinates = {
                    "x_m": float(relative_tip[0]),
                    "y_m": float(relative_tip[1]),
                    "depth_m": float(self.profile.stir_rim_height_m - relative_tip[2]),
                    "frame_id": self.profile.tool_tip_frame_id,
                }
            elif isinstance(tip_coordinates, Mapping) and "local_z_m" in tip_coordinates:
                tip_coordinates = {
                    **tip_coordinates,
                    "depth_m": float(self.profile.stir_rim_height_m - float(tip_coordinates["local_z_m"])),
                }
                state["tool_tip_coordinates"] = tip_coordinates
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
        if process_parameters.get("process_type") == "stir":
            expected_path = state.get("tool_prim_path") or self.profile.source_control_path or self.profile.source_path
            grasp = state.get("grasped_object_path") == expected_path
        else:
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
            "feedback_valid": process_parameters.get("process_type") != "stir" or tip_coordinates is not None,
            "grasp_valid": grasp,
            "engagement_valid": engagement_valid,
            "transform_progress": transform_progress,
            "transform_error": transform_error,
            "target_container_aligned": alignment <= self.profile.alignment_tolerance_m,
            "alignment_error_m": alignment,
            "source_pour_point": {"x_m": float(pour_point[0]), "y_m": float(pour_point[1]), "z_m": float(pour_point[2]), "frame_id": self.profile.frame_id},
            "feedback_object_path": state.get("tool_prim_path") or self.profile.source_control_path or self.profile.source_path,
            "target_position": {"x_m": float(target[0]), "y_m": float(target[1]), "z_m": float(target[2]), "frame_id": self.profile.frame_id},
            "stir_angle_rad": float(state.get("stir_angle", 0.0) or 0.0),
            **({
                "tool_tip_x_m": tip_coordinates["x_m"],
                "tool_tip_y_m": tip_coordinates["y_m"],
                "tool_tip_depth_m": tip_coordinates["depth_m"],
                "tool_tip_frame_id": tip_coordinates["frame_id"],
            } if process_parameters.get("process_type") == "stir" and tip_coordinates is not None else {}),
            "tilt_rad": tilt,
            **({
                "stir_tip_offset_x_m": float(state["stir_tip_offset"][0]),
                "stir_tip_offset_y_m": float(state["stir_tip_offset"][1]),
                "stir_tip_offset_z_m": float(state["stir_tip_offset"][2]),
            } if process_parameters.get("process_type") == "stir" and state.get("stir_tip_offset") is not None else {}),
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
    target_tilt = float(parameters["magnitude"])
    angular_speed = max(float(parameters["speed"]), 1e-6)
    # The atomic controller advances its rotation phases by normalized event
    # increments.  Set both directions to the requested physical angle.
    event_dt = angular_speed / (60.0 * target_tilt)
    if hasattr(active, "_events_dt") and len(active._events_dt) >= 5:
        active._events_dt[2] = event_dt
        active._events_dt[4] = event_dt
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
            # The measured PAOS interval starts at the first sampled point and
            # therefore loses one frame at each boundary.  Run two extra
            # simulation frames so the requested duration is observable.
            duration_s=float(values.get("stir_duration_s", parameters.get("hold_s"))) + (2.0 / 60.0),
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


def _usd_geometry_endpoint(object_utils: Any, prim_path: str, axis_local: Sequence[float]):
    """Measure a geometry endpoint from the live USD prim pose and bounds."""
    try:
        import numpy as np
        from pxr import Gf, Usd, UsdGeom

        stage = getattr(object_utils, "_stage", None)
        if stage is None:
            return None
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return None
        axis = np.asarray(axis_local, dtype=float)
        axis_norm = float(np.linalg.norm(axis))
        if axis.shape != (3,) or not np.isfinite(axis_norm) or axis_norm <= 0:
            return None
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
        local_range = cache.ComputeLocalBound(prim).GetRange()
        minimum = np.asarray(local_range.GetMin(), dtype=float)
        maximum = np.asarray(local_range.GetMax(), dtype=float)
        if minimum.shape != (3,) or maximum.shape != (3,) or not np.all(np.isfinite([*minimum, *maximum])):
            return None
        direction = axis / axis_norm
        endpoint = _bound_endpoint(minimum, maximum, direction)
        if endpoint is None:
            return None
        world = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).Transform(
            Gf.Vec3d(*endpoint.tolist())
        )
        return np.asarray(world, dtype=float)
    except Exception:
        return None


def _bound_endpoint(minimum: Sequence[float], maximum: Sequence[float], direction: Sequence[float]):
    import numpy as np

    lower, upper, axis = (np.asarray(value, dtype=float) for value in (minimum, maximum, direction))
    if any(value.shape != (3,) for value in (lower, upper, axis)):
        return None
    if not np.all(np.isfinite([*lower, *upper, *axis])) or np.linalg.norm(axis) <= 0:
        return None
    axis = axis / np.linalg.norm(axis)
    corners = [
        np.asarray([x, y, z], dtype=float)
        for x in (lower[0], upper[0])
        for y in (lower[1], upper[1])
        for z in (lower[2], upper[2])
    ]
    return max(corners, key=lambda point: float(np.dot(point, axis)))


def _usd_point_in_container_frame(stage: Any, container_path: str, container_center_world: Any,
                                  point_world: Any, frame_id: str):
    """Express a measured world point relative to the container geometry center."""
    try:
        import numpy as np
        from pxr import Gf, Usd, UsdGeom

        if container_center_world is None or point_world is None:
            return None
        prim = stage.GetPrimAtPath(container_path)
        if not prim.IsValid():
            return None
        inverse = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).GetInverse()
        center_local = inverse.Transform(Gf.Vec3d(*np.asarray(container_center_world, dtype=float).reshape(3).tolist()))
        point_local = inverse.Transform(Gf.Vec3d(*np.asarray(point_world, dtype=float).reshape(3).tolist()))
        relative = np.asarray(point_local - center_local, dtype=float)
        return {
            "x_m": float(relative[0]),
            "y_m": float(relative[1]),
            "frame_id": frame_id,
            "local_z_m": float(relative[2]),
        }
    except Exception:
        return None


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
        tip_xy = state.get("tool_tip_coordinates")
        if isinstance(tip_xy, Mapping):
            return min(float(parameters.get("magnitude", 0.0)),
                       math.hypot(float(tip_xy["x_m"]), float(tip_xy["y_m"])))
        radius = float(parameters.get("magnitude", 0.0))
        target = state.get("target_position", position)
        radial = sum((float(position[index]) - float(target[index])) ** 2 for index in (0, 1)) ** 0.5
        displacement = sum((float(position[index]) - float(initial_position[index])) ** 2 for index in range(3)) ** 0.5
        return min(radius, max(radial, displacement))
    return 0.0


def _identity_rotation():
    from scipy.spatial.transform import Rotation

    return Rotation


def _stir_tip_offset(tool_tip_position: Any, gripper_position: Any, np):
    """Return the measured world-space offset from the gripper to the rod tip."""
    if tool_tip_position is None or gripper_position is None:
        return None
    tip = np.asarray(tool_tip_position, dtype=float).reshape(-1)
    gripper = np.asarray(gripper_position, dtype=float).reshape(-1)
    if tip.size < 3 or gripper.size < 3:
        return None
    if not np.all(np.isfinite(tip[:3])) or not np.all(np.isfinite(gripper[:3])):
        return None
    return tip[:3] - gripper[:3]


def _stir_controller_target(container_center: Any, tip_offset: Any, np):
    """Shift the controller center so its own radius is applied at the measured rod tip."""
    center = np.asarray(container_center, dtype=float).reshape(-1)
    offset = np.asarray(tip_offset, dtype=float).reshape(-1)
    if center.size < 3 or offset.size < 3:
        raise ValueError("stir controller target requires a 3D center and tip offset")
    if not np.all(np.isfinite(center[:3])) or not np.all(np.isfinite(offset[:3])):
        raise ValueError("stir controller target requires finite center and tip offset")
    return center[:3] - offset[:3]


def _stir_trace_metrics(samples: Sequence[Mapping[str, Any]], parameters: Mapping[str, Any], profile: LabUtopiaProfile):
    """Match PAOS stir qualification using measured tip coordinates and continuous motion."""
    turns_required = float(parameters.get("turns", profile.stir_turns))
    duration_required = float(parameters.get("duration_s", profile.stir_duration_s))
    radius_required = float(parameters.get("radius_m", parameters.get("magnitude", profile.stir_radius_m)))
    depth_required = float(parameters.get("depth_m", profile.stir_depth_m))
    direction = 1.0 if parameters.get("direction", profile.stir_direction) == "ccw" else -1.0
    run_turns = 0.0
    run_duration = 0.0
    best_turns = 0.0
    best_duration = 0.0
    previous = None
    for sample in samples:
        coordinates = (sample.get("tool_tip_x_m"), sample.get("tool_tip_y_m"), sample.get("tool_tip_depth_m"))
        valid = sample.get("feedback_valid") is True and sample.get("grasp_valid") is True
        valid = valid and all(_number(value) is not None for value in coordinates)
        angle = None
        if valid:
            x, y, depth = map(float, coordinates)
            radius = math.hypot(x, y)
            valid = (
                abs(radius - radius_required) <= profile.stir_radius_tolerance_m
                and abs(depth - depth_required) <= profile.stir_depth_tolerance_m
                and radius <= profile.stir_container_radius_m
                and 0.0 <= depth <= profile.stir_container_depth_m
            )
            angle = math.atan2(y, x)
        timestamp = float(sample.get("timestamp_s", 0.0))
        delta_time = timestamp - float(previous["timestamp_s"]) if previous else 0.0
        continuous = valid and previous is not None and previous["valid"] and 0 < delta_time <= profile.max_sample_gap_s
        if continuous:
            delta_angle = (angle - previous["angle"] + math.pi) % (2.0 * math.pi) - math.pi
            directed = direction * delta_angle
            if abs(delta_angle) > profile.max_angular_step_rad or directed < 0:
                run_turns = run_duration = 0.0
            else:
                run_turns += directed / (2.0 * math.pi)
                run_duration += delta_time
                best_turns = max(best_turns, run_turns)
                best_duration = max(best_duration, run_duration)
        else:
            run_turns = run_duration = 0.0
        previous = {"timestamp_s": timestamp, "angle": angle, "valid": bool(valid)}
    return {
        "qualified": best_turns >= turns_required and best_duration + 1e-6 >= duration_required,
        "turns": best_turns,
        "duration_s": best_duration,
        "required_turns": turns_required,
        "required_duration_s": duration_required,
    }


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


def _stir_phase_events(samples, *, process_completed: bool, process_type: str,
                       profile: LabUtopiaProfile, process_parameters: Mapping[str, Any] | None = None):
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
    process_parameters = dict(process_parameters or {})
    requested_turns = float(process_parameters.get("turns", profile.stir_turns) or profile.stir_turns)
    requested_radius = float(process_parameters.get("radius_m", process_parameters.get("magnitude", profile.stir_radius_m)))
    required_stir_angle = 2.0 * 3.141592653589793 * requested_turns * 0.9
    process_metrics = _stir_trace_metrics(process_samples, process_parameters, profile)
    process_valid = bool(process_completed and process_metrics["qualified"])
    if grasp:
        events[0] = _event("acquire", 0.0, grasp["timestamp_s"], {"grasp_confirmed": True, "possession_state": "holding"})
    if aligned:
        events[1] = _event("transport", grasp["timestamp_s"] if grasp else 0.0, aligned["timestamp_s"], {"route_completed": True, "possession_state": "holding"})
    if process_valid:
        events[2] = _event(
            "process", process_started["timestamp_s"], process_end["timestamp_s"],
            {"process_type": process_type, "transform_progress": requested_radius,
             "duration_s": process_metrics["duration_s"],
             "stir_angle_rad": process_metrics["turns"] * 2.0 * 3.141592653589793,
             "required_stir_angle_rad": required_stir_angle},
        )
    elif process_started:
        events[2] = {
            "phase": "process", "status": "failed", "outcome_known": True,
            "started_at_s": float(process_started["timestamp_s"]),
            "completed_at_s": float(max(float(samples[-1]["timestamp_s"]), float(process_started["timestamp_s"]) + 0.001)),
            "facts": {"failure_reason": "stir_observation_not_qualified", **process_metrics},
        }

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


def _phase_events(samples, pickpour_success: bool, placement_done: bool, profile: LabUtopiaProfile,
                  process_parameters: Mapping[str, Any]):
    if not samples:
        return _generic_phase_events([], process_completed=False, process_type="pour")
    last = float(samples[-1]["timestamp_s"])
    grasp = next((sample for sample in samples if sample["grasp_valid"]), None)
    aligned = next((sample for sample in samples if sample["target_container_aligned"] and sample["grasp_valid"]), None)
    window = _continuous_pour_window(samples, profile, process_parameters)
    returned = next((sample for sample in reversed(samples) if sample["grasp_valid"] and abs(float(sample["tilt_rad"])) <= float(process_parameters["tolerance"])), None)
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


def _continuous_pour_window(samples, profile, process_parameters=None):
    """Find one uninterrupted grasp/alignment/tilt window of the required duration."""
    process_parameters = dict(process_parameters or {
        "magnitude": profile.tilt_rad,
        "tolerance": profile.tilt_tolerance_rad,
        "maximum_tilt_rad": profile.maximum_tilt_rad,
        "hold_s": profile.hold_s,
    })
    start = None
    previous = None
    for sample in samples:
        qualifies = (
            sample["grasp_valid"]
            and sample["target_container_aligned"]
            and abs(float(sample["tilt_rad"]) - float(process_parameters["magnitude"])) <= float(process_parameters["tolerance"])
            and abs(float(sample["tilt_rad"])) <= float(process_parameters["maximum_tilt_rad"])
        )
        timestamp = float(sample["timestamp_s"])
        if not qualifies or (previous is not None and timestamp - previous > profile.max_sample_gap_s):
            start = None
            previous = None
            continue
        if start is None:
            start = timestamp
        previous = timestamp
        if timestamp - start >= float(process_parameters["hold_s"]):
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
    window = _continuous_pour_window(
        samples,
        profile,
        {"magnitude": profile.tilt_rad, "tolerance": profile.tilt_tolerance_rad,
         "maximum_tilt_rad": profile.maximum_tilt_rad, "hold_s": profile.hold_s},
    ) if samples else None
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


def _pour_controller_target(state, profile, np, rotation_cls, process_frame=None):
    """Compensate the provider controller target for the measured mouth offset."""
    target = np.asarray(
        (process_frame or {}).get("origin_m", state["target_position"]), dtype=float
    ).copy()
    quat = np.asarray(state["object_quaternion"], dtype=float)
    size = np.asarray(state["object_size"], dtype=float)
    axis = (process_frame or {}).get("axis", profile.source_pour_axis)
    mouth_offset = rotation_cls.from_quat(quat).apply(np.asarray(axis, dtype=float) * (size[2] / 2.0))
    return target - mouth_offset


def _observation_scene_config(
    cfg, *, label_inspection_prim_path=None, label_inspection_focal_length_mm=3.5
):
    """Project LabUtopia's authored station config inside the Adapter boundary.

    The original station owns placement and optics. Register its existing
    cameras without copying layout fields into perception or Tool contracts.
    Legacy camera deployment configurations retain their original behavior.
    """
    if getattr(cfg.robot, "base_position", None) is None:
        return cfg
    from types import SimpleNamespace

    cameras = [
        {"name": "tabletop_third_person", "prim_path": "/World/PreviewCameras/ThirdPerson",
         "resolution": [1600, 1200], "clipping_range": [.05, 10.], "require_existing": True},
        {"name": "tabletop_wrist", "prim_path": str(cfg.robot.wrist_camera.prim_path),
         "resolution": [1280, 960], "clipping_range": list(cfg.robot.wrist_camera.clipping_range),
         "require_existing": True},
    ]
    if label_inspection_prim_path:
        cameras.append({
            "name": "label_inspection_r01",
            "prim_path": "/World/PAOSCameras/LabelInspectionR01",
            "resolution": [1280, 960],
            "clipping_range": [.03, 3.],
            "translation": [0., 0., 0.],
            "orientation": [1., 0., 0., 0.],
            "focal_length": float(label_inspection_focal_length_mm),
            "look_at_prim_path": str(label_inspection_prim_path),
        })
    return SimpleNamespace(
        robot=SimpleNamespace(
            type=cfg.robot.type,
            position=list(cfg.robot.base_position),
            orientation=list(getattr(cfg.robot, "base_orientation_wxyz", [1.0, 0.0, 0.0, 0.0])),
            initial_joint_positions=(list(cfg.robot.initial_joint_positions)
                                     if getattr(cfg.robot, "initial_joint_positions", None) is not None else None),
            initial_gripper_positions=(list(cfg.robot.initial_gripper_positions)
                                       if getattr(cfg.robot, "initial_gripper_positions", None) is not None else None),
        ),
        cameras=[SimpleNamespace(**camera) for camera in cameras],
        preview_light=SimpleNamespace(prim_path="/World/PreviewDomeLight", intensity=1200., color=(.88, .93, 1.)),
    )


def _get_session_scene_resources(
    session: Any | None,
    *,
    profile: LabUtopiaProfile,
    world_factory: Any,
    robot_factory: Any,
    stage_provider: Any,
    add_reference_to_stage: Any,
    object_utils: Any,
) -> dict[str, Any]:
    """Resolve one worker-owned scene, or create episode-local resources in-process."""
    if session is not None:
        existing = session.resolve("lab_scene_resources")
        if existing is not None:
            if existing["scene_usd_path"] != str(profile.scene_usd_path):
                raise IsaacLabRuntimeError("worker session cannot switch its loaded scene")
            return existing

    # Import the authored PhysicsScene before World selects its physics owner.
    add_reference_to_stage(usd_path=str(profile.scene_usd_path), prim_path="/World")
    world = world_factory()
    robot = robot_factory()
    stage = stage_provider()
    object_utils.get_instance(stage)
    scene = {
        "world": world,
        "robot": robot,
        "stage": stage,
        "scene_usd_path": str(profile.scene_usd_path),
        "world_initialized": False,
        "robot_initialized": False,
    }
    if session is not None:
        world.reset()
        if profile.startup_settle_s:
            import math

            world.play()
            for _ in range(math.ceil(profile.startup_settle_s / profile.control_dt_s)):
                world.step(render=True)
            world.pause()
        scene["world_initialized"] = True
        session.register("lab_scene_resources", scene)
    return scene


def _create_session_owned_task(
    world: Any,
    robot: Any,
    task_type: Any,
    *,
    scene_state: dict[str, Any] | None = None,
    initial_joint_positions: Any | None = None,
    initial_gripper_positions: Any | None = None,
    **kwargs: Any,
) -> Any:
    """Construct an episode Task without resetting session-owned scene resources."""
    if scene_state is None or not scene_state["world_initialized"]:
        world.reset()
        if scene_state is not None:
            scene_state["world_initialized"] = True
    task = task_type(world=world, robot=robot, session_owned_scene=True, **kwargs)
    if scene_state is None or not scene_state["robot_initialized"]:
        robot.initialize()
        if scene_state is not None:
            scene_state["robot_initialized"] = True
    if initial_joint_positions is not None or initial_gripper_positions is not None:
        _apply_initial_robot_state(
            robot, initial_joint_positions, initial_gripper_positions
        )
        _refresh_initial_robot_state(world)
    task.reset()
    if initial_joint_positions is not None or initial_gripper_positions is not None:
        _apply_initial_robot_state(
            robot, initial_joint_positions, initial_gripper_positions
        )
        _refresh_initial_robot_state(world)
    return task


def _apply_initial_robot_state(
    robot: Any, arm_positions: Any, gripper_positions: Any
) -> None:
    """Set the configured arm and gripper state after task reset, before motion."""
    import numpy as np

    if arm_positions is None or gripper_positions is None:
        raise IsaacLabRuntimeError(
            "Franka initial state requires both arm and gripper positions"
        )
    arm = np.asarray(arm_positions, dtype=float).reshape(-1)
    gripper = np.asarray(gripper_positions, dtype=float).reshape(-1)
    if arm.size != 7 or gripper.size != 2:
        raise IsaacLabRuntimeError(
            "Franka initial state requires seven arm and two gripper positions"
        )
    positions = np.concatenate((arm, gripper))
    if not np.all(np.isfinite(positions)):
        raise IsaacLabRuntimeError("Franka initial joint positions must be finite")
    actual = np.asarray(robot.get_joint_positions(), dtype=float).reshape(-1)
    if actual.size != positions.size:
        raise IsaacLabRuntimeError(
            f"Franka articulation has {actual.size} joints; expected {positions.size}"
        )
    robot.set_joint_positions(positions)


def _refresh_initial_robot_state(world: Any) -> None:
    """Propagate an authored qpos into link/camera transforms without a command."""
    was_playing = bool(world.is_playing())
    try:
        if not was_playing:
            world.play()
        world.step(render=True)
    finally:
        if not was_playing:
            world.pause()


def _target_in_world(target: Mapping[str, Any]) -> dict[str, Any]:
    """Transform perception poses/vectors into Isaac Sim world coordinates.

    PAOS perception may publish in a camera or calibrated control frame.  The
    simulator controllers, USD stage, and placement feedback all operate in
    world coordinates, so the transform is explicit and required by the
    target contract rather than inferred from a frame name.
    """
    import numpy as np
    from scipy.spatial.transform import Rotation

    resolved = deepcopy(dict(target))
    transform = resolved["world_from_control"]
    world_rotation = Rotation.from_quat(np.asarray(transform["orientation_xyzw"], dtype=float))
    world_origin = np.asarray(transform["translation_m"], dtype=float)

    def pose_to_world(pose: Mapping[str, Any]) -> dict[str, Any]:
        position = world_origin + world_rotation.apply(np.asarray(pose["position_m"], dtype=float))
        orientation = (world_rotation * Rotation.from_quat(np.asarray(pose["orientation_xyzw"], dtype=float))).as_quat()
        result = dict(pose)
        result["frame_id"] = "world"
        result["position_m"] = position.tolist()
        result["orientation_xyzw"] = orientation.tolist()
        return result

    for key in ("object_pose", "grasp_frame", "destination_pose", "return_pose"):
        resolved[key] = pose_to_world(resolved[key])
    approach = dict(resolved["approach_direction"])
    approach["frame_id"] = "world"
    approach["vector"] = world_rotation.apply(np.asarray(approach["vector"], dtype=float)).tolist()
    resolved["approach_direction"] = approach
    if isinstance(resolved.get("process_frame"), Mapping):
        process = dict(resolved["process_frame"])
        process["frame_id"] = "world"
        process["origin_m"] = (
            world_origin + world_rotation.apply(np.asarray(process["origin_m"], dtype=float))
        ).tolist()
        process["axis"] = world_rotation.apply(np.asarray(process["axis"], dtype=float)).tolist()
        resolved["process_frame"] = process
    return resolved


def _configure_target_controllers(controller: Any, target: Mapping[str, Any], process_type: str) -> None:
    """Inject the selected grasp pose and approach into LabUtopia's pick primitive."""
    import numpy as np

    picker = getattr(controller, "pick_controller", None)
    if picker is None:
        raise IsaacLabRuntimeError("selected LabUtopia task does not expose its pick controller")
    original_forward = picker.forward
    grasp = target["grasp_frame"]
    grasp_position = np.asarray(grasp["position_m"], dtype=float)
    grasp_orientation = np.asarray(grasp["orientation_xyzw"], dtype=float)
    approach = np.asarray(target["approach_direction"]["vector"], dtype=float)
    grasp_prim = target.get("tool_prim_path") or target["entity_prim_path"]
    original_approach = picker._calculate_approach_direction
    picker._calculate_approach_direction = lambda _position: approach.copy()

    def configured_pick(*args, **kwargs):
        kwargs["picking_position"] = grasp_position.copy()
        kwargs["end_effector_orientation"] = grasp_orientation.copy()
        kwargs["pre_offset_x"] = 0.0
        kwargs["pre_offset_z"] = 0.0
        kwargs["grasp_object_path"] = grasp_prim
        kwargs["object_name"] = process_type
        return original_forward(*args, **kwargs)

    picker.forward = configured_pick
    # Preserve the controller method for callers that reuse an episode object.
    picker._paos_original_approach = original_approach
    destination = target["destination_pose"]
    destination_position = np.asarray(destination["position_m"], dtype=float)
    destination_orientation = np.asarray(destination["orientation_xyzw"], dtype=float)
    return_orientation = np.asarray(target["return_pose"]["orientation_xyzw"], dtype=float)
    if process_type == "stir":
        active = getattr(controller, "stir_controller", None)
        if active is None:
            raise IsaacLabRuntimeError("selected LabUtopia task does not expose its stir controller")
        original = active.forward

        def configured_stir(*args, **kwargs):
            kwargs["center_position"] = destination_position.copy()
            kwargs["end_effector_orientation"] = destination_orientation.copy()
            return original(*args, **kwargs)

        active.forward = configured_stir
        place = getattr(controller, "place_controller", None)
        if place is not None:
            original_place = place.forward

            def configured_place(*args, **kwargs):
                kwargs["end_effector_orientation"] = return_orientation.copy()
                return original_place(*args, **kwargs)

            place.forward = configured_place
    elif process_type == "pour":
        active = getattr(controller, "pour_controller", None)
        if active is None:
            raise IsaacLabRuntimeError("selected LabUtopia task does not expose its pour controller")
        original = active.forward

        def configured_pour(*args, **kwargs):
            kwargs["target_position"] = destination_position.copy()
            kwargs["target_end_effector_orientation"] = destination_orientation.copy()
            kwargs["source_name"] = process_type
            return original(*args, **kwargs)

        active.forward = configured_pour


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
