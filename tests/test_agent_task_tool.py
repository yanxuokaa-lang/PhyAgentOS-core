from __future__ import annotations

import asyncio
import json
from unittest.mock import Mock

import pytest

from PhyAgentOS.agent.tools.forge_task import ForgeTaskCancelTool, ForgeTaskCreateTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskBusyError, AgentTaskCoordinator, ToolExecutionRecord
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


def _task_with_query_record(
    tmp_path,
    *,
    provider_status: str,
    motion_authorized: bool = False,
    resources=None,
):
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    task = coordinator.create_task(
        task_description="provider-neutral discovery task",
        verification=TaskVerificationContract(mode="off"),
    )
    record = ToolExecutionRecord(
        record_id=f"query-{provider_status}",
        revision_id=task.active_revision_id,
        tool_id="resource.describe",
        semantics="query",
        caller_id="paos:test",
        status="succeeded",
        response={
            "data": {
                "status": provider_status,
                "resources": resources if resources is not None else [
                    {"resource_id": "resource-1", "availability": "available"}
                ],
                "motion_authorized": motion_authorized,
            }
        },
    )
    coordinator.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(record),
        event_type="test_query_record",
    )
    return coordinator, coordinator.get_task(task.task_id), record


def test_agent_cancel_requires_structured_blocker_record():
    tool = ForgeTaskCancelTool(Mock())
    assert "blocker_record_id" in tool.parameters["required"]


def test_available_query_motion_false_cannot_cancel_task(tmp_path):
    coordinator, task, record = _task_with_query_record(
        tmp_path,
        provider_status="available",
        motion_authorized=False,
    )
    tool = ForgeTaskCancelTool(coordinator)

    response = json.loads(asyncio.run(tool.execute(
        task.task_id,
        blocker_record_id=record.record_id,
        reason="motion_authorized=false",
    )))

    assert response["ok"] is False
    assert response["error"]["code"] == "agent_cancel_blocker_invalid"
    assert coordinator.get_task(task.task_id).cancellation_requested is False


@pytest.mark.parametrize("provider_status", ["unavailable", "invalid", "stale"])
def test_failed_query_status_remains_valid_agent_cancel_blocker(tmp_path, provider_status):
    coordinator, task, record = _task_with_query_record(
        tmp_path,
        provider_status=provider_status,
    )
    tool = ForgeTaskCancelTool(coordinator)

    response = json.loads(asyncio.run(tool.execute(
        task.task_id,
        blocker_record_id=record.record_id,
        reason=f"provider status {provider_status}",
    )))

    assert response["ok"] is True
    assert coordinator.get_task(task.task_id).cancellation_requested is True


def test_operator_cancel_remains_available_without_blocker_record(tmp_path):
    coordinator, task, _record = _task_with_query_record(
        tmp_path,
        provider_status="available",
    )

    result = asyncio.run(coordinator.cancel_task(task.task_id, reason="operator stop"))

    assert result.cancellation_requested is True


def test_no_available_resources_remain_a_valid_agent_cancel_blocker(tmp_path):
    coordinator, task, record = _task_with_query_record(
        tmp_path,
        provider_status="available",
        resources=[
            {"resource_id": "left", "availability": "unavailable"},
            {"resource_id": "right", "availability": "busy"},
        ],
    )
    tool = ForgeTaskCancelTool(coordinator)

    response = json.loads(asyncio.run(tool.execute(
        task.task_id,
        blocker_record_id=record.record_id,
        reason="no available resource",
    )))

    assert response["ok"] is True
