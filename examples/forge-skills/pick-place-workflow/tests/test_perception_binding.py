from __future__ import annotations

from copy import deepcopy

import pytest

from pick_place_workflow.perception_binding import (
    BindingRequest,
    PerceptionBindingAdapter,
    PerceptionBindingError,
)


def _chain(*, scene: str = "scene-1", duplicate_source: bool = False):
    observation = {
        "status": "available",
        "observation_ref": f"observation://{scene}/camera-front",
        "scene_revision": scene,
        "frame": {"frame_id": "camera-front", "unit": "m"},
        "calibration_ref": "artifact://calibration/lab-v1",
        "freshness_ms": 4,
        "artifacts": [
            {"ref": f"artifact://observations/{scene}/rgb", "kind": "rgb", "media_type": "image/png"}
        ],
    }
    entities = [
        {"entity_ref": "entity://reagent-a", "category": "reagent_a", "confidence": 0.95},
        {"entity_ref": "entity://beaker-1", "category": "beaker", "confidence": 0.99},
    ]
    if duplicate_source:
        entities.append({"entity_ref": "entity://reagent-a-2", "category": "reagent_a", "confidence": 0.9})
    understanding = {
        "status": "available",
        "observation_ref": observation["observation_ref"],
        "scene_revision": scene,
        "frame": observation["frame"],
        "calibration_ref": observation["calibration_ref"],
        "entities": entities,
        "spatial_envelopes": [
            {"entity_ref": "entity://reagent-a", "frame_id": "camera-front", "unit": "m",
             "min_xyz_m": [0.1, 0.1, 0.0], "max_xyz_m": [0.2, 0.2, 0.2], "confidence": 0.93},
            {"entity_ref": "entity://beaker-1", "frame_id": "camera-front", "unit": "m",
             "min_xyz_m": [0.4, 0.1, 0.0], "max_xyz_m": [0.6, 0.3, 0.2], "confidence": 0.96},
        ],
    }
    candidate_set = f"candidate-set://{scene}/camera-front"
    grasp = {
        "status": "available",
        "observation_ref": observation["observation_ref"],
        "scene_revision": scene,
        "frame": observation["frame"],
        "calibration_ref": observation["calibration_ref"],
        "candidate_set_ref": candidate_set,
        "candidates": [{
            "candidate_ref": f"candidate://{scene}/reagent-a-0",
            "entity_ref": "entity://reagent-a",
            "grasp_frame": {"frame_id": "camera-front", "unit": "m",
                             "position_m": [0.15, 0.15, 0.1],
                             "orientation_xyzw": [0.0, 0.0, 0.0, 1.0]},
            "approach_direction": {"frame_id": "camera-front", "unit": "unitless", "vector": [0.0, 0.0, -1.0]},
            "score": 0.9,
            "confidence": 0.91,
            "provenance": [f"artifact://grasp/{scene}/candidate-0"],
            "qualification": "proposed",
        }],
    }
    capability = {
        "status": "available",
        "snapshot_ref": f"artifact://capabilities/{scene}/snapshot",
        "observation_ref": observation["observation_ref"],
        "scene_revision": scene,
        "calibration_ref": observation["calibration_ref"],
        "motion_authorized": False,
    }
    return observation, understanding, grasp, capability


class QueryChain:
    def __init__(self, *, scene: str = "scene-1", mismatch: str | None = None):
        self.observation, self.understanding, self.grasp, self.capability = _chain(scene=scene)
        self.mismatch = mismatch
        self.calls: list[str] = []

    def __call__(self, tool_id, arguments):
        self.calls.append(tool_id)
        result = {
            "scene.observe": self.observation,
            "scene.understand": self.understanding,
            "grasp.propose": self.grasp,
            "manipulation.capabilities": self.capability,
        }[tool_id]
        result = deepcopy(result)
        if tool_id == self.mismatch:
            result["scene_revision"] = "other-scene"
        return result


class Preparation:
    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(deepcopy(request))
        candidate = request["candidates"][0]
        return {
            "status": "available",
            "observation_ref": request["observation_ref"],
            "scene_revision": request["scene_revision"],
            "frame": {"frame_id": request["frame_id"], "unit": "m"},
            "calibration_ref": request["calibration_ref"],
            "preparation_ref": "preparation://scene-1/camera-front",
            "candidate_set_ref": request["candidate_set_ref"],
            "candidate_ref": candidate["candidate_ref"],
            "destination_ref": request["destination_ref"],
            "assignment_ref": "artifact://assignments/scene-1/arm-a",
        }


def _adapter(query=None, preparation=None, *, duplicate_source=False):
    query = query or QueryChain()
    preparation = preparation or Preparation()
    request = BindingRequest(
        sensor_refs=("camera/front",),
        source_category="reagent_a",
        destination_category="beaker",
        max_age_ms=1000,
    )
    if duplicate_source:
        query.understanding = _chain(duplicate_source=True)[1]
    return PerceptionBindingAdapter(query, preparation, request), query, preparation


def test_adapter_composes_queries_and_returns_measured_binding():
    adapter, query, preparation = _adapter()
    binding = adapter.bind()
    assert query.calls == [
        "scene.observe", "scene.understand", "grasp.propose", "manipulation.capabilities"
    ]
    assert binding.entity_ref == "entity://reagent-a"
    assert binding.destination_ref == "destination://beaker-1"
    assert binding.measured_pose["position_m"] == [0.15000000000000002, 0.15000000000000002, 0.1]
    assert binding.measured_geometry["size_m"] == [0.1, 0.1, 0.2]
    assert binding.candidate_ref == "candidate://scene-1/reagent-a-0"
    assert preparation.requests[0]["source_entity"]["entity_ref"] == "entity://reagent-a"


def test_adapter_rejects_semantic_ambiguity_without_motion():
    adapter, _, _ = _adapter(duplicate_source=True)
    with pytest.raises(PerceptionBindingError, match="ambiguous"):
        adapter.bind()


def test_adapter_rejects_mixed_query_provenance():
    adapter, _, _ = _adapter(QueryChain(mismatch="grasp.propose"))
    with pytest.raises(PerceptionBindingError, match="changed scene revision"):
        adapter.bind()


def test_adapter_rejects_preparation_from_another_scene_revision():
    adapter, _, _ = _adapter(preparation=lambda request: {
        "status": "available",
        "observation_ref": request["observation_ref"],
        "scene_revision": "old-scene",
        "frame": {"frame_id": request["frame_id"], "unit": "m"},
        "calibration_ref": request["calibration_ref"],
        "preparation_ref": "preparation://old-scene/camera-front",
        "candidate_set_ref": request["candidate_set_ref"],
        "candidate_ref": request["candidates"][0]["candidate_ref"],
        "destination_ref": request["destination_ref"],
        "assignment_ref": "artifact://assignments/old/arm-a",
    })
    with pytest.raises(PerceptionBindingError, match="preparation changed observation provenance"):
        adapter.bind()


def test_adapter_refresh_requires_expected_revision_and_same_semantic_targets():
    adapter, _, _ = _adapter()
    previous = adapter.bind()
    adapter.query_invoker = QueryChain(scene="scene-2")
    with pytest.raises(PerceptionBindingError, match="differs from the execution revision"):
        adapter.refresh_binding(previous, "scene-3")


def test_adapter_is_not_ready_without_all_provider_ports():
    request = BindingRequest(("camera/front",), "reagent_a", "beaker", 1000)
    adapter = PerceptionBindingAdapter(None, None, request)
    assert adapter.ready is False
    with pytest.raises(PerceptionBindingError, match="providers"):
        adapter.bind()
