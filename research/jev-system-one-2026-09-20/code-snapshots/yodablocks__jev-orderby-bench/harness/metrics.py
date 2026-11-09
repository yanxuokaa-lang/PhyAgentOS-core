"""Calibration and ranking metrics for the Phase 1 gate.

Two families, because the build spec's gate as written measures the wrong
thing for half the product.

Calibration (Brier, ECE) answers "is 0.7 really 70%". It is the right
question for `jev_bool`, where the probability is surfaced to the caller
and thresholded.

Ranking (Spearman, pairwise inversion) answers "does sorting by this put
rows in the right order". That is what semantic ORDER BY actually does.
The two come apart in both directions:

  - A model whose probabilities are all squashed into [0.4, 0.6] but
    perfectly ordered has terrible ECE and sorts perfectly.
  - A model that is well calibrated in aggregate can still invert many
    individual pairs, and sorts badly.

So a gate on ECE alone can kill a model that sorts fine, or pass one that
sorts badly. Report both, gate on both.

Brier and ECE are classification metrics and do not apply to a continuous
Score. For Score we report rank metrics against the human labels, plus
the scale, because Score returns a probability-weighted mean over level
*indices*: range 0..len(rubric)-1, not 0..1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats


# --- calibration -------------------------------------------------------

def brier(probs: np.ndarray, labels: np.ndarray) -> float:
    """Mean squared error of probabilistic predictions. Lower is better."""
    p, y = np.asarray(probs, float), np.asarray(labels, float)
    return float(np.mean((p - y) ** 2))


def brier_decomposition(probs, labels, n_bins: int = 10) -> dict:
    """Murphy decomposition: Brier = reliability - resolution + uncertainty.

    Worth reporting because it separates two failure modes the single
    Brier number conflates. High reliability means the probabilities are
    wrong. Low resolution means they are uninformative: the model says
    0.5 to everything. A model can get a respectable Brier by predicting
    the base rate every time, and that model is useless for ORDER BY.
    """
    p, y = np.asarray(probs, float), np.asarray(labels, float)
    base = y.mean()
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)

    reliability = resolution = 0.0
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            continue
        w = m.sum() / len(p)
        reliability += w * (p[m].mean() - y[m].mean()) ** 2
        resolution += w * (y[m].mean() - base) ** 2

    return {
        "reliability": float(reliability),   # lower better
        "resolution": float(resolution),     # higher better
        "uncertainty": float(base * (1 - base)),
        "brier": brier(p, y),
    }


def ece(probs, labels, n_bins: int = 10, adaptive: bool = True) -> dict:
    """Expected calibration error.

    Adaptive (equal-mass) binning by default. With ~120 rows per primitive
    type, fixed-width bins leave some bins nearly empty, and an empty bin's
    error is pure noise that still gets weighted into the total. Equal-mass
    bins put the same number of samples in each, so every bin's estimate
    has comparable variance.

    Returns the bin table too, because a single ECE number hides whether
    the error is one bad bin or a systematic slope.
    """
    p, y = np.asarray(probs, float), np.asarray(labels, float)
    n = len(p)
    if n == 0:
        return {"ece": float("nan"), "mce": float("nan"), "bins": [], "n": 0}

    if adaptive:
        # Stable sort: Jev returns two-decimal probabilities, so ties are
        # common and a tie group often straddles a bin boundary. With an
        # unstable sort, which side of the boundary a tied row lands on
        # depends on input order, and bin-level numbers (observed rate,
        # gap, Wilson interval, MCE) change between runs over identical
        # data. The caller supplies rows in a canonical order.
        order = np.argsort(p, kind="stable")
        splits = np.array_split(order, min(n_bins, n))
    else:
        edges = np.linspace(0, 1, n_bins + 1)
        idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
        splits = [np.where(idx == b)[0] for b in range(n_bins)]

    total, mce, table = 0.0, 0.0, []
    for s in splits:
        if len(s) == 0:
            continue
        conf, acc = p[s].mean(), y[s].mean()
        gap = abs(conf - acc)
        total += (len(s) / n) * gap
        mce = max(mce, gap)
        # Wilson interval: the honest uncertainty on this bin's accuracy.
        lo, hi = _wilson(y[s].sum(), len(s))
        table.append(
            {
                "n": int(len(s)),
                "mean_pred": float(conf),
                "observed": float(acc),
                "gap": float(gap),
                "ci_low": lo,
                "ci_high": hi,
                "p_min": float(p[s].min()),
                "p_max": float(p[s].max()),
            }
        )

    return {
        "ece": float(total),
        "mce": float(mce),          # worst single bin
        "bins": table,
        "n": int(n),
        "n_bins_used": len(table),
        "binning": "adaptive" if adaptive else "fixed",
    }


def _wilson(successes: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    phat = successes / n
    denom = 1 + z**2 / n
    centre = (phat + z**2 / (2 * n)) / denom
    half = z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / denom
    lo, hi = max(0.0, centre - half), min(1.0, centre + half)
    # The interval contains phat analytically, but at phat = 1 the float
    # arithmetic can land at 0.9999999999999999, and a bound that sits
    # a hair inside the observed rate gives the reliability diagram a
    # negative error bar, which matplotlib refuses.
    return (float(min(lo, phat)), float(max(hi, phat)))


# --- ranking: what ORDER BY actually depends on ------------------------

def pairwise_inversions(scores, labels) -> dict:
    """Fraction of discordant pairs among pairs the ground truth orders.

    This is the direct measure of whether ORDER BY works. Ties in the
    predicted score are counted as half-discordant: a tie gives the sort
    no information, and which row surfaces first is then arbitrary.
    """
    s, y = np.asarray(scores, float), np.asarray(labels, float)
    comparable = discordant = ties = 0
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            if y[i] == y[j]:
                continue          # ground truth has no opinion on this pair
            comparable += 1
            higher_i = y[i] > y[j]
            if s[i] == s[j]:
                ties += 1
                discordant += 0.5
            elif (s[i] > s[j]) != higher_i:
                discordant += 1
    if comparable == 0:
        return {"inversion_rate": float("nan"), "comparable_pairs": 0, "ties": 0}
    return {
        "inversion_rate": float(discordant / comparable),
        "comparable_pairs": int(comparable),
        "tied_pairs": int(ties),
    }


def sort_key_resolution(values, ks=(10, 20, 50, 100)) -> dict:
    """How much ordering information the sort key actually carries.

    Independent of labels. ORDER BY over a probability only orders rows
    whose probabilities differ; rows that share a value come back in
    whatever order the engine's sort left them, which is not stable
    across runs or thread counts. So for `ORDER BY p DESC LIMIT k` the
    question is whether the cut at k falls inside a group of tied rows.
    If it does, the result is a sample of that group, not a ranking.
    """
    v = np.asarray(values, float)
    n = len(v)
    if n == 0:
        return {"n": 0}
    uniq, counts = np.unique(v, return_counts=True)
    pairs = n * (n - 1) // 2
    tied = int(sum(c * (c - 1) // 2 for c in counts))
    decimals = 0
    for x in v:
        s = f"{x:.10f}".rstrip("0").rstrip(".")
        decimals = max(decimals, len(s.split(".")[1]) if "." in s else 0)
    desc = np.sort(v)[::-1]
    limits = {}
    for k in ks:
        if k > n:
            continue
        vk = desc[k - 1]                       # value at the cut
        above = int((v > vk).sum())            # rows strictly better
        group = int((v == vk).sum())           # rows tied at the cut
        # The top-k is a ranking only if the tie group at the cut fits
        # entirely inside it: above + group == k.
        limits[str(k)] = {
            "value_at_cut": float(vk),
            "tie_group_at_cut": group,
            "rows_strictly_above_cut": above,
            "cuts_inside_tie": bool(above + group > k),
            "arbitrary_slots": int(max(0, k - above)) if above + group > k else 0,
        }
    top = float(uniq[-1])
    return {
        "n": int(n),
        "distinct_values": int(len(uniq)),
        "decimal_places": int(decimals),
        "tied_pair_fraction": float(tied / pairs) if pairs else float("nan"),
        "largest_tie_group": int(counts.max()),
        "largest_tie_value": float(uniq[counts.argmax()]),
        "rows_at_max": int((v == top).sum()),
        "max_value": top,
        "order_by_desc_limit": limits,
    }


def rank_metrics(scores, labels) -> dict:
    s, y = np.asarray(scores, float), np.asarray(labels, float)
    out: dict = {}
    if len(np.unique(s)) < 2 or len(np.unique(y)) < 2:
        out["spearman"] = float("nan")
        out["kendall_tau"] = float("nan")
    else:
        out["spearman"] = float(stats.spearmanr(s, y).statistic)
        out["kendall_tau"] = float(stats.kendalltau(s, y).statistic)
    out.update(pairwise_inversions(s, y))

    # AUC via the rank identity, valid when labels are binary.
    uniq = np.unique(y)
    if len(uniq) == 2:
        pos, neg = s[y == uniq[1]], s[y == uniq[0]]
        if len(pos) and len(neg):
            ranks = stats.rankdata(np.concatenate([pos, neg]))
            auc = (ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (
                len(pos) * len(neg)
            )
            out["auc"] = float(auc)
    return out


# --- invariants: measurable with zero ground-truth labels --------------

def negation_symmetry(p_positive, p_negated) -> dict:
    """Does P(q) + P(not q) equal 1?

    The jev-1.13 jaggedness page explicitly disclaims this: "no guarantee
    that P(noul) equals 1 - P(not noul) across separate questions". That
    disclaimer makes the violation worth measuring rather than assuming.

    This needs no labels at all, so it is immune to the label-provenance
    problem that makes hand-labeled calibration numbers suspect. A large
    asymmetry means the probability depends on question phrasing as much
    as on evidence, which undermines any threshold a caller sets.
    """
    a, b = np.asarray(p_positive, float), np.asarray(p_negated, float)
    resid = a + b - 1.0
    return {
        "n": int(len(a)),
        "mean_abs_violation": float(np.mean(np.abs(resid))),
        "median_abs_violation": float(np.median(np.abs(resid))),
        "max_abs_violation": float(np.max(np.abs(resid))) if len(a) else float("nan"),
        "p95_abs_violation": float(np.percentile(np.abs(resid), 95)) if len(a) else float("nan"),
        "signed_bias": float(np.mean(resid)),  # >0 = says yes to both framings
        "frac_over_0.10": float(np.mean(np.abs(resid) > 0.10)) if len(a) else float("nan"),
        "frac_over_0.20": float(np.mean(np.abs(resid) > 0.20)) if len(a) else float("nan"),
    }


def order_invariance(runs: list[list[float]]) -> dict:
    """Stability of a distribution under permutation of the option list.

    For Choice, options are a map and order should not matter. For Score,
    levels are evaluated independently and the model never sees level
    numbers, so ordinality is imposed entirely by our array order. If a
    reversed rubric does not mirror the score, the rubric is not actually
    ordinal and every sort key built from it is noise.

    `runs` is a list of aligned probability vectors, one per permutation,
    already mapped back to a common option order.
    """
    arr = np.asarray(runs, float)
    if arr.ndim != 2 or arr.shape[0] < 2:
        return {"error": "need >= 2 permutations"}
    spread = arr.max(axis=0) - arr.min(axis=0)
    argmaxes = arr.argmax(axis=1) if arr.shape[1] > 1 else arr.argmax(axis=0)
    return {
        "n_permutations": int(arr.shape[0]),
        "max_prob_spread": float(spread.max()),
        "mean_prob_spread": float(spread.mean()),
        "argmax_stable": bool(len(np.unique(argmaxes)) == 1),
        "total_variation": float(0.5 * np.abs(arr - arr.mean(axis=0)).sum(axis=1).max()),
    }


# --- gate --------------------------------------------------------------

@dataclass
class Gate:
    """Phase 1 stop/go.

    Thresholds are our own, set before seeing results so they cannot be
    rationalised afterwards. They are deliberately not the vendor's: the
    vendor's 67.8% agreement figure is self-run and unreproduced, and
    agreement with averaged frontier judgments is not calibration.

    The spec asks for the three primitives to be reported separately
    because they may calibrate differently. They must therefore be *gated*
    separately too. Gating only jev_bool would let a Score that inverts a
    third of its pairs through, and `jev_score_val` is the accessor ORDER
    BY actually sorts on: it is the single most product-critical number
    here, so it gets its own condition rather than riding on the Boolean.

    Rationale for each:
      ece <= 0.10        A stated 0.8 that is really 0.7 is tolerable for
                         ranking; wider and the probability is decorative.
      inversion <= 0.15  Above roughly one bad pair in six, a sorted page
                         of results looks visibly wrong to a user. Applied
                         to Boolean and Score independently.
      resolution > 0     Anything at or below zero means the model is not
                         separating the classes at all.
      negation <= 0.15   Beyond this, phrasing moves the answer as much as
                         evidence does.
    """

    max_ece: float = 0.10
    max_inversion_rate: float = 0.15
    min_resolution: float = 0.0
    max_negation_violation: float = 0.15
    failures: list[str] = field(default_factory=list)

    def check(
        self,
        *,
        ece_val=None,
        inversion=None,
        resolution=None,
        negation=None,
        score_inversion=None,
        choice_ece=None,
    ):
        self.failures = []
        if ece_val is not None and ece_val > self.max_ece:
            self.failures.append(f"jev_bool ECE {ece_val:.3f} > {self.max_ece}")
        if inversion is not None and inversion > self.max_inversion_rate:
            self.failures.append(
                f"jev_bool inversion rate {inversion:.3f} > {self.max_inversion_rate}"
            )
        if resolution is not None and resolution <= self.min_resolution:
            self.failures.append(
                f"jev_bool resolution {resolution:.4f} <= {self.min_resolution} "
                "(model is not separating classes)"
            )
        if negation is not None and negation > self.max_negation_violation:
            self.failures.append(
                f"negation asymmetry {negation:.3f} > {self.max_negation_violation}"
            )
        # The sort key for jev_score_val / semantic ORDER BY.
        if score_inversion is not None and score_inversion > self.max_inversion_rate:
            self.failures.append(
                f"jev_score inversion rate {score_inversion:.3f} > "
                f"{self.max_inversion_rate} (this is the ORDER BY sort key)"
            )
        if choice_ece is not None and choice_ece > self.max_ece:
            self.failures.append(
                f"jev_choice confidence ECE {choice_ece:.3f} > {self.max_ece}"
            )
        return not self.failures

    @property
    def passed(self) -> bool:
        return not self.failures
