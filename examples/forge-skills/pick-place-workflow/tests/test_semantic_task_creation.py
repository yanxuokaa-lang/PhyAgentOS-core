from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tomllib
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest
from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.agent.tools.forge_task import ForgeTaskCreateTool
from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskCoordinator
from PhyAgentOS.providers.base import LLMProvider

from pick_place_workflow.perception_binding import PerceptionBindingAdapter
from pick_place_workflow.semantic_task_creation import (
    AsyncQuerySemanticPlanBuilder,
    PickPlaceSemanticPlanBuilderFactory,
    QuerySemanticPlanBuilder,
    SemanticTaskCreationError,
)


def _provider(*, prefix: str = "a", scene: str = "scene-1", duplicate: bool = False):
    observation = {
        "status": "available", "observation_ref": f"observation://{scene}/front",
        "scene_revision": scene, "frame": {"frame_id": "camera-front", "unit": "m"},
        "calibration_ref": "artifact://calibration/front", "freshness_ms": 5,
        "artifacts": [{"ref": f"artifact://observations/{scene}/rgb"}],
    }
    source = f"entity://{prefix}-bottle"
    destination = f"entity://{prefix}-beaker"
    entities = [
        {"entity_ref": source, "category": "reagent_bottle", "label": prefix, "confidence": 0.95},
        {"entity_ref": destination, "category": "beaker", "confidence": 0.99},
    ]
    if duplicate:
        entities.append({"entity_ref": f"entity://{prefix}-bottle-2", "category": "reagent_bottle", "label": prefix, "confidence": 0.9})
    understanding = {
        "status": "available", "observation_ref": observation["observation_ref"],
        "scene_revision": scene, "frame": observation["frame"],
        "calibration_ref": observation["calibration_ref"], "entities": entities,
        "spatial_envelopes": [
            {"entity_ref": source, "frame_id": "camera-front", "min_xyz_m": [0, 0, 0], "max_xyz_m": [0.1, 0.1, 0.2], "confidence": 0.9},
            {"entity_ref": destination, "frame_id": "camera-front", "min_xyz_m": [0.3, 0, 0], "max_xyz_m": [0.5, 0.2, 0.2], "confidence": 0.9},
        ],
    }
    grasp = {
        "status": "available", "observation_ref": observation["observation_ref"],
        "scene_revision": scene, "frame": observation["frame"],
        "calibration_ref": observation["calibration_ref"], "candidate_set_ref": f"candidate-set://{scene}/{prefix}",
        "candidates": [{"candidate_ref": f"candidate://{scene}/{prefix}/0", "entity_ref": source, "confidence": 0.9}],
    }
    capability = {
        "status": "available", "snapshot_ref": f"artifact://capabilities/{scene}",
        "observation_ref": observation["observation_ref"], "scene_revision": scene,
        "calibration_ref": observation["calibration_ref"], "motion_authorized": False,
    }
    values = {"scene.observe": observation, "scene.understand": understanding,
              "grasp.propose": grasp, "manipulation.capabilities": capability}

    def invoke(tool_id, arguments):
        del arguments
        return deepcopy(values[tool_id])

    return invoke


def _request(prefix: str = "a"):
    return [{
        "subtask_id": f"pour-{prefix}", "operation": "pour",
        "source_category": "reagent_bottle", "destination_category": "beaker",
        "sensor_refs": ["camera/front"], "max_age_ms": 1000,
        "source_selector": {"label": prefix}, "parameters": {"magnitude": 0.8},
    }]


def _builder(query):
    return QuerySemanticPlanBuilder(
        query,
    )


def _async_builder(query):
    return AsyncQuerySemanticPlanBuilder(
        query,
    )


def test_semantic_builder_binds_provider_and_emits_one_agent_node():
    plan = _builder(_provider()).build("pour reagent", _request())
    nodes = plan["nodes"]
    assert [node["capability"] for node in nodes] == ["manipulation.execute_subtask", "task.verify"]
    binding = nodes[0]["input_bindings"]
    assert binding["binding"]["entity_ref"] == "entity://a-bottle"
    assert binding["operation"] == "pour"
    assert "prim_path" not in json.dumps(binding)
    assert len(plan["planner_decision_digest"]) == 64
    assert len(plan["policy_snapshot_digest"]) == 64


def test_semantic_builder_is_provider_replaceable():
    first = _builder(_provider(prefix="a")).build("pour a", _request("a"))
    second = _builder(_provider(prefix="b")).build("pour b", _request("b"))
    assert first["nodes"][0]["input_bindings"]["binding"]["entity_ref"] != second["nodes"][0]["input_bindings"]["binding"]["entity_ref"]


def test_semantic_builder_serializes_multiple_subtasks_as_one_ordered_plan():
    provider = _provider()
    plan = _builder(provider).build(
        "pour then stir",
        _request() + [{
            "subtask_id": "stir-after-pour", "operation": "stir",
            "source_category": "reagent_bottle", "destination_category": "beaker",
            "sensor_refs": ["camera/front"], "max_age_ms": 1000,
            "source_selector": {"label": "a"},
        }],
    )
    assert plan["nodes"][1]["dependencies"] == ["pour-a"]
    assert plan["nodes"][2]["node_id"] == "verify"


def test_semantic_builder_rejects_scene_revision_change_between_subtasks():
    calls = [_provider(scene="scene-1"), _provider(scene="scene-2")]
    query_index = 0

    def changing_provider(tool_id, arguments):
        nonlocal query_index
        if tool_id == "scene.observe":
            query_index += 1
        return calls[min(query_index - 1, 1)](tool_id, arguments)

    with pytest.raises(SemanticTaskCreationError, match="share one scene revision"):
        _builder(changing_provider).build(
            "two operations", _request() + [{**_request()[0], "subtask_id": "second"}]
        )


def test_forge_task_create_persists_only_after_semantic_binding(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    tool = ForgeTaskCreateTool(coordinator, semantic_plan_builder=_builder(_provider()))
    result = json.loads(asyncio.run(tool.execute("pour reagent", {"mode": "off"}, semantic_subtasks=_request())))
    assert result["ok"] is True
    task = coordinator.get_task(result["data"]["task_id"])
    assert task.active_revision.plan_graph.nodes[0].capability == "manipulation.execute_subtask"


def test_semantic_binding_failure_does_not_call_coordinator():
    coordinator = Mock()
    tool = ForgeTaskCreateTool(
        coordinator,
        semantic_plan_builder=_builder(_provider(duplicate=True)),
    )
    with pytest.raises(SemanticTaskCreationError, match="ambiguous"):
        asyncio.run(tool.execute("pour reagent", {"mode": "off"}, semantic_subtasks=_request()))
    coordinator.create_task.assert_not_called()


def test_async_gateway_query_builder_runs_before_task_persistence(tmp_path):
    sync_provider = _provider()
    calls = []

    async def async_query(tool_id, arguments):
        calls.append(tool_id)
        return sync_provider(tool_id, arguments)

    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    tool = ForgeTaskCreateTool(coordinator, semantic_plan_builder=_async_builder(async_query))
    result = json.loads(asyncio.run(tool.execute(
        "pour reagent", {"mode": "off"}, semantic_subtasks=_request()
    )))
    assert result["ok"] is True
    assert calls == ["scene.observe", "scene.understand", "grasp.propose", "manipulation.capabilities"]
    task = coordinator.get_task(result["data"]["task_id"])
    assert task.active_revision.plan_graph.nodes[0].input_bindings["binding"]["entity_ref"] == "entity://a-bottle"


def test_async_stale_query_fails_before_task_persistence():
    sync_provider = _provider()

    async def stale_query(tool_id, arguments):
        response = sync_provider(tool_id, arguments)
        if tool_id == "scene.observe":
            response["freshness_ms"] = 5000
        return response

    coordinator = Mock()
    tool = ForgeTaskCreateTool(coordinator, semantic_plan_builder=_async_builder(stale_query))
    with pytest.raises(SemanticTaskCreationError, match="stale"):
        asyncio.run(tool.execute("pour reagent", {"mode": "off"}, semantic_subtasks=_request()))
    coordinator.create_task.assert_not_called()


def test_optional_factory_injects_live_query_port_without_environment_dependency():
    query = _provider()
    builder = PickPlaceSemanticPlanBuilderFactory().create(query_invoker=query)
    assert isinstance(builder, AsyncQuerySemanticPlanBuilder)
    plan = asyncio.run(builder.build("pour reagent", _request()))
    assert plan["nodes"][0]["input_bindings"]["binding"]["entity_ref"] == "entity://a-bottle"


def test_async_builder_binds_policy_digest_to_live_query_tool_specs():
    query = _provider()
    observed_specs = []

    class RuntimeQueryPort:
        async def invoke_query(self, endpoint_id, operation, arguments):
            tool_id = next(
                tool_id for tool_id, spec in PerceptionBindingAdapter._QUERY_SPECS.items()
                if spec["endpoint_id"] == endpoint_id and spec["operation"] == operation
            )
            return query(tool_id, arguments)

        async def get_tool(self, tool_id):
            spec = dict(PerceptionBindingAdapter._QUERY_SPECS[tool_id])
            spec["semantics"] = "query"
            observed_specs.append(tool_id)
            return {"data": spec}

    builder = PickPlaceSemanticPlanBuilderFactory().create(query_invoker=RuntimeQueryPort())
    plan = asyncio.run(builder.build("pour reagent", _request()))
    assert observed_specs == list(PerceptionBindingAdapter._QUERY_SPECS)
    assert len(plan["policy_snapshot_digest"]) == 64


def test_installed_workflow_metadata_declares_semantic_builder_entry_point():
    project_file = Path(__file__).parents[1] / "pyproject.toml"
    metadata = tomllib.loads(project_file.read_text(encoding="utf-8"))
    entry_points = metadata["project"]["entry-points"]["paos.semantic_plan_builders"]
    assert entry_points["pick_place_workflow"] == (
        "pick_place_workflow.semantic_task_creation:PickPlaceSemanticPlanBuilderFactory"
    )


def test_built_workflow_wheel_is_discovered_by_paos_registry(tmp_path):
    pytest.importorskip("hatchling")
    repository = Path(__file__).resolve().parents[4]
    workflow = repository / "examples/forge-skills/pick-place-workflow"
    wheelhouse = tmp_path / "wheelhouse"
    site_packages = tmp_path / "site-packages"
    wheelhouse.mkdir()
    site_packages.mkdir()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheelhouse),
            str(workflow),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    wheel = next(wheelhouse.glob("*.whl"))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-compile",
            "--target",
            str(site_packages),
            str(wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    smoke = (
        "from PhyAgentOS.agent.semantic_builder_registry import SemanticPlanBuilderRegistry; "
        "registry = SemanticPlanBuilderRegistry(); "
        "ids = registry.discover(); "
        "assert 'pick_place_workflow' in ids, ids; "
        "builder = registry.create('pick_place_workflow', query_invoker=object()); "
        "assert callable(getattr(builder, 'build', None)); "
        "assert type(builder).__name__ == 'AsyncQuerySemanticPlanBuilder'"
    )
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        value
        for value in (str(repository), str(site_packages), existing_pythonpath)
        if value
    )
    subprocess.run(
        [sys.executable, "-c", smoke],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def test_agent_loop_registered_task_tool_executes_measured_subtask_creation(tmp_path):
    sync_query = _provider()

    async def query(tool_id, arguments):
        return sync_query(tool_id, arguments)

    class Provider(LLMProvider):
        async def chat(self, messages, model=None, **kwargs):
            del messages, model, kwargs
            raise AssertionError("task-tool integration must not invoke the model")

        def get_default_model(self):
            return "test-model"

    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    builder = _async_builder(query)
    loop = AgentLoop(
        bus=MessageBus(),
        provider=Provider(),
        workspace=tmp_path,
        forge_task_coordinator=coordinator,
        semantic_plan_builder=builder,
    )
    tool = loop.tools.get("forge_task_create")
    assert tool is not None
    assert "semantic_subtasks" in tool.parameters["properties"]

    result = json.loads(asyncio.run(loop.tools.execute("forge_task_create", {
        "task_description": "Pour reagent A into the beaker",
        "verification": {"mode": "off"},
        "semantic_subtasks": _request(),
    })))
    assert result["ok"] is True
    task = coordinator.get_task(result["data"]["task_id"])
    nodes = task.active_revision.plan_graph.nodes
    assert [node.capability for node in nodes] == [
        "manipulation.execute_subtask", "task.verify",
    ]
    assert nodes[0].input_bindings["binding"]["entity_ref"] == "entity://a-bottle"
