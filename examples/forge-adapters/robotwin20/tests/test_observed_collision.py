from itertools import product

import numpy as np
import pytest

from robotwin20_adapter.observed_collision import (
    ObservedCollisionPolicy,
    depth_points,
    inside_convex,
    local_contact,
    visibility_counts,
    voxel_boxes,
)


def box(low, high):
    return np.array(list(product(*zip(low, high))))


def test_support_refinement_retains_all_points_and_uncertainty_without_grid_overfill():
    from robotwin20_adapter.observed_collision import voxel_boxes

    points = np.array([[.001, .001, .7405], [.012, .003, .7417],
                       [.018, .009, .748], [.041, .004, .79]])
    coarse, count = voxel_boxes(points, .01, .001)
    refined, new_count = voxel_boxes(points, .01, .001, support_z=.7417, refinement_band=.02)
    assert new_count >= count
    for point in points:
        assert any(np.all(point - .001 >= np.array(b["position_m"]) - b["half_extents_m"] - 1e-12)
                   and np.all(point + .001 <= np.array(b["position_m"]) + b["half_extents_m"] + 1e-12)
                   for b in refined)
    # Mixed higher points remain, rather than flattening a row onto the table.
    assert max(b["position_m"][2] + b["half_extents_m"][2] for b in refined[1:]) == pytest.approx(.750)
    assert refined[0] == coarse[-1]
    assert all(b["half_extents_m"][2] < coarse[0]["half_extents_m"][2] for b in refined[1:])
    # A high return elsewhere in the old merged row no longer inflates support
    # under a different cell; occupied high returns themselves are still kept.
    support = [b for b in refined if abs(b["position_m"][0] - .005) < .001]
    assert max(b["position_m"][2] + b["half_extents_m"][2] for b in support) == pytest.approx(.742)


def gripper():
    return {"panda_hand": [box([-.03, -.05, -.02], [.03, .05, 0])],
            "panda_leftfinger": [box([-.01, -.05, .01], [.01, -.04, .06])],
            "panda_rightfinger": [box([-.01, .04, .01], [.01, .05, .06])]}


def test_local_contact_does_not_require_whole_object_to_fit_aperture():
    target = np.array([[0, 0, .03], [0, .01, .04], [0, -.01, .04], [.2, .3, .04]])
    result = local_contact(target, np.empty((0, 3)), gripper(), approach_delta=np.array([0, 0, -.08]), policy=ObservedCollisionPolicy())
    assert result["status"] == "valid"
    assert result["inner_target_points"] == 3
    assert result["hidden_surface_geometry"] == "unknown"


@pytest.mark.parametrize("point,label", [([0, 0, -.01], "target_panda_hand"),
                                        ([0, .045, .04], "target_panda_rightfinger"),
                                        ([0, .045, -.06], "target_panda_rightfinger")])
def test_solid_and_approach_sweep_collisions_reject(point, label):
    target = np.array([[0, 0, .03], [0, .01, .04], [0, -.01, .04], point])
    result = local_contact(target, np.empty((0, 3)), gripper(), approach_delta=np.array([0, 0, -.08]), policy=ObservedCollisionPolicy())
    assert label + "_approach_collision" in result["rejection_reasons"]


def test_unclassified_environment_is_not_exempt_and_empty_contact_rejects():
    result = local_contact(np.empty((0, 3)), np.array([[0, 0, -.01]]), gripper(), approach_delta=np.zeros(3), policy=ObservedCollisionPolicy())
    assert "environment_panda_hand_approach_collision" in result["rejection_reasons"]
    assert "insufficient_observed_inner_contact" in result["rejection_reasons"]


def test_actual_convex_volume_not_its_box_and_uncertainty_margin():
    tetra = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    points = np.array([[.8, .8, .8], [.1, .1, .1], [-.0005, .1, .1]])
    assert inside_convex(points, tetra).tolist() == [False, True, False]
    assert inside_convex(points, tetra, .001).tolist() == [False, True, True]


def test_voxel_merging_preserves_every_occupied_cell_without_bridging_gaps():
    points = np.array([[.001, .001, .001], [.011, .001, .001], [.031, .001, .001], [-.001, .011, .001]])
    boxes, count = voxel_boxes(points, .01, .001)
    assert count == 4
    assert len(boxes) == 3
    def covered(point):
        return any(np.all(np.abs(point - b["position_m"]) <= np.array(b["half_extents_m"]) + 1e-12) for b in boxes)
    assert all(covered(p) for p in points)
    assert not covered(np.array([.025, .005, .005]))


def test_depth_projection_keeps_unclassified_valid_points():
    depth = np.array([[1000., 0], [np.nan, 2000.]])
    transform = np.eye(4)
    transform[0, 3] = .5
    points, ys, xs = depth_points(depth, np.eye(3), transform, .001)
    assert points.tolist() == [[.5, 0, 1], [2.5, 2, 2]]
    assert ys.tolist() == xs.tolist() == [0, 1]


def test_depth_visibility_distinguishes_free_surface_occluded_and_missing():
    points = np.array([[0, 0, .5], [0, 0, 1], [0, 0, 2], [10, 0, 1], [0, 0, -1]])
    assert visibility_counts(points, np.ones((2, 2)), np.eye(3), np.eye(4), 1., .001) == {
        "observed_free_samples": 1, "surface_band_samples": 1, "occluded_samples": 1, "unobserved_samples": 2}
