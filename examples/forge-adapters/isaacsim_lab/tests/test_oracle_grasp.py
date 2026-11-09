"""Oracle execution mode: truth grasp geometry, provider wiring and route preselection."""
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from isaacsim_lab.oracle_grasp_geometry import (
    OracleGraspGeometryError,
    OracleSimulatorTruthGraspProvider,
    bottle_grasp_candidates,
    rod_grasp_candidates,
    validate_depth_fractions,
    validate_gripper_geometry,
)
from isaacsim_lab.perception_runtime import build_visual_providers
from isaacsim_lab.phase_motion import IsaacPhaseMotion, PhaseMotionError, acquire_route_selection
from isaacsim_lab.visual_geometry import candidate_world_pose
from isaacsim_lab.visual_perception import LabArtifactStore, RecordedGraspProvider

GRIPPER = {"gripper_width_m": 0.08, "finger_height_m": 0.06, "finger_depth_m": 0.05}


def _cylinder(radius, height, center, axis="z", samples=400):
    axis_vector = np.asarray({"z": (0, 0, 1), "x": (1, 0, 0)}[axis], dtype=float)
    reference = np.array([1.0, 0.0, 0.0]) if axis == "z" else np.array([0.0, 0.0, 1.0])
    basis = np.cross(axis_vector, reference)
    basis /= np.linalg.norm(basis)
    second = np.cross(axis_vector, basis)
    theta = np.linspace(0, 2 * np.pi, samples)
    offsets = np.linspace(-height / 2, height / 2, samples)
    center = np.asarray(center, dtype=float)
    return np.asarray([
        center + axis_vector * offset + basis * (radius * np.cos(angle)) + second * (radius * np.sin(angle))
        for offset, angle in zip(offsets, theta)
    ])


def test_validate_gripper_geometry_rejects_invalid_values():
    with pytest.raises(OracleGraspGeometryError):
        validate_gripper_geometry(None)
    with pytest.raises(OracleGraspGeometryError):
        validate_gripper_geometry({**GRIPPER, "gripper_width_m": 0})
    with pytest.raises(OracleGraspGeometryError):
        validate_gripper_geometry({**GRIPPER, "finger_height_m": True})
    with pytest.raises(OracleGraspGeometryError):
        validate_gripper_geometry({**GRIPPER, "finger_depth_m": float("nan")})


def test_validate_depth_fractions_bounds():
    assert validate_depth_fractions(None, (0.35, 0.5)) == (0.35, 0.5)
    assert validate_depth_fractions([0.4], (0.35,)) == (0.4,)
    with pytest.raises(OracleGraspGeometryError):
        validate_depth_fractions([0.05], (0.35,))
    with pytest.raises(OracleGraspGeometryError):
        validate_depth_fractions([0.95], (0.35,))
    with pytest.raises(OracleGraspGeometryError):
        validate_depth_fractions([], (0.35,))


def test_bottle_candidates_target_semantic_body_band():
    points = _cylinder(radius=0.03, height=0.2, center=(0.5, 0.0, 0.1))
    rim = {"tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0], "rim_radius_m": 0.03}
    candidates = bottle_grasp_candidates(points, rim, gripper=GRIPPER, base_xy=(0.0, 0.0))
    assert [round(value["position_world_m"][2], 4) for value in candidates] == [0.13, 0.10, 0.07]
    for value in candidates:
        position = np.asarray(value["position_world_m"])
        rotation = value["rotation_world"]
        # Approach horizontally toward the base, positioned on the near sidewall.
        assert position[0] == pytest.approx(0.47, abs=1e-4)
        assert np.allclose(rotation[:, 0], [-1, 0, 0], atol=2e-3)
        # The provider z-axis spans the vessel axis, so the TCP finger span follows it.
        assert np.allclose(rotation[:, 2], [0, 0, 1], atol=2e-3)
        assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-9)
        assert np.linalg.det(rotation) > 0


def test_bottle_candidates_reject_unresolved_geometry():
    rim = {"tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0], "rim_radius_m": 0.03}
    short = _cylinder(radius=0.03, height=0.01, center=(0.5, 0.0, 0.195))
    with pytest.raises(OracleGraspGeometryError):
        bottle_grasp_candidates(short, rim, gripper=GRIPPER, base_xy=(0.0, 0.0))
    thin = _cylinder(radius=0.001, height=0.2, center=(0.5, 0.0, 0.1))
    with pytest.raises(OracleGraspGeometryError):
        bottle_grasp_candidates(thin, rim, gripper=GRIPPER, base_xy=(0.0, 0.0))


def test_rod_candidates_leave_each_end_free():
    length = 0.2
    points = _cylinder(radius=0.005, height=length, center=(0.5, 0.0, 0.1), axis="x")
    pair = {"origin_world": [0.4, 0.0, 0.1], "tip_world": [0.6, 0.0, 0.1]}
    candidates = rod_grasp_candidates(points, pair, gripper=GRIPPER, base_xy=(0.0, 0.0))
    assert len(candidates) == 2
    positions = [np.asarray(value["position_world_m"]) for value in candidates]
    # Shaft fractions 0.3 and 0.7 leave opposite ends farther than the ambiguity ratio.
    distances = np.linalg.norm(positions[0] - np.asarray([[0.4, 0, 0.1], [0.6, 0, 0.1]]), axis=1)
    assert abs(distances[0] - distances[1]) > length * 0.12
    for value in candidates:
        rotation = value["rotation_world"]
        assert np.allclose(rotation[:, 2], [1, 0, 0], atol=2e-3)
        assert np.allclose(rotation[:, 0], [0, -1, 0], atol=2e-3)  # deterministic perpendicular


def test_rod_candidates_reject_short_rods():
    pair = {"origin_world": [0.5, 0.0, 0.1], "tip_world": [0.53, 0.0, 0.1]}
    points = _cylinder(radius=0.005, height=0.03, center=(0.515, 0.0, 0.1), axis="x")
    with pytest.raises(OracleGraspGeometryError):
        rod_grasp_candidates(points, pair, gripper=GRIPPER, base_xy=(0.0, 0.0))


def _write_record(store, *, category, features, points, transform):
    points_ref = store.write("object-point-cloud", np.asarray(points, dtype=float))
    return {
        "observation_ref": "observation://capture/view",
        "scene_revision": "capture",
        "frame_id": "view",
        "calibration_ref": "calibration://capture/view",
        "entity_ref": "entity://simulator-truth-R01",
        "category": category,
        "geometry_qualification": "simulator_ground_truth",
        "process_feature_candidates": features,
        "world_from_camera": np.asarray(transform, dtype=float).tolist(),
        "points_ref": points_ref,
        "geometry_ref": "artifact://labutopia/observed-geometry/truth.json",
    }


def _world_from_camera():
    transform = np.eye(4)
    transform[:3, :3] = Rotation.from_euler("z", 0.4).as_matrix()
    transform[:3, 3] = [0.1, -0.05, 0.02]
    return transform


def _propose_request(record, **overrides):
    request = {
        "observation_ref": record["observation_ref"],
        "scene_revision": record["scene_revision"],
        "frame_id": record["frame_id"],
        "calibration_ref": record["calibration_ref"],
        "targets": [{"entity_ref": record["entity_ref"]}],
    }
    request.update(overrides)
    return request


def test_bottle_record_generates_provider_shaped_candidates(tmp_path):
    store = LabArtifactStore(tmp_path)
    points = _cylinder(radius=0.03, height=0.2, center=(0.5, 0.0, 0.1))
    transform = _world_from_camera()
    camera_points = (points - transform[:3, 3]) @ transform[:3, :3]
    rim = {"feature_kind": "rim", "feature_role": "pour_lip",
           "tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0], "rim_radius_m": 0.03}
    record = _write_record(store, category="reagent_bottle", features=[rim],
                           points=camera_points, transform=transform)
    provider = OracleSimulatorTruthGraspProvider(store, gripper_geometry=GRIPPER)
    provider.bind_records(lambda calibration_ref: {record["entity_ref"]: record})
    output = provider.propose(_propose_request(record))
    assert output["geometry_qualification"] == "simulator_ground_truth"
    assert output["source"] == "simulator_truth_oracle"
    assert output["provider_available"] is True
    assert len(output["candidates"]) == 3
    provider_from_tcp = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1]], dtype=float)
    expected_depths = [0.13, 0.10, 0.07]
    for candidate, depth in zip(output["candidates"], expected_depths):
        assert set(candidate) == {"candidate_ref", "entity_ref", "grasp_frame", "approach_direction",
                                  "score", "confidence", "provenance", "qualification", "grasp_geometry"}
        assert candidate["grasp_frame"]["frame_id"] == record["frame_id"]
        assert candidate["provenance"] == [record["points_ref"], record["geometry_ref"]]
        pose, approach = candidate_world_pose(
            candidate, np.asarray(record["world_from_camera"]), provider_from_tcp)
        assert np.allclose(pose[:3, 3], [0.47, 0.0, depth], atol=1e-3)
        assert np.allclose(approach, [-1, 0, 0], atol=1e-3)


def test_provider_requires_same_capture_truth_record(tmp_path):
    store = LabArtifactStore(tmp_path)
    points = _cylinder(radius=0.03, height=0.2, center=(0.5, 0.0, 0.1))
    rim = {"feature_kind": "rim", "tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0]}
    record = _write_record(store, category="reagent_bottle", features=[rim], points=points,
                           transform=_world_from_camera())
    provider = OracleSimulatorTruthGraspProvider(store, gripper_geometry=GRIPPER)
    provider.bind_records(lambda calibration_ref: {record["entity_ref"]: record})
    with pytest.raises(OracleGraspGeometryError, match="same-capture"):
        provider.propose(_propose_request(record, scene_revision="other"))
    stale = dict(record)
    stale["geometry_qualification"] = "validated_observation"
    provider.bind_records(lambda calibration_ref: {record["entity_ref"]: stale})
    with pytest.raises(OracleGraspGeometryError, match="simulator_ground_truth"):
        provider.propose(_propose_request(record))


def test_provider_reports_ambiguities_without_candidates(tmp_path):
    store = LabArtifactStore(tmp_path)
    points = _cylinder(radius=0.03, height=0.2, center=(0.5, 0.0, 0.1))
    rims = [{"feature_kind": "rim", "tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0]},
            {"feature_kind": "rim", "tip_world": [0.5, 0.0, 0.21], "axis_world": [0.0, 0.0, 1.0]}]
    record = _write_record(store, category="reagent_bottle", features=rims, points=points,
                           transform=_world_from_camera())
    provider = OracleSimulatorTruthGraspProvider(store, gripper_geometry=GRIPPER)
    provider.bind_records(lambda calibration_ref: {record["entity_ref"]: record})
    output = provider.propose(_propose_request(record))
    assert output["candidates"] == []
    assert output["ambiguities"][0]["code"] == "oracle_grasp_requires_single_rim"

    tube = _write_record(store, category="test_tube", features=[], points=points,
                         transform=_world_from_camera())
    provider.bind_records(lambda calibration_ref: {tube["entity_ref"]: tube})
    output = provider.propose(_propose_request(tube))
    assert output["ambiguities"][0]["code"] == "oracle_grasp_unsupported_category"


def test_unbound_provider_fails_closed(tmp_path):
    store = LabArtifactStore(tmp_path)
    provider = OracleSimulatorTruthGraspProvider(store, gripper_geometry=GRIPPER)
    with pytest.raises(OracleGraspGeometryError, match="not bound"):
        provider.propose({"targets": [], "observation_ref": "o", "scene_revision": "s",
                          "frame_id": "f", "calibration_ref": "c"})


def test_oracle_profile_builds_and_binds_without_model_workers(tmp_path):
    profile = Path(__file__).parents[1] / "configs/labutopia-oracle-perception.json"
    visual, grasps = build_visual_providers(profile, None, tmp_path, None)
    assert isinstance(grasps, RecordedGraspProvider)
    # The bound records accessor proves the oracle provider was wired; without
    # any understood capture it must fail closed on the same-capture contract.
    with pytest.raises(OracleGraspGeometryError, match="same-capture"):
        grasps.propose({"observation_ref": "o", "scene_revision": "s", "frame_id": "f",
                        "calibration_ref": "c", "targets": [{"entity_ref": "entity://x"}]})
    receipts = [item for item in tmp_path.rglob("*.json")
                if "perception-configuration" in str(item)]
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["grasp_source"] == "simulator_truth_oracle"


def test_grasp_source_validation_rejects_invalid_combinations(tmp_path):
    profile = Path(__file__).parents[1] / "configs/labutopia-oracle-perception.json"
    config = json.loads(profile.read_text(encoding="utf-8"))
    config["grasp_source"] = "unexpected"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="grasp_source"):
        build_visual_providers(path, None, tmp_path, None)

    config["grasp_source"] = "simulator_truth_oracle"
    config["perception_mode"] = "model"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="simulator_truth_oracle"):
        build_visual_providers(path, None, tmp_path, None)

    config["perception_mode"] = "simulator_truth"
    config.pop("oracle_grasp")
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="oracle_grasp"):
        build_visual_providers(path, None, tmp_path, None)


def test_acquire_route_selection_accepts_truth_preselected():
    assert acquire_route_selection(
        {"acquire_route_selection": "simulator_truth_preselected"}) == "simulator_truth_preselected"
    with pytest.raises(PhaseMotionError, match="unsupported acquire route selection policy"):
        acquire_route_selection({"acquire_route_selection": "oracle"})


def test_preselected_policy_qualifies_exactly_one_variant():
    model = object.__new__(IsaacPhaseMotion)
    model.config = {
        "approach_distance_m": .12,
        "acquire_route_selection": "simulator_truth_preselected",
        "acquire_transit_clearance_candidates_m": [.04, .08, .12],
        "acquire_transport_orientation_candidates_xyzw": [[1., 0., 0., 0.], [0., 1., 0., 0.]],
        "acquire_axial_symmetry_angles_rad": [0., np.pi / 2],
        "acquire_staging_corridor_candidates": [
            {"approach_distance_m": .12, "staging_backoff_m": 0., "tangential_offset_m": 0.},
            {"approach_distance_m": .18, "staging_backoff_m": .08, "tangential_offset_m": .06},
        ],
        "acquire_route_strategies": ["staged"],
        "lift_distance_m": .10,
        "settle_s": .6,
        "acquire_timing": "stage_continuous",
    }
    model.scene = {"physics_evidence_ref": "artifact://labutopia/scene-physics/actual.json"}
    model._time_acquire_route = lambda route: route.update(execution_steps=list(route["steps"]))
    model.validate_grasp_aperture = lambda _target: None
    current = np.eye(4)
    current[:3, 3] = [-.45, 0., 1.0]
    body = np.eye(4)
    body[:3, 3] = [-.27, -.36, .82]
    model.tcp = lambda: current.copy()
    model.observed_pose = lambda _source: body.copy()
    model.bind_observed_model = lambda *_args: (body.copy(), np.eye(4))
    model.body_pose = lambda _path: np.eye(4)
    artifacts = []
    model._artifact = lambda kind, data: artifacts.append((kind, data)) or "artifact://readiness/test.json"
    captured = []

    def qualify(waypoints, *_args, **_kwargs):
        captured.append(waypoints)
        return {"start_joints": [0.] * 7, "steps": [{"joints": [.2] + [0.] * 6, "stage": "lift"}]}

    model.qualify = qualify
    target = {
        "world_from_control": {"translation_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "entity_prim_path": "/World/R03/Model",
        "destination_prim_path": "/World/BEAKER/Model",
        "object_pose": {"position_m": [-.27, -.36, .82], "orientation_xyzw": [0., 0., 0., 1.]},
        "grasp_frame": {"position_m": [-.27, -.36, .86], "orientation_xyzw": [0., 0., 0., 1.]},
        "approach_direction": {"vector": [0., -1., 0.]},
        "destination_pose": {"position_m": [-.08, 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "return_pose": {"position_m": [-.27, -.36, .82], "orientation_xyzw": [0., 0., 0., 1.]},
    }
    observation_model = {"grasp_symmetry": {"kind": "axial", "axis_world": [0., 0., 1.],
                                            "origin_world": [-.27, -.36, .82]}}
    route, _evidence = model.prepare({"manipulation_target": target, "observation_model": observation_model,
                                      "scene_revision": "scene"})
    assert len(captured) == 1
    started = [value for kind, value in artifacts if kind == "acquire-search"
               and value.get("status") == "started"][0]
    assert started["policy"] == "simulator_truth_preselected"
    assert started["variant_count"] == 1
    assert route["acquire_route_selection"] == "simulator_truth_preselected"
    assert route["acquire_transit_clearance_m"] == pytest.approx(.04)
    assert route["acquire_axial_symmetry_angle_rad"] == 0.0
