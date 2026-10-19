"""Provider-neutral feedback evaluation and phase facts for composite cycles.

This module consumes measurements and lifecycle events only. It does not issue
commands, access devices, or infer that a requested motion actually occurred.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


class CycleProtocolError(ValueError):
    pass


PHASES = (
    "acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat",
)


@dataclass
class CyclePhaseProtocol:
    """Settle an ordered phase-event stream into observable phase facts."""

    phase_facts: dict[str, dict[str, Any]] = field(default_factory=dict)
    failed_phase: str | None = None
    outcome_known: bool = True
    last_completed_at_s: float | None = None

    def consume(self, events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not events:
            self.outcome_known = False
        for event in events:
            self._consume_one(event)
        completed = [phase for phase in PHASES if self.phase_facts.get(phase, {}).get("completed") is True]
        return {
            "phase_facts": {phase: dict(fact) for phase, fact in self.phase_facts.items()},
            "completed_phases": completed,
            "failed_phase": self.failed_phase,
            "outcome_known": self.outcome_known,
            "process_completed": (self.phase_facts.get("process", {}).get("completed") is True
                                  and self.phase_facts.get("process", {}).get("facts", {}).get(
                                      "process_measurement_qualified") is True),
            "return_completed": all(self.phase_facts.get(phase, {}).get("completed") is True
                                     for phase in ("reorient_exit", "stow", "release", "retreat")),
        }

    def _consume_one(self, event: Mapping[str, Any]) -> None:
        if not isinstance(event, Mapping):
            raise CycleProtocolError("cycle phase event must be a mapping")
        phase, status = event.get("phase"), event.get("status")
        if phase not in PHASES or status not in {"completed", "failed", "unknown"}:
            raise CycleProtocolError("cycle phase event has an invalid phase or status")
        if self.failed_phase is not None or not self.outcome_known:
            raise CycleProtocolError("cycle phase event follows a terminal or unknown phase")
        expected = len(self.phase_facts)
        if expected >= len(PHASES) or phase != PHASES[expected]:
            raise CycleProtocolError(f"cycle phase out of order: expected {PHASES[min(expected, len(PHASES)-1)]}")
        facts = event.get("facts", {})
        if not isinstance(facts, Mapping):
            raise CycleProtocolError("cycle phase facts must be a mapping")
        started = event.get("started_at_s")
        ended = event.get("completed_at_s")
        if not _finite(started) or (self.last_completed_at_s is not None and started < self.last_completed_at_s):
            raise CycleProtocolError("cycle phase timestamps must be monotonic")
        if status != "unknown" and (not _finite(ended) or ended <= started):
            raise CycleProtocolError("settled cycle phase requires a positive observed interval")
        if ended is not None and (not _finite(ended) or ended < started):
            raise CycleProtocolError("cycle phase completion time precedes its start")
        if status == "unknown" or event.get("outcome_known") is not True:
            self.phase_facts[phase] = {"completed": False, "status": "unknown", "facts": dict(facts),
                                       "started_at_s": float(started), "completed_at_s": ended}
            self.failed_phase, self.outcome_known = phase, False
            return
        if status == "failed":
            self.phase_facts[phase] = {"completed": False, "status": "failed", "facts": dict(facts),
                                       "started_at_s": float(started), "completed_at_s": float(ended)}
            self.failed_phase = phase
            self.last_completed_at_s = float(ended)
            return
        required = {
            "acquire": {"grasp_confirmed": True, "possession_state": "holding"},
            "transport": {"route_completed": True, "possession_state": "holding"},
            "process": {"possession_state": "holding"},
            "reorient_exit": {"tool_reoriented_or_exited": True, "possession_state": "holding"},
            "stow": {"object_support_state": "on_support"},
            "release": {"release_confirmed": True, "possession_state": "empty"},
            "retreat": {"retreat_completed": True, "clear_of_target": True, "observation_ready": True},
        }[phase]
        if any(facts.get(key) != value for key, value in required.items()):
            raise CycleProtocolError(f"cycle phase lacks observable completion facts: {phase}")
        if phase == "process" and not isinstance(facts.get("process_measurement_qualified"), bool):
            raise CycleProtocolError("cycle process phase lacks a measured qualification result")
        self.phase_facts[phase] = {"completed": True, "status": "completed", "facts": dict(facts),
                                   "started_at_s": float(started), "completed_at_s": float(ended)}
        self.last_completed_at_s = float(ended)


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _profile_value(profile: Mapping[str, Any], key: str) -> float:
    value = profile.get(key)
    if not _finite(value) or value < 0:
        raise CycleProtocolError(f"cycle evaluation profile requires finite non-negative {key}")
    return float(value)


def _positive_profile_value(profile: Mapping[str, Any], key: str) -> float:
    value = _profile_value(profile, key)
    if value <= 0:
        raise CycleProtocolError(f"cycle evaluation profile requires positive {key}")
    return value


def _samples(samples: Sequence[Mapping[str, Any]], max_gap_s: float) -> list[Mapping[str, Any]]:
    if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes)) or len(samples) < 2:
        return []
    result = []
    previous = None
    for sample in samples:
        if not isinstance(sample, Mapping) or not _finite(sample.get("timestamp_s")):
            return []
        timestamp = float(sample["timestamp_s"])
        if previous is not None and (timestamp <= previous or timestamp - previous > max_gap_s):
            # A gap splits the valid interval; callers never bridge it.
            sample = {**sample, "_discontinuity": True}
        result.append(sample)
        previous = timestamp
    return result


def evaluate_pour_feedback(samples: Sequence[Mapping[str, Any]], parameters: Mapping[str, Any],
                           profile: Mapping[str, Any]) -> dict[str, Any]:
    """Measure qualified hold seconds only across jointly valid adjacent samples."""
    max_gap = _positive_profile_value(profile, "max_sample_gap_s")
    alignment_tolerance = _profile_value(profile, "alignment_tolerance_m")
    tilt_tolerance = _profile_value(profile, "tilt_tolerance_rad")
    max_tilt = _profile_value(profile, "maximum_tilt_rad")
    target, required = float(parameters["tilt_rad"]), float(parameters["hold_s"])
    longest = 0.0
    run = 0.0
    previous = None
    valid_samples = 0
    for sample in _samples(samples, max_gap):
        timestamp = float(sample["timestamp_s"])
        valid = (
            sample.get("feedback_valid") is True and sample.get("grasp_valid") is True
            and _finite(sample.get("alignment_error_m"))
            and abs(float(sample["alignment_error_m"])) <= alignment_tolerance
            and _finite(sample.get("tilt_rad"))
            and abs(float(sample["tilt_rad"]) - target) <= tilt_tolerance
            and abs(float(sample["tilt_rad"])) <= max_tilt
            and sample.get("target_container_aligned") is True
        )
        if valid:
            valid_samples += 1
        delta = timestamp - float(previous["timestamp_s"]) if previous else 0.0
        continuous = (previous is not None and valid and previous.get("_qualified") is True
                      and not sample.get("_discontinuity") and delta <= max_gap)
        if continuous:
            run += delta
        else:
            run = 0.0
        longest = max(longest, run)
        previous = {**sample, "_qualified": valid}
    return {"qualified_tilt_hold_s": longest, "longest_continuous_hold_s": longest,
            "valid_sample_count": valid_samples, "process_completed": longest >= required,
            "result_meaning": "motion_goal_reached" if longest >= required else "motion_goal_not_reached",
            "liquid_amount": "unmeasured", "transfer_verified": False}


def evaluate_stir_feedback(samples: Sequence[Mapping[str, Any]], parameters: Mapping[str, Any],
                           profile: Mapping[str, Any]) -> dict[str, Any]:
    """Measure requested-direction turns from continuous tool-tip samples."""
    max_gap = _positive_profile_value(profile, "max_sample_gap_s")
    max_angular_step = _positive_profile_value(profile, "max_angular_step_rad")
    radius_tol = _profile_value(profile, "radius_tolerance_m")
    depth_tol = _profile_value(profile, "depth_tolerance_m")
    container_radius = _positive_profile_value(profile, "container_radius_m")
    container_depth = _positive_profile_value(profile, "container_depth_m")
    target_radius = float(parameters["radius_m"])
    target_depth = float(parameters["depth_m"])
    requested_turns = float(parameters["turns"])
    requested_duration = float(parameters["duration_s"])
    direction = 1.0 if parameters["direction"] == "ccw" else -1.0
    if target_radius + radius_tol > container_radius or target_depth + depth_tol > container_depth:
        raise CycleProtocolError("stir target is outside the configured container region")
    turns = 0.0
    valid_count = 0
    previous = None
    previous_angle = None
    run_turns = 0.0
    run_duration = 0.0
    longest_turns = 0.0
    longest_duration = 0.0
    process_completed = False
    for sample in _samples(samples, max_gap):
        coordinates = (sample.get("tool_tip_x_m"), sample.get("tool_tip_y_m"), sample.get("tool_tip_depth_m"))
        valid = (sample.get("feedback_valid") is True and sample.get("grasp_valid") is True
                 and all(_finite(value) for value in coordinates))
        if valid:
            x, y, depth = map(float, coordinates)
            radius = math.hypot(x, y)
            valid = (abs(radius - target_radius) <= radius_tol
                     and abs(depth - target_depth) <= depth_tol
                     and radius <= container_radius and 0 <= depth <= container_depth)
        if valid:
            valid_count += 1
        timestamp = float(sample["timestamp_s"])
        delta_t = timestamp - float(previous["timestamp_s"]) if previous else 0.0
        continuous = (valid and previous is not None and previous.get("_qualified") is True
                      and not sample.get("_discontinuity") and delta_t <= max_gap)
        if continuous:
            angle = math.atan2(float(sample["tool_tip_y_m"]), float(sample["tool_tip_x_m"]))
            delta_angle = (angle - float(previous_angle) + math.pi) % (2 * math.pi) - math.pi
            signed = direction * delta_angle
            if abs(delta_angle) > max_angular_step:
                run_turns = 0.0
                run_duration = 0.0
            elif signed > 0:
                turns += signed / (2 * math.pi)
                run_turns += signed / (2 * math.pi)
            elif signed < 0:
                run_turns = 0.0
                run_duration = 0.0
            if abs(delta_angle) <= max_angular_step and signed >= 0:
                run_duration += delta_t
                longest_turns = max(longest_turns, run_turns)
                longest_duration = max(longest_duration, run_duration)
                process_completed = process_completed or (
                    run_turns >= requested_turns and run_duration >= requested_duration
                )
        else:
            run_turns = 0.0
            run_duration = 0.0
        previous_angle = math.atan2(float(sample["tool_tip_y_m"]), float(sample["tool_tip_x_m"])) if valid else None
        previous = {**sample, "_qualified": valid}
    completed = process_completed
    return {"in_container_turns": longest_turns, "in_container_duration_s": longest_duration,
            "longest_directional_turns": longest_turns, "valid_sample_count": valid_count,
            "process_completed": completed,
            "result_meaning": "motion_goal_reached" if completed else "motion_goal_not_reached",
            "mixing_quality": "unmeasured", "homogeneous": False}


def evaluate_manipulation_feedback(samples: Sequence[Mapping[str, Any]], parameters: Mapping[str, Any],
                                   profile: Mapping[str, Any]) -> dict[str, Any]:
    """Qualify a generic transform from measured progress and engagement.

    Providers report progress in the requested transform's signed direction;
    this keeps rotation and translation semantics independent of a particular
    object or LabUtopia task controller.
    """
    max_gap = _positive_profile_value(profile, "max_sample_gap_s")
    progress_tolerance = _profile_value(profile, "transform_tolerance")
    target = float(parameters["transform"]["magnitude"])
    required_hold = float(parameters["hold_s"])
    longest = 0.0
    run = 0.0
    valid_count = 0
    previous = None
    for sample in _samples(samples, max_gap):
        progress = sample.get("transform_progress")
        error = sample.get("transform_error")
        valid = (
            sample.get("feedback_valid") is True
            and sample.get("grasp_valid") is True
            and sample.get("engagement_valid") is True
            and _finite(progress) and _finite(error)
            and float(progress) >= target - progress_tolerance
            and abs(float(error)) <= progress_tolerance
        )
        valid_count += int(valid)
        timestamp = float(sample["timestamp_s"])
        delta = timestamp - float(previous["timestamp_s"]) if previous else 0.0
        continuous = valid and previous is not None and previous.get("_qualified") is True \
            and not sample.get("_discontinuity") and delta <= max_gap
        run = run + delta if continuous else 0.0
        longest = max(longest, run)
        previous = {**sample, "_qualified": valid}
    completed = longest >= required_hold
    return {
        "transform_progress": target if completed else None,
        "transform_hold_s": longest,
        "valid_sample_count": valid_count,
        "process_completed": completed,
        "result_meaning": "motion_goal_reached" if completed else "motion_goal_not_reached",
    }


def evaluate_process_feedback(operation: str, samples: Sequence[Mapping[str, Any]],
                              parameters: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    if operation == "pour_cycle":
        return evaluate_pour_feedback(samples, parameters, profile)
    if operation == "stir_cycle":
        return evaluate_stir_feedback(samples, parameters, profile)
    if operation == "manipulation_cycle":
        return evaluate_manipulation_feedback(samples, parameters, profile)
    raise CycleProtocolError(f"unsupported cycle operation: {operation}")
