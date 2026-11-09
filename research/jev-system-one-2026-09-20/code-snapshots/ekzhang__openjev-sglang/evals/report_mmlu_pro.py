# /// script
# requires-python = ">=3.12"
# ///
"""Summarize a completed Jev/OpenJev MMLU-Pro run without calling an API."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from metrics import wilson
from run_files import load_run


def summarize(rows, manifest, output):
    name = "Jev" if manifest["model"] == "~typesafe/jev-latest" else "OpenJev"
    if sorted(r["index"] for r in rows) != sorted(manifest["indices"]):
        raise ValueError("Report requires every sampled question exactly once")
    n = len(rows)
    correct = sum(r["prediction"] == r["answer"] for r in rows)
    accuracy = correct / n
    low, high = wilson(correct, n)
    groups = defaultdict(list)
    for r in rows:
        groups[r["category"]].append(r["prediction"] == r["answer"])
    result = {
        "manifest": manifest,
        "correct": correct,
        "count": n,
        "accuracy": accuracy,
        "wilson_95": [low, high],
        "response_model_ids": sorted({r["model"] for r in rows}),
        "reported_cost_usd": (
            sum(r["usage"]["cost"] for r in rows)
            if all("cost" in r.get("usage", {}) for r in rows)
            else None
        ),
        "requests_with_retries": sum(r["attempts"] > 1 for r in rows),
        "subjects": {
            name: {
                "correct": sum(values),
                "count": len(values),
                "accuracy": sum(values) / len(values),
            }
            for name, values in sorted(groups.items())
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        f"# {name} on a random MMLU-Pro subset",
        "",
        f"**{accuracy:.2%} accuracy ({correct:,}/{n:,})**; approximate 95% Wilson interval "
        f"{low:.2%}–{high:.2%}.",
        "",
        f"Sampled {n:,} test questions uniformly without replacement, seed {manifest['seed']}. "
        "This is a subset estimate, not a full-test score. The interval treats questions as "
        "independent and does not apply a finite-population correction.",
        "",
        f"Zero-shot direct answers through {name}'s `choice` endpoint. "
        "State contains only the question; criteria map original answer letters to option text. "
        "No gold answers or provided rationales enter the request. The API's selected choice "
        "is scored by exact match. No retries based on correctness.",
        "",
        "This differs from the benchmark's usual five-shot chain-of-thought setup; "
        "do not treat it as a reproduction of published leaderboard scores. "
        "Public benchmark training overlap is unknown.",
        "",
        f"Resolved model: {', '.join(result['response_model_ids'])}. "
        + (
            f"Successful-response cost: ${result['reported_cost_usd']:.4f}. "
            if result["reported_cost_usd"] is not None
            else "API response cost unavailable. "
        )
        + f"Saved responses with in-run retries: {result['requests_with_retries']} "
        "(excludes attempts from interrupted collection segments).",
        "",
        "| Subject | Correct | Questions | Accuracy |",
        "|---|---:|---:|---:|",
    ]
    for name, g in result["subjects"].items():
        lines.append(f"| {name} | {g['correct']} | {g['count']} | {g['accuracy']:.2%} |")
    lines += [
        "",
        "Source: [TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) "
        "([official evaluation](https://github.com/TIGER-AI-Lab/MMLU-Pro)). "
        "The pinned revision, dataset hash, sampled row indices, prompt, and request settings "
        "are recorded in metrics.json. Raw dataset text is not committed.",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    print(lines[2], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest, rows = load_run(args.run)
    summarize(rows, manifest, args.output)
