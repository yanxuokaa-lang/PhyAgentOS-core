from types import SimpleNamespace

from PhyAgentOS.agent.prompt_context import continuation_task_prompt_projection


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
