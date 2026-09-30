from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.prompt_context import visible_tool_names
from PhyAgentOS.agent.tools.forge_task import (
    ForgeTaskRebindRuntimeTool,
    build_forge_task_tools,
)
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import ForgeSkillBinding
from PhyAgentOS.forge.task import (
    AgentTaskCoordinator,
    AgentTaskError,
    ToolExecutionRecord,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract
from PhyAgentOS.verification.request_builder import VerificationRequestBuilder


def _binding(binding_id: str, runtime: str, version: str) -> ForgeSkillBinding:
    return ForgeSkillBinding(
        binding_id=binding_id,
        skill_name="pick-place-workflow",
        skill_version=version,
        manifest_sha256="a" * 64,
        skill_document_sha256="b" * 64,
        runtime_profile="robotwin",
        runtime_instance_id=runtime,
        gateway_url="http://127.0.0.1:19020",
        required_tools=(),
    )


class _Resolver:
    def __init__(self, replacement: ForgeSkillBinding) -> None:
        self.replacement = replacement

    async def freeze(self, candidate_id: str, *, task_id: str) -> ForgeSkillBinding:
        assert candidate_id == "candidate-current"
        assert task_id
        return self.replacement


class _ActivationManager:
    activation = SimpleNamespace(
        activation_id="activation-current",
        binding_candidate_id="candidate-current",
        role="primary",
        skill_name="pick-place-workflow",
        skill_version="2.10.0",
        content_sha256="b" * 64,
    )

    def require_activation(self, *, session_key: str, activation_id: str, role: str):
        assert session_key == "cli:rgb"
        assert activation_id == self.activation.activation_id
        assert role == "primary"
        return self.activation

    def instructions_for_activation(self, *, session_key: str, activation_id: str) -> str:
        self.require_activation(
            session_key=session_key,
            activation_id=activation_id,
            role="primary",
        )
        return "Use fresh synchronized observations before planning."


def test_explicit_runtime_rebind_preserves_history_and_forces_fresh_discovery(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
    )
    task = coordinator.create_task(
        task_description="Arrange blocks",
        verification=TaskVerificationContract(mode="off"),
        origin_session_key="cli:rgb",
    )
    prior = _binding("binding-prior", "runtime-prior", "2.9.5")
    replacement = _binding("binding-current", "runtime-current", "2.10.0")

    def bind_prior(current):
        current.primary_skill_binding = prior
        current.active_revision.skill_binding_id = prior.binding_id
        current.runtime_snapshot_ref = "runtime:runtime-prior"
        current.clarification_id = "clarification-rebind"
        current.clarification_answer = "Continue on the replacement Runtime."

    coordinator.store.update(task.task_id, bind_prior, event_type="test_prior_binding")
    coordinator.binding_resolver = _Resolver(replacement)
    coordinator.activation_manager = _ActivationManager()
    coordinator.runtime_task_binding_ids = {prior.binding_id}

    rebound = asyncio.run(
        coordinator.rebind_active_runtime(
            task.task_id,
            activation_id="activation-current",
            clarification_id="clarification-rebind",
            reason="user authorized replacement Runtime",
        )
    )

    assert rebound.primary_skill_binding == replacement
    assert rebound.active_skill_instructions == (
        "Use fresh synchronized observations before planning."
    )
    assert rebound.supporting_skill_bindings == [prior]
    assert rebound.revisions[0].skill_binding_id == prior.binding_id
    assert rebound.active_revision.skill_binding_id == replacement.binding_id
    assert rebound.active_revision.discovery_evidence_refs == ()
    assert rebound.active_revision.fresh_evidence_requirements == (
        "scene.observe",
        "scene.understand",
        "manipulation.capabilities",
        "scene.bind",
    )
    assert coordinator.runtime_task_binding_ids == {replacement.binding_id}
    assert VerificationRequestBuilder._validate_agent_task_lineage(rebound) == frozenset()
    assert rebound.clarification_id is None
    assert rebound.clarification_question is None
    assert rebound.clarification_node_id is None
    assert rebound.clarification_answer is None

    persisted = coordinator.store.get(task.task_id)
    assert persisted.clarification_id is None
    assert persisted.clarification_question is None
    assert persisted.clarification_node_id is None
    assert persisted.clarification_answer is None

    names = (
        "activate_skill",
        "forge_task_get",
        "forge_task_rebind_runtime",
        "forge_tool_context",
        "forge_tool_query",
    )
    hidden = visible_tool_names(names, persisted)
    assert "activate_skill" not in hidden
    assert "forge_task_rebind_runtime" not in hidden


def test_runtime_rebind_tool_is_explicitly_exposed():
    tools = build_forge_task_tools(SimpleNamespace())
    names = [tool.name for tool in tools]
    assert "forge_task_rebind_runtime" in names
    tool = next(item for item in tools if isinstance(item, ForgeTaskRebindRuntimeTool))
    assert tool.parameters["required"] == [
        "task_id",
        "activation_id",
        "clarification_id",
        "reason",
    ]


def test_runtime_rebind_rejects_unsettled_action(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
    )
    task = coordinator.create_task(
        task_description="Arrange blocks",
        verification=TaskVerificationContract(mode="off"),
        origin_session_key="cli:rgb",
    )
    prior = _binding("binding-prior", "runtime-prior", "2.9.5")

    def add_pending_action(current):
        current.primary_skill_binding = prior
        current.active_revision.skill_binding_id = prior.binding_id
        current.clarification_id = "clarification-rebind"
        current.clarification_answer = "Continue on the replacement Runtime."
        current.active_revision.execution_records.append(
            ToolExecutionRecord(
                record_id="tool-pending",
                revision_id=current.active_revision_id,
                tool_id="object.acquire",
                semantics="action",
                skill_binding_id=prior.binding_id,
                caller_id="paos:test",
                status="running",
                invocation_id="invocation://object-acquire/pending",
            )
        )

    coordinator.store.update(
        task.task_id,
        add_pending_action,
        event_type="test_pending_action",
    )
    coordinator.binding_resolver = _Resolver(
        _binding("binding-current", "runtime-current", "2.10.0")
    )
    coordinator.activation_manager = _ActivationManager()

    with pytest.raises(AgentTaskError, match="non-terminal"):
        asyncio.run(
            coordinator.rebind_active_runtime(
                task.task_id,
                activation_id="activation-current",
                clarification_id="clarification-rebind",
                reason="unsafe migration attempt",
            )
        )


def test_runtime_rebind_requires_persisted_clarification(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
    )
    task = coordinator.create_task(
        task_description="Arrange blocks",
        verification=TaskVerificationContract(mode="off"),
        origin_session_key="cli:rgb",
    )
    prior = _binding("binding-prior", "runtime-prior", "2.9.5")
    coordinator.store.update(
        task.task_id,
        lambda current: (
            setattr(current, "primary_skill_binding", prior),
            setattr(current.active_revision, "skill_binding_id", prior.binding_id),
        ),
        event_type="test_prior_binding_without_authorization",
    )
    coordinator.binding_resolver = _Resolver(
        _binding("binding-current", "runtime-current", "2.10.0")
    )
    coordinator.activation_manager = _ActivationManager()

    with pytest.raises(AgentTaskError, match="clarification authorization"):
        asyncio.run(
            coordinator.rebind_active_runtime(
                task.task_id,
                activation_id="activation-current",
                clarification_id="missing",
                reason="unauthorized migration attempt",
            )
        )


def test_runtime_rebind_tools_are_visible_only_after_authorized_clarification(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
    )
    task = coordinator.create_task(
        task_description="Arrange blocks",
        verification=TaskVerificationContract(mode="off"),
        origin_session_key="cli:rgb",
    )
    names = (
        "activate_skill",
        "forge_task_get",
        "forge_task_rebind_runtime",
        "forge_tool_context",
        "forge_tool_query",
    )
    assert "forge_task_rebind_runtime" not in visible_tool_names(names, task)
    assert "activate_skill" not in visible_tool_names(names, task)

    authorized = task.model_copy(
        update={
            "clarification_id": "clarification-rebind",
            "clarification_answer": "Continue on the replacement Runtime.",
        }
    )
    visible = visible_tool_names(names, authorized)
    assert "activate_skill" in visible
    assert "forge_task_rebind_runtime" in visible

    in_flight = authorized.model_copy(deep=True)
    in_flight.active_revision.execution_records.append(
        ToolExecutionRecord(
            record_id="tool-pending",
            revision_id=in_flight.active_revision_id,
            tool_id="object.acquire",
            semantics="action",
            caller_id="paos:test",
            status="running",
            invocation_id="invocation://object-acquire/pending",
        )
    )
    hidden = visible_tool_names(names, in_flight)
    assert "activate_skill" not in hidden
    assert "forge_task_rebind_runtime" not in hidden
