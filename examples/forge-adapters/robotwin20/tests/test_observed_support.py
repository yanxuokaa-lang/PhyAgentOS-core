import numpy as np
import pytest
from test_route_inputs import _facts

from robotwin20_adapter.collision_world import build_collision_world, validate_collision_world
from robotwin20_adapter.observed_support import estimate_support


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
