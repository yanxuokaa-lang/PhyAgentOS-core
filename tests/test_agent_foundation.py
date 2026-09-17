from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from PhyAgentOS.agent.experience.activation import SkillActivationManager
from PhyAgentOS.agent.experience.store import ExperienceStore
from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.agent.plan_proposal import compile_task_plan
from PhyAgentOS.agent.planning_loop import _planning_record_status
from PhyAgentOS.agent.recovery_decisions import AgentRecoveryDecisions
from PhyAgentOS.agent.tools.forge_task import (
    ForgeTaskClarificationTool,
    ForgeTaskGetTool,
    ForgeTaskMaterializePlanTool,
)
from PhyAgentOS.agent.tools.forge_tool_api import ForgeToolQueryTool
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


def test_semantic_submission_rejects_root_produced_evidence_before_tool_result(tmp_path):
    c, task = setup_task(tmp_path)
    nodes = semantic_nodes(1)
    nodes[0]["capability"] = "scene.observe"
    nodes[0]["produced_evidence"] = ["observation_ref", "scene_revision"]
    with pytest.raises(ValueError, match="root discovery nodes cannot declare produced_evidence"):
        compile_task_plan(task, nodes, reason="reject unresolved discovery outputs")
    assert len(c.get_task(task.task_id).revisions) == 1


def test_materialized_unstarted_graph_can_be_corrected_append_only(tmp_path):
    c, task = setup_task(tmp_path)
    first = semantic_nodes(1)
    first[0]["conditions"] = ["unproduced_fact"]
    with pytest.raises(ValueError, match="condition facts"):
        asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
            task.task_id, nodes=first, reason="invalid root condition"
        ))

    # A graph with no executed Tool or settlement may be corrected without
    # overwriting the old revision; once execution facts exist, normal replan
    # rules remain the only replacement path.
    first[0].pop("conditions")
    first_result = json.loads(asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
        task.task_id, nodes=first, reason="initial graph"
    )))
    assert first_result["ok"] is True
    old_revision = c.get_task(task.task_id).active_revision_id
    corrected = semantic_nodes(2)
    corrected_result = json.loads(asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
        task.task_id, nodes=corrected, reason="correct unstarted graph"
    )))
    assert corrected_result["ok"] is True
    result = c.get_task(task.task_id)
    assert len(result.revisions) == 3
    assert result.revisions[1].revision_id == old_revision
    assert result.active_revision_id != old_revision
    assert result.active_revision.plan_graph is not None
    assert len(result.active_revision.plan_graph.nodes) == 3


def test_semantic_materialization_rejects_fabricated_evidence_refs(tmp_path):
    c, task = setup_task(tmp_path)
    nodes = semantic_nodes(1)
    nodes[0]["required_evidence"] = ["observation://fabricated"]
    with pytest.raises(ValueError, match="unknown or fabricated refs"):
        asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
            task.task_id,
            nodes=nodes,
            evidence_refs=["observation://fabricated"],
            reason="must reject caller-supplied evidence",
        ))
    assert len(c.get_task(task.task_id).revisions) == 1


def test_complete_plan_materialization_rejects_fabricated_evidence_refs(tmp_path):
    c, task = setup_task(tmp_path)
    graph = compile_task_plan(task, semantic_nodes(1), reason="complete graph")
    with pytest.raises(ValueError, match="unknown or fabricated refs"):
        asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
            task.task_id,
            plan_graph=graph.model_dump(mode="json"),
            plan_graph_ref="artifact://plans/fabricated",
            evidence_refs=["artifact://fabricated"],
            reason="must reject fabricated graph evidence",
        ))
    assert len(c.get_task(task.task_id).revisions) == 1


def test_semantic_materialization_accepts_exact_persisted_evidence_ref(tmp_path):
    c, task = setup_task(tmp_path)
    record_id, _ = c._append_execution(
        task.task_id,
        "scene.observe",
        "query",
        {},
        tool=task.primary_skill_binding.required_tools[0],
    )
    c._finish_execution(
        task.task_id,
        record_id,
        status="succeeded",
        response={"status": "available", "scene_revision": "scene-1",
                  "evidence_refs": ["artifact://observation/1"]},
    )
    nodes = semantic_nodes(1)
    nodes[0]["required_evidence"] = ["artifact://observation/1"]
    result = json.loads(asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
        task.task_id,
        nodes=nodes,
        reason="use exact Coordinator evidence",
    )))
    assert result["ok"] is True
    assert "artifact://observation/1" in c.get_task(task.task_id).active_revision.discovery_evidence_refs


def test_materialization_rejects_graph_of_completed_query_only(tmp_path):
    c, task = setup_task(tmp_path)
    required_policy = ToolSpecPolicy(
        tool_id="scene.observe", semantics="query", spec_digest="e" * 64,
        requires_before_plan=True, capabilities=("scene.observe", "object.relocate"),
    )
    understand_policy = ToolSpecPolicy(
        tool_id="scene.understand", semantics="query", spec_digest="f" * 64,
        requires_before_plan=True,
    )
    task = c.store.update(
        task.task_id,
        lambda item: setattr(
            item,
            "primary_skill_binding",
            item.primary_skill_binding.model_copy(update={
                "required_tools": (
                    item.primary_skill_binding.required_tools[0].model_copy(
                        update={"planning_policy": required_policy}
                    ),
                    BoundToolSpec(
                        tool_id="scene.understand", semantics="query", spec_sha256="a" * 64,
                        ready_at_binding=True, planning_policy=understand_policy,
                    ),
                ),
            }),
        ),
        event_type="test_preplan_policy",
    )
    direct_result = json.loads(asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
        task.task_id,
        plan_graph={},
        plan_graph_ref="artifact://plans/not-ready",
        reason="direct graph must not bypass discovery admission",
    )))
    assert direct_result["ok"] is False
    assert direct_result["error"]["code"] == "discovery_required"
    assert len(c.get_task(task.task_id).revisions) == 1
    record_id, _ = c._append_execution(
        task.task_id, "scene.observe", "query", {},
        tool=task.primary_skill_binding.required_tools[0],
    )
    c._finish_execution(
        task.task_id, record_id, status="succeeded",
        response={"status": "available", "scene_revision": "scene-1",
                  "evidence_refs": ["artifact://observation/1"]},
    )
    result = json.loads(asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
        task.task_id,
        nodes=[{"node_id": "move", "obligation_id": "move", "capability": "object.relocate"}],
        reason="reject frozen discovery-only graph",
    )))
    assert result["ok"] is False
    assert result["error"]["code"] == "discovery_required"
    assert len(c.get_task(task.task_id).revisions) == 1


def test_materialized_graph_correction_is_rejected_after_execution_fact(tmp_path):
    c, task = setup_task(tmp_path)
    first = json.loads(asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
        task.task_id, nodes=semantic_nodes(1), reason="initial graph"
    )))
    assert first["ok"] is True
    c._append_execution(
        task.task_id,
        "scene.observe",
        "query",
        {},
        tool=task.primary_skill_binding.required_tools[0],
    )
    with pytest.raises(AgentTaskError, match="execution facts"):
        asyncio.run(ForgeTaskMaterializePlanTool(c).execute(
            task.task_id, nodes=semantic_nodes(2), reason="late correction"
        ))


def test_forge_task_tool_responses_json_encode_nested_task_records(tmp_path):
    """CLI-facing tools must return JSON after coordinator state is persisted."""

    async def exercise():
        c, task = setup_task(tmp_path)

        fetched = json.loads(await ForgeTaskGetTool(c).execute(task.task_id))
        assert fetched["ok"] is True
        assert fetched["data"]["task_id"] == task.task_id

        waiting = json.loads(
            await ForgeTaskClarificationTool(c).execute(
                task.task_id,
                question="Which direction should be used?",
                node_id="arrange",
            )
        )
        assert waiting["ok"] is True
        assert waiting["data"]["status"] == "waiting_for_user"
        assert waiting["data"]["clarification_question"] == "Which direction should be used?"

    asyncio.run(exercise())


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
        initial_use = c.record_skill_use(
            task.task_id,
            activation_id="activation-1",
            skill_name="pick-place-workflow",
            skill_version="2.2.0",
            content_sha256="b" * 64,
            instructions="HISTORICAL FULL INSTRUCTIONS",
            decision_ref="task:initial",
        )
        provider = ScriptedProvider([
            LLMResponse(content="Need observation"),
            LLMResponse(content="Still need observation"),
        ])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path, forge_task_coordinator=c)
        first = await loop.run_node_turn(task_id=task.task_id, revision_id=task.active_revision_id, node_id="selected", prompt="node evidence")
        second = await loop.run_node_turn(task_id=task.task_id, revision_id=task.active_revision_id, node_id="selected", prompt="node evidence")
        sent = json.dumps(provider.requests[0]["messages"])
        assert "Move only the left red object" in sent
        assert sent.count("Observe after grasp.") == 1
        assert "HISTORICAL FULL INSTRUCTIONS" not in sent
        assert "node evidence" in sent
        assert "agent_node_prompt_projection_v1" in sent
        assert first.model_failure_code is None
        assert second.model_failure_code is None
        reloaded = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object()).get_task(task.task_id)
        assert reloaded.primary_skill_instructions == "Observe after grasp."
        assert len(reloaded.skill_uses) == 2
        assert reloaded.skill_uses[0].use_id == initial_use.use_id
        assert reloaded.skill_uses[1].node_id == "selected"
        with pytest.raises(AgentTaskError, match="immutable"):
            c.store.update(task.task_id, lambda item: setattr(item, "primary_skill_instructions", "changed"), event_type="bad_update")
    asyncio.run(exercise())


def test_record_skill_use_is_idempotent_for_same_node_decision(tmp_path):
    c, task = setup_task(tmp_path)
    arguments = {
        "activation_id": "activation-1",
        "skill_name": "pick-place-workflow",
        "skill_version": "2.2.0",
        "content_sha256": "b" * 64,
        "instructions": "Observe, prepare, then execute through Forge.",
        "decision_ref": "node:revision-1:prepare",
        "node_id": "prepare",
    }

    first = c.record_skill_use(task.task_id, **arguments)
    repeated = c.record_skill_use(task.task_id, **arguments)
    distinct = c.record_skill_use(
        task.task_id,
        **{**arguments, "decision_ref": "node:revision-1:place", "node_id": "place"},
    )

    current = c.get_task(task.task_id)
    assert repeated.use_id == first.use_id
    assert distinct.use_id != first.use_id
    assert len(current.skill_uses) == 2
    assert current.active_revision.skill_use_ids == (first.use_id, distinct.use_id)


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


@pytest.mark.parametrize("status", ["available", "unavailable"])
def test_query_receipt_is_persisted_identity_not_gateway_verdict(tmp_path, status):
    async def exercise():
        c, task = setup_task(tmp_path)
        gateway = {"ok": True, "data": {"status": status, "scene_revision": "scene-1"}}
        c.client = SimpleNamespace(invoke_query_tool=AsyncMock(return_value=gateway))
        c._require_binding_tool = AsyncMock(return_value=task.primary_skill_binding.required_tools[0])
        output = json.loads(await ForgeToolQueryTool(c.client, c).execute(
            "scene.observe", {}, task_id=task.task_id,
        ))
        record = c.get_task(task.task_id).execution_records[0]
        assert output["paos_record"] == {
            "task_id": task.task_id, "revision_id": task.active_revision_id,
            "record_id": record.record_id, "evidence_refs": record.evidence_refs,
        }
        assert output["data"] == gateway["data"]
        assert record.response == gateway
        assert "paos_record" not in gateway
        assert _planning_record_status(record) == ("succeeded" if status == "available" else "failed")
        assert c.get_task(task.task_id).active_revision.plan_graph is None
    asyncio.run(exercise())


def test_discovery_receipt_can_materialize_without_task_get(tmp_path):
    class DiscoveryPlanner(ScriptedProvider):
        async def chat(self, **kwargs):
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                return LLMResponse(content=None, tool_calls=[ToolCallRequest(
                    "discover", "forge_tool_query", {"task_id": task.task_id,
                    "tool_id": "scene.observe", "arguments": {}},
                )])
            if len(self.requests) == 2:
                receipt = json.loads(kwargs["messages"][-1]["content"])["paos_record"]
                return LLMResponse(content=None, tool_calls=[ToolCallRequest(
                    "materialize", "forge_task_materialize_plan", {
                        "task_id": task.task_id, "nodes": semantic_nodes(2),
                        "evidence_refs": receipt["evidence_refs"],
                    },
                )])
            return LLMResponse(content="Plan submitted")

    async def exercise():
        provider = DiscoveryPlanner()
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path,
                         forge_task_coordinator=c, max_iterations=3)
        loop.tools.register(ForgeToolQueryTool(c.client, c))
        _, used, _ = await loop._run_agent_loop([{"role": "user", "content": task.task_description}])
        result = c.get_task(task.task_id)
        assert used == ["forge_tool_query", "forge_task_materialize_plan"]
        assert len(result.revisions) == 2
        assert len(result.active_revision.plan_graph.nodes) == 3
        assert result.active_revision.discovery_evidence_refs == tuple(result.execution_records[0].evidence_refs)
        assert len(result.execution_records) == 1

    c, task = setup_task(tmp_path)
    c.client = SimpleNamespace(invoke_query_tool=AsyncMock(return_value={
        "ok": True, "data": {"status": "available", "scene_revision": "scene-1"},
    }))
    c._require_binding_tool = AsyncMock(return_value=task.primary_skill_binding.required_tools[0])
    asyncio.run(exercise())


@pytest.mark.parametrize("interrupt_tool", [False, True])
@pytest.mark.parametrize("via_timeout", [False, True])
def test_interrupted_turn_retains_context_and_resumes_same_task(tmp_path, interrupt_tool, via_timeout):
    async def exercise():
        c, task = setup_task(tmp_path)
        entered = asyncio.Event()
        blocker = asyncio.Event()

        class InterruptedProvider(ScriptedProvider):
            async def chat(self, **kwargs):
                if not self.responses:
                    entered.set()
                    await blocker.wait()
                return await super().chat(**kwargs)

        calls = [ToolCallRequest("read", "forge_task_get", {"task_id": task.task_id})]
        if interrupt_tool:
            calls.extend([
                ToolCallRequest("pending", "forge_task_get", {"task_id": task.task_id}),
                ToolCallRequest("not-dispatched", "forge_task_get", {"task_id": task.task_id}),
            ])
        provider = InterruptedProvider([LLMResponse(content="Discovery done; prepare plan", tool_calls=calls)])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path,
                         forge_task_coordinator=c, max_iterations=3)
        loop._connect_mcp = AsyncMock()
        loop.memory_consolidator.maybe_consolidate_by_tokens = AsyncMock()
        execute = loop.tools.execute
        n = 0

        async def interrupt(name, args):
            nonlocal n
            n += 1
            if interrupt_tool and n == 2:
                entered.set()
                await blocker.wait()
            return await execute(name, args)

        loop.tools.execute = interrupt
        if via_timeout:
            loop.turn_timeout_s = 0.2
        turn = asyncio.create_task(loop.process_direct("Continue this task", session_key="cli:retained"))
        await asyncio.wait_for(entered.wait(), 3)
        if via_timeout:
            assert "Turn timed out" in await asyncio.wait_for(turn, 3)
        else:
            turn.cancel()
            with pytest.raises(asyncio.CancelledError):
                await turn
        loop.sessions.invalidate("cli:retained")
        saved = loop.sessions.get_or_create("cli:retained").get_history(max_messages=0)
        answers = [m for m in saved if m["role"] == "tool"]
        assert len(answers) == len(calls)
        assert json.loads(answers[0]["content"])["ok"] is True
        if interrupt_tool:
            assert all(json.loads(m["content"])["error"]["type"] == "local_turn_interrupted"
                       for m in answers[1:])
            assert n == 2  # The third call was never dispatched.
        assert c.get_task(task.task_id).status == AgentTaskStatus.EXECUTING
        assert c.get_task(task.task_id).active_revision.plan_graph is None

        provider.responses = [
            LLMResponse(content=None, tool_calls=[ToolCallRequest("plan", "forge_task_materialize_plan", {
                "task_id": task.task_id, "nodes": semantic_nodes(2),
            })]), LLMResponse(content="Plan submitted"),
        ]
        loop.turn_timeout_s = 3
        assert await loop.process_direct("Submit the plan", session_key="cli:retained") == "Plan submitted"
        system = provider.requests[-1]["messages"][0]["content"]
        assert "Current persisted AgentTask snapshot" in system
        assert task.task_id in system
        assert "does not authorize takeover" in system
        assert len(c.get_task(task.task_id).revisions) == 2
        assert c.get_task(task.task_id).execution_records == []
        history = loop.sessions.get_or_create("cli:retained").get_history(max_messages=0)
        assert sum(m["role"] == "tool" and m["tool_call_id"] == "read" for m in history) == 1
    asyncio.run(exercise())


def test_diagnostic_query_does_not_invent_task_receipt():
    async def exercise():
        result = {"ok": True, "data": {"status": "available"}}
        client = SimpleNamespace(invoke_query_tool=AsyncMock(return_value=result))
        assert json.loads(await ForgeToolQueryTool(client, None).execute("scene.observe", {})) == result
    asyncio.run(exercise())
