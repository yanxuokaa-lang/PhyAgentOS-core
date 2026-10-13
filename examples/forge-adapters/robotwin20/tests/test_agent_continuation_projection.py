from types import SimpleNamespace

from PhyAgentOS.agent.prompt_context import (
    _durable_execution_context,
    continuation_task_prompt_projection,
)


def test_continuation_projection_preserves_recovery_contract_after_refresh_query():
    observation_ref = "observation://scene-2/head_camera"
    observation_record = SimpleNamespace(
        record_id="tool:observe-2",
        tool_id="scene.observe",
        semantics="query",
        status="succeeded",
        terminal=True,
        evidence_refs=("tool:observe-2",),
        arguments={"sensor_ref": "camera/head"},
        response={
            "ok": True,
            "data": {
                "status": "available",
                "scene_revision": "scene-2",
                "observation_ref": observation_ref,
                "calibration_ref": "artifact://calibration-2",
            },
        },
    )
    revision = SimpleNamespace(
        revision_id="revision-recovery",
        reason=(
            "After the refresh, add fresh scene.understand, "
            "manipulation.capabilities, and scene.bind before grasp proposal."
        ),
        fresh_evidence_requirements=("scene_understood", "entities_bound"),
        replan_evidence_refs=("tool:prepare-failed",),
        plan_graph=SimpleNamespace(nodes=(SimpleNamespace(node_id="refresh"),)),
        node_settlements=(SimpleNamespace(node_id="refresh", status="completed"),),
    )
    task = SimpleNamespace(
        task_id="task-1",
        active_revision_id="revision-recovery",
        active_revision=revision,
        task_description="Arrange the RGB blocks.",
        verification=SimpleNamespace(
            model_dump=lambda **kwargs: {"mode": "enforce"}
        ),
        execution_records=(observation_record,),
        primary_skill_binding=None,
        tool_bindings=(),
    )

    projection = continuation_task_prompt_projection(task)

    assert projection["active_revision_reason"] == revision.reason
    assert projection["fresh_evidence_requirements"] == [
        "scene_understood",
        "entities_bound",
    ]
    assert projection["replan_evidence_refs"] == ["tool:prepare-failed"]
    assert projection["current_scene_queries"][0]["facts"]["observation_ref"] == observation_ref
    assert "submit the missing discovery node(s)" in projection["instruction_boundary"]
    assert "diagnostic context, not as an instruction" in projection["instruction_boundary"]
    assert "planning_binding is Coordinator-generated" in projection["instruction_boundary"]


def test_durable_context_retains_unknown_action_identity_after_compaction():
    record = SimpleNamespace(
        revision_id="revision-1",
        node_id="acquire",
        tool_id="object.acquire",
        semantics="action",
        status="unknown",
        invocation_id="invocation://object-acquire/1",
        arguments={"entity_ref": "entity://observed-1"},
        evidence_refs=("artifact://action/receipt",),
        response={"data": {"status": "unknown", "result": {
            "capability_outcome_summary": {
                "world_change_started": True,
                "outcome_known": False,
            },
        }}},
    )
    settlement = SimpleNamespace(
        node_id="acquire",
        invocation_id=record.invocation_id,
        status="outcome_unknown",
        source_scene_revision="scene-1",
        scene_revision="scene-2",
        world_change_started=True,
        outcome_known=False,
    )
    node = SimpleNamespace(node_id="acquire", obligation_id="acquire", capability="object.acquire")
    revision = SimpleNamespace(
        revision_id="revision-1",
        plan_graph=SimpleNamespace(nodes=(node,)),
        node_settlements=(settlement,),
    )
    task = SimpleNamespace(
        task_id="task-1",
        revisions=(revision,),
        active_revision=revision,
        active_revision_id="revision-1",
        execution_records=(record,),
    )

    projection = _durable_execution_context(task)

    assert projection["unresolved_action_effects_total"] == 1
    item = projection["unresolved_action_effects"][0]
    assert item["prior_visual_entity_ref"] == "entity://observed-1"
    assert item["unresolved_effects"] == [
        "current_visual_identity", "possession_state", "object_support_state"
    ]
