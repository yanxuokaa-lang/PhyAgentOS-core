"""Regressions for partial effects and current facts across relocation nodes."""

import asyncio
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.planning_context import PlanningContextUnavailableError, context_from_task
from PhyAgentOS.agent.planning_loop import AgentLoopNodeExecutor, NodeExecutionContext
from PhyAgentOS.forge.capability_runtime import ActionAdmission, CapabilityRuntime
from PhyAgentOS.planning import PlanNode, ToolResultEnvelope, settle_node


def result(**kwargs):
    return ToolResultEnvelope(task_id="task", revision_id="revision", node_id="relocate", tool_id="place", **kwargs)


@pytest.mark.parametrize("status", ["failed", "cancelled", "stopped", "unknown"])
def test_failure_retains_effects_measured_scene_and_evidence(status):
    settlement = settle_node(
        PlanNode(node_id="relocate", obligation_id="move", capability="object.relocate"),
        result(status=status, world_changed=True, new_scene_revision="scene-2", outcome_known=False, evidence_refs=("slip",)),
        current_scene_revision="scene-1",
    )
    assert settlement.status == "outcome_unknown"
    assert settlement.world_change_started is True
    assert settlement.outcome_known is False
    assert settlement.scene_revision == "scene-2"
    assert settlement.evidence_refs == ("slip",)


def test_started_motion_does_not_require_fabricated_scene():
    value = result(status="failed", world_change_started=True, outcome_known=False)
    assert value.new_scene_revision is None


def test_observation_only_cannot_settle_declared_relocation_evidence():
    node = PlanNode(node_id="relocate", obligation_id="move", capability="object.relocate", produced_evidence=("placed",))
    settlement = settle_node(node, result(status="succeeded", evidence_refs=("observed",)), current_scene_revision="scene-1")
    assert settlement.status == "failed"
    assert settlement.failure_code == "missing_produced_evidence"


def record(payload, *, status="succeeded", terminal=True, evidence=()):
    return SimpleNamespace(response={"data": payload}, status=status, terminal=terminal, evidence_refs=evidence)


def task(*records):
    return SimpleNamespace(execution_records=records, active_revision=SimpleNamespace(node_settlements=[]))


def test_current_scene_retires_geometry_and_empty_snapshot_releases_resource():
    records = task(
        record({"scene_revision": "scene-1", "resources_in_use": ["arm:right"], "condition_facts": {"clear": True}}, evidence=("old-grasp",)),
        record({"new_scene_revision": "scene-2", "resources_in_use": [], "evidence_refs": ["new-observation"]}),
        record({"scene_revision": "echoed-scene"}, status="failed"),
        record({"scene_revision": "pending-scene", "resources_in_use": ["arm:right"]}, terminal=False),
    )
    current = context_from_task(records)
    assert current.scene_revision == "scene-2"
    assert current.evidence_refs == frozenset({"new-observation"})
    assert not current.resources_in_use
    assert not current.condition_facts
    assert records.execution_records[0].evidence_refs == ("old-grasp",)


def test_failed_input_echo_cannot_supply_initial_scene():
    with pytest.raises(PlanningContextUnavailableError):
        context_from_task(task(record({"scene_revision": "input"}, status="failed")))


def test_partial_effect_blocks_old_scene_until_fresh_observation():
    observed = record({"scene_revision": "scene-1"}, evidence=("old",))
    failed = record({"scene_revision": "scene-1", "capability_outcome_summary": {"world_change_started": True, "outcome_known": False}}, status="failed")
    with pytest.raises(PlanningContextUnavailableError, match="fresh observation"):
        context_from_task(task(observed, failed))
    refreshed = context_from_task(task(observed, failed, record({"scene_revision": "scene-2"}, evidence=("fresh",))))
    assert refreshed.scene_revision == "scene-2"
    assert refreshed.evidence_refs == frozenset({"fresh"})


def test_unknown_effect_requires_observation_even_with_a_runtime_revision():
    current = task(record({"scene_revision": "scene-1"}), record({"new_scene_revision": "scene-2", "outcome_known": False}, status="unknown"))
    with pytest.raises(PlanningContextUnavailableError):
        context_from_task(current)
    recovery = context_from_task(current, allow_refresh=True)
    assert recovery.scene_revision == "scene-2"
    assert dict(recovery.condition_facts)["scene_current"] is False


def test_node_executor_projects_nested_failed_action_after_successful_observation():
    revision = SimpleNamespace(execution_records=[])
    saved_task = SimpleNamespace(active_revision=revision, active_revision_id="revision")

    class Loop:
        async def run_node_turn(self, **kwargs):
            revision.execution_records.extend([
                SimpleNamespace(record_id="observe", node_id="relocate", tool_id="observe", terminal=True, status="succeeded", error=None, evidence_refs=(), response={"data": {"new_scene_revision": "scene-2"}}),
                SimpleNamespace(record_id="place", node_id="relocate", tool_id="place", terminal=True, status="failed", error=None, evidence_refs=(), response={"data": {"result": {"new_scene_revision": "scene-3", "world_changed": True, "capability_outcome_summary": {"world_change_started": True, "outcome_known": False, "artifact_refs": ["artifact://slip"], "failure_code": "slip", "failure_owner": "execution"}}}}),
            ])

    executor = AgentLoopNodeExecutor(Loop(), SimpleNamespace(get_task=lambda _: saved_task))
    context = NodeExecutionContext(task_id="task", revision_id="revision", node_id="relocate", capability="object.relocate", dependencies=(), required_evidence=(), input_bindings={}, scene_revision="scene-1")
    projected = asyncio.run(executor(context))
    assert projected.status == "failed"
    assert projected.world_changed is True
    assert projected.world_change_started is True
    assert projected.outcome_known is False
    assert projected.new_scene_revision == "scene-3"
    assert projected.evidence_refs == ("artifact://slip",)
    assert projected.failure_code == "slip"


class _LifecycleClient:
    def __init__(self, statuses, results):
        self.statuses = iter(statuses)
        self.results = iter(results)
        self.status_calls = 0
        self.result_calls = 0

    async def invocation_status(self, _invocation_id):
        self.status_calls += 1
        return next(self.statuses)

    async def invocation_result(self, _invocation_id):
        self.result_calls += 1
        return next(self.results)


class _LifecycleCoordinator:
    def __init__(self, client):
        self.client = client
        records = []
        self.task = SimpleNamespace(
            active_revision=SimpleNamespace(execution_records=records),
            execution_records=records,
            active_revision_id="revision",
        )
        self.unknown_codes = []
        self.started = 0

    def get_task(self, _task_id):
        return self.task

    async def start_action(self, _task_id, _tool_id, _arguments, *, planning_binding=None):
        self.started += 1
        binding = planning_binding or {}
        self.task.active_revision.execution_records.append(SimpleNamespace(
            record_id="action-1",
            node_id=binding.get("node_id", "relocate"),
            semantics="action",
            tool_id="object.place",
            status="accepted",
            terminal=False,
            invocation_id="invocation://place/1",
            error=None,
            evidence_refs=(),
            response={"data": {"phase": "accepted"}},
        ))
        return {"data": {"invocation_id": "invocation://place/1"}}

    def observe_action(self, _task_id, _invocation_id, response):
        record = self.task.active_revision.execution_records[0]
        data = response.get("data", response)
        status = data.get("status") or data.get("phase")
        if status == "completed":
            status = "succeeded"
        record.status = status
        record.response = response
        record.terminal = status in {"succeeded", "failed", "cancelled", "stopped", "unknown"}

    def mark_execution_unknown(self, _task_id, _record_id, *, code, message):
        record = self.task.active_revision.execution_records[0]
        record.status = "unknown"
        record.terminal = True
        record.error = {"code": code, "message": message}
        self.unknown_codes.append(code)


class _ActionAgent:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.turns = 0

    async def run_node_turn(self, *, task_id, node_id, **_kwargs):
        self.turns += 1
        await self.coordinator.start_action(
            task_id,
            "object.place",
            {"entity_ref": "entity://green"},
            planning_binding={"node_id": node_id},
        )


def _executor_context():
    return NodeExecutionContext(
        task_id="task",
        revision_id="revision",
        node_id="relocate",
        capability="object.relocate",
        dependencies=(),
        required_evidence=(),
        input_bindings={"entity_ref": "entity://green"},
        scene_revision="scene://s0",
    )


def test_agent_node_executor_reconciles_action_to_terminal_result_without_resend():
    client = _LifecycleClient(
        statuses=[{"data": {"status": "running"}}, {"data": {"status": "running"}}],
        results=[
            {"data": {"status": "pending"}},
            {"data": {"status": "succeeded", "result": {
                "status": "succeeded",
                "world_changed": True,
                "new_scene_revision": "scene://s2",
                "capability_outcome_summary": {"world_change_started": True, "outcome_known": True},
            }}},
        ],
    )
    coordinator = _LifecycleCoordinator(client)
    agent = _ActionAgent(coordinator)
    projected = asyncio.run(AgentLoopNodeExecutor(agent, coordinator)(_executor_context()))

    record = coordinator.task.active_revision.execution_records[0]
    assert projected.status == "succeeded"
    assert projected.new_scene_revision == "scene://s2"
    assert record.status == "succeeded"
    assert client.status_calls == 2
    assert client.result_calls == 2
    assert coordinator.started == 1
    assert agent.turns == 1


@pytest.mark.parametrize("terminal_status", ["failed", "unknown"])
def test_agent_node_executor_preserves_failed_or_unknown_action_status(terminal_status):
    client = _LifecycleClient(
        statuses=[{"data": {"status": terminal_status}}],
        results=[{"data": {"status": terminal_status, "result": {
            "status": terminal_status,
            "failure_code": "provider_failure",
            "capability_outcome_summary": {"world_change_started": True, "outcome_known": False},
        }}}],
    )
    coordinator = _LifecycleCoordinator(client)
    projected = asyncio.run(AgentLoopNodeExecutor(_ActionAgent(coordinator), coordinator)(_executor_context()))
    assert projected.status == terminal_status
    assert coordinator.task.active_revision.execution_records[0].status == terminal_status


def test_agent_node_executor_marks_poll_budget_exhaustion_unknown():
    client = _LifecycleClient(
        statuses=[{"data": {"status": "running"}}],
        results=[{"data": {"status": "pending"}}],
    )
    coordinator = _LifecycleCoordinator(client)
    projected = asyncio.run(
        AgentLoopNodeExecutor(_ActionAgent(coordinator), coordinator, max_action_polls=1)(_executor_context())
    )
    assert projected.status == "unknown"
    record = coordinator.task.active_revision.execution_records[0]
    assert record.status == "unknown"
    assert record.response["error"]["code"] == "action_poll_budget_exhausted"


def test_agent_node_executor_marks_gateway_read_failure_unknown():
    class BrokenClient(_LifecycleClient):
        async def invocation_status(self, _invocation_id):
            raise TimeoutError("gateway read timed out")

    coordinator = _LifecycleCoordinator(BrokenClient([], []))
    projected = asyncio.run(AgentLoopNodeExecutor(_ActionAgent(coordinator), coordinator)(_executor_context()))
    assert projected.status == "unknown"
    assert coordinator.unknown_codes == ["action_reconciliation_failed"]


@pytest.mark.parametrize("started", [True, None])
@pytest.mark.parametrize("semantics", ["action", "session"])
def test_runtime_does_not_claim_unconfirmed_motion_stopped(started, semantics):
    class Endpoint:
        def admit(self, arguments):
            return ActionAdmission(pending_polls=3, terminal_result={"status": "succeeded", "capability_outcome_summary": {"world_change_started": started, "outcome_known": True, "artifact_refs": ["artifact://partial"]}})

    runtime = CapabilityRuntime()
    runtime.register_tool({"tool_id": "motion", "endpoint_id": "motion", "operation": "run", "semantics": semantics}, Endpoint())
    invocation = runtime.start_action("motion")["invocation_id"]
    request = runtime.cancel_invocation if semantics == "action" else runtime.stop_invocation
    assert request(invocation)["accepted"] is True
    terminal = runtime.invocation_result(invocation)
    assert terminal["status"] == "unknown"
    summary = terminal["result"]["capability_outcome_summary"]
    assert summary["outcome_known"] is False
    assert summary["world_change_started"] is started
    assert summary["artifact_refs"] == ["artifact://partial"]
