from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from PhyAgentOS.agent.experience.activation import SkillActivationManager
from PhyAgentOS.agent.experience.store import ExperienceStore
from PhyAgentOS.agent.loop import AgentLoop, AgentLoopRunResult
from PhyAgentOS.agent.plan_proposal import (
    _complete_persisted_runtime_bindings,
    _inject_task_verification_semantics,
    _validate_structured_node_intent,
    compile_task_plan,
)
from PhyAgentOS.agent.planning_loop import _planning_record_status
from PhyAgentOS.agent.prompt_context import (
    _compact_activation_results,
    compact_tool_result,
    visible_tool_names,
)
from PhyAgentOS.agent.recovery_decisions import (
    AgentRecoveryDecisions,
    _scene_refresh_bootstrap_capability,
    _scene_refresh_bootstrap_node_id,
)
from PhyAgentOS.agent.tools.forge_task import (
    ForgeTaskClarificationTool,
    ForgeTaskGetTool,
    ForgeTaskMaterializePlanTool,
    _prune_satisfied_discovery_prefix,
)
from PhyAgentOS.agent.tools.forge_tool_api import (
    ForgeToolActionResultTool,
    ForgeToolActionStatusTool,
    ForgeToolQueryTool,
    ForgeToolSessionResultTool,
    ForgeToolSessionStatusTool,
    _resolve_observation_bound_query_arguments,
    _scene_bind_argument_error,
)
from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec, ForgeSkillBinding
from PhyAgentOS.forge.task import (
    AgentTaskCoordinator,
    AgentTaskError,
    AgentTaskStatus,
    ToolExecutionRecord,
    utc_now,
)
from PhyAgentOS.planning import (
    NodeSettlement,
    PlanNode,
    ToolSpecPolicy,
    build_replan_delta,
    plan_node_digest,
)
from PhyAgentOS.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from PhyAgentOS.session.manager import Session
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


@pytest.mark.parametrize(
    ("projection_scope", "phase", "expected"),
    [
        ("task", "task_creation", True),
        ("task", "discovery", True),
        ("task", "planning_execution", True),
        ("node", "planning_execution", False),
        ("task", "verification", False),
    ],
)
def test_agent_loop_retries_provider_timeout_before_tool_dispatch(
    projection_scope, phase, expected
):
    assert AgentLoop._retry_provider_timeout(
        projection_scope=projection_scope,
        phase=phase,
    ) is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [(AgentTaskStatus.AWAITING_REPLAN, False), (AgentTaskStatus.EXECUTING, True)],
)
def test_model_failure_preserves_coordinator_replan_checkpoint(status, expected):
    task = SimpleNamespace(status=status)
    assert AgentLoop._should_fail_task_after_model_failure(task) is expected


def test_bound_discovery_can_recover_compacted_skill_and_contracts():
    names = (
        "read_file",
        "list_dir",
        "forge_task_get",
        "forge_tool_context",
        "forge_tool_query",
        "forge_task_materialize_plan",
    )
    unbound = set(visible_tool_names(names, None))
    assert "read_file" in unbound

    bound_task = SimpleNamespace(
        status="executing",
        terminal=False,
        cancellation_requested=False,
        pause_requested=False,
        primary_skill_binding=SimpleNamespace(required_tools=()),
        active_revision=SimpleNamespace(plan_graph=None, execution_records=()),
        execution_records=(),
    )
    visible = set(visible_tool_names(names, bound_task))
    assert "read_file" in visible
    assert "forge_tool_context" in visible
    assert "forge_task_materialize_plan" in visible
    assert "forge_tool_query" in visible


def test_replan_turn_claims_bounded_lease_before_model_request(tmp_path):
    async def exercise():
        coordinator, task = setup_task(tmp_path)
        coordinator.record_planning_node_blocked(
            task.task_id, task.active_revision_id, "prepare-red", "semantic repair required"
        )
        before = coordinator.get_task(task.task_id).replan_deadline
        loop = AgentLoop(
            bus=MessageBus(),
            provider=ScriptedProvider([LLMResponse(content="Replan inspected.")]),
            workspace=tmp_path,
            forge_task_coordinator=coordinator,
            max_iterations=1,
        )
        await loop._run_agent_loop(
            [{"role": "user", "content": "Continue the existing task."}],
            active_task_id=task.task_id,
        )
        current = coordinator.get_task(task.task_id)
        assert current.replan_extension_used is True
        assert current.replan_deadline is not None
        assert before is not None and current.replan_deadline > before
        assert sum(
            event["event_type"] == "plan_revision_attempt_lease_claimed"
            for event in coordinator.store.events(task.task_id)
        ) == 1

    asyncio.run(exercise())


def test_operator_retry_restores_only_expired_replan_same_task(tmp_path):
    coordinator, task = setup_task(tmp_path)
    coordinator.record_planning_node_blocked(
        task.task_id, task.active_revision_id, "prepare-red", "semantic repair required"
    )
    coordinator.store.update(
        task.task_id,
        lambda current: setattr(
            current, "replan_deadline", utc_now() - timedelta(seconds=1)
        ),
        event_type="test_expire_replan",
    )
    with pytest.raises(AgentTaskError, match="replan deadline expired"):
        coordinator.begin_revision(task.task_id, reason="expired recovery")
    failed = coordinator.get_task(task.task_id)
    revision_ids = tuple(item.revision_id for item in failed.revisions)
    restored = coordinator.retry_expired_replan(
        task.task_id, reason="operator continues the same acceptance task"
    )
    assert restored.task_id == task.task_id
    assert restored.status == AgentTaskStatus.AWAITING_REPLAN
    assert tuple(item.revision_id for item in restored.revisions) == revision_ids
    assert restored.replan_deadline is not None and restored.replan_deadline > utc_now()
    assert restored.replan_extension_used is False
    assert coordinator.store.events(task.task_id)[-1]["event_type"] == (
        "plan_revision_retry_authorized"
    )


def test_operator_retry_rejects_unrelated_failed_task(tmp_path):
    coordinator, task = setup_task(tmp_path)
    coordinator.store.update(
        task.task_id,
        lambda current: (
            setattr(current, "status", AgentTaskStatus.FAILED),
            current.evidence_errors.append("unrelated failure"),
        ),
        event_type="test_unrelated_failure",
    )
    with pytest.raises(AgentTaskError, match="did not fail"):
        coordinator.retry_expired_replan(task.task_id, reason="not permitted")


def test_agent_loop_retries_empty_stop_before_task_creation_dispatch(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(content=None, finish_reason="stop"),
            LLMResponse(content="Recovered control-plane turn."),
        ])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path, max_iterations=1,
        )
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Create the RGB pick-place task."}],
        )

        assert len(provider.requests) == 2
        assert provider.requests[0] == provider.requests[1]
        assert result.content == "Recovered control-plane turn."
        assert result.model_failure_code is None

    asyncio.run(exercise())


def test_agent_loop_does_not_retry_nonempty_stop_response(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(content="No action is required.", finish_reason="stop"),
        ])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path, max_iterations=1,
        )
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Create the RGB pick-place task."}],
        )

        assert len(provider.requests) == 1
        assert result.content == "No action is required."

    asyncio.run(exercise())


def test_save_turn_persists_parseable_forge_task_projection() -> None:
    loop = object.__new__(AgentLoop)
    session = Session(key="cli:rgb")
    raw = json.dumps({
        "ok": True,
        "data": {
            "task_id": "task-rgb",
            "status": "executing",
            "revision_id": "revision-rgb",
            "plan_graph_ref": "artifact://plan/rgb",
            "required_tools": [{"input_schema": {"large": "x" * 20_000}}],
        },
    })
    loop._save_turn(session, [{"role": "tool", "name": "forge_task_get", "content": raw}], 0)

    persisted = session.messages[0]["content"]
    payload = json.loads(persisted)
    assert payload["ok"] is True
    assert payload["data"]["task_id"] == "task-rgb"
    assert payload["data"]["revision_id"] == "revision-rgb"
    assert payload["data"]["plan_graph_ref"] == "artifact://plan/rgb"
    assert "required_tools" not in persisted
    assert compact_tool_result("forge_task_get", persisted) != raw


def test_save_turn_keeps_activation_parseable_for_task_creation_and_recovery() -> None:
    loop = object.__new__(AgentLoop)
    session = Session(key="cli:rgb")
    activation = json.dumps({
        "ok": True,
        "activation": {"activation_id": "activation-rgb", "skill_name": "pick-place-workflow"},
        "skill": "workflow instructions " * 2_000,
        "applicable_lessons": [{"lesson_id": "lesson-rgb"}],
    })
    task = json.dumps({"ok": True, "data": {"task_id": "task-rgb"}})

    loop._save_turn(session, [
        {"role": "tool", "name": "activate_skill", "content": activation},
        {"role": "tool", "name": "forge_task_create", "content": task},
    ], 0)

    history = session.get_history()
    assert json.loads(history[0]["content"])["skill"].startswith("workflow instructions")
    assert json.loads(history[1]["content"])["data"]["task_id"] == "task-rgb"
    compacted = _compact_activation_results(history, enabled=True)
    result = json.loads(compacted[0]["content"])
    assert result["activation"]["activation_id"] == "activation-rgb"
    assert result["applicable_lessons"] == [{"lesson_id": "lesson-rgb"}]
    assert result["skill"]["status"] == "persisted_in_coordinator_skill_use"
    assert "workflow instructions" not in compacted[0]["content"]

    activation_only = Session(key="cli:activation-only")
    loop._save_turn(activation_only, [
        {"role": "tool", "name": "activate_skill", "content": activation},
    ], 0)
    history_without_task = activation_only.get_history()
    assert _compact_activation_results(history_without_task, enabled=False) == history_without_task
    assert json.loads(history_without_task[0]["content"])["skill"].startswith("workflow instructions")


def setup_task(tmp_path, goal="Move the left red object into the tray", *, origin_session_key=None):
    c = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    task = c.create_task(task_description=goal, verification=TaskVerificationContract(mode="off"),
                         origin_session_key=origin_session_key)
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


def test_structured_node_intent_excludes_flat_task_verification_semantics():
    local_intent = {
        "goal": "Prepare the selected acquire route",
        "success_criteria": ["The selected candidate is qualified prepared."],
        "allowed_arms": ["right_arm"],
        "coordination_mode": "single_arm",
    }
    bindings = {"intent": local_intent}

    _inject_task_verification_semantics(
        bindings,
        verification_goal="Verify the complete task",
        verification_criteria=["All final outputs pass verification."],
    )

    assert bindings == {"intent": local_intent}


def test_legacy_node_receives_flat_task_verification_semantics():
    bindings = {}

    _inject_task_verification_semantics(
        bindings,
        verification_goal="Verify the complete task",
        verification_criteria=["All final outputs pass verification."],
    )

    assert bindings == {
        "goal": "Verify the complete task",
        "success_criteria": ["All final outputs pass verification."],
    }


def test_structured_manipulation_intent_rejects_unknown_fields_before_revision():
    class Policy:
        trusted_argument_builder = "manipulation_intent_v2"

    node = PlanNode(
        node_id="prepare-red",
        obligation_id="prepare-red",
        capability="manipulation.prepare",
        input_bindings={"intent": {
            "goal": "prepare the observed red block",
            "success_criteria": ["one candidate is prepared"],
            "allowed_arms": ["left"],
            "coordination_mode": "single_arm",
            "operation": "prepare",
        }},
    )

    with pytest.raises(ValueError, match=r"prepare-red.*unsupported fields: operation"):
        _validate_structured_node_intent(node, (Policy(),))


def test_structured_manipulation_intent_accepts_shared_semantic_fields():
    class Policy:
        trusted_argument_builder = "manipulation_intent_v2"

    node = PlanNode(
        node_id="prepare-red",
        obligation_id="prepare-red",
        capability="manipulation.prepare",
        input_bindings={"intent": {
            "goal": "prepare the observed red block",
            "success_criteria": ["one candidate is prepared"],
            "allowed_arms": ["left"],
            "coordination_mode": "single_arm",
            "constraints": ["preserve current scene evidence"],
        }},
    )

    _validate_structured_node_intent(node, (Policy(),))


def test_materialize_prunes_only_settled_discovery_prefix_and_rewires_dependencies():
    query_tools = []
    for tool_id in (
        "scene.observe", "scene.understand", "manipulation.capabilities", "scene.bind"
    ):
        policy = ToolSpecPolicy(
            tool_id=tool_id, semantics="query", spec_digest="a" * 64,
            capabilities=(tool_id,), requires_before_plan=True,
        )
        query_tools.append(BoundToolSpec(
            tool_id=tool_id, semantics="query", spec_sha256="a" * 64,
            ready_at_binding=True, planning_policy=policy,
        ))
    query_tools.append(BoundToolSpec(
        tool_id="grasp.propose", semantics="query", spec_sha256="a" * 64,
        ready_at_binding=True, planning_policy=ToolSpecPolicy(
            tool_id="grasp.propose", semantics="query", spec_digest="a" * 64,
            capabilities=("grasp.propose",),
        ),
    ))
    evidence = {
        "scene.observe": "tool:observe", "scene.understand": "tool:understand",
        "manipulation.capabilities": "tool:capabilities", "scene.bind": "tool:bind",
    }
    records = [SimpleNamespace(
        tool_id=tool_id, semantics="query", status="succeeded",
        arguments=(
            {"sensor_refs": ["camera/head", "camera/front"], "max_age_ms": 1000}
            if tool_id == "scene.observe"
            else {"entity_refs": ["entity://e1", "entity://e2", "entity://e3"]}
            if tool_id == "scene.bind" else {}
        ), response={"data": {"status": "available"}},
        evidence_refs=[evidence[tool_id]],
    ) for tool_id in evidence]
    task = SimpleNamespace(
        active_revision=SimpleNamespace(plan_graph=None, execution_records=records),
        primary_skill_binding=SimpleNamespace(required_tools=tuple(query_tools)),
    )
    nodes = [
        {"node_id": "observe", "obligation_id": "observe", "capability": "scene.observe",
         "input_bindings": {"sensor_refs": ["camera/head", "camera/front"], "max_age_ms": 1000}},
        {"node_id": "understand", "obligation_id": "understand", "capability": "scene.understand",
         "dependencies": ["observe"], "required_evidence": ["tool:observe"]},
        {"node_id": "capabilities", "obligation_id": "capabilities", "capability": "manipulation.capabilities",
         "dependencies": ["understand"], "required_evidence": ["tool:understand"]},
        {"node_id": "bind", "obligation_id": "bind", "capability": "scene.bind",
         "dependencies": ["capabilities"], "required_evidence": ["tool:capabilities"],
         "input_bindings": {"entity_refs": ["entity://e1", "entity://e2", "entity://e3"]}},
        {"node_id": "grasp", "obligation_id": "grasp", "capability": "grasp.propose",
         "dependencies": ["bind"], "required_evidence": ["tool:bind"]},
    ]
    retained, pruned = _prune_satisfied_discovery_prefix(task, nodes)
    assert pruned == ("observe", "understand", "capabilities", "bind")
    assert [node["node_id"] for node in retained] == ["grasp"]
    assert retained[0]["dependencies"] == []


def test_materialize_does_not_prune_mismatched_observation_inputs():
    policy = ToolSpecPolicy(
        tool_id="scene.observe", semantics="query", spec_digest="a" * 64,
        capabilities=("scene.observe",), requires_before_plan=True,
    )
    task = SimpleNamespace(
        active_revision=SimpleNamespace(plan_graph=None, execution_records=[SimpleNamespace(
            tool_id="scene.observe", semantics="query", status="succeeded",
            arguments={"sensor_refs": ["camera/head"], "max_age_ms": 1000},
            response={"data": {"status": "available"}}, evidence_refs=["tool:observe"],
        )]),
        primary_skill_binding=SimpleNamespace(required_tools=(BoundToolSpec(
            tool_id="scene.observe", semantics="query", spec_sha256="a" * 64,
            ready_at_binding=True, planning_policy=policy,
        ),)),
    )
    nodes = [{
        "node_id": "observe", "obligation_id": "observe", "capability": "scene.observe",
        "input_bindings": {"sensor_refs": ["camera/head", "camera/front"], "max_age_ms": 1000},
    }]
    retained, pruned = _prune_satisfied_discovery_prefix(task, nodes)
    assert pruned == ()
    assert retained == nodes


def test_materialize_reports_pruned_prefix_and_submits_suffix(monkeypatch):
    observe_policy = ToolSpecPolicy(
        tool_id="scene.observe", semantics="query", spec_digest="a" * 64,
        capabilities=("scene.observe",), requires_before_plan=True,
    )
    grasp_policy = ToolSpecPolicy(
        tool_id="grasp.propose", semantics="query", spec_digest="b" * 64,
        capabilities=("grasp.propose",),
    )
    observe = SimpleNamespace(
        tool_id="scene.observe", semantics="query", ownership="task", status="succeeded",
        arguments={"sensor_refs": ["camera/head"], "max_age_ms": 1000},
        response={"data": {"status": "available", "scene_revision": "scene-1"}},
        evidence_refs=["tool:observe"],
    )
    active_revision = SimpleNamespace(plan_graph=None, execution_records=[observe])
    task = SimpleNamespace(
        task_id="task-prefix",
        active_revision=active_revision,
        revisions=(active_revision,),
        runtime_binding=None,
        primary_skill_binding=SimpleNamespace(
            skill_document_sha256="c" * 64,
            required_tools=(
                BoundToolSpec(tool_id="scene.observe", semantics="query", spec_sha256="a" * 64,
                              ready_at_binding=True, planning_policy=observe_policy),
                BoundToolSpec(tool_id="grasp.propose", semantics="query", spec_sha256="b" * 64,
                              ready_at_binding=True, planning_policy=grasp_policy),
            ),
        ),
    )
    coordinator = Mock()
    coordinator.get_task.return_value = task
    coordinator.materialize_plan_revision.return_value = {"revision_id": "revision-suffix"}
    monkeypatch.setattr(
        "PhyAgentOS.agent.planning_context.context_from_task",
        lambda *_args, **_kwargs: SimpleNamespace(
            evidence_refs=frozenset({"tool:observe"}), condition_facts={},
        ),
    )
    nodes = [
        {"node_id": "observe", "obligation_id": "observe", "capability": "scene.observe",
         "input_bindings": {"sensor_refs": ["camera/head"], "max_age_ms": 1000}},
        {"node_id": "grasp", "obligation_id": "grasp", "capability": "grasp.propose",
         "dependencies": ["observe"], "required_evidence": ["tool:observe"]},
    ]
    result = json.loads(asyncio.run(ForgeTaskMaterializePlanTool(coordinator).execute(
        task.task_id, nodes=nodes, reason="continue after discovery",
    )))
    assert result["diagnostics"] == {"pruned_discovery_node_ids": ["observe"]}
    submitted = coordinator.materialize_plan_revision.call_args.kwargs["plan_graph"]
    assert [node.node_id for node in submitted.nodes] == ["grasp"]
    assert submitted.nodes[0].dependencies == ()


def test_prepare_bindings_reuse_unique_current_capability_and_destination_facts():
    active_revision = SimpleNamespace(execution_records=[SimpleNamespace(
        tool_id="manipulation.capabilities",
        status="succeeded",
        response={"data": {"snapshot_ref": "artifact://capabilities/current"}},
    )])
    task = SimpleNamespace(revisions=[active_revision], active_revision=active_revision)
    nodes = (
        PlanNode(
            node_id="red_prepare",
            obligation_id="red-prepare",
            capability="manipulation.prepare",
            input_bindings={"entity_ref": "entity://red"},
        ),
        PlanNode(
            node_id="red_place",
            obligation_id="red-place",
            capability="object.place",
            input_bindings={
                "entity_ref": "entity://red",
                "destination_ref": "destination://left",
            },
        ),
    )

    completed = _complete_persisted_runtime_bindings(task, nodes)
    assert completed[0].input_bindings == {
        "entity_ref": "entity://red",
        "destination_ref": "destination://left",
        "capability_snapshot_ref": "artifact://capabilities/current",
    }


def test_prepare_bindings_map_observed_identity_to_benchmark_destination():
    discovery = SimpleNamespace(execution_records=[
        SimpleNamespace(
            tool_id="task.goal",
            status="succeeded",
            response={
                "status": "available",
                "goal_source": "benchmark_task_definition",
                "goals": [{
                    "execution_entity_ref": "entity://block-green-1",
                    "destination_ref": "destination://benchmark/green",
                }],
            },
        ),
        SimpleNamespace(
            tool_id="scene.bind",
            node_id="bind-scene",
            status="succeeded",
            response={
                "status": "available",
                "entities": [{
                    "entity_ref": "entity://observed-green",
                    "execution_entity_ref": "entity://block-green-1",
                }],
            },
        ),
        SimpleNamespace(
            tool_id="manipulation.capabilities",
            status="succeeded",
            response={
                "status": "available",
                "snapshot_ref": "artifact://capabilities/scene-1",
            },
        ),
    ])
    task = SimpleNamespace(revisions=[discovery], active_revision=discovery)
    nodes = (
        PlanNode(
            node_id="green-grasp",
            obligation_id="green-grasp",
            capability="grasp.propose",
            input_bindings={"entity_ref": "entity://observed-green"},
        ),
        PlanNode(
            node_id="green-prepare",
            obligation_id="green-prepare",
            capability="manipulation.prepare",
            dependencies=("green-grasp",),
        ),
    )

    completed = _complete_persisted_runtime_bindings(task, nodes)

    assert completed[1].input_bindings == {
        "entity_ref": "entity://observed-green",
        "destination_ref": "destination://benchmark/green",
        "capability_snapshot_ref": "artifact://capabilities/scene-1",
    }


def test_task_goal_identity_injects_destination_without_optional_goal_source():
    discovery = SimpleNamespace(execution_records=[
        SimpleNamespace(
            tool_id="task.goal",
            status="succeeded",
            response={
                "status": "available",
                "goals": [{
                    "execution_entity_ref": "entity://runtime-object",
                    "destination_ref": "destination://external/slot",
                }],
            },
        ),
        SimpleNamespace(
            tool_id="scene.bind",
            node_id="bind-scene",
            status="succeeded",
            response={
                "status": "available",
                "entities": [{
                    "entity_ref": "entity://observed-object",
                    "execution_entity_ref": "entity://runtime-object",
                }],
            },
        ),
    ])
    task = SimpleNamespace(revisions=[discovery], active_revision=discovery)
    nodes = (PlanNode(
        node_id="prepare-object",
        obligation_id="prepare-object",
        capability="manipulation.prepare",
        input_bindings={"entity_ref": "entity://observed-object"},
    ),)

    completed = _complete_persisted_runtime_bindings(task, nodes)

    assert completed[0].input_bindings["destination_ref"] == (
        "destination://external/slot"
    )


def test_benchmark_destination_overrides_agent_authored_target():
    discovery = SimpleNamespace(execution_records=[
        SimpleNamespace(
            tool_id="task.goal", status="succeeded",
            response={
                "status": "available",
                "goal_source": "benchmark_task_definition",
                "goals": [{
                    "execution_entity_ref": "entity://block-green-1",
                    "destination_ref": "destination://benchmark/green",
                }],
            },
        ),
        SimpleNamespace(
            tool_id="scene.bind", node_id="bind-scene", status="succeeded",
            response={
                "status": "available",
                "binding_ref": "artifact://binding/current",
                "entities": [{
                    "entity_ref": "entity://observed-green",
                    "execution_entity_ref": "entity://block-green-1",
                }],
            },
        ),
    ])
    task = SimpleNamespace(revisions=[discovery], active_revision=discovery)
    nodes = (PlanNode(
        node_id="green-prepare", obligation_id="green-prepare",
        capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://observed-green",
            "destination_ref": "destination://agent-authored/staging",
        },
    ),)

    completed = _complete_persisted_runtime_bindings(task, nodes)

    assert completed[0].input_bindings["destination_ref"] == (
        "destination://benchmark/green"
    )


def test_ambiguous_benchmark_destinations_remove_agent_authored_target():
    discovery = SimpleNamespace(execution_records=[SimpleNamespace(
        tool_id="task.goal", status="succeeded",
        response={
            "status": "available",
            "goal_source": "benchmark_task_definition",
            "goals": [
                {
                    "execution_entity_ref": "entity://block-green-1",
                    "destination_ref": "destination://benchmark/green-a",
                },
                {
                    "execution_entity_ref": "entity://block-green-1",
                    "destination_ref": "destination://benchmark/green-b",
                },
            ],
        },
    )])
    task = SimpleNamespace(revisions=[discovery], active_revision=discovery)
    nodes = (PlanNode(
        node_id="green-prepare", obligation_id="green-prepare",
        capability="manipulation.prepare",
        input_bindings={
            "execution_entity_ref": "entity://block-green-1",
            "destination_ref": "destination://agent-authored/staging",
        },
    ),)

    completed = _complete_persisted_runtime_bindings(task, nodes)

    assert "destination_ref" not in completed[0].input_bindings


def test_prepare_bindings_do_not_reuse_scene_facts_from_closed_revision():
    closed = SimpleNamespace(execution_records=[
        SimpleNamespace(
            tool_id="manipulation.capabilities",
            status="succeeded",
            response={"snapshot_ref": "artifact://capabilities/stale"},
        ),
        SimpleNamespace(
            tool_id="grasp.propose",
            node_id="green-grasp",
            status="succeeded",
            response={"candidates": [{"entity_ref": "entity://stale-green"}]},
        ),
    ])
    active = SimpleNamespace(execution_records=[])
    task = SimpleNamespace(revisions=[closed, active], active_revision=active)
    node = PlanNode(
        node_id="green-prepare",
        obligation_id="green-prepare",
        capability="manipulation.prepare",
        dependencies=("green-grasp",),
    )

    completed = _complete_persisted_runtime_bindings(task, (node,))

    assert completed[0].input_bindings == {}


def test_pick_place_creation_projection_restores_after_task_creation(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "activate", "activate_skill", {"name": "pick-place-workflow", "role": "primary"},
            )]),
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "create", "forge_task_create", {
                    "task_description": "Arrange the observed RGB blocks",
                    "verification": {"mode": "off"},
                },
            )]),
            LLMResponse(content="Task creation completed."),
        ])
        coordinator = AgentTaskCoordinator(
            workspace=tmp_path, config=ForgeConfig(), client=object()
        )
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path,
            forge_task_coordinator=coordinator, max_iterations=4,
        )

        async def execute(name, arguments):
            if name == "activate_skill":
                return json.dumps({
                    "ok": True,
                    "activation": {
                        "skill_name": "pick-place-workflow",
                        "activation_id": "activation_test",
                    },
                })
            if name == "forge_task_create":
                task = coordinator.create_task(
                    task_description="Arrange the observed RGB blocks",
                    verification=TaskVerificationContract(mode="off"),
                    origin_session_key="cli:test",
                )
                return json.dumps({"ok": True, "data": {"task_id": task.task_id}})
            raise AssertionError(f"unexpected tool execution: {name}")

        loop.tools.execute = AsyncMock(side_effect=execute)
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Create the RGB pick-place task."}],
            experience_session_key="cli:test",
        )

        assert result.content == "Task creation completed."
        assert [call.args[0] for call in loop.tools.execute.await_args_list] == [
            "activate_skill", "forge_task_create",
        ]
        first_names = {tool["function"]["name"] for tool in provider.requests[0]["tools"]}
        creation_names = {tool["function"]["name"] for tool in provider.requests[1]["tools"]}
        restored_names = {tool["function"]["name"] for tool in provider.requests[2]["tools"]}
        assert "exec" in first_names
        assert creation_names <= {
            "activate_skill", "forge_task_create", "forge_tool_context", "forge_tool_query",
        }
        assert "exec" in restored_names

    asyncio.run(exercise())


@pytest.mark.parametrize("phase", ["task_creation", "discovery"])
@pytest.mark.parametrize("recover", [False, True])
def test_task_preplanning_model_timeout_retries_same_request_once(tmp_path, phase, recover):
    async def exercise():
        timeout = LLMResponse(content="LLM request timed out after 50 seconds", finish_reason="error")
        provider = ScriptedProvider([
            timeout,
            LLMResponse(content="Continue planning") if recover else timeout,
        ])
        coordinator = setup_task(tmp_path)[0] if phase == "discovery" else None
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path,
            forge_task_coordinator=coordinator, max_iterations=1,
        )
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Arrange RGB blocks"}],
            active_task_id=coordinator.store.active().task_id if coordinator else None,
        )

        assert len(provider.requests) == 2
        assert provider.requests[0] == provider.requests[1]
        assert result.tools_used == []
        assert result.model_failure_code is (None if recover else "provider_timeout")
        assert result.content == ("Continue planning" if recover else timeout.content)

    asyncio.run(exercise())


def test_node_turn_does_not_layer_model_timeout_retry(tmp_path):
    async def exercise():
        coordinator, task = setup_task(tmp_path)
        provider = ScriptedProvider([
            LLMResponse(content="LLM request timed out after 50 seconds", finish_reason="error"),
            LLMResponse(content="must remain unused"),
        ])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path,
            forge_task_coordinator=coordinator,
        )
        result = await loop.run_node_turn(
            task_id=task.task_id, revision_id=task.active_revision_id,
            node_id="red_prepare", prompt="Use current evidence",
        )

        assert len(provider.requests) == 1
        assert result.model_failure_code == "provider_timeout"
        assert result.tools_used == []

    asyncio.run(exercise())


def test_node_turn_repeated_reads_correct_once_then_converge_without_execution(tmp_path):
    async def exercise():
        coordinator, task = setup_task(tmp_path, goal="Execute one semantic node")
        await ForgeTaskMaterializePlanTool(coordinator).execute(
            task.task_id,
            nodes=semantic_nodes(1),
            reason="fixture node",
        )
        current = coordinator.get_task(task.task_id)
        node_id = current.active_revision.plan_graph.nodes[0].node_id
        provider = ScriptedProvider([
            _tool_response(index, "forge_tool_context", {"tool_id": "scene.observe"})
            for index in range(10)
        ])
        loop = AgentLoop(
            bus=MessageBus(),
            provider=provider,
            workspace=tmp_path,
            forge_task_coordinator=coordinator,
            max_iterations=10,
        )
        loop.tools.execute = AsyncMock(return_value=json.dumps({
            "ok": True, "data": {"readiness": "ready"}, "motion_authorized": False,
        }))

        result = await loop.run_node_turn(
            task_id=task.task_id,
            revision_id=current.active_revision_id,
            node_id=node_id,
            prompt="Execute only the current node.",
        )

        assert result.turn_failure_code == "node_selection_no_progress"
        assert len(provider.requests) == 3
        assert sum(
            message.get("role") == "system"
            and "current planning node has made no Coordinator progress"
            in message.get("content", "")
            for message in result.messages
        ) == 1
        assert coordinator.get_task(task.task_id).active_revision.execution_records == []
        assert coordinator.get_task(task.task_id).active_revision.planning_selections == []

    asyncio.run(exercise())


@pytest.mark.parametrize("recover", [False, True])
def test_rejected_materialization_prose_gets_one_discovery_continuation(tmp_path, recover):
    async def exercise():
        coordinator, task = setup_task(tmp_path)
        attempt = LLMResponse(content=None, tool_calls=[ToolCallRequest(
            "materialize", "forge_task_materialize_plan", {"task_id": task.task_id},
        )])
        provider = ScriptedProvider([
            attempt, LLMResponse(content="I will correct the plan"),
            attempt if recover else LLMResponse(content="Still cannot submit"),
        ])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path,
                         forge_task_coordinator=coordinator, max_iterations=4)
        calls = []

        async def execute(name, arguments):
            calls.append(name)
            if len(calls) == 1:
                return 'Error: root conditions are not true'
            return await ForgeTaskMaterializePlanTool(coordinator).execute(
                task.task_id, nodes=semantic_nodes(1), reason="correct rejected graph",
            )

        loop.tools.execute = AsyncMock(side_effect=execute)
        result = await loop._run_agent_loop(
            [{"role": "user", "content": task.task_description}],
            active_task_id=task.task_id,
            yield_after_tools=frozenset({"forge_task_materialize_plan"}),
        )
        assert len(provider.requests) == 3
        assert len(calls) == (2 if recover else 1)
        assert (coordinator.get_task(task.task_id).active_revision.plan_graph is not None) == recover
        assert result.model_failure_code is None
        if not recover:
            assert result.content == "Still cannot submit"

    asyncio.run(exercise())


def test_discovery_complete_prose_cannot_abandon_active_task_before_materialization(tmp_path):
    async def exercise():
        coordinator, task = setup_task(tmp_path)
        coordinator.store.update(
            task.task_id,
            lambda current: current.active_revision.execution_records.append(
                ToolExecutionRecord(
                    record_id="tool-observe",
                    revision_id=current.active_revision_id,
                    tool_id="scene.observe",
                    semantics="query",
                    caller_id="paos:test",
                    status="succeeded",
                    arguments={"sensor_ref": "camera/front", "max_age_ms": 1000},
                    response={"data": {
                        "status": "available",
                        "observation_ref": "observation://scene/front",
                        "scene_revision": "scene-1",
                        "calibration_ref": "artifact://scene/calibration",
                    }},
                    evidence_refs=["tool:tool-observe"],
                )
            ),
            event_type="test_discovery_complete",
        )
        provider = ScriptedProvider([
            LLMResponse(content=(
                "The active task and materialization tool are unavailable; create a new task."
            )),
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "materialize",
                "forge_task_materialize_plan",
                {
                    "task_id": task.task_id,
                    "nodes": semantic_nodes(1),
                    "reason": "continue the persisted active task",
                },
            )]),
        ])
        loop = AgentLoop(
            bus=MessageBus(),
            provider=provider,
            workspace=tmp_path,
            forge_task_coordinator=coordinator,
            max_iterations=3,
        )

        result = await loop._run_agent_loop(
            [{"role": "user", "content": task.task_description}],
            active_task_id=task.task_id,
            yield_after_tools=frozenset({"forge_task_materialize_plan"}),
        )

        assert len(provider.requests) == 2
        assert result.tools_used == ["forge_task_materialize_plan"]
        assert coordinator.get_task(task.task_id).active_revision.plan_graph is not None
        correction = provider.requests[1]["messages"][-1]["content"]
        assert task.task_id in correction
        assert "currently visible forge_task_materialize_plan" in correction

    asyncio.run(exercise())


def test_node_turn_yields_after_selection_requires_replan(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "reject-selection",
                "forge_plan_select",
                {
                    "task_id": "task-1",
                    "node_id": "prepare-green",
                    "tool_id": "manipulation.prepare",
                    "decision_reason": "prepare current candidates",
                },
            )]),
        ])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path, max_iterations=4
        )
        loop.tools.execute = AsyncMock(return_value=json.dumps({
            "ok": False,
            "error": {
                "code": "node_tool_binding_incompatible",
                "requires_replan": True,
                "retryable_in_revision": False,
            },
            "motion_authorized": False,
        }))

        result = await loop._run_agent_loop(
            [{"role": "user", "content": "execute current node"}],
            projection_scope="node",
            projection_node_id="prepare-green",
            allowed_tool_names=frozenset({"forge_plan_select"}),
        )

        assert len(provider.requests) == 1
        assert result.tools_used == ["forge_plan_select"]
        assert "replacement plan segment" in result.content

    asyncio.run(exercise())


def test_forge_plan_select_contract_defaults_projection_only_arguments():
    from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool

    tool = ForgePlanSelectTool(coordinator=Mock(), dispatch_getter=lambda: None)
    schema = tool.parameters

    assert "arguments" not in schema["required"]
    assert schema["properties"]["arguments"]["default"] == {}


def test_discovery_yields_after_non_retryable_scene_understanding_failure(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[
                ToolCallRequest(
                    "understand",
                    "forge_tool_query",
                    {"task_id": "task-1", "tool_id": "scene.understand", "arguments": {}},
                ),
                ToolCallRequest(
                    "refresh-observation",
                    "forge_tool_query",
                    {"task_id": "task-1", "tool_id": "scene.observe", "arguments": {}},
                ),
            ]),
            LLMResponse(content="must remain unused"),
        ])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path, max_iterations=4
        )
        loop.tools.execute = AsyncMock(return_value=json.dumps({
            "ok": True,
            "data": {
                "status": "unavailable",
                "error": {
                    "code": "understanding_provider_error",
                    "reason": "transport+timeout",
                    "failure_stage": "provider",
                    "retryable": False,
                },
                "motion_authorized": False,
            },
            "paos_record": {
                "task_id": "task-1",
                "revision_id": "revision-1",
                "record_id": "record-1",
                "evidence_refs": [],
            },
        }))

        result = await loop._run_agent_loop(
            [{"role": "user", "content": "understand the current scene"}],
            projection_scope="task",
        )

        assert len(provider.requests) == 1
        loop.tools.execute.assert_awaited_once_with(
            "forge_tool_query",
            {"task_id": "task-1", "tool_id": "scene.understand", "arguments": {}},
        )
        assert result.tools_used == ["forge_tool_query"]
        assert "provider readiness recovers" in result.content
        deferred = next(
            message for message in result.messages
            if message.get("tool_call_id") == "refresh-observation"
        )
        deferred_payload = json.loads(deferred["content"])
        assert deferred_payload["status"] == "deferred_to_provider_recovery"
        assert deferred_payload["motion_authorized"] is False

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "result",
    [
        "[]",
        json.dumps({"ok": True}),
        json.dumps({
            "ok": True,
            "data": {
                "status": "unavailable",
                "error": {
                    "code": "missing_calibration",
                    "failure_stage": "request",
                    "retryable": False,
                },
            },
        }),
    ],
)
def test_scene_understanding_request_errors_do_not_wait_for_provider_recovery(result):
    assert AgentLoop._scene_understanding_provider_blocked(
        tool_name="forge_tool_query",
        arguments={"tool_id": "scene.understand"},
        result=result,
    ) is False


def test_scene_understanding_invalid_request_is_corrected_in_same_task(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "invalid-understand",
                "forge_tool_query",
                {"task_id": "task-1", "tool_id": "scene.understand", "arguments": {}},
            )]),
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "corrected-understand",
                "forge_tool_query",
                {
                    "task_id": "task-1",
                    "tool_id": "scene.understand",
                    "arguments": {"max_age_ms": 1000},
                },
            )]),
            LLMResponse(content="Scene understanding request corrected."),
        ])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path, max_iterations=4
        )
        loop.tools.execute = AsyncMock(side_effect=[
            json.dumps({
                "ok": True,
                "data": {
                    "status": "invalid",
                    "error": {
                        "code": "invalid_freshness",
                        "reason": "validation",
                        "retryable": False,
                    },
                    "motion_authorized": False,
                },
            }),
            json.dumps({
                "ok": True,
                "data": {"status": "available", "entities": []},
            }),
        ])

        result = await loop._run_agent_loop(
            [{"role": "user", "content": "understand the current scene"}],
            projection_scope="task",
        )

        assert result.tools_used == ["forge_tool_query", "forge_tool_query"]
        assert result.content == "Scene understanding request corrected."
        correction_messages = provider.requests[1]["messages"]
        assert any(
            message.get("role") == "system"
            and "rejected before any provider inference" in message.get("content", "")
            and "do not wait for provider readiness" in message.get("content", "")
            for message in correction_messages
        )

    asyncio.run(exercise())


def test_node_turn_can_correct_selection_input_without_replan(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "wrong-mode", "forge_plan_select", {"projection_source": {"record_id": "proposal"}},
            )]),
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "correct-mode", "forge_plan_select", {"projection_sources": {
                    "candidates": {"record_id": "proposal"},
                }},
            )]),
            LLMResponse(content="Selection persisted."),
        ])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path, max_iterations=4)
        loop.tools.execute = AsyncMock(side_effect=[
            json.dumps({"ok": False, "error": {
                "code": "consumer_projection_invalid", "retryable_in_revision": True,
                "requires_replan": False,
                "message": "named consumer projection accepts projection_sources only",
            }, "motion_authorized": False}),
            json.dumps({"ok": True, "data": {"selection": {"use_selected_arguments": True}},
                        "motion_authorized": False}),
        ])

        result = await loop._run_agent_loop(
            [{"role": "user", "content": "select current prepare node"}],
            projection_scope="node", projection_node_id="prepare-green",
            allowed_tool_names=frozenset({"forge_plan_select"}),
        )

        assert len(provider.requests) == 3
        assert result.tools_used == ["forge_plan_select", "forge_plan_select"]
        assert result.content == "Selection persisted."
        correction_context = provider.requests[1]["messages"]
        assert any(message.get("tool_call_id") == "wrong-mode" and
                   json.loads(message["content"])["error"]["code"] == "consumer_projection_invalid"
                   for message in correction_context)
        assert any(
            message.get("role") == "system"
            and "named projection slots" in message.get("content", "")
            and "Do not use projection_source" in message.get("content", "")
            for message in correction_context
        )
        assert loop.tools.execute.await_count == 2

    asyncio.run(exercise())


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


def test_initial_turn_yields_immediately_after_plan_materialization(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Move one observed object into the tray")
        request = {
            "task_id": task.task_id,
            "nodes": semantic_nodes(1),
            "reason": "selected from current observation",
        }
        provider = ScriptedProvider([
            LLMResponse(
                content="Materializing the current scene-bound segment.",
                tool_calls=[
                    ToolCallRequest(
                        "plan-call",
                        "forge_task_materialize_plan",
                        request,
                    )
                ],
            ),
        ])
        loop = AgentLoop(
            bus=MessageBus(),
            provider=provider,
            workspace=tmp_path,
            forge_task_coordinator=c,
            max_iterations=3,
        )

        result = await loop._run_agent_loop(
            [{"role": "user", "content": task.task_description}],
            yield_after_tools=frozenset({"forge_task_materialize_plan"}),
        )

        assert len(provider.requests) == 1
        assert result.tools_used == ["forge_task_materialize_plan"]
        assert result.content is not None and "long-horizon" in result.content
        assert c.get_task(task.task_id).active_revision.plan_graph is not None
        assert result.messages[-1]["role"] == "tool"

    asyncio.run(exercise())


def test_bounded_turn_rejects_provider_tool_outside_allowed_set(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(
                content=None,
                tool_calls=[
                    ToolCallRequest(
                        "hidden-query",
                        "forge_tool_query",
                        {"tool_id": "grasp.propose"},
                    )
                ],
            ),
            LLMResponse(content="No allowed state transition was selected."),
        ])
        loop = AgentLoop(
            bus=MessageBus(),
            provider=provider,
            workspace=tmp_path,
            max_iterations=2,
        )
        loop.tools.execute = AsyncMock(side_effect=AssertionError("hidden Tool executed"))

        result = await loop._run_agent_loop(
            [{"role": "user", "content": "continue only through declared tools"}],
            allowed_tool_names=frozenset(),
        )

        loop.tools.execute.assert_not_awaited()
        assert result.tools_used == []
        rejection = next(
            message for message in result.messages
            if message.get("tool_call_id") == "hidden-query"
        )
        assert json.loads(rejection["content"])["error"]["type"] == (
            "tool_not_available_in_turn"
        )

    asyncio.run(exercise())


def test_node_turn_cannot_browse_another_nodes_sources(tmp_path):
    async def exercise():
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "cross-node", "forge_plan_ready",
                {"node_id": "unrelated", "source_record_id": "record-other"},
            )]),
            LLMResponse(content="Source browsing must use the current node."),
        ])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path, max_iterations=2)
        loop.tools.execute = AsyncMock(side_effect=AssertionError("cross-node source read"))
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "execute current node"}],
            projection_scope="node", projection_node_id="current",
            allowed_tool_names=frozenset({"forge_plan_ready"}),
        )
        loop.tools.execute.assert_not_awaited()
        rejected = next(m for m in result.messages if m.get("tool_call_id") == "cross-node")
        assert json.loads(rejected["content"])["error"]["code"] == "source_node_out_of_scope"

    asyncio.run(exercise())


def test_node_turn_yields_after_bound_execution_and_cannot_continue_revision(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Resolve one current semantic node")
        await ForgeTaskMaterializePlanTool(c).execute(
            task.task_id,
            nodes=semantic_nodes(1),
            reason="current scene-bound node",
        )
        current = c.get_task(task.task_id)
        provider = ScriptedProvider([
            LLMResponse(
                content="Execute the current Query, then incorrectly continue the graph.",
                tool_calls=[
                    ToolCallRequest(
                        "node-query",
                        "forge_tool_query",
                        {"tool_id": "scene.observe", "arguments": {}},
                    ),
                    ToolCallRequest(
                        "illegal-continuation",
                        "forge_task_continue_plan",
                        {
                            "task_id": task.task_id,
                            "nodes": semantic_nodes(1),
                            "reason": "must not execute inside the old node turn",
                        },
                    ),
                ],
            ),
        ])
        loop = AgentLoop(
            bus=MessageBus(),
            provider=provider,
            workspace=tmp_path,
            forge_tool_client=SimpleNamespace(),
            forge_task_coordinator=c,
            max_iterations=3,
        )
        loop.turn_timeout_s = 0.5

        async def governed_execution(*_args, **_kwargs):
            await asyncio.sleep(0.6)
            return json.dumps({"ok": True})

        loop.tools.execute = AsyncMock(side_effect=governed_execution)

        result = await loop.run_node_turn(
            task_id=task.task_id,
            revision_id=current.active_revision_id,
            node_id=current.active_revision.plan_graph.nodes[0].node_id,
            prompt="Execute only this semantic node.",
        )

        visible = {item["function"]["name"] for item in provider.requests[0]["tools"]}
        assert visible == {
            "forge_plan_select",
            "forge_tool_context",
            "forge_tool_query",
            "forge_tool_start_action",
            "forge_tool_start_session",
        }
        assert "forge_plan_activate" not in visible
        assert "forge_task_get" not in visible
        assert "forge_task_continue_plan" not in visible
        assert "forge_task_finalize" not in visible
        assert "exec" not in visible
        loop.tools.execute.assert_awaited_once_with(
            "forge_tool_query",
            {"tool_id": "scene.observe", "arguments": {}},
        )
        deferred = next(
            message for message in result.messages
            if message.get("tool_call_id") == "illegal-continuation"
        )
        assert json.loads(deferred["content"])["error"]["type"] == "control_handoff"
        assert len(provider.requests) == 1
        assert c.get_task(task.task_id).active_revision_id == current.active_revision_id

    asyncio.run(exercise())


def test_segment_continuation_turn_appends_next_revision_without_execution_tools(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Move two scene-bound objects in sequence")
        await ForgeTaskMaterializePlanTool(c).execute(
            task.task_id,
            nodes=semantic_nodes(1),
            reason="first scene-bound segment",
        )
        current = c.get_task(task.task_id)
        for node in current.active_revision.plan_graph.nodes:
            c.record_node_settlement(NodeSettlement(
                task_id=task.task_id,
                revision_id=current.active_revision_id,
                node_id=node.node_id,
                status="completed",
                scene_revision="scene-1",
            ))
        c.store.update(
            task.task_id,
            lambda record: record.active_revision.execution_records.append(
                ToolExecutionRecord(
                    record_id="tool-current-scene",
                    revision_id=current.active_revision_id,
                    tool_id="scene.bind",
                    semantics="query",
                    caller_id="agent-task-test",
                    status="succeeded",
                    response={"ok": True, "data": {"scene_revision": "scene-1"}},
                    evidence_refs=["tool:tool-current-scene"],
                )
            ),
            event_type="fixture_current_scene",
        )
        provider = ScriptedProvider([
            LLMResponse(
                content="Appending the next scene-bound segment.",
                tool_calls=[
                    ToolCallRequest(
                        "continue-call",
                        "forge_task_continue_plan",
                        {
                            "task_id": task.task_id,
                            "nodes": semantic_nodes(1),
                            "reason": "fresh evidence supports the next segment",
                        },
                    )
                ],
            ),
        ])
        loop = AgentLoop(
            bus=MessageBus(),
            provider=provider,
            workspace=tmp_path,
            forge_task_coordinator=c,
            max_iterations=3,
        )
        original_build = loop.prompt_context.build
        prompt_tool_sets: list[frozenset[str]] = []

        def record_prompt_tools(**kwargs):
            prompt_tool_sets.append(frozenset(kwargs["all_tool_names"]))
            return original_build(**kwargs)

        loop.prompt_context.build = record_prompt_tools

        result = await loop.run_segment_continuation_turn(task_id=task.task_id)

        updated = c.get_task(task.task_id)
        assert len(provider.requests) == 1
        visible = {item["function"]["name"] for item in provider.requests[0]["tools"]}
        assert "forge_task_continue_plan" in visible
        assert "forge_task_finalize" in visible
        assert "forge_tool_query" not in visible
        sent = json.dumps(provider.requests[0])
        assert "predecessor-only source producers" in sent
        assert "Declaring dependent Action nodes does not execute or authorize them" in sent
        assert prompt_tool_sets == [frozenset({
            "forge_task_continue_plan",
            "forge_task_begin_revision",
            "forge_task_finalize",
            "forge_task_cancel",
            "forge_task_request_clarification",
        })]
        assert result.tools_used == ["forge_task_continue_plan"]
        assert len(updated.revisions) == 3
        assert updated.active_revision_id != current.active_revision_id

    asyncio.run(exercise())


def test_segment_continuation_keeps_read_only_context_in_agent_turn(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Choose the next segment from current facts")
        await ForgeTaskMaterializePlanTool(c).execute(
            task.task_id, nodes=semantic_nodes(1), reason="first segment",
        )
        current = c.get_task(task.task_id)
        current_revision_id = current.active_revision_id
        for node in current.active_revision.plan_graph.nodes:
            c.record_node_settlement(NodeSettlement(
                task_id=task.task_id, revision_id=current.active_revision_id,
                node_id=node.node_id, status="completed", scene_revision="scene-1",
            ))
        provider = ScriptedProvider([
            _tool_response(0, "forge_tool_context", {"tool_id": "scene.observe"}),
            _tool_response(1, "forge_task_continue_plan", {
                "task_id": task.task_id, "nodes": semantic_nodes(1),
                "reason": "context read completed; continue",
            }),
            LLMResponse(content="done"),
        ])
        client = SimpleNamespace(
            get_tool=AsyncMock(return_value={"data": {"input_schema": {"type": "object"}}}),
            get_tool_context=AsyncMock(return_value={"data": {"ready": True}}),
        )
        c.client = client
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path,
            forge_task_coordinator=c, forge_tool_client=client, max_iterations=3,
        )
        result = await loop.run_segment_continuation_turn(task_id=task.task_id)
        assert result.turn_failure_code is None
        assert result.tools_used[:2] == ["forge_tool_context", "forge_task_continue_plan"]
        # Context is an intermediate read. The model receives another turn;
        # the attempted control outcome is then rejected by the Coordinator
        # because this fixture has no scene evidence, with no Action dispatch.
        assert len(provider.requests) == 3
        continue_result = next(
            message for message in result.messages
            if message.get("name") == "forge_task_continue_plan"
        )
        assert "no persisted scene revision" in continue_result["content"]
        updated = c.get_task(task.task_id)
        assert updated.active_revision_id == current_revision_id

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


def test_semantic_submission_rejects_unpersisted_future_evidence(tmp_path):
    _c, task = setup_task(tmp_path)
    nodes = semantic_nodes(1)
    nodes[0]["required_evidence"] = ["tool:existing-observation"]
    nodes[1]["required_evidence"] = ["tool:invented-future-record"]
    with pytest.raises(ValueError, match="dependencies for future Tool results"):
        compile_task_plan(
            task,
            nodes,
            reason="reject invented future evidence",
            initial_evidence_refs=("tool:existing-observation",),
        )


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


def test_clarification_rejects_successful_query_motion_flag(tmp_path):
    c, task = setup_task(tmp_path)
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(
            ToolExecutionRecord(
                record_id="tool-observe-available",
                revision_id=current.active_revision_id,
                tool_id="scene.observe",
                semantics="query",
                caller_id="agent-task-test",
                status="succeeded",
                arguments={"sensor_ref": "camera/front", "max_age_ms": 1000},
                response={"data": {
                    "status": "available",
                    "motion_authorized": False,
                    "observation_ref": "observation://scene/front",
                    "scene_revision": "scene-1",
                    "calibration_ref": "artifact://scene/calibration",
                }},
                evidence_refs=["tool:tool-observe-available"],
            )
        ),
        event_type="test_available_query_motion_flag",
    )

    result = json.loads(asyncio.run(ForgeTaskClarificationTool(c).execute(
        task.task_id,
        question="motion_authorized=false requires external authorization",
    )))

    assert result["ok"] is False
    assert result["error"]["code"] == "query_motion_authorization_not_blocker"
    assert result["error"]["next_step"] == "forge_task_materialize_plan"
    assert c.get_task(task.task_id).status == AgentTaskStatus.EXECUTING


def test_clarification_still_accepts_unavailable_query_blocker(tmp_path):
    c, task = setup_task(tmp_path)
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(
            ToolExecutionRecord(
                record_id="tool-observe-unavailable",
                revision_id=current.active_revision_id,
                tool_id="scene.observe",
                semantics="query",
                caller_id="agent-task-test",
                status="succeeded",
                arguments={"sensor_ref": "camera/front", "max_age_ms": 1000},
                response={"data": {
                    "status": "unavailable",
                    "motion_authorized": False,
                }},
                evidence_refs=["tool:tool-observe-unavailable"],
            )
        ),
        event_type="test_unavailable_query_motion_flag",
    )

    result = json.loads(asyncio.run(ForgeTaskClarificationTool(c).execute(
        task.task_id,
        question="The scene provider is unavailable; should I wait?",
    )))

    assert result["ok"] is True
    assert result["data"]["status"] == "waiting_for_user"


def test_agent_loop_continues_to_materialization_after_false_query_blocker(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path)
        c.store.update(
            task.task_id,
            lambda current: current.active_revision.execution_records.append(
                ToolExecutionRecord(
                    record_id="tool-observe-available-loop",
                    revision_id=current.active_revision_id,
                    tool_id="scene.observe",
                    semantics="query",
                    caller_id="agent-task-test",
                    status="succeeded",
                    arguments={"sensor_ref": "camera/front", "max_age_ms": 1000},
                    response={"data": {
                        "status": "available",
                        "motion_authorized": False,
                        "observation_ref": "observation://scene/front",
                        "scene_revision": "scene-1",
                        "calibration_ref": "artifact://scene/calibration",
                    }},
                    evidence_refs=["tool:tool-observe-available-loop"],
                )
            ),
            event_type="test_loop_available_query_motion_flag",
        )
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "clarify",
                "forge_task_request_clarification",
                {
                    "task_id": task.task_id,
                    "question": "motion_authorized=false needs external authorization",
                },
            )]),
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "materialize",
                "forge_task_materialize_plan",
                {
                    "task_id": task.task_id,
                    "nodes": semantic_nodes(1),
                    "reason": "continue after read-only discovery",
                },
            )]),
        ])
        loop = AgentLoop(
            bus=MessageBus(),
            provider=provider,
            workspace=tmp_path,
            forge_task_coordinator=c,
            max_iterations=3,
        )

        result = await loop._run_agent_loop(
            [{"role": "user", "content": task.task_description}],
            active_task_id=task.task_id,
            yield_after_tools=frozenset({"forge_task_materialize_plan"}),
        )

        current = c.get_task(task.task_id)
        assert len(provider.requests) == 2
        assert result.tools_used == [
            "forge_task_request_clarification",
            "forge_task_materialize_plan",
        ]
        assert current.status == AgentTaskStatus.EXECUTING
        assert current.active_revision.plan_graph is not None

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


def test_node_turn_receives_original_goal_without_reinjecting_full_skill(tmp_path):
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
        assert "Observe after grasp." not in sent
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


def test_model_failure_settlement_closes_task_without_unresolved_execution(tmp_path):
    coordinator, task = setup_task(tmp_path)

    result = coordinator.fail_task(task.task_id, reason="agent model/control-plane failure: turn_timeout")

    assert result.status is AgentTaskStatus.FAILED
    assert result.terminal
    assert result.evidence_errors[-1].endswith("turn_timeout")
    assert coordinator.get_task(task.task_id).status is AgentTaskStatus.FAILED


def test_model_failure_settlement_does_not_bypass_unresolved_action(tmp_path):
    coordinator, task = setup_task(tmp_path)
    coordinator.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(
            ToolExecutionRecord(
                record_id="execution-pending",
                revision_id=current.active_revision_id,
                tool_id="object.place",
                semantics="action",
                caller_id="agent",
                status="accepted",
                invocation_id="invocation-pending",
            )
        ),
        event_type="test_pending_action",
    )

    with pytest.raises(AgentTaskError, match="non-terminal"):
        coordinator.fail_task(task.task_id, reason="agent model/control-plane failure: turn_timeout")
    assert coordinator.get_task(task.task_id).status is AgentTaskStatus.EXECUTING


def test_record_skill_use_is_atomic_across_store_instances(tmp_path):
    c, task = setup_task(tmp_path)
    peer = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
    )
    barrier = threading.Barrier(2)
    arguments = {
        "activation_id": "activation-concurrent",
        "skill_name": "pick-place-workflow",
        "skill_version": "2.2.0",
        "content_sha256": "c" * 64,
        "instructions": "Observe, prepare, then execute through Forge.",
        "decision_ref": "node:revision-concurrent:prepare",
        "node_id": "prepare",
    }

    def record(coordinator):
        barrier.wait(timeout=2)
        return coordinator.record_skill_use(task.task_id, **arguments)

    with ThreadPoolExecutor(max_workers=2) as pool:
        uses = tuple(pool.map(record, (c, peer)))

    current = c.get_task(task.task_id)
    events = [
        item
        for item in c.store.events(task.task_id)
        if item["event_type"] == "skill_use_recorded"
    ]
    assert uses[0].use_id == uses[1].use_id
    assert [item.use_id for item in current.skill_uses] == [uses[0].use_id]
    assert current.active_revision.skill_use_ids == (uses[0].use_id,)
    assert len(events) == 1
    assert events[0]["payload"]["use_id"] == uses[0].use_id


@pytest.mark.parametrize("status,expected", [("unavailable", "failed"), ("empty", "failed"), ("stale", "failed"), ("unknown", "unknown"), ("available", "succeeded")])
def test_query_availability_is_not_transport_success(status, expected):
    record = SimpleNamespace(
        semantics="query",
        status="succeeded",
        response={"status": status, "motion_authorized": False},
    )
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


def test_runtime_owned_non_replannable_failure_stops_without_model_recovery(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path)
        graph = compile_task_plan(task, semantic_nodes(1), reason="test plan")
        c.expand_discovery_revision(
            task.task_id,
            plan_graph=graph,
            plan_graph_ref="artifact://plans/runtime-owned-failure",
        )

        def add_failure(current):
            current.active_revision.execution_records.append(ToolExecutionRecord(
                record_id="prepare-runtime-failure",
                revision_id=graph.revision_id,
                node_id="chosen-0",
                node_digest=plan_node_digest(graph.nodes[0]),
                obligation_id=graph.nodes[0].obligation_id,
                input_binding_digest="d" * 64,
                decision_trace_ref="artifact://planning-traces/runtime-owned-failure",
                tool_id="consumer.query",
                semantics="query",
                caller_id="paos:test",
                status="succeeded",
                response={"data": {
                    "status": "unavailable",
                    "failure_owner": "runtime_adapter",
                    "retryable_in_revision": False,
                    "requires_replan": False,
                    "recommended_action": "fix_runtime_contract",
                }},
            ))

        c.store.update(task.task_id, add_failure, event_type="fixture_runtime_failure")
        settlement = NodeSettlement(
            task_id=task.task_id,
            revision_id=graph.revision_id,
            node_id="chosen-0",
            status="failed",
            failure_code="provider_contract_error",
        )
        provider = ScriptedProvider([])
        chooser = AgentRecoveryDecisions(provider, "fixture-model", c)

        result = await chooser.select_recovery(
            graph=graph,
            settlement=settlement,
            delta=build_replan_delta(graph, settlement),
            context=settlement,
        )

        assert result == "stop"
        assert provider.requests == []
        event = c.store.events(task.task_id)[-1]
        assert event["event_type"] == "agent_recovery_decided"
        assert event["payload"]["reason"].endswith("fix_runtime_contract")

    asyncio.run(exercise())


def test_successful_action_does_not_trigger_non_replannable_failure_shortcut(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path)
        graph = compile_task_plan(task, semantic_nodes(1), reason="test plan")
        c.expand_discovery_revision(
            task.task_id,
            plan_graph=graph,
            plan_graph_ref="artifact://plans/successful-action-recovery",
        )

        def add_success(current):
            current.active_revision.execution_records.append(ToolExecutionRecord(
                record_id="successful-action",
                revision_id=graph.revision_id,
                node_id="chosen-0",
                node_digest=plan_node_digest(graph.nodes[0]),
                obligation_id=graph.nodes[0].obligation_id,
                input_binding_digest="d" * 64,
                decision_trace_ref="artifact://planning-traces/successful-action",
                tool_id="object.acquire",
                semantics="action",
                caller_id="paos:test",
                status="succeeded",
                response={"data": {"result": {
                    "status": "succeeded",
                    "retryable_in_revision": False,
                    "requires_replan": False,
                    "recommended_action": "continue",
                }}},
            ))

        c.store.update(task.task_id, add_success, event_type="fixture_successful_action")
        settlement = NodeSettlement(
            task_id=task.task_id,
            revision_id=graph.revision_id,
            node_id="chosen-0",
            status="failed",
            failure_code="postcondition_requires_review",
        )
        provider = ScriptedProvider([LLMResponse(
            content=None,
            tool_calls=[ToolCallRequest(
                "decision",
                "submit_recovery",
                {"decision": "stop", "reason": "postcondition needs review"},
            )],
        )])

        result = await AgentRecoveryDecisions(
            provider, "fixture-model", c
        ).select_recovery(
            graph=graph,
            settlement=settlement,
            delta=build_replan_delta(graph, settlement),
            context=settlement,
        )

        assert result == "stop"
        assert len(provider.requests) == 1
        assert c.store.events(task.task_id)[-1]["payload"]["reason"] == (
            "postcondition needs review"
        )

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


def test_unknown_world_change_bootstraps_scene_refresh_without_model_proposal(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path)
        observe_tool = task.primary_skill_binding.required_tools[0]
        observe_policy = observe_tool.planning_policy.model_copy(
            update={"capabilities": ("scene.observe",), "refreshes_scene": True}
        )
        work_policy = ToolSpecPolicy(
            tool_id="fixture.work",
            semantics="action",
            spec_digest="d" * 64,
            capabilities=("object.relocate", "task.verify"),
        )
        binding = task.primary_skill_binding.model_copy(update={
            "required_tools": (
                observe_tool.model_copy(update={"planning_policy": observe_policy}),
                BoundToolSpec(
                    tool_id="fixture.work",
                    semantics="action",
                    spec_sha256="d" * 64,
                    ready_at_binding=True,
                    planning_policy=work_policy,
                ),
            ),
        })
        c.store.update(
            task.task_id,
            lambda current: setattr(current, "primary_skill_binding", binding),
            event_type="test_scene_refresh_binding",
        )
        task = c.get_task(task.task_id)
        graph = compile_task_plan(task, semantic_nodes(1), reason="initial action segment")
        settlement = NodeSettlement(
            task_id=task.task_id,
            revision_id=graph.revision_id,
            node_id="chosen-0",
            status="outcome_unknown",
            failure_code="grasp_lift_unverified",
            world_change_started=True,
            outcome_known=False,
            retryable_in_revision=False,
            requires_replan=True,
            recommended_action="reconcile_world",
        )
        provider = ScriptedProvider([])

        proposal = await AgentRecoveryDecisions(
            provider, "fixture-model", c
        ).propose_replan(
            graph=graph,
            settlement=settlement,
            delta=build_replan_delta(graph, settlement),
            context=settlement,
        )

        assert provider.requests == []
        assert proposal.delta.retry_parent_node_id == "chosen-0"
        assert proposal.delta.preserve_node_ids == ()
        assert proposal.reason == (
            "Runtime reported an unknown outcome after a world-changing Action; "
            "refresh the current scene before planning any further Action"
        )
        recovery_node = proposal.plan_graph.nodes[0]
        assert recovery_node.node_id.startswith("recovery_scene_refresh_")
        assert recovery_node.node_id not in {node.node_id for node in graph.nodes}
        assert recovery_node.model_dump(mode="json") == {
            "node_id": recovery_node.node_id,
            "obligation_id": "refresh_current_scene_after_unknown_effect",
            "capability": "scene.observe",
            "dependencies": [],
            "conditions": [],
            "required_evidence": [],
            "produced_evidence": [],
            "resources": [],
            "effects": [],
            "input_bindings": {},
            "retry_of": None,
        }
        assert len(c.get_task(task.task_id).revisions) == 1
        assert c.get_task(task.task_id).execution_records == []

    asyncio.run(exercise())


def test_scene_refresh_bootstrap_node_identity_is_stable_and_avoids_source_collision():
    source = SimpleNamespace(
        revision_id="revision-source",
        nodes=(SimpleNamespace(node_id="existing-node"),),
    )

    assert _scene_refresh_bootstrap_node_id(source) == (
        "recovery_scene_refresh_revision-source"
    )
    assert _scene_refresh_bootstrap_node_id(source) == (
        "recovery_scene_refresh_revision-source"
    )

    source.nodes = (
        SimpleNamespace(node_id="recovery_scene_refresh_revision-source"),
        SimpleNamespace(node_id="recovery_scene_refresh_revision-source_2"),
    )
    assert _scene_refresh_bootstrap_node_id(source) == (
        "recovery_scene_refresh_revision-source_3"
    )


def test_scene_refresh_bootstrap_rejects_capability_bound_to_stale_scene_facts():
    policy = ToolSpecPolicy(
        tool_id="fixture.observe",
        semantics="query",
        spec_digest="a" * 64,
        capabilities=("scene.refresh",),
        input_binding_keys=("scene_revision",),
        refreshes_scene=True,
    )
    task = SimpleNamespace(
        primary_skill_binding=SimpleNamespace(
            required_tools=(
                BoundToolSpec(
                    tool_id="fixture.observe",
                    semantics="query",
                    spec_sha256="a" * 64,
                    ready_at_binding=True,
                    planning_policy=policy,
                ),
            )
        )
    )

    assert _scene_refresh_bootstrap_capability(task) is None


def test_unknown_world_change_does_not_guess_ambiguous_refresh_capability(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path)
        observe_tool = task.primary_skill_binding.required_tools[0]
        observe_policy = observe_tool.planning_policy.model_copy(
            update={"capabilities": ("scene.observe",), "refreshes_scene": True}
        )
        work_policy = ToolSpecPolicy(
            tool_id="fixture.work",
            semantics="action",
            spec_digest="d" * 64,
            capabilities=("object.relocate", "task.verify"),
        )
        alternate_policy = ToolSpecPolicy(
            tool_id="alternate.observe",
            semantics="query",
            spec_digest="c" * 64,
            capabilities=("alternate.scene.refresh",),
            refreshes_scene=True,
        )
        binding = task.primary_skill_binding.model_copy(update={
            "required_tools": (
                observe_tool.model_copy(update={"planning_policy": observe_policy}),
                BoundToolSpec(
                    tool_id="fixture.work",
                    semantics="action",
                    spec_sha256="d" * 64,
                    ready_at_binding=True,
                    planning_policy=work_policy,
                ),
                BoundToolSpec(
                    tool_id="alternate.observe",
                    semantics="query",
                    spec_sha256="c" * 64,
                    ready_at_binding=True,
                    planning_policy=alternate_policy,
                ),
            ),
        })
        c.store.update(
            task.task_id,
            lambda current: setattr(current, "primary_skill_binding", binding),
            event_type="test_ambiguous_scene_refresh_binding",
        )
        task = c.get_task(task.task_id)
        graph = compile_task_plan(task, semantic_nodes(1), reason="initial action segment")
        settlement = NodeSettlement(
            task_id=task.task_id,
            revision_id=graph.revision_id,
            node_id="chosen-0",
            status="outcome_unknown",
            world_change_started=True,
            outcome_known=False,
            requires_replan=True,
        )
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[]),
        ])

        with pytest.raises(ValueError, match="recovery model returned no unique decision"):
            await AgentRecoveryDecisions(
                provider, "fixture-model", c
            ).propose_replan(
                graph=graph,
                settlement=settlement,
                delta=build_replan_delta(graph, settlement),
                context=settlement,
            )

        assert len(provider.requests) == 1
        assert len(c.get_task(task.task_id).revisions) == 1
        assert c.get_task(task.task_id).execution_records == []

    asyncio.run(exercise())


def test_model_replan_reconciles_omitted_historical_node_without_executing(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path)
        graph = compile_task_plan(task, semantic_nodes(2), reason="first")
        settlement = NodeSettlement(
            task_id=task.task_id,
            revision_id=graph.revision_id,
            node_id="chosen-1",
            status="failed",
        )
        recovery_nodes = [{
            "node_id": "recovery-observe",
            "obligation_id": "refresh-current-evidence",
            "capability": "scene.observe",
        }]
        provider = ScriptedProvider([LLMResponse(content=None, tool_calls=[ToolCallRequest(
            "proposal",
            "submit_recovery",
            {"nodes": recovery_nodes, "reason": "refresh current evidence"},
        )])])

        proposal = await AgentRecoveryDecisions(provider, "fixture-model", c).propose_replan(
            graph=graph,
            settlement=settlement,
            delta=build_replan_delta(graph, settlement),
            context=settlement,
        )

        assert proposal.delta.preserve_node_ids == ()
        assert tuple(node.node_id for node in proposal.plan_graph.nodes) == ("recovery-observe",)
        current = c.get_task(task.task_id)
        assert len(current.revisions) == 1
        assert current.execution_records == []

    asyncio.run(exercise())


def test_model_replan_repairs_changed_preserve_candidate_without_executing(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path)
        graph = compile_task_plan(task, semantic_nodes(2), reason="first")
        settlement = NodeSettlement(
            task_id=task.task_id,
            revision_id=graph.revision_id,
            node_id="chosen-1",
            status="failed",
        )
        changed = semantic_nodes(2)
        changed[0]["obligation_id"] = "changed-completed-obligation"
        repaired = [{
            "node_id": "recovery-observe",
            "obligation_id": "refresh-current-evidence",
            "capability": "scene.observe",
        }]
        provider = ScriptedProvider([
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "invalid",
                "submit_recovery",
                {"nodes": changed, "reason": "changed preserved work"},
            )]),
            LLMResponse(content=None, tool_calls=[ToolCallRequest(
                "repaired",
                "submit_recovery",
                {"nodes": repaired, "reason": "refresh current evidence"},
            )]),
        ])

        proposal = await AgentRecoveryDecisions(provider, "fixture-model", c).propose_replan(
            graph=graph,
            settlement=settlement,
            delta=build_replan_delta(graph, settlement),
            context=settlement,
        )

        assert proposal.delta.preserve_node_ids == ()
        assert tuple(node.node_id for node in proposal.plan_graph.nodes) == ("recovery-observe",)
        assert len(provider.requests) == 2
        repair_context = json.loads(provider.requests[1]["messages"][1]["content"])
        assert "replacement content changed" in repair_context["repair"]["validation_error"]
        current = c.get_task(task.task_id)
        assert len(current.revisions) == 1
        assert current.execution_records == []
        assert any(
            event["event_type"] == "agent_replan_proposal_rejected"
            for event in c.store.events(task.task_id)
        )

    asyncio.run(exercise())


@pytest.mark.parametrize("repaired", [True, False])
def test_automatic_replan_repairs_cross_revision_retry_once_without_execution(tmp_path, repaired):
    async def exercise():
        c, task = setup_task(tmp_path)
        graph = compile_task_plan(task, semantic_nodes(2), reason="first")
        settlement = NodeSettlement(task_id=task.task_id, revision_id=graph.revision_id,
                                    node_id="chosen-0", status="failed")
        invalid = semantic_nodes(2)
        invalid[0]["retry_of"] = "prior-revision-prepare"
        provider = ScriptedProvider([LLMResponse(content=None, tool_calls=[ToolCallRequest(
            str(i), "submit_recovery", {"nodes": nodes, "reason": "Refresh current evidence"},
        )]) for i, nodes in enumerate((invalid, semantic_nodes(2) if repaired else invalid))])
        operation = AgentRecoveryDecisions(provider, "fixture", c).propose_replan(
            graph=graph, settlement=settlement, delta=build_replan_delta(graph, settlement), context=settlement)
        if repaired:
            proposal = await operation
            assert proposal.plan_graph.nodes[0].retry_of is None
        else:
            with pytest.raises(ValueError, match="retry_of references an unknown node"):
                await operation
        assert len(provider.requests) == 2
        context = json.loads(provider.requests[1]["messages"][1]["content"])
        assert "retry_of references an unknown node" in context["repair"]["validation_error"]
        assert context["repair"]["rejected_proposal"]["nodes"] == invalid
        assert "omit prior-revision retry_of" in provider.requests[0]["messages"][0]["content"]
        current = c.get_task(task.task_id)
        assert len(current.revisions) == 1
        assert current.execution_records == []
        assert any(e["event_type"] == "agent_replan_proposal_rejected" for e in c.store.events(task.task_id))
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


@pytest.mark.parametrize(
    "tool_type,semantics,operation,expected_reconcile",
    [
        (ForgeToolActionStatusTool, "action", "status", False),
        (ForgeToolActionResultTool, "action", "result", True),
        (ForgeToolSessionStatusTool, "session", "status", False),
        (ForgeToolSessionResultTool, "session", "result", True),
    ],
)
def test_invocation_read_tools_settle_only_from_result(
    tool_type,
    semantics,
    operation,
    expected_reconcile,
):
    response = {"data": {"status": "succeeded"}}
    client = SimpleNamespace(
        base_url="http://test.invalid",
    )
    coordinator = SimpleNamespace(
        require_action_invocation=Mock(),
        require_session_invocation=Mock(),
        read_invocation=AsyncMock(return_value=response),
        read_session_invocation=AsyncMock(return_value=response),
        observe_action=Mock(),
        observe_session=Mock(),
    )

    output = json.loads(asyncio.run(
        tool_type(client, coordinator).execute("task-1", "invocation-1")
    ))

    assert output == response
    read_method = (
        coordinator.read_invocation
        if semantics == "action"
        else coordinator.read_session_invocation
    )
    read_method.assert_awaited_once_with(
        "task-1", "invocation-1", result=operation == "result"
    )
    getattr(coordinator, f"require_{semantics}_invocation").assert_called_once_with(
        "task-1", "invocation-1"
    )
    getattr(coordinator, f"observe_{semantics}").assert_called_once_with(
        "task-1",
        "invocation-1",
        response,
        reconcile_settlement=expected_reconcile,
    )


@pytest.mark.parametrize(
    ("gateway_status", "binding_retained"),
    [("succeeded", False), ("unknown", True)],
)
def test_terminal_task_reconciles_original_unknown_action_without_reopening(
    tmp_path, gateway_status, binding_retained
):
    async def exercise():
        coordinator, task = setup_task(tmp_path)
        invocation_id = "invocation://object-place/original"
        coordinator.runtime_invocation_ids = {invocation_id}
        coordinator.runtime_task_binding_ids = {"binding-test"}
        coordinator.client = SimpleNamespace(
            base_url="http://test.invalid",
            invocation_result=AsyncMock(return_value={"data": {"status": gateway_status}})
        )

        def add_unknown_action(current):
            current.status = AgentTaskStatus.FAILED
            current.active_revision.execution_records.append(ToolExecutionRecord(
                record_id="action-record-1",
                revision_id=current.active_revision_id,
                tool_id="object.place",
                semantics="action",
                caller_id="paos:test",
                status="unknown",
                invocation_id=invocation_id,
                error={"code": "action_poll_budget_exhausted"},
            ))

        coordinator.store.update(
            task.task_id, add_unknown_action, event_type="test_unknown_action"
        )
        result = json.loads(await ForgeToolActionResultTool(
            coordinator.client, coordinator
        ).execute(task.task_id, invocation_id))

        saved = coordinator.get_task(task.task_id)
        record = saved.execution_records[-1]
        assert result["data"]["status"] == gateway_status
        assert saved.status == AgentTaskStatus.FAILED
        assert record.status == gateway_status
        assert (invocation_id in coordinator.runtime_invocation_ids) is binding_retained
        assert ("binding-test" in coordinator.runtime_task_binding_ids) is binding_retained

    asyncio.run(exercise())


def test_scene_bind_query_copies_observation_identity_without_overriding_entities():
    observation = ToolExecutionRecord(
        record_id="observe-1",
        revision_id="revision-1",
        tool_id="scene.observe",
        semantics="query",
        caller_id="paos:test",
        status="succeeded",
        arguments={"sensor_ref": "camera/head"},
        response={"data": {"status": "available", "observation_ref": "observation://scene/head",
                            "scene_revision": "scene-1", "calibration_ref": "artifact://calibration/1"}},
    )
    task = SimpleNamespace(active_revision_id="revision-1", execution_records=[observation])
    resolved = _resolve_observation_bound_query_arguments(
        "scene.bind", task, {"entity_refs": ["entity://red"]}
    )
    assert resolved == {
        "entity_refs": ["entity://red"],
        "observation_ref": "observation://scene/head",
        "scene_revision": "scene-1",
        "calibration_ref": "artifact://calibration/1",
    }


def test_scene_bind_rejects_alias_and_ambiguous_understanding_entities():
    understanding = SimpleNamespace(
        tool_id="scene.understand",
        status="succeeded",
        revision_id="revision-1",
        record_id="understand-1",
        response={"data": {
            "entities": [
                {"entity_ref": "entity://e1", "category": "green cube"},
                {"entity_ref": "entity://e4", "category": "white surface"},
            ],
            "ambiguities": [{
                "code": "entity_identity_uncertain",
                "entity_refs": ["entity://e4"],
            }],
        }},
    )
    task = SimpleNamespace(active_revision_id="revision-1", execution_records=[understanding])
    alias_error = _scene_bind_argument_error(task, {"entities": []})
    assert alias_error["code"] == "scene_bind_requires_entity_refs"
    ambiguous_error = _scene_bind_argument_error(
        task, {"entity_refs": ["entity://e1", "entity://e4"]}
    )
    assert ambiguous_error["code"] == "ambiguous_entity_selection"
    assert ambiguous_error["ambiguous_entity_refs"] == ["entity://e4"]
    assert ambiguous_error["recommended_unambiguous_entity_refs"] == ["entity://e1"]
    assert ambiguous_error["selection_constraints"] == {
        "recommendation_scope": "perception_ambiguity_only",
        "ambiguity_scope": "referenced_entities",
        "must_match_task_entities": True,
        "environment_only_substitution_forbidden": True,
    }


def test_scene_bind_treats_empty_ambiguity_scope_as_global():
    understanding = SimpleNamespace(
        tool_id="scene.understand",
        status="succeeded",
        revision_id="revision-1",
        record_id="understand-global-ambiguity",
        response={"data": {
            "entities": [{"entity_ref": "entity://e1", "category": "object"}],
            "ambiguities": [{
                "code": "correspondence_uncertain",
                "message": "identity scope is global",
                "entity_refs": [],
            }],
        }},
    )
    task = SimpleNamespace(
        active_revision_id="revision-1",
        execution_records=[understanding],
    )

    error = _scene_bind_argument_error(
        task, {"entity_refs": ["entity://e1"]}
    )

    assert error["code"] == "ambiguous_entity_selection"
    assert error["ambiguous_entity_refs"] == ["entity://e1"]
    assert error["recommended_unambiguous_entity_refs"] == []


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


def test_opt_in_skill_recovery_reads_persisted_current_instructions_and_survives_compaction(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Inspect")
        instructions = "Current Coordinator-owned Skill constraints. " * 1000
        c.store.update(task.task_id, lambda t: setattr(t, "active_skill_instructions", instructions),
                       event_type="fixture_active_instructions")
        getter = ForgeTaskGetTool(c)
        default = json.loads(compact_tool_result("forge_task_get", await getter.execute(task.task_id)))["result"]
        assert "requested_skill_instructions" not in default["data"]
        recovered = json.loads(compact_tool_result("forge_task_get", await getter.execute(
            task.task_id, include_skill_instructions=True,
        )))["result"]
        assert recovered["data"]["requested_skill_instructions"] == instructions
        assert getter.parameters["properties"]["include_skill_instructions"]["default"] is False
        provider = ScriptedProvider([
            _tool_response(0, "forge_task_get", {
                "task_id": task.task_id, "include_skill_instructions": True,
            }),
            LLMResponse(content="Constraints recovered"),
        ])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path,
                         forge_task_coordinator=c, max_iterations=2, discovery_no_progress_limit=1)
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Recover constraints"}], active_task_id=task.task_id,
        )
        assert result.turn_failure_code is None
        assert instructions in json.loads(next(m["content"] for m in provider.requests[1]["messages"]
            if m.get("name") == "forge_task_get"))["result"]["data"]["requested_skill_instructions"]
        assert "Discovery has made no Coordinator progress" not in json.dumps(provider.requests[1]["messages"])
    asyncio.run(exercise())


def _tool_response(index, name, arguments):
    return LLMResponse(content=None, tool_calls=[ToolCallRequest(str(index), name, arguments)])


def test_distinct_live_contracts_then_real_task_bound_query_advance_discovery(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Inspect the current workspace")
        client = SimpleNamespace(
            get_tool=AsyncMock(return_value={"data": {"input_schema": {"type": "object"}}}),
            get_tool_context=AsyncMock(return_value={"data": {"readiness": "ready"}}),
            invoke_query_tool=AsyncMock(return_value={"ok": True, "data": {
                "status": "available", "scene_revision": "fixture-scene-1",
            }}),
        )
        c.client = client
        c._require_binding_tool = AsyncMock(return_value=task.primary_skill_binding.required_tools[0])
        provider = ScriptedProvider([
            *[_tool_response(i, "forge_tool_context", {"tool_id": f"fixture.query.{i}"}) for i in range(5)],
            _tool_response(5, "forge_tool_query", {
                "task_id": task.task_id, "tool_id": "scene.observe", "arguments": {},
            }),
        ])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path,
            forge_task_coordinator=c, forge_tool_client=client,
            max_iterations=6, discovery_no_progress_limit=1,
        )
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Inspect"}], active_task_id=task.task_id,
            yield_after_tools=frozenset({"forge_tool_query"}),
        )
        assert result.turn_failure_code is None
        assert len(provider.requests) == 6
        assert client.invoke_query_tool.await_count == 1
        assert len(c.get_task(task.task_id).execution_records) == 1
        assert c.get_task(task.task_id).execution_records[0].status == "succeeded"
        for request in provider.requests:
            assert "forge_tool_context" in {t["function"]["name"] for t in request["tools"]}
            assert "Discovery has made no Coordinator progress" not in json.dumps(request["messages"])
    asyncio.run(exercise())


@pytest.mark.parametrize("repeated_tool", ["exec", "forge_tool_context"])
def test_discovery_repeated_reads_correct_once_then_stop(tmp_path, repeated_tool):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Inspect the workspace")
        client = SimpleNamespace(
            get_tool=AsyncMock(return_value={"data": {"input_schema": {"type": "object"}}}),
            get_tool_context=AsyncMock(return_value={"data": {"readiness": "ready"}}),
        )
        arguments = {"command": "read status"} if repeated_tool == "exec" else {"tool_id": "scene.observe"}
        provider = ScriptedProvider([_tool_response(i, repeated_tool, arguments) for i in range(20)])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path,
                         forge_task_coordinator=c, forge_tool_client=client,
                         max_iterations=20, discovery_no_progress_limit=2)
        if repeated_tool == "exec":
            loop.tools.get("exec").execute = AsyncMock(return_value="status unchanged")
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Inspect"}], active_task_id=task.task_id,
        )
        assert result.turn_failure_code == "discovery_no_progress"
        assert len(provider.requests) == (4 if repeated_tool == "exec" else 5)
        assert sum(m.get("role") == "system" and "Discovery has made no Coordinator progress" in
                   m.get("content", "") for m in result.messages) == 1
        assert c.get_task(task.task_id).execution_records == []
        assert c.get_task(task.task_id).active_revision.plan_graph is None
    asyncio.run(exercise())


def test_discovery_stale_scene_lineage_corrects_once_then_stops_without_refresh(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Bind the current scene")
        provider = ScriptedProvider([
            _tool_response(0, "forge_tool_query", {
                "task_id": task.task_id,
                "tool_id": "scene.bind",
                "arguments": {"entity_refs": ["entity://seen"]},
            }),
            _tool_response(1, "forge_tool_query", {
                "task_id": task.task_id,
                "tool_id": "scene.bind",
                "arguments": {"entity_refs": ["entity://seen"]},
            }),
        ])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path,
            forge_task_coordinator=c, max_iterations=4, discovery_no_progress_limit=6,
        )
        stale = json.dumps({
            "ok": True,
            "data": {
                "status": "unavailable",
                "motion_authorized": False,
                "error": {
                    "code": "scene_revision_mismatch",
                    "failure_stage": "current_scene",
                    "retryable": True,
                    "retryable_in_revision": False,
                    "requires_replan": True,
                    "recommended_action": "refresh_declared_evidence",
                    "expected_scene_revision": "scene-1",
                    "actual_scene_revision": "scene-3",
                },
            },
        })
        loop.tools.execute = AsyncMock(return_value=stale)

        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Bind the current scene"}],
            active_task_id=task.task_id,
        )

        assert result.turn_failure_code == "scene_lineage_no_progress"
        assert len(provider.requests) == 2
        assert result.tools_used == ["forge_tool_query", "forge_tool_query"]
        assert all(
            call.args[1]["tool_id"] == "scene.bind"
            for call in loop.tools.execute.await_args_list
        )
        assert "no Tool or Action was automatically dispatched" in result.content
        assert sum(
            message.get("role") == "system"
            and "declared scene lineage is stale" in message.get("content", "")
            for message in result.messages
        ) == 1
        correction = next(
            message for message in result.messages
            if message.get("role") == "system"
            and "declared scene lineage is stale" in message.get("content", "")
        )
        assert "this operation" in correction["content"]
        assert "dependent operation" in correction["content"]

    asyncio.run(exercise())


def test_stale_scene_lineage_persists_across_bounded_agent_turns(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Resume the current scene binding")
        stale_response = {
            "data": {
                "status": "unavailable",
                "error": {
                    "code": "scene_revision_mismatch",
                    "expected_scene_revision": "scene-1",
                    "actual_scene_revision": "scene-3",
                },
            },
        }

        def persist_stale(current):
            current.active_revision.execution_records.append(ToolExecutionRecord(
                record_id="stale-record",
                revision_id=current.active_revision_id,
                tool_id="scene.bind",
                semantics="query",
                caller_id="fixture",
                arguments={"entity_refs": ["entity://seen"]},
                status="succeeded",
                response=stale_response,
            ))

        c.store.update(task.task_id, persist_stale, event_type="test_stale_lineage")
        provider = ScriptedProvider([_tool_response(0, "forge_tool_query", {
            "task_id": task.task_id,
            "tool_id": "scene.bind",
            "arguments": {"entity_refs": ["entity://seen"]},
        })])
        loop = AgentLoop(
            bus=MessageBus(), provider=provider, workspace=tmp_path,
            forge_task_coordinator=c, max_iterations=2,
        )
        result_payload = json.dumps({"ok": True, "data": stale_response["data"]})
        loop.tools.execute = AsyncMock(return_value=result_payload)

        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Resume the current scene binding"}],
            active_task_id=task.task_id,
        )

        assert result.turn_failure_code == "scene_lineage_no_progress"
        assert len(provider.requests) == 1
        assert "same stale scene lineage" in result.content

    asyncio.run(exercise())


def test_discovery_correction_leaves_next_query_to_model_and_recovers(tmp_path):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Inspect")
        client = SimpleNamespace(invoke_query_tool=AsyncMock(return_value={
            "ok": True, "data": {"status": "available", "scene_revision": "fixture-scene"},
        }))
        c.client = client
        c._require_binding_tool = AsyncMock(return_value=task.primary_skill_binding.required_tools[0])
        provider = ScriptedProvider([
            _tool_response(0, "exec", {"command": "read status"}),
            _tool_response(1, "exec", {"command": "read status"}),
            _tool_response(2, "forge_tool_query", {
                "task_id": task.task_id, "tool_id": "scene.observe", "arguments": {},
            }),
        ])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path,
                         forge_task_coordinator=c, forge_tool_client=client,
                         max_iterations=10, discovery_no_progress_limit=2)
        loop.tools.get("exec").execute = AsyncMock(return_value="unchanged")
        result = await loop._run_agent_loop(
            [{"role": "user", "content": "Inspect"}], active_task_id=task.task_id,
            yield_after_tools=frozenset({"forge_tool_query"}),
        )
        assert result.turn_failure_code is None
        assert len(provider.requests) == 3
        assert "Discovery has made no Coordinator progress" in json.dumps(provider.requests[2]["messages"])
        assert result.tools_used == ["exec", "exec", "forge_tool_query"]
        assert client.invoke_query_tool.await_count == 1
        assert c.get_task(task.task_id).execution_records[0].status == "succeeded"
    asyncio.run(exercise())


@pytest.mark.parametrize("system_turn", [False, True])
@pytest.mark.parametrize("failure", ["tool_iteration_limit", "discovery_no_progress"])
def test_iteration_exhaustion_settles_both_entrypoints(tmp_path, system_turn, failure):
    async def exercise():
        c, task = setup_task(tmp_path, goal="Inspect", origin_session_key="cli:budget")
        provider = ScriptedProvider([
            _tool_response(i, "exec", {"command": "read status"}) for i in range(20)
        ])
        loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path,
                         forge_task_coordinator=c,
                         max_iterations=1 if failure == "tool_iteration_limit" else 20,
                         discovery_no_progress_limit=2)
        loop.tools.get("exec").execute = AsyncMock(return_value="unchanged")
        if system_turn:
            from PhyAgentOS.bus.events import InboundMessage
            await loop._process_message(InboundMessage(
                channel="system", sender_id="fixture", chat_id="cli:budget", content="Inspect",
            ))
        else:
            await loop.process_direct("Inspect", session_key="cli:budget")
        current = c.get_task(task.task_id)
        assert current.status == AgentTaskStatus.FAILED
        assert failure in current.evidence_errors[-1]
        assert current.execution_records == []
    asyncio.run(exercise())


@pytest.mark.parametrize("recovery_state", [
    "pending", "unknown", "awaiting_replan", "waiting_for_user", "cancelling",
])
def test_loop_failure_convergence_preserves_owned_recovery(tmp_path, recovery_state):
    c, task = setup_task(tmp_path, origin_session_key="cli:recovery")
    if recovery_state == "awaiting_replan":
        c.record_planning_node_blocked(task.task_id, task.active_revision_id, "fixture", "repair")
    elif recovery_state == "waiting_for_user":
        c.request_clarification(task.task_id, question="Provide the missing capability")
    elif recovery_state == "cancelling":
        c.store.update(task.task_id, lambda t: setattr(t, "status", AgentTaskStatus.CANCELLING),
                       event_type="fixture_cancelling")
    else:
        c.store.update(task.task_id, lambda t: t.active_revision.execution_records.append(
            ToolExecutionRecord(
                record_id="owned", revision_id=t.active_revision_id, tool_id="object.place",
                semantics="action", caller_id="fixture", invocation_id="original-invocation",
                status="accepted" if recovery_state == "pending" else "unknown",
            )), event_type="fixture_owned_execution")
    before = c.get_task(task.task_id).status
    loop = AgentLoop(bus=MessageBus(), provider=ScriptedProvider(), workspace=tmp_path,
                     forge_task_coordinator=c)
    loop._settle_turn_failure(AgentLoopRunResult(
        content="Stopped", tools_used=[], messages=[], turn_failure_code="tool_iteration_limit",
    ), "cli:recovery")
    assert c.get_task(task.task_id).status == before


def test_semantic_submission_rejects_untrusted_predecessor_effect_condition(tmp_path):
    _c, task = setup_task(tmp_path)
    nodes = semantic_nodes(1)
    nodes[0]["effects"] = ["candidates_available"]
    nodes[1]["dependencies"] = [nodes[0]["node_id"]]
    nodes[1]["conditions"] = ["candidates_available"]
    with pytest.raises(ValueError, match="descriptive effects are not trusted"):
        compile_task_plan(task, nodes, reason="effect is not fact", initial_condition_facts={})
    assert nodes[1]["conditions"] == ["candidates_available"]
    graph = compile_task_plan(task, nodes, reason="trusted fact", initial_condition_facts={"candidates_available": True})
    assert graph.nodes[1].conditions == ("candidates_available",)
