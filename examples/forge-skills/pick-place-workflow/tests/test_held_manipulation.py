from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest
import yaml
from PhyAgentOS.forge.capability_runtime import CapabilityRuntimeError
from PhyAgentOS.planning import execute_argument_projection, project_tool_spec

from pick_place_workflow.held_manipulation import (
    POUR_TOOL_SPEC,
    PREPARE_HELD_TOOL_SPEC,
    STIR_TOOL_SPEC,
    HeldActionEndpoint,
    HeldPreparationEndpoint,
    project_result,
)
from pick_place_workflow.persistent_runtime import PersistentPossession, build_persistent_runtime

CALLER = "paos:task-1:revision-1:record-1"
ACQUIRE = "invocation://object-acquire/one"


def request(operation="pour", scene="scene-1", held=ACQUIRE):
    parameters = {"pour": {"tilt_rad": 1.7, "hold_s": 2.0},
                  "stir": {"radius_m": 0.015, "depth_m": 0.04, "turns": 2.0,
                           "duration_s": 4.0, "direction": "ccw"},
                  "place": {}}[operation]
    return {"entity_ref": "entity://bottle-a", "destination_ref": "destination://lab/beaker",
            "observation_ref": f"observation://{scene}/camera", "scene_revision": scene,
            "frame_id": "camera", "calibration_ref": "artifact://lab/calibration",
            "capability_snapshot_ref": "artifact://lab/capabilities", "acquire_invocation_ref": ACQUIRE,
            "held_invocation_ref": held, "operation": operation, "parameters": parameters,
            "freshness_ms": 0, "max_age_ms": 1000}


def possession():
    return PersistentPossession(state="holding", owner="paos:task-1", entity_ref="entity://bottle-a",
                                acquire_invocation_ref=ACQUIRE, last_invocation_ref=ACQUIRE,
                                scene_revision="scene-1")


class Provider:
    def __init__(self):
        self.routes = {}
        self.starts = []
        self.next_result = None
        self.pending = False
        self.cancelled = False
        self.fail_start = False

    def describe(self, request):
        raise AssertionError("unrelated capability Query was called")

    def prepare_held(self, args):
        prepared = {**deepcopy(args), "preparation_ref": f"preparation://lab/{len(self.routes)}",
                    "assignment_ref": "artifact://lab/assignment"}
        self.routes[prepared["preparation_ref"]] = deepcopy(prepared)
        return {"status": "available", "arguments": prepared}

    def resolve(self, phase, args):
        prepared = self.routes[args["preparation_ref"]]
        if args != prepared:
            raise ValueError("changed prepared arguments")
        return {**deepcopy(prepared), "assignment": {"task_id": "task-1", "assignment_ref": args["assignment_ref"]}}

    def start(self, phase, invocation, owner, args):
        self.starts.append((phase, invocation, owner, deepcopy(args)))
        if self.fail_start:
            raise OSError("lost acknowledgement")
        return self

    def poll(self):
        return None if self.pending else deepcopy(self.next_result)

    def cancel(self):
        self.cancelled = True

    def stop(self):
        self.cancel()


def measured(operation="pour", **changes):
    metrics = {"pour": {"aligned_hold_s": 2.1, "maximum_tilt_rad": 1.8},
               "stir": {"in_container_turns": 2.1, "in_container_duration_s": 4.1},
               "place": {"position_error_m": 0.001}}[operation]
    return {"status": "succeeded", "outcome_known": True, "world_change_started": True,
            "new_scene_revision": "scene-2", "artifact_refs": ["artifact://lab/measured"],
            "operation_completed": True, "measurements": metrics,
            "entity_ref": "entity://bottle-a", "destination_ref": "destination://lab/beaker",
            "possession_state": "empty" if operation == "place" else "holding",
            "returned_to_safe_pose": True, "release_confirmed": True, "retreat_completed": True,
            "clear_of_target": True, "observation_ready": True, **changes}


def runtime(provider, held):
    return build_persistent_runtime(
        client=provider, understanding_provider=object(), grasp_provider=object(),
        preparation_provider=object(), capability_provider=provider,
        resolve_preparation=provider.resolve, tool_context_provider=lambda _: {"ready": True},
        possession=held, held_preparation_provider=provider, resolve_held_preparation=provider.resolve,
    )


def prepare(rt, args):
    result = rt.invoke_query("held_preparation", "prepare", args)
    jsonschema.validate(result, PREPARE_HELD_TOOL_SPEC["output_schema"])
    return result["arguments"]


@pytest.mark.parametrize("operation,tool_id", [("pour", "object.pour"), ("stir", "tool.stir")])
def test_runtime_operation_then_fresh_return_placement(operation, tool_id):
    provider, held = Provider(), possession()
    rt = runtime(provider, held)
    args = prepare(rt, request(operation))
    assert not provider.starts  # Preparation is a Query.
    provider.next_result = measured(operation)
    invocation = rt.start_action(tool_id, args, caller_id=CALLER)["invocation_id"]
    assert held.state == "operating"
    result = rt.invocation_result(invocation)
    assert result["status"] == "succeeded"
    jsonschema.validate(result["result"], rt.get_tool(tool_id)["output_schema"]["properties"]["result"])
    assert held.state == "holding" and held.acquire_invocation_ref == ACQUIRE
    assert held.last_invocation_ref == invocation and held.scene_revision == "scene-2"
    with pytest.raises(CapabilityRuntimeError):
        rt.start_action(tool_id, args, caller_id=CALLER)
    returned = prepare(rt, request("place", "scene-2", invocation))
    provider.next_result = measured("place", new_scene_revision="scene-3")
    place_id = rt.start_action("object.place", returned, caller_id=CALLER)["invocation_id"]
    result = rt.invocation_result(place_id)
    jsonschema.validate(result["result"], rt.get_tool("object.place")["output_schema"]["properties"]["result"])
    assert result["status"] == "succeeded" and held.state == "empty"
    assert [item[0] for item in provider.starts] == [operation, "place"]


@pytest.mark.parametrize("spec", [POUR_TOOL_SPEC, STIR_TOOL_SPEC])
def test_action_projection_consumes_exact_preparation(spec):
    policy = project_tool_spec(spec)
    provider = Provider()
    args = provider.prepare_held(request(spec["operation"]))["arguments"]
    actual = execute_argument_projection(
        policy.argument_projection_plan,
        records={"preparation": ({"entity_ref": args["entity_ref"], "arguments": args}, None)},
        literals={}, source_record_ids={"preparation": "preparation"},
    )
    assert actual == args
    jsonschema.validate(actual, spec["input_schema"])


@pytest.mark.parametrize("changes", [
    {"measurements": {}}, {"operation_completed": False}, {"artifact_refs": []},
    {"new_scene_revision": None}, {"new_scene_revision": "scene-1"}, {"returned_to_safe_pose": False},
    {"possession_state": "empty"}, {"destination_ref": "destination://wrong"},
    {"measurements": {"aligned_hold_s": 0.1, "maximum_tilt_rad": 1.8}},
    {"measurements": {"aligned_hold_s": float("nan"), "maximum_tilt_rad": 1.8}},
])
def test_unproven_success_is_unknown_and_blocks_replay(changes):
    provider, held = Provider(), possession()
    rt = runtime(provider, held)
    args = prepare(rt, request())
    provider.next_result = measured(**changes)
    invocation = rt.start_action("object.pour", args, caller_id=CALLER)["invocation_id"]
    result = rt.invocation_result(invocation)
    assert result["status"] == "unknown" and held.state == "uncertain"
    with pytest.raises(CapabilityRuntimeError):
        rt.start_action("object.pour", args, caller_id=CALLER)
    assert len(provider.starts) == 1


@pytest.mark.parametrize("spec", [PREPARE_HELD_TOOL_SPEC, POUR_TOOL_SPEC, STIR_TOOL_SPEC])
def test_published_contract_matches_runtime(spec):
    path = Path(__file__).resolve().parents[1] / "contracts" / f"{spec['tool_id']}.tool.yaml"
    assert yaml.safe_load(path.read_text()) == spec


@pytest.mark.parametrize("operation,tool_id", [("pour", "object.pour"), ("stir", "tool.stir")])
def test_real_acquire_endpoint_feeds_held_operation_and_return(operation, tool_id):
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    acquire = {key: value for key, value in request().items() if key in {
        "entity_ref", "observation_ref", "scene_revision", "frame_id", "calibration_ref",
        "capability_snapshot_ref", "freshness_ms", "max_age_ms",
    }}
    acquire.update(candidate_set_ref="candidate-set://scene-1/camera", candidate_ref="candidate://bottle-a/0",
                   preparation_ref="preparation://scene-1/camera", assignment_ref="artifact://lab/assignment")
    provider.routes[acquire["preparation_ref"]] = deepcopy(acquire)
    provider.next_result = measured(new_scene_revision="scene-acquired")
    acquired_id = rt.start_action("object.acquire", acquire, caller_id=CALLER)["invocation_id"]
    assert rt.invocation_result(acquired_id)["status"] == "succeeded"
    assert held.acquire_invocation_ref == acquired_id and held.last_invocation_ref == acquired_id
    args = request(operation, "scene-acquired", acquired_id)
    args["acquire_invocation_ref"] = acquired_id
    prepared = prepare(rt, args)
    provider.next_result = measured(operation)
    operation_id = rt.start_action(tool_id, prepared, caller_id=CALLER)["invocation_id"]
    assert rt.invocation_result(operation_id)["status"] == "succeeded"
    returned = request("place", "scene-2", operation_id)
    returned["acquire_invocation_ref"] = acquired_id
    prepared = prepare(rt, returned)
    provider.next_result = measured("place", new_scene_revision="scene-returned")
    place_id = rt.start_action("object.place", prepared, caller_id=CALLER)["invocation_id"]
    assert rt.invocation_result(place_id)["status"] == "succeeded"
    assert held.state == "empty"
    assert [item[0] for item in provider.starts] == ["acquire", operation, "place"]


def test_completed_pour_with_failed_retreat_retains_effect_without_repour():
    held = possession()
    raw = measured(status="failed", returned_to_safe_pose=False)
    args = Provider().prepare_held(request())["arguments"]
    result = project_result(raw, args, held, "invocation://object-pour/one")
    assert result["status"] == "failed" and result["operation_completed"] is True
    assert held.state == "holding" and held.last_invocation_ref != ACQUIRE
    assert result["capability_outcome_summary"]["retryable_in_revision"] is False


def test_cancel_requests_provider_stop_and_waits_for_actual_result():
    provider, held = Provider(), possession()
    rt = runtime(provider, held)
    args = prepare(rt, request())
    provider.pending = True
    invocation = rt.start_action("object.pour", args, caller_id=CALLER)["invocation_id"]
    assert rt.cancel_invocation(invocation)["accepted"]
    assert provider.cancelled and held.state == "operating"
    provider.pending = False
    provider.next_result = {"status": "cancelled", "outcome_known": False}
    assert rt.invocation_result(invocation)["status"] == "unknown"
    assert held.state == "uncertain"


def test_start_acknowledgement_loss_does_not_restore_old_holding():
    provider, held = Provider(), possession()
    rt = runtime(provider, held)
    args = prepare(rt, request())
    provider.fail_start = True
    invocation = rt.start_action("object.pour", args, caller_id=CALLER)["invocation_id"]
    assert rt.invocation_result(invocation)["status"] == "unknown"
    assert held.state == "uncertain"


def test_deferred_start_rechecks_state_and_rejects_competing_action():
    provider, held = Provider(), possession()
    args = HeldPreparationEndpoint(provider, held).invoke(request())["arguments"]
    endpoint = HeldActionEndpoint("pour", provider, provider.resolve, held)
    one = endpoint.admit_for_caller(args, caller_id=CALLER)
    two = endpoint.admit_for_caller(args, caller_id=CALLER)
    one.start("invocation://object-pour/one", "attempt://one")
    with pytest.raises(ValueError, match="requires holding"):
        two.start("invocation://object-pour/two", "attempt://two")
    assert len(provider.starts) == 1


@pytest.mark.parametrize("field,value", [
    ("entity_ref", "entity://other"), ("scene_revision", "old"),
    ("held_invocation_ref", "invocation://object-pour/old"),
    ("freshness_ms", 1001), ("parameters", {"tilt_rad": float("inf"), "hold_s": 2}),
])
def test_invalid_preparation_cannot_call_provider(field, value):
    provider, held = Provider(), possession()
    args = {**request(), field: value}
    with pytest.raises((ValueError, jsonschema.ValidationError)):
        HeldPreparationEndpoint(provider, held).invoke(args)
    assert not provider.routes and not provider.starts


def test_wrong_caller_and_changed_route_parameters_are_rejected():
    provider, held = Provider(), possession()
    rt = runtime(provider, held)
    args = prepare(rt, request())
    with pytest.raises(CapabilityRuntimeError):
        rt.start_action("object.pour", args, caller_id="paos:other:rev:rec")
    args["parameters"]["hold_s"] = 20
    with pytest.raises(CapabilityRuntimeError):
        rt.start_action("object.pour", args, caller_id=CALLER)
    assert not provider.starts


def test_reconciliation_requires_latest_held_operation_and_scene():
    held = possession()
    held.state = "uncertain"
    held.last_invocation_ref = "invocation://object-pour/one"
    snapshot = {"available": True, "holding_state": "holding", "owner": held.owner,
                "entity_ref": held.entity_ref, "acquire_invocation_ref": ACQUIRE}
    assert held.reconcile(snapshot) == "uncertain"
    snapshot.update(held_invocation_ref=held.last_invocation_ref, scene_revision="scene-2")
    assert held.reconcile(snapshot) == "holding" and held.scene_revision == "scene-2"
