"""Standalone Jev System One intent-routing capability probe.

This adapter shares the intent-routing dataset and scorer contract with the
Decisions probe, but keeps Jev's state/questions request and answer envelope
separate. It records labels only and never imports PAOS.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from decision_intent_probe import (
    INTENTS,
    QUESTION_NAMES,
    RETRY_HTTP,
    ROUTES,
    build_input,
    load_json,
    load_samples,
    probability_metrics,
    validate_samples,
)

JEv_ENDPOINT = "https://www.1949-x.xn--fiqs8s/v1/systemone"
CHOICES: dict[str, list[tuple[str, str]]] = {
    "intent": [
        ("status_query", "查询当前任务进度、状态或结果。"),
        ("task_control", "明确要求暂停、恢复或停止当前任务。"),
        ("clarification_answer", "回答当前明确的待回答问题。"),
        ("new_task", "提出新的执行目标或任务要求。"),
        ("analysis", "请求解释、比较、诊断、讨论或计划分析。"),
        ("conversation", "问候与简单对话，不请求执行任务。"),
        ("mixed_or_unclear", "多个独立正向意图或信息不足以确定意图。"),
    ],
    "route": [
        ("status_read", "查询当前关联任务且 read_status 能力可用。"),
        ("task_control", "明确控制当前任务且请求的具体控制能力可用。"),
        ("clarification_reply", "存在待回答问题，用户消息确实在回答该问题。"),
        ("conversation", "简单对话，不处理任务或复杂问题。"),
        ("system2", "新任务、分析、多意图、歧义、对象缺失或能力不可用。"),
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_endpoint(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("JEV_API_URL must be an https URL without credentials, query, or fragment")
    if parsed.path.rstrip("/") != "/v1/systemone":
        raise ValueError("JEV_API_URL must resolve to /v1/systemone")
    return f"https://{parsed.netloc}/v1/systemone"


def question_definitions() -> dict[str, dict[str, Any]]:
    instructions = {
        "intent": "依据 state 中的最新用户消息、相关短对话和任务状态识别意图；区分正向操作请求与否定、引用、讨论；多个独立正向意图或无法确定时选 mixed_or_unclear。",
        "route": "依据 state 和 capability_state 选择处理路径。只有对象明确且对应能力可用时选择简单路径；新任务、分析、多意图、歧义、对象缺失或能力不可用时选择 system2。只判断，不执行操作。",
    }
    return {
        name: {
            "type": "choice",
            "instructions": instructions[name],
            "criteria": {value: description for value, description in CHOICES[name]},
        }
        for name in QUESTION_NAMES
    }


def build_request(case: dict[str, Any], model: str) -> dict[str, Any]:
    return {
        "model": model,
        "state": json.dumps(build_input(case), ensure_ascii=False, separators=(",", ":")),
        "questions": question_definitions(),
    }


def _write_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _valid_answers(payload: dict[str, Any]) -> tuple[bool, dict[str, Any], str | None]:
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return False, {}, "schema_failure:answers"
    if set(answers) != set(QUESTION_NAMES):
        return False, answers, "schema_failure:question_names"
    for name in QUESTION_NAMES:
        answer = answers[name]
        if not isinstance(answer, dict):
            return False, {}, f"schema_failure:{name}"
        if answer.get("type") != "choice" or answer.get("choice") not in {v for v, _ in CHOICES[name]}:
            return False, {}, f"schema_failure:{name}"
    return True, answers, None


def _request_once(
    client: httpx.Client,
    endpoint: str,
    key: str,
    payload: dict[str, Any],
) -> tuple[int, dict[str, Any], str | None, str | None]:
    try:
        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        try:
            body = response.json()
        except ValueError:
            body = {"raw_error": response.text[:2000]}
        error = None if 200 <= response.status_code < 300 else f"http_{response.status_code}"
        return response.status_code, body, response.headers.get("x-request-id"), error
    except (httpx.TimeoutException, httpx.NetworkError, OSError) as exc:
        return 0, {}, None, f"transport:{type(exc).__name__}"


def _confusion(rows: list[dict[str, Any]], samples: dict[str, dict[str, Any]], prediction: str, gold: str) -> dict[str, dict[str, int]]:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        matrix[samples[row["case_id"]][gold]][row[prediction]] += 1
    return {key: dict(value) for key, value in sorted(matrix.items())}


def score_command(run_dir: Path) -> int:
    run = load_json(run_dir / "run.json")
    config = load_json(Path(run["config_path"]))
    samples = {s["case_id"]: s for s in load_samples(Path(config["dataset_path"]))}
    predictions = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    valid = [p for p in predictions if p.get("intent") in INTENTS and p.get("route") in ROUTES]
    responses = [
        json.loads(line)
        for line in (run_dir / "responses.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    successful_responses = [row for row in responses if row.get("http_status") == 200]
    transport_failures = [row for row in responses if row.get("http_status") == 0]
    usage = Counter()
    for row in successful_responses:
        for name, value in row.get("response", {}).get("usage", {}).items():
            if isinstance(value, int):
                usage[name] += value
    durations = [float(row["duration_seconds"]) for row in successful_responses]
    metric: dict[str, Any] = {
        "backend": "jev_systemone",
        "run_id": run["run_id"],
        "phase": run["phase"],
        "logical_requests": len(predictions),
        "valid_joint_answers": len(valid),
        "answer_coverage": len(valid) / len(predictions) if predictions else 0.0,
        "intent_accuracy": None,
        "route_accuracy": None,
        "joint_accuracy": None,
        "errors": len(predictions) - len(valid),
        "attempts": len(responses),
        "transport_failures": len(transport_failures),
        "retry_attempts": max(0, len(responses) - len(predictions)),
        "latency_seconds": {
            "mean": statistics.fmean(durations) if durations else None,
            "min": min(durations) if durations else None,
            "max": max(durations) if durations else None,
        },
        "usage": dict(usage),
    }
    if valid:
        metric["intent_accuracy"] = sum(p["intent"] == samples[p["case_id"]]["gold_intent"] for p in valid) / len(valid)
        metric["route_accuracy"] = sum(p["route"] == samples[p["case_id"]]["gold_route"] for p in valid) / len(valid)
        metric["joint_accuracy"] = sum(p["intent"] == samples[p["case_id"]]["gold_intent"] and p["route"] == samples[p["case_id"]]["gold_route"] for p in valid) / len(valid)
    metric["probability_metrics"] = {
        "intent": probability_metrics(valid, samples, "intent", INTENTS, "gold_intent"),
        "route": probability_metrics(valid, samples, "route", ROUTES, "gold_route"),
    }
    metric["intent_confusion"] = _confusion(valid, samples, "intent", "gold_intent")
    metric["route_confusion"] = _confusion(valid, samples, "route", "gold_route")
    (run_dir / "metrics.json").write_text(json.dumps(metric, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "report.md").write_text("# Jev intent-routing report\n\n```json\n" + json.dumps(metric, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    print(json.dumps(metric, ensure_ascii=False, indent=2))
    return 0


def run_command(
    config_path: Path,
    phase: str,
    dry_run: bool,
    smoke: bool,
    resume: Path | None,
) -> int:
    config = load_json(config_path)
    samples = load_samples(Path(config["dataset_path"]))
    errors = validate_samples(samples)
    if errors:
        raise ValueError("dataset invalid: " + "; ".join(errors[:5]))
    endpoint = normalize_endpoint(os.environ.get("JEV_API_URL", config["endpoint_base_url"]))
    if resume:
        run_dir = resume
        run = load_json(run_dir / "run.json")
        if run.get("backend") != "jev_systemone" or run.get("phase") != phase:
            raise ValueError("resume run backend/phase does not match this invocation")
        if load_json(run_dir / "config.json") != {**config, "api_key_source": "JEV_API_KEY environment only"}:
            raise ValueError("resume run config does not match the requested config")
        run_id = run["run_id"]
    else:
        run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        run_dir = Path(config["output_root"]) / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "run.json").write_text(json.dumps({"run_id": run_id, "backend": "jev_systemone", "phase": phase, "subset": "smoke" if smoke else "full", "created_at": utc_now(), "config_path": str(config_path.resolve())}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        artifact_config = {**config, "api_key_source": "JEV_API_KEY environment only"}
        (run_dir / "config.json").write_text(json.dumps(artifact_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "environment.json").write_text(json.dumps({"python": sys.version, "platform": platform.platform(), "endpoint_host": urlparse(endpoint).hostname, "endpoint_kind": "jev_systemone", "model_requested": config["model_requested"], "dataset_version": config["dataset_version"], "prompt_version": config["prompt_version"], "started_at": utc_now()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected = [s for s in samples if s["split"] == phase]
    if smoke:
        if phase != "development":
            raise ValueError("--smoke is only valid with --phase development")
        selected = selected[:5]
    existing: dict[str, dict[str, Any]] = {}
    pred_path = run_dir / "predictions.jsonl"
    if pred_path.exists():
        for line in pred_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("phase") == phase and row.get("terminal"):
                    existing[row["case_id"]] = row
    key = os.environ.get("JEV_API_KEY")
    if not dry_run and not key:
        raise ValueError("JEV_API_KEY is required for a network run; use --dry-run for local projection")
    client = httpx.Client(
        timeout=httpx.Timeout(float(config["timeout_seconds"])),
        follow_redirects=False,
    )
    for index, case in enumerate(selected):
        if case["case_id"] in existing:
            continue
        if index and not dry_run:
            time.sleep(float(config.get("inter_request_delay_seconds", 0)))
        logical_id = f"{run_id}:{phase}:{case['case_id']}"
        payload = build_request(case, config["model_requested"])
        _write_jsonl(run_dir / "requests.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "order": index, "state": payload["state"]})
        if dry_run:
            _write_jsonl(run_dir / "predictions.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "terminal": True, "status": "not_called"})
            continue
        chosen = None
        for attempt in range(config["max_transport_retries"] + 1):
            started = time.monotonic()
            attempt_started_at = utc_now()
            _write_jsonl(run_dir / "attempts.jsonl", {"logical_request_id": logical_id, "attempt_index": attempt, "event": "start", "started_at": attempt_started_at})
            status, raw, provider_id, error = _request_once(client, endpoint, key, payload)
            duration = time.monotonic() - started
            _write_jsonl(run_dir / "attempts.jsonl", {"logical_request_id": logical_id, "attempt_index": attempt, "event": "complete", "started_at": attempt_started_at, "completed_at": utc_now(), "duration_seconds": duration, "http_status": status, "provider_request_id": provider_id, "error": error})
            _write_jsonl(run_dir / "responses.jsonl", {"logical_request_id": logical_id, "attempt_index": attempt, "http_status": status, "provider_request_id": provider_id, "duration_seconds": duration, "response": raw})
            valid, answers, schema_error = _valid_answers(raw) if status == 200 else (False, {}, None)
            if valid:
                chosen = {"answers": answers, "attempt_index": attempt, "duration_seconds": duration, "http_status": status, "provider_request_id": provider_id}
                break
            retryable = status in RETRY_HTTP or status == 0
            if retryable and attempt < config["max_transport_retries"]:
                continue
            if not retryable or attempt == config["max_transport_retries"] or schema_error:
                _write_jsonl(run_dir / "errors.jsonl", {"logical_request_id": logical_id, "attempt_index": attempt, "category": error or schema_error or "request_failure", "http_status": status})
                break
        if chosen:
            answers = chosen["answers"]
            _write_jsonl(run_dir / "predictions.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "terminal": True, "intent": answers["intent"]["choice"], "route": answers["route"]["choice"], "answers": answers, "attempt_index": chosen["attempt_index"], "duration_seconds": chosen["duration_seconds"], "provider_request_id": chosen["provider_request_id"]})
        else:
            _write_jsonl(run_dir / "predictions.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "terminal": True, "status": "invalid_or_failed"})
    client.close()
    print(run_dir)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="jev_intent_probe")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--phase", choices=("development", "evaluation"), required=True)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--smoke", action="store_true")
    run.add_argument("--resume", type=Path)
    score = sub.add_parser("score")
    score.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            return run_command(args.config, args.phase, args.dry_run, args.smoke, args.resume)
        return score_command(args.run_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
