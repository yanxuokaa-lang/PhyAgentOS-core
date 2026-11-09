# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy>=2,<3", "matplotlib>=3.10,<4"]
# ///
"""Report a paired BoolQ run: uv run evals/report_boolq.py --help."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from metrics import binary_metrics
from metrics import wilson_rate as wilson
from run_files import load_run as load_complete_run
from run_files import read_jsonl

SCALARS = [
    "accuracy",
    "brier",
    "log_loss",
    "mean_top_probability",
    "overconfidence_gap",
    "positive_ece_10",
    "top_ece_10",
]


def load_run(path):
    manifest, rows = load_complete_run(path)
    manifest["execution"] = read_jsonl(path / "execution.jsonl", missing_ok=True)
    return manifest, rows


def bootstrap(runs, draws=2000):
    """Paired resampling by passage, preserving repeated questions about the same passage."""
    groups = runs[0][1]
    _, cluster = np.unique([r["passage_hash"] for r in groups], return_inverse=True)
    count = int(cluster.max()) + 1
    rng = np.random.default_rng(42)
    results = np.empty((draws, len(runs), len(SCALARS)))
    prepared = []
    for _, rows in runs:
        p = np.array([r["p_yes"] for r in rows])
        y = np.array([r["label"] for r in rows], dtype=float)
        correct = ((p >= 0.5) == y).astype(float)
        c = np.maximum(p, 1 - p)
        per_row = np.stack(
            [
                correct,
                (p - y) ** 2,
                -np.log(np.maximum(1e-15, np.where(y, p, 1 - p))),
                c,
                c - correct,
            ]
        )
        prepared.append((p, y, c, correct, per_row))
    for j in range(draws):
        cluster_weights = np.bincount(rng.integers(count, size=count), minlength=count)
        weights = cluster_weights[cluster]
        total = weights.sum()
        for k, (p, y, c, correct, per_row) in enumerate(prepared):
            results[j, k, :5] = per_row @ weights / total
            for offset, (prob, label) in enumerate([(p, y), (c, correct)], start=5):
                bins = np.minimum((prob * 10).astype(int), 9)
                # n_bin * |mean(p)-mean(y)| = |sum(p-y)| within each bin.
                gap = np.bincount(bins, weights=weights * (prob - label), minlength=10)
                results[j, k, offset] = np.abs(gap).sum() / total
    intervals = []
    for k in range(len(runs)):
        intervals.append(
            {
                name: np.quantile(results[:, k, i], [0.025, 0.975]).tolist()
                for i, name in enumerate(SCALARS)
            }
        )
    differences = (
        {
            name: np.quantile(results[:, 0, i] - results[:, 1, i], [0.025, 0.975]).tolist()
            for i, name in enumerate(SCALARS)
        }
        if len(runs) == 2
        else None
    )
    return intervals, differences, count


def chart(models, target, n):
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "DejaVu Sans",
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    colors = ["#2671bd", "#cb583e"]
    for ax in axes[0]:
        ax.plot([0, 1], [0, 1], "--", color="#8a8a8a", lw=1, label="Perfect calibration")
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.grid(alpha=0.18)
    for k, (name, data) in enumerate(models.items()):
        m = data["metrics"]
        for ax, field in zip(axes[0], ["positive_reliability", "top_reliability"], strict=True):
            bins = [b for b in m[field] if b["count"]]
            x = np.array([b["mean_probability"] for b in bins])
            y = np.array([b["observed_frequency"] for b in bins])
            bounds = np.array([wilson(b["observed_frequency"], b["count"]) for b in bins])
            ax.errorbar(
                x,
                y,
                yerr=np.maximum(0, np.stack([y - bounds[:, 0], bounds[:, 1] - y])),
                fmt="o-",
                color=colors[k],
                capsize=3,
                label=name,
                lw=1.6,
            )
        bins = m["positive_reliability"]
        axes[1, 0].bar(
            np.arange(10) + (k - (len(models) - 1) / 2) * 0.36,
            [b["count"] for b in bins],
            width=0.36,
            color=colors[k],
            label=name,
        )
        confident = m["high_certainty"]
        values = [100 * b["errors"] / b["count"] if b["count"] else 0 for b in confident]
        bars = axes[1, 1].bar(
            np.arange(3) + (k - (len(models) - 1) / 2) * 0.36,
            values,
            width=0.36,
            color=colors[k],
            label=name,
        )
        for bar, b in zip(bars, confident, strict=True):
            axes[1, 1].annotate(
                f"n={b['count']:,}",
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )
    axes[0, 0].set(
        title="Probability of yes",
        xlabel="Mean predicted P(yes)",
        ylabel="Observed fraction of yes labels",
    )
    axes[0, 1].set(
        title="Probability of the selected answer",
        xlabel="Mean max(P(yes), P(no))",
        ylabel="Observed accuracy",
    )
    axes[0, 1].set_xlim(0.5, 1)
    axes[1, 0].set(
        title="Where the predictions fall",
        ylabel="Examples",
        xlabel="P(yes) bin (width 0.1)",
        xticks=np.arange(10),
        xticklabels=[f"{i / 10:.1f}" for i in range(10)],
    )
    axes[1, 1].set(
        title="Errors among highly certain answers",
        ylabel="Observed error rate (%)",
        xticks=np.arange(3),
        xticklabels=["≥90%", "≥95%", "≥99%"],
    )
    axes[1, 1].margins(y=0.2)
    for ax in axes.flat:
        ax.legend(fontsize=9)
    fig.suptitle(
        f"BoolQ calibration · {n:,} development examples\n"
        "Raw API probabilities · no fitted calibration",
        fontsize=17,
    )
    fig.savefig(target / "calibration.png", dpi=180)
    fig.savefig(target / "calibration.pdf")
    plt.close(fig)


def reliability_comparison(models, target, n):
    """One shared axis for directly comparing the returned boolean probabilities."""
    fig, ax = plt.subplots(figsize=(8, 7.7))
    fig.subplots_adjust(left=0.12, right=0.96, top=0.84, bottom=0.17)
    fig.suptitle("BoolQ calibration: OpenJev vs Jev", fontsize=19, y=0.97)
    fig.text(
        0.5,
        0.92,
        f"{n:,} shared questions · raw P(yes) · 10 equal-width bins",
        ha="center",
        fontsize=11,
        color="#555555",
    )
    ax.plot([0, 1], [0, 1], "--", color="#777777", lw=1.3, label="Perfect calibration")
    for (name, data), color in zip(models.items(), ["#2671bd", "#cb583e"], strict=True):
        bins = [b for b in data["metrics"]["positive_reliability"] if b["count"]]
        x = [b["mean_probability"] for b in bins]
        y = [b["observed_frequency"] for b in bins]
        bounds = np.array([wilson(b["observed_frequency"], b["count"]) for b in bins])
        ax.fill_between(x, bounds[:, 0], bounds[:, 1], color=color, alpha=0.10)
        ax.plot(x, y, "o-", color=color, lw=2.3, markersize=6, label=name)
    ax.set(
        xlim=(0, 1),
        ylim=(0, 1),
        xlabel="Predicted probability of Yes (bin average)",
        ylabel="Fraction actually labeled Yes",
        xticks=np.linspace(0, 1, 6),
        yticks=np.linspace(0, 1, 6),
    )
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.18)
    ax.legend(loc="upper left", framealpha=0.96, fontsize=11)
    fig.text(
        0.5,
        0.065,
        "Closer to the diagonal means better calibration.\n"
        "Shading: approximate 95% binwise Wilson intervals; sparse bins are less certain.",
        ha="center",
        fontsize=10,
        color="#555555",
        linespacing=1.6,
    )
    fig.savefig(target / "reliability.png", dpi=180)
    fig.savefig(target / "reliability.pdf")
    plt.close(fig)


def main(args):
    paths = [args.openjev, args.jev] if args.jev else [args.openjev]
    runs = [load_run(p) for p in paths]
    names = [
        "Jev / OpenRouter" if manifest["model"].startswith("~typesafe/") else "OpenJev / Qwen3.6"
        for manifest, _ in runs
    ]
    for manifest, rows in runs[1:]:
        for key in ["sha256", "count", "instructions", "state", "criteria"]:
            assert manifest[key] == runs[0][0][key], f"Mismatched protocol: {key}"
        assert [(r["label"], r["passage_hash"]) for r in rows] == [
            (r["label"], r["passage_hash"]) for r in runs[0][1]
        ]
    intervals, paired, clusters = bootstrap(runs, args.bootstrap)
    models = {}
    for name, (manifest, rows), interval in zip(names, runs, intervals, strict=True):
        metrics = binary_metrics([r["p_yes"] for r in rows], [int(r["label"]) for r in rows])
        models[name] = {
            "manifest": manifest,
            "metrics": metrics,
            "bootstrap_95": interval,
            "requests_with_retries": sum(r["attempts"] > 1 for r in rows),
            "response_model_ids": sorted({r["model"] for r in rows}),
            "reported_cost_usd": (
                sum(r["usage"]["cost"] for r in rows)
                if all(r.get("usage") and "cost" in r["usage"] for r in rows)
                else None
            ),
        }
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "models": models,
        "bootstrap": {"draws": args.bootstrap, "seed": 42, "unit": "passage", "clusters": clusters},
        "paired_difference_95_openjev_minus_jev": paired,
    }
    (args.output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    chart(models, args.output, runs[0][0]["count"])
    if len(models) == 2:
        reliability_comparison(models, args.output, runs[0][0]["count"])
    lines = [
        "# BoolQ calibration",
        "",
        f"Evaluated {runs[0][0]['count']:,} labeled development "
        "examples. Passage is the state; the yes/no question is a `noul` question. "
        "Metrics use raw returned P(yes), not the entropy confidence field. "
        "No examples were used to fit temperature or otherwise recalibrate probabilities.",
        "",
        "| Metric | " + " | ".join(names) + " |",
        "|---|" + "---|" * len(names),
    ]
    for key, title, percent in [
        ("accuracy", "Accuracy ↑", True),
        ("brier", "Brier score ↓", False),
        ("log_loss", "Log loss, nats ↓", False),
        ("mean_top_probability", "Mean selected-answer probability", True),
        ("overconfidence_gap", "Mean probability minus accuracy", True),
        ("positive_ece_10", "P(yes) ECE, 10 equal-width bins ↓", True),
        ("top_ece_10", "Selected-answer ECE, 10 equal-width bins ↓", True),
    ]:
        cells = []
        for model in models.values():
            scale = 100 if percent else 1
            v = model["metrics"][key] * scale
            low, high = [x * scale for x in model["bootstrap_95"][key]]
            cells.append(
                f"{v:.2f}% [{low:.2f}, {high:.2f}]"
                if percent
                else f"{v:.4f} [{low:.4f}, {high:.4f}]"
            )
        lines.append(f"| {title} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Intervals: 95% percentile bootstrap, resampling passages together "
        f"({clusters:,} unique passages; {args.bootstrap:,} draws, seed 42). "
        "Paired difference intervals are in metrics.json. ECE depends on binning and has "
        "finite-sample bias; Brier/log loss also reflect predictive skill, not calibration "
        "alone. Brier is mean (P(yes) − label)². Log loss clips true-label probabilities "
        "below 1e-15. Ties at 0.5 predict yes.",
        "",
        "![Calibration](reliability.png)"
        if len(models) == 2
        else "![Calibration](calibration.png)",
        "",
        "[Detailed calibration dashboard](calibration.png)",
        "",
        "Plot error bars are approximate 95% Wilson intervals within bins; the report's "
        "aggregate intervals use passage clustering.",
        "",
        "## Highly certain errors",
        "",
        "| Model | Probability threshold | Examples | Errors | Accuracy | Mean probability |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, model in models.items():
        for b in model["metrics"]["high_certainty"]:
            if b["count"]:
                lines.append(
                    f"| {name} | {b['threshold']:.0%} | {b['count']} | {b['errors']} | "
                    f"{1 - b['errors'] / b['count']:.2%} | {b['mean_probability']:.2%} |"
                )
    lines += [
        "",
        "## Protocol and limits",
        "",
        "- Dataset: [BoolQ](https://github.com/google-research-datasets/boolean-questions), "
        "3,270 labeled development examples (Hugging Face validation split). "
        "The official test labels are hidden.",
        "- Dataset revision, byte hash, exact prompt, endpoint and model are in each run's "
        "manifest.json. Predictions are resumable and indexed by dataset row.",
        "- This is passage-grounded yes/no classification, not unrestricted factual truth "
        "or production-domain calibration. Public benchmark training overlap is unknown.",
        "- Both endpoints receive identical payloads except model ID. Their internal "
        "prompts, model weights and inference procedures can differ.",
        "- Completion is required: the report refuses missing or duplicate predictions.",
        "- BoolQ is released under CC BY-SA 3.0. Raw dataset text is not checked into this repo.",
    ]
    for name, model in models.items():
        lines.append(
            f"- {name}: response model IDs "
            f"{', '.join(model['response_model_ids'])}; "
            f"{model['requests_with_retries']} requests needed retries."
        )
        if model["reported_cost_usd"] is not None:
            lines.append(
                f"- {name}: reported cost for successful responses "
                f"${model['reported_cost_usd']:.4f} (excludes pilot and failed attempts)."
            )
    (args.output / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:15]))
    print(f"Report: {args.output / 'report.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openjev", type=Path, default=Path("evals/runs/boolq"))
    parser.add_argument("--jev", type=Path)
    parser.add_argument("--output", type=Path, default=Path("evals/runs/boolq-report"))
    parser.add_argument("--bootstrap", type=int, default=2000)
    main(parser.parse_args())
