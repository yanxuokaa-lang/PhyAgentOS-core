from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.experience.activation import SkillActivationManager
from PhyAgentOS.agent.experience.store import ExperienceStore
from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.agent.plan_proposal import compile_task_plan
from PhyAgentOS.agent.planning_loop import _planning_record_status
from PhyAgentOS.agent.recovery_decisions import AgentRecoveryDecisions
from PhyAgentOS.agent.tools.forge_task import ForgeTaskMaterializePlanTool
from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec, ForgeSkillBinding
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskError, AgentTaskStatus
from PhyAgentOS.planning import NodeSettlement, ToolSpecPolicy, build_replan_delta
from PhyAgentOS.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from PhyAgentOS.verification.contracts import TaskVerificationContract


class ScriptedProvider(LLMProvider):
    """A model transport fixture, not evidence of semantic model accuracy."""

    def __init__(self, responses=()):
        super().__init__()
        self.responses = list(responses)
        self.requests = []

    async def chat(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)

    def get_default_model(self):
        return "fixture-model"


def setup_task(tmp_path, goal="Move the left red object into the tray"):
    c = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    task = c.create_task(task_description=goal, verification=TaskVerificationContract(mode="off"))
    policy = ToolSpecPolicy(tool_id="scene.observe", semantics="query", spec_digest="a" * 64,
                            capabilities=("scene.observe", "object.relocate", "task.verify"))
    binding = ForgeSkillBinding(
        binding_id="binding-test", skill_name="pick-place-workflow", skill_version="1.0.0",
        manifest_sha256="a" * 64, skill_document_sha256="b" * 64,
        runtime_profile="test", runtime_instance_id="test-runtime", gateway_url="http://test.invalid",
        required_tools=(BoundToolSpec(tool_id="scene.observe", semantics="query", spec_sha256="a" * 64,
                                     ready_at_binding=True, planning_policy=policy),),
    )
    c.store.update(task.task_id, lambda item: setattr(item, "primary_skill_binding", binding), event_type="test_binding")
    return c, c.get_task(task.task_id)


def semantic_nodes(count):
    nodes = [{"node_id": f"chosen-{i}", "obligation_id": f"move-{i}", "capability": "object.relocate",
              "input_bindings": {"entity_ref": f"entity://observed-{i}", "destination_ref": "region://tray"},
              "dependencies": [f"chosen-{i-1}"] if i else []} for i in range(count)]
    nodes.append({"node_id": "final-observation", "obligation_id": "verify-goal", "capability": "task.verify",
                  "dependencies": [node["node_id"] for node in nodes]})
    return nodes


@pytest.mark.parametrize("count", [1, 2, 3])
def test_model_tool_call_materializes_variable_objects_in_same_task(tmp_path, count):
    async def exercise():
        c, task = setup_task(tmp_path, goal=f"Move {count} observed objects into the tray")
        request = {"task_id": task.task_id, "nodes": semantic_nodes(count), "reason": "selected from current observation"}
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[ToolCallRequest("plan-call", "forge_task_materialize_plan", request)]),
            LLMResponse(content="Plan submitted"),
        ])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path,
                         forge_task_coordinator=c, max_iterations=3)
        await loop._run_agent_loop([{"role": "user", "content": task.task_description}])
        result = c.get_task(task.task_id)
        assert len(result.revisions) == 2
        assert result.revisions[0].revision_id == task.active_revision_id
        assert len(result.active_revision.plan_graph.nodes) == count + 1
        assert result.active_revision.plan_graph.nodes[0].input_bindings["entity_ref"] == "entity://observed-0"
        assert result.execution_records == []
        assert loop.experience is None
    asyncio.run(exercise())


def test_semantic_submission_rejects_cycle_undeclared_capability_and_ambiguous_input(tmp_path):
    c, task = setup_task(tmp_path)
    nodes = semantic_nodes(2)
    nodes[0]["dependencies"] = ["chosen-1"]
    with pytest.raises(ValueError, match="cycle"):
        compile_task_plan(task, nodes, reason="bad graph")
    nodes = semantic_nodes(1)
    nodes[0]["capability"] = "undeclared.execute"
    with pytest.raises(ValueError, match="outside"):
        compile_task_plan(task, nodes, reason="bad capability")
    with pytest.raises(ValueError, match="either"):
        asyncio.run(ForgeTaskMaterializePlanTool(c).execute(task.task_id, nodes=[], plan_graph={}))
    assert len(c.get_task(task.task_id).revisions) == 1


def test_activation_retains_instructions_when_source_changes(tmp_path):
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    source = skill_dir / "SKILL.md"
    source.write_text("---\nname: test-skill\ndescription: test\n---\nObserve before advancing.\n")
    manager = SkillActivationManager(workspace=tmp_path, store=ExperienceStore(tmp_path))
    manager.begin_turn("session", "move object")
    first, content, _ = manager.activate(session_key="session", name="test-skill", role="primary")
    source.write_text("---\nname: test-skill\ndescription: test\n---\nNew instructions.\n")
    again, repeated, _ = manager.activate(session_key="session", name="test-skill", role="primary")
    assert again.activation_id == first.activation_id
    assert repeated == content
    assert manager.instructions_for_activation(session_key="session", activation_id=first.activation_id) == content
    manager.begin_turn("next", "next task")
    _, later, _ = manager.activate(session_key="next", name="test-skill", role="primary")
    assert "New instructions" in later


def test_node_turn_receives_original_goal_and_persisted_skill(tmp_path):
    async def exercise():
        c = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
        task = c.create_task(task_description="Move only the left red object", verification=TaskVerificationContract(mode="off"))
        # Create an isolated persisted task fixture with its activated instructions.
        task = task.model_copy(update={"task_id": "task-with-instructions", "primary_skill_instructions": "Observe after grasp."})
        c.store.update("%s" % c.store.active().task_id, lambda item: setattr(item, "status", AgentTaskStatus.FAILED), event_type="fixture_end")
        c.store.create(task)
        provider = ScriptedProvider([LLMResponse(content="Need observation")])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path, forge_task_coordinator=c)
        await loop.run_node_turn(task_id=task.task_id, revision_id=task.active_revision_id, node_id="selected", prompt="node evidence")
        sent = json.dumps(provider.requests[0]["messages"])
        assert "Move only the left red object" in sent
        assert "Observe after grasp." in sent
        assert "node evidence" in sent
        reloaded = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object()).get_task(task.task_id)
        assert reloaded.primary_skill_instructions == "Observe after grasp."
        with pytest.raises(AgentTaskError, match="immutable"):
            c.store.update(task.task_id, lambda item: setattr(item, "primary_skill_instructions", "changed"), event_type="bad_update")
    asyncio.run(exercise())


@pytest.mark.parametrize("status,expected", [("unavailable", "failed"), ("empty", "failed"), ("stale", "failed"), ("unknown", "unknown"), ("available", "succeeded")])
def test_query_availability_is_not_transport_success(status, expected):
    record = SimpleNamespace(semantics="query", status="succeeded", response={"status": status})
    assert _planning_record_status(record) == expected


@pytest.mark.parametrize("decision", ["stop", "replay", "replan", "illegal"])
def test_model_recovery_is_read_only_and_invalid_output_stops(tmp_path, decision):
    async def exercise():
        c, task = setup_task(tmp_path)
        graph = compile_task_plan(task, semantic_nodes(2), reason="test plan")
        settlement = NodeSettlement(task_id=task.task_id, revision_id=graph.revision_id,
                                    node_id="chosen-0", status="failed", failure_code="grasp_empty")
        delta = build_replan_delta(graph, settlement)
        provider = ScriptedProvider([LLMResponse(content=None, tool_calls=[ToolCallRequest(
            "decision", "submit_recovery", {"decision": decision, "reason": "observed failure"},
        )])])
        chooser = AgentRecoveryDecisions(provider, "fixture-model", c)
        result = await chooser.select_recovery(graph=graph, settlement=settlement, delta=delta, context=settlement)
        assert result == (decision if decision != "illegal" else "stop")
        assert len(c.get_task(task.task_id).revisions) == 1
        assert c.get_task(task.task_id).execution_records == []
        assert "NEVER repeats" in provider.requests[0]["messages"][0]["content"]
    asyncio.run(exercise())


def test_model_replan_preserves_task_identity_without_executing(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path)
        graph = compile_task_plan(task, semantic_nodes(2), reason="first")
        settlement = NodeSettlement(task_id=task.task_id, revision_id=graph.revision_id, node_id="chosen-0", status="failed")
        provider = ScriptedProvider([LLMResponse(content=None, tool_calls=[ToolCallRequest(
            "proposal", "submit_recovery", {"nodes": semantic_nodes(2), "reason": "retry with observation"},
        )])])
        proposal = await AgentRecoveryDecisions(provider, "fixture-model", c).propose_replan(
            graph=graph, settlement=settlement, delta=build_replan_delta(graph, settlement), context=settlement,
        )
        assert proposal.plan_graph.task_id == task.task_id
        assert proposal.plan_graph.revision_id != graph.revision_id
        assert proposal.delta.retry_parent_node_id == "chosen-0"
        assert len(c.get_task(task.task_id).revisions) == 1
    asyncio.run(exercise())
