import jsonschema
import pytest
from PhyAgentOS.planning import project_tool_spec

from pick_place_workflow.object_acquire import ACQUIRE_TOOL_SPEC
from pick_place_workflow.object_place import PLACE_TOOL_SPEC
from pick_place_workflow.persistent_runtime import (
    PersistentActionEndpoint,
    PersistentPossession,
    _ProjectedDriver,
    _spec,
)


def arguments(place=False):
    value = {"observation_ref": "observation://scene/camera", "scene_revision": "scene", "frame_id": "camera",
             "calibration_ref": "artifact://scene/calibration", "freshness_ms": 0, "max_age_ms": 1000,
             "candidate_set_ref": "candidate-set://scene/camera", "preparation_ref": "preparation://scene/camera",
             "candidate_ref": "candidate://red/0", "entity_ref": "entity://red",
             "capability_snapshot_ref": "artifact://scene/capability", "assignment_ref": "artifact://scene/assignment"}
    if place:
        value.update(acquire_invocation_ref="invocation://object-acquire/1", destination_ref="destination://red-slot")
    return value


@pytest.mark.parametrize("phase,spec", [("acquire", ACQUIRE_TOOL_SPEC), ("place", PLACE_TOOL_SPEC)])
def test_persistent_results_conform_to_published_live_schema(phase, spec):
    class Driver:
        def poll(self):
            return {"status": "succeeded", "outcome_known": True, "world_change_started": True,
                    "new_scene_revision": "scene-2", "artifact_refs": ["artifact://scene/action"]}
    result = _ProjectedDriver(Driver(), phase, arguments(phase == "place")).poll()
    live = _spec(spec)
    jsonschema.validate(result, live["output_schema"]["properties"]["result"])
    policy = project_tool_spec(live)
    assert "object.relocate" in policy.capabilities
    assert policy.input_binding_keys == (("entity_ref", "destination_ref") if phase == "place" else ("entity_ref",))


def test_owner_from_gateway_caller_is_stable_across_revision_and_record():
    seen = []
    class Client:
        def start(self, phase, invocation, owner, resolved):
            seen.append(owner)
            return object()
    endpoint = PersistentActionEndpoint("acquire", Client(), lambda phase, request: {
        **request, "assignment": {"task_id": "task-1", "assignment_ref": request["assignment_ref"]}})
    for caller in ("paos:task-1:revision-1:record-1", "paos:task-1:revision-2:record-9"):
        admission = endpoint.admit_for_caller(arguments(), caller_id=caller)
        assert not seen or seen == ["paos:task-1"]
        admission.start("invocation", "attempt")
    assert seen == ["paos:task-1", "paos:task-1"]
    with pytest.raises(ValueError, match="caller"):
        endpoint.admit_for_caller(arguments(), caller_id="diagnostic")
    with pytest.raises(ValueError, match="this task"):
        endpoint.admit_for_caller(arguments(), caller_id="paos:other:revision:record")


def test_composition_registers_all_seven_required_tools():
    from pick_place_workflow.persistent_runtime import build_persistent_runtime

    class Providers:
        def describe(self, request):
            return None

        def understand(self, request):
            return None

        def propose(self, request):
            return None

        def prepare(self, request):
            return None

    provider = Providers()
    runtime = build_persistent_runtime(
        client=object(), understanding_provider=provider, grasp_provider=provider,
        preparation_provider=provider, capability_provider=provider,
        resolve_preparation=lambda phase, request: request,
        tool_context_provider=lambda tool_id: {"ready": False, "binding_error": "not started"},
    )
    assert {tool["tool_id"] for tool in runtime.list_tools()["tools"]} == {
        "scene.observe", "scene.understand", "grasp.propose", "manipulation.capabilities",
        "manipulation.prepare", "object.acquire", "object.place",
    }
    assert all(runtime.get_context(tool["tool_id"])["ready"] is False for tool in runtime.list_tools()["tools"])


def test_unknown_place_cannot_produce_semantic_completion_evidence():
    class Driver:
        def poll(self):
            return {"status": "succeeded", "outcome_known": False, "artifact_refs": ["artifact://scene/partial"]}

    result = _ProjectedDriver(Driver(), "place", arguments(True)).poll()
    assert result["status"] == "unknown"
    assert result["evidence_refs"] == ["artifact://scene/partial"]
    assert result["capability_outcome_summary"]["post_release_evidence"]["availability"] == "none"


def test_evidence_free_success_does_not_complete_relocate():
    class Driver:
        def poll(self):
            return {"status": "succeeded", "outcome_known": True, "world_change_started": True}

    result = _ProjectedDriver(Driver(), "place", arguments(True)).poll()
    assert result["status"] == "unknown"
    assert result["evidence_refs"] == []
    assert result["capability_outcome_summary"]["outcome_known"] is False
    assert result["capability_outcome_summary"]["world_change_started"] is True


def test_persistent_possession_requires_acquire_then_matching_place():
    possession = PersistentPossession()
    possession.begin("acquire", owner="paos:task", entity_ref="entity://red")
    assert possession.state == "acquiring"
    possession.settle("acquire", {"status": "succeeded", "outcome_known": True, "world_change_started": True})
    assert possession.state == "holding"
    with pytest.raises(ValueError, match="does not match"):
        possession.validate_begin("place", owner="paos:other", entity_ref="entity://red", acquire_ref=None)
    possession.acquire_invocation_ref = "invocation://object-acquire/abc"
    possession.validate_begin("place", owner="paos:task", entity_ref="entity://red", acquire_ref="invocation://object-acquire/abc")
    possession.begin("place", owner="paos:task", entity_ref="entity://red", acquire_ref="invocation://object-acquire/abc")
    assert possession.state == "placing"
    possession.settle("place", {"status": "succeeded", "outcome_known": True, "world_change_started": True})
    assert possession.state == "empty"


def test_uncertain_possession_blocks_second_acquire_and_preserves_owner():
    possession = PersistentPossession()
    possession.begin("acquire", owner="paos:task", entity_ref="entity://red")
    possession.settle("acquire", {"status": "unknown", "outcome_known": False, "world_change_started": True})
    assert possession.state == "uncertain"
    with pytest.raises(ValueError, match="not admissible"):
        possession.validate_begin("acquire", owner="paos:task", entity_ref="entity://blue")
    assert possession.owner == "paos:task"
    assert possession.entity_ref == "entity://red"


def test_cancel_or_stop_without_physical_confirmation_does_not_release():
    possession = PersistentPossession()
    possession.begin("acquire", owner="paos:task", entity_ref="entity://red")
    possession.settle("acquire", {"status": "cancelled", "outcome_known": False, "world_change_started": True})
    assert possession.state == "uncertain"
