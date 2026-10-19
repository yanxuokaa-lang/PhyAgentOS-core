"""Normalize provider observations before cycle feedback evaluation.

The adapter is deliberately provider-neutral. A deployment supplies a source
profile and raw observations; this module validates provenance and projects
only the fields consumed by :mod:`cycle_protocol`. It does not transform
coordinates, run kinematics, read sensors, or infer physical success.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class FeedbackAdapterError(ValueError):
    """The requested operation or source profile cannot be normalized."""


@dataclass(frozen=True)
class FeedbackNormalization:
    """Result of one provider observation stream normalization."""

    operation: str
    status: str
    samples: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]
    source_profile: dict[str, Any]
    evaluation_profile: dict[str, Any]

    @property
    def valid(self) -> bool:
        return self.status == "valid"


_OPERATIONS = {"pour_cycle", "stir_cycle", "manipulation_cycle"}
_HOLDING_STATES = {"holding", "grasped", "secured", "closed"}
_EMPTY_STATES = {"empty", "released", "lost", "open"}


@dataclass(frozen=True)
class FeedbackAdapter:
    """Bound adapter configuration for one cycle operation and deployment."""

    operation: str
    source_profile: Mapping[str, Any]
    evaluation_profile: Mapping[str, Any]

    def normalize(self, observations: Sequence[Mapping[str, Any]]) -> FeedbackNormalization:
        return normalize_feedback(
            self.operation,
            observations,
            source_profile=self.source_profile,
            evaluation_profile=self.evaluation_profile,
        )


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _append_error(errors: list[str], code: str) -> None:
    if code not in errors:
        errors.append(code)


def _grasp_valid(observation: Mapping[str, Any]) -> tuple[bool | None, str | None]:
    """Map explicit deployment grasp states without treating absence as success."""

    value = observation.get("grasp_valid")
    if isinstance(value, bool):
        return value, None
    state = observation.get("grasp_state")
    if isinstance(state, Mapping):
        state = state.get("state")
    if isinstance(state, str):
        normalized = state.strip().lower()
        if normalized in _HOLDING_STATES:
            return True, None
        if normalized in _EMPTY_STATES:
            return False, None
        if normalized in {"unknown", "uncertain", "invalid"}:
            return None, "grasp_state_unknown"
    if value is None and state is None:
        return None, "missing_grasp_feedback"
    return None, "invalid_grasp_feedback"


def _tip_coordinates(observation: Mapping[str, Any]) -> tuple[Any, Any, Any, Any]:
    tip = observation.get("tool_tip")
    if isinstance(tip, Mapping):
        return tip.get("x_m"), tip.get("y_m"), tip.get("depth_m"), tip.get("frame_id")
    return (
        observation.get("tool_tip_x_m"),
        observation.get("tool_tip_y_m"),
        observation.get("tool_tip_depth_m"),
        observation.get("tool_tip_frame_id"),
    )


def _profile_error(operation: str, profile: Mapping[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(profile, Mapping):
        return {}, ["missing_source_profile"]
    normalized = dict(profile)
    errors: list[str] = []
    for key in ("frame_id", "calibration_ref", "container_frame_id"):
        if not _text(normalized.get(key)):
            _append_error(errors, f"missing_source_{key}")
    if operation == "stir_cycle" and not _text(normalized.get("tool_tip_frame_id")):
        _append_error(errors, "missing_source_tool_tip_frame_id")
    return normalized, errors


def normalize_feedback(
    operation: str,
    observations: Sequence[Mapping[str, Any]],
    *,
    source_profile: Mapping[str, Any] | None,
    evaluation_profile: Mapping[str, Any],
    expected_source_profile: Mapping[str, Any] | None = None,
) -> FeedbackNormalization:
    """Normalize one raw observation stream for the existing cycle calculator.

    Structural errors make the whole stream invalid and force every projected
    sample to ``feedback_valid=False``. This prevents a valid-looking prefix
    from qualifying a cycle after a frame, calibration, timestamp, or grasp
    provenance failure. A provider-reported ``feedback_valid=False`` is a
    legitimate observation gap and remains usable as a non-qualifying sample.
    """

    if operation not in _OPERATIONS:
        raise FeedbackAdapterError(f"unsupported feedback operation: {operation}")
    profile, errors = _profile_error(operation, source_profile)
    if isinstance(expected_source_profile, Mapping):
        for key in ("frame_id", "calibration_ref"):
            expected = expected_source_profile.get(key)
            if _text(expected) and profile.get(key) != expected:
                _append_error(errors, f"source_profile_{key}_mismatch")
    if not isinstance(evaluation_profile, Mapping):
        _append_error(errors, "missing_evaluation_profile")
        normalized_evaluation_profile: dict[str, Any] = {}
    else:
        normalized_evaluation_profile = dict(evaluation_profile)
    if not _finite(normalized_evaluation_profile.get("max_sample_gap_s")):
        _append_error(errors, "missing_sampling_profile_max_sample_gap_s")
    elif float(normalized_evaluation_profile["max_sample_gap_s"]) <= 0:
        _append_error(errors, "invalid_sampling_profile_max_sample_gap_s")

    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        observations = ()
        _append_error(errors, "observations_not_a_sequence")
    if not observations:
        return FeedbackNormalization(
            operation=operation,
            status="unknown",
            samples=(),
            errors=tuple(errors or ["no_feedback_observations"]),
            source_profile=profile,
            evaluation_profile=normalized_evaluation_profile,
        )

    projected: list[dict[str, Any]] = []
    previous_timestamp: float | None = None
    for observation in observations:
        if not isinstance(observation, Mapping):
            _append_error(errors, "observation_not_a_mapping")
            continue
        timestamp = observation.get("timestamp_s")
        timestamp_valid = _finite(timestamp)
        if not timestamp_valid:
            _append_error(errors, "invalid_timestamp")
            timestamp_value = 0.0 if previous_timestamp is None else previous_timestamp
        else:
            timestamp_value = float(timestamp)
            if previous_timestamp is not None and timestamp_value <= previous_timestamp:
                _append_error(errors, "timestamp_not_monotonic")
            previous_timestamp = timestamp_value

        sample: dict[str, Any] = {
            "timestamp_s": timestamp_value,
            "feedback_valid": False,
            "frame_id": profile.get("frame_id"),
            "calibration_ref": profile.get("calibration_ref"),
            "container_frame_id": profile.get("container_frame_id"),
        }
        if observation.get("frame_id") != profile.get("frame_id"):
            _append_error(errors, "frame_mismatch" if observation.get("frame_id") is not None else "missing_frame_id")
        if observation.get("calibration_ref") != profile.get("calibration_ref"):
            _append_error(
                errors,
                "calibration_mismatch" if observation.get("calibration_ref") is not None else "missing_calibration_ref",
            )
        if observation.get("container_frame_id") != profile.get("container_frame_id"):
            _append_error(
                errors,
                "container_frame_mismatch"
                if observation.get("container_frame_id") is not None
                else "missing_container_frame_id",
            )

        grasp, grasp_error = _grasp_valid(observation)
        if grasp_error:
            _append_error(errors, grasp_error)
        sample["grasp_valid"] = grasp is True

        feedback_valid = observation.get("feedback_valid")
        if not isinstance(feedback_valid, bool):
            _append_error(errors, "missing_feedback_valid")
        sample["feedback_valid"] = feedback_valid is True

        if operation == "pour_cycle":
            aligned = observation.get("target_container_aligned")
            alignment_error = observation.get("alignment_error_m")
            tilt = observation.get("tilt_rad")
            if not isinstance(aligned, bool):
                _append_error(errors, "missing_container_alignment")
            if not _finite(alignment_error):
                _append_error(errors, "missing_alignment_error")
            if not _finite(tilt):
                _append_error(errors, "missing_tilt")
            sample.update(
                target_container_aligned=aligned is True,
                alignment_error_m=float(alignment_error) if _finite(alignment_error) else 0.0,
                tilt_rad=float(tilt) if _finite(tilt) else 0.0,
            )
        elif operation == "stir_cycle":
            x, y, depth, tip_frame = _tip_coordinates(observation)
            if tip_frame != profile.get("tool_tip_frame_id"):
                _append_error(
                    errors,
                    "tool_tip_frame_mismatch" if tip_frame is not None else "missing_tool_tip_frame_id",
                )
            if not _finite(x) or not _finite(y) or not _finite(depth):
                _append_error(errors, "missing_tool_tip_coordinates")
            sample.update(
                tool_tip_x_m=float(x) if _finite(x) else 0.0,
                tool_tip_y_m=float(y) if _finite(y) else 0.0,
                tool_tip_depth_m=float(depth) if _finite(depth) else 0.0,
                tool_tip_frame_id=tip_frame,
            )
        else:
            progress = observation.get("transform_progress")
            error = observation.get("transform_error")
            engaged = observation.get("engagement_valid")
            if not _finite(progress):
                _append_error(errors, "missing_transform_progress")
            if not _finite(error):
                _append_error(errors, "missing_transform_error")
            if not isinstance(engaged, bool):
                _append_error(errors, "missing_engagement_valid")
            sample.update(
                transform_progress=float(progress) if _finite(progress) else 0.0,
                transform_error=float(error) if _finite(error) else 0.0,
                engagement_valid=engaged is True,
            )
        projected.append(sample)

    if errors:
        projected = [
            {**sample, "feedback_valid": False, "grasp_valid": False} for sample in projected
        ]
        status = "invalid"
    else:
        status = "valid"
    return FeedbackNormalization(
        operation=operation,
        status=status,
        samples=tuple(projected),
        errors=tuple(errors),
        source_profile=profile,
        evaluation_profile=normalized_evaluation_profile,
    )


__all__ = ["FeedbackAdapter", "FeedbackAdapterError", "FeedbackNormalization", "normalize_feedback"]
