from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.agent.prompt_context import (
    AgentPromptContextManager,
    PromptBudgetExceededError,
    compact_tool_result,
    node_task_prompt_projection,
    task_prompt_projection,
    visible_tool_names,
)
from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.agent.tools.forge_task import ForgeTaskCreateTool, ForgeTaskFinalizeTool
from PhyAgentOS.agent.tools.registry import ToolRegistry
from PhyAgentOS.bus.queue import MessageBus
from PhyAgentOS.config.schema import AgentDefaults, ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec, ForgeSkillBinding, required_preplan_queries
from PhyAgentOS.forge.task import (
    AgentTaskCoordinator,
    TaskNotReadyForFinalizationError,
)
from PhyAgentOS.planning import ToolSpecPolicy
from PhyAgentOS.providers.base import LLMProvider, LLMResponse
from PhyAgentOS.verification.contracts import TaskVerificationContract


class _NamedTool(Tool):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._name

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> str:
        return "ok"


class _Provider(LLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.requests = []

    async def chat(self, **kwargs):
        self.requests.append(kwargs)
        return LLMResponse(content="done")

    def get_default_model(self) -> str:
        return "fixture-model"


def _task(*, graph=None, records=(), status="executing", settlements=()):
    return SimpleNamespace(
        task_id="task-rgb",
        status=SimpleNamespace(value=status),
        terminal=status in {"succeeded", "failed", "cancelled"},
        origin_session_key="cli:test",
        task_description="Arrange RGB blocks",
        active_revision_id="revision-1",
        active_revision=SimpleNamespace(
            revision_id="revision-1",
            number=1,
            reason="initial plan",
            counts_toward_replan_budget=True,
            skill_binding_id="skill-binding-1",
            runtime_binding_id="runtime-binding-1",
            skill_use_ids=("skill-use-1",),
            plan_graph=graph,
            plan_graph_ref="artifact://plans/revision-1" if graph is not None else None,
            plan_graph_digest="plan-digest" if graph is not None else None,
            planner_decision_digest="planner-digest" if graph is not None else None,
            policy_snapshot_digest="policy-digest" if graph is not None else None,
            node_settlements=settlements,
            preserved_node_ids=(),
            invalidated_node_ids=(),
            retry_parent_node_id=None,
            fresh_evidence_requirements=(),
            discovery_evidence_refs=("tool:discovery-1",),
            replan_evidence_refs=(),
            execution_records=list(records),
        ),
        execution_records=list(records),
        verdict=None,
        verification={"mode": "off"},
        primary_skill_binding=None,
        primary_skill_instructions="Follow the frozen workflow.",
        runtime_binding=None,
        tool_bindings=(),
        supporting_skill_bindings=(),
        skill_uses=(),
        before_snapshot_ref=None,
        after_snapshot_ref=None,
        evidence_bundle_ref=None,
        evidence_bundle_id=None,
        evidence_errors=[],
        replan_deadline=None,
        replan_extension_used=False,
        cancellation_requested=False,
        pause_requested=False,
    )


def _estimate(messages, names):
    return sum(len(str(message.get("content", ""))) for message in messages) + 10 * len(names)


def test_agent_loop_selects_task_from_current_session_not_global_active():
    session_task = SimpleNamespace(task_id="task-session", terminal=False)
    other_task = SimpleNamespace(task_id="task-other", terminal=False)

    class Store:
        def find_by_origin_session_key(self, key):
            return [session_task] if key == "cli:session" else [other_task]

    loop = object.__new__(AgentLoop)
    loop.forge_task_coordinator = SimpleNamespace(store=Store())

    assert loop._task_for_session("cli:session") is session_task


def test_agent_loop_does_not_fallback_to_unbound_legacy_active_task():
    legacy_task = SimpleNamespace(task_id="task-legacy", terminal=False, origin_session_key=None)

    class Store:
        def find_by_origin_session_key(self, _key):
            return []

        def active(self):
            return legacy_task

    loop = object.__new__(AgentLoop)
    loop.forge_task_coordinator = SimpleNamespace(store=Store())
    loop.sessions = SimpleNamespace(
        get_or_create=lambda _key: SimpleNamespace(get_history=lambda **_kwargs: [])
    )

    assert loop._task_for_session("cli:new") is None


def test_agent_loop_resumes_legacy_task_explicitly_referenced_by_session():
    legacy_task = SimpleNamespace(task_id="task-legacy", terminal=False, origin_session_key=None)

    class Store:
        def find_by_origin_session_key(self, _key):
            return []

        def get(self, task_id):
            assert task_id == legacy_task.task_id
            return legacy_task

    history = [{
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "read-task",
            "type": "function",
            "function": {
                "name": "forge_task_get",
                "arguments": json.dumps({"task_id": legacy_task.task_id}),
            },
        }],
    }]
    loop = object.__new__(AgentLoop)
    loop.forge_task_coordinator = SimpleNamespace(store=Store())
    loop.sessions = SimpleNamespace(
        get_or_create=lambda _key: SimpleNamespace(get_history=lambda **_kwargs: history)
    )

    assert loop._task_for_session("cli:retained") is legacy_task


def test_agent_loop_does_not_bind_legacy_task_from_plain_text_reference():
    class Store:
        def find_by_origin_session_key(self, _key):
            return []

        def get(self, _task_id):
            raise AssertionError("plain text must not be treated as a task binding")

    history = [{"role": "user", "content": "Continue task-legacy"}]
    loop = object.__new__(AgentLoop)
    loop.forge_task_coordinator = SimpleNamespace(store=Store())
    loop.sessions = SimpleNamespace(
        get_or_create=lambda _key: SimpleNamespace(get_history=lambda **_kwargs: history)
    )

    assert loop._task_for_session("cli:new") is None


def test_agent_loop_does_not_resume_terminal_legacy_task_for_stop_path():
    legacy_task = SimpleNamespace(task_id="task-legacy", terminal=True, origin_session_key=None)

    class Store:
        def find_by_origin_session_key(self, _key):
            return []

        def get(self, _task_id):
            return legacy_task

    history = [{
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "read-task",
            "type": "function",
            "function": {
                "name": "forge_task_get",
                "arguments": {"task_id": legacy_task.task_id},
            },
        }],
    }]
    loop = object.__new__(AgentLoop)
    loop.forge_task_coordinator = SimpleNamespace(store=Store())
    loop.sessions = SimpleNamespace(
        get_or_create=lambda _key: SimpleNamespace(get_history=lambda **_kwargs: history)
    )

    assert loop._task_for_session("cli:retained", include_terminal=False) is None
    assert loop._task_for_session("cli:retained", include_terminal=True) is legacy_task


def test_task_create_rejects_placeholder_noop_description():
    coordinator = SimpleNamespace(create_task=lambda **_kwargs: None)
    tool = ForgeTaskCreateTool(coordinator)
    with pytest.raises(ValueError, match="executable user task"):
        asyncio.run(tool.execute(
            "noop",
            TaskVerificationContract(mode="off").model_dump(mode="json"),
        ))


def test_agent_defaults_use_272k_window_and_260k_trigger() -> None:
    defaults = AgentDefaults()
    assert defaults.context_window_tokens == 272_000
    assert defaults.context_compaction_trigger_tokens == 260_000

    legacy = AgentDefaults(contextWindowTokens=65_536)
    assert legacy.context_compaction_trigger_tokens == int(65_536 * 0.95)

    with pytest.raises(ValueError, match="must be smaller"):
        AgentDefaults(contextWindowTokens=100, contextCompactionTriggerTokens=100)


def test_registry_filters_model_visibility_without_unregistering_execution() -> None:
    registry = ToolRegistry()
    registry.register(_NamedTool("one"))
    registry.register(_NamedTool("two"))
    assert [item["function"]["name"] for item in registry.get_definitions({"two"})] == ["two"]
    assert registry.has("one") and registry.has("two")
    assert asyncio.run(registry.execute("one", {})) == "ok"


def test_visible_forge_tools_follow_task_phase() -> None:
    names = (
        "read_file",
        "activate_skill",
        "forge_task_create",
        "forge_task_get",
        "forge_task_begin_revision",
        "forge_task_materialize_plan",
        "forge_task_continue_plan",
        "forge_task_finalize",
        "forge_tool_context",
        "forge_tool_query",
        "forge_plan_activate",
        "forge_plan_ready",
        "forge_plan_select",
        "forge_tool_start_action",
        "forge_tool_action_status",
        "forge_tool_action_result",
        "forge_tool_cancel_action",
        "forge_tool_start_session",
        "forge_tool_session_status",
        "forge_tool_session_result",
        "forge_tool_stop_session",
    )
    creation = visible_tool_names(names, None)
    assert "forge_task_create" in creation
    assert "forge_tool_query" in creation
    assert "forge_tool_start_action" not in creation

    discovery = visible_tool_names(names, _task())
    assert "forge_tool_query" in discovery
    assert "forge_task_materialize_plan" in discovery
    assert "forge_tool_start_action" not in discovery

    completed = (
        SimpleNamespace(tool_id="scene.observe", status="succeeded"),
        SimpleNamespace(tool_id="scene.understand", status="succeeded"),
    )
    ready_discovery = visible_tool_names(names, _task(records=completed))
    assert "forge_task_materialize_plan" in ready_discovery

    graph = SimpleNamespace(nodes=())
    planning = visible_tool_names(names, _task(graph=graph))
    assert {"forge_plan_activate", "forge_plan_ready", "forge_plan_select"} <= set(planning)
    assert "forge_tool_start_action" in planning
    assert "forge_task_begin_revision" not in planning
    assert "forge_task_continue_plan" not in planning

    completed_graph = SimpleNamespace(nodes=(SimpleNamespace(node_id="done"),))
    completed_settlement = SimpleNamespace(node_id="done", status="completed")
    continuation = visible_tool_names(
        names,
        _task(graph=completed_graph, settlements=(completed_settlement,)),
    )
    assert "forge_task_continue_plan" in continuation

    pending = SimpleNamespace(status="running", semantics="action")
    reconcile = visible_tool_names(names, _task(graph=graph, records=(pending,)))
    assert {
        "forge_tool_action_status",
        "forge_tool_action_result",
        "forge_tool_cancel_action",
    } <= set(reconcile)
    assert "forge_tool_start_action" not in reconcile

    awaiting = visible_tool_names(names, _task(graph=graph, status="awaiting_replan"))
    assert "forge_task_begin_revision" in awaiting
    assert "forge_tool_start_action" not in awaiting

    paused_task = _task(graph=graph)
    paused_task.pause_requested = True
    paused = visible_tool_names(names, paused_task)
    assert "forge_tool_start_action" not in paused

    cancelling = visible_tool_names(names, _task(graph=graph, status="cancelling"))
    assert "forge_tool_start_action" not in cancelling
    assert "forge_tool_start_session" not in cancelling
    assert "forge_tool_action_status" in cancelling

    waiting = _task(graph=graph, status="waiting_for_user")
    waiting_tools = visible_tool_names(names, waiting)
    assert "forge_tool_context" in waiting_tools
    assert "forge_tool_query" not in waiting_tools
    assert AgentPromptContextManager.phase(waiting) == "waiting_for_user"


def test_finalize_tool_returns_recoverable_structured_error() -> None:
    class Coordinator:
        async def finalize_task(self, task_id: str):
            raise TaskNotReadyForFinalizationError(
                "cannot finalize while active PlanGraph has incomplete node settlements: observe",
                reason="incomplete_plan",
            )

    payload = json.loads(asyncio.run(ForgeTaskFinalizeTool(Coordinator()).execute("task-rgb")))
    assert payload["ok"] is False
    assert payload["error"]["code"] == "task_not_ready_for_finalization"
    assert payload["error"]["reason"] == "incomplete_plan"
    assert payload["motion_authorized"] is False


def test_discovery_visibility_uses_skill_declared_prerequisites() -> None:
    names = ("forge_task_materialize_plan", "forge_tool_query", "forge_tool_context")
    task = _task()
    policy = ToolSpecPolicy(
        tool_id="inspect.scene", semantics="query", spec_digest="a" * 64,
        requires_before_plan=True,
    )
    task.primary_skill_binding = ForgeSkillBinding(
        binding_id="binding-1", skill_name="fixture", skill_version="1",
        manifest_sha256="b" * 64, skill_document_sha256="c" * 64,
        runtime_profile="fixture", runtime_instance_id="runtime-1",
        gateway_url="http://fixture", required_tools=(
            BoundToolSpec(tool_id="inspect.scene", semantics="query", spec_sha256="d" * 64,
                          ready_at_binding=True, planning_policy=policy),
        ),
    )
    assert "forge_task_materialize_plan" not in visible_tool_names(names, task)
    task.active_revision.execution_records = [
        SimpleNamespace(tool_id="inspect.scene", status="succeeded")
    ]
    assert "forge_task_materialize_plan" in visible_tool_names(names, task)
    task.active_revision.execution_records = []
    assert "forge_task_materialize_plan" not in visible_tool_names(names, task)

    task.primary_skill_binding = None
    task.tool_bindings = (BoundToolSpec(
        tool_id="inspect.scene", semantics="query", spec_sha256="d" * 64,
        ready_at_binding=True, planning_policy=policy,
    ),)
    assert required_preplan_queries(task) == frozenset({"inspect.scene"})


def test_discovery_visibility_does_not_count_provider_failure_as_success() -> None:
    names = ("forge_task_materialize_plan", "forge_tool_query", "forge_tool_context")
    task = _task()
    policy = ToolSpecPolicy(
        tool_id="inspect.scene", semantics="query", spec_digest="a" * 64,
        requires_before_plan=True,
    )
    task.primary_skill_binding = ForgeSkillBinding(
        binding_id="binding-1", skill_name="fixture", skill_version="1",
        manifest_sha256="b" * 64, skill_document_sha256="c" * 64,
        runtime_profile="fixture", runtime_instance_id="runtime-1",
        gateway_url="http://fixture", required_tools=(
            BoundToolSpec(tool_id="inspect.scene", semantics="query", spec_sha256="d" * 64,
                          ready_at_binding=True, planning_policy=policy),
        ),
    )
    task.active_revision.execution_records = [SimpleNamespace(
        tool_id="inspect.scene", status="succeeded",
        response={"status": "unavailable"},
    )]
    assert "forge_task_materialize_plan" not in visible_tool_names(names, task)


def test_compaction_preserves_visual_and_execution_references() -> None:
    content = json.dumps(
        {
            "ok": True,
            "data": {
                "status": "available",
                "observation_ref": "observation://scene/head",
                "scene_revision": "scene-2",
                "calibration_ref": "artifact://scene/calibration",
                "entities": [
                    {
                        "entity_ref": "entity://block-red",
                        "category": "block",
                        "world_T_object": list(range(16)),
                    }
                ],
                "object_geometry": [
                    {"entity_ref": "entity://block-red", "extent": [0.04, 0.04, 0.04]}
                ],
                "tool": {
                    "tool_id": "scene.bind",
                    "input_schema": {
                        "type": "object",
                        "properties": {"entity_refs": {"type": "array"}},
                        "required": ["entity_refs"],
                    },
                },
                "irrelevant_provider_debug": "x" * 5_000,
            },
            "paos_record": {
                "task_id": "task-rgb",
                "revision_id": "revision-1",
                "record_id": "record-1",
                "evidence_refs": ["tool:record-1"],
            },
        }
    )
    summary = json.loads(compact_tool_result("forge_tool_query", content))
    encoded = json.dumps(summary)
    assert "observation://scene/head" in encoded
    assert "entity://block-red" in encoded
    assert "world_T_object" in encoded
    assert "input_schema" in encoded
    assert "properties" in encoded
    assert "tool:record-1" in encoded
    assert "irrelevant_provider_debug" not in encoded


def test_prompt_budget_rebuilds_from_current_turn_and_task_projection() -> None:
    record = SimpleNamespace(
        record_id="record-1",
        revision_id="revision-1",
        tool_id="scene.understand",
        semantics="query",
        status="succeeded",
        node_id=None,
        invocation_id=None,
        attempt_id=None,
        evidence_refs=["tool:record-1"],
        arguments={"observation_ref": "observation://scene/head"},
        response={
            "data": {
                "status": "available",
                "scene_revision": "scene-2",
                "entities": [{"entity_ref": "entity://block-red"}],
            }
        },
        error=None,
    )
    task = _task(records=(record,))
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "old" * 400},
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "arrange RGB"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1"}]},
        {
            "role": "tool",
            "name": "forge_tool_query",
            "tool_call_id": "c1",
            "content": json.dumps(
                {
                    "ok": True,
                    "data": {
                        "scene_revision": "scene-2",
                        "evidence_refs": ["tool:record-1"],
                        "debug": "z" * 2_000,
                    },
                }
            ),
        },
    ]
    manager = AgentPromptContextManager(
        context_window_tokens=3_000, compaction_trigger_tokens=2_000
    )
    view = manager.build(
        messages=messages,
        turn_start_index=3,
        all_tool_names=(
            "read_file",
            "forge_task_get",
            "forge_tool_query",
            "forge_task_materialize_plan",
        ),
        task=task,
        estimate_tokens=_estimate,
    )
    encoded = json.dumps(view.messages)
    assert view.compacted is True
    assert "oldoldold" not in encoded
    assert "arrange RGB" in encoded
    assert "task-rgb" in encoded
    assert "entity://block-red" in encoded
    assert "tool:record-1" in encoded


def test_superseded_forge_results_compact_before_global_trigger() -> None:
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "inspect contexts"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "old"}]},
        {
            "role": "tool",
            "name": "forge_tool_context",
            "tool_call_id": "old",
            "content": json.dumps(
                {
                    "ok": True,
                    "data": {
                        "tool": {
                            "tool_id": "scene.observe",
                            "input_schema": {"type": "object"},
                            "irrelevant_provider_debug": "x" * 2_000,
                        }
                    },
                }
            ),
        },
        {"role": "assistant", "content": None, "tool_calls": [{"id": "new"}]},
        {
            "role": "tool",
            "name": "forge_tool_context",
            "tool_call_id": "new",
            "content": json.dumps(
                {
                    "ok": True,
                    "data": {
                        "tool": {
                            "tool_id": "scene.bind",
                            "input_schema": {"type": "object"},
                            "marker": "latest-full-result",
                        }
                    },
                }
            ),
        },
    ]
    manager = AgentPromptContextManager(
        context_window_tokens=20_000,
        compaction_trigger_tokens=18_000,
    )
    view = manager.build(
        messages=messages,
        turn_start_index=1,
        all_tool_names=("forge_tool_context",),
        task=None,
        estimate_tokens=_estimate,
    )
    assert "agent_tool_result_summary_v1" in view.messages[3]["content"]
    assert "irrelevant_provider_debug" not in view.messages[3]["content"]
    assert "latest-full-result" in view.messages[5]["content"]


def test_prompt_budget_fails_locally_when_current_required_input_exceeds_window() -> None:
    manager = AgentPromptContextManager(context_window_tokens=100, compaction_trigger_tokens=80)
    with pytest.raises(PromptBudgetExceededError, match="exceeds context window"):
        manager.build(
            messages=[
                {"role": "system", "content": "s" * 60},
                {"role": "user", "content": "u" * 60},
            ],
            turn_start_index=1,
            all_tool_names=(),
            task=None,
            estimate_tokens=_estimate,
        )


def test_prompt_budget_reserves_configured_response_tokens() -> None:
    manager = AgentPromptContextManager(
        context_window_tokens=100,
        compaction_trigger_tokens=95,
        reserved_output_tokens=20,
    )
    assert manager.prompt_token_limit == 80
    with pytest.raises(PromptBudgetExceededError, match="reserved output 20"):
        manager.build(
            messages=[{"role": "user", "content": "u" * 85}],
            turn_start_index=0,
            all_tool_names=(),
            task=None,
            estimate_tokens=_estimate,
        )


def test_agent_loop_sends_phase_scoped_tools_and_fresh_task_projection(tmp_path) -> None:
    async def exercise() -> None:
        coordinator = AgentTaskCoordinator(
            workspace=tmp_path,
            config=ForgeConfig(),
            client=object(),
        )
        task = coordinator.create_task(
            task_description="Arrange RGB blocks",
            verification=TaskVerificationContract(mode="off"),
            origin_session_key="cli:test",
        )
        provider = _Provider()
        loop = AgentLoop(
            bus=MessageBus(),
            provider=provider,
            workspace=tmp_path,
            forge_task_coordinator=coordinator,
            max_iterations=1,
        )
        result, _, _ = await loop._run_agent_loop(
            [{"role": "system", "content": "system"}, {"role": "user", "content": "continue"}],
            experience_session_key="cli:test",
        )
        assert result == "done"
        request = provider.requests[0]
        tool_names = {item["function"]["name"] for item in request["tools"]}
        assert "forge_task_materialize_plan" in tool_names
        assert "forge_tool_start_action" not in tool_names
        sent = json.dumps(request["messages"])
        assert task.task_id in sent
        assert "read_only_projection_from_AgentTaskCoordinator" in sent

    asyncio.run(exercise())


def test_task_projection_preserves_all_action_invocation_identities() -> None:
    records = [
        SimpleNamespace(
            record_id=f"record-{index}",
            revision_id="revision-1",
            tool_id="object.place",
            semantics="action",
            status="succeeded",
            skill_binding_id="skill-binding-1",
            runtime_binding_id="runtime-binding-1",
            skill_use_ids=("skill-use-1",),
            tool_spec_sha256=f"tool-spec-{index}",
            caller_id="agent:test",
            node_id=f"node-{index}",
            node_digest=f"node-digest-{index}",
            obligation_id=f"obligation-{index}",
            input_binding_digest=f"input-digest-{index}",
            decision_trace_ref=f"artifact://decision/{index}",
            ownership="runtime",
            invocation_id=f"invocation-{index}",
            attempt_id=f"attempt-{index}",
            evidence_refs=[f"artifact://evidence/{index}"],
            arguments={},
            response={},
            error=None,
        )
        for index in range(3)
    ]
    encoded = json.dumps(
        task_prompt_projection(_task(graph=SimpleNamespace(nodes=()), records=records))
    )
    for index in range(3):
        assert f"invocation-{index}" in encoded
        assert f"artifact://evidence/{index}" in encoded
        assert f"artifact://decision/{index}" in encoded
        assert f"input-digest-{index}" in encoded


def test_task_projection_preserves_revision_bindings_and_node_obligations() -> None:
    node = SimpleNamespace(
        node_id="node-place",
        obligation_id="place-red-left",
        capability="object.place",
        dependencies=("node-acquire",),
        conditions=("scene.current",),
        required_evidence=("binding.current", "preparation.accepted"),
        produced_evidence=("placement.terminal",),
        resources=({"resource_id": "left_arm", "access": "exclusive"},),
        effects=("scene.changed",),
        input_bindings={
            "entity_ref": "entity://red",
            "preparation_ref": "artifact://preparation/red",
        },
        retry_of=None,
    )
    task = _task(graph=SimpleNamespace(nodes=(node,)))
    task.primary_skill_binding = {
        "binding_id": "skill-binding-1",
        "skill_name": "pick-place-workflow",
        "skill_version": "2.0.2",
        "required_tools": ({
            "tool_id": "object.place",
            "semantics": "action",
            "input_schema": {"type": "object"},
        },),
    }
    task.runtime_binding = {
        "binding_id": "runtime-binding-1",
        "runtime_profile": "robotwin-persistent",
        "runtime_instance_id": "runtime-1",
    }
    task.tool_bindings = (
        {
            "tool_id": "object.place",
            "semantics": "action",
            "spec_sha256": "tool-spec-place",
            "ready_at_binding": True,
            "input_schema": {"type": "object"},
        },
    )
    task.skill_uses = (
        SimpleNamespace(
            use_id="skill-use-1",
            activation_id="activation-1",
            skill_name="pick-place-workflow",
            skill_version="2.0.2",
            content_sha256="skill-content",
            decision_ref="artifact://decision/skill-use-1",
            node_id="node-place",
            attempt_id=None,
            outcome="selected",
        ),
    )

    encoded = json.dumps(task_prompt_projection(task))
    assert "input_schema" not in encoded
    for required in (
        "Follow the frozen workflow.",
        "skill-binding-1",
        "runtime-binding-1",
        "artifact://plans/revision-1",
        "tool:discovery-1",
        "place-red-left",
        "binding.current",
        "placement.terminal",
        "artifact://preparation/red",
        "left_arm",
        "scene.changed",
        "artifact://decision/skill-use-1",
    ):
        assert required in encoded


def test_node_projection_is_reference_only_and_scoped_to_current_node() -> None:
    current = SimpleNamespace(
        node_id="node-place",
        obligation_id="place-red-left",
        capability="object.place",
        dependencies=("node-acquire",),
        conditions=("scene.current",),
        required_evidence=("binding.current",),
        input_bindings={"entity_ref": "entity://red"},
        resources=(),
        effects=("scene.changed",),
        retry_of=None,
    )
    unrelated = SimpleNamespace(
        node_id="node-blue",
        obligation_id="place-blue-right",
        capability="object.place",
        dependencies=(),
        conditions=(),
        required_evidence=(),
        input_bindings={"entity_ref": "entity://blue"},
        resources=(),
        effects=(),
        retry_of=None,
    )
    task = _task(graph=SimpleNamespace(nodes=(current, unrelated)))
    task.primary_skill_binding = SimpleNamespace(
        binding_id="skill-binding-1",
        skill_name="pick-place-workflow",
        skill_version="2.2.0",
        skill_document_sha256="b" * 64,
        runtime_profile="robotwin-persistent",
        runtime_instance_id="runtime-1",
        gateway_identity="gateway-1",
        required_tools=(),
    )
    task.skill_uses = (
        SimpleNamespace(
            use_id="skill-use-current",
            activation_id="activation-1",
            skill_name="pick-place-workflow",
            skill_version="2.2.0",
            content_sha256="b" * 64,
            instructions="CURRENT FULL INSTRUCTIONS MUST NOT BE COPIED",
            decision_ref="node:revision-1:node-place",
            node_id="node-place",
            attempt_id=None,
            outcome="selected",
        ),
        SimpleNamespace(
            use_id="skill-use-unrelated",
            activation_id="activation-1",
            skill_name="pick-place-workflow",
            skill_version="2.2.0",
            content_sha256="b" * 64,
            instructions="UNRELATED FULL INSTRUCTIONS MUST NOT BE COPIED",
            decision_ref="node:revision-1:node-blue",
            node_id="node-blue",
            attempt_id=None,
            outcome="selected",
        ),
    )

    encoded = json.dumps(node_task_prompt_projection(task, "node-place"))

    assert "agent_node_prompt_projection_v1" in encoded
    assert "skill-use-current" in encoded
    assert "skill-use-unrelated" not in encoded
    assert "place-red-left" in encoded
    assert "place-blue-right" not in encoded
    assert "FULL INSTRUCTIONS" not in encoded
    assert "primary_skill_instructions" not in encoded


def test_node_projection_scope_requires_node_identity() -> None:
    manager = AgentPromptContextManager(
        context_window_tokens=20_000,
        compaction_trigger_tokens=18_000,
    )

    with pytest.raises(ValueError, match="requires projection_node_id"):
        manager.build(
            messages=[{"role": "user", "content": "continue"}],
            turn_start_index=0,
            all_tool_names=(),
            task=_task(),
            estimate_tokens=_estimate,
            projection_scope="node",
        )


def test_task_projection_does_not_report_compaction_by_itself() -> None:
    manager = AgentPromptContextManager(
        context_window_tokens=20_000,
        compaction_trigger_tokens=18_000,
    )
    view = manager.build(
        messages=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": "continue"},
        ],
        turn_start_index=1,
        all_tool_names=("forge_task_get", "forge_tool_query"),
        task=_task(),
        estimate_tokens=_estimate,
    )
    assert view.compacted is False
    assert "read_only_projection_from_AgentTaskCoordinator" in json.dumps(view.messages)
