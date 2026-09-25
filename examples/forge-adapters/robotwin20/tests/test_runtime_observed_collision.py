import json
from itertools import product
from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_observed_collision as observed
from robotwin_planning_geometry import SimulationProbeError, _validate_gripper_table_clearance

from robotwin20_adapter.observed_collision import ObservedCollisionPolicy


def test_released_mesh_encloses_all_observed_points_uncertainty_and_release_sweep():
    from scipy.spatial import ConvexHull

    points = np.array(list(product([-.02, .02], [-.01, .01], [-.015, .015])))
    source = np.eye(4)
    source[:3, 3] = [.3, -.2, .8]
    scene = {"descriptor": {"target_entity_ref": "red"}, "target": points + source[:3, 3],
             "policy": ObservedCollisionPolicy(), "evidence": {"target_mask_ref": "mask"}}
    task = SimpleNamespace(_paos_observed_collision=scene)
    candidate = {"entity_ref": "red", "placement_target": {
        "target_object_pose": {"position_m": [-.1, .2, .8],
                               "orientation_xyzw": [0, 0, np.sqrt(.5), np.sqrt(.5)]},
        "release_clearance_m": .005},
        "execution_grasp": {"support_clear_direction": {"vector": [0, 0, 1]}}}
    mesh = observed.released_target_mesh(task, candidate, source.reshape(-1).tolist())
    vertices = np.array(mesh["vertices"])
    hull = ConvexHull(vertices)
    transformed = points @ np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]) + [-.1, .2, .8]
    for shift in (0., .005):
        for offset in product([-.001, .001], repeat=3):
            samples = transformed + [0, 0, shift] + offset
            assert np.max(samples @ hull.equations[:, :3].T + hull.equations[:, 3]) < 1e-10
    triangles = vertices[mesh["faces"]]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    assert np.all(np.sum(normals * (triangles.mean(axis=1) - vertices.mean(axis=0)), axis=1) > 0)
    assert mesh["source"] == scene["evidence"]
    candidate["entity_ref"] = "blue"
    with pytest.raises(ValueError, match="differs from observed collision binding"):
        observed.released_target_mesh(task, candidate, source.reshape(-1).tolist())


class Link:
    def __init__(self, position, name="panda_hand"):
        self.position = np.asarray(position, dtype=float)
        self.name = name

    def get_name(self):
        return self.name

    def get_pose(self):
        return SimpleNamespace(p=self.position, q=[1, 0, 0, 0])

    def get_collision_shapes(self):
        return [SimpleNamespace(get_vertices=lambda: np.array(list(product([-.1, .1], repeat=3))),
                                get_local_pose=lambda: SimpleNamespace(p=np.zeros(3), q=[1, 0, 0, 0]))]


def fixture_scene(tmp_path, monkeypatch):
    calibration = {"camera_name": "camera", "intrinsic_cv": np.eye(3).tolist(),
                   "extrinsic_cv": np.eye(4).tolist()}
    (tmp_path / "calibration").write_text(json.dumps(calibration))
    np.save(tmp_path / "depth.npy", [[1000., 1000., 1000., 0.]])
    np.save(tmp_path / "mask.npy", [[True, False, False, False]])
    monkeypatch.setattr(observed, "_artifact_path", lambda root, ref: root / ref)
    link = Link([2., 0., 1.])
    entity = SimpleNamespace(get_links=lambda: [link])
    task = SimpleNamespace(robot=SimpleNamespace(left_entity=entity, right_entity=entity,
                          left_planner=SimpleNamespace(), right_planner=SimpleNamespace()))
    descriptor = {"scene_revision": "scene", "target_entity_ref": "entity", "calibration_ref": "calibration",
                  "frame_id": "camera", "world_T_camera": np.eye(4).reshape(-1).tolist(),
                  "depth_ref": "depth", "target_mask_ref": "mask", "policy": ObservedCollisionPolicy().to_dict()}
    world = {key: descriptor[key] for key in ("scene_revision", "target_entity_ref", "calibration_ref")}
    world["observed_collision"] = descriptor
    return task, world, link


def test_full_depth_keeps_unclassified_environment_and_filters_only_measured_self(tmp_path, monkeypatch):
    task, world, link = fixture_scene(tmp_path, monkeypatch)
    observed.configure_observed_collision(task, world, tmp_path)
    scene = task._paos_observed_collision
    assert scene["target"].tolist() == [[0., 0., 1.]]
    assert scene["environment"].tolist() == [[1., 0., 1.]]
    assert scene["evidence"]["robot_self_points"] == 1
    assert task.robot.left_planner._paos_observed_collision is scene
    assert task.robot.right_planner._paos_observed_collision is scene
    observed.configure_observed_collision(task, world, tmp_path)
    assert task._paos_observed_collision is scene
    link.position[0] = 3.
    observed.configure_observed_collision(task, world, tmp_path)
    assert len(task._paos_observed_collision["environment"]) == 2


def test_target_self_conflict_and_stale_lineage_cannot_silently_drop_points(tmp_path, monkeypatch):
    task, world, link = fixture_scene(tmp_path, monkeypatch)
    link.position[0] = 0.
    with pytest.raises(ValueError, match="overlaps robot"):
        observed.configure_observed_collision(task, world, tmp_path)
    world["scene_revision"] = "later"
    with pytest.raises(ValueError, match="lineage"):
        observed.configure_observed_collision(task, world, tmp_path)


def test_missing_depth_fails_instead_of_using_actor_geometry(tmp_path, monkeypatch):
    task, world, _ = fixture_scene(tmp_path, monkeypatch)
    world["observed_collision"]["depth_ref"] = "missing"
    with pytest.raises(FileNotFoundError):
        observed.configure_observed_collision(task, world, tmp_path)


def test_actual_route_target_collision_restores_joints_on_rejection():
    qpos = np.arange(7, dtype=float)
    original = qpos.copy()
    links = [Link([0., 0., 1.], name) for name in ("panda_hand", "panda_leftfinger", "panda_rightfinger")]
    def set_qpos(value):
        qpos[:] = value
    entity = SimpleNamespace(get_links=lambda: links, get_qpos=lambda: qpos, set_qpos=set_qpos)
    task = SimpleNamespace(robot=SimpleNamespace(right_entity=entity),
                           _paos_observed_support={"position_m": [0., 0., 0.], "half_extents_m": [.5, .5, .1]},
                           _paos_observed_collision={"target": np.array([[0., 0., 1.]]), "policy": ObservedCollisionPolicy()})
    with pytest.raises(SimulationProbeError, match="observed target intersects"):
        _validate_gripper_table_clearance(task, "right", np.zeros((1, 7)), phase="contact")
    np.testing.assert_array_equal(qpos, original)
