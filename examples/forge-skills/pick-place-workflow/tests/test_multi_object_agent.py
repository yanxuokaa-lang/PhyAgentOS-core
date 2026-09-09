from __future__ import annotations

import pytest
from PhyAgentOS.agent.planning_loop import NodeContextProvider, PlanningLoopAdapter
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskError
from PhyAgentOS.planning import AdmissionContext, ToolResultEnvelope
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


def test_scene_binding_accepts_optional_capability_and_assignment_evidence():
    bound = SceneObjectBinding.model_validate({
        **entity("green"),
        "capability_snapshot_ref": "artifact://capabilities/s0",
        "assignment_ref": "artifact://assignments/s0/green",
    })
    assert bound.capability_snapshot_ref == "artifact://capabilities/s0"
    assert bound.assignment_ref == "artifact://assignments/s0/green"
    with pytest.raises(ValueError, match="artifact://"):
        SceneObjectBinding.model_validate({**entity("red"), "assignment_ref": "assignment://bad"})


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
    bindings = {node.node_id: node.input_bindings for node in graph.nodes}
    assert bindings["relocate_1.observe"] == {
        "entity_ref": "entity://green",
        "destination_ref": "region://green",
        "benchmark_object_ref": "block-green-1",
        "observation_ref": "artifact://observation/s0",
        "scene_revision": "scene://s0",
        "frame_id": "camera_front",
        "calibration_ref": "artifact://calibration/front",
        "geometry_artifact_ref": "artifact://geometry/green",
    }
    assert bindings["relocate_2.place"]["geometry_artifact_ref"] == "artifact://geometry/red"
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
    nodes = {node.node_id: node for node in task.active_revision.plan_graph.nodes}
    assert list(nodes) == ["relocate_1", "verify"]
    assert nodes["relocate_1"].input_bindings["scene_revision"] == "scene://s0"


@pytest.mark.asyncio
@pytest.mark.parametrize("planning_mode", ["baseline", "agent_composed"])
async def test_runner_persists_optional_execution_evidence_in_plan_nodes(tmp_path, planning_mode):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
        planning_mode=planning_mode,
    )
    task = await runner.create_task(
        task_description="evidence-bound block",
        entities=[{
            **entity("green"),
            "capability_snapshot_ref": "artifact://capabilities/s0",
            "assignment_ref": "artifact://assignments/s0/green",
        }],
        verification=TaskVerificationContract(mode="off"),
        task_id=f"task-evidence-{planning_mode}",
        revision_id=f"revision-evidence-{planning_mode}",
    )
    nodes = [node for node in task.active_revision.plan_graph.nodes if node.node_id != "verify"]
    assert nodes
    assert all(node.input_bindings["capability_snapshot_ref"] == "artifact://capabilities/s0" for node in nodes)
    assert all(node.input_bindings["assignment_ref"] == "artifact://assignments/s0/green" for node in nodes)


@pytest.mark.asyncio
async def test_runner_rejects_stale_scene_before_agent_loop(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    class AgentLoop:
        def build_long_horizon_controller(self):
            raise AssertionError("stale scene must be rejected before controller creation")

    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=AgentLoop(),
        scene_revision_provider=lambda _task_id: "scene://new",
    )
    with pytest.raises(MultiObjectAgentError, match="stale"):
        await runner.run(
            task_description="stale scene",
            entities=[entity("green")],
            verification=TaskVerificationContract(mode="off"),
            task_id="task-stale-1",
            revision_id="revision-stale-1",
        )
    with pytest.raises(AgentTaskError, match="not found"):
        coordinator.get_task("task-stale-1")


@pytest.mark.asyncio
async def test_two_object_dry_run_propagates_scene_revision_to_later_object(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    runner = MultiObjectAgentRunner(
        coordinator=coordinator,
        agent_loop=object(),
        scene_revision_provider=lambda _task_id: "scene://s0",
    )
    task = await runner.create_task(
        task_description="place two blocks sequentially",
        entities=[entity("green"), entity("red")],
        verification=TaskVerificationContract(mode="off"),
        task_id="task-revision-propagation",
        revision_id="revision-revision-propagation",
    )
    current_scene = {"value": "scene://s0"}
    contexts: list[tuple[str, str]] = []

    def admission(_task_id: str) -> AdmissionContext:
        return AdmissionContext(scene_revision=current_scene["value"])

    def execute(context):
        contexts.append((context.node_id, context.scene_revision))
        changed = context.node_id.endswith(".place")
        next_scene = None
        evidence = ()
        if changed:
            next_scene = "scene://s2" if current_scene["value"] == "scene://s0" else "scene://s3"
            current_scene["value"] = next_scene
            entity_ref = context.input_bindings["entity_ref"]
            evidence = (f"placed:{entity_ref}",)
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id=context.capability,
            status="succeeded",
            world_changed=changed,
            new_scene_revision=next_scene,
            evidence_refs=evidence,
        )

    adapter = PlanningLoopAdapter(
        coordinator,
        context_provider=NodeContextProvider(coordinator.get_task),
        node_executor=execute,
        admission_context_provider=admission,
    )
    result = await adapter.run(task.task_id, scene_revision="scene://s0")
    assert result.status == "completed"
    assert contexts[-1] == ("verify", "scene://s3")
    assert next(scene for node, scene in contexts if node == "relocate_2.observe") == "scene://s2"
    assert [node for node, _ in contexts if node.endswith(".place")] == [
        "relocate_1.place", "relocate_2.place"
    ]
