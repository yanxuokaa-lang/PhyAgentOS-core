from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from isaacsim_lab.agent_host import (
    LabPlanningContext,
    ObservedQueryPort,
    compose_host,
    environment_guidance,
)
from isaacsim_lab.profile import LabUtopiaProfile


@pytest.mark.asyncio
async def test_semantic_query_port_retains_only_observed_runtime_receipts():
    class Client:
        async def invoke_query_tool(self, tool_id, arguments):
            return {'data': {'status': arguments['status'], 'observation_ref': 'observation://real'}}
    port = ObservedQueryPort(Client())
    result = await port('scene.observe', {'status': 'unavailable'})
    assert result['status'] == 'unavailable'
    assert not port.observations
    await port('scene.observe', {'status': 'available'})
    assert set(port.observations) == {'observation://real'}


def test_planning_context_cannot_admit_agent_invented_observation():
    nodes = [SimpleNamespace(input_bindings={'binding': {'observation_ref': ref}})
             for ref in ('observation://real', 'observation://invented')]
    task = SimpleNamespace(execution_records=(), tool_bindings=(), primary_skill_binding=None,
                           active_revision=SimpleNamespace(plan_graph=SimpleNamespace(nodes=nodes)))
    coordinator = SimpleNamespace(get_task=lambda _: task, effective_node_settlements=lambda _: ())
    engine = SimpleNamespace(backend=SimpleNamespace(current_scene_revision=lambda: 'scene-current'))
    query = SimpleNamespace(observations={'observation://real': {}})
    result = LabPlanningContext(coordinator, engine, query)('task')
    assert result.scene_revision == 'scene-current'
    assert result.evidence_refs == {'observation://real'}


def test_host_guidance_defaults_to_no_motion():
    assert 'motion is disabled' in environment_guidance('sensor://front', False)
    assert 'Simulated motion is authorized' in environment_guidance('sensor://front', True)


def test_host_guidance_uses_user_task_parameters_for_generic_process_actions():
    guidance = environment_guidance('sensor://front', False)
    assert 'operation="pour" or operation="stir"' in guidance
    assert 'object.pour and tool.stir' in guidance
    assert 'tilt_rad and hold_s' in guidance
    assert 'radius_m, depth_m, turns, duration_s and direction' in guidance
    assert 'Do not hard-code a bottle count, operation sequence, or numeric process values' in guidance
    assert 'Ask the user for missing required values before creating a manipulation task' in guidance
    assert 'do not use the legacy pour_cycle or stir_cycle names' in guidance
    assert 'Default pour parameters' not in guidance
    assert 'Default stir parameters' not in guidance


@pytest.mark.parametrize('has_receipt', [True, False])
@pytest.mark.parametrize('terminal', [True, False])
def test_pending_first_action_uses_real_query_context_for_reconciliation(has_receipt, terminal):
    from PhyAgentOS.agent.planning_context import PlanningContextUnavailableError

    node = SimpleNamespace(input_bindings={'binding': {'observation_ref': 'observation://real'}})
    task = SimpleNamespace(execution_records=(SimpleNamespace(terminal=terminal),), tool_bindings=(),
                           primary_skill_binding=None, active_revision=SimpleNamespace(
                               plan_graph=SimpleNamespace(nodes=[node])))
    coordinator = SimpleNamespace(get_task=lambda _: task, effective_node_settlements=lambda _: ())
    engine = SimpleNamespace(backend=SimpleNamespace(current_scene_revision=lambda: 'scene-after-lift'))
    queries = SimpleNamespace(observations={'observation://real': {}} if has_receipt else {})
    context = LabPlanningContext(coordinator, engine, queries)
    if has_receipt and not terminal:
        assert context('task').scene_revision == 'scene-after-lift'
        assert context('task').evidence_refs == {'observation://real'}
    else:
        with pytest.raises(PlanningContextUnavailableError):
            context('task')


@pytest.mark.asyncio
async def test_host_enrolls_real_subtask_contract_and_rejects_other_actions(tmp_path, monkeypatch):
    monkeypatch.setattr("isaacsim_lab.agent_host.build_visual_providers", lambda *args: (Mock(), Mock()))
    from PhyAgentOS.forge.task import AgentTaskError, TaskVerificationContract

    for name in ("camera.yaml", "scene.usd", "robot.usd"):
        (tmp_path / name).write_text("test fixture; never loaded by a simulator")
    profile = LabUtopiaProfile.from_mapping({
        "lab_root": str(tmp_path), "config_path": "camera.yaml", "scene_usd_path": "scene.usd", "robot_usd_path": "robot.usd",
        "source_path": "/World/source", "destination_path": "/World/destination"}, base_dir=tmp_path)
    loop, coordinator, bundle, assignments = compose_host(
        profile=profile, workspace=tmp_path, provider=Mock(generation=SimpleNamespace(max_tokens=2048)), inference=Mock(),
        model="test-model", sensor_ref="sensor://front")
    try:
        task = await coordinator.create_task(task_description="test manipulation", verification=TaskVerificationContract(mode="off"))
        assert coordinator.config.execution_timeout_s == 1800
        executor = loop.long_horizon_controller.adapter.node_executor
        assert executor.max_action_polls * executor.action_poll_interval_s == 1800
        assert task.runtime_binding is not None
        contract = await coordinator.enroll_tool_contract(task.task_id, "manipulation.execute_subtask", "action")
        assert contract.planning_policy is not None
        assert "manipulation.execute_subtask" in contract.planning_policy.capabilities
        assert coordinator.get_task(task.task_id).tool_bindings == [contract]
        with pytest.raises(AgentTaskError, match="not authorized"):
            await coordinator.enroll_tool_contract(task.task_id, "object.acquire", "action")
        resolver = coordinator.binding_resolver
        resolver.runtime_registry.replace(replace(resolver.runtime_registry.current(), runtime_instance_id="replacement"))
        with pytest.raises(AgentTaskError, match="binding"):
            await coordinator.enroll_tool_contract(task.task_id, "manipulation.execute_subtask", "action")
    finally:
        await loop.close_mcp()
        await coordinator.client.close()
        bundle.client.close()
        assignments.close()
