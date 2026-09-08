from __future__ import annotations

import asyncio

from PhyAgentOS.agent.long_horizon import LongHorizonTaskController
from PhyAgentOS.agent.planning_loop import NodeContextProvider, PlanningLoopAdapter
from PhyAgentOS.cli.commands import _interactive_task_control
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskStatus
from PhyAgentOS.planning import (
    AdmissionContext,
    PlanGraph,
    PlanNode,
    ToolResultEnvelope,
    plan_graph_digest,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract


def _graph(task_id: str, revision_id: str) -> PlanGraph:
    payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [
            PlanNode(node_id="first", obligation_id="ob-first", capability="object.arrange").model_dump(mode="json"),
            PlanNode(node_id="second", obligation_id="ob-second", capability="object.arrange", dependencies=("first",)).model_dump(mode="json"),
        ],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    return PlanGraph.model_validate(payload)


def _coordinator(tmp_path):
    return AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
        verifier=None,
    )


def _controller(c, calls):
    def execute(context):
        calls.append(context.node_id)
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="succeeded",
        )

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(scene_revision="scene-1"),
    )
    return LongHorizonTaskController(
        c,
        adapter,
        scene_revision_provider=lambda _: "scene-1",
    )


def test_controller_pause_and_resume_at_node_checkpoint(tmp_path):
    c = _coordinator(tmp_path)
    task = c.create_task(task_description="long task", verification=TaskVerificationContract(mode="off"))
    c.expand_discovery_revision(task.task_id, plan_graph=_graph(task.task_id, "revision-1"), plan_graph_ref="artifact://plan/1")
    calls = []
    controller = _controller(c, calls)

    assert controller.pause(task.task_id).status == "paused"
    assert controller.status(task.task_id).status == "paused"
    restarted_controller = _controller(c, calls)
    paused = asyncio.run(restarted_controller.run(task.task_id))
    assert paused.status == "paused"
    assert calls == []
    assert c.get_task(task.task_id).pause_requested is True

    restarted_controller.resume(task.task_id)
    result = asyncio.run(restarted_controller.run(task.task_id))
    assert result.status == "completed"
    assert calls == ["first", "second"]
    assert c.get_task(task.task_id).pause_requested is False


def test_controller_short_circuits_terminal_task(tmp_path):
    c = _coordinator(tmp_path)
    task = c.create_task(task_description="already done", verification=TaskVerificationContract(mode="off"))
    c.store.update(
        task.task_id,
        lambda current: setattr(current, "status", AgentTaskStatus.SUCCEEDED),
        event_type="test_terminal",
    )
    calls = []
    result = asyncio.run(_controller(c, calls).run(task.task_id))
    assert result.status == "succeeded"
    assert calls == []
    assert _controller(c, calls).pause(task.task_id).status == "succeeded"


def test_controller_does_not_run_while_replan_is_awaited(tmp_path):
    c = _coordinator(tmp_path)
    task = c.create_task(task_description="needs recovery", verification=TaskVerificationContract(mode="off"))
    c.request_replan(task.task_id, reason="test recovery")
    calls = []
    result = asyncio.run(_controller(c, calls).run(task.task_id))
    assert result.status == "awaiting_replan"
    assert calls == []


def test_control_only_controller_uses_persisted_coordinator_state(tmp_path):
    c = _coordinator(tmp_path)
    task = c.create_task(task_description="control", verification=TaskVerificationContract(mode="off"))
    controller = LongHorizonTaskController.for_control(c)

    assert controller.status(task.task_id).status == "executing"
    assert controller.pause(task.task_id).status == "paused"
    assert controller.status(task.task_id).status == "paused"
    assert controller.resume(task.task_id).status == "executing"
    try:
        asyncio.run(controller.run(task.task_id))
    except RuntimeError as exc:
        assert "control-only" in str(exc)
    else:
        raise AssertionError("control-only controller must not execute without an adapter")


def test_interactive_task_control_consumes_only_supported_commands(tmp_path):
    c = _coordinator(tmp_path)
    task = c.create_task(task_description="interactive", verification=TaskVerificationContract(mode="off"))
    controller = LongHorizonTaskController.for_control(c)

    assert _interactive_task_control(f"/task pause {task.task_id}", controller) is True
    assert c.get_task(task.task_id).pause_requested is True
    assert _interactive_task_control(f"/task resume {task.task_id}", controller) is True
    assert c.get_task(task.task_id).pause_requested is False
    assert _interactive_task_control("/task unknown task", controller) is False


def test_controller_start_runs_in_background_and_replays_without_tools(tmp_path):
    c = _coordinator(tmp_path)
    task = c.create_task(task_description="background", verification=TaskVerificationContract(mode="off"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=_graph(task.task_id, "revision-1"),
        plan_graph_ref="artifact://plan/background",
    )
    calls = []
    controller = _controller(c, calls)

    async def exercise():
        started = controller.start(task.task_id)
        assert started.status == "executing"
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return controller.replay(task.task_id)

    replay = asyncio.run(exercise())
    assert calls == ["first", "second"]
    assert replay["revision-1"] == ()


def test_interactive_async_stop_uses_coordinator_cancellation(tmp_path):
    c = _coordinator(tmp_path)
    task = c.create_task(task_description="stop", verification=TaskVerificationContract(mode="off"))
    controller = LongHorizonTaskController.for_control(c)

    async def exercise():
        return await _interactive_task_control_async(f"/task stop {task.task_id}", controller)

    from PhyAgentOS.cli.commands import _interactive_task_control_async
    assert asyncio.run(exercise()) is True
    assert c.get_task(task.task_id).cancellation_requested is True
