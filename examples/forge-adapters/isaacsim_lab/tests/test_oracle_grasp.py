"""Oracle execution mode: truth grasp geometry, provider wiring and route preselection."""
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from isaacsim_lab.oracle_grasp_geometry import (
    DEFAULT_TCP_PAD_SPAN_OFFSET_M,
    OracleGraspGeometryError,
    OracleSimulatorTruthGraspProvider,
    _approach_perpendicular_to_axis,
    _horizontal_toward_base,
    _provider_rotation,
    bottle_grasp_candidates,
    rod_grasp_candidates,
    validate_depth_fractions,
    validate_gripper_geometry,
    validate_tilt_angles,
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
    bands = [0.14, 0.13, 0.12, 0.11, 0.10, 0.09, 0.08, 0.07]
    assert [value["position_world_m"][2] for value in candidates] == pytest.approx(
        [band + DEFAULT_TCP_PAD_SPAN_OFFSET_M for band in bands])
    for value in candidates:
        position = np.asarray(value["position_world_m"])
        rotation = value["rotation_world"]
        # Approach horizontally toward the base, placed on the raised span axis.
        assert position[0] == pytest.approx(0.5, abs=1e-4)
        assert position[1] == pytest.approx(0.0, abs=1e-4)
        assert np.allclose(rotation[:, 0], [-1, 0, 0], atol=2e-3)
        # The provider z-axis spans the vessel axis, so the TCP finger span follows it.
        assert np.allclose(rotation[:, 2], [0, 0, 1], atol=2e-3)
        assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-9)
        assert np.linalg.det(rotation) > 0


def test_bottle_candidates_cover_squat_vessel_gate_window():
    """Live run4 regression: R01 (0.08 m vessel, 0.0144 m rim, 0.06 m fingers).

    The task-affordance gate accepts only projections between the opening
    clearance max(2 x rim radius, 8% of extent) and the support clearance
    max(12% of extent, 0.012 + half the finger height). Coarse fractions
    (0.35/0.50/0.65) all fell outside that window; the dense body band must
    keep at least one candidate inside whenever the window is wider than one
    sampling step.
    """
    points = _cylinder(radius=0.032, height=0.08, center=(0.5, 0.0, 0.04))
    rim = {"tip_world": [0.5, 0.0, 0.08], "axis_world": [0.0, 0.0, 1.0], "rim_radius_m": 0.0144}
    candidates = bottle_grasp_candidates(points, rim, gripper=GRIPPER, base_xy=(0.0, 0.0))
    axis = np.asarray(rim["axis_world"], dtype=float)
    tip = np.asarray(rim["tip_world"], dtype=float)
    projections = (points - tip) @ axis
    extent = float(np.ptp(projections))
    support_projection = float(np.quantile(projections, 0.02))
    opening_bound = -max(2 * rim["rim_radius_m"], extent * 0.08)
    support_bound = support_projection + max(extent * 0.12, 0.012 + max(
        GRIPPER["finger_height_m"], GRIPPER["finger_depth_m"]) * 0.5)
    inside = [
        candidate for candidate in candidates
        if support_bound < float(np.dot(np.asarray(candidate["position_world_m"]) - tip, axis))
        < opening_bound
    ]
    assert inside, "dense oracle body band must intersect the gate window of a squat vessel"


def test_bottle_candidates_reject_unresolved_geometry():
    rim = {"tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0], "rim_radius_m": 0.03}
    short = _cylinder(radius=0.03, height=0.01, center=(0.5, 0.0, 0.195))
    with pytest.raises(OracleGraspGeometryError):
        bottle_grasp_candidates(short, rim, gripper=GRIPPER, base_xy=(0.0, 0.0))
    thin = _cylinder(radius=0.001, height=0.2, center=(0.5, 0.0, 0.1))
    with pytest.raises(OracleGraspGeometryError):
        bottle_grasp_candidates(thin, rim, gripper=GRIPPER, base_xy=(0.0, 0.0))


def test_bottle_tilt_zero_keeps_rotation_but_raises_position_on_axis():
    """With tilt 0 the candidates keep the legacy frame and only raise the pose.

    The reference rebuilds the historical frame with the unchanged geometry
    helpers and moves the legacy sidewall point onto the span axis raised by
    the pad-span offset, so any deviation in the tilt=0 path (for example
    accidental renormalization) breaks this test.
    """
    points = _cylinder(radius=0.03, height=0.2, center=(0.5, 0.0, 0.1))
    rim = {"tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0], "rim_radius_m": 0.03}
    fractions = (0.3, 0.5)
    tip = np.asarray(rim["tip_world"], dtype=float)
    axis = np.asarray(rim["axis_world"], dtype=float)
    extent = float(np.ptp((points - tip) @ axis))
    approach = _approach_perpendicular_to_axis(_horizontal_toward_base(points.mean(0), (0., 0.)), axis)
    legacy_rotation = _provider_rotation(approach, axis)
    expected = [{
        "position_world_m": tip + axis * (-extent * fraction) + axis * DEFAULT_TCP_PAD_SPAN_OFFSET_M,
        "rotation_world": legacy_rotation,
    } for fraction in fractions]
    for tilts in (None, [0.0]):
        candidates = bottle_grasp_candidates(points, rim, gripper=GRIPPER, base_xy=(0., 0.),
                                             depth_fractions=fractions, tilt_angles=tilts)
        assert len(candidates) == len(expected)
        for candidate, want in zip(candidates, expected):
            assert np.array_equal(np.asarray(candidate["position_world_m"]),
                                  want["position_world_m"])
            assert np.array_equal(candidate["rotation_world"], want["rotation_world"])


def test_bottle_tilt_variants_keep_contact_and_tilt_the_frame():
    points = _cylinder(radius=0.03, height=0.2, center=(0.5, 0.0, 0.1))
    rim = {"tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0], "rim_radius_m": 0.03}
    fractions = (0.4, 0.6)
    tilts = [0.0, 0.2618, 0.5236, 0.6981]
    candidates = bottle_grasp_candidates(points, rim, gripper=GRIPPER, base_xy=(0., 0.),
                                         depth_fractions=fractions, tilt_angles=tilts)
    assert len(candidates) == len(fractions) * len(tilts)
    axis = np.asarray(rim["axis_world"], dtype=float)
    tip = np.asarray(rim["tip_world"], dtype=float)
    approach = _approach_perpendicular_to_axis(_horizontal_toward_base(points.mean(0), (0., 0.)), axis)
    extent = float(np.ptp((points - tip) @ axis))
    for f_index, fraction in enumerate(fractions):
        group = candidates[f_index * len(tilts):(f_index + 1) * len(tilts)]
        axis_point = tip + axis * (-extent * fraction)
        for t_index, tilt in enumerate(tilts):
            candidate = group[t_index]
            position = np.asarray(candidate["position_world_m"])
            rotation = np.asarray(candidate["rotation_world"])
            # Outer fraction, inner tilt: depth bands stay contiguous per tilt group.
            tilted_axis = axis * np.cos(tilt) + approach * np.sin(tilt)
            # The on-axis placement travels with the tilted span axis.
            assert position == pytest.approx(axis_point + tilted_axis * DEFAULT_TCP_PAD_SPAN_OFFSET_M)
            assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-9)
            assert np.linalg.det(rotation) > 0
            assert float(np.dot(rotation[:, 0], axis)) == pytest.approx(-np.sin(tilt), abs=1e-9)
            assert float(np.dot(rotation[:, 2], axis)) == pytest.approx(np.cos(tilt), abs=1e-9)


def test_validate_tilt_angles_bounds_and_ordering():
    assert validate_tilt_angles(None, (0.,)) == (0.,)
    assert validate_tilt_angles([0.5, 0.2, 0.5], (0.,)) == (0.2, 0.5)
    assert validate_tilt_angles((0, 0.3), (0.,)) == (0.0, 0.3)
    for invalid in ([-0.01], [np.pi / 2], [float("nan")], [float("inf")], [], [True], ["0.2"], 0.3):
        with pytest.raises(OracleGraspGeometryError, match="oracle tilt_angles_rad"):
            validate_tilt_angles(invalid, (0.,))


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
    assert output["provider_available"] is True
    assert len(output["candidates"]) == 8
    # The snapshot must pass the generic grasp-proposal contract exactly.
    from PhyAgentOS.forge.capability_runtime.grasp_proposal import (
        normalize_snapshot,
        validate_snapshot,
    )
    snapshot = normalize_snapshot(output)
    assert snapshot is not None
    assert validate_snapshot(snapshot, frame_id=record["frame_id"],
                             requested_entity_refs={record["entity_ref"]}) is None
    assert output["funnel"] == {"decoded": 8, "canonicalized": 8, "deduplicated": 8, "retained": 8}
    assert record["points_ref"] in output["produced_evidence_refs"]
    provider_from_tcp = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1]], dtype=float)
    expected_bands = [0.14, 0.13, 0.12, 0.11, 0.10, 0.09, 0.08, 0.07]
    for candidate, band in zip(output["candidates"], expected_bands):
        assert set(candidate) == {"candidate_ref", "entity_ref", "grasp_frame", "approach_direction",
                                  "score", "confidence", "provenance", "qualification", "grasp_geometry"}
        assert candidate["grasp_frame"]["frame_id"] == record["frame_id"]
        assert candidate["provenance"] == [record["points_ref"], record["geometry_ref"]]
        pose, approach = candidate_world_pose(
            candidate, np.asarray(record["world_from_camera"]), provider_from_tcp)
        assert np.allclose(pose[:3, 3], [0.5, 0.0, band + DEFAULT_TCP_PAD_SPAN_OFFSET_M], atol=1e-3)
        assert np.allclose(approach, [-1, 0, 0], atol=1e-3)


def test_provider_tilt_configuration_extends_bottle_candidates(tmp_path):
    store = LabArtifactStore(tmp_path)
    points = _cylinder(radius=0.03, height=0.2, center=(0.5, 0.0, 0.1))
    transform = _world_from_camera()
    camera_points = (points - transform[:3, 3]) @ transform[:3, :3]
    rim = {"feature_kind": "rim", "tip_world": [0.5, 0.0, 0.2], "axis_world": [0.0, 0.0, 1.0],
           "rim_radius_m": 0.03}
    record = _write_record(store, category="reagent_bottle", features=[rim],
                           points=camera_points, transform=transform)
    legacy = OracleSimulatorTruthGraspProvider(store, gripper_geometry=GRIPPER)
    legacy.bind_records(lambda calibration_ref: {record["entity_ref"]: record})
    legacy_output = legacy.propose(_propose_request(record))
    assert len(legacy_output["candidates"]) == 8  # backward-compatible default count
    tilted = OracleSimulatorTruthGraspProvider(store, gripper_geometry=GRIPPER,
                                               tilt_angles=[0.0, 0.5236])
    tilted.bind_records(lambda calibration_ref: {record["entity_ref"]: record})
    tilted_output = tilted.propose(_propose_request(record))
    assert tilted.tilt_angles == (0.0, 0.5236)
    assert len(tilted_output["candidates"]) == 16
    assert [item["candidate_ref"] for item in tilted_output["candidates"]] == [
        f"candidate://simulator-truth-R01/{index}" for index in range(16)]
    # With outer fraction / inner tilt ordering, every len(tilts)-th candidate
    # is the tilt=0 pose; only candidate_ref differs (global numbering), so the
    # remaining snapshot fields must equal the legacy candidates bit-for-bit.
    for tilted_candidate, legacy_candidate in zip(tilted_output["candidates"][::2],
                                                  legacy_output["candidates"]):
        assert ({key: value for key, value in tilted_candidate.items() if key != "candidate_ref"}
                == {key: value for key, value in legacy_candidate.items() if key != "candidate_ref"})
    with pytest.raises(OracleGraspGeometryError, match="oracle tilt_angles_rad"):
        OracleSimulatorTruthGraspProvider(store, gripper_geometry=GRIPPER, tilt_angles=[2.0])


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
    # Preselection carries the truth-derived grasp orientation itself
    # (carry-as-grasped): transit_orient applies no world-frame reorientation.
    assert Rotation.from_matrix(captured[0][2][0][:3, :3]).as_quat() == pytest.approx([0., 0., 0., 1.])
    started = [value for kind, value in artifacts if kind == "acquire-search"
               and value.get("status") == "started"][0]
    assert started["policy"] == "simulator_truth_preselected"
    assert started["variant_count"] == 1
    assert route["acquire_route_selection"] == "simulator_truth_preselected"
    assert route["acquire_transit_clearance_m"] == pytest.approx(.04)
    assert route["acquire_transport_orientation_xyzw"] is None
    assert route["acquire_axial_symmetry_angle_rad"] == 0.0


def _preselected_model(artifacts, captured):
    """Bare IsaacPhaseMotion with the preselected policy and stubbed mechanisms."""
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
    model._artifact = lambda kind, data: artifacts.append((kind, data)) or "artifact://readiness/test.json"

    def qualify(waypoints, *_args, **_kwargs):
        captured.append(waypoints)
        return {"start_joints": [0.] * 7, "steps": [{"joints": [.2] + [0.] * 6, "stage": "lift"}]}

    model.qualify = qualify
    return model


def _preselected_target():
    return {
        "world_from_control": {"translation_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "entity_prim_path": "/World/R03/Model",
        "destination_prim_path": "/World/BEAKER/Model",
        "object_pose": {"position_m": [-.27, -.36, .82], "orientation_xyzw": [0., 0., 0., 1.]},
        "grasp_frame": {"position_m": [-.27, -.36, .86], "orientation_xyzw": [0., 0., 0., 1.]},
        "approach_direction": {"vector": [0., -1., 0.]},
        "destination_pose": {"position_m": [-.08, 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "return_pose": {"position_m": [-.27, -.36, .82], "orientation_xyzw": [0., 0., 0., 1.]},
    }


def test_preselected_policy_honours_matching_probe_variant_selection():
    artifacts, captured = [], []
    model = _preselected_model(artifacts, captured)
    model._probe_variant_selection = {
        "candidate://R03/0": {
            "scene_revision": "scene",
            "axial_symmetry_angle_rad": np.pi / 2,
            "approach_distance_m": .18,
        },
        "candidate://R03/other": {
            "scene_revision": "scene",
            "axial_symmetry_angle_rad": 0.,
            "approach_distance_m": .12,
        },
    }
    target = _preselected_target()
    target["candidate_ref"] = "candidate://R03/0"
    observation_model = {"grasp_symmetry": {"kind": "axial", "axis_world": [0., 0., 1.],
                                            "origin_world": [-.27, -.36, .82]}}
    route, _evidence = model.prepare({"manipulation_target": target, "observation_model": observation_model,
                                      "scene_revision": "scene"})
    assert len(captured) == 1
    # The probe-validated azimuth and approach distance are the preselected
    # answer, not the first configured element of either dimension.
    assert route["acquire_axial_symmetry_angle_rad"] == pytest.approx(np.pi / 2)
    assert route["acquire_approach_distance_m"] == pytest.approx(.18)


def test_preselected_policy_falls_back_when_probe_selection_identity_drifts():
    artifacts, captured = [], []
    model = _preselected_model(artifacts, captured)
    model._probe_variant_selection = {
        "candidate://R03/9": {
            "scene_revision": "scene",
            "axial_symmetry_angle_rad": np.pi / 2,
            "approach_distance_m": .18,
        },
    }
    target = _preselected_target()
    target["candidate_ref"] = "candidate://R03/0"
    observation_model = {"grasp_symmetry": {"kind": "axial", "axis_world": [0., 0., 1.],
                                            "origin_world": [-.27, -.36, .82]}}
    route, _evidence = model.prepare({"manipulation_target": target, "observation_model": observation_model,
                                      "scene_revision": "scene"})
    assert route["acquire_axial_symmetry_angle_rad"] == 0.0


def test_preselected_policy_falls_back_without_probe_selection():
    artifacts, captured = [], []
    model = _preselected_model(artifacts, captured)
    target = _preselected_target()
    target["candidate_ref"] = "candidate://R03/0"
    observation_model = {"grasp_symmetry": {"kind": "axial", "axis_world": [0., 0., 1.],
                                            "origin_world": [-.27, -.36, .82]}}
    route, _evidence = model.prepare({"manipulation_target": target, "observation_model": observation_model,
                                      "scene_revision": "scene"})
    assert route["acquire_axial_symmetry_angle_rad"] == 0.0
