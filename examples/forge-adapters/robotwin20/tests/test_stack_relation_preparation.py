from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
from test_persistent_preparation import composition
from test_route_inputs import _facts

from robotwin20_adapter.grounding import Grounding
from robotwin20_adapter.persistent_action_approval import PersistentSimulationActionApprover
from robotwin20_adapter.route_inputs import CURRENT_SCENE_FACTS_SCHEMA_VERSION, validate_scene_facts
from robotwin20_adapter.stack_relation_preparation import (
    StackRelationPreparationError,
    build_stack_relation_execution_provider_factory,
    build_stack_relation_route_preparation,
)


def composed(tmp_path):
    inputs, provider, routes = composition(tmp_path)
    intent = inputs["intent"]
    identity = {key: inputs[key] for key in ("scene_revision", "observation_ref", "calibration_ref")}
    provider.client.snapshot["scene_validity"] = "action_driven"
    # Grounding and preparation use the same current-scene client; no Action API exists.
    grounding = Grounding(provider.client, tmp_path, None)
    source = np.eye(4)
    source[:3, 3] = [0.1, 0.2, 0.3]
    functional = source.copy()
    functional[2, 3] += 0.02
    obj = _facts()["objects"][0]
    obj.update(entity_ref=intent["entity_ref"], world_T_object=source.reshape(-1).tolist(),
               world_T_functional_point=functional.reshape(-1).tolist())
    for key in ("world_T_object_target", "world_T_functional_target", "target_ref"):
        obj.pop(key)
    scene = _facts()
    scene.update(identity, schema_version=CURRENT_SCENE_FACTS_SCHEMA_VERSION, objects=[obj])
    grounding.bindings[inputs["binding_ref"]] = {
        **identity, "frame_id": inputs["frame_id"], "objects": {intent["entity_ref"]: obj},
        "scene_facts": scene,
    }
    target = np.eye(4)
    target[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    target[:3, 3] = [0.3, 0.4, 0.5]
    relation = {
        "entity_ref": intent["entity_ref"], "destination_ref": inputs["destination_ref"],
        "world_T_object_target": target.reshape(-1).tolist(),
        "evidence_refs": ["artifact://relation/support"],
    }
    request = {**identity, "entity_ref": intent["entity_ref"], "intent": deepcopy(intent),
               "observation_frame_id": inputs["frame_id"], "relation_binding": relation,
               "candidate_ref": "relation-target://support/1"}
    inputs["target_geometry_source"] = "simulator_actor_geometry"
    provider.approval_issuer = PersistentSimulationActionApprover(
        tmp_path, task_name="stack_blocks_three", mode="runtime_monitored")
    builder = provider.route_builder
    seen = []
    # Only external planning is substituted: production Grounding.scene_facts,
    # PersistentPreparationProvider, CompleteRouteSelector and PreparedRoutes run.
    query = provider.client.query
    provider.client.query = lambda operation, arguments, **kw: (
        {} if operation == "bind_observed_entities" else query(operation, arguments, **kw))
    grounding._observed_support = lambda binding: None
    def build(arguments, **kwargs):
        facts = validate_scene_facts(grounding.scene_facts(arguments))
        seen.append(facts)
        bundle = builder.build(arguments, **kwargs)
        for candidate in bundle["base_request"]["candidates"]:
            candidate["placement_target"]["target_ref"] = arguments["destination_ref"]
        for option in bundle["options"]:
            option["candidate"]["placement_target"]["target_ref"] = arguments["destination_ref"]
        return bundle
    provider.route_builder = SimpleNamespace(build=build)
    deployment = SimpleNamespace(preparation_provider=provider, grounding=grounding)
    return request, inputs, deployment, seen


def test_real_preparation_preserves_intent_and_projects_relation_geometry(tmp_path):
    request, inputs, deployment, seen = composed(tmp_path)
    original = deepcopy((request, inputs))
    route = build_stack_relation_route_preparation(
        deployment, prepare_inputs=lambda req, task: inputs)(request, "task-1")
    assert (request, inputs) == original
    assert route["assignment"]["task_id"] == "task-1"
    assert route["task_id"] == "task-1"
    assert route["candidate_ref"].startswith("candidate://")
    assert route["candidate_ref"] != request["candidate_ref"]
    assert route["approval_ref"].startswith("artifact://")
    for key in ("observation_ref", "frame_id", "calibration_ref", "candidate_set_ref", "capability_snapshot_ref"):
        assert route[key] == inputs[key]
    assert route["preparation_ref"].startswith("preparation://")
    facts = seen[0]
    assert facts["geometry_source"] == "observation"
    assert facts["target_geometry_source"] == "simulator_actor_geometry"
    assert facts["target_evidence_refs"] == ["artifact://relation/support"]
    target = np.asarray(request["relation_binding"]["world_T_object_target"]).reshape(4, 4)
    obj = facts["objects"][0]
    assert obj["world_T_object_target"] == target.reshape(-1).tolist()
    expected = target.copy()
    expected[2, 3] += 0.02
    np.testing.assert_allclose(np.asarray(obj["world_T_functional_target"]).reshape(4, 4), expected)


@pytest.mark.parametrize("key", ["intent", "binding_ref", "capability_snapshot_ref", "candidates", "target_geometry_source"])
def test_missing_inputs_rejected_without_target_publication(tmp_path, key):
    request, inputs, deployment, seen = composed(tmp_path)
    inputs.pop(key)
    with pytest.raises(ValueError):
        build_stack_relation_route_preparation(deployment, prepare_inputs=lambda *args: inputs)(request, "task-1")
    assert not seen
    assert not deployment.grounding.targets
    assert not (tmp_path / "relation-targets").exists()


@pytest.mark.parametrize("key", ["scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref", "frame_id"])
def test_input_identity_drift_rejected_before_binding(tmp_path, key):
    request, inputs, deployment, seen = composed(tmp_path)
    inputs[key] += "-wrong"
    with pytest.raises(StackRelationPreparationError):
        build_stack_relation_route_preparation(deployment, prepare_inputs=lambda *args: inputs)(request, "task-1")
    assert not seen
    assert not deployment.grounding.targets


def test_stale_world_rejected_without_target_publication(tmp_path):
    request, inputs, deployment, seen = composed(tmp_path)
    deployment.preparation_provider.client.snapshot["scene_revision"] = "next-scene"
    with pytest.raises(ValueError, match="stale"):
        build_stack_relation_route_preparation(deployment, prepare_inputs=lambda *args: inputs)(request, "task-1")
    assert not seen
    assert not deployment.grounding.targets


@pytest.mark.parametrize("change", ["entity", "pose", "evidence"])
def test_bad_relation_rejected_before_writing(tmp_path, change):
    request, inputs, deployment, seen = composed(tmp_path)
    binding = request["relation_binding"]
    if change == "entity":
        binding["entity_ref"] = "entity://other"
    elif change == "pose":
        binding["world_T_object_target"] = [0.0] * 16
    else:
        binding["evidence_refs"] = []
    with pytest.raises(ValueError):
        build_stack_relation_route_preparation(deployment, prepare_inputs=lambda *args: inputs)(request, "task-1")
    assert not seen
    assert not deployment.grounding.targets
    assert not (tmp_path / "relation-targets").exists()


def test_real_preparation_failure_propagates_without_action(tmp_path):
    request, inputs, deployment, seen = composed(tmp_path)
    def fail(*args, **kwargs):
        raise RuntimeError("planner offline")
    deployment.preparation_provider.route_builder = SimpleNamespace(build=fail)
    with pytest.raises(RuntimeError, match="planner offline"):
        build_stack_relation_route_preparation(deployment, prepare_inputs=lambda *args: inputs)(request, "task-1")
    assert not deployment.preparation_provider.prepared_routes._routes


def test_unconfigured_resolver_and_closed_motion_factory(tmp_path):
    request, inputs, deployment, seen = composed(tmp_path)
    with pytest.raises(StackRelationPreparationError, match="not configured"):
        build_stack_relation_route_preparation(deployment)(request, "task-1")
    provider = build_stack_relation_execution_provider_factory()(object(), deployment)
    admission = provider.admit(request, invocation_id="invocation-1", attempt_id="attempt-1")
    assert admission.terminal_result["error"]["code"] == "stack_relation_motion_unqualified"
    assert admission.driver is None
    assert not seen


@pytest.mark.parametrize("field", ["destination", "candidate_target"])
def test_prepared_destination_drift_is_rejected(tmp_path, field):
    request, inputs, deployment, seen = composed(tmp_path)
    original = deployment.preparation_provider.prepare
    def prepare(arguments):
        result = original(arguments)
        route = result["route_arguments"]
        if field == "destination":
            route["destination_ref"] = "destination://other"
        else:
            route["route_request"]["candidates"][0]["placement_target"]["target_ref"] = "destination://other"
        return result
    deployment.preparation_provider.prepare = prepare
    with pytest.raises(StackRelationPreparationError):
        build_stack_relation_route_preparation(deployment, prepare_inputs=lambda *args: inputs)(request, "task-1")
