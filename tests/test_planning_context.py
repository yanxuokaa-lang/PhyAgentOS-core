from __future__ import annotations

from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.planning_context import (
    PlanningContextUnavailableError,
    context_from_task,
)


def _record(
    record_id: str,
    *,
    tool_id: str,
    arguments: dict,
    response: dict,
) -> SimpleNamespace:
    return SimpleNamespace(
        record_id=record_id,
        tool_id=tool_id,
        terminal=True,
        status="succeeded",
        semantics="query",
        arguments=arguments,
        response=response,
        evidence_refs=(f"tool:{record_id}",),
    )


def _task(
    *records: SimpleNamespace,
    discovery_evidence_refs: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        execution_records=records,
        active_revision=SimpleNamespace(
            node_settlements=(),
            discovery_evidence_refs=discovery_evidence_refs,
        ),
        primary_skill_binding=None,
        tool_bindings=(
            SimpleNamespace(
                tool_id="scene.observe",
                planning_policy=SimpleNamespace(refreshes_scene=True),
            ),
            SimpleNamespace(
                tool_id="scene.understand",
                planning_policy=SimpleNamespace(refreshes_scene=False),
            ),
        ),
    )


def test_context_excludes_query_evidence_bound_to_an_older_scene() -> None:
    observation = _record(
        "observe-current",
        tool_id="scene.observe",
        arguments={"sensor_ref": "camera/head"},
        response={
            "ok": True,
            "data": {"status": "available", "scene_revision": "scene-new"},
        },
    )
    stale_query = _record(
        "understand-stale",
        tool_id="scene.understand",
        arguments={
            "scene_revision": "scene-old",
            "observation_ref": "observation://old",
        },
        response={"ok": True, "data": {"status": "available", "entities": []}},
    )
    current_query = _record(
        "capabilities-current",
        tool_id="scene.understand",
        arguments={"scene_revision": "scene-new"},
        response={"ok": True, "data": {"status": "available"}},
    )

    context = context_from_task(
        _task(observation, stale_query, current_query),
        allow_refresh=True,
    )

    assert context.scene_revision == "scene-new"
    assert context.evidence_refs == frozenset({"tool:observe-current", "tool:capabilities-current"})


def test_context_rejects_query_whose_request_and_response_scenes_conflict() -> None:
    conflicting_query = _record(
        "understand-conflict",
        tool_id="scene.understand",
        arguments={"scene_revision": "scene-old"},
        response={
            "ok": True,
            "data": {"status": "available", "scene_revision": "scene-new"},
        },
    )

    with pytest.raises(PlanningContextUnavailableError):
        context_from_task(_task(conflicting_query), allow_refresh=True)


def test_context_accepts_refresh_scene_but_rejects_old_nonrefresh_response() -> None:
    first_observation = _record(
        "observe-first",
        tool_id="scene.observe",
        arguments={"sensor_ref": "camera/head"},
        response={"ok": True, "data": {"scene_revision": "scene-1"}},
    )
    refreshed_observation = _record(
        "observe-second",
        tool_id="scene.observe",
        arguments={"sensor_ref": "camera/head"},
        response={"ok": True, "data": {"scene_revision": "scene-2"}},
    )
    stale_response = _record(
        "understand-old-response",
        tool_id="scene.understand",
        arguments={},
        response={"ok": True, "data": {"scene_revision": "scene-1"}},
    )

    context = context_from_task(
        _task(first_observation, refreshed_observation, stale_response),
        allow_refresh=True,
    )

    assert context.scene_revision == "scene-2"
    assert context.evidence_refs == frozenset({"tool:observe-second"})


def test_context_accepts_refresh_query_from_current_to_new_scene() -> None:
    first_observation = _record(
        "observe-first",
        tool_id="scene.observe",
        arguments={"sensor_ref": "camera/head"},
        response={"ok": True, "data": {"scene_revision": "scene-1"}},
    )
    refreshed_observation = _record(
        "observe-second",
        tool_id="scene.observe",
        arguments={"scene_revision": "scene-1"},
        response={"ok": True, "data": {"scene_revision": "scene-2"}},
    )

    context = context_from_task(
        _task(first_observation, refreshed_observation),
        allow_refresh=True,
    )

    assert context.scene_revision == "scene-2"
    assert context.evidence_refs == frozenset({"tool:observe-second"})


def test_context_restores_only_selected_discovery_evidence_after_world_change() -> None:
    observation = _record(
        "observe-current",
        tool_id="scene.observe",
        arguments={"sensor_ref": "camera/head"},
        response={"ok": True, "data": {"scene_revision": "scene-new"}},
    )
    acquire = _record(
        "acquire",
        tool_id="object.acquire",
        arguments={"scene_revision": "scene-old"},
        response={
            "ok": True,
            "data": {
                "status": "succeeded",
                "world_changed": True,
                "new_scene_revision": "scene-new",
            },
        },
    )

    context = context_from_task(
        _task(
            observation,
            acquire,
            discovery_evidence_refs=("tool:goal", "tool:bind"),
        ),
        allow_refresh=True,
    )

    assert context.scene_revision == "scene-new"
    assert context.evidence_refs == frozenset(
        {"tool:observe-current", "tool:acquire", "tool:goal", "tool:bind"}
    )


def test_context_does_not_restore_unselected_historical_discovery_evidence() -> None:
    observation = _record(
        "observe-current",
        tool_id="scene.observe",
        arguments={"sensor_ref": "camera/head"},
        response={"ok": True, "data": {"scene_revision": "scene-new"}},
    )

    context = context_from_task(
        _task(
            observation,
            discovery_evidence_refs=("tool:selected",),
        ),
        allow_refresh=True,
    )

    assert "tool:selected" in context.evidence_refs
    assert "tool:historical" not in context.evidence_refs
