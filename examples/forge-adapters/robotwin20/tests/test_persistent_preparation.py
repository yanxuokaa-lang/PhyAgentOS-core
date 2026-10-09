import json
import time
from copy import deepcopy

import pytest
from PhyAgentOS.forge.capability_runtime.manipulation_prepare import preparation_ref_for_request
from test_arm_candidates import _intent, _profile, _result
from test_route_readiness import _request

from robotwin20_adapter.arm_candidates import (
    CompleteRouteSelector,
    build_capability_snapshot,
    enumerate_arm_candidates,
)
from robotwin20_adapter.persistent_preparation import PersistentPreparationProvider
from robotwin20_adapter.prepared_routes import PreparedRoutes
from robotwin20_adapter.route_evidence import _artifact_path


def composition(tmp_path, *, status="pass", node_id="pick-red", task_id="task-1"):
    intent = _intent().model_copy(update={"node_id": node_id, "task_id": task_id})
    route = _request(tmp_path)
    profile = _profile()
    capability = build_capability_snapshot(
        profile, scene_revision=intent.scene_revision,
        observation_ref=intent.observation_ref, calibration_ref=intent.calibration_ref,
        profile_digest="1" * 64, snapshot_ref="artifact://scene/capability",
    )
    (tmp_path / "scene").mkdir(exist_ok=True)
    (tmp_path / "scene/capability.json").write_text(capability.model_dump_json())
    request = {key: getattr(intent, key) for key in (
        "scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref",
    )}
    request.update(intent=intent.model_dump(mode="json"), frame_id=intent.observation_frame_id,
                   binding_ref="artifact://entity-bindings/current",
                   destination_ref="destination://slot", capability_snapshot_ref=capability.snapshot_ref,
                   candidates=deepcopy(route["candidates"]))

    class Client:
        snapshot = {"scene_revision": intent.scene_revision, "holding_state": "empty"}

        def query(self, operation, arguments, *, timeout_s=None):
            assert operation == "snapshot"
            return deepcopy(self.snapshot)

    class Builder:
        def build(self, arguments, *, deadline=None, metrics=None):
            return {"destination_ref": arguments["destination_ref"], "base_request": route,
                    "options": enumerate_arm_candidates(intent, route["candidates"], profile)}

    def evaluate(current_route, option):
        result = _result(current_route, option, status=status)
        result.update(
            task_id=intent.task_id,
            revision_id=intent.revision_id,
            node_id=intent.node_id,
            node_digest=intent.node_digest,
        )
        return result

    client = Client()
    routes = PreparedRoutes(client, tmp_path)
    provider = PersistentPreparationProvider(
        client=client, route_builder=Builder(),
        selector=CompleteRouteSelector(evaluate, profile), prepared_routes=routes,
    )
    return request, provider, routes


@pytest.mark.parametrize("node_id", ["pick-red", "pick.red"])
def test_selection_registers_geometry_but_requires_separate_approval(tmp_path, node_id):
    request, provider, routes = composition(tmp_path, node_id=node_id)
    output = provider.prepare(request)
    assignment = output["assignments"][0]
    expected_preparation_ref = preparation_ref_for_request(request)
    assert expected_preparation_ref == (
        f"preparation://blocks_ranking_rgb-0-1/task-1/revision-1/{node_id}/head_camera"
    )
    assert json.loads(_artifact_path(tmp_path, assignment["assignment_ref"]).read_text()) == assignment
    assert assignment["motion_authorized"] is False
    arguments = {key: request[key] for key in (
        "scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref", "frame_id", "capability_snapshot_ref",
    )}
    arguments.update(preparation_ref=expected_preparation_ref,
                     candidate_ref=assignment["candidate_ref"], entity_ref=assignment["entity_ref"],
                     assignment_ref=assignment["assignment_ref"])
    with pytest.raises(ValueError, match="no execution approval"):
        routes("acquire", arguments)
    (tmp_path / "scene/approval.json").write_text("{}")
    routes.bind_approval(arguments["preparation_ref"], arguments["candidate_ref"], "artifact://scene/approval")
    assert routes("acquire", arguments)["assignment"] == assignment
    assert provider.prepare(request) == output
    assert routes("acquire", arguments)["approval_ref"] == "artifact://scene/approval"


def test_preparation_identity_isolated_across_tasks_with_same_scene_and_frame(tmp_path):
    request_one, provider_one, routes = composition(tmp_path, task_id="task-1")
    request_two, provider_two, _ = composition(tmp_path, task_id="task-2")
    provider_two.prepared_routes = routes

    output_one = provider_one.prepare(request_one)
    preparation_one = next(iter(routes._routes.values()))["preparation_ref"]
    provider_two.prepare(request_two)
    preparation_two = next(
        value for value in routes._routes.values()
        if value["assignment"]["task_id"] == "task-2"
    )["preparation_ref"]
    assert preparation_one != preparation_two
    assert preparation_one.startswith(
        "preparation://blocks_ranking_rgb-0-1/task-1/"
    )
    assert preparation_two.startswith(
        "preparation://blocks_ranking_rgb-0-1/task-2/"
    )
    assert len(routes._routes) == 2
    assert provider_one.prepare(request_one) == output_one


def test_runtime_monitored_preparation_issues_route_bound_approval(tmp_path):
    from robotwin20_adapter.persistent_action_approval import (
        PersistentSimulationActionApprover,
        validate_persistent_action_approval,
    )

    request, provider, routes = composition(tmp_path)
    provider.approval_issuer = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    )
    output = provider.prepare(request)
    assignment = output["assignments"][0]
    prepared = next(iter(routes._routes.values()))
    approval = validate_persistent_action_approval(
        tmp_path,
        prepared["approval_ref"],
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
        route_request=prepared["route_request"],
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
    )
    assert approval["assignment_ref"] == assignment["assignment_ref"]


def test_deferred_route_uses_core_prepared_qualification(tmp_path):
    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import (
        normalize_snapshot,
        validate_snapshot,
    )

    request, provider, _ = composition(tmp_path)
    original = provider.selector.evaluator

    def evaluate(route_request, option):
        result = original(route_request, option)
        result = dict(result)
        result.update(
            status="deferred",
            phase="none",
            code="execution_checks_deferred",
            detail="dynamic checks run inside the admitted simulation Action",
        )
        result["checks"] = dict(result["checks"])
        result["checks"].update(contact_dynamics="deferred", stop_control="deferred")
        return result

    provider.selector = CompleteRouteSelector(
        evaluate,
        _profile(),
        deferred_checks=("contact_dynamics", "stop_control"),
    )
    output = provider.prepare(request)
    assert output["prepared_candidates"][0]["qualification"] == "prepared"
    snapshot = normalize_snapshot(output)
    assert snapshot is not None
    assert validate_snapshot(
        snapshot,
        candidate_entities={item["candidate_ref"]: item["entity_ref"] for item in request["candidates"]},
    ) is None
    assert output["assignments"][0]["decision_basis"][:2] == [
        "complete_route_static_readiness",
        "execution_checks_deferred",
    ]


def test_failed_complete_routes_produce_no_prepared_assignment(tmp_path):
    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import PreparationProviderError

    request, provider, routes = composition(tmp_path, status="fail")
    with pytest.raises(PreparationProviderError, match="route collides") as caught:
        provider.prepare(request)
    assert caught.value.code == "no_admissible_route"
    assert caught.value.failure_owner == "planning"
    assert caught.value.requires_replan is True
    assert caught.value.recommended_action == "replan_from_provider_result"
    saved = json.loads(next((tmp_path / "preparation-rejections").glob("*.json")).read_text())
    assert len(saved["failed_routes"]) == 2
    assert not routes._routes
    assert not (tmp_path / "assignments").exists()


def test_observed_uncertainty_reaches_public_failure_without_changing_recovery_code(tmp_path):
    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import PreparationProviderError

    request, provider, _ = composition(tmp_path, status="fail")
    metrics = {"contact_qualification": [{"candidate_ref": request["candidates"][0]["candidate_ref"],
               "observed_collision": {"visibility_scope": "observed_only"},
               "visibility": {"occluded_samples": 12, "unobserved_samples": 4},
               "evidence_ref": "artifact://contact/0"}]}
    with pytest.raises(PreparationProviderError, match="unobserved space remains unknown") as caught:
        provider.prepare(request, metrics=metrics)
    assert caught.value.code == "no_admissible_route"
    assert caught.value.failure_owner == "planning"
    assert caught.value.requires_replan is True
    assert caught.value.recommended_action == "replan_from_provider_result"
    assert "artifact://contact/0" in str(caught.value)
    assert "'occluded_samples': 12" in str(caught.value)


def test_readiness_infrastructure_failure_is_not_an_empty_candidate_set(tmp_path):
    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import PreparationProviderError

    request, provider, routes = composition(tmp_path)

    def unavailable(*args):
        raise ValueError("observation model provenance mismatch")

    provider.selector.evaluator = unavailable
    with pytest.raises(PreparationProviderError, match="observation model provenance mismatch") as caught:
        provider.prepare(request)
    assert caught.value.code == "readiness_provider_unavailable"
    assert caught.value.failure_owner == "runtime_provider"
    assert caught.value.retryable_in_revision is False
    assert caught.value.requires_replan is False
    assert caught.value.recommended_action == "fix_runtime_contract"
    assert not routes._routes


def test_arm_planning_contract_failure_is_public_and_not_replanned(tmp_path):
    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import PreparationProviderError

    from robotwin20_adapter.arm_candidates import ArmProfileBindingError

    request, provider, routes = composition(tmp_path)

    def fail_build(*_args, **_kwargs):
        raise ArmProfileBindingError("route option arm profile binding is invalid")

    provider.route_builder.build = fail_build
    metrics = {}
    with pytest.raises(PreparationProviderError) as caught:
        provider.prepare(request, metrics=metrics)

    assert caught.value.code == "arm_planning_contract_invalid"
    assert str(caught.value) == "route option arm profile binding is invalid"
    assert caught.value.failure_owner == "runtime_adapter"
    assert caught.value.retryable_in_revision is False
    assert caught.value.requires_replan is False
    assert caught.value.recommended_action == "fix_runtime_contract"
    assert metrics["failure"]["type"] == "ArmProfileBindingError"
    assert not routes._routes


def test_other_arm_planning_failures_are_not_misclassified_as_binding_contracts(tmp_path):
    from robotwin20_adapter.arm_candidates import ArmPlanningError

    request, provider, _ = composition(tmp_path)

    def fail_build(*_args, **_kwargs):
        raise ArmPlanningError("arm candidate enumeration exceeds configured max_options")

    provider.route_builder.build = fail_build
    with pytest.raises(ArmPlanningError, match="exceeds configured max_options"):
        provider.prepare(request)


def test_finalized_review_is_exposed_as_preparation_evidence(tmp_path):
    request, provider, routes = composition(tmp_path)
    ref = "artifact://selected/review"
    provider.route_builder.finalize = lambda bundle, route, **_kwargs: ref
    result = provider.prepare(request)
    assert ref in result["prepared_candidates"][0]["evidence"]
    assert next(iter(routes._routes.values()))["review_request_ref"] == ref


def test_planner_contact_diagnostic_is_exposed_as_preparation_evidence(tmp_path):
    request, provider, _ = composition(tmp_path)
    ref = "artifact://contact/planner-world-0"
    result = provider.prepare(
        request,
        metrics={
            "contact_qualification": [
                {
                    "candidate_ref": request["candidates"][0]["candidate_ref"],
                    "mode": "planner_world_only",
                    "evidence_ref": ref,
                }
            ]
        },
    )
    assert ref in result["prepared_candidates"][0]["evidence"]


def test_finalization_failure_does_not_register_executable_route(tmp_path):
    request, provider, routes = composition(tmp_path)

    def fail(bundle, route, **_kwargs):
        raise ValueError("source manifest mismatch")

    provider.route_builder.finalize = fail
    with pytest.raises(ValueError, match="manifest mismatch"):
        provider.prepare(request)
    assert not routes._routes
    assert not (tmp_path / "assignments").exists()


@pytest.mark.parametrize("change", ["scene", "holding", "destination"])
def test_changed_world_or_destination_is_not_published(tmp_path, change):
    request, provider, routes = composition(tmp_path)
    original = provider.route_builder.build

    def build(arguments, **kwargs):
        bundle = original(arguments, **kwargs)
        if change == "scene":
            provider.client.snapshot["scene_revision"] = "next-scene"
        elif change == "holding":
            provider.client.snapshot["holding_state"] = "holding"
        else:
            bundle["destination_ref"] = "destination://other"
        return bundle

    provider.route_builder.build = build
    with pytest.raises(ValueError, match="world changed|destination"):
        provider.prepare(request)
    assert not routes._routes
    assert not (tmp_path / "assignments").exists()


def test_complete_preparation_deadline_spans_builder_and_selector(tmp_path):
    request, provider, routes = composition(tmp_path)
    original = provider.route_builder.build

    def slow_build(arguments, **kwargs):
        time.sleep(0.02)
        return original(arguments, **kwargs)

    provider.route_builder.build = slow_build
    provider.timeout_s = 0.005

    with pytest.raises(TimeoutError, match="deadline"):
        provider.prepare(request)
    assert not routes._routes
    assert not (tmp_path / "assignments").exists()


def test_snapshot_calls_receive_remaining_total_budget(tmp_path):
    request, provider, routes = composition(tmp_path)
    original = provider.client.query
    budgets = []

    def query(operation, arguments, *, timeout_s=None):
        assert timeout_s is not None and 0 < timeout_s <= provider.timeout_s
        budgets.append(timeout_s)
        return original(operation, arguments)

    provider.client.query = query
    provider.prepare(request)
    assert len(budgets) == 2
    assert budgets[1] < budgets[0]
    assert routes._routes


@pytest.mark.parametrize("worker_code,public_code", [
    ("BindingPoseChangedError", "binding_pose_changed"),
    ("BindingPoseUnavailableError", "binding_pose_unavailable"),
])
def test_worker_binding_rejection_is_a_public_preparation_failure(tmp_path, worker_code, public_code):
    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import PreparationProviderError

    from robotwin20_adapter.persistent_client import PersistentWorkerClient

    request, provider, routes = composition(tmp_path)

    class Worker:
        def request(self, payload):
            return {"ok": False, "error": {"code": worker_code, "message": "/private/internal/detail"}}

    client = PersistentWorkerClient(Worker())

    def fail_build(arguments, **kwargs):
        return client.query("bind_observed_entities", {})

    provider.route_builder.build = fail_build
    metrics = {}
    with pytest.raises(PreparationProviderError) as caught:
        provider.prepare(request, metrics=metrics)
    assert caught.value.code == public_code
    assert caught.value.failure_owner == "evidence"
    assert caught.value.requires_replan is True
    assert caught.value.recommended_action == "refresh_declared_evidence"
    assert caught.value.fresh_evidence_requirements == ("current_observation_lineage",)
    assert "/private" not in str(caught.value)
    assert not client._transport_lost
    assert metrics["status"] == "failed"
    assert not routes._routes
