from __future__ import annotations

import asyncio
from time import monotonic
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.recovery_decisions import (
    AgentRecoveryDecisions,
    _same_capture_alternative_candidates,
    recovery_method_options,
)


def _task(*, tools=(), records=()):
    return SimpleNamespace(
        execution_records=records,
        primary_skill_binding=SimpleNamespace(required_tools=tools),
        tool_bindings=(),
    )


def _policy(*, semantics="query", capabilities=("scene.observe",)):
    return SimpleNamespace(
        semantics=semantics,
        capabilities=capabilities,
    )


def test_recovery_options_include_read_only_replay_and_investigation_replan():
    task = _task(
        tools=(SimpleNamespace(
            semantics="query",
            planning_policy=_policy(capabilities=("scene.observe", "scene.understand")),
        ),),
        records=(SimpleNamespace(
            revision_id="revision-1",
            node_id="understand",
            semantics="query",
            status="succeeded",
            response={"data": {"status": "available"}},
        ),),
    )
    graph = SimpleNamespace(
        revision_id="revision-1",
        nodes=(SimpleNamespace(node_id="understand", obligation_id="understanding"),),
    )
    settlement = SimpleNamespace(
        node_id="understand",
        status="failed",
        requires_replan=True,
        evidence_refs=("evidence://missing",),
    )
    delta = SimpleNamespace(fresh_evidence_requirements=("scene:current",))

    options = recovery_method_options(task, graph, settlement, delta, context={})

    assert [item.option_id for item in options] == ["stop", "replay", "replan"]
    replan = options[-1]
    assert replan.investigation_capabilities == ("scene.observe", "scene.understand")
    assert set(replan.addresses) == {"evidence://missing", "scene:current"}
    assert replan.unfinished_obligations == ("understanding",)


def test_recovery_options_remove_replay_for_unknown_physical_effect():
    task = _task(records=(SimpleNamespace(
        revision_id="revision-1",
        node_id="move",
        semantics="action",
        status="unknown",
    ),))
    graph = SimpleNamespace(revision_id="revision-1")
    settlement = SimpleNamespace(
        node_id="move",
        status="outcome_unknown",
        requires_replan=True,
        evidence_refs=(),
    )
    delta = SimpleNamespace(fresh_evidence_requirements=())

    options = recovery_method_options(task, graph, settlement, delta, context={})

    assert [item.option_id for item in options] == ["stop"]
    assert "unknown_action_or_session" not in options[0].prohibited_when


def test_recovery_options_report_gap_when_no_query_capability_exists():
    task = _task(records=(SimpleNamespace(
        revision_id="revision-1",
        node_id="observe",
        semantics="query",
        status="failed",
    ),))
    graph = SimpleNamespace(revision_id="revision-1")
    settlement = SimpleNamespace(
        node_id="observe",
        status="failed",
        requires_replan=True,
        evidence_refs=("scene:current",),
    )
    delta = SimpleNamespace(fresh_evidence_requirements=("calibration:current",))

    options = recovery_method_options(task, graph, settlement, delta, context={})

    assert [item.option_id for item in options] == ["stop"]
    assert set(options[0].addresses) == {"scene:current", "calibration:current"}


def test_recovery_options_do_not_replay_business_unavailable_query():
    task = _task(records=(SimpleNamespace(
        revision_id="revision-1",
        node_id="observe",
        semantics="query",
        status="failed",
        response={"data": {"status": "unavailable"}},
    ),))
    graph = SimpleNamespace(revision_id="revision-1")
    settlement = SimpleNamespace(
        node_id="observe",
        status="failed",
        requires_replan=True,
        evidence_refs=("scene:current",),
    )
    delta = SimpleNamespace(fresh_evidence_requirements=("scene:current",))

    options = recovery_method_options(task, graph, settlement, delta, context={})

    assert [item.option_id for item in options] == ["stop"]


def test_recovery_llm_does_not_start_after_expired_deadline():
    class Provider:
        async def chat_with_retry(self, **_kwargs):
            raise AssertionError("expired recovery deadline must not call the provider")

    task = _task()
    task.task_id = "task-1"
    graph = SimpleNamespace(
        task_id="task-1", revision_id="revision-1", nodes=(),
        model_dump=lambda **_kwargs: {},
    )
    settlement = SimpleNamespace(
        node_id="observe", status="failed", requires_replan=True,
        evidence_refs=(), model_dump=lambda **_kwargs: {},
    )
    delta = SimpleNamespace(
        fresh_evidence_requirements=(), model_dump=lambda **_kwargs: {},
    )
    context = SimpleNamespace(model_dump=lambda **_kwargs: {})

    decisions = AgentRecoveryDecisions(Provider(), "model", SimpleNamespace(
        get_task=lambda _task_id: task,
    ))

    with pytest.raises(TimeoutError, match="deadline exhausted"):
        asyncio.run(decisions._ask(
            graph, settlement, delta, context,
            decision_deadline=monotonic() - 1.0,
        ))


def _route_recovery_records(*, scene_revision="scene-1"):
    binding = {
        "entity_ref": "entity://r01",
        "candidate_set_ref": "candidate-set://scene-1/grasp",
        "candidate_ref": "candidate://r01/failed",
        "observation_ref": "observation://scene-1/camera",
        "scene_revision": "scene-1",
        "frame_id": "camera",
        "calibration_ref": "artifact://calibration/scene-1",
    }
    failed_action = SimpleNamespace(
        revision_id="revision-1", node_id="pour-r01", semantics="action",
        status="failed", arguments={"operation": "pour", "binding": binding},
        response={"data": {"result": {
            "status": "failed",
            "capability_outcome_summary": {
                "status": "failed", "requires_replan": True,
                "world_change_started": False, "outcome_known": True,
                "possession_state": "empty",
            },
            "subtask_result": {"receipts": [{
                "sequence_index": 0,
                "tool_id": "manipulation.prepare",
                "response": {
                    "motion_authorized": False,
                    "failure_owner": "runtime_adapter",
                    "rejected_candidate_refs": [
                        "candidate://r01/failed",
                        "candidate://r01/rejected-by-prepare",
                    ],
                    "error": {"code": "no_admissible_grasp", "message": "route_collision"},
                },
            }]},
        }}},
    )
    affordance_query = SimpleNamespace(
        revision_id="revision-1", node_id="affordances", semantics="query",
        status="succeeded", tool_id="manipulation.grasp_task_affordances",
        record_id="query-record-1",
        arguments={"operation": "pour", "entity_refs": ["entity://r01", "entity://beaker"]},
        response={"data": {
            "status": "available",
            "candidate_set_ref": "grasp-affordance-set://scene-1",
            "grasp_candidate_set_ref": (
                "candidate-set://scene-1/grasp"
                if scene_revision == "scene-1"
                else "candidate-set://scene-2/grasp"
            ),
            "process_feature_candidate_set_ref": "process-feature-set://scene-1",
            "observation_ref": "observation://scene-1/camera",
            "scene_revision": scene_revision,
            "frame_id": "camera",
            "calibration_ref": "artifact://calibration/scene-1",
            "candidates": [
                {"combination_ref": "grasp-affordance://failed",
                 "entity_ref": "entity://r01",
                 "grasp_candidate_ref": "candidate://r01/failed",
                 "process_feature_refs": ["process-feature://rim"]},
                {"combination_ref": "grasp-affordance://alternative",
                 "entity_ref": "entity://r01",
                 "grasp_candidate_ref": "candidate://r01/alternative",
                 "process_feature_refs": ["process-feature://rim"]},
                {"combination_ref": "grasp-affordance://rejected",
                 "entity_ref": "entity://r01",
                 "grasp_candidate_ref": "candidate://r01/rejected-by-prepare",
                 "process_feature_refs": ["process-feature://rim"]},
            ],
        }},
    )
    return failed_action, affordance_query


def test_no_motion_grasp_recovery_projects_same_capture_alternative_opaque_refs():
    failed, query = _route_recovery_records()
    task = _task(
        tools=(SimpleNamespace(
            semantics="query", planning_policy=_policy(capabilities=(
                "manipulation.grasp_task_affordances",)),
        ),),
        records=(query, failed),
    )
    task.task_id = "task-1"
    graph = SimpleNamespace(
        task_id="task-1", revision_id="revision-1", nodes=(),
    )
    settlement = SimpleNamespace(
        node_id="pour-r01", status="failed", outcome_known=True,
        world_change_started=False, requires_replan=True, evidence_refs=(),
    )

    projected = _same_capture_alternative_candidates(task, graph, settlement)
    options = recovery_method_options(
        task, graph, settlement, SimpleNamespace(fresh_evidence_requirements=()), {},
    )

    assert projected["source_record_id"] == "query-record-1"
    assert projected["candidates"] == [{
        "combination_ref": "grasp-affordance://alternative",
        "grasp_candidate_ref": "candidate://r01/alternative",
        "process_feature_refs": ["process-feature://rim"],
    }]
    assert [item.option_id for item in options] == ["stop", "replan"]
    assert options[-1].addresses == ("same_capture_alternative_grasp_candidate",)


def test_no_motion_grasp_recovery_stops_when_candidate_provenance_is_stale():
    failed, stale_query = _route_recovery_records(scene_revision="scene-2")
    task = _task(
        tools=(SimpleNamespace(
            semantics="query", planning_policy=_policy(capabilities=(
                "manipulation.grasp_task_affordances",)),
        ),),
        records=(stale_query, failed),
    )
    graph = SimpleNamespace(task_id="task-1", revision_id="revision-1", nodes=())
    settlement = SimpleNamespace(
        node_id="pour-r01", status="failed", outcome_known=True,
        world_change_started=False, requires_replan=True, evidence_refs=(),
    )

    options = recovery_method_options(
        task, graph, settlement, SimpleNamespace(fresh_evidence_requirements=()), {},
    )
    assert [item.option_id for item in options] == ["stop"]


def test_recovery_prompt_receives_only_same_capture_opaque_candidate_projection():
    failed, query = _route_recovery_records()
    failed.record_id = "action-record-1"
    failed.tool_id = "manipulation.execute_subtask"
    failed.error = None
    failed.evidence_refs = ()
    task = _task(
        tools=(SimpleNamespace(
            semantics="query", planning_policy=_policy(capabilities=(
                "manipulation.grasp_task_affordances",)),
        ),),
        records=(query, failed),
    )
    task.task_id = "task-1"
    task.task_description = "Pour reagent into beaker"
    task.verification = SimpleNamespace(model_dump=lambda **_kwargs: {})
    task.skill_uses = ()
    task.active_skill_instructions = ""
    task.primary_skill_instructions = ""
    graph = SimpleNamespace(
        task_id="task-1", revision_id="revision-1", nodes=(),
        model_dump=lambda **_kwargs: {"nodes": []},
    )
    settlement = SimpleNamespace(
        node_id="pour-r01", status="failed", outcome_known=True,
        world_change_started=False, requires_replan=True, evidence_refs=(),
        model_dump=lambda **_kwargs: {"status": "failed"},
    )
    delta = SimpleNamespace(
        fresh_evidence_requirements=(), model_dump=lambda **_kwargs: {},
    )
    context = SimpleNamespace(model_dump=lambda **_kwargs: {})

    class Provider:
        messages = None

        async def chat_with_retry(self, **kwargs):
            self.messages = kwargs["messages"]
            return SimpleNamespace(
                finish_reason="stop",
                tool_calls=[SimpleNamespace(
                    name="submit_recovery",
                    arguments={"reason": "select alternate", "nodes": []},
                )],
            )

    provider = Provider()
    decisions = AgentRecoveryDecisions(
        provider, "model", SimpleNamespace(get_task=lambda _task_id: task),
    )

    value = asyncio.run(decisions._ask(
        graph, settlement, delta, context,
        decision_deadline=monotonic() + 30.0, replan=True,
    ))

    prompt = provider.messages[1]["content"]
    assert value["reason"] == "select alternate"
    assert "candidate://r01/alternative" in prompt
    assert "grasp-affordance://alternative" in prompt
    assert "position_m" not in prompt
