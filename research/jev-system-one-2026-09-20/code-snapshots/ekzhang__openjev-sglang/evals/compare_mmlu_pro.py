# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy>=2,<3", "matplotlib>=3.10,<4"]
# ///
"""Compare paired MMLU-Pro runs, including an optional previous OpenJev prompt."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from metrics import paired, wilson
from run_files import load_run

BLUE = "#2671bd"
ORANGE = "#cb583e"


def main(args):
    paths = {"OpenJev": args.openjev, "Jev": args.jev}
    if args.previous:
        paths["OpenJev before"] = args.previous
    runs = {name: load_run(path) for name, path in paths.items()}
    reference, rows = runs["OpenJev"]
    for manifest, other in runs.values():
        for key in ["indices", "sha256", "instructions", "state", "criteria", "shots"]:
            if manifest[key] != reference[key]:
                raise ValueError(f"Mismatched protocol: {key}")
        if [(r["index"], r["answer"], r["category"]) for r in rows] != [
            (r["index"], r["answer"], r["category"]) for r in other
        ]:
            raise ValueError("Mismatched gold labels or subjects")
    correct = {
        name: np.array([r["prediction"] == r["answer"] for r in data])
        for name, (_, data) in runs.items()
    }
    n = len(rows)
    categories = np.array([r["category"] for r in rows])
    subjects = {}
    for category in sorted(set(categories)):
        mask = categories == category
        subjects[category] = {
            "count": int(mask.sum()),
            **{name: float(values[mask].mean()) for name, values in correct.items()},
        }
    overall = {
        name: {
            "correct": int(values.sum()),
            "count": n,
            "accuracy": float(values.mean()),
            "wilson_95": wilson(int(values.sum()), n),
        }
        for name, values in correct.items()
    }
    outcomes = paired(correct["OpenJev"], correct["Jev"])
    prompt_change = paired(correct["OpenJev before"], correct["OpenJev"]) if args.previous else None
    report = {
        "overall": overall,
        "subjects": subjects,
        "openjev_vs_jev": outcomes,
        "prompt_change": prompt_change,
        "bootstrap": {"draws": 10000, "seed": 42, "unit": "question", "paired": True},
        "protocol": {
            "count": n,
            "seed": reference["seed"],
            "shots": 0,
            "description": "Same sampled questions and API payloads except model ID.",
        },
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig = plt.figure(figsize=(14, 9.5), facecolor="white")
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.45, 1],
        height_ratios=[0.72, 1],
        left=0.18,
        right=0.96,
        bottom=0.18,
        top=0.83,
        hspace=0.65,
        wspace=0.3,
    )
    subject_ax = fig.add_subplot(grid[:, 0])
    overall_ax = fig.add_subplot(grid[0, 1])
    paired_ax = fig.add_subplot(grid[1, 1])
    order = sorted(
        subjects, key=lambda c: subjects[c]["Jev"] - subjects[c]["OpenJev"], reverse=True
    )
    for i, category in enumerate(order):
        data = subjects[category]
        a, b = data["OpenJev"] * 100, data["Jev"] * 100
        subject_ax.plot([a, b], [i, i], color="#c5c9cf", lw=2.5, zorder=1)
        subject_ax.scatter(a, i, color=BLUE, s=62, zorder=3, label="OpenJev" if i == 0 else None)
        subject_ax.scatter(b, i, color=ORANGE, s=62, zorder=3, label="Jev" if i == 0 else None)
        subject_ax.text(min(a, b) - 2, i, f"{min(a, b):.0f}", ha="right", va="center", fontsize=9)
        subject_ax.text(max(a, b) + 2, i, f"{max(a, b):.0f}", ha="left", va="center", fontsize=9)
    subject_ax.set(
        yticks=range(len(order)),
        yticklabels=[f"{c.replace('_', ' ').title()}  (n={subjects[c]['count']})" for c in order],
        xlim=(0, 104),
        xticks=range(0, 101, 20),
        xlabel="Accuracy (%)",
    )
    subject_ax.invert_yaxis()
    subject_ax.set_title("Where the gap comes from", loc="left", pad=35, fontweight="bold")
    subject_ax.legend(loc="lower left", bbox_to_anchor=(0, 1.005), ncols=2, frameon=False)
    subject_ax.grid(axis="x", alpha=0.17)
    subject_ax.spines["left"].set_visible(False)
    subject_ax.tick_params(axis="y", length=0, pad=10)

    names = ["Jev", "OpenJev"] + (["OpenJev before"] if args.previous else [])
    chart_names = ["Jev", "OpenJev"]
    colors = [ORANGE, BLUE]
    for i, name in enumerate(chart_names):
        data = overall[name]
        value = data["accuracy"] * 100
        low, high = np.array(data["wilson_95"]) * 100
        overall_ax.errorbar(
            value,
            i,
            xerr=[[value - low], [high - value]],
            fmt="o",
            color=colors[i],
            markersize=8,
            capsize=4,
            lw=2,
        )
        overall_ax.text(high + 1.5, i, f"{value:.1f}%", va="center", fontsize=11, color=colors[i])
    overall_ax.set(
        yticks=range(len(chart_names)),
        yticklabels=chart_names,
        ylim=(len(chart_names) - 0.5, -0.5),
        xlim=(40, 100),
        xticks=[40, 60, 80, 100],
        xlabel="Accuracy (%) · 95% Wilson intervals",
    )
    overall_ax.set_title("Overall accuracy", loc="left", pad=16, fontweight="bold")
    overall_ax.spines["left"].set_visible(False)
    overall_ax.tick_params(axis="y", length=0)
    overall_ax.grid(axis="x", alpha=0.17)

    cells = [
        (0, 0, outcomes["both_correct"], "Both correct", "#e0ece6"),
        (1, 0, outcomes["left_only"], "Only OpenJev", "#e1edf8"),
        (0, 1, outcomes["right_only"], "Only Jev", "#f7e7de"),
        (1, 1, outcomes["both_wrong"], "Both wrong", "#eceef0"),
    ]
    for x, y, count, label, color in cells:
        paired_ax.add_patch(Rectangle((x, y), 1, 1, facecolor=color, edgecolor="white", lw=4))
        paired_ax.text(
            x + 0.5,
            y + 0.38,
            f"{count:,}",
            ha="center",
            va="center",
            fontsize=23,
            fontweight="bold",
        )
        paired_ax.text(
            x + 0.5, y + 0.70, f"{label}\n{count / n:.1%}", ha="center", va="center", fontsize=10
        )
    paired_ax.set(
        xlim=(0, 2),
        ylim=(2, 0),
        xticks=[0.5, 1.5],
        xticklabels=["Jev correct", "Jev wrong"],
        yticks=[0.5, 1.5],
        yticklabels=["OpenJev\ncorrect", "OpenJev\nwrong"],
    )
    paired_ax.xaxis.tick_top()
    paired_ax.tick_params(length=0, pad=9)
    for spine in paired_ax.spines.values():
        spine.set_visible(False)
    paired_ax.set_title("Which questions do they solve?", loc="left", pad=35, fontweight="bold")
    fig.suptitle(
        "MMLU-Pro: OpenJev vs Jev", x=0.08, ha="left", y=0.97, fontsize=24, fontweight="bold"
    )
    fig.text(
        0.08,
        0.92,
        f"{n:,} identical sampled questions · seed {reference['seed']} · zero-shot direct answers",
        fontsize=13,
        color="#555555",
    )
    fig.text(
        0.08,
        0.065,
        "OpenJev: Qwen3.6-35B-A3B NVFP4, one-token scoring. "
        "Updated prompt uses plain option descriptions.\n"
        "Subject results are descriptive; sample sizes vary. "
        "This is not the standard full-test reasoning benchmark.",
        fontsize=10,
        color="#555555",
        linespacing=1.7,
    )
    fig.savefig(args.output / "comparison.png", dpi=180)
    fig.savefig(args.output / "comparison.pdf")
    plt.close(fig)

    lines = [
        "# MMLU-Pro comparison",
        "",
        "![Comparison](comparison.png)",
        "",
        "| Model / prompt | Correct | Accuracy | 95% Wilson interval |",
        "|---|---:|---:|---:|",
    ]
    for name in names:
        d = overall[name]
        lines.append(
            f"| {name} | {d['correct']}/{n} | {d['accuracy']:.1%} | "
            f"{d['wilson_95'][0]:.1%}–{d['wilson_95'][1]:.1%} |"
        )
    lines += [
        "",
        "Jev minus updated OpenJev: "
        f"**{100 * outcomes['right_minus_left']:.1f} percentage points** "
        f"(paired 95% bootstrap interval {100 * outcomes['difference_95'][0]:.1f} "
        f"to {100 * outcomes['difference_95'][1]:.1f}).",
        "",
        f"Both correct: {outcomes['both_correct']}; only Jev correct: {outcomes['right_only']}; "
        f"only OpenJev correct: {outcomes['left_only']}; both wrong: {outcomes['both_wrong']}.",
    ]
    if prompt_change:
        lines += [
            "",
            "Prompt cleanup changed OpenJev accuracy by "
            f"**{100 * prompt_change['right_minus_left']:+.1f} points** "
            f"(paired 95% bootstrap interval {100 * prompt_change['difference_95'][0]:+.1f} "
            f"to {100 * prompt_change['difference_95'][1]:+.1f}). "
            f"It corrected {prompt_change['right_only']} previously wrong answers "
            f"and broke {prompt_change['left_only']} previously correct ones.",
        ]
    lines += [
        "",
        "Same question indices, gold labels, option order, and external API instructions "
        "are verified across runs. Internal models and prompts differ. "
        "The updated OpenJev prompt removes option JSON wrappers and hides keys "
        "when descriptions are supplied; null descriptions fall back to the option name. "
        "Thinking remains disabled and scoring uses one output token.",
        "",
        "Intervals assume independent questions and omit finite-population correction. "
        "Paired differences use 10,000 bootstrap draws, seed 42. "
        "The prompt was revised after inspecting earlier results, so this is a diagnostic "
        "comparison on a reused subset, not an untouched holdout. "
        "No other inference settings were intentionally changed; batch scheduling may also "
        "cause small numerical differences.",
        "",
        "Dataset: [MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro). "
        f"This {n:,}-question, zero-shot API evaluation is not a reproduction of "
        "published full-test chain-of-thought scores.",
    ]
    (args.output / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(report["overall"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--openjev", type=Path, default=Path("evals/runs/mmlu-pro-openjev-simple-options")
    )
    parser.add_argument("--jev", type=Path, default=Path("evals/runs/mmlu-pro-jev"))
    parser.add_argument("--previous", type=Path, default=Path("evals/runs/mmlu-pro-openjev"))
    parser.add_argument(
        "--output", type=Path, default=Path("evals/results/mmlu-pro-2026-09-18/comparison")
    )
    main(parser.parse_args())
