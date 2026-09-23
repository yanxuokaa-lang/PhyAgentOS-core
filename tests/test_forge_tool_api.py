from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.tools.forge_tool_api import (
    ForgeToolQueryTool,
    ForgeToolStartActionTool,
    _call,
    _effective_query_timeout_ms,
    _task_query_source_records,
)
from PhyAgentOS.forge.tool_client import ForgeToolAPITimeoutError


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
def test_task_query_copies_exact_source_fields_and_keeps_literal_arguments(
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
            arguments={},
            response=observation,
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
        arguments={"max_age_ms": 1000},
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
    assert "not visible" in result["error"]["message"]


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
        tool_id="scene.understand",
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
