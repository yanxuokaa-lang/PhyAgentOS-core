from __future__ import annotations

from types import SimpleNamespace

from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.planning import AdmissionDecision


class _Coordinator:
    def __init__(self, task):
        self.task = task

    def get_task(self, task_id: str):
        assert task_id == self.task.task_id
        return self.task


class _Dispatch:
    graph = SimpleNamespace(task_id="old-task")

    def __init__(self):
        self.calls = 0

    def admit_forge_tool(self, wrapper_name, arguments):
        self.calls += 1
        return AdmissionDecision(
            allowed=False,
            code="identity_mismatch",
            detail="stale dispatch rejected the call",
            node_id="unknown",
            tool_id=str(arguments.get("tool_id", "unknown")),
        )


def _loop(task, dispatch):
    loop = AgentLoop.__new__(AgentLoop)
    loop._planning_dispatch = dispatch
    loop.forge_task_coordinator = _Coordinator(task)
    return loop


def _task(*, graph=None, terminal=False):
    return SimpleNamespace(
        task_id="new-task",
        terminal=terminal,
        active_revision=SimpleNamespace(plan_graph=graph),
    )


def test_stale_dispatch_allows_only_pre_graph_scene_observe():
    dispatch = _Dispatch()
    loop = _loop(_task(), dispatch)

    result = loop._planning_guard(
        "forge_tool_query",
        {"task_id": "new-task", "tool_id": "scene.observe"},
    )

    assert result is None
    assert dispatch.calls == 0


def test_pre_graph_exception_does_not_allow_actions_or_bound_queries():
    dispatch = _Dispatch()
    loop = _loop(_task(), dispatch)

    action_result = loop._planning_guard(
        "forge_tool_start_action",
        {"task_id": "new-task", "tool_id": "object.acquire"},
    )
    bound_query_result = loop._planning_guard(
        "forge_tool_query",
        {
            "task_id": "new-task",
            "tool_id": "scene.observe",
            "planning_binding": {"node_id": "initial-observe"},
        },
    )

    assert '"code":"identity_mismatch"' in action_result
    assert '"code":"identity_mismatch"' in bound_query_result
    assert dispatch.calls == 2


def test_graph_bound_or_terminal_tasks_still_use_dispatch():
    dispatch = _Dispatch()
    graph_task_loop = _loop(_task(graph=SimpleNamespace()), dispatch)
    terminal_task_loop = _loop(_task(terminal=True), dispatch)

    graph_result = graph_task_loop._planning_guard(
        "forge_tool_query",
        {"task_id": "new-task", "tool_id": "scene.observe"},
    )
    terminal_result = terminal_task_loop._planning_guard(
        "forge_tool_query",
        {"task_id": "new-task", "tool_id": "scene.observe"},
    )

    assert '"code":"identity_mismatch"' in graph_result
    assert '"code":"identity_mismatch"' in terminal_result
    assert dispatch.calls == 2


def test_same_task_query_is_not_treated_as_discovery():
    dispatch = _Dispatch()
    dispatch.graph = SimpleNamespace(task_id="new-task")
    loop = _loop(_task(), dispatch)

    result = loop._planning_guard(
        "forge_tool_query",
        {"task_id": "new-task", "tool_id": "scene.observe"},
    )

    assert '"code":"identity_mismatch"' in result
    assert dispatch.calls == 1
