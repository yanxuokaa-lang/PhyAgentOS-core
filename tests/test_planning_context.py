from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.planning_loop import NodeContextProvider, StaleNodeContextError


def _task_with_stale_discovery_evidence(*, required_evidence: tuple[str, ...]):
    stale_ref = "tool:tool_old_scene_understanding"
    node = SimpleNamespace(
        node_id="observe_after_acquire",
        capability="scene.observe",
        dependencies=(),
        required_evidence=required_evidence,
        input_bindings={"sensor_ref": "camera/head", "max_age_ms": 1000},
    )
    stale_record = SimpleNamespace(
        revision_id="revision-1",
        record_id="tool_old_scene_understanding",
        tool_id="scene.understand",
        semantics="query",
        status="succeeded",
        evidence_refs=(stale_ref,),
        arguments={"scene_revision": "scene-old"},
        response={"data": {"status": "available", "scene_revision": "scene-old"}},
        error=None,
    )
    revision = SimpleNamespace(
        revision_id="revision-1",
        plan_graph=SimpleNamespace(task_id="task-1", nodes=(node,)),
        node_settlements=(),
        discovery_evidence_refs=(stale_ref,),
        execution_records=(stale_record,),
        fresh_evidence_requirements=(),
        replan_evidence_refs=(),
    )
    binding = SimpleNamespace(
        required_tools=(
            SimpleNamespace(
                tool_id="scene.observe",
                planning_policy=SimpleNamespace(refreshes_scene=True),
            ),
            SimpleNamespace(
                tool_id="scene.understand",
                planning_policy=SimpleNamespace(refreshes_scene=False),
            ),
        )
    )
    return SimpleNamespace(
        active_revision=revision,
        revisions=(revision,),
        primary_skill_binding=binding,
    )


def test_context_skips_unrequired_stale_discovery_evidence_after_world_change():
    task = _task_with_stale_discovery_evidence(required_evidence=())

    context = NodeContextProvider(lambda _task_id: task).build(
        "task-1",
        "observe_after_acquire",
        scene_revision="scene-new",
    )

    assert context.evidence_context == ()
    assert context.scene_revision == "scene-new"


def test_context_rejects_explicitly_required_stale_discovery_evidence():
    stale_ref = "tool:tool_old_scene_understanding"
    task = _task_with_stale_discovery_evidence(required_evidence=(stale_ref,))

    with pytest.raises(
        StaleNodeContextError,
        match="required evidence tool_old_scene_understanding belongs to stale scene revision",
    ):
        NodeContextProvider(lambda _task_id: task).build(
            "task-1",
            "observe_after_acquire",
            scene_revision="scene-new",
        )
