"""Standalone Decisions API intent-routing capability probe.

This module intentionally has no PAOS imports. It owns only dataset validation,
request/response recording, and offline scoring.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

INTENTS = (
    "status_query",
    "task_control",
    "clarification_answer",
    "new_task",
    "analysis",
    "conversation",
    "mixed_or_unclear",
)
ROUTES = ("status_read", "task_control", "clarification_reply", "conversation", "system2")
TASK_STATUSES = ("none", "executing", "paused", "waiting_for_user", "terminal")
CONTROL_OPS = ("pause", "resume", "stop")
QUESTION_NAMES = ("intent", "route")
RETRY_HTTP = {408, 429, 500, 502, 503, 504}
PROBABILITY_EPSILON = 1e-12


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_samples(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
    return rows


def normalize_endpoint(value: str, expected_host: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ValueError("DECISIONS_API_URL must use https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("DECISIONS_API_URL must not contain credentials, query, or fragment")
    if parsed.hostname != expected_host:
        raise ValueError(f"endpoint host {parsed.hostname!r} does not match config host {expected_host!r}")
    path = parsed.path.rstrip("/")
    if path in ("", "/v1"):
        path = "/v1/decisions"
    if path != "/v1/decisions":
        raise ValueError("DECISIONS_API_URL must resolve to /v1/decisions")
    return f"https://{parsed.netloc}/v1/decisions"


def _capability_state_valid(state: dict[str, Any]) -> None:
    required = {"has_current_task", "task_ref", "task_status", "task_goal_summary", "pending_clarification", "capabilities"}
    if set(state) != required:
        raise ValueError(f"capability_state fields must be {sorted(required)}")
    has_task = state["has_current_task"]
    status = state["task_status"]
    if not isinstance(has_task, bool) or status not in TASK_STATUSES:
        raise ValueError("invalid has_current_task/task_status")
    if has_task != (status != "none"):
        raise ValueError("has_current_task must match task_status != none")
    if has_task:
        if not isinstance(state["task_ref"], str) or not state["task_ref"].startswith("synthetic:"):
            raise ValueError("task_ref must use synthetic namespace")
    elif state["task_ref"] is not None or state["task_goal_summary"] is not None:
        raise ValueError("no-task state must have null task_ref/task_goal_summary")
    pending = state["pending_clarification"]
    if set(pending) != {"present", "question_summary"}:
        raise ValueError("invalid pending_clarification fields")
    if pending["present"] != bool(pending["question_summary"]):
        raise ValueError("pending clarification presence must match question_summary")
    caps = state["capabilities"]
    if set(caps) != {"read_status", "pause", "resume", "stop"} or not all(isinstance(v, bool) for v in caps.values()):
        raise ValueError("invalid capability booleans")
    if not has_task and any(caps.values()):
        raise ValueError("no-task state cannot advertise task capabilities")
    if status == "terminal" and any(caps[k] for k in CONTROL_OPS):
        raise ValueError("terminal task cannot advertise control capabilities")


def validate_samples(samples: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    families: dict[str, str] = {}
    split_counts = Counter()
    for index, case in enumerate(samples):
        prefix = f"case[{index}]"
        required = {"case_id", "family_id", "split", "message", "recent_turns", "capability_state", "gold_intent", "gold_route", "gold_control_operations", "gold_reason", "tags", "annotation_status", "source_kind"}
        missing = required - set(case)
        if missing:
            errors.append(f"{prefix}: missing {sorted(missing)}")
            continue
        case_id, family, split = case["case_id"], case["family_id"], case["split"]
        if case_id in ids:
            errors.append(f"{prefix}: duplicate case_id {case_id}")
        ids.add(case_id)
        previous_split = families.setdefault(family, split)
        if previous_split != split:
            errors.append(f"{prefix}: family crosses split")
        if split not in {"development", "evaluation"}:
            errors.append(f"{prefix}: invalid split")
        split_counts[split] += 1
        if case["gold_intent"] not in INTENTS or case["gold_route"] not in ROUTES:
            errors.append(f"{prefix}: invalid gold label")
        if not isinstance(case["gold_control_operations"], list) or any(op not in CONTROL_OPS for op in case["gold_control_operations"]):
            errors.append(f"{prefix}: invalid gold_control_operations")
        if case["source_kind"] != "synthetic" or case["annotation_status"] != "adjudicated":
            errors.append(f"{prefix}: only adjudicated synthetic cases are allowed")
        try:
            _capability_state_valid(case["capability_state"])
        except ValueError as exc:
            errors.append(f"{prefix}: {exc}")
        if case["gold_intent"] == "conversation" and case["gold_route"] != "conversation":
            errors.append(f"{prefix}: conversation intent requires conversation route")
        if case["gold_route"] == "status_read" and not (case["capability_state"]["has_current_task"] and case["capability_state"]["capabilities"]["read_status"]):
            errors.append(f"{prefix}: status_read requires current task/read_status")
        if case["gold_route"] == "task_control" and not any(case["capability_state"]["capabilities"].get(op, False) for op in case["gold_control_operations"]):
            errors.append(f"{prefix}: task_control requires requested capability")
    if split_counts != Counter({"development": 20, "evaluation": 60}):
        errors.append(f"split counts must be 20/60, got {dict(split_counts)}")
    return errors


def question_definitions() -> list[dict[str, Any]]:
    return [
        {"type": "choice", "name": "intent", "instructions": "依据最新用户消息、相关短对话和任务状态识别用户意图。区分正向操作请求与否定、引用、讨论；多个独立正向意图或无法确定时选 mixed_or_unclear。", "choices": [{"value": v, "description": d} for v, d in [("status_query", "查询当前任务进度、状态或结果。"), ("task_control", "明确要求暂停、恢复或停止当前任务。"), ("clarification_answer", "回答当前明确的待回答问题。"), ("new_task", "提出新的执行目标或任务要求。"), ("analysis", "请求解释、比较、诊断、讨论或计划分析。"), ("conversation", "问候与简单对话，不请求执行任务。"), ("mixed_or_unclear", "多个独立正向意图或信息不足以确定意图。")]]},
        {"type": "choice", "name": "route", "instructions": "根据原始消息、相关短对话和 capability_state 选择处理路径。只有对象明确且对应 capability 为 true 时选择简单状态、控制或澄清路径；新任务、分析、多意图、歧义、对象缺失或能力不可用时选择 system2。只判断，不执行操作。", "choices": [{"value": v, "description": d} for v, d in [("status_read", "查询当前关联任务（包括可查询的 terminal task），且 read_status 能力可用。"), ("task_control", "明确控制当前任务，且请求的具体控制能力可用。"), ("clarification_reply", "存在待回答问题，用户消息确实在回答该问题。"), ("conversation", "简单对话，不处理任务或复杂问题。"), ("system2", "新任务、分析、多意图、歧义、对象缺失或能力不可用。")]]},
    ]


def build_input(case: dict[str, Any]) -> dict[str, Any]:
    return {"message": case["message"], "recent_turns": case["recent_turns"], "capability_state": case["capability_state"]}


def build_request(case: dict[str, Any], model: str) -> dict[str, Any]:
    return {"model": model, "input": json.dumps(build_input(case), ensure_ascii=False, separators=(",", ":")), "questions": question_definitions()}


def probability_metrics(
    rows: list[dict[str, Any]],
    samples: dict[str, dict[str, Any]],
    question: str,
    labels: tuple[str, ...],
    gold_field: str,
    bins: int = 10,
) -> dict[str, Any]:
    """Score complete multiclass probability distributions on valid answers."""
    scored: list[tuple[list[float], str]] = []
    label_set = set(labels)
    for row in rows:
        answer = row.get("answers", {}).get(question, {})
        raw = answer.get("probabilities")
        if not isinstance(raw, dict) or set(raw) != label_set:
            continue
        values = [raw[label] for label in labels]
        if not all(isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 for value in values):
            continue
        total = math.fsum(values)
        if total <= 0:
            continue
        probabilities = [float(value) / total for value in values]
        scored.append((probabilities, samples[row["case_id"]][gold_field]))

    result: dict[str, Any] = {
        "samples": len(scored),
        "coverage": len(scored) / len(rows) if rows else 0.0,
        "ece_10_bin": None,
        "brier_multiclass": None,
        "nll": None,
        "nll_epsilon": PROBABILITY_EPSILON,
    }
    if not scored:
        return result

    brier_total = 0.0
    nll_total = 0.0
    calibration_bins: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for probabilities, gold in scored:
        gold_index = labels.index(gold)
        brier_total += math.fsum(
            (probability - (1.0 if index == gold_index else 0.0)) ** 2
            for index, probability in enumerate(probabilities)
        )
        nll_total -= math.log(max(probabilities[gold_index], PROBABILITY_EPSILON))
        confidence = max(probabilities)
        predicted_label = labels[probabilities.index(confidence)]
        bin_index = min(int(confidence * bins), bins - 1)
        calibration_bins[bin_index].append((confidence, predicted_label == gold))

    ece = 0.0
    for bucket in calibration_bins:
        if not bucket:
            continue
        mean_confidence = math.fsum(item[0] for item in bucket) / len(bucket)
        accuracy = sum(item[1] for item in bucket) / len(bucket)
        ece += len(bucket) / len(scored) * abs(accuracy - mean_confidence)
    result.update(
        {
            "ece_10_bin": ece,
            "brier_multiclass": brier_total / len(scored),
            "nll": nll_total / len(scored),
        }
    )
    return result


def _write_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _valid_answers(payload: dict[str, Any]) -> tuple[bool, dict[str, Any], str | None]:
    answers = payload.get("answers")
    if not isinstance(answers, list):
        return False, {}, "schema_failure:answers"
    found: dict[str, Any] = {}
    for answer in answers:
        if not isinstance(answer, dict) or answer.get("name") in found:
            return False, {}, "schema_failure:duplicate_or_invalid_answer"
        name = answer.get("name")
        if name not in QUESTION_NAMES:
            return False, {}, "schema_failure:unknown_question"
        if name in QUESTION_NAMES:
            if answer.get("type") == "refusal":
                return False, {}, f"refusal:{name}"
            if answer.get("type") != "choice" or not isinstance(answer.get("choice"), str):
                return False, {}, f"schema_failure:{name}"
            found[name] = answer
    if set(found) != set(QUESTION_NAMES):
        return False, found, "schema_failure:missing_question"
    return True, found, None


def _request_once(endpoint: str, key: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any], str | None, str | None]:
    request = Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw), response.headers.get("x-request-id"), None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw_error": raw[:2000]}
        return exc.code, body, exc.headers.get("x-request-id"), f"http_{exc.code}"
    except (URLError, TimeoutError, OSError) as exc:
        return 0, {}, None, f"transport:{type(exc).__name__}"


def _artifact_environment(config: dict[str, Any], endpoint: str) -> dict[str, Any]:
    return {"python": sys.version, "platform": platform.platform(), "runner": "decision_intent_probe", "runner_version": "0.1.0", "endpoint_host": urlparse(endpoint).hostname, "endpoint_kind": config["endpoint_kind"], "model_requested": config["model_requested"], "dataset_version": config["dataset_version"], "prompt_version": config["prompt_version"], "route_policy_version": config["route_policy_version"], "started_at": utc_now()}


def validate_command(config_path: Path) -> int:
    config = load_json(config_path)
    dataset_path = Path(config["dataset_path"])
    samples = load_samples(dataset_path)
    errors = validate_samples(samples)
    if config["model_requested"] != "gpt-6-luna":
        errors.append("model_requested must be gpt-6-luna")
    if config["endpoint_host"] != "api.shuaiapi.com":
        errors.append("this validation config must target api.shuaiapi.com")
    try:
        normalize_endpoint(os.environ.get("DECISIONS_API_URL", config["endpoint_base_url"]), config["endpoint_host"])
    except ValueError as exc:
        errors.append(str(exc))
    probe = {"message": "x", "recent_turns": [], "capability_state": samples[0]["capability_state"]}
    request = build_request({**samples[0], "message": "x", "recent_turns": []}, config["model_requested"])
    serialized = request["input"]
    if any(secret in serialized for secret in ("gold_intent", "gold_route", "annotation_status", "case_id")):
        errors.append("request input contains local-only fields")
    if json.loads(serialized) != probe:
        errors.append("request input projection mismatch")
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print(f"valid: {len(samples)} samples (development={sum(s['split']=='development' for s in samples)}, evaluation={sum(s['split']=='evaluation' for s in samples)})")
    return 0


def run_command(config_path: Path, phase: str, dry_run: bool, resume: Path | None, smoke: bool) -> int:
    config = load_json(config_path)
    samples = load_samples(Path(config["dataset_path"]))
    errors = validate_samples(samples)
    if errors:
        raise ValueError("dataset invalid: " + "; ".join(errors[:5]))
    endpoint = normalize_endpoint(os.environ.get("DECISIONS_API_URL", config["endpoint_base_url"]), config["endpoint_host"])
    if resume:
        run_dir = resume
        run_id = load_json(run_dir / "run.json")["run_id"]
    else:
        run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        run_dir = Path(config["output_root"]) / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "run.json").write_text(json.dumps({"run_id": run_id, "phase": phase, "subset": "smoke" if smoke else "full", "created_at": utc_now(), "config_path": str(config_path.resolve())}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "environment.json").write_text(json.dumps(_artifact_environment(config, endpoint), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected = [s for s in samples if s["split"] == phase]
    if smoke:
        if phase != "development":
            raise ValueError("--smoke is only valid with --phase development")
        selected = selected[:5]
    existing = {}
    pred_path = run_dir / "predictions.jsonl"
    if pred_path.exists():
        for line in pred_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("phase") == phase and row.get("terminal"):
                    existing[row["case_id"]] = row
    key = os.environ.get("DECISIONS_API_KEY")
    if not dry_run and not key:
        raise ValueError("DECISIONS_API_KEY is required for a network run; use --dry-run for local projection")
    for index, case in enumerate(selected):
        if case["case_id"] in existing:
            continue
        logical_id = f"{run_id}:{phase}:{case['case_id']}:repeat0"
        payload = build_request(case, config["model_requested"])
        if dry_run:
            _write_jsonl(run_dir / "requests.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "order": index, "input": payload["input"], "dry_run": True})
            _write_jsonl(run_dir / "predictions.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "terminal": True, "dry_run": True, "status": "not_called"})
            continue
        _write_jsonl(run_dir / "requests.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "order": index, "input": payload["input"]})
        chosen = None
        for attempt in range(config["max_transport_retries"] + 1):
            started = time.monotonic()
            attempt_started_at = utc_now()
            _write_jsonl(run_dir / "attempts.jsonl", {"logical_request_id": logical_id, "attempt_index": attempt, "event": "start", "started_at": attempt_started_at})
            status, raw, provider_id, error = _request_once(endpoint, key, payload, config["timeout_seconds"])
            duration = time.monotonic() - started
            _write_jsonl(run_dir / "attempts.jsonl", {"logical_request_id": logical_id, "attempt_index": attempt, "event": "complete", "started_at": attempt_started_at, "completed_at": utc_now(), "duration_seconds": duration, "http_status": status, "provider_request_id": provider_id, "error": error})
            _write_jsonl(run_dir / "responses.jsonl", {"logical_request_id": logical_id, "attempt_index": attempt, "http_status": status, "provider_request_id": provider_id, "duration_seconds": duration, "response": raw})
            valid, answers, schema_error = _valid_answers(raw)
            if valid:
                chosen = {"answers": answers, "attempt_index": attempt, "duration_seconds": duration, "http_status": status, "provider_request_id": provider_id}
                break
            retryable = status in RETRY_HTTP or status == 0
            if not retryable or schema_error:
                _write_jsonl(run_dir / "errors.jsonl", {"logical_request_id": logical_id, "attempt_index": attempt, "category": schema_error or error or "request_failure", "http_status": status})
                break
        if chosen:
            predictions = {name: chosen["answers"][name] for name in QUESTION_NAMES}
            _write_jsonl(run_dir / "predictions.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "terminal": True, "intent": predictions["intent"]["choice"], "route": predictions["route"]["choice"], "answers": predictions, "attempt_index": chosen["attempt_index"], "duration_seconds": chosen["duration_seconds"], "provider_request_id": chosen["provider_request_id"]})
        else:
            _write_jsonl(run_dir / "predictions.jsonl", {"logical_request_id": logical_id, "case_id": case["case_id"], "phase": phase, "terminal": True, "status": "invalid_or_failed"})
    print(run_dir)
    return 0


def score_command(run_dir: Path) -> int:
    run = load_json(run_dir / "run.json")
    samples = {s["case_id"]: s for s in load_samples(Path(load_json(Path(run["config_path"]))["dataset_path"]))}
    predictions = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    valid = [p for p in predictions if p.get("intent") in INTENTS and p.get("route") in ROUTES]
    metric: dict[str, Any] = {"run_id": run["run_id"], "phase": run["phase"], "logical_requests": len(predictions), "valid_joint_answers": len(valid), "intent_accuracy": None, "route_accuracy": None, "joint_accuracy": None, "errors": len(predictions) - len(valid)}
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
    (run_dir / "report.md").write_text("# Decisions intent-routing report\n\n```json\n" + json.dumps(metric, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    print(json.dumps(metric, ensure_ascii=False, indent=2))
    return 0


def _confusion(rows: list[dict[str, Any]], samples: dict[str, dict[str, Any]], prediction: str, gold: str) -> dict[str, dict[str, int]]:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        matrix[samples[row["case_id"]][gold]][row[prediction]] += 1
    return {key: dict(value) for key, value in sorted(matrix.items())}


def compare_command(left: Path, right: Path) -> int:
    left_metrics, right_metrics = load_json(left / "metrics.json"), load_json(right / "metrics.json")
    print(json.dumps({"left": left_metrics, "right": right_metrics}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="decision_intent_probe")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--config", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--phase", choices=("development", "evaluation"), required=True)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--smoke", action="store_true", help="run the first five development cases")
    run.add_argument("--resume", type=Path)
    score = sub.add_parser("score")
    score.add_argument("--run-dir", type=Path, required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("--left", type=Path, required=True)
    compare.add_argument("--right", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            return validate_command(args.config)
        if args.command == "run":
            return run_command(args.config, args.phase, args.dry_run, args.resume, args.smoke)
        if args.command == "score":
            return score_command(args.run_dir)
        return compare_command(args.left, args.right)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
