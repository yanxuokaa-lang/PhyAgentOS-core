from __future__ import annotations

from types import SimpleNamespace

from PhyAgentOS.agent.recovery_decisions import recovery_method_options


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
