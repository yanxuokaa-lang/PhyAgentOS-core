"""Known-answer tests for the metrics.

These matter more than usual. The whole deliverable is a set of numbers,
so a silent bug in the metric layer produces confident wrong findings
rather than a crash. Every case below has a value computed by hand or by
an independent identity.

Run: python3 harness/test_metrics.py
"""

import sys

import numpy as np

from metrics import (
    Gate,
    _wilson,
    brier,
    brier_decomposition,
    ece,
    negation_symmetry,
    order_invariance,
    pairwise_inversions,
    rank_metrics,
    sort_key_resolution,
)

failures = []


def check(name, got, want, tol=1e-9):
    ok = abs(got - want) <= tol if want == want else got != got
    print(f"{'PASS' if ok else 'FAIL'}  {name}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(name)


# --- Wilson interval ---------------------------------------------------
# Must contain the observed rate at both edges for every bin size the
# harness can produce. At phat = 1, n = 60 the float arithmetic used to
# return an upper bound of 0.9999999999999999, and the reliability
# diagram then handed matplotlib a negative error bar.
_bad = [n for n in range(1, 400)
        if _wilson(0, n)[0] > 0.0 or _wilson(n, n)[1] < 1.0]
assert not _bad, f"Wilson interval excludes phat for n in {_bad[:5]}"
print("PASS  wilson interval contains phat at 0/n and n/n for n < 400")

# --- sort-key resolution -------------------------------------------------
# Five rows tied at the top, two below. 21 pairs, C(5,2)=10 of them tied.
# LIMIT 5 takes exactly the tie group: a ranking. LIMIT 3 cuts inside it:
# 3 arbitrary slots drawn from 5 rows. LIMIT 6 takes the group plus the
# next row: determined again.
_r = sort_key_resolution([0.99] * 5 + [0.5, 0.1], ks=(3, 5, 6))
check("resolution distinct", _r["distinct_values"], 3)
check("resolution tied pair fraction", _r["tied_pair_fraction"], 10 / 21)
check("resolution rows at max", _r["rows_at_max"], 5)
check("resolution decimals", _r["decimal_places"], 2)
assert _r["order_by_desc_limit"]["3"]["cuts_inside_tie"] is True
check("resolution LIMIT 3 arbitrary slots", _r["order_by_desc_limit"]["3"]["arbitrary_slots"], 3)
assert _r["order_by_desc_limit"]["5"]["cuts_inside_tie"] is False
assert _r["order_by_desc_limit"]["6"]["cuts_inside_tie"] is False
print("PASS  resolution: LIMIT inside a tie group is flagged, at its edge is not")
# All distinct: no ties anywhere, every LIMIT is a ranking.
_r = sort_key_resolution([0.9, 0.8, 0.7, 0.6], ks=(2,))
check("resolution no ties", _r["tied_pair_fraction"], 0.0)
assert _r["order_by_desc_limit"]["2"]["cuts_inside_tie"] is False
# All identical: every pair tied, any LIMIT below n is arbitrary.
_r = sort_key_resolution([0.5] * 4, ks=(2,))
check("resolution all tied", _r["tied_pair_fraction"], 1.0)
check("resolution all tied arbitrary slots", _r["order_by_desc_limit"]["2"]["arbitrary_slots"], 2)

# --- Brier -------------------------------------------------------------
# Perfect predictions -> 0. Maximally wrong -> 1.
check("brier perfect", brier([1.0, 0.0, 1.0], [1, 0, 1]), 0.0)
check("brier worst", brier([0.0, 1.0], [1, 0]), 1.0)
# Hand: ((0.5-1)^2 + (0.5-0)^2)/2 = (0.25+0.25)/2 = 0.25
check("brier all-half", brier([0.5, 0.5], [1, 0]), 0.25)

# Murphy identity: brier == reliability - resolution + uncertainty.
rng = np.random.default_rng(0)
p = rng.uniform(0, 1, 500)
y = (rng.uniform(0, 1, 500) < p).astype(int)
d = brier_decomposition(p, y, n_bins=10)
check(
    "murphy identity",
    d["reliability"] - d["resolution"] + d["uncertainty"],
    d["brier"],
    tol=0.02,  # binning makes this approximate, not exact
)

# --- ECE ---------------------------------------------------------------
# A perfectly calibrated construction: within each group, predicted
# probability equals the observed frequency exactly.
probs, labels = [], []
for prob, n in [(0.2, 100), (0.5, 100), (0.8, 100)]:
    k = int(round(prob * n))
    probs += [prob] * n
    labels += [1] * k + [0] * (n - k)
r = ece(probs, labels, n_bins=3, adaptive=True)
check("ece perfectly calibrated", r["ece"], 0.0, tol=1e-9)

# Maximally overconfident: says 1.0, is always wrong.
r = ece([1.0] * 50, [0] * 50, n_bins=5)
check("ece fully overconfident", r["ece"], 1.0, tol=1e-9)
check("mce fully overconfident", r["mce"], 1.0, tol=1e-9)

# Wilson interval must bracket the observed rate.
r = ece([0.5] * 40, [1] * 20 + [0] * 20, n_bins=1)
b = r["bins"][0]
assert b["ci_low"] <= b["observed"] <= b["ci_high"], "wilson must bracket"
print("PASS  wilson brackets observed")

# --- ranking -----------------------------------------------------------
# Perfect ordering: no inversions.
check(
    "inversions perfect",
    pairwise_inversions([0.1, 0.2, 0.9], [0, 0, 1])["inversion_rate"],
    0.0,
)
# Exactly reversed: every comparable pair discordant.
check(
    "inversions reversed",
    pairwise_inversions([0.9, 0.8, 0.1], [0, 0, 1])["inversion_rate"],
    1.0,
)
# All tied: no information, half credit by construction.
check(
    "inversions all tied",
    pairwise_inversions([0.5, 0.5], [0, 1])["inversion_rate"],
    0.5,
)
# Hand: labels [0,0,1,1] give 4 comparable pairs. scores [0.1,0.9,0.2,0.8]
# discordant pairs: (0.9 vs 0.2) and (0.9 vs 0.8) -> 2/4 = 0.5
check(
    "inversions hand-counted",
    pairwise_inversions([0.1, 0.9, 0.2, 0.8], [0, 0, 1, 1])["inversion_rate"],
    0.5,
)

# AUC identity: perfect separation -> 1.0, reversed -> 0.0.
check("auc perfect", rank_metrics([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1])["auc"], 1.0)
check("auc reversed", rank_metrics([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1])["auc"], 0.0)
check("auc chance", rank_metrics([0.5, 0.5, 0.5, 0.5], [0, 0, 1, 1])["auc"], 0.5)

# The case that justifies reporting both families: squashed but perfectly
# ordered probabilities. Terrible ECE, flawless sort.
sq_p = [0.48, 0.49, 0.51, 0.52]
sq_y = [0, 0, 1, 1]
sq_ece = ece(sq_p, sq_y, n_bins=2)["ece"]
sq_inv = pairwise_inversions(sq_p, sq_y)["inversion_rate"]
print(f"      squashed-but-ordered: ECE={sq_ece:.3f} inversion={sq_inv:.3f}")
assert sq_ece > 0.4 and sq_inv == 0.0, "this case must show the divergence"
print("PASS  ece/ranking divergence demonstrated")

# --- invariants --------------------------------------------------------
check(
    "negation perfect",
    negation_symmetry([0.8, 0.3], [0.2, 0.7])["mean_abs_violation"],
    0.0,
    tol=1e-12,
)
# Says yes to both framings: 0.8 + 0.8 - 1 = 0.6 violation, positive bias.
n = negation_symmetry([0.8], [0.8])
check("negation both-yes violation", n["mean_abs_violation"], 0.6, tol=1e-12)
check("negation both-yes bias", n["signed_bias"], 0.6, tol=1e-12)

inv = order_invariance([[0.7, 0.3], [0.7, 0.3]])
check("order invariance identical spread", inv["max_prob_spread"], 0.0)
assert inv["argmax_stable"], "identical runs must be stable"
inv = order_invariance([[0.7, 0.3], [0.3, 0.7]])
check("order invariance flipped spread", inv["max_prob_spread"], 0.4, tol=1e-12)
assert not inv["argmax_stable"], "flipped argmax must be reported unstable"
print("PASS  order invariance argmax flags")

# --- gate --------------------------------------------------------------
g = Gate()
assert g.check(ece_val=0.05, inversion=0.10, resolution=0.05, negation=0.05)
print("PASS  gate passes good numbers")
g2 = Gate()
assert not g2.check(ece_val=0.30, inversion=0.10, resolution=0.05, negation=0.05)
assert "ECE" in g2.failures[0]
print(f"PASS  gate fails bad ECE: {g2.failures}")
g3 = Gate()
assert not g3.check(ece_val=0.01, inversion=0.02, resolution=0.0, negation=0.01)
print(f"PASS  gate catches zero resolution: {g3.failures}")

# The regression that matters most: a Boolean that passes everything while
# Score inverts a third of its pairs must still fail, because jev_score_val
# is what ORDER BY sorts on.
g4 = Gate()
assert not g4.check(
    ece_val=0.02, inversion=0.03, resolution=0.2, negation=0.02,
    score_inversion=0.33,
)
assert "jev_score" in g4.failures[0], g4.failures
print(f"PASS  gate catches bad Score ranking despite good Boolean: {g4.failures}")

g5 = Gate()
assert not g5.check(ece_val=0.02, inversion=0.03, resolution=0.2,
                    negation=0.02, choice_ece=0.4)
print(f"PASS  gate catches bad Choice confidence: {g5.failures}")

g6 = Gate()
assert g6.check(ece_val=0.02, inversion=0.03, resolution=0.2, negation=0.02,
                score_inversion=0.05, choice_ece=0.04)
print("PASS  gate passes when all three primitives are good")

print()
if failures:
    print(f"{len(failures)} FAILURES: {failures}")
    sys.exit(1)
print("all metric tests passed")
