"""Run the prepared ten-question request on one GPU and persist timings/results."""

import argparse
import json
import os
import platform
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import torch
import transformers

from litjev.backend import ModelSettings, TransformersScorer
from litjev.benchmark import evaluate
from litjev.decision import SchemaDecisionEngine
from litjev.schema import DecisionSchema, SystemOneRequest
from litjev.slots import SLOT_FORMAT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", default="mmlu-request-preview.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--sequential", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("Benchmark requires exactly one visible CUDA GPU")
    prepared = json.loads(Path(args.input).read_text())
    request = SystemOneRequest.model_validate(prepared["runs"][0]["request"])
    schema = request.to_schema()
    labels = prepared["labels"]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "job_id": os.environ.get("SLURM_JOB_ID"),
        "hostname": platform.node(),
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "model_path": args.model,
        "dataset": prepared["dataset"],
        "dataset_revision": prepared["revision"],
        "split": prepared["split"],
        "protocol": "first ten test questions; direct label scoring; no CoT",
        "mode": "sequential_single_question" if args.sequential else "two_forward_cached_branches",
        "slot_format": SLOT_FORMAT,
        "calibration_fitted": False,
        "request": request.model_dump(),
        "labels": labels,
        "runs": [],
    }
    torch.cuda.synchronize()
    loading = time.perf_counter()
    scorer = TransformersScorer.load(ModelSettings(model_id=args.model, device_map="cuda:0"))
    torch.cuda.synchronize()
    report["model_load_seconds"] = time.perf_counter() - loading
    engine = SchemaDecisionEngine(scorer, model_id="Qwen/Qwen3.8-27B")
    calls = []
    hook = scorer.model.register_forward_pre_hook(
        lambda model, inputs, kwargs: calls.append(list(kwargs["input_ids"].shape)),
        with_kwargs=True,
    )
    print(f"Model loaded in {report['model_load_seconds']:.3f}s", flush=True)
    for index in range(4):
        calls.clear()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        inference = time.perf_counter()
        evaluation, per_question = evaluate(engine, schema, args.sequential, torch.cuda.synchronize)
        response = evaluation.result
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - inference
        expected_calls = 20 if args.sequential else 2
        if len(calls) != expected_calls:
            raise RuntimeError(f"Expected {expected_calls} forwards, observed {len(calls)}")
        correct = sum(a.choice == labels[key] for key, a in response.answers.items())
        report["runs"].append(
            {
                "phase": "cold" if index == 0 else "warm",
                "elapsed_seconds": elapsed,
                "per_question_seconds": per_question,
                "observed_forward_calls": len(calls),
                "observed_input_shapes": list(calls),
                "correct": correct,
                "count": 10,
                "accuracy": correct / 10,
                "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "response": asdict(response),
                "diagnostics": evaluation.diagnostics,
            }
        )
        report["total_seconds"] = time.perf_counter() - started
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Run {index}: {correct}/10, {elapsed:.3f}s", flush=True)
    hook.remove()
    schemas = (
        [DecisionSchema({name: field}) for name, field in schema.items()]
        if args.sequential
        else [schema]
    )
    report["input_audit"] = []
    for item in schemas:
        compiled = scorer._compile("Answer each question using its listed options.", item)
        report["input_audit"].append(
            {
                "question_ids": list(item),
                "input_ids": compiled.input_ids,
                "decoded_input": [scorer.tokenizer.decode(row) for row in compiled.input_ids],
                "slot_positions": compiled.positions,
            }
        )
    output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
