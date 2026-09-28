import numpy as np
import pytest
from test_route_inputs import _facts

from robotwin20_adapter.collision_world import build_collision_world, validate_collision_world
from robotwin20_adapter.observed_support import estimate_support, estimate_support_from_depth


def test_support_does_not_raise_whole_table_to_outlier_or_discard_obstacle():
    plane = np.array([[x, y, .74] for x in np.linspace(-.4, .4, 12) for y in np.linspace(-.3, .3, 12)])
    points = np.vstack([plane, [[.1, .1, .765], [-.1, -.1, .71]]])
    support = estimate_support(points, "artifact://observed/support")
    assert sum((support["position_m"][2], support["half_extents_m"][2])) == pytest.approx(.741)
    assert support["estimation"]["residual_count"] == 2
    for point in points[-2:]:
        assert any(np.all(abs(point - box["position_m"]) <= np.array(box["half_extents_m"]) + 1e-12)
                   for box in support["residual_boxes"])
    facts = _facts()
    facts.update(geometry_source="observation", support_surface=support)
    refs = {item["entity_ref"]: "artifact://geometry/" + str(i) for i, item in enumerate(facts["objects"])}
    world = build_collision_world(facts, target_entity_ref=facts["objects"][0]["entity_ref"],
        source_scene_facts_ref="artifact://scene/facts", geometry_refs=refs, calibration_ref=facts["calibration_ref"])
    validate_collision_world(world)
    residuals = [o for o in world["obstacles"] if "observed-support-residual" in o["entity_ref"]]
    assert len(residuals) == 2
    assert all(o["geometry_ref"] == support["evidence_ref"] for o in residuals)


def test_depth_support_excludes_observed_masks_and_keeps_all_sources():
    depth = np.full((10, 10), 740.0)
    mask = np.zeros((10, 10), dtype=bool)
    mask[4:6, 4:6] = True
    depth[mask] = 180.0
    support = estimate_support_from_depth(
        depth,
        [[100.0, 0.0, 4.5], [0.0, 100.0, 4.5], [0.0, 0.0, 1.0]],
        np.eye(4),
        [mask],
        "artifact://scene/depth",
        excluded_mask_refs=["artifact://scene/block-mask"],
    )

    assert support["estimation"]["point_count"] == 96
    assert support["estimation"]["height_m"] == pytest.approx(0.74)
    assert support["source_refs"] == ["artifact://scene/depth", "artifact://scene/block-mask"]


def test_depth_support_rejects_unaligned_masks_and_missing_provenance():
    depth = np.full((8, 8), 740.0)
    with pytest.raises(ValueError, match="differs from scene depth"):
        estimate_support_from_depth(depth, np.eye(3), np.eye(4), [np.zeros((7, 8))], "artifact://depth",
                                    excluded_mask_refs=["artifact://mask"])
    with pytest.raises(ValueError, match="provenance is invalid"):
        estimate_support_from_depth(depth, np.eye(3), np.eye(4), [np.zeros_like(depth)], "artifact://depth")


def test_depth_support_rejects_sparse_unmasked_evidence():
    depth = np.full((8, 8), 740.0)
    mask = np.ones_like(depth, dtype=bool)
    mask[:2, :2] = False
    with pytest.raises(ValueError, match="insufficient unmasked depth"):
        estimate_support_from_depth(depth, np.eye(3), np.eye(4), [mask], "artifact://depth",
                                    excluded_mask_refs=["artifact://mask"])


def test_depth_support_rejects_empty_instance_mask():
    depth = np.full((8, 8), 740.0)
    with pytest.raises(ValueError, match="instance mask is empty"):
        estimate_support_from_depth(depth, np.eye(3), np.eye(4), [np.zeros_like(depth, dtype=bool)],
                                    "artifact://depth", excluded_mask_refs=["artifact://mask"])


@pytest.mark.parametrize("kind", ["few", "line", "tilted", "nonfinite"])
def test_unsupported_support_geometry_is_not_flattened(kind):
    points = np.array([[x, y, .74] for x in np.linspace(-.4, .4, 12) for y in np.linspace(-.3, .3, 12)])
    if kind == "few":
        points = points[:2]
    elif kind == "line":
        points[:, 1] = 0
    elif kind == "tilted":
        points[:, 2] += .4 * points[:, 0]
    else:
        points[0, 2] = np.nan
    with pytest.raises(ValueError):
        estimate_support(points, "artifact://observed/support")
