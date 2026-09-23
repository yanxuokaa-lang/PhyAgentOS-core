import asyncio
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.agent.prompt_context import continuation_task_prompt_projection
from PhyAgentOS.agent.tools.forge_task import ForgeTaskContinuePlanTool
from PhyAgentOS.agent.tools.forge_tool_api import (
    ForgeToolStartActionTool,
    ForgeToolStartSessionTool,
)


class _Coordinator:
    def __init__(self):
        self.seen = None

    def selected_execution_binding(self, task_id, tool_id, semantics, binding):
        assert (task_id, tool_id, semantics) == ("task-1", "object.place", "action")
        return SimpleNamespace(model_dump=lambda mode="json": {"node_id": "place"})

    def selected_execution_arguments(self, task_id, tool_id, semantics, arguments, binding):
        self.seen = arguments
        return {"preparation_ref": "preparation://scene/red", "assignment_ref": "assignment://red"}

    async def start_action(self, task_id, tool_id, arguments, **kwargs):
        return {"ok": True, "data": arguments}


class _NoSelectionCoordinator(_Coordinator):
    def selected_execution_binding(self, task_id, tool_id, semantics, binding):
        from PhyAgentOS.forge.task import AgentTaskError

        raise AgentTaskError("selected execution has no matching unconsumed selection")

    async def start_action(self, task_id, tool_id, arguments, **kwargs):
        pytest.fail("Action reached Gateway without a selection")


@pytest.mark.parametrize("literal_ref", ["preparation://rewritten", "preparation://stale", ""])
@pytest.mark.parametrize("binding", [{"node_id": "place"}, None])
def test_selected_action_ignores_reassembled_literal_arguments(literal_ref, binding):
    coordinator = _Coordinator()
    tool = ForgeToolStartActionTool(coordinator)
    result = asyncio.run(tool.execute(
        task_id="task-1",
        tool_id="object.place",
        arguments={"preparation_ref": literal_ref},
        planning_binding=binding,
    ))
    assert "preparation://scene/red" in result
    assert coordinator.seen == {}


def test_action_without_selection_never_reaches_gateway():
    result = asyncio.run(ForgeToolStartActionTool(_NoSelectionCoordinator()).execute(
        task_id="task-1", tool_id="object.place", arguments={"preparation_ref": "fabricated"},
    ))
    assert "no matching unconsumed selection" in result


def test_selected_session_ignores_reassembled_literal_arguments():
    class SessionCoordinator(_Coordinator):
        def selected_execution_binding(self, task_id, tool_id, semantics, binding):
            assert (task_id, tool_id, semantics) == ("task-1", "camera.stream", "session")
            return SimpleNamespace(model_dump=lambda mode="json": {"node_id": "session"})

        async def start_session(self, task_id, tool_id, arguments, **kwargs):
            return {"ok": True, "data": arguments}

    coordinator = SessionCoordinator()
    result = asyncio.run(ForgeToolStartSessionTool(coordinator).execute(
        task_id="task-1", tool_id="camera.stream", ownership="task",
        arguments={"preparation_ref": "preparation://rewritten"},
    ))
    assert "preparation://scene/red" in result
    assert coordinator.seen == {}


def test_unbound_diagnostic_query_does_not_read_a_task():
    loop = object.__new__(AgentLoop)
    loop._planning_dispatch = SimpleNamespace(admit_forge_tool=lambda name, args: None)
    loop.forge_task_coordinator = SimpleNamespace(
        get_task=lambda _id: pytest.fail("unbound diagnostic read a task")
    )
    assert loop._planning_guard("forge_tool_query", {
        "tool_id": "scene.observe", "arguments": {},
    }) is None


def test_continuation_projection_excludes_prior_execution_payloads():
    node = SimpleNamespace(node_id="red-place", capability="object.place")
    settled = SimpleNamespace(node_id="red-place", status="completed")
    revision = SimpleNamespace(
        revision_id="revision-1",
        plan_graph=SimpleNamespace(nodes=(node,)),
        node_settlements=(settled,),
        discovery_evidence_refs=("artifact://current",),
        replan_evidence_refs=(),
    )
    task = SimpleNamespace(
        task_id="task-1",
        active_revision_id="revision-1",
        active_revision=revision,
        task_description="Arrange blocks",
        verification={"mode": "semantic"},
    )
    projection = continuation_task_prompt_projection(task)
    assert projection["completed_nodes"] == ["red-place"]
    assert projection["latest_effect"] is None
    assert "current_evidence_refs" not in projection
    assert "execution_records" not in projection
    assert "preparation_ref" not in str(projection)


def test_continuation_rejects_future_dependency_before_task_access():
    tool = ForgeTaskContinuePlanTool(SimpleNamespace(get_task=lambda _id: pytest.fail("task read")))
    with pytest.raises(ValueError, match="future nodes need a later continuation"):
        asyncio.run(tool.execute(
            task_id="task-1",
            nodes=[{"node_id": "observe-next", "dependencies": ["understand-next"]}],
            reason="refresh scene",
        ))


def test_continuation_projection_keeps_latest_effect_without_old_payload():
    effect = SimpleNamespace(
        node_id="red-place", tool_id="object.place", semantics="action", status="succeeded",
        evidence_refs=("artifact://action", "artifact://video"),
        response={"data": {"result": {
            "world_change_started": True, "new_scene_revision": "scene-2",
            "post_release_evidence": {"availability": "complete", "artifact_refs": ["artifact://action"]},
            "preparation_ref": "preparation://old-scene/red",
        }}},
    )
    revision = SimpleNamespace(plan_graph=SimpleNamespace(nodes=()), node_settlements=())
    task = SimpleNamespace(task_id="task-1", active_revision_id="revision-1",
                           active_revision=revision, execution_records=[effect],
                           task_description="Arrange blocks", verification={"mode": "semantic"})
    projection = continuation_task_prompt_projection(task)
    assert projection["latest_effect"]["new_scene_revision"] == "scene-2"
    assert projection["latest_effect"]["post_release_evidence"]["availability"] == "complete"
    assert "preparation://old-scene/red" not in str(projection)
