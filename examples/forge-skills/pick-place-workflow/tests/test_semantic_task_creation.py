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
from PhyAgentOS.providers.base import LLMProvider, LLMResponse, ToolCallRequest

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
        if tool_id == "scene.observe":
            return deepcopy(values[tool_id])
        request = arguments.get("request", {})
        if tool_id == "scene.understand":
            request = arguments
        elif tool_id == "grasp.propose":
            target = arguments["targets"][0]
            source_ref = target["entity_ref"]
            source_label = source_ref.removeprefix("entity://").removesuffix("-bottle")
            return {
                **deepcopy(grasp),
                "candidate_set_ref": f"candidate-set://{scene}/{source_label}",
                "candidates": [{"candidate_ref": f"candidate://{scene}/{source_label}/0",
                                  "entity_ref": source_ref, "confidence": 0.9}],
            }
        elif tool_id != "scene.understand":
            return deepcopy(values[tool_id])
        source_category = request.get("source_category", "reagent_bottle")
        source_label = request.get("source_selector", {}).get("label", prefix)
        destination_category = request.get("destination_category", "beaker")
        destination_label = request.get("destination_selector", {}).get("label", f"{prefix}-beaker")
        source_ref = f"entity://{source_label}-bottle"
        destination_ref = f"entity://{destination_label}"
        if tool_id == "scene.understand":
            if duplicate:
                return {
                    **deepcopy(understanding),
                    "entities": [
                        {"entity_ref": source_ref, "category": source_category, "label": source_label, "confidence": 0.95},
                        {"entity_ref": f"entity://{source_label}-bottle-2", "category": source_category, "label": source_label, "confidence": 0.9},
                        {"entity_ref": destination_ref, "category": destination_category, "label": destination_label, "confidence": 0.99},
                    ],
                }
            return {
                **deepcopy(understanding),
                "entities": [
                    {"entity_ref": source_ref, "category": source_category, "label": source_label, "confidence": 0.95},
                    {"entity_ref": destination_ref, "category": destination_category, "label": destination_label, "confidence": 0.99},
                ],
                "spatial_envelopes": [
                    {"entity_ref": source_ref, "frame_id": "camera-front", "min_xyz_m": [0, 0, 0], "max_xyz_m": [0.1, 0.1, 0.2], "confidence": 0.9},
                    {"entity_ref": destination_ref, "frame_id": "camera-front", "min_xyz_m": [0.3, 0, 0], "max_xyz_m": [0.5, 0.2, 0.2], "confidence": 0.9},
                ],
            }
        return deepcopy(values[tool_id])

    return invoke


def _request(prefix: str = "a"):
    return [{
        "subtask_id": f"pour-{prefix}", "operation": "pour",
        "source_category": "reagent_bottle", "destination_category": "beaker",
        "sensor_refs": ["camera/front"], "max_age_ms": 1000,
        "source_selector": {"label": prefix}, "parameters": {"tilt_rad": 0.8, "hold_s": 1.0},
    }]


def _mixture_query(tool_id, arguments):
    """A replaceable no-motion Query provider keyed by current semantic selectors."""
    identity = {
        "observation_ref": "observation://mix-scene/front",
        "scene_revision": "mix-scene",
        "frame": {"frame_id": "camera-front", "unit": "m"},
        "calibration_ref": "artifact://calibration/front",
        "freshness_ms": 5,
    }
    if tool_id == "scene.observe":
        return {**identity, "status": "available",
                "artifacts": [{"ref": "artifact://observations/mix-scene/rgb"}]}
    if tool_id == "scene.understand":
        return {
            **identity, "status": "available",
            "entities": [
                {"entity_ref": "entity://reagent-a", "category": "reagent_bottle", "label": "reagent-a", "confidence": 0.98},
                {"entity_ref": "entity://reagent-b", "category": "reagent_bottle", "label": "reagent-b", "confidence": 0.98},
                {"entity_ref": "entity://glass-rod", "category": "stir_tool", "label": "glass-rod", "confidence": 0.98},
                {"entity_ref": "entity://mixing-vessel", "category": "mixing_vessel", "label": "mixing-vessel", "confidence": 0.99},
                {"entity_ref": "entity://other-vessel", "category": "mixing_vessel", "label": "other-vessel", "confidence": 0.99},
            ],
            "spatial_envelopes": [
                *[{"entity_ref": ref, "frame_id": "camera-front", "min_xyz_m": [0, 0, 0], "max_xyz_m": [0.1, 0.1, 0.2], "confidence": 0.95}
                  for ref in ("entity://reagent-a", "entity://reagent-b", "entity://glass-rod", "entity://mixing-vessel", "entity://other-vessel")],
            ],
        }
    if tool_id == "grasp.propose":
        target = arguments["targets"][0]
        source_ref = target["entity_ref"]
        source_label = source_ref.removeprefix("entity://")
        return {**identity, "status": "available",
                "candidate_set_ref": f"candidate-set://mix-scene/{source_label}",
                "candidates": [{"candidate_ref": f"candidate://mix-scene/{source_label}/0",
                                  "entity_ref": target["entity_ref"], "confidence": 0.95}]}
    if tool_id == "manipulation.capabilities":
        return {**identity, "status": "available",
                "snapshot_ref": "artifact://capabilities/mix-scene", "motion_authorized": False}
    raise AssertionError(tool_id)


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


@pytest.mark.parametrize("parameters", [
    {"radius_m": 0.009, "depth_m": 0.04, "turns": 2.0, "duration_s": 4.0},
    {"radius_m": 0.009, "depth_m": 0.04, "turns": 2.0, "duration_s": 4.0,
     "direction": "clockwise"},
])
def test_semantic_builder_rejects_invalid_stir_parameters_before_perception(parameters):
    provider_calls = []

    def provider(tool_id, arguments):
        provider_calls.append((tool_id, arguments))
        return _provider()(tool_id, arguments)

    request = {
        "subtask_id": "stir-a", "operation": "stir", "source_category": "stir_tool",
        "destination_category": "mixing_vessel", "sensor_refs": ["camera/front"],
        "max_age_ms": 1000, "parameters": parameters,
    }
    with pytest.raises(SemanticTaskCreationError, match="invalid stir parameters"):
        _builder(provider).build("stir vessel", [request])
    assert provider_calls == []


def test_semantic_builder_serializes_multiple_subtasks_as_one_ordered_plan():
    provider = _provider()
    plan = _builder(provider).build(
        "perform two ordered pours",
        _request() + [{**_request()[0], "subtask_id": "pour-b", "depends_on": ["pour-a"]}],
    )
    assert plan["nodes"][1]["dependencies"] == ["pour-a"]
    assert plan["nodes"][2]["node_id"] == "verify"


def test_agent_loop_tool_call_binds_two_distinct_reagents_then_stir_rod_to_same_vessel(tmp_path):
    class ScriptedProvider(LLMProvider):
        def __init__(self):
            super().__init__()
            self.responses = [
                LLMResponse(content=None, tool_calls=[ToolCallRequest(
                    "mix-task", "forge_task_create", {
                        "task_description": "将试剂A和试剂B依次倒入烧杯，再用玻璃棒搅拌",
                        "verification": {"mode": "off"},
                        "semantic_subtasks": [
                            {"subtask_id": "pour-a", "operation": "pour",
                             "source_category": "reagent_bottle", "destination_category": "mixing_vessel",
                             "sensor_refs": ["camera/front"], "max_age_ms": 1000,
                             "parameters": {"tilt_rad": 0.8, "hold_s": 1.0},
                             "source_selector": {"label": "reagent-a"},
                             "destination_selector": {"label": "mixing-vessel"}},
                            {"subtask_id": "pour-b", "operation": "pour",
                             "source_category": "reagent_bottle", "destination_category": "mixing_vessel",
                             "sensor_refs": ["camera/front"], "max_age_ms": 1000,
                             "parameters": {"tilt_rad": 0.9, "hold_s": 1.2},
                             "source_selector": {"label": "reagent-b"},
                             "destination_selector": {"label": "mixing-vessel"}},
                            {"subtask_id": "stir-mixture", "operation": "stir",
                             "source_category": "stir_tool", "destination_category": "mixing_vessel",
                             "sensor_refs": ["camera/front"], "max_age_ms": 1000,
                             "parameters": {"radius_m": 0.009, "depth_m": 0.04, "turns": 2.0,
                                             "duration_s": 4.0, "direction": "ccw"},
                             "source_selector": {"label": "glass-rod"},
                             "destination_selector": {"label": "mixing-vessel"}},
                        ],
                    },
                )]),
                LLMResponse(content="已按标签生成两种试剂后搅拌的任务计划；执行需等待实验室路线资格。"),
            ]

        async def chat(self, **kwargs):
            del kwargs
            return self.responses.pop(0)

        def get_default_model(self):
            return "test-model"

    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    provider = ScriptedProvider()
    loop = AgentLoop(
        bus=MessageBus(), provider=provider, workspace=tmp_path,
        forge_task_coordinator=coordinator,
        semantic_plan_builder=AsyncQuerySemanticPlanBuilder(_mixture_query),
        max_iterations=3,
    )
    result = asyncio.run(loop._run_agent_loop([
        {"role": "user", "content": "将试剂A和试剂B混合后搅拌"},
    ]))
    assert "路线资格" in result.content
    task = coordinator.store.active()
    if task is None:
        records = list(coordinator.store.list_all())
        assert records, "Agent tool call must persist the semantic task"
        task = records[-1]
    nodes = task.active_revision.plan_graph.nodes
    assert [node.node_id for node in nodes] == ["pour-a", "pour-b", "stir-mixture", "verify"]
    assert [node.input_bindings["binding"]["entity_ref"] for node in nodes[:3]] == [
        "entity://reagent-a", "entity://reagent-b", "entity://glass-rod",
    ]
    assert len({node.input_bindings["binding"]["destination_ref"] for node in nodes[:3]}) == 1
    assert nodes[1].dependencies == ("pour-a",)
    assert nodes[2].dependencies == ("pour-b",)
    assert all(node.capability == "manipulation.execute_subtask" for node in nodes[:3])


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda requests: requests[:1], "final stir-tool"),
        (lambda requests: requests[:1] + requests[2:], "at least two reagent"),
            (lambda requests: [requests[0], {**requests[1], "source_selector": {"label": "reagent-a"}}, requests[2]], "distinct reagent"),
        (lambda requests: [requests[0], requests[2], requests[1]], "end with exactly one stir"),
        (lambda requests: [*requests[:2], {**requests[2], "destination_selector": {"label": "other-vessel"}}], "same observed vessel"),
    ],
)
def test_semantic_mixture_plan_rejects_incomplete_or_misbound_requests(mutate, message):
    requests = [
        {"subtask_id": "pour-a", "operation": "pour", "source_category": "reagent_bottle",
         "destination_category": "mixing_vessel", "sensor_refs": ["camera/front"],
         "max_age_ms": 1000, "source_selector": {"label": "reagent-a"},
         "parameters": {"tilt_rad": 0.8, "hold_s": 1.0},
         "destination_selector": {"label": "mixing-vessel"}},
        {"subtask_id": "pour-b", "operation": "pour", "source_category": "reagent_bottle",
         "destination_category": "mixing_vessel", "sensor_refs": ["camera/front"],
         "max_age_ms": 1000, "source_selector": {"label": "reagent-b"},
         "parameters": {"tilt_rad": 0.8, "hold_s": 1.0},
         "destination_selector": {"label": "mixing-vessel"}},
        {"subtask_id": "stir-mixture", "operation": "stir", "source_category": "stir_tool",
         "destination_category": "mixing_vessel", "sensor_refs": ["camera/front"],
         "max_age_ms": 1000, "source_selector": {"label": "glass-rod"},
         "parameters": {"radius_m": 0.009, "depth_m": 0.04, "turns": 2.0,
                         "duration_s": 4.0, "direction": "ccw"},
         "destination_selector": {"label": "mixing-vessel"}},
    ]
    with pytest.raises(SemanticTaskCreationError, match=message):
        _builder(_mixture_query).build("mix two reagents and stir", mutate(requests))


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
    subtasks = _request()
    subtasks[0]["semantic_intent"] = {"goal": "pour selected reagent", "success_criteria": ["bottle returned"],
                                       "allowed_arms": ["franka"], "coordination_mode": "single_arm"}
    arguments = {"task_description": "pour reagent", "verification": {"mode": "off"}, "semantic_subtasks": subtasks}
    assert tool.validate_params(arguments) == []
    result = json.loads(asyncio.run(tool.execute(**arguments)))
    assert result["ok"] is True
    task = coordinator.get_task(result["data"]["task_id"])
    assert task.active_revision.plan_graph.nodes[0].capability == "manipulation.execute_subtask"
    assert task.active_revision.plan_graph.nodes[0].input_bindings["semantic_intent"] == subtasks[0]["semantic_intent"]


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


def test_installed_paos_and_workflow_wheels_start_cli_and_discover_builder(tmp_path):
    pytest.importorskip("hatchling")
    repository = Path(__file__).resolve().parents[4]
    workflow = repository / "examples/forge-skills/pick-place-workflow"
    wheelhouse = tmp_path / "wheelhouse"
    site_packages = tmp_path / "site-packages"
    wheelhouse.mkdir()
    site_packages.mkdir()

    for project in (repository, workflow):
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
                str(project),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    wheels = list(wheelhouse.glob("*.whl"))
    assert len(wheels) == 2
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
            *(str(wheel) for wheel in wheels),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    smoke = (
        "from pathlib import Path; "
        "import sys; "
        "target = Path(sys.argv[1]).resolve(); "
        "import PhyAgentOS, pick_place_workflow; "
        "assert Path(PhyAgentOS.__file__).resolve().is_relative_to(target); "
        "assert Path(pick_place_workflow.__file__).resolve().is_relative_to(target); "
        "from PhyAgentOS.agent.semantic_builder_registry import SemanticPlanBuilderRegistry; "
        "registry = SemanticPlanBuilderRegistry(); "
        "ids = registry.discover(); "
        "assert 'pick_place_workflow' in ids, ids; "
        "builder = registry.create('pick_place_workflow', query_invoker=object()); "
        "assert callable(getattr(builder, 'build', None)); "
        "assert type(builder).__name__ == 'AsyncQuerySemanticPlanBuilder'; "
        "from typer.testing import CliRunner; "
        "from PhyAgentOS.cli.commands import app; "
        "result = CliRunner().invoke(app, ['--help']); "
        "assert result.exit_code == 0, result.exception; "
        "assert 'PhyAgentOS' in result.stdout"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(site_packages)
    subprocess.run(
        [sys.executable, "-c", smoke, str(site_packages)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=tmp_path,
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


def test_agent_loop_model_tool_call_creates_semantic_subtask_once(tmp_path):
    sync_query = _provider()

    async def query(tool_id, arguments):
        return sync_query(tool_id, arguments)

    class ScriptedProvider(LLMProvider):
        def __init__(self):
            super().__init__()
            self.requests = []
            self.responses = [
                LLMResponse(content=None, tool_calls=[ToolCallRequest(
                    "create-semantic-task",
                    "forge_task_create",
                    {
                        "task_description": "Pour reagent A into the beaker",
                        "verification": {"mode": "off"},
                        "semantic_subtasks": _request(),
                    },
                )]),
                LLMResponse(content="Semantic task created from current observation."),
            ]

        async def chat(self, **kwargs):
            self.requests.append(kwargs)
            return self.responses.pop(0)

        def get_default_model(self):
            return "test-model"

    provider = ScriptedProvider()
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    loop = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=tmp_path,
        forge_task_coordinator=coordinator,
        semantic_plan_builder=_async_builder(query),
        max_iterations=3,
    )

    result = asyncio.run(loop._run_agent_loop([
        {"role": "user", "content": "Pour reagent A into the beaker."},
    ]))

    assert result.content == "Semantic task created from current observation."
    assert result.tools_used == ["forge_task_create"]
    assert provider.responses == []
    schemas = provider.requests[0]["tools"]
    task_schema = next(
        item["function"] for item in schemas
        if item["function"]["name"] == "forge_task_create"
    )
    assert "semantic_subtasks" in task_schema["parameters"]["properties"]
    assert len(provider.requests) == 2

    task = coordinator.store.active()
    assert task is not None
    nodes = task.active_revision.plan_graph.nodes
    assert [node.capability for node in nodes] == [
        "manipulation.execute_subtask", "task.verify",
    ]
    assert nodes[0].input_bindings["binding"]["entity_ref"] == "entity://a-bottle"
