from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from robotwin20_adapter.stack_relation_execution import StackRelationExecutionProvider
from robotwin20_adapter.stack_relation_preparation import (
    StackRelationPreparationError,
    build_stack_relation_execution_provider_factory,
    build_stack_relation_route_preparation,
)

ENTITY_REF = "entity://stack-block-2"
DESTINATION_REF = "destination://stack-block-1"
SCENE_REVISION = "stack-0-2"


def _request():
    return {
        "entity_ref": ENTITY_REF,
        "goal_relation": "on",
        "relation_target_ref": "entity://stack-block-1",
        "scene_revision": SCENE_REVISION,
        "observation_ref": "observation://stack/2",
        "observation_frame_id": "camera-head",
        "calibration_ref": "artifact://calibration",
        "intent": {"task_id": "task-1", "motion_authorized": False},
        "relation_binding": {
            "entity_ref": ENTITY_REF,
            "relation_target_ref": "entity://stack-block-1",
            "destination_ref": DESTINATION_REF,
            "world_T_object_target": [0.0] * 16,
            "evidence_refs": ["artifact://relation/target"],
        },
    }


def _prepared_result():
    """Mirror the persistent prepare result produced by PersistentPreparationProvider."""
    assignment = {
        "task_id": "task-1",
        "entity_ref": ENTITY_REF,
        "candidate_ref": "candidate://stack-block-2/g1",
        "assignment_ref": "artifact://assignments/1",
    }
    route_request = {
        "request_id": "route-1",
        "scene_revision": SCENE_REVISION,
        "destination_ref": DESTINATION_REF,
        "candidates": [{
            "candidate_ref": assignment["candidate_ref"],
            "entity_ref": assignment["entity_ref"],
        }],
    }
    route_arguments = {
        "observation_ref": "observation://stack/2",
        "scene_revision": SCENE_REVISION,
        "frame_id": "camera-head",
        "calibration_ref": "artifact://calibration",
        "candidate_set_ref": "candidate-set://stack",
        "capability_snapshot_ref": "artifact://capability",
        "preparation_ref": f"preparation://{SCENE_REVISION}/task-1/rev-1/node-1/camera-head",
        "candidate_ref": assignment["candidate_ref"],
        "entity_ref": assignment["entity_ref"],
        "assignment_ref": assignment["assignment_ref"],
        "route_request": route_request,
        "approval_ref": "artifact://approvals/1",
        "destination_ref": DESTINATION_REF,
        "assignment": assignment,
    }
    return {
        "prepared_candidates": [{
            "candidate_ref": assignment["candidate_ref"],
            "entity_ref": assignment["entity_ref"],
            "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
            "evidence": ["artifact://evidence/1"],
            "qualification": "prepared",
        }],
        "provider_available": True,
        "assignments": [assignment],
        "destination_ref": DESTINATION_REF,
        "route_arguments": route_arguments,
    }


class FakePreparation:
    """Record the manipulation.prepare request; never start any Action."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.requests = []
        self.started = []

    def prepare(self, request, *, metrics=None):
        self.requests.append(deepcopy(dict(request)))
        if self.error is not None:
            raise self.error
        return deepcopy(self.result if self.result is not None else _prepared_result())

    def start(self, *arguments):
        self.started.append(arguments)


def _deployment(fake):
    return SimpleNamespace(preparation_provider=fake)


def test_prepare_route_returns_validated_relation_route():
    fake = FakePreparation()
    request = _request()
    route = build_stack_relation_route_preparation(_deployment(fake))(request, "task-1")

    StackRelationExecutionProvider._validate_route(route, request, "task-1")
    assert route["route_request"]["destination_ref"] == DESTINATION_REF
    assert route["route_request"]["destination_ref"] == request["relation_binding"]["destination_ref"]
    assert route["entity_ref"] == request["relation_binding"]["entity_ref"]
    assert route["approval_ref"].startswith("artifact://")
    assert set((
        "scene_revision", "entity_ref", "candidate_ref", "assignment_ref",
        "assignment", "route_request", "approval_ref",
    )) <= set(route)
    prepare_request = fake.requests[0]
    assert "relation_binding" not in prepare_request
    assert "intent" not in prepare_request
    assert prepare_request["destination_ref"] == DESTINATION_REF
    assert prepare_request["entity_ref"] == ENTITY_REF
    assert prepare_request["scene_revision"] == SCENE_REVISION
    assert prepare_request["observation_ref"] == request["observation_ref"]
    assert prepare_request["calibration_ref"] == request["calibration_ref"]


@pytest.mark.parametrize("mutate", [
    lambda request: request.pop("relation_binding"),
    lambda request: request["relation_binding"].pop("destination_ref"),
    lambda request: request["relation_binding"].pop("entity_ref"),
    lambda request: request.pop("entity_ref"),
    lambda request: request.pop("scene_revision"),
])
def test_prepare_route_requires_relation_binding_fields_before_preparing(mutate):
    fake = FakePreparation()
    request = _request()
    mutate(request)

    with pytest.raises(StackRelationPreparationError, match="relation binding fields are missing"):
        build_stack_relation_route_preparation(_deployment(fake))(request, "task-1")

    assert fake.requests == []


def test_prepare_route_rejects_destination_diverged_from_relation_binding():
    result = _prepared_result()
    result["route_arguments"]["route_request"]["destination_ref"] = "destination://elsewhere"
    fake = FakePreparation(result=result)

    with pytest.raises(
        StackRelationPreparationError, match="differs from current relation target"
    ):
        build_stack_relation_route_preparation(_deployment(fake))(_request(), "task-1")


def test_prepare_route_propagates_preparation_failure_without_starting_motion():
    failure = RuntimeError("materializer offline")
    fake = FakePreparation(error=failure)

    with pytest.raises(RuntimeError) as excinfo:
        build_stack_relation_route_preparation(_deployment(fake))(_request(), "task-1")

    assert excinfo.value is failure
    assert len(fake.requests) == 1
    assert fake.started == []


def test_factory_composes_provider_with_closed_motion_gate():
    fake = FakePreparation()
    client = SimpleNamespace(start=lambda *_arguments: (_ for _ in ()).throw(AssertionError("no motion")))

    provider = build_stack_relation_execution_provider_factory()(client, _deployment(fake))

    assert isinstance(provider, StackRelationExecutionProvider)
    assert provider.client is client
    assert provider.motion_supported() is False
    admission = provider.admit(_request(), invocation_id="gateway-1", attempt_id="attempt-1")
    assert admission.driver is None
    assert admission.terminal_result["status"] == "failed"
    assert admission.terminal_result["error"]["code"] == "stack_relation_motion_unqualified"
    assert fake.requests == []
