from __future__ import annotations

import asyncio
import json
from unittest.mock import Mock

import pytest

from PhyAgentOS.agent.tools.forge_task import ForgeTaskCreateTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskBusyError, AgentTaskCoordinator
from PhyAgentOS.verification.contracts import TaskVerificationContract


def test_task_create_requires_explicit_verification_choice():
    coordinator = Mock()
    tool = ForgeTaskCreateTool(coordinator)
    assert tool.parameters["properties"]["verification"]["required"] == ["mode"]
    with pytest.raises(ValueError, match="verification.mode must be explicit"):
        asyncio.run(tool.execute("Arrange RGB and verify", {}))
    coordinator.create_task.assert_not_called()
    assert TaskVerificationContract().mode == "off"


def test_task_create_preserves_enforced_verification(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object(), verifier=Mock())
    tool = ForgeTaskCreateTool(coordinator)
    contract = {"mode": "enforce", "goal": "Arrange RGB",
                "success_criteria": ["All three blocks occupy their destinations"]}
    created = json.loads(asyncio.run(tool.execute("Arrange RGB", contract)))
    task = coordinator.get_task(created["data"]["task_id"])
    assert task.verification.mode == "enforce"
    assert task.verification.success_criteria == contract["success_criteria"]


def test_task_create_reports_cross_session_owner_without_takeover(tmp_path):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    first = ForgeTaskCreateTool(coordinator)
    first.set_context("cli:owner")
    verification = {"mode": "off"}
    created = json.loads(asyncio.run(first.execute("owner task", verification)))
    assert created["ok"] is True

    second = ForgeTaskCreateTool(coordinator)
    second.set_context("cli:other")
    conflict = json.loads(asyncio.run(second.execute("other task", verification)))
    assert conflict["ok"] is False
    assert conflict["error"]["code"] == "agent_task_busy"
    assert conflict["error"]["task_id"] == created["data"]["task_id"]
    assert conflict["error"]["owner_session_key"] == "cli:owner"
    assert "read-only" in conflict["error"]["action"]
    assert conflict["motion_authorized"] is False


def test_task_create_reports_busy_error_raised_by_bound_async_creation():
    class AsyncBusyCoordinator:
        async def create_task(self, **_kwargs):
            raise AgentTaskBusyError("task_bound", "cli:bound-owner")

    tool = ForgeTaskCreateTool(AsyncBusyCoordinator())
    tool.set_context("cli:other")
    conflict = json.loads(asyncio.run(tool.execute("other task", {"mode": "off"})))
    assert conflict["ok"] is False
    assert conflict["error"]["task_id"] == "task_bound"
    assert conflict["error"]["owner_session_key"] == "cli:bound-owner"
