from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from PhyAgentOS.forge.capability_runtime import ActionAdmission
from PhyAgentOS.planning import project_tool_spec

from pick_place_workflow.relation_execution import (
    RELATION_ESTABLISH_TOOL_SPEC,
    RelationEstablishActionEndpoint,
)


def _identity():
    return {
        "entity_ref": "entity://stack-block-2",
        "goal_relation": "on",
        "relation_target_ref": "entity://stack-block-1",
        "scene_revision": "scene-8",
        "observation_ref": "observation://scene-8/head_camera",
        "observation_frame_id": "head_camera",
        "calibration_ref": "artifact://scene-8/calibration",
    }


def _context():
    identity = _identity()
    return {
        "task_id": "task-1",
        "revision_id": "revision-2",
        "node_id": "place_middle",
        "node_digest": "node-digest",
        "input_binding_digest": "binding-digest",
        "planning_binding": {
            "entity_ref": identity["entity_ref"],
            "goal_relation": identity["goal_relation"],
            "relation_target_ref": identity["relation_target_ref"],
            "scene_revision": identity["scene_revision"],
            "observation_ref": identity["observation_ref"],
            "observation_frame_id": identity["observation_frame_id"],
            "calibration_ref": identity["calibration_ref"],
        },
        "intent": {
            "task_id": "task-1",
            "revision_id": "revision-2",
            "node_id": "place_middle",
            "node_digest": "node-digest",
            "calibration_ref": identity["calibration_ref"],
            "motion_authorized": False,
        },
    }


def _binding():
    return {
        **_identity(),
        "relation_candidate_ref": "relation-target://run-1/candidate-1",
        "relation_candidate_set_ref": "relation-target-set://run-1/set-1",
        "destination_ref": "destination://run-1/table-place-1",
        "world_T_object_target": [
            1, 0, 0, 0.1,
            0, 1, 0, 0.2,
            0, 0, 1, 0.3,
            0, 0, 0, 1,
        ],
        "evidence_refs": ["artifact://run-1/geometry-1"],
        "motion_authorized": False,
    }


def _query_result():
    return {
        "status": "available",
        "candidate_set_ref": "relation-target-set://run-1/set-1",
        **{key: _identity()[key] for key in (
            "entity_ref", "goal_relation", "relation_target_ref", "scene_revision",
            "observation_ref", "calibration_ref",
        )},
        "frame_id": _identity()["observation_frame_id"],
        "candidates": [{
            "candidate_ref": "relation-target://run-1/candidate-1",
            "destination_ref": "destination://run-1/table-place-1",
            "world_T_object_target": _binding()["world_T_object_target"],
            "evidence_refs": ["artifact://run-1/geometry-1"],
        }],
        "motion_authorized": False,
    }


def _arguments():
    return {
        **_identity(),
        "relation_query_result": _query_result(),
        "candidate_ref": "relation-target://run-1/candidate-1",
        "intent": deepcopy(_context()["intent"]),
    }


def test_relation_action_defers_to_substitutable_provider_with_runtime_ids():
    class Provider:
        request = None

        def admit(self, request, *, invocation_id, attempt_id):
            self.request = (dict(request), invocation_id, attempt_id)
            return ActionAdmission(terminal_result={"status": "unavailable", "outcome_known": True})

    provider = Provider()
    endpoint = RelationEstablishActionEndpoint(provider, lambda _caller: _context())

    admission = endpoint.admit_for_caller(_arguments(), caller_id="paos:task-1")

    assert provider.request is None
    started = admission.start("invocation-1", "attempt-1")
    assert provider.request[1:] == ("invocation-1", "attempt-1")
    assert started.terminal_result["status"] == "unavailable"
    assert provider.request[0]["relation_binding"]["motion_authorized"] is False


def test_relation_action_tool_contract_binds_geometry_to_query_source():
    errors = list(
        Draft202012Validator(RELATION_ESTABLISH_TOOL_SPEC["input_schema"]).iter_errors(
            _arguments()
        )
    )

    assert errors == []
    policy = project_tool_spec(RELATION_ESTABLISH_TOOL_SPEC)
    assert policy.capabilities == ("relation.establish",)
    assert policy.argument_source_requirements[0].source_tool_id == "relation.target"


@pytest.mark.parametrize(
    ("argument_change", "binding_change"),
    [({"scene_revision": "scene-7"}, {}), ({}, {"observation_ref": "observation://scene-7/head_camera"})],
)
def test_relation_action_rejects_stale_or_mismatched_lineage_before_provider(
    argument_change, binding_change
):
    class MustNotRun:
        def admit(self, *_args, **_kwargs):
            raise AssertionError("invalid lineage must not reach the Provider")

    arguments = _arguments()
    arguments.update(argument_change)
    if binding_change:
        arguments["relation_query_result"].update(binding_change)
    endpoint = RelationEstablishActionEndpoint(MustNotRun(), lambda _caller: _context())

    with pytest.raises(ValueError, match="Coordinator node|current observation"):
        endpoint.admit_for_caller(arguments, caller_id="paos:task-1")


def test_relation_action_provider_exception_is_unknown_not_success():
    class FailingProvider:
        def admit(self, *_args, **_kwargs):
            raise RuntimeError("provider lost execution feedback")

    endpoint = RelationEstablishActionEndpoint(FailingProvider(), lambda _caller: _context())
    admission = endpoint.admit_for_caller(_arguments(), caller_id="paos:task-1")

    result = admission.start("invocation-1", "attempt-1")

    assert result.terminal_result["status"] == "unknown"
    assert result.terminal_result["outcome_known"] is False


def test_relation_action_requires_task_owned_caller():
    endpoint = RelationEstablishActionEndpoint(object(), lambda _caller: _context())

    with pytest.raises(ValueError, match="PAOS task"):
        endpoint.admit_for_caller(_arguments(), caller_id="cli:direct")


def test_relation_action_rejects_calibration_mismatch_in_coordinator_intent():
    context = _context()
    context["intent"]["calibration_ref"] = "artifact://other/calibration"
    endpoint = RelationEstablishActionEndpoint(object(), lambda _caller: context)

    with pytest.raises(ValueError, match="calibration"):
        endpoint.admit_for_caller(_arguments(), caller_id="paos:task-1")
