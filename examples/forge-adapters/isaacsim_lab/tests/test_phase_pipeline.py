"""Exercise real Runtime endpoints and storage; only the simulator is substituted."""
from copy import deepcopy
from time import monotonic, sleep
from types import SimpleNamespace

import pytest
from PhyAgentOS.forge.capability_runtime.manipulation_prepare import preparation_ref_for_request
from PhyAgentOS.forge.manipulation import ArmAssignment, arm_assignment_digest
from pick_place_workflow.persistent_runtime import PersistentPossession, register_subtask_tool
from pick_place_workflow.subtask_executor import PerceptionBinding, SubtaskSpec

from isaacsim_lab.paos_client import build_labutopia_runtime


def observed(entity, revision):
    frame = "front"
    pose = {"frame_id": frame, "unit": "m", "position_m": [0.2, 0.1, 0.8],
            "orientation_xyzw": [0, 0, 0, 1]}
    candidate = {"candidate_ref": f"candidate://{entity}/{revision}", "entity_ref": f"entity://{entity}",
                 "grasp_frame": pose, "approach_direction": {"frame_id": frame, "unit": "unitless", "vector": [0, 0, -1]},
                 "score": 0.99, "confidence": 0.99, "provenance": [f"artifact://grasp/{revision}/{entity}"],
                 "qualification": "proposed"}
    return PerceptionBinding(
        entity_ref=f"entity://{entity}", semantic_label=entity, category="stir_tool" if entity == "rod" else "reagent_bottle",
        destination_semantic_label="beaker", destination_category="beaker",
        measured_pose=pose, measured_geometry={"size_m": [0.04, 0.04, 0.15]},
        grasp_candidate=candidate, grasp_candidate_ref=f"candidate-set://{revision}/{frame}",
        candidate_set_ref=f"candidate-set://{revision}/{frame}", candidate_ref=candidate["candidate_ref"],
        capability_snapshot_ref=f"artifact://capabilities/{revision}", binding_ref=f"artifact://bindings/{revision}/{entity}",
        destination_ref="destination://beaker", destination_pose=pose, process_frame="frame://beaker",
        observation_ref=f"observation://{revision}/{frame}", scene_revision=revision, frame_id=frame,
        calibration_ref=f"artifact://calibration/{revision}/front", freshness_ms=0, max_age_ms=1000,
        confidence=0.99, provenance=f"artifact://observations/{revision}",
    )


def context_for(binding, node):
    identity = {"task_id": "mixture", "revision_id": "plan-1", "node_id": node, "node_digest": "a" * 64}
    intent = {**identity, "version": "manipulation_intent_v2", "entity_ref": binding.entity_ref,
              "observation_ref": binding.observation_ref, "scene_revision": binding.scene_revision,
              "observation_frame_id": binding.frame_id, "calibration_ref": binding.calibration_ref,
              "candidate_set_ref": binding.candidate_set_ref, "goal": "mix selected reagents and stir",
              "success_criteria": ["measured process and return"], "allowed_arms": ["franka"],
              "coordination_mode": "single_arm", "constraints": [], "motion_authorized": False}
    return {**identity, "intent": intent, "obligation_id": node,
            "input_binding_digest": "b" * 64, "decision_trace_ref": "artifact://decisions/mixture",
            "planning_binding": {**{k: identity[k] for k in ("revision_id", "node_id", "node_digest")},
                                 "obligation_id": node, "input_binding_digest": "b" * 64,
                                 "decision_trace_ref": "artifact://decisions/mixture"}}


class PhaseEngine:
    """Deterministic no-motion mechanism, never a claim of real physics success."""
    def __init__(self, fail_operation=None):
        self.revision = "scene-0"
        self.calls = []
        self.fail_operation = fail_operation

    def prepare_manipulation(self, request):
        assert request["scene_revision"] == self.revision
        candidate = request["candidates"][0]
        intent = request["intent"]
        assert intent["scene_revision"] == self.revision
        assert intent["observation_ref"] == request["observation_ref"]
        assert intent["calibration_ref"] == request["calibration_ref"]
        assignment = {k: intent[k] for k in ("task_id", "revision_id", "node_id", "node_digest", "entity_ref",
                                             "observation_ref", "scene_revision", "calibration_ref", "candidate_set_ref", "coordination_mode")}
        assignment.update(assignment_ref=f"artifact://assignment/{intent['node_id']}", selected_arm_ids=["franka"],
                          candidate_ref=candidate["candidate_ref"], route_digest="c" * 64,
                          capability_snapshot_ref=request["capability_snapshot_ref"],
                          readiness_evidence_ref=f"artifact://readiness/{intent['node_id']}", decision_basis=["fixture route checks"],
                          alternatives=[], motion_authorized=False, schema_version="paos-arm-assignment/v1")
        assignment["assignment_digest"] = arm_assignment_digest(assignment)
        assignment = ArmAssignment.model_validate(assignment).model_dump(mode="json")
        return {"status": "available", "prepared_candidates": [{
            "candidate_ref": candidate["candidate_ref"], "entity_ref": candidate["entity_ref"],
            "qualification": "prepared", "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
            "evidence": [assignment["readiness_evidence_ref"]],
        }], "assignments": [assignment], "destination_ref": request["destination_ref"],
                "route_arguments": {"entity_ref": candidate["entity_ref"], "candidate_ref": candidate["candidate_ref"],
                                    "preparation_ref": preparation_ref_for_request(request),
                                    "scene_revision": self.revision, "destination_ref": request["destination_ref"],
                                    "manipulation_target": request["manipulation_target"]}}

    def prepare_held(self, request):
        assert request["scene_revision"] == self.revision
        assert request["calibration_ref"] == f"artifact://calibration/{self.revision}/front"
        self.calls.append(("prepare_held", request["operation"], request["entity_ref"], self.revision))
        return {"status": "available", "motion_authorized": False, "route_arguments": dict(request),
                "route_digest": "d" * 64, "readiness_evidence_ref": f"artifact://readiness/{self.revision}"}

    def execute_phase(self, phase, request, cancel, **kwargs):
        assert request["scene_revision"] == self.revision
        assert request["assignment"]["task_id"] == "mixture"
        assert request["assignment"]["calibration_ref"] == f"artifact://calibration/{self.revision}/front"
        assert request["manipulation_target"]["entity_ref"] == request["entity_ref"]
        self.calls.append(("execute", phase, request["entity_ref"], self.revision))
        self.revision = f"scene-{int(self.revision.split('-')[1]) + 1}"
        failed = phase == self.fail_operation
        return {"status": "failed" if failed else "succeeded", "outcome_known": True,
                "entity_ref": request["entity_ref"], "destination_ref": request["destination_ref"],
                "world_change_started": True, "new_scene_revision": self.revision,
                "artifact_refs": [f"artifact://feedback/{self.revision}"],
                "possession_state": "empty" if phase == "place" else "holding",
                "operation_completed": not failed, "returned_to_safe_pose": True,
                "release_confirmed": phase == "place", "retreat_completed": phase == "place",
                "clear_of_target": phase == "place", "observation_ready": phase == "place",
                "object_support_state": "on_support" if phase == "place" else "lifted",
                "measurements": {"aligned_hold_s": 1., "maximum_tilt_rad": 1.,
                                 "in_container_turns": 2., "in_container_duration_s": 4.}}


class TargetResolver:
    def resolve(self, binding, request):
        pose = binding["measured_pose"]
        return {**{k: binding[k] for k in ("entity_ref", "destination_ref", "scene_revision", "frame_id", "calibration_ref", "candidate_ref")},
                "control_frame_id": binding["frame_id"],
                "world_from_control": {"parent_frame_id": "world", "child_frame_id": binding["frame_id"],
                                       "translation_m": [0, 0, 0], "orientation_xyzw": [0, 0, 0, 1]},
                "entity_prim_path": "/World/selected", "destination_prim_path": "/World/vessel",
                "object_pose": pose, "grasp_frame": pose, "return_pose": pose, "destination_pose": pose,
                "approach_direction": binding["grasp_candidate"]["approach_direction"],
                "process_frame": {"frame_id": binding["frame_id"], "origin_m": [0.2, 0.1, 0.8], "axis": [0, 0, 1]},
                "tool_frame": {"frame_id": "tool", "tip_axis_local": [0, 0, -1]}}


def run_mixture(tmp_path, fail_operation=None):
    engine = PhaseEngine(fail_operation)
    context = {}
    possession = PersistentPossession()
    bundle = build_labutopia_runtime(
        profile=SimpleNamespace(lab_root=tmp_path), engine=engine,
        understanding_provider=object(), grasp_provider=object(), preparation_provider=None, capability_provider=SimpleNamespace(describe=lambda _request: None),
        resolve_preparation=lambda *_args: pytest.fail("must use stored route"),
        tool_context_provider=lambda _tool: {"ready": True}, target_resolver=TargetResolver(),
        allow_live=True, possession=possession,
    )
    refreshes = []
    def refresh(binding, revision):
        assert revision == engine.revision
        refreshes.append(revision)
        return observed(binding.semantic_label, revision)
    register_subtask_tool(bundle.runtime, refresh, lambda _tool: {"ready": True}, lambda _caller: context,
                          bundle.client._assignment_store)
    outcomes = []
    try:
        for node, entity, operation, params in (
            ("pour-a", "reagent-a", "pour", {"tilt_rad": .87, "hold_s": .6}),
            ("pour-b", "reagent-b", "pour", {"tilt_rad": .87, "hold_s": .6}),
            ("stir", "rod", "stir", {"radius_m": .009, "depth_m": .04, "turns": 2., "duration_s": 4., "direction": "ccw"}),
        ):
            # The Agent binds the whole plan before any physical action.
            binding = observed(entity, "scene-0")
            context.clear()
            context.update(context_for(binding, node))
            context["scene_revision"] = engine.revision
            original_intent = deepcopy(context["intent"])
            spec = SubtaskSpec(subtask_id=node, operation=operation, binding=binding, parameters=params)
            arguments = spec.model_dump(mode="json", exclude_none=True)
            arguments["intent"] = context["intent"]
            invocation = bundle.runtime.start_action("manipulation.execute_subtask", arguments,
                                                     caller_id=f"paos:mixture:plan-1:{node}")["invocation_id"]
            deadline = monotonic() + 5
            while monotonic() < deadline:
                result = bundle.runtime.invocation_result(invocation)
                if result["status"] != "pending":
                    break
                sleep(.001)
            outcomes.append(deepcopy(result))
            assert context["intent"] == original_intent
            if result["status"] != "succeeded":
                break
        return outcomes, engine.calls, possession, refreshes
    finally:
        bundle.client.close()


def test_two_reagents_and_stir_traverse_real_runtime_and_stored_routes(tmp_path):
    outcomes, calls, possession, refreshes = run_mixture(tmp_path)
    assert [result["status"] for result in outcomes] == ["succeeded"] * 3, outcomes
    assert [(phase, entity) for kind, phase, entity, _ in calls if kind == "execute"] == [
        (phase, entity) for entity, process in (("entity://reagent-a", "pour"), ("entity://reagent-b", "pour"), ("entity://rod", "stir"))
        for phase in ("acquire", process, "place")]
    for outcome in outcomes:
        subtask = outcome["result"]["subtask_result"]
        assert len(subtask["receipts"]) == 6
        assert subtask["possession_state"] == "empty"
    assert refreshes == [f"scene-{number}" for number in range(1, 9)]
    assert possession.state == "empty"


def test_real_phase_assignment_projection_traverses_runtime(tmp_path, monkeypatch):
    from isaacsim_lab.phase_motion import preparation_result

    def prepare(self, request):
        # Substitute the plant route only; use the same assignment projection
        # used after measured qualification inside the Isaac worker.
        return preparation_result(request, {"operation": "acquire", "scene_revision": self.revision,
                                           "steps": []}, "artifact://readiness/fixture")

    monkeypatch.setattr(PhaseEngine, "prepare_manipulation", prepare)
    outcomes, calls, possession, _ = run_mixture(tmp_path)
    assert [outcome["status"] for outcome in outcomes] == ["succeeded"] * 3, outcomes
    assert len([item for item in calls if item[0] == "execute"]) == 9
    assert possession.state == "empty"


@pytest.mark.parametrize("operation", ["pour", "stir"])
def test_failed_process_stops_without_replaying_or_releasing(tmp_path, operation):
    outcomes, calls, possession, _ = run_mixture(tmp_path, operation)
    assert outcomes[-1]["status"] == "failed", outcomes
    assert possession.state == "holding"
    actions = [phase for kind, phase, _, _ in calls if kind == "execute"]
    assert actions.count(operation) == 1
    assert actions[-1] == operation


def test_private_routes_remain_in_storage_not_agent_subtask_receipts(tmp_path):
    import json
    import sqlite3

    outcomes, _, _, _ = run_mixture(tmp_path)
    assert len(outcomes) == 3
    assert "/World/" not in json.dumps(outcomes)
    with sqlite3.connect(tmp_path / "outputs/paos/assignment-artifacts.sqlite3") as connection:
        documents = [json.loads(row[0]) for row in connection.execute("SELECT document_json FROM assignment_artifacts")]
    assert len(documents) == 9  # one acquire + two fresh held preparations per subtask
    assert all(document["route_arguments"]["manipulation_target"] for document in documents)
    for document in documents:
        assignment = ArmAssignment.model_validate(document["assignment"])
        if assignment.assignment_ref.startswith("artifact://labutopia/"):
            assert assignment.route_digest == "d" * 64
            assert assignment.readiness_evidence_ref.endswith(assignment.scene_revision)


def test_preparation_unavailable_is_a_known_no_motion_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(PhaseEngine, "prepare_manipulation", lambda *_args: {
        "status": "unavailable", "motion_authorized": False,
        "failure_code": "measured_collision_route_unavailable",
    })
    outcomes, calls, possession, _ = run_mixture(tmp_path)
    assert outcomes[-1]["status"] == "failed", outcomes
    assert calls == []
    assert possession.state == "empty"
    receipt = outcomes[-1]["result"]["subtask_result"]["receipts"][0]
    assert receipt["response"]["error"]["code"] == "measured_collision_route_unavailable"


def test_unknown_process_stops_without_replay(tmp_path, monkeypatch):
    original = PhaseEngine.execute_phase
    def execute(self, phase, *args, **kwargs):
        result = original(self, phase, *args, **kwargs)
        if phase == "pour":
            result.update(status="unknown", outcome_known=False, possession_state="uncertain")
        return result
    monkeypatch.setattr(PhaseEngine, "execute_phase", execute)
    outcomes, calls, possession, _ = run_mixture(tmp_path)
    assert outcomes[-1]["status"] == "unknown"
    assert possession.state == "uncertain"
    assert [phase for kind, phase, _, _ in calls if kind == "execute"] == ["acquire", "pour"]


def test_held_preparation_rejects_changed_parameters_before_process(tmp_path, monkeypatch):
    original = PhaseEngine.prepare_held
    def prepare(self, request):
        result = original(self, request)
        result["route_arguments"]["parameters"] = {"tilt_rad": 1.5, "hold_s": 100.}
        return result
    monkeypatch.setattr(PhaseEngine, "prepare_held", prepare)
    outcomes, calls, possession, _ = run_mixture(tmp_path)
    assert outcomes[-1]["status"] == "failed"
    assert possession.state == "holding"
    assert [phase for kind, phase, _, _ in calls if kind == "execute"] == ["acquire"]
