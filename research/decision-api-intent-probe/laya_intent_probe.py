"""Local Laya intent-routing capability probe.

Run this module with the dedicated Laya interpreter. It shares the fixed
dataset and label contract with the remote probes and never imports PAOS.
"""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import platform
import statistics
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_intent_probe import (
    INTENTS,
    ROUTES,
    build_input,
    load_json,
    load_samples,
    probability_metrics,
    question_definitions,
    validate_samples,
)

CHECKPOINTS = ("english", "multilingual", "typed-decisions")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def laya_questions() -> dict[str, dict[str, Any]]:
    return {
        question["name"]: {
            "type": question["type"],
            "instructions": question["instructions"],
            "criteria": {
                choice["value"]: choice["description"]
                for choice in question["choices"]
            },
        }
        for question in question_definitions()
    }


def _write_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _confusion(
    rows: list[dict[str, Any]],
    samples: dict[str, dict[str, Any]],
    prediction: str,
    gold: str,
) -> dict[str, dict[str, int]]:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        matrix[samples[row["case_id"]][gold]][row[prediction]] += 1
    return {key: dict(value) for key, value in sorted(matrix.items())}


def score_command(run_dir: Path) -> int:
    run = load_json(run_dir / "run.json")
    config = load_json(Path(run["config_path"]))
    samples = {
        sample["case_id"]: sample
        for sample in load_samples(Path(config["dataset_path"]))
    }
    predictions = [
        json.loads(line)
        for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    valid = [
        row
        for row in predictions
        if row.get("intent") in INTENTS and row.get("route") in ROUTES
    ]
    durations = [float(row["duration_seconds"]) for row in valid]
    metric: dict[str, Any] = {
        "backend": "laya_local",
        "checkpoint": run["checkpoint"],
        "run_id": run["run_id"],
        "phase": run["phase"],
        "logical_requests": len(predictions),
        "valid_joint_answers": len(valid),
        "answer_coverage": len(valid) / len(predictions) if predictions else 0.0,
        "intent_accuracy": None,
        "route_accuracy": None,
        "joint_accuracy": None,
        "errors": len(predictions) - len(valid),
        "latency_seconds": {
            "mean": statistics.fmean(durations) if durations else None,
            "min": min(durations) if durations else None,
            "max": max(durations) if durations else None,
        },
    }
    if valid:
        metric["intent_accuracy"] = sum(
            row["intent"] == samples[row["case_id"]]["gold_intent"] for row in valid
        ) / len(valid)
        metric["route_accuracy"] = sum(
            row["route"] == samples[row["case_id"]]["gold_route"] for row in valid
        ) / len(valid)
        metric["joint_accuracy"] = sum(
            row["intent"] == samples[row["case_id"]]["gold_intent"]
            and row["route"] == samples[row["case_id"]]["gold_route"]
            for row in valid
        ) / len(valid)
    metric["probability_metrics"] = {
        "intent": probability_metrics(valid, samples, "intent", INTENTS, "gold_intent"),
        "route": probability_metrics(valid, samples, "route", ROUTES, "gold_route"),
    }
    metric["intent_confusion"] = _confusion(valid, samples, "intent", "gold_intent")
    metric["route_confusion"] = _confusion(valid, samples, "route", "gold_route")
    (run_dir / "metrics.json").write_text(
        json.dumps(metric, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "report.md").write_text(
        "# Laya local intent-routing report\n\n```json\n"
        + json.dumps(metric, ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    print(json.dumps(metric, ensure_ascii=False, indent=2))
    return 0


def run_command(config_path: Path, checkpoint: str, phase: str, smoke: bool) -> int:
    import laya
    import torch

    config = load_json(config_path)
    samples = load_samples(Path(config["dataset_path"]))
    errors = validate_samples(samples)
    if errors:
        raise ValueError("dataset invalid: " + "; ".join(errors[:5]))
    if checkpoint not in CHECKPOINTS:
        raise ValueError(f"checkpoint must be one of {CHECKPOINTS}")

    selected = [sample for sample in samples if sample["split"] == phase]
    if smoke:
        if phase != "development":
            raise ValueError("--smoke is only valid with --phase development")
        selected = selected[:5]

    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    run_dir = Path(config["output_root"]) / checkpoint / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "backend": "laya_local",
                "checkpoint": checkpoint,
                "phase": phase,
                "subset": "smoke" if smoke else "full",
                "created_at": utc_now(),
                "config_path": str(config_path.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    load_started = time.perf_counter()
    agent = laya.load(checkpoint, device=config["device"])
    load_seconds = time.perf_counter() - load_started
    environment = {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "laya_version": importlib.metadata.version("laya"),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": str(agent.device),
        "checkpoint": checkpoint,
        "checkpoint_revision": getattr(agent, "revision", None),
        "load_seconds": load_seconds,
        "dataset_version": config["dataset_version"],
        "prompt_version": config["prompt_version"],
        "route_policy_version": config["route_policy_version"],
        "started_at": utc_now(),
    }
    (run_dir / "environment.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    questions = laya_questions()
    for index, case in enumerate(selected):
        logical_id = f"{run_id}:{phase}:{case['case_id']}"
        state = build_input(case)
        _write_jsonl(
            run_dir / "requests.jsonl",
            {
                "logical_request_id": logical_id,
                "case_id": case["case_id"],
                "phase": phase,
                "order": index,
                "state": state,
            },
        )
        started = time.perf_counter()
        try:
            response = agent.predict(state, questions)
            duration = time.perf_counter() - started
            answers = response.get("answers") if isinstance(response, dict) else None
            _write_jsonl(
                run_dir / "responses.jsonl",
                {
                    "logical_request_id": logical_id,
                    "duration_seconds": duration,
                    "response": response,
                },
            )
            if not isinstance(answers, dict):
                raise ValueError("Laya response has no answers object")
            intent = answers.get("intent", {}).get("choice")
            route = answers.get("route", {}).get("choice")
            if intent not in INTENTS or route not in ROUTES:
                raise ValueError("Laya response contains an unknown choice")
            _write_jsonl(
                run_dir / "predictions.jsonl",
                {
                    "logical_request_id": logical_id,
                    "case_id": case["case_id"],
                    "phase": phase,
                    "terminal": True,
                    "intent": intent,
                    "route": route,
                    "answers": answers,
                    "duration_seconds": duration,
                },
            )
        except (RuntimeError, ValueError, TypeError) as exc:
            duration = time.perf_counter() - started
            _write_jsonl(
                run_dir / "errors.jsonl",
                {
                    "logical_request_id": logical_id,
                    "category": type(exc).__name__,
                    "message": str(exc),
                    "duration_seconds": duration,
                },
            )
            _write_jsonl(
                run_dir / "predictions.jsonl",
                {
                    "logical_request_id": logical_id,
                    "case_id": case["case_id"],
                    "phase": phase,
                    "terminal": True,
                    "status": "invalid_or_failed",
                    "duration_seconds": duration,
                },
            )
    del agent
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(run_dir)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="laya_intent_probe")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--checkpoint", choices=CHECKPOINTS, required=True)
    run.add_argument("--phase", choices=("development", "evaluation"), required=True)
    run.add_argument("--smoke", action="store_true")
    score = sub.add_parser("score")
    score.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            return run_command(args.config, args.checkpoint, args.phase, args.smoke)
        return score_command(args.run_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
