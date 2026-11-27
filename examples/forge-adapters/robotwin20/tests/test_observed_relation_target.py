import json
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
from robotwin_blocks_ranking_adapter import StackBlocksThreeTaskAdapter
from test_route_inputs import _facts

from robotwin20_adapter.grounding import IDENTITY_KEYS, Grounding
from robotwin20_adapter.observed_relation_target import ObservedRelationTargetProvider
from robotwin20_adapter.route_evidence import _artifact_path
from robotwin20_adapter.route_inputs import CURRENT_SCENE_FACTS_SCHEMA_VERSION


def observed_scene(tmp_path, *, identity=None, moving_execution=2, grounding=None):
    identity = identity or dict(scene_revision="s1", observation_ref="observation://s1/camera",
                                calibration_ref="artifact://capture/calibration")
    frame = identity["observation_ref"].rsplit("/", 1)[1]
    transform = np.eye(4)
    transform[:3, 3] = [.1, .2, .05]
    calibration = tmp_path.joinpath(identity["calibration_ref"].removeprefix("artifact://")).with_suffix(".json")
    calibration.parent.mkdir(parents=True, exist_ok=True)
    calibration.write_text(json.dumps({"camera_name": frame, "extrinsic_cv": np.linalg.inv(transform).tolist(),
                                      "intrinsic_cv": [[80., 0., 29.5], [0., 80., 29.5], [0., 0., 1.]]}))
    capture = tmp_path / "capture"
    capture.mkdir(exist_ok=True)
    np.save(capture / "depth.npy", np.full((60, 60), 740.), allow_pickle=False)
    visual = {index: "entity://red-block" if index == moving_execution else f"entity://visual-{index}"
              for index in (1, 2, 3)}
    understanding = {**identity, "status": "available", "frame": {"frame_id": frame, "unit": "m"},
                     "entities": [], "spatial_envelopes": [], "derived_artifacts": [], "ambiguities": []}
    facts = _facts()
    facts.update(identity, schema_version=CURRENT_SCENE_FACTS_SCHEMA_VERSION, objects=[])
    for index in (1, 2, 3):
        center = np.array([-.2 + .2 * (index - 1), 0., .82])
        extent = .035 if index != moving_execution else .015
        pose = np.eye(4)
        pose[:3, 3] = center
        obj = deepcopy(_facts()["objects"][0])
        obj.update(entity_ref=f"entity://stack-block-{index}", actor_name=f"block{index}",
                   world_T_object=pose.reshape(-1).tolist(), world_T_functional_point=pose.reshape(-1).tolist(),
                   half_extents_m=[.04] * 3)
        for key in ("world_T_object_target", "world_T_functional_target", "target_ref"):
            obj.pop(key, None)
        facts["objects"].append(obj)
        ref = visual[index]
        camera_center = center - transform[:3, 3]
        understanding["entities"].append({"entity_ref": ref, "category": "block", "confidence": .95})
        cloud_ref = f"artifact://capture/cloud-{index}"
        understanding["spatial_envelopes"].append({"entity_ref": ref, "frame_id": frame, "unit": "m",
            "min_xyz_m": (camera_center - extent).tolist(), "max_xyz_m": (camera_center + extent).tolist(),
            "confidence": .95, "provenance": [cloud_ref]})
        xy = np.array([(x, y) for x in np.linspace(-extent, extent, 11)
                       for y in np.linspace(-extent, extent, 11)])
        world = np.c_[xy + center[:2], np.full(len(xy), center[2] + extent)]
        np.save(capture / f"cloud-{index}.npy", world - transform[:3, 3], allow_pickle=False)
        mask = np.zeros((60, 60), dtype=bool)
        mask[20:23, index * 10:index * 10 + 3] = True
        np.save(capture / f"mask-{index}.npy", mask, allow_pickle=False)
        understanding["derived_artifacts"].extend([
            {"kind": "object_point_cloud", "artifact_ref": cloud_ref, "entity_ref": ref,
             **identity, "frame_id": frame, "provenance": [cloud_ref]},
            {"kind": "instance_mask", "artifact_ref": f"artifact://capture/mask-{index}",
             "entity_ref": ref, **identity, "frame_id": frame, "provenance": [cloud_ref]},
            {"kind": "object_geometry", "artifact_ref": f"artifact://capture/model-{index}",
             "entity_ref": ref, **identity, "frame_id": frame, "provenance": [cloud_ref],
             "descriptor": {"dimensions_m": [extent * 2] * 3}},
        ])
    if grounding is None:
        calls = []
        def query(operation, arguments, **kwargs):
            calls.append(operation)
            assert operation in {"snapshot", "bind_observed_entities"}
            return {"scene_revision": identity["scene_revision"], "scene_validity": "action_driven",
                    "holding_state": "empty"}
        grounding = Grounding(SimpleNamespace(query=query, calls=calls), tmp_path, lambda _: deepcopy(facts),
                              goal_source="benchmark_task_definition")
    grounding.source = lambda _: deepcopy(facts)
    grounding.goal_source = "benchmark_task_definition"
    grounding.bindings.clear()
    if "_observed_support" in grounding.__dict__:
        del grounding.__dict__["_observed_support"]
    observation = {**identity, "status": "available", "frame": {"frame_id": frame},
                   "captured_at": "2026-11-26T00:00:00Z", "artifacts": [
                       {"kind": "depth", "ref": "artifact://capture/depth", **identity, "frame_id": frame}]}
    grounding.remember("scene.observe", observation)
    grounding.remember("scene.understand", understanding)
    bound = grounding.bind({**identity, "entity_refs": list(visual.values())})
    provider = ObservedRelationTargetProvider(grounding, task_name="stack_blocks_three")
    request = {**identity, "frame_id": frame, "binding_ref": bound["binding_ref"],
               "entity_ref": visual[moving_execution], "goal_relation": "on", "freshness_ms": 0,
               "max_age_ms": 1000, "relation_target_ref": visual[1] if moving_execution == 2 else "surface://table"}
    return SimpleNamespace(provider=provider, grounding=grounding, request=request, bound=bound,
                           understanding=understanding, facts=facts, visual=visual)


@pytest.mark.parametrize("moving_execution", [1, 2])
def test_real_binding_observed_target_and_benchmark_goal_projection(tmp_path, moving_execution):
    state = observed_scene(tmp_path, moving_execution=moving_execution)
    goals = StackBlocksThreeTaskAdapter().goal_facts(None, seed=0)
    goals["goal_ref"] = "artifact://task/goal"
    original = deepcopy(goals)
    projection = state.provider.project_relation_goal(goals,
        subtask_id="place_base" if moving_execution == 1 else "place_middle",
        binding_ref=state.bound["binding_ref"], identity=state.request)
    assert goals == original
    assert projection["entity_ref"] == "entity://red-block"
    assert len(projection["scene_entity_refs"]) == 3
    saved = json.loads(_artifact_path(tmp_path, projection["evidence_refs"][-1]).read_text())
    assert saved["source_goal"] == goals
    assert saved["execution_entity_ref"] == f"entity://stack-block-{moving_execution}"
    result = state.provider.propose(state.request)
    candidate = result["candidates"][0]
    evidence = json.loads(_artifact_path(tmp_path, candidate["evidence_refs"][0]).read_text())
    assert result["entity_ref"] == "entity://red-block"
    assert evidence["geometry_source"] == "observation"
    assert len(evidence["execution_mappings"]) == 3
    assert evidence["query"] == state.request
    assert evidence["calibration_ref"] == state.request["calibration_ref"]
    assert evidence["depth_ref"] == "artifact://capture/depth"
    if moving_execution == 2:
        # Non-unit camera pose is applied, and actor half extents (.04) are not used.
        np.testing.assert_allclose(np.asarray(candidate["world_T_object_target"])[[3, 7, 11]], [-.2, 0., .871])
    assert set(state.grounding.client.calls) <= {"snapshot", "bind_observed_entities"}


def test_observed_top_plane_remains_available_with_dense_side_geometry(tmp_path):
    state = observed_scene(tmp_path)
    cloud = tmp_path / "capture/cloud-1.npy"
    top = np.load(cloud)
    side = np.repeat(top, 5, axis=0)
    side[:, 2] -= np.tile(np.linspace(.01, .05, 5), len(top))
    np.save(cloud, np.concatenate([top, side]))
    result = state.provider.propose(state.request)
    assert result["status"] == "available"
    np.testing.assert_allclose(np.asarray(result["candidates"][0]["world_T_object_target"])[[3, 7, 11]],
                               [-.2, 0., .871])


@pytest.mark.parametrize("change", ["missing_binding", "stale", "frame", "duplicate_execution", "missing_cloud",
                                    "cloud_lineage", "calibration", "sparse", "tilt", "contaminated", "small"])
def test_observed_target_rejects_evidence_without_publishing(tmp_path, change):
    state = observed_scene(tmp_path)
    binding = state.grounding.bindings[state.bound["binding_ref"]]
    cloud = tmp_path / "capture/cloud-1.npy"
    points = np.load(cloud)
    if change == "missing_binding":
        state.request["binding_ref"] = "artifact://fake/binding"
    elif change == "stale":
        state.request["scene_revision"] = "new-scene"
    elif change == "frame":
        state.request["frame_id"] = "other"
    elif change == "duplicate_execution":
        binding["bindings"][1]["execution_entity_ref"] = binding["bindings"][0]["execution_entity_ref"]
    elif change == "missing_cloud":
        cloud.unlink()
    elif change == "cloud_lineage":
        key = tuple(state.request[name] for name in IDENTITY_KEYS)
        state.grounding.understandings[key]["derived_artifacts"][0]["scene_revision"] = "old"
    elif change == "calibration":
        path = _artifact_path(tmp_path, state.request["calibration_ref"])
        data = json.loads(path.read_text())
        data["extrinsic_cv"][0][3] += .1
        path.write_text(json.dumps(data))
    elif change == "sparse":
        np.save(cloud, points[:10])
    elif change == "tilt":
        points[:, 2] += (points[:, 0] - points[:, 0].mean()) * .1
        np.save(cloud, points)
    elif change == "contaminated":
        points[0, 2] += .03
        np.save(cloud, points)
    elif change == "small":
        points[:, :2] = (points[:, :2] - points[:, :2].mean(0)) * .1 + points[:, :2].mean(0)
        np.save(cloud, points)
    with pytest.raises((ValueError, OSError)):
        state.provider.propose(state.request)
    assert not (tmp_path / "relation-target-evidence").exists()
