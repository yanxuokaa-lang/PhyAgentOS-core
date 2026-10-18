"""No-motion tests for the complete-cycle public Tool boundary."""

from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest
import yaml
from PhyAgentOS.forge.capability_runtime import CapabilityRuntimeError

from pick_place_workflow.held_manipulation import (
    POUR_CYCLE_TOOL_SPEC,
    PREPARE_CYCLE_TOOL_SPEC,
    STIR_CYCLE_TOOL_SPEC,
)
from pick_place_workflow.persistent_runtime import PersistentPossession, build_persistent_runtime

CALLER = "paos:task-1:revision-1:record-1"


def request(operation="pour_cycle"):
    parameters = ({"tilt_rad": 1.7, "hold_s": 2.0} if operation == "pour_cycle" else
                  {"radius_m": 0.015, "depth_m": 0.04, "turns": 2.0, "duration_s": 4.0,
                   "direction": "cw"})
    return {"entity_ref": "entity://bottle-a", "destination_ref": "destination://lab/beaker",
            "return_destination_ref": "destination://lab/bottle-home",
            "observation_ref": "observation://scene-1/camera", "scene_revision": "scene-1",
            "frame_id": "camera", "calibration_ref": "artifact://lab/calibration",
            "capability_snapshot_ref": "artifact://lab/capabilities", "operation": operation,
            "parameters": parameters, "freshness_ms": 0, "max_age_ms": 1000}


class Provider:
    def __init__(self):
        self.routes, self.starts = {}, []
        self.result, self.pending = None, False
        self.cancelled, self.fail_start = False, False

    def describe(self, request):
        raise AssertionError("unrelated capability Query was called")

    def prepare_cycle(self, args):
        prepared = {**deepcopy(args), "preparation_ref": f"preparation://cycle/{len(self.routes)}",
                    "assignment_ref": "artifact://lab/assignment"}
        self.routes[prepared["preparation_ref"]] = deepcopy(prepared)
        return {"status": "available", "arguments": prepared}

    def prepare_held(self, args):
        prepared = {**deepcopy(args), "preparation_ref": f"preparation://held/{len(self.routes)}",
                    "assignment_ref": "artifact://lab/assignment"}
        self.routes[prepared["preparation_ref"]] = deepcopy(prepared)
        return {"status": "available", "arguments": prepared}

    def resolve(self, operation, args):
        if args != self.routes[args["preparation_ref"]]:
            raise ValueError("changed prepared cycle")
        return {**deepcopy(args), "assignment": {"task_id": "task-1", "assignment_ref": args["assignment_ref"]}}

    def start(self, operation, invocation, owner, args):
        self.starts.append((operation, invocation, owner, deepcopy(args)))
        if self.fail_start:
            raise OSError("lost acknowledgement")
        return self

    def poll(self):
        return None if self.pending else deepcopy(self.result)

    def cancel(self):
        self.cancelled = True

    def stop(self):
        self.cancel()


def measured(operation="pour_cycle", **changes):
    metrics = ({"qualified_tilt_hold_s": 2.1} if operation == "pour_cycle" else
               {"in_container_turns": 2.1, "in_container_duration_s": 4.1,
                "trajectory_qualified": True, "direction": "cw"})
    return {"status": "succeeded", "outcome_known": True, "world_change_started": True,
            "new_scene_revision": "scene-2", "artifact_refs": ["artifact://lab/cycle-measured"],
            "operation_completed": True, "process_completed": True, "return_completed": True,
            "failed_phase": None, "measurements": metrics, "entity_ref": "entity://bottle-a",
            "destination_ref": "destination://lab/beaker",
            "return_destination_ref": "destination://lab/bottle-home", "possession_state": "empty",
            "release_confirmed": True, "retreat_completed": True, "clear_of_target": True,
            "observation_ready": True, "object_support_state": "on_support", **changes}


def runtime(provider, held):
    return build_persistent_runtime(
        client=provider, understanding_provider=object(), grasp_provider=object(),
        preparation_provider=object(), capability_provider=provider,
        resolve_preparation=provider.resolve, tool_context_provider=lambda _: {"ready": True},
        possession=held, held_preparation_provider=provider, resolve_held_preparation=provider.resolve,
    )


@pytest.mark.parametrize("spec", [PREPARE_CYCLE_TOOL_SPEC, POUR_CYCLE_TOOL_SPEC, STIR_CYCLE_TOOL_SPEC])
def test_published_cycle_contract_matches_runtime(spec):
    path = Path(__file__).resolve().parents[1] / "contracts" / f"{spec['tool_id']}.tool.yaml"
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == spec


@pytest.mark.parametrize("operation,tool_id,spec", [
    ("pour_cycle", "object.pour_cycle", POUR_CYCLE_TOOL_SPEC),
    ("stir_cycle", "tool.stir_cycle", STIR_CYCLE_TOOL_SPEC),
])
def test_complete_cycle_is_one_action_from_empty_to_empty(operation, tool_id, spec):
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    prepared = rt.invoke_query("cycle_preparation", "prepare", request(operation))
    jsonschema.validate(prepared, PREPARE_CYCLE_TOOL_SPEC["output_schema"])
    assert prepared["status"] == "available" and not provider.starts
    args = prepared["arguments"]
    provider.result = measured(operation)
    invocation = rt.start_action(tool_id, args, caller_id=CALLER)["invocation_id"]
    assert held.state == "acquiring"
    result = rt.invocation_result(invocation)
    assert result["status"] == "succeeded"
    jsonschema.validate(result["result"], spec["output_schema"]["properties"]["result"])
    assert result["result"]["process_completed"] and result["result"]["return_completed"]
    assert held.state == "empty" and [item[0] for item in provider.starts] == [operation]


@pytest.mark.parametrize("operation,tool_id", [
    ("pour_cycle", "object.pour_cycle"), ("stir_cycle", "tool.stir_cycle"),
])
def test_cycle_process_feedback_must_meet_requested_target(operation, tool_id):
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request(operation))["arguments"]
    metrics = ({"qualified_tilt_hold_s": 1.0} if operation == "pour_cycle" else
               {"in_container_turns": 2.1, "in_container_duration_s": 4.1,
                "trajectory_qualified": False, "direction": "cw"})
    provider.result = measured(operation, measurements=metrics)
    invocation = rt.start_action(tool_id, args, caller_id=CALLER)["invocation_id"]
    assert rt.invocation_result(invocation)["status"] == "unknown" and held.state == "uncertain"


def test_completed_process_with_failed_return_is_not_replayed():
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    provider.result = measured(status="failed", operation_completed=False, return_completed=False,
                               possession_state="holding", release_confirmed=False,
                               failed_phase="return", failure_code="return_blocked")
    invocation = rt.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    result = rt.invocation_result(invocation)
    assert result["status"] == "failed"
    assert result["result"]["process_completed"] and not result["result"]["return_completed"]
    assert held.state == "holding" and held.cycle_invocation_ref == invocation
    assert held.acquire_invocation_ref is None
    with pytest.raises(CapabilityRuntimeError):
        rt.start_action("object.pour_cycle", args, caller_id=CALLER)
    assert len(provider.starts) == 1


def test_recovery_after_cycle_return_failure_uses_place_only():
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    provider.result = measured(status="failed", operation_completed=False, return_completed=False,
                               possession_state="holding", release_confirmed=False,
                               failed_phase="return", failure_code="return_blocked")
    cycle = rt.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    result = rt.invocation_result(cycle)
    assert result["status"] == "failed" and result["result"]["process_completed"]

    placement = request("pour_cycle")
    placement.update(operation="place", parameters={},
                     destination_ref=placement["return_destination_ref"], scene_revision="scene-2",
                     held_invocation_ref=cycle, cycle_invocation_ref=cycle)
    placement.pop("return_destination_ref")
    prepared = rt.invoke_query("held_preparation", "prepare", placement)
    assert prepared["status"] == "available"
    provider.result = {
        **measured("place"), "entity_ref": placement["entity_ref"],
        "destination_ref": placement["destination_ref"], "new_scene_revision": "scene-3",
    }
    place = rt.start_action("object.place", prepared["arguments"], caller_id=CALLER)["invocation_id"]
    assert rt.invocation_result(place)["status"] == "succeeded"
    assert [item[0] for item in provider.starts] == ["pour_cycle", "place"]
    assert held.state == "empty"


@pytest.mark.parametrize("changes", [
    {"return_completed": False}, {"process_completed": False}, {"artifact_refs": []},
    {"release_confirmed": False}, {"possession_state": "holding"},
    {"return_destination_ref": "destination://wrong"}, {"new_scene_revision": "scene-1"},
])
def test_unproven_success_blocks_replay(changes):
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    provider.result = measured(**changes)
    invocation = rt.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    assert rt.invocation_result(invocation)["status"] == "unknown"
    with pytest.raises(CapabilityRuntimeError):
        rt.start_action("object.pour_cycle", args, caller_id=CALLER)
    assert len(provider.starts) == 1


def test_cancel_waits_for_actual_stop_and_lost_start_is_unknown():
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    provider.pending = True
    invocation = rt.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    assert rt.cancel_invocation(invocation)["accepted"] and provider.cancelled
    assert held.state == "acquiring"
    provider.pending = False
    provider.result = {"status": "cancelled", "outcome_known": False}
    assert rt.invocation_result(invocation)["status"] == "unknown"
    assert held.state == "uncertain"


def test_changed_parameters_or_wrong_owner_cannot_start():
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    with pytest.raises(CapabilityRuntimeError):
        rt.start_action("object.pour_cycle", args, caller_id="paos:other:rev:record")
    args["parameters"]["hold_s"] = 20
    with pytest.raises(CapabilityRuntimeError):
        rt.start_action("object.pour_cycle", args, caller_id=CALLER)
    assert not provider.starts
