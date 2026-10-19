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
    profile_path: Path | None = None
    frame_id: str = "lab_camera_front"
    calibration_ref: str = "artifact://labutopia/calibration-v1"
    scene_revision: str = "labutopia-scene-v1"
    observation_ref: str = "observation://labutopia/initial"
    capability_snapshot_ref: str = "artifact://labutopia/capabilities-v1"
    return_destination_ref: str = "destination://labutopia/source-home"
    container_frame_id: str = "container://labutopia/beaker2"
    max_age_ms: int = 1000
    freshness_ms: int = 0
    tilt_rad: float = 0.87
    hold_s: float = 0.6
    alignment_tolerance_m: float = 0.05
    tilt_tolerance_rad: float = 0.10
    maximum_tilt_rad: float = 1.50
    max_sample_gap_s: float = 0.10
    gripper_closed_max_m: float = 0.035
    object_lift_threshold_m: float = 0.04
    grasp_distance_tolerance_m: float = 0.16
    source_pour_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    supported_operations: tuple[str, ...] = ("pour_cycle", "stir_cycle")
    headless: bool = True

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
            frame_id=_text(value, "frame_id", "lab_camera_front"),
            calibration_ref=_text(value, "calibration_ref", "artifact://labutopia/calibration-v1"),
            scene_revision=_text(value, "scene_revision", "labutopia-scene-v1"),
            observation_ref=_text(value, "observation_ref", "observation://labutopia/initial"),
            capability_snapshot_ref=_text(value, "capability_snapshot_ref", "artifact://labutopia/capabilities-v1"),
            return_destination_ref=_text(value, "return_destination_ref", "destination://labutopia/source-home"),
            container_frame_id=_text(value, "container_frame_id", "container://labutopia/beaker2"),
            max_age_ms=_positive_int(value, "max_age_ms", 1000),
            freshness_ms=_nonnegative_int(value, "freshness_ms", 0),
            tilt_rad=_positive_float(value, "tilt_rad", 0.87),
            hold_s=_positive_float(value, "hold_s", 0.6),
            alignment_tolerance_m=_positive_float(value, "alignment_tolerance_m", 0.05),
            tilt_tolerance_rad=_positive_float(value, "tilt_tolerance_rad", 0.10),
            maximum_tilt_rad=_positive_float(value, "maximum_tilt_rad", 1.50),
            max_sample_gap_s=_positive_float(value, "max_sample_gap_s", 0.10),
            gripper_closed_max_m=_positive_float(value, "gripper_closed_max_m", 0.035),
            object_lift_threshold_m=_positive_float(value, "object_lift_threshold_m", 0.04),
            grasp_distance_tolerance_m=_positive_float(value, "grasp_distance_tolerance_m", 0.16),
            source_pour_axis=_vector3(value, "source_pour_axis", (0.0, 0.0, 1.0)),
            supported_operations=_operations(value.get("supported_operations", ("pour_cycle", "stir_cycle"))),
            headless=bool(value.get("headless", True)),
        )
        profile.validate_paths()
        if profile.tilt_rad + profile.tilt_tolerance_rad > profile.maximum_tilt_rad:
            raise LabProfileError("tilt target exceeds maximum configured tilt")
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
        if not self.source_path.startswith("/World/") or not self.destination_path.startswith("/World/"):
            raise LabProfileError("source_path and destination_path must be absolute /World prim paths")

    def paos_input(self, previous: Mapping[str, Any] | None = None, *, operation: str = "pour_cycle") -> dict[str, Any]:
        """Project the prior PAOS observation/preparation input into the lab scene."""
        if operation not in {"pour_cycle", "stir_cycle", "manipulation_cycle"}:
            raise LabProfileError("unsupported cycle operation")
        if operation not in self.supported_operations:
            raise LabProfileError(f"profile does not support {operation}")
        previous = dict(previous or {})
        required = {
            "entity_ref": _entity_ref(self.source_path),
            "destination_ref": _destination_ref(self.destination_path),
            "return_destination_ref": self.return_destination_ref,
            "observation_ref": self.observation_ref,
            "scene_revision": self.scene_revision,
            "frame_id": self.frame_id,
            "calibration_ref": self.calibration_ref,
            "capability_snapshot_ref": self.capability_snapshot_ref,
            "operation": operation,
            "freshness_ms": self.freshness_ms,
            "max_age_ms": self.max_age_ms,
        }
        if operation == "pour_cycle":
            required["parameters"] = {"tilt_rad": self.tilt_rad, "hold_s": self.hold_s}
        elif operation == "stir_cycle":
            required["parameters"] = dict(previous.get("parameters") or {})
        elif not previous.get("parameters"):
            raise LabProfileError("manipulation_cycle requires caller-supplied parameters")
        for key, value in required.items():
            if key not in previous or previous[key] in (None, ""):
                previous[key] = value
        if previous["entity_ref"] != required["entity_ref"] or previous["destination_ref"] != required["destination_ref"]:
            raise LabProfileError("previous PAOS input targets a different source or destination")
        if previous["frame_id"] != self.frame_id or previous["calibration_ref"] != self.calibration_ref:
            raise LabProfileError("previous PAOS input has stale frame or calibration identity")
        return previous

    def source_profile(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "calibration_ref": self.calibration_ref,
            "container_frame_id": self.container_frame_id,
            "source_pour_axis": list(self.source_pour_axis),
        }

    def evaluation_profile(self) -> dict[str, Any]:
        return {
            "max_sample_gap_s": self.max_sample_gap_s,
            "alignment_tolerance_m": self.alignment_tolerance_m,
            "tilt_tolerance_rad": self.tilt_tolerance_rad,
            "maximum_tilt_rad": self.maximum_tilt_rad,
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


def _entity_ref(path: str) -> str:
    return f"entity://{path.rsplit('/', 1)[-1]}"


def _destination_ref(path: str) -> str:
    return f"destination://{path.rsplit('/', 1)[-1]}"
