import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_blocks_ranking_adapter as module

from robotwin20_adapter.grasp_adaptation import adapt_grasp_candidate


def _pose(x=0.0):
    matrix = np.eye(4)
    matrix[0, 3] = x
    return SimpleNamespace(to_transformation_matrix=lambda: matrix)


def _task(success=True):
    actors = []
    for index in range(3):
        actor = SimpleNamespace(
            get_pose=lambda index=index: _pose(index * 0.1),
            get_functional_point=lambda *_args, index=index: _pose(index * 0.1),
        )
        actors.append(actor)
    return SimpleNamespace(
        block1=actors[0],
        block2=actors[1],
        block3=actors[2],
        block1_target_pose=[0.0, -0.1, 0.75, 1, 0, 0, 0],
        block2_target_pose=[0.1, -0.1, 0.75, 1, 0, 0, 0],
        block3_target_pose=[0.2, -0.1, 0.75, 1, 0, 0, 0],
        check_success=lambda: success,
    )


def test_task_adapter_rejects_other_capability_families():
    with pytest.raises(module.BlocksRankingRgbTaskAdapterError, match="does not support"):
        module.task_adapter("open_microwave")


def test_goal_and_benchmark_facts_are_separate_from_execution_geometry(monkeypatch):
    monkeypatch.setattr(module, "_half_extents", lambda _actor: [0.02, 0.02, 0.02])
    monkeypatch.setattr(module, "_pose_from_pq_wxyz", lambda value: _pose(value[0]))
    adapter = module.task_adapter("blocks_ranking_rgb")
    task = _task()

    execution = adapter.capture_objects(task, include_targets=False)
    goals = adapter.goal_facts(task, seed=7)
    benchmark = adapter.benchmark_result(task, seed=7, scene_revision="scene-4")

    assert all(not any("target" in key for key in item) for item in execution)
    assert goals["schema_version"] == "paos-task-goals/v1"
    assert goals["geometry_source"] == "benchmark_task_definition"
    assert [item["execution_entity_ref"] for item in goals["goals"]] == [
        "entity://block-red-1",
        "entity://block-green-1",
        "entity://block-blue-1",
    ]
    assert benchmark["success"] is True
    assert benchmark["score"] == 1.0
    assert benchmark["motion_authorized"] is False


def _oracle_request(entity_ref="entity://observed-green", scene_revision="scene-4"):
    return {
        "observation_ref": "observation://scene-4/head_camera",
        "scene_revision": scene_revision,
        "frame_id": "head_camera",
        "calibration_ref": "artifact://scene-4/calibration",
        "freshness_ms": 0,
        "max_age_ms": 1000,
        "targets": [
            {
                "entity_ref": entity_ref,
                "category": "cube",
                "confidence": 0.99,
                "spatial_envelope": {
                    "frame_id": "head_camera",
                    "unit": "m",
                    "min_xyz_m": [-0.02, -0.02, 0.73],
                    "max_xyz_m": [0.02, 0.02, 0.77],
                    "confidence": 0.99,
                    "provenance": ["artifact://scene-4/envelope"],
                },
                "geometry_artifacts": [
                    {
                        "artifact_ref": "artifact://scene-4/derived/green-points",
                        "kind": "object_point_cloud",
                        "observation_ref": "observation://scene-4/head_camera",
                        "scene_revision": "scene-4",
                        "entity_ref": entity_ref,
                        "frame_id": "head_camera",
                        "calibration_ref": "artifact://scene-4/calibration",
                        "provenance": ["artifact://scene-4/depth"],
                    }
                ],
            }
        ],
    }


def _oracle_task():
    task = _task()
    actor = task.block2
    task._paos_observed_entities = {"entity://observed-green": actor}
    task._paos_observed_bindings = {
        "entity://observed-green": {
            "captured_pose": actor.get_pose().to_transformation_matrix().tolist(),
            "model": {},
        }
    }
    return task


def test_oracle_grasp_round_trips_through_existing_adaptation():
    adapter = module.task_adapter("blocks_ranking_rgb")
    request = _oracle_request()
    task = _oracle_task()
    calibration = {
        "camera_name": "head_camera",
        "extrinsic_cv": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
    }
    provider_to_contact = [
        1.0, 0.0, 0.0, 0.10527314,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]

    result = adapter.oracle_grasp_candidates(
        task,
        request,
        calibration=calibration,
        provider_to_contact_flat=provider_to_contact,
        scene_revision="scene-4",
    )

    assert result["geometry_source"] == "oracle_actor"
    assert result["motion_authorized"] is False
    assert len(result["candidates"]) == 4
    assert result["funnel"] == {
        "decoded": 4,
        "canonicalized": 4,
        "deduplicated": 4,
        "retained": 4,
    }
    payload = (json.dumps(calibration, sort_keys=True, separators=(",", ":")) + "\n").encode()
    adapted = adapt_grasp_candidate(
        result["candidates"][0],
        payload,
        {
            "observation_ref": request["observation_ref"],
            "observation_frame_id": request["frame_id"],
            "scene_revision": request["scene_revision"],
            "frame_id": "world",
            "calibration_ref": request["calibration_ref"],
            "calibration_sha256": hashlib.sha256(payload).hexdigest(),
            "calibration_revision": "test",
            "candidate_set_ref": "candidate-set://scene-4/head_camera",
        },
        {
            "schema_version": "paos-robotwin20-grasp-adaptation/v2",
            "extrinsic_semantics": "world_to_camera_cv",
            "provider_T_contact_center": provider_to_contact,
            "robot_target_frame": "robotwin_gripper",
            "robot_target_reference_distance_m": 0.12,
            "robot_gripper_bias_m": 0.08,
            "robot_delta_matrix": [[0, 0, 1], [0, -1, 0], [1, 0, 0]],
            "adaptation_provenance_ref": "artifact://test/adaptation",
            "support_clear_direction": {
                "frame_id": "world",
                "vector": [0.0, 0.0, 1.0],
                "provenance_ref": "artifact://test/support",
            },
        },
    )
    expected = np.asarray(task.block2.get_pose().to_transformation_matrix()) @ np.asarray(
        module.BlocksRankingRgbTaskAdapter.object_contact_template
    ).reshape(4, 4)
    assert adapted["contact_center_pose"]["position_m"] == pytest.approx(
        expected[:3, 3], abs=1e-7
    )
    assert adapted["ingress_direction"]["vector"] == pytest.approx(
        expected[:3, 2], abs=1e-7
    )


def test_oracle_grasp_accepts_current_envelope_provenance_without_point_cloud():
    adapter = module.task_adapter("blocks_ranking_rgb")
    request = _oracle_request()
    request["targets"][0].pop("geometry_artifacts")
    result = adapter.oracle_grasp_candidates(
        _oracle_task(),
        request,
        calibration={
            "camera_name": "head_camera",
            "extrinsic_cv": [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]],
        },
        provider_to_contact_flat=list(np.eye(4).reshape(-1)),
        scene_revision="scene-4",
    )

    assert result["geometry_source"] == "oracle_actor"
    assert result["oracle_evidence"][0]["input_provenance_ref"] == "artifact://scene-4/envelope"
    assert len(result["candidates"]) == 4


@pytest.mark.parametrize(
    ("request_value", "calibration", "scene_revision", "message"),
    [
        (_oracle_request(scene_revision="old-scene"), {"camera_name": "head_camera", "extrinsic_cv": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]}, "scene-4", "stale"),
        (_oracle_request(entity_ref="entity://unknown"), {"camera_name": "head_camera", "extrinsic_cv": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]}, "scene-4", "binding"),
        (_oracle_request(), {"camera_name": "other", "extrinsic_cv": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]}, "scene-4", "calibration"),
    ],
)
def test_oracle_grasp_rejects_stale_or_unbound_inputs(
    request_value, calibration, scene_revision, message
):
    with pytest.raises(module.BlocksRankingRgbTaskAdapterError, match=message):
        module.task_adapter("blocks_ranking_rgb").oracle_grasp_candidates(
            _oracle_task(),
            request_value,
            calibration=calibration,
            provider_to_contact_flat=list(np.eye(4).reshape(-1)),
            scene_revision=scene_revision,
        )
