from __future__ import annotations

import pytest
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskCoordinator
from PhyAgentOS.verification.contracts import TaskVerificationContract

from pick_place_workflow.multi_object_agent import (
    MultiObjectAgentError,
    MultiObjectAgentRunner,
    SceneObjectBinding,
    bind_scene_objects,
)


def entity(name: str, *, destination: str | None = None, scene: str = "scene://s0") -> dict:
    return {
        "entity_ref": f"entity://{name}",
        "benchmark_object_ref": f"block-{name}-1",
        "destination_ref": destination or f"region://{name}",
        "observation_ref": "artifact://observation/s0",
        "scene_revision": scene,
        "frame_id": "camera_front",
        "calibration_ref": "artifact://calibration/front",
        "geometry_artifact_ref": f"artifact://geometry/{name}",
        "category": "block",
    }


def test_bind_scene_objects_excludes_surface_and_requires_unique_bindings():
    values = bind_scene_objects([
        entity("green"),
        {**entity("table"), "category": "desktop_surface"},
    ])
    assert [item.entity_ref for item in values] == ["entity://green"]
    with pytest.raises(MultiObjectAgentError, match="destination_ref"):
        bind_scene_objects([entity("a"), entity("b", destination="region://a")])


def test_bind_scene_objects_rejects_mixed_scene_revision():
    with pytest.raises(MultiObjectAgentError, match="scene revision"):
        bind_scene_objects([entity("a", scene="scene://s0"), entity("b", scene="scene://s1")])


@pytest.mark.asyncio
async def test_runner_creates_one_task_with_all_object_obligations(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
    )
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
        planning_mode="baseline",
    )
    task = await runner.create_task(
        task_description="sort two blocks",
        entities=[entity("green"), entity("red")],
        verification=TaskVerificationContract(mode="off", success_criteria=["both blocks placed"]),
        task_id="task-multi-1",
        revision_id="revision-multi-1",
    )
    graph = task.active_revision.plan_graph
    assert graph is not None
    assert task.task_id == "task-multi-1"
    assert {node.obligation_id for node in graph.nodes if node.node_id != "verify"} == {
        "relocate_1", "relocate_2"
    }
    assert set(graph.nodes[-1].dependencies) == {"relocate_1.place", "relocate_2.place"}
    assert len(task.revisions) == 1


@pytest.mark.asyncio
async def test_runner_semantic_mode_does_not_force_tool_queue(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
        planning_mode="agent_composed",
    )
    task = await runner.create_task(
        task_description="sort one block",
        entities=[SceneObjectBinding.model_validate(entity("green"))],
        verification=TaskVerificationContract(mode="off"),
        task_id="task-semantic-1",
        revision_id="revision-semantic-1",
    )
    assert [node.node_id for node in task.active_revision.plan_graph.nodes] == ["relocate_1", "verify"]
