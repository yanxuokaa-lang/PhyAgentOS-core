"""No-motion synthetic records for provider feedback normalization."""

import math

from pick_place_workflow.cycle_protocol import evaluate_process_feedback
from pick_place_workflow.feedback_adapter import normalize_feedback

POUR_SOURCE = {
    "frame_id": "camera_front",
    "calibration_ref": "calibration://front/v3",
    "container_frame_id": "container://beaker",
}
POUR_PROFILE = {
    "max_sample_gap_s": 0.6,
    "alignment_tolerance_m": 0.01,
    "tilt_tolerance_rad": 0.05,
    "maximum_tilt_rad": 1.5,
}
STIR_SOURCE = {
    **POUR_SOURCE,
    "tool_tip_frame_id": "tool://stirrer-tip",
}
STIR_PROFILE = {
    "max_sample_gap_s": 0.2,
    "radius_tolerance_m": 0.002,
    "depth_tolerance_m": 0.002,
    "container_radius_m": 0.05,
    "container_depth_m": 0.08,
    "max_angular_step_rad": 0.5,
}


def pour_observations(*, feedback_valid=True, **changes):
    values = []
    for index in range(7):
        values.append({
            "timestamp_s": index * 0.5,
            "frame_id": "camera_front",
            "calibration_ref": "calibration://front/v3",
            "container_frame_id": "container://beaker",
            "grasp_state": "holding",
            "feedback_valid": feedback_valid,
            "target_container_aligned": True,
            "alignment_error_m": 0.001,
            "tilt_rad": 1.2,
        })
    values[0].update(changes)
    return values


def stir_observations():
    return [
        {
            "timestamp_s": index * 0.05,
            "frame_id": "camera_front",
            "calibration_ref": "calibration://front/v3",
            "container_frame_id": "container://beaker",
            "tool_tip": {
                "frame_id": "tool://stirrer-tip",
                "x_m": 0.02 * math.cos(2 * math.pi * index / 40),
                "y_m": 0.02 * math.sin(2 * math.pi * index / 40),
                "depth_m": 0.03,
            },
            "grasp_valid": True,
            "feedback_valid": True,
        }
        for index in range(41)
    ]


def test_valid_pour_normalization_is_consumable_by_existing_calculator():
    normalized = normalize_feedback(
        "pour_cycle", pour_observations(), source_profile=POUR_SOURCE,
        evaluation_profile=POUR_PROFILE,
    )
    assert normalized.status == "valid"
    assert normalized.samples[0]["grasp_valid"] is True
    assert normalized.samples[0]["frame_id"] == POUR_SOURCE["frame_id"]
    assert normalized.samples[0]["calibration_ref"] == POUR_SOURCE["calibration_ref"]
    result = evaluate_process_feedback(
        "pour_cycle", normalized.samples, {"tilt_rad": 1.2, "hold_s": 2.0},
        normalized.evaluation_profile,
    )
    assert result["process_completed"] is True


def test_valid_stir_normalization_preserves_tip_frame_and_directional_trajectory():
    normalized = normalize_feedback(
        "stir_cycle", stir_observations(), source_profile=STIR_SOURCE,
        evaluation_profile=STIR_PROFILE,
    )
    assert normalized.status == "valid"
    assert normalized.samples[-1]["tool_tip_depth_m"] == 0.03
    result = evaluate_process_feedback(
        "stir_cycle", normalized.samples,
        {"radius_m": 0.02, "depth_m": 0.03, "turns": 1.0, "duration_s": 1.0, "direction": "ccw"},
        normalized.evaluation_profile,
    )
    assert result["process_completed"] is True


def test_timestamp_rollback_invalidates_the_whole_stream():
    observations = pour_observations()
    observations[4]["timestamp_s"] = 1.0
    normalized = normalize_feedback(
        "pour_cycle", observations, source_profile=POUR_SOURCE,
        evaluation_profile=POUR_PROFILE,
    )
    assert normalized.status == "invalid"
    assert "timestamp_not_monotonic" in normalized.errors
    result = evaluate_process_feedback(
        "pour_cycle", normalized.samples, {"tilt_rad": 1.2, "hold_s": 2.0}, POUR_PROFILE,
    )
    assert result["process_completed"] is False


def test_frame_calibration_and_coordinate_omissions_fail_closed():
    observations = pour_observations()
    observations[2].pop("frame_id")
    observations[3]["calibration_ref"] = None
    observations[4].pop("container_frame_id")
    normalized = normalize_feedback(
        "pour_cycle", observations, source_profile=POUR_SOURCE,
        evaluation_profile=POUR_PROFILE,
    )
    assert normalized.status == "invalid"
    assert {"missing_frame_id", "missing_calibration_ref", "missing_container_frame_id"} <= set(normalized.errors)
    assert all(sample["feedback_valid"] is False for sample in normalized.samples)


def test_missing_tip_coordinates_or_grasp_evidence_cannot_qualify_stir():
    observations = stir_observations()
    observations[5]["tool_tip"].pop("y_m")
    observations[6].pop("grasp_valid")
    observations[6]["grasp_state"] = "unknown"
    normalized = normalize_feedback(
        "stir_cycle", observations, source_profile=STIR_SOURCE,
        evaluation_profile=STIR_PROFILE,
    )
    assert normalized.status == "invalid"
    assert "missing_tool_tip_coordinates" in normalized.errors
    assert "grasp_state_unknown" in normalized.errors
    assert all(sample["feedback_valid"] is False for sample in normalized.samples)


def test_explicit_invalid_feedback_is_not_physical_success():
    normalized = normalize_feedback(
        "pour_cycle", pour_observations(feedback_valid=False), source_profile=POUR_SOURCE,
        evaluation_profile=POUR_PROFILE,
    )
    assert normalized.status == "valid"
    result = evaluate_process_feedback(
        "pour_cycle", normalized.samples, {"tilt_rad": 1.2, "hold_s": 2.0}, POUR_PROFILE,
    )
    assert result["process_completed"] is False


def test_source_profile_must_match_action_frame_and_calibration():
    normalized = normalize_feedback(
        "pour_cycle", pour_observations(), source_profile=POUR_SOURCE,
        evaluation_profile=POUR_PROFILE,
        expected_source_profile={
            "frame_id": "camera_rear",
            "calibration_ref": "calibration://rear/v1",
        },
    )
    assert normalized.status == "invalid"
    assert {
        "source_profile_frame_id_mismatch",
        "source_profile_calibration_ref_mismatch",
    } <= set(normalized.errors)


def test_normalized_sample_contract_retains_provenance_for_revalidation():
    first = normalize_feedback(
        "pour_cycle", pour_observations(), source_profile=POUR_SOURCE,
        evaluation_profile=POUR_PROFILE,
    )
    second = normalize_feedback(
        "pour_cycle", first.samples, source_profile=POUR_SOURCE,
        evaluation_profile=POUR_PROFILE,
        expected_source_profile=POUR_SOURCE,
    )
    assert second.status == "valid"
    assert second.samples == first.samples


def test_normalize_and_evaluate_generic_transform_feedback():
    observations = [{
        "timestamp_s": index * 0.2, "frame_id": "camera", "calibration_ref": "artifact://cal",
        "container_frame_id": "container://target", "feedback_valid": True,
        "grasp_valid": True, "engagement_valid": True, "transform_progress": 1.0,
        "transform_error": 0.01,
    } for index in range(5)]
    source = {"frame_id": "camera", "calibration_ref": "artifact://cal", "container_frame_id": "container://target"}
    normalized = normalize_feedback("manipulation_cycle", observations, source_profile=source,
                                    evaluation_profile={"max_sample_gap_s": 0.3,
                                                        "transform_tolerance": 0.05})
    assert normalized.valid
    result = evaluate_process_feedback("manipulation_cycle", normalized.samples, {
        "hold_s": 0.6, "transform": {"magnitude": 1.0},
    }, normalized.evaluation_profile)
    assert result["process_completed"] is True
