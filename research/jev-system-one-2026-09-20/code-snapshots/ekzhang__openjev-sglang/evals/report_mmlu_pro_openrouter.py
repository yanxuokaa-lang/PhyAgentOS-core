# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy>=2,<3", "matplotlib>=3.10,<4"]
# ///
"""Offline comparison of a hosted one-token MMLU-Pro run against Jev and OpenJev."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from metrics import paired, wilson
from run_files import load_run


def report(run, output, reference_path, jev_path):
    manifest, rows = load_run(run)
    reference, baseline = load_run(reference_path)
    jev_manifest, jev = load_run(jev_path)
    indices = set(manifest["indices"])
    for other_manifest in [reference, jev_manifest]:
        if other_manifest["sha256"] != manifest["sha256"]:
            raise ValueError("Dataset mismatch")
    baseline = [r for r in baseline if r["index"] in indices]
    jev = [r for r in jev if r["index"] in indices]

    def identity(data):
        return [(r["index"], r["question_id"], r["answer"], r["category"]) for r in data]

    if identity(rows) != identity(baseline) or identity(rows) != identity(jev):
        raise ValueError("Mismatched question identities or gold labels")
    runs = {"OpenJev · Qwen3.6-35B-A3B": baseline, "Qwen3.8-27B · Parasail": rows, "Jev": jev}
    correct = {
        name: np.array([r["prediction"] == r["answer"] for r in rr]) for name, rr in runs.items()
    }
    overall = {
        name: {
            "correct": int(v.sum()),
            "count": len(v),
            "accuracy": float(v.mean()),
            "wilson_95": wilson(int(v.sum()), len(v)),
        }
        for name, v in correct.items()
    }
    ours = correct["Qwen3.8-27B · Parasail"]
    subjects = {
        c: {
            "count": sum(r["category"] == c for r in rows),
            **{
                name: float(v[[r["category"] == c for r in rows]].mean())
                for name, v in correct.items()
            },
        }
        for c in sorted({r["category"] for r in rows})
    }
    metrics = {
        "overall": overall,
        "subjects": subjects,
        "qwen38_minus_openjev": paired(correct["OpenJev · Qwen3.6-35B-A3B"], ours),
        "qwen38_minus_jev": paired(correct["Jev"], ours),
        "unresolved": sum(r["prediction"] is None for r in rows),
        "all_labels_returned": sum(r["all_labels_returned"] for r in rows),
        "response_models": sorted({r["model"] for r in rows}),
        "response_providers": sorted({r["provider"] for r in rows}),
        "completion_tokens": sum(r["usage"]["completion_tokens"] for r in rows),
        "reasoning_tokens": sum(
            r["usage"]["completion_tokens_details"]["reasoning_tokens"] for r in rows
        ),
        "reported_cost_usd": sum(r["usage"].get("cost", 0) for r in rows),
        "requests_with_retries": sum(r["attempts"] > 1 for r in rows),
        "request_latency_median_s": float(np.median([r["latency_s"] for r in rows])),
        "manifest": manifest,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    lines = [
        "# Qwen3.8-27B: one-token MMLU-Pro",
        "",
        "| Model/service | Correct | Accuracy | 95% Wilson CI |",
        "|---|---:|---:|---:|",
    ]
    for name, m in overall.items():
        lo, hi = m["wilson_95"]
        lines.append(
            f"| {name} | {m['correct']}/{m['count']} | {m['accuracy']:.1%} | {lo:.1%}–{hi:.1%} |"
        )
    lines += [
        "",
        f"Same {len(rows)} test questions from the earlier seed-42 sample. "
        "Qwen3.8 uses zero-shot plain multiple-choice chat through OpenRouter, pinned to Parasail, "
        "thinking disabled, max_tokens=1, temperature=1, top_p=1, no logit bias. "
        "Prediction is the highest-logprob exact uppercase answer label, not the sampled token.",
        "",
        "The services share questions and option order, but their prompt wrappers and backends "
        "differ. OpenJev uses its state/question wrapper and an answer prefix; this hosted "
        "run uses the plain prompt saved in the manifest. Jev's internal computation is unknown. "
        "This is a service comparison, not an isolated model ablation or a reproduction of "
        "five-shot chain-of-thought leaderboard scores.",
        "",
        f"Unresolved (no valid label in top-20): {metrics['unresolved']}; these count wrong. "
        f"All answer labels returned: {metrics['all_labels_returned']}/{len(rows)}. "
        "If any valid label is returned, its argmax over valid labels is determined even when "
        "other labels are omitted. Missing probabilities are not treated as zero; no calibration "
        "metrics are computed from truncated distributions.",
        "",
        f"Reported output: {metrics['completion_tokens']} tokens, "
        f"{metrics['reasoning_tokens']} reasoning tokens. "
        f"Successful-response cost: ${metrics['reported_cost_usd']:.4f}. "
        f"Requests with retries: {metrics['requests_with_retries']}.",
        "",
    ]
    for key in ["qwen38_minus_openjev", "qwen38_minus_jev"]:
        m = metrics[key]
        lo, hi = m["difference_95"]
        lines.append(
            f"{key}: {m['right_minus_left'] * 100:+.1f} percentage points "
            f"(paired bootstrap 95% interval {lo * 100:+.1f} to {hi * 100:+.1f}; "
            "10,000 draws, seed 42, resampled question pairs)."
        )
    lines += [
        "",
        "![Comparison](comparison.png)",
        "",
        "## Subject breakdown",
        "",
        "| Subject | Questions | OpenJev | Qwen3.8 | Jev |",
        "|---|---:|---:|---:|---:|",
    ]
    for c, m in subjects.items():
        values = " | ".join(f"{m[name]:.1%}" for name in runs)
        lines.append(f"| {c} | {m['count']} | {values} |")
    (output / "report.md").write_text("\n".join(lines) + "\n")
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 7), gridspec_kw={"width_ratios": [1.8, 1]})
    colors = ["#2671bd", "#289675", "#cb583e"]
    cats = sorted(subjects, key=lambda c: subjects[c]["Qwen3.8-27B · Parasail"])
    for name, color in zip(runs, colors, strict=True):
        ax.scatter(
            [subjects[c][name] * 100 for c in cats], range(len(cats)), label=name, color=color, s=40
        )
    ax.set(
        yticks=range(len(cats)),
        yticklabels=[f"{c.replace('_', ' ').title()} ({subjects[c]['count']})" for c in cats],
        xlim=(0, 103),
        xlabel="Accuracy (%)",
        title="Accuracy by subject (question count)",
    )
    for i, m in enumerate(overall.values()):
        value = m["accuracy"] * 100
        lo, hi = np.array(m["wilson_95"]) * 100
        bx.errorbar(
            value, i, xerr=[[value - lo], [hi - value]], fmt="o", color=colors[i], capsize=4
        )
        bx.text(value, i + 0.18, f"{value:.1f}%", ha="center", color=colors[i], fontweight="bold")
    bx.set(
        yticks=range(3),
        yticklabels=["OpenJev", "Qwen3.8-27B", "Jev"],
        ylim=(-0.5, 2.6),
        xlim=(40, 95),
        xlabel="Accuracy (%) · 95% Wilson intervals",
        title="Overall",
    )
    for a in (ax, bx):
        a.grid(axis="x", alpha=0.2)
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"MMLU-Pro · same {len(rows):,} questions", fontsize=19)
    fig.legend(
        *ax.get_legend_handles_labels(),
        loc="lower center",
        ncols=3,
        frameon=False,
        bbox_to_anchor=(0.5, 0.04),
    )
    fig.text(
        0.5,
        0.025,
        "Zero-shot service comparison; prompt wrappers differ. "
        "Qwen runs generate one answer token; Jev internals unknown.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.11, 1, 0.94))
    fig.savefig(output / "comparison.png", dpi=160)
    fig.savefig(output / "comparison.pdf")
    plt.close(fig)
    print(
        json.dumps(
            {k: v for k, v in metrics.items() if k not in {"subjects", "manifest"}}, indent=2
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, nargs="?", default=Path("evals/runs/qwen38-27b"))
    parser.add_argument("--output", type=Path, default=Path("evals/results/qwen38-27b"))
    parser.add_argument(
        "--reference", type=Path, default=Path("evals/runs/mmlu-pro-openjev-simple-options")
    )
    parser.add_argument("--jev", type=Path, default=Path("evals/runs/mmlu-pro-jev"))
    args = parser.parse_args()
    report(args.run, args.output, args.reference, args.jev)
