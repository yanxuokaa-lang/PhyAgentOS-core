import numpy as np
import pytest
from diagnose_observed_contact import adjacent, aligned_cloud, bounds, local_visible_geometry


def test_pixel_correspondence_excludes_invalid_depth_and_rejects_reordering():
    depth = np.array([[1., 0.], [np.nan, 2.]])
    mask = np.ones((2, 2), bool)
    cloud = np.array([[0, 0, 1], [2, 2, 2.]])
    ys, xs, residual = aligned_cloud(mask, depth, np.eye(3), cloud, 1.)
    assert ys.tolist() == [0, 1]
    assert xs.tolist() == [0, 1]
    assert residual == 0
    with pytest.raises(ValueError, match="ordering"):
        aligned_cloud(mask, depth, np.eye(3), cloud[::-1], 1.)
    with pytest.raises(ValueError, match="subsampled"):
        aligned_cloud(mask, depth, np.eye(3), cloud[:1], 1.)


def test_support_adjacency_does_not_wrap_image_edges():
    mask = np.zeros((4, 4), bool)
    mask[0, 0] = True
    result = adjacent(mask)
    assert result.sum() == 3
    assert not result[-1, -1]


def test_local_geometry_retains_all_points_and_reports_empty_neighborhood():
    points = np.array([[0, -.02, 0], [0, .02, 0], [.2, .3, .4]])
    original = points.copy()
    hand = {"position_m": [0, 0, 0], "orientation_xyzw": [0, 0, 0, 1]}
    result = local_visible_geometry(points, hand, np.zeros(3), [.01])
    assert result["all_visible_hand_bounds"]["count"] == 3
    assert result["neighborhoods"][0]["count"] == 2
    assert result["neighborhoods"][0]["closing_width_m"] == pytest.approx(.04)
    assert np.array_equal(points, original)
    empty = local_visible_geometry(points, hand, np.ones(3), [.01])["neighborhoods"][0]
    assert empty["count"] == 0
    assert empty["closing_width_m"] is None
    assert bounds(np.empty((0, 3)))["span_m"] is None


def test_local_geometry_respects_hand_frame_rotation():
    points = np.array([[-.02, 0, 0], [.02, 0, 0]])
    hand = {"position_m": [0, 0, 0], "orientation_xyzw": [0, 0, np.sqrt(.5), np.sqrt(.5)]}
    result = local_visible_geometry(points, hand, np.zeros(3), [.005])
    assert result["neighborhoods"][0]["count"] == 2
    assert result["neighborhoods"][0]["closing_width_m"] == pytest.approx(.04)
