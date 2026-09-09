from copy import deepcopy

import jsonschema
import pytest
from PhyAgentOS.forge.capability_runtime.manipulation_prepare import (
    MANIPULATION_TOOL_SPEC,
    ManipulationPreparationEndpoint,
)
from PhyAgentOS.forge.manipulation import arm_assignment_digest
from test_manipulation_prepare import prepared, request_payload


def request_and_result():
    request = request_payload()
    request.update(destination_ref="destination://shelf", capability_snapshot_ref="artifact://scene/capabilities")
    intent = {key: request[key] for key in ("observation_ref", "scene_revision", "calibration_ref", "candidate_set_ref")}
    intent.update(task_id="task", revision_id="revision", node_id="relocate", node_digest="a" * 64,
                  entity_ref="entity://bottle-1", goal="place bottle", success_criteria=["on shelf"], allowed_arms=["left"],
                  coordination_mode="single_arm", observation_frame_id=request["frame_id"])
    intent["calibration_ref"] = request["calibration_ref"] = "artifact://scene/calibration"
    request["intent"] = intent
    assignment = {key: value for key, value in intent.items() if key not in {"goal", "success_criteria", "allowed_arms", "observation_frame_id"}}
    assignment.update(assignment_ref="artifact://scene/assignment", candidate_ref=request["candidates"][0]["candidate_ref"],
                      selected_arm_ids=["left"], route_digest="b" * 64, capability_snapshot_ref=request["capability_snapshot_ref"],
                      readiness_evidence_ref="artifact://prep-7/kinematic-1", decision_basis=["complete_route"])
    assignment["assignment_digest"] = arm_assignment_digest(assignment)
    # Include defaults in the digest, as required by the existing typed model.
    assignment.update(schema_version="paos-arm-assignment/v1", alternatives=[], motion_authorized=False)
    assignment["assignment_digest"] = arm_assignment_digest(assignment)
    result = {"prepared_candidates": [prepared(1)], "provider_available": True,
              "assignments": [assignment], "destination_ref": request["destination_ref"]}
    return request, result


def test_preparation_returns_typed_bound_assignment_with_no_motion_authority():
    request, result = request_and_result()
    class Provider:
        def prepare(self, arguments):
            return result
    output = ManipulationPreparationEndpoint(Provider()).invoke(request)
    assert output["status"] == "available"
    assert output["assignments"][0]["selected_arm_ids"] == ["left"]
    assert output["motion_authorized"] is False
    jsonschema.validate(request, MANIPULATION_TOOL_SPEC["input_schema"])
    jsonschema.validate(output, MANIPULATION_TOOL_SPEC["output_schema"])


@pytest.mark.parametrize("field,value", [("task_id", "other"), ("scene_revision", "other"),
                                        ("capability_snapshot_ref", "artifact://other/capability"),
                                        ("readiness_evidence_ref", "artifact://other/readiness"),
                                        ("selected_arm_ids", ["right"])])
def test_preparation_rejects_assignment_binding_drift(field, value):
    request, result = request_and_result()
    result = deepcopy(result)
    result["assignments"][0][field] = value
    result["assignments"][0]["assignment_digest"] = arm_assignment_digest(result["assignments"][0])
    class Provider:
        def prepare(self, arguments):
            return result
    output = ManipulationPreparationEndpoint(Provider()).invoke(request)
    assert output["status"] == "invalid"
    assert output["error"]["code"] == "invalid_assignment_binding"


def test_incomplete_route_request_never_calls_provider():
    request, _ = request_and_result()
    del request["destination_ref"]
    class Provider:
        def prepare(self, arguments):
            pytest.fail("invalid request reached provider")
    assert ManipulationPreparationEndpoint(Provider()).invoke(request)["status"] == "invalid"
