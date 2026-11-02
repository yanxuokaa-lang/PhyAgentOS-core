from itertools import product
from types import SimpleNamespace

import numpy as np
import pytest

from isaacsim_lab.finger_collision import convex_slice_boxes, cooked_convex_points


def wedge():
    # A sloping finger: the whole-box low corner is unoccupied.
    return np.array([[x, y, z] for x, z in ((0., 0.), (.04, .04), (0., .04))
                     for y in (-.005, .005)])


def test_slices_remove_empty_corner_and_cover_convex_interior_and_full_sweep():
    points = wedge()
    boxes = convex_slice_boxes(points, .003)
    # This supporting plane separates the real solid from a nearby surface.
    normal = np.array([-1., 0., 1.]) / np.sqrt(2.)
    minima = [min(np.dot(p, normal) for p in product(*zip(lo, hi))) for lo, hi in boxes]
    assert min(minima) > -.003
    whole_min = min(np.dot(p, normal) for p in product(*zip(points.min(0), points.max(0))))
    assert whole_min < -.02
    rng = np.random.default_rng(7)
    weights = rng.dirichlet(np.ones(len(points)), 2000)
    interior = weights @ points
    assert all(any(np.all(p >= lo - 1e-10) and np.all(p <= hi + 1e-10)
                   for lo, hi in boxes) for p in np.vstack((points, interior)))
    # Full prismatic travel is covered, including intermediate openings.
    travel = np.array([0., .04, 0.])
    for opening in np.linspace(0., 1., 7):
        assert all(any(np.all(p >= lo - 1e-10) and np.all(p <= hi + travel + 1e-10)
                       for lo, hi in boxes) for p in interior + opening * travel)


def test_slice_crossing_edges_are_retained_even_without_vertices_in_slice():
    points = np.array(list(product((-.01, .01), (-.01, .01), (0., .10))))
    boxes = convex_slice_boxes(points, .01)
    assert len(boxes) == 10
    for index, (lo, hi) in enumerate(boxes):
        assert lo == pytest.approx([-.01, -.01, index * .01], abs=2e-10)
        assert hi == pytest.approx([.01, .01, (index + 1) * .01], abs=2e-10)


@pytest.mark.parametrize('points,step', [([], .01), ([[0, 0, 0]] * 4, .01),
                                       ([[0, 0, float('nan')]] * 4, .01), (wedge(), 0)])
def test_invalid_convex_evidence_rejects(points, step):
    with pytest.raises(ValueError):
        convex_slice_boxes(points, step)


def test_cooking_receipt_is_copied_synchronously_and_keeps_all_components():
    calls = []
    def request(**kwargs):
        calls.append(kwargs)
        kwargs['on_result']('valid', [SimpleNamespace(vertices=wedge()),
                                     SimpleNamespace(vertices=wedge() + .1)])
    parts = cooked_convex_points(request, 12, 34, 'valid')
    assert len(parts) == 2
    assert calls[0]['run_asynchronously'] is False
    assert calls[0]['stage_id'] == 12 and calls[0]['collision_prim_id'] == 34
    np.testing.assert_allclose(parts[1], wedge() + .1)


@pytest.mark.parametrize('mode', ['missing', 'failed', 'empty', 'invalid'])
def test_cooking_failure_never_becomes_an_empty_clear_shape(mode):
    def request(**kwargs):
        if mode != 'missing':
            kwargs['on_result']('bad' if mode == 'failed' else 'valid',
                                [] if mode == 'empty' else
                                [SimpleNamespace(vertices=[[0, 0, float('nan')]])])
    with pytest.raises(ValueError):
        cooked_convex_points(request, 12, 34, 'valid')


def test_existing_collision_route_removes_empty_corner_but_keeps_margin_contact(monkeypatch):
    import sys
    import types

    from scipy.spatial.transform import Rotation

    from isaacsim_lab.phase_motion import IsaacPhaseMotion, PhaseMotionError, pose_matrix

    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = {'workspace_min_m': [-1.] * 3, 'workspace_max_m': [1.] * 3,
                    'collision_margin_m': .003}
    model.hand_from_tcp = np.eye(4)
    model.robot = SimpleNamespace(prim_path='/robot')
    model.spheres = []
    model.tcp = lambda _q: pose_matrix([0., 0., .01], Rotation.from_euler('y', np.pi / 4).as_quat())
    calls = []
    support_z = 0.

    def overlap_box(half, center, quaternion, report, _any):
        rotation = Rotation.from_quat(quaternion).as_matrix()
        calls.append((half, center))
        if center[2] - np.abs(rotation[2]) @ half <= support_z:
            report(SimpleNamespace(collision='/table'))

    carb = types.ModuleType('carb')
    carb.Float3 = carb.Float4 = lambda *v: v
    physx = types.ModuleType('omni.physx')
    physx.get_physx_scene_query_interface = lambda: SimpleNamespace(overlap_box=overlap_box)
    monkeypatch.setitem(sys.modules, 'carb', carb)
    monkeypatch.setitem(sys.modules, 'omni.physx', physx)

    def geometry(boxes):
        return [(1, np.array(list(product(*zip(lo, hi)))), np.eye(4), np.eye(4), 1, (0., .04))
                for lo, hi in boxes]

    model.finger_geometry = geometry([(wedge().min(0), wedge().max(0))])
    with pytest.raises(PhaseMotionError, match='finger overlaps'):
        model._collisions(np.zeros(7), '/source', False, False, np.eye(4))
    boxes = convex_slice_boxes(wedge(), .003)
    model.finger_geometry = geometry(boxes)
    calls.clear()
    model._collisions(np.zeros(7), '/source', False, False, np.eye(4))
    assert len(calls) == len(boxes)
    # The solid is 10 mm above support; increasing support to 6 mm must
    # reject due to the unchanged 3 mm per-axis padding, before solid contact.
    support_z = .006
    with pytest.raises(PhaseMotionError) as caught:
        model._collisions(np.zeros(7), '/source', False, False, np.eye(4))
    assert caught.value.diagnostics['collision_margin_m'] == .003
    assert caught.value.diagnostics['finger_opening_mode'] == 'full_travel_sweep'


def test_sliced_finger_covers_transformed_solid_and_measured_opening_uncertainty():
    from scipy.spatial.transform import Rotation

    from isaacsim_lab.phase_motion import IsaacPhaseMotion, pose_matrix

    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = {'position_tolerance_m': .002}
    model.robot = SimpleNamespace(get_joint_positions=lambda: np.array([.02]), get_dof_index=lambda _: 0)
    parent = pose_matrix([.01, -.02, .03], Rotation.from_euler('xyz', [.3, .2, .1]).as_quat())
    child = pose_matrix([.01, .02, .03], Rotation.from_euler('x', -.4).as_quat())
    model.finger_geometry = [(1, np.array(list(product(*zip(lo, hi)))), parent, child, 1, (0., .04))
                             for lo, hi in convex_slice_boxes(wedge(), .003)]
    points = np.random.default_rng(3).dirichlet(np.ones(6), 200) @ wedge()
    for measured, limits in ((False, (0., .04)), (True, (.018, .022))):
        boxes = list(model.finger_boxes(measured=measured))
        for opening in np.linspace(*limits, 5):
            shift = np.eye(4)
            shift[1, 3] = opening
            transform = parent @ shift @ np.linalg.inv(child)
            transformed = points @ transform[:3, :3].T + transform[:3, 3]
            assert all(any(np.all(p >= lo - 1e-9) and np.all(p <= hi + 1e-9)
                           for lo, hi in boxes) for p in transformed)
