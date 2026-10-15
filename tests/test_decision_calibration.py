from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from PhyAgentOS.agent.decision_calibration import (
    CalibrationConfig,
    ProbeAPI,
    build_probe_request,
    collect_calibration,
    extract_calibration,
)
from PhyAgentOS.agent.decision_evaluation import DecisionEvaluationDataset


def _source(tmp_path):
    db = tmp_path / "tasks.sqlite3"
    with sqlite3.connect(db) as connection:
        connection.executescript(
            "CREATE TABLE agent_tasks (task_id TEXT, record_json TEXT, created_at TEXT, "
            "updated_at TEXT, origin_session_key TEXT);"
            "CREATE TABLE agent_task_events (event_id INTEGER, task_id TEXT, "
            "event_type TEXT, created_at TEXT, payload_json TEXT);"
        )
        time = "2026-10-13T00:00:00+00:00"
        task = {"task_description": "PRIVATE-GOAL", "revisions": [{
            "revision_id": "revision-private", "execution_records": [
                {"record_id": "record-private", "semantics": "action", "status": "unknown",
                 "created_at": time, "response": {"data": {"status": "unknown", "secret": "PRIVATE"}}},
                {"record_id": "query-private", "semantics": "query", "status": "succeeded",
                 "created_at": time, "response": {"data": {"status": "unavailable"}}},
            ],
        }]}
        connection.execute("INSERT INTO agent_tasks VALUES (?, ?, ?, ?, ?)",
                           ("task-private", json.dumps(task), time, time, "cli:rgb-test-1"))
        error = {"error": {"code": "tool_input_schema_invalid", "message": "PRIVATE",
                           "missing_fields": ["calibration_ref", "observation_ref", "scene_revision"]}}
        connection.execute("INSERT INTO agent_task_events VALUES (?, ?, ?, ?, ?)",
                           (1, "task-private", "planning_selection_rejected", time, json.dumps(error)))
    return db


def _extract(tmp_path):
    db = _source(tmp_path)
    original = db.read_bytes()
    directory = extract_calibration(
        database=db, since="2026-10-12T00:00:00+00:00", until="2026-10-15T00:00:00+00:00",
        session_prefix="cli:rgb-", output_root=tmp_path / "extracted", repo_root=Path.cwd(),
    )
    assert db.read_bytes() == original
    return directory


def _config(tmp_path, monkeypatch):
    directory = _extract(tmp_path)
    monkeypatch.setenv("PROBE_TEST_KEY", "test-key-do-not-persist")
    api = {"endpoint": "https://example.test/api", "model": "test-model", "api_key_env": "PROBE_TEST_KEY"}
    config = directory / "config.json"
    config.write_text(json.dumps({"dataset": "dataset.json", "output_root": "runs",
                                  "jev": api, "system2": api, "max_cases": 3, "max_requests": 6}))
    return config


def test_extract_is_read_only_sanitized_and_not_independent(tmp_path):
    directory = _extract(tmp_path)
    text = (directory / "dataset.json").read_text()
    assert "PRIVATE" not in text and "task-private" not in text and "revision-private" not in text
    dataset = DecisionEvaluationDataset.model_validate_json(text)
    assert len(dataset.cases) == 3 and dataset.planned_held_out_cases == 0
    assert {case.split for case in dataset.cases} == {"calibration"}
    assert dataset.labeler_id == dataset.reviewer_id
    provenance = json.loads((directory / "source_manifest.json").read_text())
    assert provenance["source_record_count"] == 3 and provenance["family_count"] == 1
    assert provenance["sources"]["missing_identity"][0]["event_id"] == 1


def test_requests_do_not_leak_gold_or_provenance(tmp_path):
    dataset = DecisionEvaluationDataset.model_validate_json((_extract(tmp_path) / "dataset.json").read_text())
    case = dataset.cases[0]
    a = build_probe_request(case, arm="jev", model="jev", max_tokens=512)
    b = build_probe_request(case, arm="system2", model="sol", max_tokens=512)
    assert json.loads(a["state"]) == json.loads(b["messages"][1]["content"])["state"]
    assert a["questions"]["decision"]["criteria"] == json.loads(b["messages"][1]["content"])["criteria"]
    for payload in (a, b):
        text = json.dumps(payload)
        for forbidden in ("expected_selected_id", "reviewer_id", "decision_input_ref", "source_manifest", "case_id"):
            assert forbidden not in text


@pytest.mark.asyncio
async def test_real_http_shape_pairs_no_host_claim_and_evaluator(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch)
    calls = []

    def respond(request):
        body = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer test-key-do-not-persist"
        calls.append("jev" if "questions" in body else "system2")
        if "questions" in body:
            return httpx.Response(200, json={"model": "observed-jev-version",
                "answers": {"decision": {"type": "choice", "choice": "option-1"}}})
        return httpx.Response(200, json={"model": "observed-sol-version", "choices": [
            {"message": {"content": '{"choice":"option-1"}'}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        directory = await collect_calibration(config, repo_root=Path.cwd(), client=client)
    assert calls == ["jev", "system2", "system2", "jev", "jev", "system2"]
    manifest = json.loads((directory / "collection_manifest.json").read_text())
    report = json.loads((Path(manifest["evaluation_run_dir"]) / "acceptance_report.json").read_text())
    assert manifest["completed_pairs"] == 3
    assert (directory / "collector_source" / "decision_calibration.py").is_file()
    assert (directory / "source_manifest.json").is_file()
    assert (directory / "label_review.json").is_file()
    assert report["active_eligible"] is False
    assert {"measured_evidence", "held_out_only", "independent_label_review",
            "host_admission_evaluated", "actual_substitution_observed"} <= set(report["ineligibility_reasons"])
    rows = json.loads((directory / "measurements.json").read_text())["records"]
    assert all(row["host_outcome"] == "not_evaluated" and not row["system2_invoked"] for row in rows)
    assert rows[0]["model_version"] == "observed-jev-version"
    assert all("test-key-do-not-persist" not in file.read_text() for file in directory.rglob("*.json"))


@pytest.mark.asyncio
async def test_failures_remain_in_denominator_and_no_retries(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch)
    calls = 0

    def respond(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("secret diagnostic must not be persisted")
        if calls == 2:
            return httpx.Response(503, json={"error": "private upstream details"})
        if calls == 3:
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={"model": "observed", "answers": {}, "choices": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        directory = await collect_calibration(config, repo_root=Path.cwd(), client=client)
    assert calls == 6
    rows = json.loads((directory / "measurements.json").read_text())["records"]
    assert rows[0]["provider_outcome"] == "timeout" and len(rows) == 3
    assert rows[0]["model_version"] is None
    for file in directory.rglob("*.json"):
        assert "secret diagnostic" not in file.read_text()
        assert "private upstream details" not in file.read_text()


@pytest.mark.asyncio
async def test_missing_credential_stops_before_network(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch)
    monkeypatch.delenv("PROBE_TEST_KEY")
    with pytest.raises(ValueError, match="credential"):
        await collect_calibration(config, repo_root=Path.cwd())
    assert not (config.parent / "runs").exists()


@pytest.mark.asyncio
async def test_request_cap_stops_before_network(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch)
    data = json.loads(config.read_text())
    data["max_requests"] = 2
    config.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="max_requests"):
        await collect_calibration(config, repo_root=Path.cwd())


@pytest.mark.asyncio
async def test_cancellation_keeps_completed_arm_without_inventing_pair(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch)
    calls = 0

    def respond(request):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise asyncio.CancelledError()
        return httpx.Response(200, json={"answers": {"decision": {"type": "choice", "choice": "escalate"}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(asyncio.CancelledError):
            await collect_calibration(config, repo_root=Path.cwd(), client=client)
    directory = next((config.parent / "runs").iterdir())
    manifest = json.loads((directory / "collection_manifest.json").read_text())
    assert manifest["status"] == "interrupted" and manifest["completed_pairs"] == 0
    assert len(list(directory.glob("*.jev.json"))) == 1
    assert not (directory / "measurements.json").exists()


@pytest.mark.parametrize("endpoint", ["http://example.test", "https://key@example.test", "https://example.test/?key=x"])
def test_no_credentials_in_endpoint(endpoint):
    with pytest.raises(ValueError, match="HTTPS"):
        ProbeAPI(endpoint=endpoint, model="test", api_key_env="TEST_KEY")


def test_calibration_config_excludes_embedded_keys():
    with pytest.raises(ValueError):
        CalibrationConfig.model_validate({"api_key": "do-not-store"})
