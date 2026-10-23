from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

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
    def __init__(
        self,
        *,
        scene: str = "scene-1",
        mismatch: str | None = None,
        preparation_status: str = "available",
        preparation_candidate_ref: str | None = None,
    ):
        self.observation, self.understanding, self.grasp, self.capability = _chain(scene=scene)
        self.mismatch = mismatch
        self.preparation_status = preparation_status
        self.preparation_candidate_ref = preparation_candidate_ref
        self.calls: list[str] = []

    def __call__(self, tool_id, arguments):
        self.calls.append(tool_id)
        if tool_id == "manipulation.prepare":
            candidate = arguments["candidates"][0]
            return {
                "status": self.preparation_status,
                "observation_ref": self.observation["observation_ref"],
                "scene_revision": self.observation["scene_revision"],
                "frame": self.observation["frame"],
                "calibration_ref": self.observation["calibration_ref"],
                "preparation_ref": "preparation://scene-1/camera-front",
                "candidate_set_ref": arguments["candidate_set_ref"],
                "motion_authorized": False,
                "prepared_candidates": [{
                    "candidate_ref": self.preparation_candidate_ref or candidate["candidate_ref"],
                    "entity_ref": candidate["entity_ref"],
                    "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
                    "evidence": ["artifact://readiness/scene-1/candidate-0"],
                    "qualification": "prepared",
                }],
            }
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


@pytest.mark.asyncio
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_binding_projects_understanding_envelope_through_real_grasp_endpoint(asynchronous):
    from PhyAgentOS.forge.capability_runtime.grasp_proposal import GraspProposalEndpoint

    query = QueryChain()
    for envelope in query.understanding["spatial_envelopes"]:
        envelope["provenance"] = [query.observation["artifacts"][0]["ref"]]
    candidates = query.grasp["candidates"]
    endpoint = GraspProposalEndpoint(SimpleNamespace(propose=lambda request: {
        "candidates": candidates, "ambiguities": [],
        "funnel": dict.fromkeys(("decoded", "canonicalized", "deduplicated", "retained"), 1),
        "produced_evidence_refs": candidates[0]["provenance"],
    }))

    def invoke(tool_id, arguments):
        if tool_id == "grasp.propose":
            result = endpoint.invoke(arguments)
            assert result["status"] == "available", result
            return result
        return query(tool_id, arguments)

    async def invoke_async(tool_id, arguments):
        return invoke(tool_id, arguments)

    adapter = PerceptionBindingAdapter(invoke_async if asynchronous else invoke, BindingRequest(
        sensor_refs=("sensor://front",), source_category="reagent_a", destination_category="beaker", max_age_ms=1000))
    binding = await adapter.bind_async() if asynchronous else adapter.bind()
    assert binding.entity_ref == "entity://reagent-a"


def test_refresh_uses_previous_entity_instead_of_shared_adapter_initial_selector():
    query = QueryChain()
    original_request = BindingRequest(sensor_refs=("sensor://front",), source_category="reagent_a",
                                      destination_category="beaker", max_age_ms=1000)
    adapter = PerceptionBindingAdapter(query, original_request)
    first = adapter.bind()
    previous_b = first.model_copy(update={"entity_ref": "entity://reagent-b", "category": "reagent_b"})
    query.observation, query.understanding, query.grasp, query.capability = _chain(scene="scene-2")
    query.understanding["entities"].extend([
        {"entity_ref": "entity://reagent-b", "category": "reagent_b", "confidence": .95},
        {"entity_ref": "entity://distractor", "category": "reagent_b", "confidence": .95},
    ])
    query.understanding["spatial_envelopes"].append({
        **query.understanding["spatial_envelopes"][0], "entity_ref": "entity://reagent-b"})
    query.grasp["candidates"][0]["entity_ref"] = "entity://reagent-b"
    refreshed = adapter.refresh_binding(previous_b, "scene-2")
    assert refreshed.entity_ref == "entity://reagent-b"
    assert refreshed.destination_ref == first.destination_ref
    assert refreshed.scene_revision == "scene-2"
    assert adapter.request == original_request


@pytest.mark.parametrize("stale_stage", [None, "understanding", "grasp", "capability"])
def test_refresh_accepts_new_capture_calibration_but_rejects_mixed_query_lineage(stale_stage):
    query = QueryChain()
    adapter = PerceptionBindingAdapter(query, BindingRequest(
        sensor_refs=("sensor://front",), source_category="reagent_a",
        destination_category="beaker", max_age_ms=1000))
    previous = adapter.bind()
    query.observation, query.understanding, query.grasp, query.capability = _chain(scene="scene-2")
    for name in ("observation", "understanding", "grasp", "capability"):
        getattr(query, name)["calibration_ref"] = "artifact://calibration/new-capture"
    if stale_stage:
        getattr(query, stale_stage)["calibration_ref"] = previous.calibration_ref
        with pytest.raises(PerceptionBindingError, match="changed calibration provenance"):
            adapter.refresh_binding(previous, "scene-2")
    else:
        refreshed = adapter.refresh_binding(previous, "scene-2")
        assert refreshed.entity_ref == previous.entity_ref
        assert refreshed.calibration_ref == "artifact://calibration/new-capture"


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


class AlternateQueryProvider:
    """Independent provider implementation using the object Query port."""

    def __init__(self):
        self.calls: list[str] = []

    def invoke_query(self, endpoint_id, operation, arguments):
        del arguments
        self.calls.append(f"{endpoint_id}:{operation}")
        observation = {
            "status": "available",
            "observation_ref": "observation://mujo/overhead-01",
            "scene_revision": "mujo-scene-7",
            "frame": {"frame_id": "overhead-01", "unit": "m"},
            "calibration_ref": "artifact://calibration/mujo-v2",
            "freshness_ms": 7,
            "artifacts": [{"ref": "artifact://mujo/rgbd/7", "kind": "rgbd"}],
        }
        entities = [
            {"entity_ref": "entity://sample-vial-07", "category": "sample_vial", "confidence": 0.94},
            {"entity_ref": "entity://mixing-vessel-02", "category": "mixing_vessel", "confidence": 0.97},
        ]
        envelopes = [
            {"entity_ref": "entity://sample-vial-07", "frame_id": "overhead-01", "unit": "m",
             "min_xyz_m": [0.2, 0.1, 0.0], "max_xyz_m": [0.28, 0.18, 0.16], "confidence": 0.92},
            {"entity_ref": "entity://mixing-vessel-02", "frame_id": "overhead-01", "unit": "m",
             "min_xyz_m": [0.5, 0.2, 0.0], "max_xyz_m": [0.68, 0.4, 0.22], "confidence": 0.95},
        ]
        identity = {
            "observation_ref": observation["observation_ref"],
            "scene_revision": observation["scene_revision"],
            "frame": observation["frame"],
            "calibration_ref": observation["calibration_ref"],
        }
        if operation == "observe":
            return {**observation}
        if operation == "understand":
            return {"status": "available", **identity, "entities": entities, "spatial_envelopes": envelopes}
        if operation == "propose":
            return {
                "status": "available", **identity,
                "candidate_set_ref": "candidate-set://mujo-scene-7/overhead-01",
                "candidates": [{
                    "candidate_ref": "candidate://mujo-scene-7/sample-vial-07/0",
                    "entity_ref": "entity://sample-vial-07",
                    "grasp_frame": {"frame_id": "overhead-01", "unit": "m",
                                    "position_m": [0.24, 0.14, 0.08],
                                    "orientation_xyzw": [0.0, 0.0, 0.707, 0.707]},
                    "approach_direction": {"frame_id": "overhead-01", "unit": "unitless",
                                             "vector": [0.0, 0.0, -1.0]},
                    "score": 0.88, "confidence": 0.9,
                    "provenance": ["artifact://mujo/grasp/7/0"],
                    "qualification": "proposed",
                }],
            }
        if operation == "describe":
            return {
                "status": "available", "snapshot_ref": "artifact://capabilities/mujo-scene-7",
                "observation_ref": observation["observation_ref"],
                "scene_revision": observation["scene_revision"],
                "calibration_ref": observation["calibration_ref"], "motion_authorized": False,
            }
        raise AssertionError(f"unexpected Query operation: {operation}")


class AlternatePreparationProvider:
    """Preparation provider with a different interface and reference scheme."""

    def __init__(self):
        self.requests: list[dict] = []

    def prepare_binding(self, request):
        self.requests.append(deepcopy(request))
        candidate = request["candidates"][0]
        return {
            "status": "prepared",
            "observation_ref": request["observation_ref"],
            "scene_revision": request["scene_revision"],
            "frame": {"frame_id": request["frame_id"], "unit": "m"},
            "calibration_ref": request["calibration_ref"],
            "preparation_ref": "preparation://mujo-scene-7/arm-2",
            "candidate_set_ref": request["candidate_set_ref"],
            "candidate_ref": candidate["candidate_ref"],
            "destination_ref": request["destination_ref"],
            "assignment_ref": "artifact://assignments/mujo-scene-7/arm-2",
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
    return PerceptionBindingAdapter(query, request), query, preparation


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
    assert preparation.requests == []
    assert binding.binding_ref == "artifact://observations/scene-1/rgb"


def test_runtime_bound_adapter_stays_provider_neutral_before_subtask_selection():
    query = QueryChain()
    adapter, _, preparation = _adapter(query=query)

    class RuntimeQueryPort:
        def __init__(self):
            self.calls = []

        def invoke_query(self, endpoint_id, operation, arguments):
            self.calls.append((endpoint_id, operation))
            endpoint_to_tool = {
                ("scene_observation", "observe"): "scene.observe",
                ("scene_understanding", "understand"): "scene.understand",
                ("grasp_proposal", "propose"): "grasp.propose",
                ("manipulation_capabilities", "describe"): "manipulation.capabilities",
            }
            tool_id = endpoint_to_tool.get((endpoint_id, operation))
            if tool_id is not None:
                return query(tool_id, arguments)
            if (endpoint_id, operation) == ("manipulation_preparation", "prepare"):
                return query("manipulation.prepare", arguments)
            raise AssertionError(f"unexpected Runtime endpoint: {endpoint_id}:{operation}")

    runtime = RuntimeQueryPort()
    adapter.with_query_invoker(runtime).bind()

    assert runtime.calls == [
        ("scene_observation", "observe"),
        ("scene_understanding", "understand"),
        ("grasp_proposal", "propose"),
        ("manipulation_capabilities", "describe"),
    ]
    assert preparation.requests == []


def test_runtime_bound_adapter_does_not_query_preparation_before_assignment():
    query = QueryChain(preparation_status="unavailable")
    adapter, _, preparation = _adapter(query=query)

    adapter.with_query_invoker(query).bind()
    assert preparation.requests == []


def test_runtime_bound_adapter_does_not_validate_preparation_candidate_before_assignment():
    query = QueryChain(preparation_candidate_ref="candidate://scene-1/other")
    adapter, _, preparation = _adapter(query=query)

    adapter.with_query_invoker(query).bind()
    assert preparation.requests == []


def test_adapter_is_reusable_with_an_independent_provider_implementation():
    query = AlternateQueryProvider()
    preparation = AlternatePreparationProvider()
    adapter = PerceptionBindingAdapter(
        query,
        BindingRequest(
            sensor_refs=("camera/overhead-01",),
            source_category="sample_vial",
            destination_category="mixing_vessel",
            max_age_ms=1000,
        ),
    )

    binding = adapter.bind()

    assert query.calls == [
        "scene_observation:observe",
        "scene_understanding:understand",
        "grasp_proposal:propose",
        "manipulation_capabilities:describe",
    ]
    assert binding.entity_ref == "entity://sample-vial-07"
    assert binding.destination_ref == "destination://mixing-vessel-02"
    assert binding.scene_revision == "mujo-scene-7"
    assert binding.candidate_ref == "candidate://mujo-scene-7/sample-vial-07/0"
    assert preparation.requests == []


def test_adapter_rejects_semantic_ambiguity_without_motion():
    adapter, _, _ = _adapter(duplicate_source=True)
    with pytest.raises(PerceptionBindingError, match="ambiguous"):
        adapter.bind()


def test_adapter_rejects_mixed_query_provenance():
    adapter, _, _ = _adapter(QueryChain(mismatch="grasp.propose"))
    with pytest.raises(PerceptionBindingError, match="changed scene revision"):
        adapter.bind()


def test_adapter_does_not_consume_preparation_from_another_scene_revision():
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
    adapter.bind()


def test_adapter_refresh_requires_expected_revision_and_same_semantic_targets():
    adapter, _, _ = _adapter()
    previous = adapter.bind()
    adapter.query_invoker = QueryChain(scene="scene-2")
    with pytest.raises(PerceptionBindingError, match="differs from the execution revision"):
        adapter.refresh_binding(previous, "scene-3")


def test_adapter_is_not_ready_without_all_provider_ports():
    request = BindingRequest(("camera/front",), "reagent_a", "beaker", 1000)
    adapter = PerceptionBindingAdapter(None, request)
    assert adapter.ready is False
    with pytest.raises(PerceptionBindingError, match="providers"):
        adapter.bind()
