from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from unittest.mock import Mock

import pytest
from PhyAgentOS.agent.tools.forge_task import ForgeTaskCreateTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskCoordinator

from pick_place_workflow.semantic_task_creation import (
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
        planner_decision_digest="a" * 64,
        policy_snapshot_digest="b" * 64,
    )


def test_semantic_builder_binds_provider_and_emits_one_agent_node():
    plan = _builder(_provider()).build("pour reagent", _request())
    nodes = plan["nodes"]
    assert [node["capability"] for node in nodes] == ["manipulation.execute_subtask", "task.verify"]
    binding = nodes[0]["input_bindings"]
    assert binding["binding"]["entity_ref"] == "entity://a-bottle"
    assert binding["operation"] == "pour"
    assert "prim_path" not in json.dumps(binding)


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
