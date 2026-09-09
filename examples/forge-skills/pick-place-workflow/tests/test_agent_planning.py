from __future__ import annotations

import pytest
from PhyAgentOS.planning import (
    AdmissionContext,
    ResourceClaim,
    ToolCallEnvelope,
    ToolSpecPolicy,
    derive_ready_nodes,
)
from pydantic import ValidationError

from pick_place_workflow.agent_planning import (
    AgentPlanningError,
    AgentSubtaskSpec,
    DynamicToolPlanner,
    ToolSelectionError,
    compose_agent_plan,
    compose_executable_pick_place_plan,
    select_planning_mode,
)


def _plan():
    return compose_agent_plan(
        "task-1",
        "revision-1",
        (
            AgentSubtaskSpec(
                subtask_id="relocate-red",
                entity_ref="entity://red-block",
                destination_ref="region://red-bin",
                required_evidence=("observation:red",),
                resources=(ResourceClaim(resource_class="arm:right"),),
            ),
            AgentSubtaskSpec(
                subtask_id="relocate-blue",
                entity_ref="entity://blue-block",
                depends_on=(),
                required_evidence=("observation:blue",),
                resources=(ResourceClaim(resource_class="arm:left"),),
            ),
        ),
        planner_decision_digest="1" * 64,
        policy_snapshot_digest="2" * 64,
    )


def _policy(tool_id: str, capability: str) -> ToolSpecPolicy:
    return ToolSpecPolicy(
        tool_id=tool_id,
        semantics="query",
        spec_digest="3" * 64,
        capabilities=(capability,),
        required_evidence=("observation:red",),
    )


def test_agent_plan_compiles_multi_entity_partial_order_and_verify_join():
    plan = _plan()
    assert plan.mode == "agent_composed"
    assert derive_ready_nodes(plan.graph, {}, {"observation:red", "observation:blue"}) == (
        "relocate-blue",
        "relocate-red",
    )
    assert plan.graph.nodes[-1].node_id == "verify"
    assert set(plan.graph.nodes[-1].dependencies) == {"relocate-red", "relocate-blue"}
    assert dict(plan.entity_bindings)["relocate-red"] == "entity://red-block"
    assert plan.graph.nodes[0].input_bindings == {"entity_ref": "entity://red-block", "destination_ref": "region://red-bin"}


def test_agent_plan_rejects_duplicate_unknown_and_invalid_bindings():
    with pytest.raises(AgentPlanningError, match="unknown subtask"):
        compose_agent_plan(
            "task-1", "revision-1",
            (AgentSubtaskSpec(subtask_id="red", entity_ref="entity://red", depends_on=("missing",)),),
            planner_decision_digest="1" * 64, policy_snapshot_digest="2" * 64,
        )
    with pytest.raises(AgentPlanningError, match="unique"):
        compose_agent_plan(
            "task-1", "revision-1",
            (AgentSubtaskSpec(subtask_id="red", entity_ref="entity://red"), AgentSubtaskSpec(subtask_id="red", entity_ref="entity://red2")),
            planner_decision_digest="1" * 64, policy_snapshot_digest="2" * 64,
        )
    with pytest.raises(ValidationError):
        AgentSubtaskSpec(subtask_id="red", entity_ref="not-an-entity")
    with pytest.raises(AgentPlanningError, match="cycle"):
        compose_agent_plan(
            "task-1", "revision-1",
            (
                AgentSubtaskSpec(subtask_id="red", entity_ref="entity://red", depends_on=("blue",)),
                AgentSubtaskSpec(subtask_id="blue", entity_ref="entity://blue", depends_on=("red",)),
            ),
            planner_decision_digest="1" * 64, policy_snapshot_digest="2" * 64,
        )


def test_dynamic_planner_selects_alternative_tools_and_admits_without_execution():
    plan = _plan()
    planner = DynamicToolPlanner(
        plan,
        (
            _policy("understand.rgb", "object.relocate"),
            _policy("understand.depth", "object.relocate"),
        ),
    )
    assert planner.candidate_tools("relocate-red") == ("understand.rgb", "understand.depth")
    call = ToolCallEnvelope(
        task_id="task-1", revision_id="revision-1", node_id="relocate-red",
        tool_id="understand.depth", tool_spec_digest="3" * 64,
        input_binding_digest="4" * 64, scene_revision="scene-1",
        idempotency_key="idem-1", semantics="query",
    )
    decision = planner.admit(call, AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset({"observation:red"})))
    assert decision.allowed is True
    assert decision.motion_authorized is False
    assert planner.admit(call, AdmissionContext(scene_revision="scene-2", evidence_refs=frozenset({"observation:red"}))).code == "stale_scene"
    assert planner.admit(call, AdmissionContext(scene_revision="scene-1")).code == "node_not_ready"
    with pytest.raises(ToolSelectionError):
        planner.candidate_tools("missing")
    rejected = planner.admit(call.model_copy(update={"tool_id": "other"}), AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset({"observation:red"})))
    assert rejected.code == "tool_not_declared"


def test_mode_switch_is_explicit_and_baseline_remains_untouched():
    assert select_planning_mode("baseline") == "baseline"
    assert select_planning_mode("agent_composed") == "agent_composed"
    with pytest.raises(AgentPlanningError):
        select_planning_mode("fixed")


def test_executable_pick_place_projection_preserves_skill_order_and_bindings():
    plan = compose_executable_pick_place_plan(
        "blocks-ranking-rgb-seed-0", "revision-1",
        (
            AgentSubtaskSpec(
                subtask_id="green", entity_ref="entity://block-green-1",
                destination_ref="destination://bin/primary",
            ),
            AgentSubtaskSpec(
                subtask_id="red", entity_ref="entity://block-red-1",
                destination_ref="destination://bin/secondary", depends_on=("green",),
            ),
        ),
        planner_decision_digest="1" * 64,
        policy_snapshot_digest="2" * 64,
    )
    nodes = {node.node_id: node for node in plan.graph.nodes}
    assert [node.capability for node in plan.graph.nodes[:7]] == [
        "scene.observe", "manipulation.capabilities", "scene.understand",
        "grasp.propose", "manipulation.prepare", "object.acquire", "object.place",
    ]
    assert nodes["red.observe"].dependencies == ("green.place",)
    assert nodes["green.place"].input_bindings == {
        "entity_ref": "entity://block-green-1",
        "destination_ref": "destination://bin/primary",
    }
    assert nodes["red.acquire"].input_bindings["entity_ref"] == "entity://block-red-1"
    assert set(nodes["verify"].dependencies) == {"green.place", "red.place"}
    assert dict(plan.entity_bindings)["red.place"] == "entity://block-red-1"


def test_executable_projection_admits_declared_tool_without_motion_authority():
    plan = compose_executable_pick_place_plan(
        "blocks-ranking-rgb-seed-0", "revision-1",
        (AgentSubtaskSpec(subtask_id="green", entity_ref="entity://block-green-1"),),
        planner_decision_digest="1" * 64,
        policy_snapshot_digest="2" * 64,
    )
    policy = ToolSpecPolicy(
        tool_id="scene.observe", semantics="query", spec_digest="3" * 64,
        capabilities=("scene.observe",),
    )
    planner = DynamicToolPlanner(plan, (policy,))
    call = ToolCallEnvelope(
        task_id=plan.graph.task_id, revision_id=plan.graph.revision_id,
        node_id="green.observe", tool_id="scene.observe", tool_spec_digest="3" * 64,
        input_binding_digest="4" * 64, scene_revision="scene-0",
        idempotency_key="idem-0", semantics="query",
    )
    decision = planner.admit(call, AdmissionContext(scene_revision="scene-0"))
    assert decision.allowed is True
    assert decision.motion_authorized is False
