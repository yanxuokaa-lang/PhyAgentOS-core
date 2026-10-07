from pathlib import Path

import pytest
import yaml
from test_arm_candidates import _profile
from test_controller_qualification import _plan

from robotwin20_adapter.controller_qualification import qualification_capability_ref
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
        arm_profile_digest="a" * 64, depth_scale_to_m=0.002,
    )
    assert deployment.preparation_provider.client is client
    assert deployment.preparation_provider.prepared_routes is deployment.prepared_routes
    assert deployment.runtime_arguments()["resolve_preparation"] is deployment.prepared_routes
    assert deployment.capability_provider.client is client
    assert deployment.preparation_provider.route_builder.scene_source.__name__ == "scene_facts"
    assert deployment.grounding.depth_scale_to_m == pytest.approx(0.002)
    assert deployment.preparation_provider.route_builder.contact_qualification_mode == "observed_occupancy"
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
    observed = build_persistent_deployment(
        client=client, artifact_root=tmp_path, scene_source=lambda request: None,
        materializer_command=("python", "materializer.py"), materializer_arguments=arguments,
        arm_profile_digest="a" * 64, route_geometry_source="observed",
        simulation_action_mode="runtime_monitored", task_name="blocks_ranking_rgb",
        goal_source="benchmark_task_definition",
    )
    assert observed.preparation_provider.route_builder.scene_source.__name__ == "scene_facts"
    assert observed.grounding.goal_source == "benchmark_task_definition"
    assert isinstance(observed.preparation_provider.approval_issuer, PersistentSimulationActionApprover)
    assert observed.preparation_provider.selector.deferred_checks == monitored.preparation_provider.selector.deferred_checks
    with pytest.raises(ValueError, match="observed or oracle"):
        build_persistent_deployment(
            client=client, artifact_root=tmp_path, scene_source=lambda request: None,
            materializer_command=("python",), materializer_arguments=arguments,
            arm_profile_digest="a" * 64, route_geometry_source="automatic",
        )
    invalid_route = tmp_path / "invalid-route.yaml"
    invalid_route.write_text(
        (profiles / "route-inputs.yaml").read_text(encoding="utf-8").replace(
            "failure_recovery: hold_and_reconcile", "failure_recovery: reset_simulation"
        ),
        encoding="utf-8",
    )
    arguments["route-input-profile"] = str(invalid_route)
    with pytest.raises(ValueError, match="hold_and_reconcile"):
        build_persistent_deployment(
            client=client, artifact_root=tmp_path, scene_source=lambda request: None,
            materializer_command=("python",), materializer_arguments=arguments,
            arm_profile_digest="a" * 64,
        )


def test_deployment_projects_qualification_capability_refs_into_both_consumers(tmp_path):
    arm = tmp_path / "arms.yaml"
    arm.write_text(yaml.safe_dump(_profile()))
    plan = _plan()
    plan_path = tmp_path / "qualification-plan.json"
    plan_path.write_text(plan.model_dump_json(), encoding="utf-8")
    profiles = Path(__file__).parents[1] / "profiles/robotwin20"

    deployment = build_persistent_deployment(
        client=object(), artifact_root=tmp_path, scene_source=lambda request: None,
        materializer_command=("python", "materializer.py"),
        materializer_arguments={
            "arm-planning-profile": str(arm),
            "route-input-profile": str(profiles / "route-inputs-graspnet.yaml"),
            "controller-qualification-plan": str(plan_path),
        },
        arm_profile_digest="a" * 64,
    )
    expected = {
        item.arm_id: qualification_capability_ref(plan.qualification_id, item.arm_id)
        for item in plan.capability_bindings
    }

    assert {
        item["arm_id"]: item["motion_capabilities_ref"]
        for item in deployment.preparation_provider.route_builder.arm_profile["arms"]
    } == expected
    assert {
        item["arm_id"]: item["motion_capabilities_ref"]
        for item in deployment.capability_provider.profile["arms"]
    } == expected


def test_deployment_rejects_provider_route_mismatch(tmp_path):
    arm = tmp_path / "arms.yaml"
    arm.write_text(yaml.safe_dump(_profile()))
    profiles = Path(__file__).parents[1] / "profiles/robotwin20"
    arguments = {
        "arm-planning-profile": str(arm),
        "route-input-profile": str(profiles / "route-inputs-graspnet.yaml"),
    }
    with pytest.raises(ValueError, match="provider and route input"):
        build_persistent_deployment(
            client=object(), artifact_root=tmp_path, scene_source=lambda request: None,
            materializer_command=("python",), materializer_arguments=arguments,
            arm_profile_digest="a" * 64, grasp_provider_id="graspgen",
        )


def test_deployment_wires_explicit_planner_world_policy_without_depth_collision(tmp_path):
    arm = tmp_path / "arms.yaml"
    arm.write_text(yaml.safe_dump(_profile()))
    profiles = Path(__file__).parents[1] / "profiles/robotwin20"
    deployment = build_persistent_deployment(
        client=object(), artifact_root=tmp_path, scene_source=lambda request: None,
        materializer_command=("python",),
        materializer_arguments={
            "arm-planning-profile": str(arm),
            "route-input-profile": str(profiles / "route-inputs-graspnet.yaml"),
        },
        arm_profile_digest="a" * 64,
    )

    assert deployment.preparation_provider.route_builder.contact_qualification_mode == (
        "planner_world_only"
    )
    assert deployment.grounding.collision_policy is None


@pytest.mark.parametrize(
    "policy",
    [
        {"contact_qualification": {"mode": "unknown"}},
        {"contact_qualification": {"mode": "observed_occupancy"}, "observed_collision": None},
    ],
)
def test_deployment_rejects_invalid_contact_qualification_policy(tmp_path, policy):
    arm = tmp_path / "arms.yaml"
    arm.write_text(yaml.safe_dump(_profile()))
    source = Path(__file__).parents[1] / "profiles/robotwin20/route-inputs-graspnet.yaml"
    profile = yaml.safe_load(source.read_text(encoding="utf-8"))
    profile.update(policy)
    invalid = tmp_path / "invalid-contact-policy.yaml"
    invalid.write_text(yaml.safe_dump(profile), encoding="utf-8")

    with pytest.raises((TypeError, ValueError), match="contact_qualification|observed_collision"):
        build_persistent_deployment(
            client=object(), artifact_root=tmp_path, scene_source=lambda request: None,
            materializer_command=("python",),
            materializer_arguments={
                "arm-planning-profile": str(arm), "route-input-profile": str(invalid)
            },
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
        tool_input_defaults={
            "scene.observe": {"sensor_ref": "camera/head", "max_age_ms": 1000}
        },
    )
    assert bundle.client_transport() is bundle.transport
    tools = {item["tool_id"]: item for item in bundle.runtime.list_tools()["tools"]}
    assert set(tools) == {
        "scene.observe", "manipulation.capabilities", "scene.understand",
        "grasp.propose", "manipulation.prepare", "object.acquire", "object.place",
        "scene.bind", "task.goal", "manipulation.staging", "manipulation.target",
    }
    assert tools["scene.observe"]["input_schema"]["properties"]["sensor_ref"]["default"] == "camera/head"
    assert tools["scene.observe"]["input_schema"]["properties"]["max_age_ms"]["default"] == 1000
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


@pytest.mark.parametrize(
    ("goal_source", "expected_capabilities"),
    [
        ("benchmark_task_definition", []),
        ("observation_owned", None),
    ],
)
def test_goal_source_controls_autonomous_goal_tool_planning(
    tmp_path, goal_source, expected_capabilities
):
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
        arm_profile_digest="a" * 64, goal_source=goal_source,
    )
    bundle = build_persistent_runtime_bundle(
        deployment=deployment, client=client, understanding_provider=object(),
        grasp_provider=object(),
        tool_context_provider=lambda tool_id: {"ready": True, "tool_id": tool_id},
    )
    tools = {item["tool_id"]: item for item in bundle.runtime.list_tools()["tools"]}

    for tool_id in ("manipulation.target", "manipulation.staging"):
        capabilities = tools[tool_id]["planning"]["capabilities"]
        if expected_capabilities is None:
            assert capabilities == [tool_id]
        else:
            assert capabilities == expected_capabilities
            assert tools[tool_id]["planning"]["requires_before_plan"] is False
