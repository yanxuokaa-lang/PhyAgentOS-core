"""No-motion tests for the complete-cycle public Tool boundary."""

import math
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
    def __init__(self, *, cycles=True):
        self.routes, self.starts = {}, []
        self.result, self.pending = None, False
        self.cancelled, self.fail_start = False, False
        self.cycles = cycles

    def supports_cycle(self, operation):
        return self.cycles and operation in {"pour_cycle", "stir_cycle"}

    def cycle_capability(self, operation):
        enabled = self.cycles and operation in {"pour_cycle", "stir_cycle"}
        return {
            "operation": operation,
            "preparation": enabled,
            "execution": enabled,
            "feedback": enabled,
            "return": enabled,
            "dry_run": True,
        }

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
    if operation == "pour_cycle":
        feedback = [{"timestamp_s": 2.0 + index * 0.5, "feedback_valid": True, "grasp_valid": True,
                     "target_container_aligned": True, "alignment_error_m": 0.001, "tilt_rad": 1.7}
                    for index in range(7)]
        profile = {"max_sample_gap_s": 0.6, "alignment_tolerance_m": 0.005,
                   "tilt_tolerance_rad": 0.1, "maximum_tilt_rad": 2.0}
    else:
        feedback = [{"timestamp_s": 2.0 + index * 0.11, "feedback_valid": True, "grasp_valid": True,
                     "tool_tip_x_m": 0.015 * math.cos(-index * 4 * math.pi / 40),
                     "tool_tip_y_m": 0.015 * math.sin(-index * 4 * math.pi / 40),
                     "tool_tip_depth_m": 0.04} for index in range(41)]
        profile = {"max_sample_gap_s": 0.2, "radius_tolerance_m": 0.002,
                   "depth_tolerance_m": 0.002, "container_radius_m": 0.05, "container_depth_m": 0.1,
                   "max_angular_step_rad": 0.5}
    phases = [
        {"phase": "acquire", "status": "completed", "outcome_known": True,
         "facts": {"grasp_confirmed": True, "possession_state": "holding"}},
        {"phase": "transport", "status": "completed", "outcome_known": True,
         "facts": {"route_completed": True, "possession_state": "holding"}},
        {"phase": "process", "status": "completed", "outcome_known": True, "facts": {"possession_state": "holding"}},
        {"phase": "reorient_exit", "status": "completed", "outcome_known": True,
         "facts": {"tool_reoriented_or_exited": True, "possession_state": "holding"}},
        {"phase": "stow", "status": "completed", "outcome_known": True,
         "facts": {"object_support_state": "on_support"}},
        {"phase": "release", "status": "completed", "outcome_known": True,
         "facts": {"release_confirmed": True, "possession_state": "empty"}},
        {"phase": "retreat", "status": "completed", "outcome_known": True,
         "facts": {"retreat_completed": True, "clear_of_target": True, "observation_ready": True}},
    ]
    if changes.get("failed_phase") in {"release", "return"}:
        phases[5] = {"phase": "release", "status": "failed", "outcome_known": True,
                     "facts": {"release_attempted": True}}
        phases = phases[:6]
    for index, event in enumerate(phases):
        event["started_at_s"] = float(index + 0)
        event["completed_at_s"] = float(index + 1)
    phases[2]["started_at_s"], phases[2]["completed_at_s"] = 2.0, 7.0
    for index in range(3, len(phases)):
        phases[index]["started_at_s"] = float(index + 4)
        phases[index]["completed_at_s"] = float(index + 5)
    return {"status": "succeeded", "outcome_known": True, "world_change_started": True,
            "new_scene_revision": "scene-2", "artifact_refs": ["artifact://lab/cycle-measured"],
            "operation_completed": True, "process_completed": True, "return_completed": True,
            "failed_phase": None, "measurements": {}, "feedback_samples": feedback,
            "evaluation_profile": profile, "phase_events": phases, "entity_ref": "entity://bottle-a",
            "destination_ref": "destination://lab/beaker",
            "return_destination_ref": "destination://lab/bottle-home", "possession_state": "empty",
            "release_confirmed": True, "retreat_completed": True, "clear_of_target": True,
            "observation_ready": True, "object_support_state": "on_support", **changes}


def runtime(provider, held, client=None):
    return build_persistent_runtime(
        client=client or provider, understanding_provider=object(), grasp_provider=object(),
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
    bad_trace = measured(operation)
    if operation == "pour_cycle":
        for sample in bad_trace["feedback_samples"]:
            sample["target_container_aligned"] = False
    else:
        for sample in bad_trace["feedback_samples"]:
            sample["tool_tip_x_m"], sample["tool_tip_y_m"] = 0.015, 0.0
    provider.result = bad_trace
    invocation = rt.start_action(tool_id, args, caller_id=CALLER)["invocation_id"]
    result = rt.invocation_result(invocation)
    assert result["status"] == "failed"
    assert result["result"]["failed_phase"] == "process"
    assert not result["result"]["process_completed"]


def test_cycle_projector_normalizes_raw_provider_feedback_before_evaluation():
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())[
        "arguments"
    ]
    raw = measured()
    raw["feedback_observations"] = [
        {
            "timestamp_s": sample["timestamp_s"],
            "frame_id": "camera_front",
            "calibration_ref": "calibration://front/v3",
            "container_frame_id": "container://beaker",
            "grasp_state": "holding",
            "feedback_valid": sample["feedback_valid"],
            "target_container_aligned": sample["target_container_aligned"],
            "alignment_error_m": sample["alignment_error_m"],
            "tilt_rad": sample["tilt_rad"],
        }
        for sample in raw.pop("feedback_samples")
    ]
    raw["feedback_source_profile"] = {
        "frame_id": "camera_front",
        "calibration_ref": "calibration://front/v3",
        "container_frame_id": "container://beaker",
    }
    provider.result = raw
    invocation = rt.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    settled = rt.invocation_result(invocation)
    assert settled["status"] == "succeeded"
    assert settled["result"]["process_completed"] is True


def test_cycle_projector_rejects_raw_feedback_frame_drift_as_unknown():
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    raw = measured()
    raw["feedback_observations"] = [
        {
            "timestamp_s": sample["timestamp_s"],
            "frame_id": "wrong-frame",
            "calibration_ref": "calibration://front/v3",
            "container_frame_id": "container://beaker",
            "grasp_state": "holding",
            "feedback_valid": True,
            "target_container_aligned": True,
            "alignment_error_m": 0.001,
            "tilt_rad": 1.7,
        }
        for sample in raw.pop("feedback_samples")
    ]
    raw["feedback_source_profile"] = {
        "frame_id": "camera_front",
        "calibration_ref": "calibration://front/v3",
        "container_frame_id": "container://beaker",
    }
    provider.result = raw
    invocation = rt.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    settled = rt.invocation_result(invocation)
    assert settled["status"] == "unknown"
    assert settled["result"]["process_completed"] is False
    assert settled["result"]["measurements"]["feedback_adapter_status"] == "invalid"
    assert "frame_mismatch" in settled["result"]["measurements"]["feedback_adapter_errors"]


def test_process_fact_survives_missing_artifact_reference_as_unknown_partial_result():
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    result = measured()
    result.pop("artifact_refs")
    result["evidence_refs"] = []
    provider.result = result
    invocation = rt.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    settled = rt.invocation_result(invocation)
    assert settled["status"] == "unknown"
    assert settled["result"]["process_completed"] is True
    assert settled["result"]["return_completed"] is True


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
        "status": "succeeded", "outcome_known": True, "world_change_started": True,
        "new_scene_revision": "scene-3", "artifact_refs": ["artifact://lab/place"],
        "operation_completed": True, "measurements": {"position_error_m": 0.001},
        "entity_ref": placement["entity_ref"], "destination_ref": placement["destination_ref"],
        "possession_state": "empty", "release_confirmed": True, "retreat_completed": True,
        "clear_of_target": True, "observation_ready": True,
    }
    place = rt.start_action("object.place", prepared["arguments"], caller_id=CALLER)["invocation_id"]
    assert rt.invocation_result(place)["status"] == "succeeded"
    assert [item[0] for item in provider.starts] == ["pour_cycle", "place"]
    assert held.state == "empty"


@pytest.mark.parametrize("changes", [
    {"artifact_refs": []}, {"phase_events": []},
    {"phase_events": "invalid"}, {"possession_state": "holding"},
    {"phase_events": [{"phase": "acquire", "status": "unknown", "outcome_known": False,
                       "started_at_s": 0.0, "facts": {}}]},
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


def test_unknown_after_malformed_late_phase_preserves_prior_phase_facts():
    provider, held = Provider(), PersistentPossession()
    rt = runtime(provider, held)
    args = rt.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    raw = measured()
    raw["phase_events"] = [raw["phase_events"][0], raw["phase_events"][1],
                           {"phase": "stow", "status": "completed", "outcome_known": True,
                            "started_at_s": 2.0, "completed_at_s": 3.0,
                            "facts": {"object_support_state": "on_support"}}]
    raw.update(status="unknown", outcome_known=False)
    provider.result = raw
    invocation = rt.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    result = rt.invocation_result(invocation)
    assert result["status"] == "unknown"
    assert result["result"]["completed_phases"] == ["acquire", "transport"]
    assert result["result"]["failed_phase"] == "stow"
    assert held.state == "uncertain"


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

    lost_ack_provider, lost_ack_possession = Provider(), PersistentPossession()
    lost_ack_provider.fail_start = True
    lost_ack_runtime = runtime(lost_ack_provider, lost_ack_possession)
    args = lost_ack_runtime.invoke_query("cycle_preparation", "prepare", request())["arguments"]
    invocation = lost_ack_runtime.start_action("object.pour_cycle", args, caller_id=CALLER)["invocation_id"]
    assert lost_ack_runtime.invocation_result(invocation)["status"] == "unknown"
    assert lost_ack_possession.state == "uncertain"
    assert len(lost_ack_provider.starts) == 1


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


def test_cycle_capability_controls_discovery_without_relabeling_held_tools():
    rt = runtime(Provider(cycles=False), PersistentPossession())
    ids = {tool["tool_id"] for tool in rt.list_tools()["tools"]}
    assert "object.pour_cycle" not in ids and "tool.stir_cycle" not in ids
    assert "object.pour" in ids and "tool.stir" in ids


def test_cycle_discovery_requires_both_preparation_and_execution_capability():
    provider = Provider(cycles=True)
    rt = runtime(provider, PersistentPossession(), client=object())
    ids = {tool["tool_id"] for tool in rt.list_tools()["tools"]}
    assert "object.pour_cycle" not in ids and "tool.stir_cycle" not in ids
    assert "object.pour" in ids and "tool.stir" in ids


def test_cycle_preparation_uses_the_existing_query_decorator():
    decorated = []

    def decorate(tool_id, endpoint):
        decorated.append(tool_id)
        return endpoint

    provider = Provider()
    build_persistent_runtime(
        client=provider, understanding_provider=object(), grasp_provider=object(),
        preparation_provider=object(), capability_provider=provider,
        resolve_preparation=provider.resolve, tool_context_provider=lambda _: {"ready": True},
        held_preparation_provider=provider, resolve_held_preparation=provider.resolve,
        query_decorator=decorate,
    )
    assert "manipulation.prepare_cycle" in decorated
    assert "manipulation.prepare_held" in decorated
