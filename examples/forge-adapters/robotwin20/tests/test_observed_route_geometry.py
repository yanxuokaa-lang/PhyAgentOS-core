"""Observation estimates may differ from actor truth without becoming stale."""

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_simulation_probe_worker as probe
from robotwin_planning_geometry import ObservedGeometryActor, _table_top_z
from test_grounding import pose, setup


def cloud_model(tmp_path, *, padding=0.):
    from itertools import product

    g, request, facts = setup(tmp_path)
    u = next(iter(g.understandings.values()))
    transform = np.eye(4)
    angle = np.pi / 4
    transform[:3, :3] = [[1, 0, 0], [0, np.cos(angle), -np.sin(angle)], [0, np.sin(angle), np.cos(angle)]]
    world = np.array(list(product([-.02, .02], [-.03, .03], [-.01, .01])))
    cloud = world @ transform[:3, :3]
    np.save(tmp_path / "capture/points.npy", cloud)
    u["spatial_envelopes"][0].update(min_xyz_m=(cloud.min(0) - padding).tolist(), max_xyz_m=(cloud.max(0) + padding).tolist())
    u["derived_artifacts"][0]["descriptor"] = {"shape_class": "box_envelope", "orientation_reliable": False,
        "dimensions_m": (np.ptp(cloud, axis=0) + 2 * padding).tolist()}
    u["derived_artifacts"].append({**{k: request[k] for k in ("scene_revision", "observation_ref", "calibration_ref")},
        "entity_ref": "entity://seen", "frame_id": "camera", "kind": "object_point_cloud", "artifact_ref": "artifact://capture/points"})
    return g, u, transform, world, facts


@pytest.mark.parametrize("padding", [0., .003])
def test_cloud_model_transforms_points_before_bounds_and_preserves_padding(tmp_path, padding):
    g, u, transform, world, facts = cloud_model(tmp_path, padding=padding)
    result = g._project_visual_geometry(["entity://seen"], {"entity://seen": facts["objects"][0]}, u, transform)["entity://seen"]
    model = np.asarray(result["world_T_object"]).reshape(4, 4)
    assert model == pytest.approx(np.eye(4))
    expected = np.ptp(world, axis=0) / 2 + np.abs(transform[:3, :3]) @ np.full(3, padding)
    assert result["half_extents_m"] == pytest.approx(expected)
    assert result["object_frame_id"] == "observed-envelope/world/seen"
    assert np.all(np.abs(world - model[:3, 3]) <= np.array(result["half_extents_m"]) + 1e-12)


@pytest.mark.parametrize("fault", ["stale", "frame", "duplicate", "nonfinite", "empty"])
def test_invalid_claimed_cloud_cannot_fall_back_to_envelope(tmp_path, fault):
    g, u, transform, _, facts = cloud_model(tmp_path)
    artifact = u["derived_artifacts"][-1]
    if fault == "stale":
        artifact["scene_revision"] = "old"
    elif fault == "frame":
        artifact["frame_id"] = "wrong"
    elif fault == "duplicate":
        u["derived_artifacts"].append(deepcopy(artifact))
    else:
        np.save(tmp_path / "capture/points.npy", [[float("nan"), 0, 0]] if fault == "nonfinite" else np.empty((0, 3)))
    with pytest.raises(ValueError, match="cloud"):
        g._project_visual_geometry(["entity://seen"], {"entity://seen": facts["objects"][0]}, u, transform)


def test_cloud_model_keeps_outliers_and_does_not_override_custom_shape(tmp_path):
    g, u, transform, _, facts = cloud_model(tmp_path)
    points = np.load(tmp_path / "capture/points.npy")
    np.save(tmp_path / "capture/points.npy", np.vstack([points, [1., 0., 0.]]))
    result = g._project_visual_geometry(["entity://seen"], {"entity://seen": facts["objects"][0]}, u, transform)["entity://seen"]
    assert result["half_extents_m"][0] >= .51
    u["derived_artifacts"][0]["descriptor"]["shape_class"] = "custom_shape"
    result = g._project_visual_geometry(["entity://seen"], {"entity://seen": facts["objects"][0]}, u, transform)["entity://seen"]
    assert result["object_frame_id"] == "observed-envelope/seen"


@pytest.mark.parametrize("change", [None, "actor_drift", "model_tamper", "size_tamper", "missing_binding"])
@pytest.mark.parametrize("model_frame", ["observed-envelope/observed", "observed-envelope/world/observed"])
def test_observed_route_checks_its_model_and_independent_runtime_drift(monkeypatch, change, model_frame):
    captured = np.eye(4)
    captured[:2, :2] = [[0, -1], [1, 0]]
    captured[0, 3] = .007
    current = captured.copy()
    model = {"world_T_object": np.eye(4).reshape(-1).tolist(), "half_extents_m": [.03] * 3}
    actor = SimpleNamespace(get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: current))
    task = SimpleNamespace(_paos_observed_bindings={
        "entity://observed": {"model": model, "captured_pose": captured.tolist()}})
    monkeypatch.setattr(probe, "_actor_for_entity", lambda *args: actor)
    candidate = {"entity_ref": "entity://observed", "attached_object": {"object_frame_id": model_frame}}
    artifacts = {"transform": {"world_T_object": model["world_T_object"].copy()},
                 "geometry": {"source": "observed_envelope",
                              "half_extents_m": model["half_extents_m"].copy()}}
    if change == "actor_drift":
        current[0, 3] += .01
    elif change == "model_tamper":
        artifacts["transform"]["world_T_object"][3] += .01
    elif change == "size_tamper":
        artifacts["geometry"]["half_extents_m"][0] += .01
    elif change == "missing_binding":
        task._paos_observed_bindings = {}
    if change is None:
        probe._validate_runtime_route_input_binding(task, candidate, artifacts)
        assert artifacts["transform"]["world_T_object"] == np.eye(4).reshape(-1).tolist()
    else:
        with pytest.raises(probe.SimulationProbeError):
            probe._validate_runtime_route_input_binding(task, candidate, artifacts)


def test_oracle_actor_route_uses_actor_geometry_even_with_observed_identity_binding(monkeypatch):
    actor_pose = np.eye(4)
    actor_pose[0, 3] = 0.2
    actor = SimpleNamespace(
        get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: actor_pose)
    )
    task = SimpleNamespace(
        _paos_observed_bindings={
            "entity://observed": {
                "model": {
                    "world_T_object": np.eye(4).reshape(-1).tolist(),
                    "half_extents_m": [0.03] * 3,
                },
                "captured_pose": np.eye(4).tolist(),
            }
        }
    )
    monkeypatch.setattr(probe, "_actor_for_entity", lambda *_args: actor)
    candidate = {
        "entity_ref": "entity://observed",
        "attached_object": {"object_frame_id": "block-green-1"},
    }
    artifacts = {
        "transform": {"world_T_object": actor_pose.reshape(-1).tolist()},
        "geometry": {
            "source": "sapien_collision_shape",
            "half_extents_m": [0.02] * 3,
        },
    }

    probe._validate_runtime_route_input_binding(task, candidate, artifacts)


def test_planner_pose_view_has_only_observed_geometry():
    matrix = np.eye(4)
    matrix[:3, 3] = [.1, .2, .3]
    model = ObservedGeometryActor(matrix)
    matrix[0, 3] = 99
    assert model.get_pose().p.tolist() == [.1, .2, .3]
    assert model.get_pose().q.tolist() == [1, 0, 0, 0]


def test_missing_observation_obstacle_never_falls_back_to_hidden_geometry(tmp_path):
    g, request, facts = setup(tmp_path)
    hidden = deepcopy(facts["objects"][0])
    hidden.update(entity_ref="entity://hidden", actor_name="block2", world_T_object=pose(1))
    facts["objects"].append(hidden)
    b = g.bind(request)
    t = g.target(dict(binding_ref=b["binding_ref"], entity_ref="entity://seen",
                      frame_id="world", unit="m", frame_T_object_target=pose(.2)))
    with pytest.raises(RuntimeError, match="observed collision coverage"):
        g.scene_facts({**request, "intent": {"entity_ref": "entity://seen"},
                       "destination_ref": t["destination_ref"]})


def test_support_bounds_come_from_metric_cloud_not_simulator(tmp_path):
    g, request, _ = setup(tmp_path)
    u = next(iter(g.understandings.values()))
    u["relations"] = [{"subject_ref": "entity://seen", "predicate": "on", "object_ref": "entity://support"}]
    identity = {k: request[k] for k in ("observation_ref", "scene_revision", "calibration_ref")}
    u["derived_artifacts"].append({**identity, "entity_ref": "entity://support", "frame_id": "camera",
                                   "kind": "object_point_cloud", "artifact_ref": "artifact://capture/support"})
    cloud = [[x, y, .74] for x in np.linspace(-.5, .5, 8) for y in np.linspace(-.4, .4, 8)]
    np.save(tmp_path / "capture/support.npy", cloud)
    b = g.bind(request)
    support = g._observed_support(g.bindings[b["binding_ref"]])
    assert support["position_m"] == pytest.approx([0, 0, .74])
    assert support["half_extents_m"] == pytest.approx([.5, .4, .001])
    task = SimpleNamespace(_paos_observed_support=support)
    assert _table_top_z(task) == pytest.approx(.741)
    task._paos_observed_support = None
    with pytest.raises(probe.SimulationProbeError, match="observed support"):
        _table_top_z(task)


def test_observed_support_projection_keeps_provenance_outside_planner_shape():
    from robotwin_curobo_world_port import bind_scene_table

    support = {"position_m": [0, 0, .7], "orientation_wxyz": [1, 0, 0, 0],
               "half_extents_m": [.5, .4, .02], "evidence_ref": "artifact://observed/support"}
    task = SimpleNamespace(_paos_observed_support=support,
                           robot=SimpleNamespace(left_planner=SimpleNamespace(), right_planner=SimpleNamespace()))
    bind_scene_table(task)  # No simulator table exists in this fixture.
    projected = task.robot.left_planner._paos_table_world_pose
    assert set(projected) == {"position_m", "orientation_wxyz", "half_extents_m"}
    assert projected["position_m"] == support["position_m"]
    assert support["evidence_ref"] == "artifact://observed/support"
