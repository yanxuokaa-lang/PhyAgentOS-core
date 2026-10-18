"""Offline algorithm tests over explicitly synthetic measurement fixtures."""

import math

import pytest

from pick_place_workflow.cycle_protocol import (
    CyclePhaseProtocol,
    CycleProtocolError,
    evaluate_pour_feedback,
    evaluate_stir_feedback,
)

POUR_PARAMETERS = {"tilt_rad": 1.2, "hold_s": 2.0}
POUR_PROFILE = {"max_sample_gap_s": 0.6, "alignment_tolerance_m": 0.01,
                "tilt_tolerance_rad": 0.05, "maximum_tilt_rad": 1.5}
STIR_PARAMETERS = {"radius_m": 0.02, "depth_m": 0.03, "turns": 1.0,
                   "duration_s": 2.0, "direction": "ccw"}
STIR_PROFILE = {"max_sample_gap_s": 0.2, "radius_tolerance_m": 0.002,
                "depth_tolerance_m": 0.002, "container_radius_m": 0.05,
                "container_depth_m": 0.08, "max_angular_step_rad": 0.5}


def synthetic_pour(times, *, aligned=True):
    return [{"timestamp_s": time, "feedback_valid": True, "grasp_valid": True,
             "target_container_aligned": aligned if not isinstance(aligned, dict) else aligned.get(time, True),
             "alignment_error_m": 0.001, "tilt_rad": 1.2} for time in times]


def synthetic_circle(*, direction=1, count=41, reverse=False, gap_at=None, radius=0.02, depth=0.03):
    values = []
    for index in range(count):
        angle_index = index
        if reverse:
            angle_index = index % 4
            angle = (math.pi / 2) * (angle_index if angle_index < 2 else 4 - angle_index)
        else:
            angle = direction * (2 * math.pi * index / (count - 1))
        timestamp = index * 0.1 + (2.0 if gap_at is not None and index >= gap_at else 0.0)
        values.append({"timestamp_s": timestamp, "feedback_valid": True, "grasp_valid": True,
                       "tool_tip_x_m": radius * math.cos(angle), "tool_tip_y_m": radius * math.sin(angle),
                       "tool_tip_depth_m": depth})
    return values


def test_synthetic_pour_requires_all_conditions_in_one_continuous_window():
    trace = synthetic_pour([index * 0.5 for index in range(8)], aligned={1.0: False, 1.5: False})
    result = evaluate_pour_feedback(trace, POUR_PARAMETERS, POUR_PROFILE)
    assert result["qualified_tilt_hold_s"] == pytest.approx(1.5)
    assert result["longest_continuous_hold_s"] == pytest.approx(1.5)
    assert result["process_completed"] is False
    assert result["liquid_amount"] == "unmeasured" and result["transfer_verified"] is False


def test_synthetic_pour_feedback_gap_is_not_counted_as_hold_time():
    trace = synthetic_pour([0.0, 0.5, 1.0, 3.0, 3.5, 4.0])
    result = evaluate_pour_feedback(trace, POUR_PARAMETERS, POUR_PROFILE)
    assert result["longest_continuous_hold_s"] == pytest.approx(1.0)
    assert not result["process_completed"]


def test_synthetic_stir_counts_measured_tip_direction_not_requested_path():
    result = evaluate_stir_feedback(synthetic_circle(direction=1), STIR_PARAMETERS, STIR_PROFILE)
    assert result["in_container_turns"] == pytest.approx(1.0)
    assert result["process_completed"]
    assert result["mixing_quality"] == "unmeasured" and result["homogeneous"] is False
    reversed_result = evaluate_stir_feedback(synthetic_circle(direction=-1), STIR_PARAMETERS, STIR_PROFILE)
    assert reversed_result["in_container_turns"] == pytest.approx(0.0)
    assert not reversed_result["process_completed"]


def test_synthetic_stir_rocking_sampling_gap_and_outside_region_do_not_qualify():
    rocking = evaluate_stir_feedback(synthetic_circle(reverse=True, count=41), STIR_PARAMETERS, STIR_PROFILE)
    assert rocking["in_container_turns"] < 1.0 and not rocking["process_completed"]
    interrupted = evaluate_stir_feedback(synthetic_circle(gap_at=20), STIR_PARAMETERS, STIR_PROFILE)
    assert interrupted["in_container_turns"] < 1.0 and not interrupted["process_completed"]
    outside = evaluate_stir_feedback(synthetic_circle(radius=0.035), STIR_PARAMETERS, STIR_PROFILE)
    assert outside["valid_sample_count"] == 0 and not outside["process_completed"]


def test_synthetic_stir_does_not_combine_duration_and_turns_across_a_gap():
    trace = []
    for index in range(31):
        angle = math.pi * index / 30
        trace.append({"timestamp_s": index * 0.05, "feedback_valid": True, "grasp_valid": True,
                      "tool_tip_x_m": 0.02 * math.cos(angle), "tool_tip_y_m": 0.02 * math.sin(angle),
                      "tool_tip_depth_m": 0.03})
    for index in range(13):
        angle = math.pi + math.pi * index / 12
        trace.append({"timestamp_s": 3.5 + index * 0.05, "feedback_valid": True, "grasp_valid": True,
                      "tool_tip_x_m": 0.02 * math.cos(angle), "tool_tip_y_m": 0.02 * math.sin(angle),
                      "tool_tip_depth_m": 0.03})

    result = evaluate_stir_feedback(trace, STIR_PARAMETERS, STIR_PROFILE)

    assert result["longest_directional_turns"] == pytest.approx(0.5)
    assert result["in_container_duration_s"] == pytest.approx(1.5)
    assert result["process_completed"] is False


def test_synthetic_stir_rejects_angular_aliasing_above_profile_sample_bound():
    sparse = synthetic_circle(count=5)
    result = evaluate_stir_feedback(sparse, STIR_PARAMETERS, STIR_PROFILE)
    assert result["in_container_turns"] == 0.0 and not result["process_completed"]


def test_phase_protocol_requires_ordered_observable_facts_and_keeps_partial_failure():
    protocol = CyclePhaseProtocol()
    result = protocol.consume([
        {"phase": "acquire", "status": "completed", "outcome_known": True,
         "started_at_s": 0.0, "completed_at_s": 1.0,
         "facts": {"grasp_confirmed": True, "possession_state": "holding"}},
        {"phase": "transport", "status": "completed", "outcome_known": True,
         "started_at_s": 1.0, "completed_at_s": 2.0,
         "facts": {"route_completed": True, "possession_state": "holding"}},
        {"phase": "process", "status": "completed", "outcome_known": True,
         "started_at_s": 2.0, "completed_at_s": 3.0,
         "facts": {"process_measurement_qualified": True, "possession_state": "holding"}},
        {"phase": "reorient_exit", "status": "completed", "outcome_known": True,
         "started_at_s": 3.0, "completed_at_s": 4.0,
         "facts": {"tool_reoriented_or_exited": True, "possession_state": "holding"}},
        {"phase": "stow", "status": "failed", "outcome_known": True,
         "started_at_s": 4.0, "completed_at_s": 5.0,
         "facts": {"failure_code": "return_location_unavailable"}},
    ])
    assert result["process_completed"] and not result["return_completed"]
    assert result["failed_phase"] == "stow" and result["outcome_known"]
    assert result["completed_phases"] == ["acquire", "transport", "process", "reorient_exit"]


def test_phase_protocol_rejects_out_of_order_or_unconfirmed_completion():
    assert CyclePhaseProtocol().consume([])["outcome_known"] is False
    with pytest.raises(CycleProtocolError, match="out of order"):
        CyclePhaseProtocol().consume([{"phase": "process", "status": "completed", "outcome_known": True,
                                       "started_at_s": 0, "completed_at_s": 1, "facts": {}}])
    with pytest.raises(CycleProtocolError, match="observable completion facts"):
        CyclePhaseProtocol().consume([{"phase": "acquire", "status": "completed", "outcome_known": True,
                                       "started_at_s": 0, "completed_at_s": 1, "facts": {}}])


def test_synthetic_grasp_failure_stops_before_transport_and_process():
    result = CyclePhaseProtocol().consume([{
        "phase": "acquire", "status": "failed", "outcome_known": True,
        "started_at_s": 0.0, "completed_at_s": 0.4,
        "facts": {"failure_code": "grasp_not_confirmed", "possession_state": "empty"},
    }])
    assert result["failed_phase"] == "acquire"
    assert result["completed_phases"] == [] and not result["process_completed"]
