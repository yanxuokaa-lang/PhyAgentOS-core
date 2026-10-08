from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.tools.forge_task import ForgeTaskBeginRevisionTool
from PhyAgentOS.agent.tools.forge_tool_api import (
    ForgeToolContextTool,
    ForgeToolQueryTool,
    ForgeToolStartActionTool,
    _call,
    _coordinator_carried_entities,
    _effective_query_timeout_ms,
    _task_query_source_records,
)
from PhyAgentOS.forge.tool_client import ForgeToolAPITimeoutError


def test_local_lifecycle_context_uses_agent_registry_instead_of_gateway():
    class GatewayMustNotBeCalled:
        async def get_tool(self, _tool_id):
            raise AssertionError("local lifecycle context must not query Gateway")

        async def get_tool_context(self, _tool_id):
            raise AssertionError("local lifecycle context must not query Gateway")

    local = ForgeTaskBeginRevisionTool(object())
    tool = ForgeToolContextTool(
        GatewayMustNotBeCalled(),
        local_tool_provider=lambda name: local if name == local.name else None,
    )

    result = json.loads(asyncio.run(tool.execute(local.name)))

    assert result["ok"] is True
    assert result["data"]["tool"]["name"] == "forge_task_begin_revision"
    assert result["data"]["context"]["transport"] == "local_agent_tool_registry"
    assert result["data"]["context"]["gateway"] is False


def test_unregistered_local_lifecycle_context_fails_closed_without_gateway_call():
    class GatewayMustNotBeCalled:
        async def get_tool(self, _tool_id):
            raise AssertionError("unregistered local lifecycle name must not query Gateway")

        async def get_tool_context(self, _tool_id):
            raise AssertionError("unregistered local lifecycle name must not query Gateway")

    result = json.loads(asyncio.run(ForgeToolContextTool(
        GatewayMustNotBeCalled(), local_tool_provider=lambda _name: None
    ).execute("forge_task_begin_revision")))

    assert result["ok"] is False
    assert result["error"]["code"] == "local_tool_unavailable"


def test_scene_understand_timeout_has_provider_safe_floor():
    assert _effective_query_timeout_ms("scene.understand", None) == 180_000
    assert _effective_query_timeout_ms("scene.understand", 30_000) == 180_000
    assert _effective_query_timeout_ms("scene.understand", 240_000) == 240_000


def test_other_query_timeouts_are_not_changed():
    assert _effective_query_timeout_ms("scene.observe", None) is None
    assert _effective_query_timeout_ms("scene.observe", 30_000) == 30_000


def test_timeout_response_is_explicit_and_reasoned():
    async def timed_out():
        raise ForgeToolAPITimeoutError("GET /tools/scene.understand timed out", timeout_s=180.0)

    payload = json.loads(asyncio.run(_call(timed_out)))
    assert payload["ok"] is False
    assert payload["error"]["type"] == "timeout"
    assert payload["error"]["status"] == "timeout"
    assert payload["error"]["code"] == "gateway_timeout"
    assert payload["error"]["remote_state"] == "unconfirmed"
    assert "timeout_budget_s=180" in payload["error"]["reason"]


def test_task_query_source_map_contains_only_latest_successful_query_in_active_revision():
    def record(record_id, tool_id, status, revision_id, response):
        return SimpleNamespace(
            record_id=record_id,
            tool_id=tool_id,
            semantics="query",
            status=status,
            revision_id=revision_id,
            arguments={},
            response=response,
        )

    task = SimpleNamespace(
        active_revision_id="revision-current",
        execution_records=[
            record("observe-old", "scene.observe", "succeeded", "revision-current", {"scene_revision": "old"}),
            record("observe-latest", "scene.observe", "succeeded", "revision-current", {"scene_revision": "current"}),
            record("observe-other-revision", "manipulation.capabilities", "succeeded", "revision-old", {"arm_id": "left"}),
            record("understand-failed", "scene.understand", "failed", "revision-current", {"status": "invalid"}),
        ],
    )

    sources = _task_query_source_records(task)

    assert set(sources) == {"observe-latest"}
    assert sources["observe-latest"][1]["scene_revision"] == "current"


@pytest.mark.parametrize(
    ("scene_id", "frame_id", "artifact_names"),
    [
        ("scene-3", "head_camera", ("rgb", "depth")),
        ("scene-4", "wrist_camera", ("rgb",)),
        ("scene-5", "observer_camera", ("rgb", "depth", "state")),
    ],
)
def test_task_query_copies_exact_source_fields_and_inherits_observation_max_age(
    scene_id, frame_id, artifact_names
):
    artifact_refs = [f"artifact://{scene_id}/{name}" for name in artifact_names]
    observation = {
        "observation_ref": f"observation://{scene_id}/{frame_id}",
        "scene_revision": scene_id,
        "frame": {"frame_id": frame_id},
        "calibration_ref": f"artifact://{scene_id}/calibration",
        "freshness_ms": 12,
        "artifacts": [
            {"ref": ref, "kind": name}
            for ref, name in zip(artifact_refs, artifact_names, strict=True)
        ],
    }
    task = SimpleNamespace(
        active_revision_id="revision-current",
        execution_records=[SimpleNamespace(
            record_id="observe-1",
            tool_id="scene.observe",
            semantics="query",
            status="succeeded",
            revision_id="revision-current",
            arguments={"sensor_ref": "camera/head", "max_age_ms": 1000},
            response={"ok": True, "data": observation},
        )],
    )

    class Coordinator:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

        async def invoke_query(self, task_id, tool_id, arguments, **kwargs):
            assert (task_id, tool_id) == ("task-1", "scene.understand")
            return {"ok": True, "arguments": arguments}

    sources = {
        "observation_ref": {"record_id": "observe-1", "path": ["response", "observation_ref"]},
        "scene_revision": {"record_id": "observe-1", "path": ["response", "scene_revision"]},
        "frame_id": {
            "record_id": "observe-1",
            "path": ["response", "frame", "frame_id"],
            "target_path": ["frame_id"],
        },
        "calibration_ref": {"record_id": "observe-1", "path": ["response", "calibration_ref"]},
        "freshness_ms": {"record_id": "observe-1", "path": ["response", "freshness_ms"]},
        "artifacts": {
            "record_id": "observe-1",
            "path": ["response", "artifacts"],
            "map_field": "ref",
        },
    }

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="scene.understand",
        arguments={},
        argument_sources=sources,
    )))

    assert result["ok"] is True
    assert result["arguments"] == {
        "max_age_ms": 1000,
        "observation_ref": observation["observation_ref"],
        "scene_revision": scene_id,
        "frame_id": frame_id,
        "calibration_ref": observation["calibration_ref"],
        "freshness_ms": 12,
        "artifacts": artifact_refs,
    }


@pytest.mark.parametrize(
    ("scene_id", "frame_id", "artifact_names"),
    [
        ("scene-6", "head_camera", ("rgb", "depth")),
        ("scene-7", "wrist_camera", ("rgb",)),
        ("scene-8", "observer_camera", ("rgb", "depth", "state")),
    ],
)
@pytest.mark.parametrize("tool_id", ["manipulation.capabilities", "scene.understand"])
def test_scene_followup_queries_use_observation_receipt_instead_of_retyped_refs(
    scene_id, frame_id, artifact_names, tool_id
):
    artifact_refs = [f"artifact://{scene_id}/{name}" for name in artifact_names]
    observation = {
        "status": "available",
        "observation_ref": f"observation://{scene_id}/{frame_id}",
        "scene_revision": scene_id,
        "frame": {"frame_id": frame_id, "unit": "m"},
        "calibration_ref": f"artifact://{scene_id}/calibration",
        "freshness_ms": 17,
        "artifacts": [
            {"ref": ref, "kind": name, "media_type": "image/png" if name == "rgb" else "application/octet-stream"}
            for ref, name in zip(artifact_refs, artifact_names, strict=True)
        ],
    }
    task = SimpleNamespace(
        active_revision_id="revision-current",
        execution_records=[SimpleNamespace(
            record_id="observe-1",
            tool_id="scene.observe",
            semantics="query",
            status="succeeded",
            revision_id="revision-current",
            arguments={"sensor_ref": "camera/head", "max_age_ms": 1000},
            response={"ok": True, "data": observation},
        )],
    )

    class Coordinator:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

        async def invoke_query(self, task_id, actual_tool_id, arguments, **kwargs):
            assert (task_id, actual_tool_id) == ("task-1", tool_id)
            return {"ok": True, "arguments": arguments}

    supplied = {
        "scene_revision": "copied-wrong-scene",
        "observation_ref": "observation://wrong/camera",
        "calibration_ref": "artifact://wrong/calibration",
    }
    if tool_id == "scene.understand":
        supplied["agent_owned_option"] = "preserved"

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id=tool_id,
        arguments=supplied,
    )))

    assert result["ok"] is True
    effective = result["arguments"]
    assert effective["scene_revision"] == scene_id
    assert effective["observation_ref"] == observation["observation_ref"]
    assert effective["calibration_ref"] == observation["calibration_ref"]
    if tool_id == "scene.understand":
        assert effective == {
            "scene_revision": scene_id,
            "observation_ref": observation["observation_ref"],
            "frame_id": frame_id,
            "calibration_ref": observation["calibration_ref"],
            "freshness_ms": 17,
            "artifacts": artifact_refs,
            "agent_owned_option": "preserved",
            "max_age_ms": 1000,
        }
    else:
        assert effective == {
            "scene_revision": scene_id,
            "observation_ref": observation["observation_ref"],
            "calibration_ref": observation["calibration_ref"],
        }


def test_scene_followup_query_requires_available_active_revision_observation():
    task = SimpleNamespace(active_revision_id="revision-current", execution_records=[])

    class Coordinator:
        def get_task(self, _task_id):
            return task

        async def invoke_query(self, *_args, **_kwargs):
            raise AssertionError("Query must not run without its observation source")

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="manipulation.capabilities",
        arguments={
            "scene_revision": "invented",
            "observation_ref": "invented",
            "calibration_ref": "invented",
        },
    )))

    assert result["ok"] is False
    assert "successful scene.observe Query" in result["error"]["message"]


def test_selected_scene_bind_query_resolves_entity_refs_before_validation():
    understanding = SimpleNamespace(
        record_id="understand-1",
        tool_id="scene.understand",
        semantics="query",
        status="succeeded",
        revision_id="revision-current",
        arguments={},
        response={
            "data": {
                "entities": [
                    {"entity_ref": "entity://e1", "category": "cube"},
                    {"entity_ref": "entity://e2", "category": "cube"},
                ],
                "ambiguities": [],
            }
        },
    )
    task = SimpleNamespace(
        active_revision_id="revision-current",
        execution_records=[understanding],
    )

    class Binding:
        def model_dump(self, mode="json"):
            assert mode == "json"
            return {"node_id": "bind", "revision_id": "revision-current"}

    class Coordinator:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

        def selected_execution_binding(self, task_id, tool_id, semantics, planning_binding):
            assert (task_id, tool_id, semantics) == ("task-1", "scene.bind", "query")
            assert planning_binding == {"node_id": "bind"}
            return Binding()

        def selected_execution_arguments(self, task_id, tool_id, semantics, arguments, binding):
            assert (task_id, tool_id, semantics, arguments) == (
                "task-1", "scene.bind", "query", {},
            )
            assert binding == {"node_id": "bind", "revision_id": "revision-current"}
            return {"entity_refs": ["entity://e1", "entity://e2"]}

        async def invoke_query(self, task_id, tool_id, arguments, **kwargs):
            assert (task_id, tool_id) == ("task-1", "scene.bind")
            assert arguments == {"entity_refs": ["entity://e1", "entity://e2"]}
            return {"ok": True, "data": {"status": "available"}}

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="scene.bind",
        arguments={},
        planning_binding={"node_id": "bind"},
        use_selected_arguments=True,
    )))

    assert result == {"ok": True, "data": {"status": "available"}}


def test_selected_scene_bind_query_keeps_invalid_resolved_selection_fail_closed():
    task = SimpleNamespace(active_revision_id="revision-current", execution_records=[])

    class Binding:
        def model_dump(self, mode="json"):
            assert mode == "json"
            return {"node_id": "bind", "revision_id": "revision-current"}

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def selected_execution_binding(self, *_args):
            return Binding()

        def selected_execution_arguments(self, *_args):
            return {"entity_refs": []}

        async def invoke_query(self, *_args, **_kwargs):
            raise AssertionError("invalid selected entity_refs must not reach Gateway")

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="scene.bind",
        arguments={},
        planning_binding={"node_id": "bind"},
        use_selected_arguments=True,
    )))

    assert result["ok"] is False
    assert result["error"]["type"] == "agent_task"
    assert result["error"]["code"] == "scene_bind_missing_entity_refs"


def test_scene_understand_explicit_sources_still_inherit_observation_max_age():
    observation = {
        "status": "available",
        "observation_ref": "observation://scene-9/head_camera",
        "scene_revision": "scene-9",
        "frame": {"frame_id": "head_camera", "unit": "m"},
        "calibration_ref": "artifact://scene-9/calibration",
        "freshness_ms": 9,
        "artifacts": [
            {"ref": "artifact://scene-9/rgb", "kind": "rgb"},
            {"ref": "artifact://scene-9/depth", "kind": "depth"},
        ],
    }
    task = SimpleNamespace(
        active_revision_id="revision-current",
        execution_records=[SimpleNamespace(
            record_id="observe-1",
            tool_id="scene.observe",
            semantics="query",
            status="succeeded",
            revision_id="revision-current",
            arguments={"sensor_ref": "camera/head", "max_age_ms": 1250},
            response={"ok": True, "data": observation},
        )],
    )

    class Coordinator:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

        async def invoke_query(self, task_id, tool_id, arguments, **kwargs):
            assert (task_id, tool_id) == ("task-1", "scene.understand")
            return {"ok": True, "arguments": arguments}

    sources = {
        "observation_ref": {"record_id": "observe-1", "path": ["response", "data", "observation_ref"]},
        "scene_revision": {"record_id": "observe-1", "path": ["response", "data", "scene_revision"]},
        "frame_id": {"record_id": "observe-1", "path": ["response", "data", "frame", "frame_id"]},
        "calibration_ref": {"record_id": "observe-1", "path": ["response", "data", "calibration_ref"]},
        "freshness_ms": {"record_id": "observe-1", "path": ["response", "data", "freshness_ms"]},
        "artifacts": {"record_id": "observe-1", "path": ["response", "data", "artifacts"], "map_field": "ref"},
    }

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="scene.understand",
        arguments={},
        argument_sources=sources,
    )))

    assert result["ok"] is True
    assert result["arguments"]["max_age_ms"] == 1250
    assert result["arguments"]["freshness_ms"] == 9


def test_task_query_rejects_unavailable_sources_without_gateway_call():
    task = SimpleNamespace(active_revision_id="revision-current", execution_records=[])

    class Coordinator:
        def get_task(self, _task_id):
            return task

        async def invoke_query(self, *_args, **_kwargs):
            raise AssertionError("Query must not run with an unavailable source")

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="scene.understand",
        arguments={},
        argument_sources={
            "scene_revision": {"record_id": "old-observation", "path": ["response", "scene_revision"]}
        },
    )))

    assert result["ok"] is False
    assert "successful scene.observe Query" in result["error"]["message"]


def test_failed_latest_query_does_not_fall_back_to_older_source():
    def record(record_id, status, response):
        return SimpleNamespace(
            record_id=record_id,
            tool_id="scene.observe",
            semantics="query",
            status=status,
            revision_id="revision-current",
            arguments={},
            response=response,
        )

    task = SimpleNamespace(
        active_revision_id="revision-current",
        execution_records=[
            record("observe-ok", "succeeded", {"status": "available", "scene_revision": "scene-1"}),
            record("observe-invalid", "succeeded", {"status": "invalid", "scene_revision": "unknown"}),
        ],
    )

    assert _task_query_source_records(task) == {}


def test_task_query_rejects_literal_and_source_conflicts_before_gateway_call():
    task = SimpleNamespace(
        active_revision_id="revision-current",
        execution_records=[SimpleNamespace(
            record_id="observe-1",
            tool_id="scene.observe",
            semantics="query",
            status="succeeded",
            revision_id="revision-current",
            arguments={},
            response={"scene_revision": "scene-1"},
        )],
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        async def invoke_query(self, *_args, **_kwargs):
            raise AssertionError("Conflicting Query arguments must not reach Gateway")

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="custom.readonly",
        arguments={"scene_revision": "caller-value"},
        argument_sources={
            "scene_revision": {
                "record_id": "observe-1",
                "path": ["response", "scene_revision"],
            }
        },
    )))

    assert result["ok"] is False
    assert "both literal and sourced" in result["error"]["message"]


def test_query_sources_are_task_bound_and_not_exposed_on_action_schema():
    query_properties = ForgeToolQueryTool(object(), object()).parameters["properties"]
    action_properties = ForgeToolStartActionTool(object()).parameters["properties"]
    source_schema = query_properties["argument_sources"]["additionalProperties"]

    assert "argument_sources" in query_properties
    assert "map_field" in source_schema["properties"]
    assert "argument_sources" not in action_properties


def test_query_sources_require_a_task_owner():
    tool = ForgeToolQueryTool(object(), object())
    result = json.loads(asyncio.run(tool.execute(
        tool_id="scene.understand",
        arguments={},
        argument_sources={
            "scene_revision": {"record_id": "observe-1", "path": ["response", "scene_revision"]}
        },
    )))

    assert result["ok"] is False
    assert result["error"]["message"] == "argument_sources require task_id"


def _execution_record(record_id, tool_id, semantics, revision_id, response, *, arguments=None):
    return SimpleNamespace(
        record_id=record_id,
        tool_id=tool_id,
        semantics=semantics,
        status="succeeded",
        revision_id=revision_id,
        arguments=arguments or {},
        response=response,
    )


def _carry_task(*, effect_overrides=None, include_effect=True):
    old_claim = {
        "entity_ref": "entity://unchanged",
        "category": "blue block",
        "confidence": 0.9,
        "provenance": ["artifact://scene-1/front/rgb"],
    }
    effect = {
        "schema_version": "paos-scene-effects/v1",
        "source_scene_revision": "scene-1",
        "new_scene_revision": "scene-2",
        "changed_entity_refs": ["entity://held"],
        "unaffected_entity_refs": ["entity://unchanged"],
        "changed_resources": ["possession_state"],
        "effect_evidence_refs": ["artifact://persistent/action-1"],
        "effect_scope_complete": True,
        "carry_forward_authorized": True,
    }
    effect.update(effect_overrides or {})
    action_result = {"status": "succeeded"}
    if include_effect:
        action_result["scene_effects"] = effect
    observation = {
        "status": "available",
        "observation_ref": "observation://scene-2/front",
        "scene_revision": "scene-2",
        "frame": {"frame_id": "front", "unit": "m"},
        "calibration_ref": "artifact://scene-2/front/calibration",
        "freshness_ms": 1,
        "artifacts": [{
            "ref": "artifact://scene-2/front/rgb", "kind": "rgb", "media_type": "image/png",
        }],
    }
    return SimpleNamespace(
        active_revision_id="revision-current",
        execution_records=[
            _execution_record(
                "understand-old", "scene.understand", "query", "revision-old",
                {"data": {"scene_revision": "scene-1", "entities": [old_claim]}},
            ),
            _execution_record(
                "bind-old", "scene.bind", "query", "revision-old",
                {"data": {
                    "scene_revision": "scene-1",
                    "binding_ref": "artifact://entity-bindings/source",
                    "entities": [{
                        "entity_ref": "entity://unchanged",
                        "execution_entity_ref": "entity://runtime-unchanged",
                    }],
                }},
            ),
            _execution_record(
                "action-1", "object.acquire", "action", "revision-old",
                {"data": {"result": action_result}},
            ),
            _execution_record(
                "observe-new", "scene.observe", "query", "revision-current",
                {"data": observation}, arguments={"sensor_ref": "camera/front", "max_age_ms": 1000},
            ),
        ],
    )


def test_scene_understand_rejects_agent_supplied_carried_entities():
    class Coordinator:
        def get_task(self, _task_id):
            raise AssertionError("Coordinator must not inspect an Agent-injected carry-forward")

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="scene.understand",
        arguments={"carried_entities": []},
    )))

    assert result["ok"] is False
    assert result["error"]["type"] == "agent_arguments"
    assert "Coordinator-owned" in result["error"]["message"]


def test_observation_bound_query_rejects_agent_authored_lineage_field():
    task = _carry_task()

    class Coordinator:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

        async def invoke_query(self, *_args, **_kwargs):
            raise AssertionError("invalid lineage must be rejected before Gateway invocation")

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="scene.understand",
        arguments={},
        argument_sources={
            "max_capture_skew_ms": {
                "record_id": "observe-new",
                "path": ["arguments", "max_capture_skew_ms"],
            },
        },
    )))

    assert result["ok"] is False
    assert "observation lineage is Coordinator-owned" in result["error"]["message"]


def test_stale_observation_retry_cannot_relax_max_age():
    stale = _execution_record(
        "observe-stale",
        "scene.observe",
        "query",
        "revision-current",
        {"data": {
            "status": "stale",
            "error": {"code": "stale_observation", "message": "too old"},
        }},
        arguments={"sensor_ref": "camera/front", "max_age_ms": 1000},
    )
    task = SimpleNamespace(
        active_revision_id="revision-current",
        active_revision=SimpleNamespace(execution_records=[stale]),
        execution_records=[stale],
    )

    class Coordinator:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

        async def invoke_query(self, *_args, **_kwargs):
            raise AssertionError("relaxed freshness must be rejected before Gateway invocation")

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1",
        tool_id="scene.observe",
        arguments={"sensor_ref": "camera/front", "max_age_ms": 5000},
    )))

    assert result["ok"] is False
    assert "cannot increase max_age_ms from 1000 to 5000" in result["error"]["message"]


def test_scene_understand_injects_only_coordinator_authorized_carry_forward():
    task = _carry_task()

    class Coordinator:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return task

        async def invoke_query(self, task_id, tool_id, arguments, **kwargs):
            assert (task_id, tool_id) == ("task-1", "scene.understand")
            return {"ok": True, "arguments": arguments}

    result = json.loads(asyncio.run(ForgeToolQueryTool(object(), Coordinator()).execute(
        task_id="task-1", tool_id="scene.understand", arguments={},
    )))

    carried = result["arguments"]["carried_entities"]
    assert len(carried) == 1
    assert carried[0]["entity"]["entity_ref"] == "entity://unchanged"
    assert carried[0]["execution_entity_ref"] == "entity://runtime-unchanged"
    assert carried[0]["effect_evidence_refs"] == ["artifact://persistent/action-1"]


@pytest.mark.parametrize(
    "task",
    [
        _carry_task(include_effect=False),
        _carry_task(effect_overrides={"effect_scope_complete": False}),
        _carry_task(effect_overrides={"carry_forward_authorized": False}),
        _carry_task(effect_overrides={"unaffected_entity_refs": []}),
    ],
)
def test_coordinator_does_not_carry_entities_without_complete_runtime_evidence(task):
    assert _coordinator_carried_entities(task, "scene-2") == []
