from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool


class _Coordinator:
    def __init__(self):
        self.proposals = []

    def persist_planning_selection(self, proposal):
        self.proposals.append(proposal)
        return {
            "node_id": proposal["node_id"],
            "node_digest": proposal["node_digest"],
            "obligation_id": "observe",
            "input_binding_digest": proposal["input_binding_digest"],
            "decision_trace_ref": "artifact://planning-traces/task-1/revision-1/observe/t1",
            "task_id": proposal["task_id"],
            "revision_id": proposal["revision_id"],
            "scene_revision": proposal["scene_revision"],
        }


class _Dispatch:
    graph = SimpleNamespace(task_id="task-1")

    def prepare_selection(self, **kwargs):
        return {
            "task_id": "task-1",
            "revision_id": "revision-1",
            "node_id": kwargs["node_id"],
            "node_digest": "1" * 64,
            "obligation_id": "observe",
            "tool_id": kwargs["tool_id"],
            "candidate_tool_ids": (kwargs["tool_id"],),
            "input_binding_digest": "2" * 64,
            "scene_revision": "scene-1",
            "evidence_refs": (),
            "decision_reason": kwargs["decision_reason"],
        }


def test_plan_select_is_control_plane_only_and_returns_binding():
    coordinator = _Coordinator()
    tool = ForgePlanSelectTool(coordinator, lambda: _Dispatch())

    result = json.loads(asyncio.run(tool.execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is True
    assert result["motion_authorized"] is False
    assert result["data"]["planning_binding"]["decision_trace_ref"].startswith("artifact://")
    assert coordinator.proposals[0]["tool_id"] == "scene.observe"


def test_plan_select_rejects_when_task_is_not_active_graph():
    coordinator = _Coordinator()
    tool = ForgePlanSelectTool(coordinator, lambda: None)

    result = json.loads(asyncio.run(tool.execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert coordinator.proposals == []
