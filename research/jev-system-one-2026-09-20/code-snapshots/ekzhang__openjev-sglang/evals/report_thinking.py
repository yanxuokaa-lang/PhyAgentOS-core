# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.9"]
# ///
"""Render an accuracy/latency curve for a completed thinking_probe.py run."""

import argparse
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from metrics import wilson as wilson_interval


def wilson(correct, n):
    # Preserve the original probe's normal quantile and percentage scale.
    return tuple(100 * x for x in wilson_interval(correct, n, z=1.959963984540054))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    metrics = json.loads((args.run / "metrics.json").read_text())
    manifest = json.loads((args.run / "manifest.json").read_text())
    n = len(manifest["indices"])
    assert all(r["n"] == n for r in metrics.values())
    args.output.mkdir(parents=True, exist_ok=True)
    for name in ("metrics.json", "manifest.json"):
        shutil.copyfile(args.run / name, args.output / name)
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.subplots_adjust(left=0.11, right=0.96, bottom=0.21, top=0.78)
    fig.text(0.11, 0.94, "How much does a little thinking help?", fontsize=19, weight="bold")
    fig.text(0.11, 0.88, f"Qwen3.6-35B-A3B · {n} fresh MMLU-Pro questions", fontsize=12)
    fig.text(
        0.11,
        0.835,
        "Same questions and final-answer format at every budget",
        fontsize=10,
        color="#64748b",
    )
    ax.plot(
        [r["p50_seconds"] for r in metrics.values()],
        [100 * r["accuracy"] for r in metrics.values()],
        color="#cbd5e1",
        zorder=1,
    )
    colors = ["#64748b", "#0d9488", "#2563eb", "#7c3aed"]
    offsets = [(8, -32), (8, -32), (-6, 22), (-12, 22)]
    for (budget, r), color, offset in zip(metrics.items(), colors, offsets, strict=True):
        value = 100 * r["accuracy"]
        low, high = wilson(r["correct"], n)
        ax.errorbar(
            r["p50_seconds"],
            value,
            yerr=[[value - low], [high - value]],
            fmt="o",
            color=color,
            markersize=9,
            capsize=4,
            linewidth=1.5,
            zorder=3,
        )
        title = "No thinking" if budget == "0" else f"{int(budget):,}-token cap"
        ax.annotate(
            f"{title}\n{value:.1f}%",
            (r["p50_seconds"], value),
            xytext=offset,
            textcoords="offset points",
            fontsize=10,
            ha="right" if int(budget) >= 256 else "left",
            color=color,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2},
        )
    ax.set_xscale("log")
    ax.set_xlim(
        min(r["p50_seconds"] for r in metrics.values()) * 0.7,
        max(r["p50_seconds"] for r in metrics.values()) * 1.45,
    )
    lows, highs = zip(*(wilson(r["correct"], n) for r in metrics.values()), strict=True)
    ax.set_ylim(max(0, min(lows) - 8), min(100, max(highs) + 10))
    ax.set_xlabel("Median latency per question, seconds (log scale)", labelpad=12)
    ax.set_ylabel("Accuracy (%)")
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    from matplotlib.ticker import FuncFormatter

    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))
    ax.xaxis.set_minor_formatter(
        FuncFormatter(lambda x, _: f"{x:g}" if x in [0.2, 0.5, 2, 5] else "")
    )
    fig.text(
        0.11,
        0.075,
        "Error bars: 95% Wilson intervals · B200 / NVFP4 · concurrency 16",
        fontsize=9,
        color="#64748b",
    )
    fig.text(
        0.11,
        0.04,
        "Warm container-local timings; excludes network, startup and client queue.",
        fontsize=9,
        color="#64748b",
    )
    fig.savefig(args.output / "comparison.png", dpi=180)
    fig.savefig(args.output / "comparison.pdf")
    plt.close(fig)

    lines = [
        "# Capped reasoning on MMLU-Pro",
        "",
        "![Accuracy versus latency](comparison.png)",
        "",
        "| Reasoning cap | Correct | Accuracy | Median latency | p95 latency "
        "| Mean reasoning tokens | Finished naturally |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for budget, r in metrics.items():
        natural = "—" if budget == "0" else f"{r['natural_end_count']}/{n}"
        lines.append(
            f"| {int(budget):,} | {r['correct']}/{n} | {100 * r['accuracy']:.1f}% "
            f"| {r['p50_seconds']:.2f} s | {r['p95_seconds']:.2f} s "
            f"| {r['mean_reasoning_tokens']:.1f} | {natural} |"
        )
    lines += ["", "Changes versus zero thinking (paired bootstrap, 10,000 draws):", ""]
    for budget, r in metrics.items():
        if budget != "0":
            low, high = r["paired_95_ci"]
            lines.append(
                f"- {int(budget):,} tokens: {100 * r['delta']:+.1f} percentage points "
                f"(95% interval {100 * low:+.1f} to {100 * high:+.1f})."
            )
    lines += [
        "",
        f"The same {n} questions at all budgets; sample seed {manifest['seed']}. "
        "This sample excludes the earlier 1,000-question comparison and 256-question "
        "prompt probe. Two questions were used for a mechanics pilot before the full run; "
        "there was no prompt or sampling tuning based on their accuracy.",
        "",
        "All runs use a plain zero-shot multiple-choice prompt and JSON final-answer prefix. "
        "This differs from the production OpenJev wrapper, so compare budgets within this "
        "table, not against the earlier 58.8% result. Production was not modified.",
        "",
        "Positive budgets enable Qwen's native thinking mode and use temperature 1, "
        "top_p 0.95, top_k 20, presence_penalty 1.5, and per-question sampling seeds. "
        "At the thinking-end token or hard budget cap, the harness closes the thinking "
        "block, appends a JSON answer prefix, and scores one answer token. It selects "
        "the highest label logprob. Test gold labels remain local. No examples or "
        "test rationales are supplied. The prompt does not explicitly coach brevity.",
        "",
        "Budgets run separately in ascending order at concurrency 16; caching stays enabled. "
        "Later runs can benefit from earlier cached prefixes. Latency includes both internal "
        "SGLang requests but excludes external networking, startup, and the client-side "
        "concurrency queue. These are warm serving measurements, not user-facing latency "
        "guarantees. This was one sampled reasoning trace per question/budget; intervals "
        "describe question sampling and do not capture repeat-run variability. Seeds do not "
        "guarantee identical thought prefixes across budgets under different batching.",
        "",
        "The first full attempt stopped because the harness assumed the matched thinking-end "
        "token would remain in output_ids. The Rust frontend can strip it and report it only "
        "in finish_reason. After fixing that parsing, all budgets were rerun. No partial "
        "run results enter this report. Accuracy and latency were not used to change the "
        "protocol. This is an exploratory budget comparison, not a full published-benchmark "
        "reproduction or a probability-calibration result.",
        "",
        "[Collector](../../thinking_probe.py) · [Report script](../../report_thinking.py) · "
        "[Manifest](manifest.json) · [Metrics](metrics.json)",
        "",
    ]
    (args.output / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
