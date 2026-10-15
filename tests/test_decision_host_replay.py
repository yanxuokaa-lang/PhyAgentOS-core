from __future__ import annotations

import asyncio
import json
import runpy
from pathlib import Path

import pytest

from PhyAgentOS.agent.decision_host_replay import (
    HostReplayConfig,
    ReplayCase,
    RequestRecorder,
    build_host,
    evaluate_host_run,
    run_arm,
    sanitized_understanding,
    summarize_pairs,
)
from PhyAgentOS.agent.decision_provider import DecisionResult
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskCoordinator
from PhyAgentOS.providers.base import LLMProvider, LLMResponse, ToolCallRequest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def spec():
    return runpy.run_path(str(ROOT / "examples/forge-skills/pick-place-workflow/src/pick_place_workflow/grounding.py"))["BIND_TOOL_SPEC"]


@pytest.fixture
def facts():
    return {"status": "available", "observation_ref": "observation://test",
            "scene_revision": "scene-test", "calibration_ref": "calibration://test",
            "entities": [{"entity_ref": "entity://red", "category": "red cube"},
                         {"entity_ref": "entity://blue", "category": "blue cube"},
                         {"entity_ref": "entity://surface", "category": "gray surface"}],
            "ambiguities": [{"code": "entity_identity_uncertain", "entity_refs": ["entity://surface"]}]}


def config(tmp_path):
    api = {"endpoint": "https://example.invalid/v1/chat/completions",
           "model": "test", "api_key_env": "REPLAY_TEST_KEY"}
    return HostReplayConfig(snapshot_dir=tmp_path, output_root=tmp_path / "out",
                            jev=api, system2=api,
                            cases=[ReplayCase(goal="Bind the red cube", expected_entity_refs=["entity://red"])])


class Model(LLMProvider):
    def __init__(self, *, unauthorized=False):
        super().__init__()
        self.calls = 0
        self.unauthorized = unauthorized

    def get_default_model(self):
        return "test"

    async def chat(self, messages, tools=None, **kwargs):
        self.calls += 1
        assert {tool["function"]["name"] for tool in tools} <= {"forge_plan_ready", "forge_plan_select"}
        assert str(Path.home()) not in json.dumps(messages)
        return LLMResponse(content=None, tool_calls=[ToolCallRequest(
            id="select", name="forge_tool_start_action" if self.unauthorized else "forge_plan_select",
            arguments={"task_id": "task-host-replay", "node_id": "bind-current", "tool_id": "scene.bind",
                       "arguments": {"entity_refs": ["entity://red"]},
                       "projection_sources": {"understanding": {"record_id": "offline-understanding"}},
                       "decision_reason": "red matches the goal"},
        )])


class Decision:
    def __init__(self, outcome):
        self.outcome, self.calls = outcome, 0

    async def decide(self, request, **kwargs):
        self.calls += 1
        assert len(request.candidates) == 2
        if self.outcome == "cancel":
            raise asyncio.CancelledError
        if self.outcome == "timeout":
            raise asyncio.TimeoutError
        return DecisionResult(outcome=self.outcome,
                              selected_id="query-input-1" if self.outcome == "selected" else None)


@pytest.mark.asyncio
@pytest.mark.parametrize("arm,outcome,llm_calls", [
    ("system2", "selected", 1), ("jev", "selected", 0),
    ("jev", "escalate", 1), ("jev", "timeout", 1),
])
async def test_real_context_selection_and_fallback(tmp_path, facts, spec, arm, outcome, llm_calls):
    cfg = config(tmp_path)
    model, decision = Model(), Decision(outcome)
    result = await run_arm(tmp_path, facts, spec, cfg.cases[0], cfg, model, decision, arm)
    assert result["status"] == "selected", result
    assert result["matches_authored_expectation"] is True
    assert result["node_execution_count"] == 0
    assert model.calls == llm_calls
    assert decision.calls == (arm == "jev")
    reopened = AgentTaskCoordinator(workspace=tmp_path / "workspace", config=ForgeConfig(), client=None)
    task = reopened.get_task("task-host-replay")
    assert len(task.active_revision.planning_selections) == 1
    assert len(task.execution_records) == 1  # offline source only
    assert task.active_revision.node_settlements == []
    assert result["selection"]["planning_binding"]["decision_trace_ref"].startswith("artifact://")


@pytest.mark.asyncio
async def test_cancel_persists_partial_and_never_falls_back(tmp_path, facts, spec):
    cfg, model = config(tmp_path), Model()
    with pytest.raises(asyncio.CancelledError):
        await run_arm(tmp_path, facts, spec, cfg.cases[0], cfg, model, Decision("cancel"), "jev")
    assert model.calls == 0
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "interrupted"


@pytest.mark.asyncio
async def test_unavailable_action_is_not_executed(tmp_path, facts, spec):
    cfg = config(tmp_path)
    cfg.max_iterations = 1
    result = await run_arm(tmp_path, facts, spec, cfg.cases[0], cfg, Model(unauthorized=True), Decision("selected"), "system2")
    assert result["status"] == "failed"
    assert result["selection"] is None
    assert result["node_execution_count"] == 0


def test_offline_import_preserves_ambiguity_and_no_overwrite(tmp_path, facts, spec):
    coord, context, _ = build_host(tmp_path / "workspace", facts, spec, "Select red")
    assert context.scene_bind_selection["recommended_unambiguous_entity_refs"] == ["entity://red", "entity://blue"]
    assert coord.get_task(context.task_id).tool_bindings[0].ready_at_binding is False
    with pytest.raises(FileExistsError):
        build_host(tmp_path / "workspace", facts, spec, "Select red")


def test_sanitization_excludes_images_and_paths(tmp_path, facts):
    facts.update(views=[{"rgb_path": "/private/image.png"}], private="secret")
    (tmp_path / "understanding.json").write_text(json.dumps(facts))
    clean = sanitized_understanding(tmp_path)
    assert "views" not in clean and "private" not in clean
    assert clean["ambiguities"] == facts["ambiguities"]


@pytest.mark.asyncio
async def test_http_budget_counts_attempts_without_credentials(tmp_path):
    import httpx
    recorder = RequestRecorder(tmp_path, 1)
    request = httpx.Request("POST", "https://example.invalid", json={"model": "test"},
                            headers={"Authorization": "Bearer secret"})
    await recorder.request(request)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        await recorder.request(request)
    assert "secret" not in (tmp_path / "requests.json").read_text()
    recorder.finish_pending()
    assert recorder.records[0]["status"] == "no_response"


def test_latency_retains_failures_and_only_counts_correct_substitution():
    rows = [dict(arm="jev", elapsed_ms=1, matches_authored_expectation=True, system2_calls=0, jev_calls=1, status="selected"),
            dict(arm="jev", elapsed_ms=100, system2_calls=1, jev_calls=1, status="failed"),
            dict(arm="system2", elapsed_ms=80, status="failed")]
    result = summarize_pairs(rows)
    assert result["actual_substitutions"] == 1
    assert result["latency"]["jev"]["mean_ms"] == 50.5
    assert result["latency"]["jev"]["p95_ms"] == 100


def test_export_uses_actual_host_trace_and_cannot_enable_active(tmp_path):
    cfg = config(tmp_path)
    (tmp_path / "config.json").write_text(cfg.model_dump_json())
    rows = []
    for arm in ("jev", "system2"):
        folder = tmp_path / "case-0" / arm
        folder.mkdir(parents=True)
        (folder / "context.json").write_text('{"source":"offline"}')
        (folder / "candidates.json").write_text(json.dumps([
            {"candidate_id": "query-input-1", "description": "red", "arguments": {"entity_refs": ["entity://red"]}},
            {"candidate_id": "query-input-2", "description": "blue", "arguments": {"entity_refs": ["entity://blue"]}},
        ]))
        rows.append({"case_index": 0, "arm": arm, "system2_calls": 0 if arm == "jev" else 1, "elapsed_ms": 1 if arm == "jev" else 2})
    (tmp_path / "report.json").write_text(json.dumps({"status": "completed", "results": rows}))
    (tmp_path / "requests.json").write_text(json.dumps([{"arm": "case-0/system2", "response": {"model": "test-version"}}]))
    (tmp_path / "host.log").write_text("Agent decision " + json.dumps({
        "outcome": "selected", "model_version": "jev-test", "selected_candidate_id": "query-input-1",
        "decision_trace_ref": "artifact://test/selection",
    }) + "\n")
    summary = evaluate_host_run(tmp_path, repo_root=ROOT)
    assert summary.active_eligible is False and summary.exit_code == 2
    metrics = json.loads((summary.run_dir / "metrics.json").read_text())
    assert metrics["active_eligibility_checks"]["actual_substitution_observed"] is True
    (tmp_path / "case-0/system2/context.json").write_text('{"source":"different"}')
    with pytest.raises(ValueError, match="contexts differ"):
        evaluate_host_run(tmp_path, repo_root=ROOT)
