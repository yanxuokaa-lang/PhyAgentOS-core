"""Configuration and PAOS input projection for a LabUtopia Isaac scene."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class LabProfileError(ValueError):
    """The LabUtopia scene cannot be bound to a PAOS cycle."""


@dataclass(frozen=True)
class LabUtopiaProfile:
    """Externalized paths and frame identities for one laboratory deployment."""

    lab_root: Path
    config_path: Path
    scene_usd_path: Path
    robot_usd_path: Path
    source_path: str
    destination_path: str
    source_control_path: str | None = None
    source_label: str = "试剂A"
    destination_label: str = "烧杯"
    profile_path: Path | None = None
    frame_id: str = "lab_camera_front"
    calibration_ref: str = "artifact://labutopia/calibration-v1"
    scene_revision: str = "labutopia-scene-v1"
    observation_ref: str = "observation://labutopia/initial"
    capability_snapshot_ref: str = "artifact://labutopia/capabilities-v1"
    return_destination_ref: str = "destination://labutopia/source-home"
    container_frame_id: str = "container://labutopia/beaker2"
    tool_tip_frame_id: str = "container://labutopia/beaker2"
    max_age_ms: int = 1000
    freshness_ms: int = 0
    tilt_rad: float = 0.87
    hold_s: float = 0.6
    stir_radius_m: float = 0.009
    stir_depth_m: float = 0.04
    stir_turns: float = 2.0
    stir_duration_s: float = 4.0
    stir_direction: str = "ccw"
    tool_tip_axis_local: tuple[float, float, float] = (0.0, 0.0, -1.0)
    max_angular_step_rad: float = 0.5
    stir_radius_tolerance_m: float = 0.002
    stir_depth_tolerance_m: float = 0.005
    stir_container_radius_m: float = 0.05
    stir_container_depth_m: float = 0.08
    stir_rim_height_m: float = 0.04
    alignment_tolerance_m: float = 0.05
    tilt_tolerance_rad: float = 0.10
    maximum_tilt_rad: float = 1.50
    max_sample_gap_s: float = 0.10
    gripper_closed_max_m: float = 0.035
    object_lift_threshold_m: float = 0.04
    grasp_distance_tolerance_m: float = 0.16
    source_pour_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    configured_process_type: str = "pour"
    supported_operations: tuple[str, ...] = ("pour_cycle", "stir_cycle", "manipulation_cycle")
    headless: bool = True
    camera_render_frames: int = 4
    motion_config_path: Path | None = None
    perception_config_path: Path | None = None
    worker_python_path: Path | None = None
    physics_scene_path: str = "/physicsScene"
    physics_dt_s: float = 1 / 60
    control_dt_s: float = 1 / 60
    startup_settle_s: float = 0.

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, base_dir: Path | None = None) -> "LabUtopiaProfile":
        if not isinstance(value, Mapping):
            raise LabProfileError("lab profile must be a mapping")
        base = Path(base_dir or ".").resolve()

        def path_value(name: str) -> Path:
            raw = value.get(name)
            if not isinstance(raw, str) or not raw.strip():
                raise LabProfileError(f"lab profile requires {name}")
            path = Path(raw).expanduser()
            return path if path.is_absolute() else (base / path).resolve()

        lab_root = path_value("lab_root")
        default_robot = lab_root / "assets/robots/Franka.usd"
        profile = cls(
            lab_root=lab_root,
            config_path=path_value("config_path"),
            scene_usd_path=path_value("scene_usd_path"),
            robot_usd_path=path_value("robot_usd_path") if value.get("robot_usd_path") else default_robot,
            source_path=_path(value, "source_path"),
            destination_path=_path(value, "destination_path"),
            source_control_path=_optional_path(value, "source_control_path"),
            source_label=_text(value, "source_label", "试剂A"),
            destination_label=_text(value, "destination_label", "烧杯"),
            frame_id=_text(value, "frame_id", "lab_camera_front"),
            calibration_ref=_text(value, "calibration_ref", "artifact://labutopia/calibration-v1"),
            scene_revision=_text(value, "scene_revision", "labutopia-scene-v1"),
            observation_ref=_text(value, "observation_ref", "observation://labutopia/initial"),
            capability_snapshot_ref=_text(value, "capability_snapshot_ref", "artifact://labutopia/capabilities-v1"),
            return_destination_ref=_text(value, "return_destination_ref", "destination://labutopia/source-home"),
            container_frame_id=_text(value, "container_frame_id", "container://labutopia/beaker2"),
            tool_tip_frame_id=_text(value, "tool_tip_frame_id", _text(value, "container_frame_id", "container://labutopia/beaker2")),
            max_age_ms=_positive_int(value, "max_age_ms", 1000),
            freshness_ms=_nonnegative_int(value, "freshness_ms", 0),
            tilt_rad=_positive_float(value, "tilt_rad", 0.87),
            hold_s=_positive_float(value, "hold_s", 0.6),
            stir_radius_m=_positive_float(value, "stir_radius_m", 0.009),
            stir_depth_m=_positive_float(value, "stir_depth_m", 0.04),
            stir_turns=_positive_float(value, "stir_turns", 2.0),
            stir_duration_s=_positive_float(value, "stir_duration_s", 4.0),
            stir_direction=_direction(value.get("stir_direction", "ccw")),
            tool_tip_axis_local=_vector3(value, "tool_tip_axis_local", (0.0, 0.0, -1.0)),
            max_angular_step_rad=_positive_float(value, "max_angular_step_rad", 0.5),
            stir_radius_tolerance_m=_positive_float(value, "stir_radius_tolerance_m", 0.002),
            stir_depth_tolerance_m=_positive_float(value, "stir_depth_tolerance_m", 0.005),
            stir_container_radius_m=_positive_float(value, "stir_container_radius_m", 0.05),
            stir_container_depth_m=_positive_float(value, "stir_container_depth_m", 0.08),
            stir_rim_height_m=_positive_float(value, "stir_rim_height_m", 0.04),
            alignment_tolerance_m=_positive_float(value, "alignment_tolerance_m", 0.05),
            tilt_tolerance_rad=_positive_float(value, "tilt_tolerance_rad", 0.10),
            maximum_tilt_rad=_positive_float(value, "maximum_tilt_rad", 1.50),
            max_sample_gap_s=_positive_float(value, "max_sample_gap_s", 0.10),
            gripper_closed_max_m=_positive_float(value, "gripper_closed_max_m", 0.035),
            object_lift_threshold_m=_positive_float(value, "object_lift_threshold_m", 0.04),
            grasp_distance_tolerance_m=_positive_float(value, "grasp_distance_tolerance_m", 0.16),
            source_pour_axis=_vector3(value, "source_pour_axis", (0.0, 0.0, 1.0)),
            configured_process_type=_process_type(value.get("configured_process_type", "pour")),
            supported_operations=_operations(value.get("supported_operations", ("pour_cycle", "stir_cycle", "manipulation_cycle"))),
            headless=bool(value.get("headless", True)),
            camera_render_frames=_positive_int(value, "camera_render_frames", 4),
            motion_config_path=path_value("motion_config_path") if value.get("motion_config_path") else None,
            perception_config_path=path_value("perception_config_path") if value.get("perception_config_path") else None,
            worker_python_path=path_value("worker_python_path") if value.get("worker_python_path") else None,
            physics_scene_path=_text(value, "physics_scene_path", "/physicsScene"),
            physics_dt_s=_positive_float(value, "physics_dt_s", 1 / 60),
            control_dt_s=_positive_float(value, "control_dt_s", 1 / 60),
            startup_settle_s=float(value.get("startup_settle_s", 0.)),
        )
        profile.validate_paths()
        ratio = profile.control_dt_s / profile.physics_dt_s
        if ratio < 1 or not math.isclose(ratio, round(ratio), abs_tol=1e-6):
            raise LabProfileError("control_dt_s must be an integer multiple of physics_dt_s")
        if not math.isfinite(profile.startup_settle_s) or profile.startup_settle_s < 0:
            raise LabProfileError("startup_settle_s must be finite and non-negative")
        if not profile.physics_scene_path.startswith("/"):
            raise LabProfileError("physics_scene_path must be an absolute prim path")
        if profile.tilt_rad + profile.tilt_tolerance_rad > profile.maximum_tilt_rad:
            raise LabProfileError("tilt target exceeds maximum configured tilt")
        if profile.stir_rim_height_m > profile.stir_container_depth_m:
            raise LabProfileError("stir rim height cannot exceed configured container depth")
        return profile

    @classmethod
    def from_json(cls, path: Path) -> "LabUtopiaProfile":
        path = Path(path)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LabProfileError(f"could not load lab profile: {type(exc).__name__}") from exc
        profile = cls.from_mapping(value, base_dir=path.parent)
        object.__setattr__(profile, "profile_path", path.resolve())
        return profile

    def validate_paths(self) -> None:
        for name, path in (("lab_root", self.lab_root), ("config_path", self.config_path), ("scene_usd_path", self.scene_usd_path), ("robot_usd_path", self.robot_usd_path)):
            if not path.exists():
                raise LabProfileError(f"{name} does not exist: {path}")
        if not self.config_path.is_file() or not self.scene_usd_path.is_file():
            raise LabProfileError("config_path and scene_usd_path must be files")
        if self.motion_config_path is not None and not self.motion_config_path.is_file():
            raise LabProfileError(f"motion_config_path does not exist: {self.motion_config_path}")
        if self.perception_config_path is not None and not self.perception_config_path.is_file():
            raise LabProfileError(f"perception_config_path does not exist: {self.perception_config_path}")
        if self.worker_python_path is not None and not self.worker_python_path.is_file():
            raise LabProfileError(f"worker_python_path does not exist: {self.worker_python_path}")
        if not self.source_path.startswith("/World/") or not self.destination_path.startswith("/World/"):
            raise LabProfileError("source_path and destination_path must be absolute /World prim paths")
        if self.source_control_path is not None and not self.source_control_path.startswith("/World/"):
            raise LabProfileError("source_control_path must be an absolute /World prim path")

    def paos_input(
        self,
        previous: Mapping[str, Any] | None = None,
        *,
        operation: str = "pour_cycle",
        perception_binding: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Project the prior PAOS observation/preparation input into the lab scene."""
        if operation not in {"pour_cycle", "stir_cycle", "manipulation_cycle"}:
            raise LabProfileError("unsupported cycle operation")
        if operation not in self.supported_operations:
            raise LabProfileError(f"profile does not support {operation}")
        previous = dict(previous or {})
        if perception_binding is not None and not isinstance(perception_binding, Mapping):
            raise LabProfileError("perception_binding must be a mapping")
        if isinstance(perception_binding, Mapping):
            binding_required = (
                "entity_ref", "destination_ref", "observation_ref", "scene_revision",
                "frame_id", "calibration_ref", "binding_ref", "freshness_ms", "max_age_ms",
            )
            if any(key not in perception_binding for key in binding_required):
                raise LabProfileError("perception_binding provenance is incomplete")
            freshness = perception_binding["freshness_ms"]
            max_age = perception_binding["max_age_ms"]
            if (
                isinstance(freshness, bool) or not isinstance(freshness, int) or freshness < 0
                or isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 1
                or freshness > max_age
            ):
                raise LabProfileError("perception_binding is stale or has invalid freshness")
            for key in binding_required[:7]:
                if not isinstance(perception_binding[key], str) or not perception_binding[key].strip():
                    raise LabProfileError("perception_binding provenance is invalid")
        bound_entity_ref = (
            perception_binding.get("entity_ref")
            if isinstance(perception_binding, Mapping) else None
        )
        bound_destination_ref = (
            perception_binding.get("destination_ref")
            if isinstance(perception_binding, Mapping) else None
        )
        binding_ref = (
            perception_binding.get("binding_ref")
            if isinstance(perception_binding, Mapping) else previous.get("binding_ref")
        )
        bound_observation_ref = (
            perception_binding.get("observation_ref")
            if isinstance(perception_binding, Mapping) else None
        )
        bound_scene_revision = (
            perception_binding.get("scene_revision")
            if isinstance(perception_binding, Mapping) else None
        )
        bound_frame_id = (
            perception_binding.get("frame_id")
            if isinstance(perception_binding, Mapping) else None
        )
        bound_calibration_ref = (
            perception_binding.get("calibration_ref")
            if isinstance(perception_binding, Mapping) else None
        )
        bound_freshness_ms = (
            perception_binding.get("freshness_ms")
            if isinstance(perception_binding, Mapping) else None
        )
        bound_max_age_ms = (
            perception_binding.get("max_age_ms")
            if isinstance(perception_binding, Mapping) else None
        )
        if binding_ref is not None and (
            not isinstance(binding_ref, str) or not binding_ref.startswith("artifact://")
        ):
            raise LabProfileError("binding_ref must use artifact:// scheme")
        required = {
            "entity_ref": bound_entity_ref or _entity_ref(self.source_path),
            "destination_ref": bound_destination_ref or _destination_ref(self.destination_path),
            "return_destination_ref": self.return_destination_ref,
            "observation_ref": bound_observation_ref or self.observation_ref,
            "scene_revision": bound_scene_revision or self.scene_revision,
            "frame_id": bound_frame_id or self.frame_id,
            "calibration_ref": bound_calibration_ref or self.calibration_ref,
            "capability_snapshot_ref": self.capability_snapshot_ref,
            "operation": operation,
            "freshness_ms": bound_freshness_ms if bound_freshness_ms is not None else self.freshness_ms,
            "max_age_ms": bound_max_age_ms if bound_max_age_ms is not None else self.max_age_ms,
        }
        if binding_ref is not None:
            required["binding_ref"] = binding_ref
        if operation == "pour_cycle":
            required["parameters"] = {"tilt_rad": self.tilt_rad, "hold_s": self.hold_s}
        elif operation == "stir_cycle":
            parameters = {
                "radius_m": self.stir_radius_m,
                "depth_m": self.stir_depth_m,
                "turns": self.stir_turns,
                "duration_s": self.stir_duration_s,
                "direction": self.stir_direction,
            }
            parameters.update(dict(previous.get("parameters") or {}))
            required["parameters"] = parameters
            previous["parameters"] = parameters
        elif not previous.get("parameters"):
            raise LabProfileError("manipulation_cycle requires caller-supplied parameters")
        for key, value in required.items():
            if key == "scene_revision" and previous.get(key) not in (None, ""):
                continue
            if key not in previous or previous[key] in (None, ""):
                previous[key] = value
        if perception_binding is None and binding_ref is None and (
            previous["entity_ref"] != required["entity_ref"]
            or previous["destination_ref"] != required["destination_ref"]
        ):
            raise LabProfileError("previous PAOS input targets a different source or destination")
        if not isinstance(previous["scene_revision"], str) or not previous["scene_revision"].strip():
            raise LabProfileError("previous PAOS input requires a live scene revision")
        if perception_binding is None and binding_ref is None and (
            previous["frame_id"] != self.frame_id
            or previous["calibration_ref"] != self.calibration_ref
        ):
            raise LabProfileError("previous PAOS input has stale frame or calibration identity")
        return previous

    def source_profile(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "calibration_ref": self.calibration_ref,
            "container_frame_id": self.container_frame_id,
            "tool_tip_frame_id": self.tool_tip_frame_id,
            "source_pour_axis": list(self.source_pour_axis),
            "source_control_path": self.source_control_path,
            "configured_process_type": self.configured_process_type,
            "source_label": self.source_label,
            "destination_label": self.destination_label,
        }

    def evaluation_profile(self) -> dict[str, Any]:
        return {
            "max_sample_gap_s": self.max_sample_gap_s,
            "alignment_tolerance_m": self.alignment_tolerance_m,
            "tilt_tolerance_rad": self.tilt_tolerance_rad,
            "maximum_tilt_rad": self.maximum_tilt_rad,
            "stir_radius_m": self.stir_radius_m,
            "stir_duration_s": self.stir_duration_s,
            "stir_turns": self.stir_turns,
            "max_angular_step_rad": self.max_angular_step_rad,
            "radius_tolerance_m": self.stir_radius_tolerance_m,
            "depth_tolerance_m": self.stir_depth_tolerance_m,
            "container_radius_m": self.stir_container_radius_m,
            "container_depth_m": self.stir_container_depth_m,
            "stir_rim_height_m": self.stir_rim_height_m,
        }


def _text(value: Mapping[str, Any], key: str, default: str) -> str:
    raw = value.get(key, default)
    if not isinstance(raw, str) or not raw.strip():
        raise LabProfileError(f"{key} must be a non-empty string")
    return raw


def _path(value: Mapping[str, Any], key: str) -> str:
    raw = _text(value, key, "")
    if not raw.startswith("/World/"):
        raise LabProfileError(f"{key} must be an absolute /World prim path")
    return raw


def _optional_path(value: Mapping[str, Any], key: str) -> str | None:
    raw = value.get(key)
    if raw in (None, ""):
        return None
    if not isinstance(raw, str) or not raw.startswith("/World/"):
        raise LabProfileError(f"{key} must be an absolute /World prim path")
    return raw


def _positive_float(value: Mapping[str, Any], key: str, default: float) -> float:
    raw = value.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw <= 0:
        raise LabProfileError(f"{key} must be a positive number")
    return float(raw)


def _positive_int(value: Mapping[str, Any], key: str, default: int) -> int:
    raw = value.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise LabProfileError(f"{key} must be a positive integer")
    return raw


def _nonnegative_int(value: Mapping[str, Any], key: str, default: int) -> int:
    raw = value.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise LabProfileError(f"{key} must be a non-negative integer")
    return raw


def _direction(raw: Any) -> str:
    if raw not in {"cw", "ccw"}:
        raise LabProfileError("stir_direction must be cw or ccw")
    return raw


def _vector3(value: Mapping[str, Any], key: str, default: tuple[float, float, float]) -> tuple[float, float, float]:
    raw = value.get(key, default)
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise LabProfileError(f"{key} must contain three numbers")
    components = tuple(float(item) for item in raw)
    if not all(math.isfinite(item) for item in components):
        raise LabProfileError(f"{key} must contain finite numbers")
    norm = math.sqrt(sum(item * item for item in components))
    if norm <= 0:
        raise LabProfileError(f"{key} must not be zero")
    return tuple(item / norm for item in components)


def _operations(raw: Any) -> tuple[str, ...]:
    allowed = {"pour_cycle", "stir_cycle", "manipulation_cycle"}
    if not isinstance(raw, (list, tuple)) or not raw or any(item not in allowed for item in raw):
        raise LabProfileError("supported_operations must be a non-empty list of known cycle operations")
    return tuple(dict.fromkeys(raw))


def _process_type(raw: Any) -> str:
    allowed = {"pour", "stir", "handle_rotation", "cap_unscrew", "cap_screw"}
    if not isinstance(raw, str) or raw not in allowed:
        raise LabProfileError("configured_process_type must name one supported process type")
    return raw


def _entity_ref(path: str) -> str:
    return f"entity://{path.rsplit('/', 1)[-1]}"


def _destination_ref(path: str) -> str:
    return f"destination://{path.rsplit('/', 1)[-1]}"
