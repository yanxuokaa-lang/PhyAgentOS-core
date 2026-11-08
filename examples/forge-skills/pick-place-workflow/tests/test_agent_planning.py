from __future__ import annotations

import pytest
from PhyAgentOS.planning import (
    AdmissionContext,
    ResourceClaim,
    ToolCallEnvelope,
    ToolSpecPolicy,
    derive_ready_nodes,
    project_tool_spec,
    tool_input_binding_digest,
)
from pydantic import ValidationError

from pick_place_workflow.agent_planning import (
    AgentPlanningError,
    AgentSubtaskSpec,
    DynamicToolPlanner,
    ToolSelectionError,
    bind_subtask_from_semantics,
    compose_agent_plan,
    compose_executable_pick_place_plan,
    compose_relation_goal_plan,
    compose_subtask_plan,
    select_planning_mode,
)
from pick_place_workflow.relation_execution import RELATION_ESTABLISH_TOOL_SPEC
from pick_place_workflow.subtask_executor import PerceptionBinding, SubtaskSpec


def _lab_binding():
    return PerceptionBinding(
        entity_ref="entity://reagent-a", semantic_label="reagent A", category="reagent_bottle",
        destination_semantic_label="beaker", destination_category="beaker",
        measured_pose={"position": [0.1, 0.2, 0.3]}, measured_geometry={"height_m": 0.18},
        grasp_candidate={"candidate_ref": "candidate://reagent-a/0", "entity_ref": "entity://reagent-a"},
        grasp_candidate_ref="candidate-set://scene-1/reagent-a",
        candidate_set_ref="candidate-set://scene-1/reagent-a",
        candidate_ref="candidate://reagent-a/0",
        capability_snapshot_ref="artifact://capabilities/lab-v1",
        binding_ref="artifact://perception/lab-scene-1",
        destination_ref="destination://beaker-1", destination_pose={"position": [0.2, 0.2, 0.1]},
        process_frame="frame://beaker-1", observation_ref="observation://lab/scene-1",
        scene_revision="scene-1", frame_id="lab-camera-front",
        calibration_ref="artifact://calibration/lab-v1", freshness_ms=10, max_age_ms=1000,
        confidence=0.98, provenance="artifact://perception/lab-scene-1",
    )


class _BindingProvider:
    def __init__(self, binding, *, ready=True):
        self.binding = binding
        self.ready = ready
        self.calls = 0

    def bind(self):
        self.calls += 1
        return self.binding


def test_bind_subtask_from_semantics_uses_a_provider_neutral_port():
    first = _BindingProvider(_lab_binding())
    second_binding = _lab_binding().model_copy(
        update={
            "entity_ref": "entity://reagent-b",
            "semantic_label": "reagent B",
            "candidate_ref": "candidate://reagent-b/0",
        }
    )
    second = _BindingProvider(second_binding)

    first_spec = bind_subtask_from_semantics(
        "pour-a", "pour", first, parameters={"tilt_rad": 0.8, "hold_s": 1.0}
    )
    second_spec = bind_subtask_from_semantics(
        "pour-b", "pour", second, parameters={"tilt_rad": 0.8, "hold_s": 1.0}
    )

    assert first.calls == second.calls == 1
    assert first_spec.binding.entity_ref == "entity://reagent-a"
    assert second_spec.binding.entity_ref == "entity://reagent-b"
    assert first_spec.parameters == {"tilt_rad": 0.8, "hold_s": 1.0}
    assert first_spec.tool_sequence == second_spec.tool_sequence


def test_bind_subtask_from_semantics_fails_closed_before_query_or_plan():
    unavailable = _BindingProvider(_lab_binding(), ready=False)
    with pytest.raises(AgentPlanningError, match="adapter is unavailable"):
        bind_subtask_from_semantics("pour-a", "pour", unavailable)
    assert unavailable.calls == 0

    broken = _BindingProvider(None)
    with pytest.raises(AgentPlanningError, match="semantic subtask binding failed"):
        bind_subtask_from_semantics("pour-a", "pour", broken)
    assert broken.calls == 1


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
    with pytest.raises(ValidationError, match="relation.establish"):
        AgentSubtaskSpec(
            subtask_id="stack-top",
            entity_ref="entity://stack-top",
            goal_relation="on",
            relation_target_ref="entity://stack-middle",
        )
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
            input_binding_digest=tool_input_binding_digest({}), scene_revision="scene-1",
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


def _stack_goal_facts():
    return {
        "schema_version": "paos-task-goals/v1",
        "task_name": "stack_blocks_three",
        "motion_authorized": False,
        "goals": [
            {
                "subtask_id": "place_base",
                "execution_entity_ref": "entity://stack-block-1",
                "goal_relation": "on",
                "relation_target_ref": "surface://table",
                "depends_on": [],
                "required_evidence": [],
                "produced_evidence": [
                    "support-relation:entity://stack-block-1:surface://table",
                    "stable-placement:entity://stack-block-1",
                ],
            },
            {
                "subtask_id": "place_middle",
                "execution_entity_ref": "entity://stack-block-2",
                "goal_relation": "on",
                "relation_target_ref": "entity://stack-block-1",
                "depends_on": ["place_base"],
                "required_evidence": [
                    "support-relation:entity://stack-block-1:surface://table",
                ],
                "produced_evidence": [
                    "support-relation:entity://stack-block-2:entity://stack-block-1",
                    "stable-placement:entity://stack-block-2",
                ],
            },
            {
                "subtask_id": "place_top",
                "execution_entity_ref": "entity://stack-block-3",
                "goal_relation": "on",
                "relation_target_ref": "entity://stack-block-2",
                "depends_on": ["place_middle"],
                "required_evidence": [
                    "support-relation:entity://stack-block-2:entity://stack-block-1",
                ],
                "produced_evidence": [
                    "support-relation:entity://stack-block-3:entity://stack-block-2",
                    "stable-placement:entity://stack-block-3",
                ],
            },
        ],
    }


def _relation_segment(goal_id, revision, available_evidence):
    observation_ref = f"observation://{revision}/head_camera"
    return compose_relation_goal_plan(
        "stack-task",
        f"revision-{revision}",
        _stack_goal_facts(),
        subtask_id=goal_id,
        scene_revision=revision,
        observation_ref=observation_ref,
        observation_frame_id="head_camera",
        calibration_ref="artifact://scene/calibration",
        available_evidence=tuple((*available_evidence, observation_ref)),
        planner_decision_digest="1" * 64,
        policy_snapshot_digest="2" * 64,
    )


def test_relation_planner_compiles_one_fresh_scene_segment_at_a_time():
    base = _relation_segment("place_base", "scene-0", ())
    assert [node.node_id for node in base.graph.nodes] == ["place_base"]
    assert base.graph.nodes[0].capability == "relation.establish"
    assert base.graph.nodes[0].input_bindings["relation_target_ref"] == "surface://table"
    assert base.graph.nodes[0].input_bindings["scene_revision"] == "scene-0"
    assert base.graph.nodes[0].produced_evidence == (
        "support-relation:entity://stack-block-1:surface://table",
        "stable-placement:entity://stack-block-1",
    )
    with pytest.raises(ToolSelectionError, match="no Tool candidate"):
        DynamicToolPlanner(base, ()).candidate_tools("place_base")
    relation_policy = project_tool_spec(RELATION_ESTABLISH_TOOL_SPEC)
    assert DynamicToolPlanner(base, (relation_policy,)).candidate_tools("place_base") == (
        "relation.establish",
    )
    assert set(relation_policy.input_binding_keys) == set(base.graph.nodes[0].input_bindings)

    middle = _relation_segment(
        "place_middle",
        "scene-1",
        base.graph.nodes[0].produced_evidence,
    )
    assert [node.node_id for node in middle.graph.nodes] == ["place_middle"]
    assert middle.graph.nodes[0].input_bindings["observation_ref"] == "observation://scene-1/head_camera"
    assert middle.graph.nodes[0].input_bindings["relation_target_ref"] == "entity://stack-block-1"
    assert set(middle.graph.nodes[0].required_evidence) >= set(
        base.graph.nodes[0].produced_evidence
    )


def test_relation_planner_requires_fresh_scene_and_settled_support_evidence():
    kwargs = {
        "task_id": "stack-task",
        "revision_id": "revision-1",
        "task_goal_facts": _stack_goal_facts(),
        "subtask_id": "place_middle",
        "scene_revision": "scene-1",
        "observation_ref": "observation://scene-1/head_camera",
        "observation_frame_id": "head_camera",
        "calibration_ref": "artifact://scene/calibration",
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
    }
    with pytest.raises(AgentPlanningError, match="predecessor evidence"):
        compose_relation_goal_plan(**kwargs, available_evidence=("observation://scene-1/head_camera",))
    with pytest.raises(AgentPlanningError, match="current scene"):
        compose_relation_goal_plan(
            **{**kwargs, "observation_ref": "observation://scene-0/head_camera"},
            available_evidence=("support-relation:entity://stack-block-1:surface://table",),
        )
    with pytest.raises(AgentPlanningError, match="identities must be non-empty"):
        compose_relation_goal_plan(
            **{**kwargs, "scene_revision": "", "observation_ref": "observation:///head_camera"},
            available_evidence=("support-relation:entity://stack-block-1:surface://table",),
        )


def test_relation_planner_rejects_predecessors_without_settlement_evidence():
    facts = _stack_goal_facts()
    facts["goals"][0]["produced_evidence"] = []
    with pytest.raises(AgentPlanningError, match="must declare settlement evidence"):
        compose_relation_goal_plan(
            "stack-task", "revision-1", facts,
            subtask_id="place_middle",
            scene_revision="scene-1",
            observation_ref="observation://scene-1/head_camera",
            observation_frame_id="head_camera",
            calibration_ref="artifact://scene/calibration",
            available_evidence=(
                "observation://scene-1/head_camera",
                "support-relation:entity://stack-block-1:surface://table",
            ),
            planner_decision_digest="1" * 64,
            policy_snapshot_digest="2" * 64,
        )


def test_relation_goal_cannot_be_compiled_as_static_pick_place():
    relation = AgentSubtaskSpec(
        subtask_id="stack-top",
        entity_ref="entity://stack-block-3",
        goal_relation="on",
        relation_target_ref="entity://stack-block-2",
        capability="relation.establish",
    )
    with pytest.raises(AgentPlanningError, match="fresh provider-resolved target"):
        compose_executable_pick_place_plan(
            "stack-task", "revision-1", (relation,),
            planner_decision_digest="1" * 64,
            policy_snapshot_digest="2" * 64,
        )


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
            input_binding_digest=tool_input_binding_digest({}), scene_revision="scene-0",
        idempotency_key="idem-0", semantics="query",
    )
    decision = planner.admit(call, AdmissionContext(scene_revision="scene-0"))
    assert decision.allowed is True
    assert decision.motion_authorized is False


def test_subtask_projection_has_feature_query_preparation_and_action_order():
    plan = compose_subtask_plan(
        "lab-task", "scene-1",
        (SubtaskSpec(
            subtask_id="pour-a", operation="pour", binding=_lab_binding(),
            parameters={"tilt_rad": 0.8, "hold_s": 1.0},
            semantic_intent={
                "goal": "pour reagent into the selected vessel",
                "success_criteria": ["pour process feedback is qualified"],
                "allowed_arms": ["franka"],
                "coordination_mode": "single_arm",
            },
        ),),
        planner_decision_digest="1" * 64, policy_snapshot_digest="2" * 64,
    )
    assert [node.capability for node in plan.graph.nodes] == [
        "manipulation.process_features", "manipulation.prepare_process_features",
        "manipulation.grasp_task_affordances", "manipulation.prepare_grasp_task_affordance",
        "manipulation.execute_subtask", "task.verify",
    ]
    assert plan.graph.nodes[0].dependencies == ()
    assert plan.graph.nodes[1].dependencies == ("pour-a.process_features",)
    assert plan.graph.nodes[2].dependencies == ("pour-a.prepare_process_features",)
    assert plan.graph.nodes[3].dependencies == ("pour-a.grasp_task_affordances",)
    assert plan.graph.nodes[4].dependencies == ("pour-a.prepare_grasp_task_affordance",)
    assert plan.graph.nodes[4].input_bindings["binding"]["entity_ref"] == "entity://reagent-a"
    assert "qualified_grasp_candidate_refs" not in plan.graph.nodes[4].input_bindings
