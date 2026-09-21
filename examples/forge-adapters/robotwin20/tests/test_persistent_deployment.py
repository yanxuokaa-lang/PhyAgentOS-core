from pathlib import Path

import pytest
import yaml
from test_arm_candidates import _profile

from robotwin20_adapter.persistent_action_approval import (
    PersistentSimulationActionApprover,
)
from robotwin20_adapter.persistent_client import PersistentWorkerError
from robotwin20_adapter.persistent_deployment import (
    PersistentTaskGoalProvider,
    TaskGoalEndpoint,
    build_persistent_deployment,
    build_persistent_runtime_bundle,
)


def test_deployment_wires_shared_cache_and_requires_persistent_stop_policy(tmp_path):
    arm = tmp_path / "arms.yaml"
    arm.write_text(yaml.safe_dump(_profile()))
    profiles = Path(__file__).parents[1] / "profiles/robotwin20"
    arguments = {"arm-planning-profile": str(arm),
                 "route-input-profile": str(profiles / "route-inputs-persistent.yaml")}
    client = object()
    deployment = build_persistent_deployment(
        client=client, artifact_root=tmp_path, scene_source=lambda request: None,
        materializer_command=("python", "materializer.py"), materializer_arguments=arguments,
        arm_profile_digest="a" * 64,
    )
    assert deployment.preparation_provider.client is client
    assert deployment.preparation_provider.prepared_routes is deployment.prepared_routes
    assert deployment.runtime_arguments()["resolve_preparation"] is deployment.prepared_routes
    assert deployment.capability_provider.client is client
    assert deployment.preparation_provider.route_builder.scene_source.__name__ == "scene_facts"
    oracle = build_persistent_deployment(
        client=client, artifact_root=tmp_path, scene_source=lambda request: None,
        materializer_command=("python", "materializer.py"), materializer_arguments=arguments,
        arm_profile_digest="a" * 64, route_geometry_source="oracle",
    )
    assert oracle.preparation_provider.route_builder.scene_source.__name__ == "oracle_scene_facts"
    assert oracle.preparation_provider.approval_issuer is None
    assert oracle.preparation_provider.selector.deferred_checks == frozenset()
    monitored = build_persistent_deployment(
        client=client, artifact_root=tmp_path, scene_source=lambda request: None,
        materializer_command=("python", "materializer.py"), materializer_arguments=arguments,
        arm_profile_digest="a" * 64, route_geometry_source="oracle",
        simulation_action_mode="runtime_monitored", task_name="blocks_ranking_rgb",
    )
    assert isinstance(
        monitored.preparation_provider.approval_issuer,
        PersistentSimulationActionApprover,
    )
    assert monitored.preparation_provider.selector.deferred_checks == frozenset(
        {"contact_dynamics", "stop_control"}
    )
    with pytest.raises(ValueError, match="require oracle route geometry"):
        build_persistent_deployment(
            client=client, artifact_root=tmp_path, scene_source=lambda request: None,
            materializer_command=("python", "materializer.py"), materializer_arguments=arguments,
            arm_profile_digest="a" * 64, route_geometry_source="observed",
            simulation_action_mode="runtime_monitored", task_name="blocks_ranking_rgb",
        )
    with pytest.raises(ValueError, match="observed or oracle"):
        build_persistent_deployment(
            client=client, artifact_root=tmp_path, scene_source=lambda request: None,
            materializer_command=("python",), materializer_arguments=arguments,
            arm_profile_digest="a" * 64, route_geometry_source="automatic",
        )
    arguments["route-input-profile"] = str(profiles / "route-inputs.yaml")
    with pytest.raises(ValueError, match="hold_and_reconcile"):
        build_persistent_deployment(
            client=client, artifact_root=tmp_path, scene_source=lambda request: None,
            materializer_command=("python",), materializer_arguments=arguments,
            arm_profile_digest="a" * 64,
        )


def test_task_goal_endpoint_preserves_worker_rejection_but_not_transport_loss():
    class Client:
        error = None

        def query(self, operation, arguments):
            assert operation == "task_goal_facts"
            assert arguments == {}
            if self.error is not None:
                raise self.error
            return {
                "status": "available",
                "motion_authorized": False,
                "goals": [{"destination_ref": "destination://goal"}],
            }

    client = Client()
    endpoint = TaskGoalEndpoint(PersistentTaskGoalProvider(client))
    available = endpoint.invoke({})
    assert available["status"] == "available"
    assert available["goal_source"] == "benchmark_task_definition"

    client.error = PersistentWorkerError({"code": "task_goal_invalid"})
    rejected = endpoint.invoke({})
    assert rejected["status"] == "unavailable"
    assert rejected["error"]["code"] == "task_goal_unavailable"

    client.error = RuntimeError("persistent world connection lost")
    with pytest.raises(RuntimeError, match="connection lost"):
        endpoint.invoke({})


def test_observation_owned_goal_provider_never_queries_benchmark_facts():
    class Client:
        def query(self, *_args, **_kwargs):
            raise AssertionError("observation-owned profile queried benchmark facts")

    result = PersistentTaskGoalProvider(
        Client(), goal_source="observation_owned"
    ).goal({})

    assert result == {
        "status": "unavailable",
        "motion_authorized": False,
        "error": {
            "code": "benchmark_goal_disabled",
            "message": "observation-owned profile does not expose benchmark destinations",
        },
    }


def test_runtime_bundle_registers_persistent_tools_behind_one_transport(tmp_path):
    arm = tmp_path / "arms.yaml"
    arm.write_text(yaml.safe_dump(_profile()))
    profiles = Path(__file__).parents[1] / "profiles/robotwin20"
    arguments = {
        "arm-planning-profile": str(arm),
        "route-input-profile": str(profiles / "route-inputs-persistent.yaml"),
    }
    client = object()
    deployment = build_persistent_deployment(
        client=client, artifact_root=tmp_path, scene_source=lambda request: None,
        materializer_command=("python",), materializer_arguments=arguments,
        arm_profile_digest="a" * 64,
    )
    bundle = build_persistent_runtime_bundle(
        deployment=deployment,
        client=client,
        understanding_provider=object(),
        grasp_provider=object(),
        tool_context_provider=lambda tool_id: {"ready": True, "tool_id": tool_id},
    )
    assert bundle.client_transport() is bundle.transport
    assert {item["tool_id"] for item in bundle.runtime.list_tools()["tools"]} == {
        "scene.observe", "manipulation.capabilities", "scene.understand",
        "grasp.propose", "manipulation.prepare", "object.acquire", "object.place",
        "scene.bind", "task.goal", "manipulation.target",
    }
    task_goal = next(
        item for item in bundle.runtime.list_tools()["tools"]
        if item["tool_id"] == "task.goal"
    )
    assert task_goal["planning"]["requires_before_plan"] is False
    with pytest.raises(ValueError, match="share one worker client"):
        build_persistent_runtime_bundle(
            deployment=deployment, client=object(),
            understanding_provider=object(), grasp_provider=object(),
            tool_context_provider=lambda tool_id: {"ready": True},
        )
