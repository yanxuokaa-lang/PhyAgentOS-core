from copy import deepcopy

import pytest

from robotwin20_adapter.grasp_postprocessing import (
    GRASP_POSTPROCESSING_SCHEMA_VERSION,
    GraspPostprocessingError,
    apply_contact_variant,
    derive_robot_hand_pose,
    qualify_contact_variants,
    qualify_geometry_artifact,
)


def _candidate():
    return {
        "candidate_ref": "candidate://block/0",
        "scene_revision": "scene-1",
        "execution_grasp": {
            "contact_center_pose": {
                "frame_id": "world", "position_m": [0.0, 0.0, 0.8],
                "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
            },
            "robot_target_pose": {
                "frame_id": "world", "position_m": [0.0, 0.0, 1.0],
                "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
            },
            "ingress_direction": {"vector": [0.0, 0.0, -1.0]},
        },
    }


def test_selects_minimum_backoff_that_clears_support_and_preserves_pinch():
    candidate = _candidate()
    result = qualify_contact_variants(
        candidate,
        gripper_vertices_m=[[0.0, 0.0, 0.70], [0.02, 0.0, 0.80]],
        object_center_m=[0.0, 0.0, 0.8],
        object_half_extents_m=[0.05, 0.05, 0.10],
        support_normal=[0.0, 0.0, 1.0],
        support_offset_m=0.75,
        backoff_candidates_m=[0.0, 0.04, 0.08],
    )
    assert result["schema_version"] == GRASP_POSTPROCESSING_SCHEMA_VERSION
    assert result["selected_backoff_m"] == pytest.approx(0.08)
    assert [item["status"] for item in result["variants"]] == ["rejected", "rejected", "valid"]
    applied = apply_contact_variant(candidate["execution_grasp"], result)
    assert applied["robot_target_pose"]["position_m"] == pytest.approx([0.0, 0.0, 1.08])
    assert applied["contact_center_pose"]["position_m"] == pytest.approx([0.0, 0.0, 0.88])
    assert candidate["execution_grasp"]["robot_target_pose"]["position_m"] == [0.0, 0.0, 1.0]


def test_nominal_pose_is_retained_when_already_clear():
    result = qualify_contact_variants(
        _candidate(),
        gripper_vertices_m=[[0.0, 0.0, 0.80]],
        object_center_m=[0.0, 0.0, 0.8],
        object_half_extents_m=[0.05, 0.05, 0.10],
        support_normal=[0.0, 0.0, 1.0],
        support_offset_m=0.74,
        backoff_candidates_m=[0.0, 0.04],
    )
    assert result["selected_backoff_m"] == 0.0


def test_unavailable_is_explicit_when_no_variant_can_keep_pinch_or_clear_support():
    result = qualify_contact_variants(
        _candidate(),
        gripper_vertices_m=[[0.0, 0.0, 0.70]],
        object_center_m=[0.0, 0.0, 0.8],
        object_half_extents_m=[0.05, 0.05, 0.01],
        support_normal=[0.0, 0.0, 1.0],
        support_offset_m=0.74,
        backoff_candidates_m=[0.0, 0.08],
    )
    assert result["status"] == "unavailable"
    assert result["selected_backoff_m"] is None
    with pytest.raises(GraspPostprocessingError, match="usable"):
        apply_contact_variant(_candidate()["execution_grasp"], result)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"gripper_vertices_m": []}, "vertices are empty"),
        ({"support_normal": [0.0, 0.0, 0.0]}, "degenerate"),
        ({"backoff_candidates_m": [0.1, 0.0]}, "strictly increasing"),
    ],
)
def test_invalid_geometry_is_rejected(kwargs, message):
    values = {
        "gripper_vertices_m": [[0.0, 0.0, 0.8]],
        "object_center_m": [0.0, 0.0, 0.8],
        "object_half_extents_m": [0.05, 0.05, 0.1],
        "support_normal": [0.0, 0.0, 1.0],
        "support_offset_m": 0.74,
        "backoff_candidates_m": [0.0, 0.1],
    }
    values.update(kwargs)
    with pytest.raises(GraspPostprocessingError, match=message):
        qualify_contact_variants(_candidate(), **values)


def test_qualification_does_not_mutate_candidate():
    candidate = _candidate()
    before = deepcopy(candidate)
    qualify_contact_variants(
        candidate,
        gripper_vertices_m=[[0.0, 0.0, 0.8]],
        object_center_m=[0.0, 0.0, 0.8],
        object_half_extents_m=[0.05, 0.05, 0.1],
        support_normal=[0.0, 0.0, 1.0],
        support_offset_m=0.74,
        backoff_candidates_m=[0.0],
    )
    assert candidate == before


def test_geometry_artifact_bridge_uses_all_panda_links():
    geometry = {
        "schema_version": "paos-robotwin20-grasp-contact-geometry/v1",
        "frame_id": "world",
        "scene_revision": "scene-1",
        "motion_authorized": False,
        "arms": {"right": {"links": {
            "panda_hand": [[0.0, 0.0, 0.8]],
            "panda_leftfinger": [[0.0, 0.0, 0.8]],
            "panda_rightfinger": [[0.0, 0.0, 0.8]],
        }, "reference_hand_pose": {
            "frame_id": "world", "position_m": [0.0, 0.0, 0.0],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
        }}},
        "support_plane": {"normal": [0.0, 0.0, 1.0], "offset_m": 0.74},
    }
    result = qualify_geometry_artifact(
        _candidate(), geometry, arm_id="right", object_center_m=[0.0, 0.0, 0.8],
        object_half_extents_m=[0.05, 0.05, 0.1], backoff_candidates_m=[0.0],
    )
    assert result["status"] == "qualified"


def test_geometry_artifact_projects_reference_vertices_to_target_pose():
    candidate = _candidate()
    candidate["execution_grasp"]["robot_target_pose"]["position_m"] = [1.0, 0.0, 1.0]
    candidate["execution_grasp"]["robot_target_pose"]["orientation_xyzw"] = [
        0.0, 0.0, 2**-0.5, 2**-0.5
    ]
    geometry = {
        "schema_version": "paos-robotwin20-grasp-contact-geometry/v1",
        "frame_id": "world", "scene_revision": "scene-1", "motion_authorized": False,
        "arms": {"right": {
            "links": {
                "panda_hand": [[0.0, 0.0, 0.0]],
                "panda_leftfinger": [[0.0, 0.0, 0.0]],
                "panda_rightfinger": [[0.0, 0.0, 0.0]],
            },
            "reference_hand_pose": {
                "frame_id": "world", "position_m": [0.0, 0.0, 0.0],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            },
        }},
        "support_plane": {"normal": [0.0, 0.0, 1.0], "offset_m": 0.74},
    }
    result = qualify_geometry_artifact(
        candidate, geometry, arm_id="right", object_center_m=[0.0, 0.0, 0.8],
        object_half_extents_m=[0.05, 0.05, 0.1], backoff_candidates_m=[0.0],
    )
    assert result["variants"][0]["support_clearance_m"] == pytest.approx(0.26)


def test_geometry_artifact_requires_reference_hand_pose():
    geometry = {
        "schema_version": "paos-robotwin20-grasp-contact-geometry/v1",
        "frame_id": "world", "scene_revision": "scene-1", "motion_authorized": False,
        "arms": {"right": {"links": {
            "panda_hand": [[0.0, 0.0, 0.8]],
            "panda_leftfinger": [[0.0, 0.0, 0.8]],
            "panda_rightfinger": [[0.0, 0.0, 0.8]],
        }}},
        "support_plane": {"normal": [0.0, 0.0, 1.0], "offset_m": 0.74},
    }
    with pytest.raises(GraspPostprocessingError, match="reference hand pose"):
        qualify_geometry_artifact(
            _candidate(), geometry, arm_id="right", object_center_m=[0.0, 0.0, 0.8],
            object_half_extents_m=[0.05, 0.05, 0.1], backoff_candidates_m=[0.0],
        )


def test_robot_target_pose_derives_actual_robo_twin_hand_pose():
    pose = derive_robot_hand_pose(
        _candidate()["execution_grasp"]["robot_target_pose"],
        reference_distance_m=0.12,
        gripper_bias_m=0.08,
        delta_matrix=[[0, 0, 1], [0, -1, 0], [1, 0, 0]],
    )
    assert pose["position_m"] == pytest.approx([0.04, 0.0, 1.0])
    assert pose["frame_id"] == "world"


def test_robot_target_pose_uses_profile_reference_distance_without_mutating_target():
    candidate = _candidate()
    original = deepcopy(candidate)
    pose = derive_robot_hand_pose(
        candidate["execution_grasp"]["robot_target_pose"],
        reference_distance_m=0.15,
        gripper_bias_m=0.08,
        delta_matrix=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    )
    assert pose["position_m"] == pytest.approx([0.07, 0.0, 1.0])
    assert candidate == original


@pytest.mark.parametrize(
    ("reference_distance_m", "gripper_bias_m", "delta_matrix", "message"),
    [
        (0.0, 0.08, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "reference distance"),
        (float("nan"), 0.08, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "reference distance"),
        (0.12, -0.01, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "gripper bias"),
        (0.12, 0.08, [[1, 0], [0, 1]], "delta matrix"),
    ],
)
def test_robot_target_pose_rejects_invalid_provider_transform(
    reference_distance_m, gripper_bias_m, delta_matrix, message
):
    with pytest.raises(GraspPostprocessingError, match=message):
        derive_robot_hand_pose(
            _candidate()["execution_grasp"]["robot_target_pose"],
            reference_distance_m=reference_distance_m,
            gripper_bias_m=gripper_bias_m,
            delta_matrix=delta_matrix,
        )


def test_actual_hand_pose_can_expose_nominal_table_clearance_failure():
    geometry = {
        "schema_version": "paos-robotwin20-grasp-contact-geometry/v1",
        "frame_id": "world", "scene_revision": "scene-1", "motion_authorized": False,
        "arms": {"right": {
            "links": {
                "panda_hand": [[0.0, 0.0, -0.020164]],
                "panda_leftfinger": [[0.0, 0.0, -0.020164]],
                "panda_rightfinger": [[0.0, 0.0, -0.020164]],
            },
            "reference_hand_pose": {
                "frame_id": "world", "position_m": [0.0, 0.0, 0.0],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            },
        }},
        "support_plane": {"normal": [0.0, 0.0, 1.0], "offset_m": 0.74},
    }
    result = qualify_geometry_artifact(
        _candidate(), geometry, arm_id="right", object_center_m=[0.0, 0.0, 0.8],
        object_half_extents_m=[0.05, 0.05, 0.1], backoff_candidates_m=[0.0],
        target_hand_pose={
            "frame_id": "world", "position_m": [0.0, 0.0, 0.748],
            "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
        },
    )
    assert result["status"] == "unavailable"
    assert result["variants"][0]["support_clearance_m"] == pytest.approx(-0.012164)
