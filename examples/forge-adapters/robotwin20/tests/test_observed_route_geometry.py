"""Observation estimates may differ from actor truth without becoming stale."""

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_simulation_probe_worker as probe
from robotwin_planning_geometry import ObservedGeometryActor, _table_top_z
from test_grounding import pose, setup


@pytest.mark.parametrize("change", [None, "actor_drift", "model_tamper", "size_tamper", "missing_binding"])
def test_observed_route_checks_its_model_and_independent_runtime_drift(monkeypatch, change):
    captured = np.eye(4)
    captured[:2, :2] = [[0, -1], [1, 0]]
    captured[0, 3] = .007
    current = captured.copy()
    model = {"world_T_object": np.eye(4).reshape(-1).tolist(), "half_extents_m": [.03] * 3}
    actor = SimpleNamespace(get_pose=lambda: SimpleNamespace(to_transformation_matrix=lambda: current))
    task = SimpleNamespace(_paos_observed_bindings={
        "entity://observed": {"model": model, "captured_pose": captured.tolist()}})
    monkeypatch.setattr(probe, "_actor_for_entity", lambda *args: actor)
    candidate = {"entity_ref": "entity://observed", "attached_object": {"object_frame_id": "observed-envelope/observed"}}
    artifacts = {"transform": {"world_T_object": model["world_T_object"].copy()},
                 "geometry": {"half_extents_m": model["half_extents_m"].copy()}}
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
    np.save(tmp_path / "capture/support.npy", [[-.5, -.4, .73], [.5, .4, .75], [.2, .1, .74]])
    b = g.bind(request)
    support = g._observed_support(g.bindings[b["binding_ref"]])
    assert support["position_m"] == pytest.approx([0, 0, .74])
    assert support["half_extents_m"] == pytest.approx([.5, .4, .01])
    task = SimpleNamespace(_paos_observed_support=support)
    assert _table_top_z(task) == pytest.approx(.75)
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
