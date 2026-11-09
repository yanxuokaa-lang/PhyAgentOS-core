"""Calibration metrics and accuracy intervals; no network or plotting dependencies."""

import math


def reliability(probabilities, outcomes, bins=10):
    groups = [[] for _ in range(bins)]
    for p, y in zip(probabilities, outcomes, strict=True):
        if not math.isfinite(p) or not 0 <= p <= 1 or y not in (0, 1):
            raise ValueError("Expected finite probabilities and binary labels")
        groups[min(int(p * bins), bins - 1)].append((p, y))
    result = []
    for i, group in enumerate(groups):
        n = len(group)
        mean_p = sum(p for p, _ in group) / n if n else None
        frequency = sum(y for _, y in group) / n if n else None
        result.append(
            {
                "lower": i / bins,
                "upper": (i + 1) / bins,
                "count": n,
                "mean_probability": mean_p,
                "observed_frequency": frequency,
            }
        )
    return result


def binary_metrics(probabilities, labels):
    if not probabilities or len(probabilities) != len(labels):
        raise ValueError("Need equal nonempty probability and label arrays")
    n = len(labels)
    positive_bins = reliability(probabilities, labels)
    correct = [int((p >= 0.5) == bool(y)) for p, y in zip(probabilities, labels, strict=True)]
    certainty = [max(p, 1 - p) for p in probabilities]
    top_bins = reliability(certainty, correct)

    def ece(groups):
        return (
            sum(
                g["count"] * abs(g["mean_probability"] - g["observed_frequency"])
                for g in groups
                if g["count"]
            )
            / n
        )

    losses = [
        -math.log(max(1e-15, p if y else 1 - p)) for p, y in zip(probabilities, labels, strict=True)
    ]
    return {
        "n": n,
        "positive_rate": sum(labels) / n,
        "accuracy": sum(correct) / n,
        "brier": sum((p - y) ** 2 for p, y in zip(probabilities, labels, strict=True)) / n,
        "log_loss": sum(losses) / n,
        "mean_top_probability": sum(certainty) / n,
        "overconfidence_gap": (sum(certainty) - sum(correct)) / n,
        "positive_ece_10": ece(positive_bins),
        "top_ece_10": ece(top_bins),
        "positive_reliability": positive_bins,
        "top_reliability": top_bins,
        "high_certainty": [
            {
                "threshold": threshold,
                "count": sum(c >= threshold for c in certainty),
                "errors": sum(
                    not ok for c, ok in zip(certainty, correct, strict=True) if c >= threshold
                ),
                "mean_probability": (
                    sum(c for c in certainty if c >= threshold)
                    / sum(c >= threshold for c in certainty)
                    if any(c >= threshold for c in certainty)
                    else None
                ),
            }
            for threshold in [0.9, 0.95, 0.99]
        ],
    }


def wilson(correct, n, *, z=1.96):
    return wilson_rate(correct / n, n, z=z)


def wilson_rate(p, n, *, z=1.96):
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [float(center - half), float(center + half)]


def paired(left, right):
    import numpy as np

    counts = np.bincount(left.astype(int) * 2 + right.astype(int), minlength=4)
    # Outcome order: both wrong, right only, left only, both correct.
    draws = np.random.default_rng(42).multinomial(len(left), counts / len(left), size=10000)
    differences = (draws[:, 1] - draws[:, 2]) / len(left)
    return {
        "both_wrong": int(counts[0]),
        "right_only": int(counts[1]),
        "left_only": int(counts[2]),
        "both_correct": int(counts[3]),
        "right_minus_left": float(right.mean() - left.mean()),
        "difference_95": np.quantile(differences, [0.025, 0.975]).tolist(),
    }
