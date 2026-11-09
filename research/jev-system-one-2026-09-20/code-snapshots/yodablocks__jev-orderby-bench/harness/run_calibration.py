"""Phase 1 calibration run.

Scores the corpus with Jev, computes the metrics, writes results.json and
a reliability diagram. Every response is cached, so a second run costs
nothing and the notebook is reproducible without re-spending.

Usage:
    export TYPESAFE_AI_API_KEY=...
    python3 run_calibration.py --pilot          # 10 rows, prints cost estimate
    python3 run_calibration.py                  # full run
    python3 run_calibration.py --analyze-only   # recompute from cache

Design note on batching: each row sends one request carrying every
question for that row (noul, the negated noul, choice and score). Jev
answers independent questions against one state in a single parallel
pass, so this is one request where the naive shape would be four, and the
state tokens are paid for once instead of four times.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from client import (
    BudgetExceeded,
    JevClient,
    choice,
    has_api_key,
    noul,
    repo_root,
    score,
)
from corpus import PROBES
import metrics as M

# Anchored on the git root, not a hardcoded depth: this project moved
# from a subdirectory of a larger repo to its own, and a fixed depth
# put .data/ in the user's home directory after the move.
DATA = repo_root() / ".data" / "jev-calibration"
CORPUS = DATA / "corpus.jsonl"
CACHE = DATA / "responses.sqlite"
RESULTS = Path(__file__).resolve().parents[1] / "results"

# Score rubric. Levels are ordered low -> high and each describes a
# concrete situation that stands on its own, because the model sees only
# the descriptions: never the level numbers, never the neighbours.
#
# The resulting score is a probability-weighted mean over level INDICES,
# so with 4 levels the range is 0..3, NOT 0..1. Scores from different
# rubrics are not comparable, and ORDER BY across mixed rubrics is
# meaningless.
RELEVANCE_RUBRIC = [
    "The message has nothing to do with the topic.",
    "The message mentions the topic only in passing or as an aside.",
    "The message discusses the topic as one of several subjects.",
    "The message is entirely and directly about the topic.",
]
SCORE_SCALE_MAX = len(RELEVANCE_RUBRIC) - 1

# Paraphrases that preserve the predicate of each probe question, written
# per probe rather than generated from a topic string. Each asks the same
# thing as PROBES[probe]["question"] in different words.
PARAPHRASE = {
    "space": "Does this message discuss spaceflight, astronomy, "
             "or the exploration of space?",
    "medical": "Does this message discuss medicine, health, "
               "or the treatment of illness?",
    # Preserves "is an offer", rather than the weaker "concerns selling".
    "forsale": "Is this message an offer to sell an item?",
}

CHOICE_OPTIONS = {
    "space": "Spaceflight, astronomy, or space exploration.",
    "medicine": "Medicine, health, disease, or medical treatment.",
    "for_sale": "An offer to sell or trade a specific item.",
    "cars": "Cars, driving, or automotive maintenance.",
    "computer_graphics": "Computer graphics, image formats, or rendering.",
    "other": "None of the other options fit this message.",
}


def negate(question: str) -> str:
    """Build the logical complement mechanically from the same string.

    Hand-writing a separate negative sentence introduces a confound: if
    the measured asymmetry is large, we cannot tell "Jev violates the
    identity" from "my two strings were not actually complements". So the
    negation is derived from the positive question by construction, and
    the only difference between the framings is the inserted negation.

    Note this is still not a *guaranteed* complement in natural language;
    it is only as good as the transformation. Hence the third framing in
    questions_for, which triangulates.
    """
    q = question.strip().rstrip("?")
    for prefix in ("Is this message ", "Is this product ", "Is this "):
        if q.startswith(prefix):
            return f"{prefix}NOT {q[len(prefix):]}?"
    return f"Is it NOT the case that: {q}?"


def questions_for(probe: str) -> dict:
    """Every judgment for one row, asked in a single request."""
    p = PROBES[probe]
    topic = {
        "space": "spaceflight, astronomy, or space exploration",
        "medical": "medicine, health, or medical treatment",
        "forsale": "offering an item for sale",
    }[probe]

    return {
        # Boolean -> jev_bool
        "bool": noul(p["question"]),
        # The negated twin, same request, derived mechanically from the
        # positive string. The jaggedness page disclaims
        # P(q) == 1 - P(not q), so this measures the violation instead of
        # assuming it away.
        "bool_negated": noul(negate(p["question"])),
        # A third framing, semantically equivalent to the positive but
        # worded differently. This separates two explanations for any
        # asymmetry: if paraphrase disagreement is as large as negation
        # disagreement, the model is sensitive to wording in general and
        # the negation result is not specifically about negation.
        #
        # The paraphrase must preserve the PREDICATE, not just the topic.
        # "Does this concern offering an item for sale?" is a different
        # question from "Is this offering an item for sale?": a post
        # discussing selling practices concerns sales without being an
        # offer. A drifted paraphrase inflates the control, which is the
        # denominator of negation_to_paraphrase_ratio, and would push the
        # headline toward "not negation-specific" for the wrong reason.
        "bool_paraphrase": noul(PARAPHRASE[probe]),
        # Choice -> jev_choice
        "choice": choice(
            "Which single subject best describes what this message is about?",
            CHOICE_OPTIONS,
        ),
        # Score -> jev_score
        "score": score(
            f"How directly is this message about {topic}?",
            RELEVANCE_RUBRIC,
        ),
        # Score with the rubric REVERSED. Levels are scored independently
        # and the model never sees level numbers, so ordinality is imposed
        # entirely by our array order. If a reversed rubric does not mirror
        # the score, the rubric is not ordinal and every sort key built
        # from it is noise. One extra question in a request we are already
        # paying for.
        "score_reversed": score(
            f"How directly is this message about {topic}?",
            list(reversed(RELEVANCE_RUBRIC)),
        ),
    }


def question_set_hash() -> str:
    """Fingerprint of every question this run will ask.

    Cache keys include the questions, so editing a rubric or a probe
    question silently invalidates the whole cache and triggers a full
    re-spend. Stamping this into results.json makes that visible instead
    of surprising, and marks which question set a number belongs to.
    """
    import hashlib

    blob = json.dumps(
        {p: questions_for(p) for p in PROBES}, sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def load_corpus() -> list[dict]:
    if not CORPUS.exists():
        sys.exit(f"No corpus at {CORPUS}. Run: python3 corpus.py {CORPUS}")
    return [json.loads(l) for l in CORPUS.open() if l.strip()]


def score_rows(rows, client, workers=4, use_cache=True):
    """Bounded pool. Partial failures are surfaced, never silently nulled."""
    out, errors = {}, {}

    def one(row):
        return row["row_id"], client.ask(
            row["text"], questions_for(row["probe"]), use_cache=use_cache
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, r): r for r in rows}
        done = 0
        for fut in as_completed(futures):
            row = futures[fut]
            try:
                rid, resp = fut.result()
                out[rid] = resp
            except BudgetExceeded:
                for f in futures:
                    f.cancel()
                raise
            except Exception as exc:
                errors[row["row_id"]] = f"{type(exc).__name__}: {exc}"
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(rows)} "
                      f"({client.usage.total_tokens:,} tokens, "
                      f"{client.usage.cache_hits} cached)", flush=True)

    return out, errors


def analyze(rows, responses) -> dict:
    """Compute every metric, per primitive type and per probe."""
    report: dict = {
        "n_corpus": len(rows),
        "n_scored": len(responses),
        "question_set_hash": question_set_hash(),
        "score_scale": {
            "levels": len(RELEVANCE_RUBRIC),
            "range": [0, SCORE_SCALE_MAX],
            "note": "probability-weighted mean over level indices, not 0-1; "
                    "not comparable across different rubrics",
        },
    }

    by_id = {r["row_id"]: r for r in rows}
    # Canonical order. A live run inserts responses in thread-completion
    # order, --analyze-only in corpus order; the adaptive binning splits
    # tied probabilities by input position, so without this the bin
    # tables differ between the two over identical data.
    paired = sorted(
        ((by_id[rid], responses[rid]) for rid in responses if rid in by_id),
        key=lambda pr: pr[0]["row_id"],
    )
    if not paired:
        return report

    def ans(resp, key):
        return resp.get("answers", {}).get(key, {})

    # ---- Boolean (noul) ----
    p_bool = np.array([ans(r, "bool").get("noul", np.nan) for _, r in paired])
    y = np.array([row["label"] for row, _ in paired], float)
    ok = ~np.isnan(p_bool)

    # Calibration is computed on confidently-labeled rows only. For the
    # ambiguous near-miss groups the "no" is arguable, so a correct 0.6
    # scored against a wrong False reads as miscalibration and could fail
    # the gate on label error rather than model error. Ranking keeps every
    # row: those hard cases are exactly where sort order matters, and
    # ranking only needs the pairs the labels do order.
    conf = ok & np.array([row.get("label_confident", True) for row, _ in paired])

    if ok.sum():
        report["boolean"] = {
            "n": int(ok.sum()),
            "n_calibration": int(conf.sum()),
            "n_excluded_ambiguous": int(ok.sum() - conf.sum()),
            "brier": M.brier(p_bool[conf], y[conf]),
            "decomposition": M.brier_decomposition(p_bool[conf], y[conf]),
            "ece": M.ece(p_bool[conf], y[conf], n_bins=10, adaptive=True),
            "ece_fixed_bins": M.ece(p_bool[conf], y[conf], n_bins=10, adaptive=False)["ece"],
            # Reported for comparison: if these diverge a lot, the exclusion
            # is doing heavy lifting and should be stated prominently.
            "ece_all_rows_incl_ambiguous": M.ece(p_bool[ok], y[ok], n_bins=10)["ece"],
            "ranking": M.rank_metrics(p_bool[ok], y[ok]),
            # Label-free: how many rows share a value, and whether an
            # ORDER BY ... DESC LIMIT k cut lands inside a tie group.
            "sort_key_resolution": M.sort_key_resolution(p_bool[ok]),
            "calibration_note": "Brier/ECE exclude near-miss groups whose "
                                "negative label is arguable; ranking uses all rows.",
        }

        # Per-probe, because one bad probe can hide inside the average.
        # Uses `conf`, matching the headline: a per-probe ECE computed on
        # unfiltered rows would silently disagree with the headline number
        # a reader is comparing it against.
        report["boolean"]["by_probe"] = {}
        for probe in PROBES:
            pm = np.array([row["probe"] == probe for row, _ in paired])
            mc = pm & conf
            if mc.sum() > 10:
                report["boolean"]["by_probe"][probe] = {
                    "n_calibration": int(mc.sum()),
                    "brier": M.brier(p_bool[mc], y[mc]),
                    "ece": M.ece(p_bool[mc], y[mc], n_bins=5)["ece"],
                    # Ranking keeps every row, as at the top level.
                    "ranking": M.rank_metrics(p_bool[pm & ok], y[pm & ok]),
                    "n_ranking": int((pm & ok).sum()),
                }

        # Per-stratum. The near_miss rows are the informative ones: if the
        # model is confident there, it is confidently wrong somewhere.
        report["boolean"]["by_stratum"] = {}
        for stratum in ("positive", "near_miss", "far"):
            ms = np.array([row["stratum"] == stratum for row, _ in paired]) & conf
            if ms.sum() > 5:
                report["boolean"]["by_stratum"][stratum] = {
                    "n": int(ms.sum()),
                    "mean_prob": float(p_bool[ms].mean()),
                    "base_rate": float(y[ms].mean()),
                    "brier": M.brier(p_bool[ms], y[ms]),
                    # Spread check: if a probe's confident subset collapses
                    # to the tails, its ECE is an easy-case number.
                    "prob_p10_p90": [
                        float(np.percentile(p_bool[ms], 10)),
                        float(np.percentile(p_bool[ms], 90)),
                    ],
                }

    # ---- negation invariant (needs no labels) ----
    p_neg = np.array([ans(r, "bool_negated").get("noul", np.nan) for _, r in paired])
    both = ok & ~np.isnan(p_neg)
    if both.sum():
        report["negation_invariant"] = M.negation_symmetry(p_bool[both], p_neg[both])

    # Paraphrase control. A semantically equivalent rewording should give
    # the same answer, so |P(q) - P(paraphrase)| is a floor for how much
    # wording alone moves this model. If it is comparable to the negation
    # violation, the negation result is general wording sensitivity rather
    # than anything specific to negation, and must be reported as such.
    p_par = np.array([ans(r, "bool_paraphrase").get("noul", np.nan) for _, r in paired])
    par = ok & ~np.isnan(p_par)
    if par.sum():
        diff = np.abs(p_bool[par] - p_par[par])
        report["paraphrase_control"] = {
            "n": int(par.sum()),
            "mean_abs_diff": float(diff.mean()),
            "median_abs_diff": float(np.median(diff)),
            "p95_abs_diff": float(np.percentile(diff, 95)),
            "max_abs_diff": float(diff.max()),
            "note": "floor for wording sensitivity; compare against "
                    "negation_invariant.mean_abs_violation before attributing "
                    "asymmetry to negation specifically",
        }
        neg_v = report.get("negation_invariant", {}).get("mean_abs_violation")
        if neg_v is not None and diff.mean() > 0:
            report["paraphrase_control"]["negation_to_paraphrase_ratio"] = float(
                neg_v / diff.mean()
            )
        # Also per probe, so one badly-worded paraphrase cannot move the
        # aggregate ratio and mislabel the headline invariant.
        per_probe = {}
        for probe in PROBES:
            pm = par & np.array([row["probe"] == probe for row, _ in paired])
            if pm.sum() > 5:
                pd_ = float(np.abs(p_bool[pm] - p_par[pm]).mean())
                nv = float(np.abs(p_bool[pm] + p_neg[pm] - 1).mean())
                per_probe[probe] = {
                    "n": int(pm.sum()),
                    "paraphrase_mean_abs_diff": pd_,
                    "negation_mean_abs_violation": nv,
                    "ratio": float(nv / pd_) if pd_ > 0 else None,
                }
        report["paraphrase_control"]["by_probe"] = per_probe

    # ---- Choice ----
    # Choice carries the same label ambiguity: a rec.autos post selling a
    # car is labeled `cars`, but `for_sale` is also a listed option and is
    # arguably right. Since choice ECE is a blocking gate condition, it is
    # computed on confidently-labeled rows and reported both ways.
    correct, confs, conf_flags = [], [], []
    for row, r in paired:
        if not row.get("choice_label"):
            continue
        a = ans(r, "choice")
        if "choice" not in a:
            continue
        correct.append(1.0 if a["choice"] == row["choice_label"] else 0.0)
        confs.append(a.get("confidence", np.nan))
        conf_flags.append(row.get("label_confident", True))
    if correct:
        correct = np.array(correct)
        confs = np.array(confs, float)
        cflag = np.array(conf_flags, bool)
        mall = ~np.isnan(confs)
        mconf = mall & cflag
        if mconf.sum():
            # For Choice, calibration means: does stated confidence predict
            # whether the pick was right?
            report["choice"] = {
                "n_calibration": int(mconf.sum()),
                "n_all_rows": int(mall.sum()),
                "accuracy": float(correct[mconf].mean()),
                "accuracy_all_rows": float(correct[mall].mean()),
                "brier_on_confidence": M.brier(confs[mconf], correct[mconf]),
                "ece_on_confidence": M.ece(confs[mconf], correct[mconf], n_bins=10),
                "ece_all_rows_incl_ambiguous": M.ece(
                    confs[mall], correct[mall], n_bins=10
                )["ece"],
                "decomposition": M.brier_decomposition(confs[mconf], correct[mconf]),
                "calibration_note": "computed on confidently-labeled rows; "
                                    "gate uses ece_on_confidence",
            }

    # ---- Score ----
    sc = np.array([ans(r, "score").get("score", np.nan) for _, r in paired])
    m = ~np.isnan(sc)
    if m.sum():
        # Brier/ECE do not apply to a continuous score. Rank metrics do,
        # and ranking is what ORDER BY depends on.
        mc = m & conf
        # Ordinal target. The binary label can only order positives against
        # negatives; it cannot see whether the score correctly orders
        # WITHIN the positives, which is the graded ordering ORDER BY
        # actually exploits. The 3-level stratum (far < near_miss <
        # positive) is a coarse ordinal proxy for that, so it is reported
        # alongside and is the more honest measure of graded ranking.
        strat_rank = np.array(
            [{"far": 0, "near_miss": 1, "positive": 2}[row["stratum"]]
             for row, _ in paired],
            float,
        )
        report["score"] = {
            "n": int(m.sum()),
            "n_calibration": int(mc.sum()),
            "observed_range": [float(sc[m].min()), float(sc[m].max())],
            "mean": float(sc[m].mean()),
            # Gated figure: confident labels only.
            "ranking_vs_label": M.rank_metrics(sc[mc], y[mc]),
            "ranking_vs_label_all_rows": M.rank_metrics(sc[m], y[m]),
            # Graded ranking over 3 ordinal levels rather than 2.
            "ranking_vs_ordinal_stratum": M.rank_metrics(sc[mc], strat_rank[mc]),
            "sort_key_resolution": M.sort_key_resolution(sc[m]),
            "note": "Brier/ECE omitted: they are classification metrics and "
                    "do not apply to a continuous score. ranking_vs_label is "
                    "binary so it cannot detect mis-ordering within the "
                    "positives; see ranking_vs_ordinal_stratum for graded "
                    "ordering.",
        }
        # A stratum-ordered check: far < near_miss < positive should hold
        # if the rubric is genuinely ordinal.
        means = {}
        for stratum in ("far", "near_miss", "positive"):
            mm = np.array([row["stratum"] == stratum for row, _ in paired]) & m
            if mm.sum() > 5:
                means[stratum] = float(sc[mm].mean())
        report["score"]["stratum_means"] = means
        if len(means) == 3:
            report["score"]["stratum_monotonic"] = (
                means["far"] < means["near_miss"] < means["positive"]
            )

        # Rubric ordinality invariant. With the rubric reversed, a genuinely
        # ordinal scale must mirror: score_rev ~= SCALE_MAX - score. This is
        # the check that the array order we impose corresponds to something
        # the model actually perceives as ordered. Needs no ground truth.
        sc_rev = np.array(
            [ans(r, "score_reversed").get("score", np.nan) for _, r in paired]
        )
        mr = m & ~np.isnan(sc_rev)
        if mr.sum():
            mirrored = SCORE_SCALE_MAX - sc_rev[mr]
            resid = np.abs(sc[mr] - mirrored)
            report["score"]["rubric_ordinality"] = {
                "n": int(mr.sum()),
                "mean_abs_mirror_error": float(resid.mean()),
                "median_abs_mirror_error": float(np.median(resid)),
                "p95_abs_mirror_error": float(np.percentile(resid, 95)),
                # As a fraction of the full scale, so it is readable
                # independently of how many levels the rubric has.
                "mean_error_as_scale_fraction": float(
                    resid.mean() / SCORE_SCALE_MAX
                ),
                "correlation_with_mirror": (
                    float(np.corrcoef(sc[mr], mirrored)[0, 1])
                    if len(np.unique(sc[mr])) > 1
                    and len(np.unique(mirrored)) > 1
                    else float("nan")
                ),
                "note": "reversed rubric should mirror: "
                        "score_reversed ~= scale_max - score. Large error "
                        "means the rubric is not ordinal to the model and "
                        "any sort key built from it is noise.",
            }

    # ---- gate ----
    gate = M.Gate()
    b = report.get("boolean", {})
    gate.check(
        ece_val=b.get("ece", {}).get("ece"),
        inversion=b.get("ranking", {}).get("inversion_rate"),
        resolution=b.get("decomposition", {}).get("resolution"),
        negation=report.get("negation_invariant", {}).get("mean_abs_violation"),
        # Gated separately: jev_score_val is what ORDER BY sorts on, so a
        # Score that inverts pairs must stop Phase 2 on its own merits.
        # Gate on the ordinal-stratum inversion, which can see mis-ordering
        # within the positives; the binary version cannot.
        score_inversion=report.get("score", {})
        .get("ranking_vs_ordinal_stratum", {})
        .get("inversion_rate"),
        choice_ece=report.get("choice", {}).get("ece_on_confidence", {}).get("ece"),
    )
    report["gate"] = {
        "passed": gate.passed,
        "failures": gate.failures,
        "thresholds": {
            "max_ece": gate.max_ece,
            "max_inversion_rate": gate.max_inversion_rate,
            "min_resolution": gate.min_resolution,
            "max_negation_violation": gate.max_negation_violation,
        },
    }
    return report


def reliability_diagram(report, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bins = report.get("boolean", {}).get("ece", {}).get("bins", [])
    if not bins:
        return None

    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(6, 7), height_ratios=[3, 1], sharex=True
    )
    x = [b["mean_pred"] for b in bins]
    obs = [b["observed"] for b in bins]
    lo = [max(0.0, o - b["ci_low"]) for o, b in zip(obs, bins)]
    hi = [max(0.0, b["ci_high"] - o) for o, b in zip(obs, bins)]

    ax.plot([0, 1], [0, 1], "--", color="#999", lw=1, label="perfect calibration")
    ax.errorbar(x, obs, yerr=[lo, hi], fmt="o-", color="#2b6cb0",
                capsize=3, lw=1.5, label="observed (95% Wilson CI)")
    ax.set_ylabel("observed frequency")
    ax.set_title(
        f"jev_bool reliability  |  ECE={report['boolean']['ece']['ece']:.3f}  "
        f"Brier={report['boolean']['brier']:.3f}  n={report['boolean']['n']}"
    )
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax2.bar(x, [b["n"] for b in bins], width=0.06, color="#a0aec0")
    ax2.set_xlabel("predicted probability")
    ax2.set_ylabel("count")
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def carry_forward_usage(new_usage: dict, prior: dict | None, analyze_only: bool) -> dict:
    """Keep the cost record of the run that produced the cached responses.

    A re-analysis spends nothing, so its own usage block is all zeros. If
    that overwrote results.json, the only record of what the numbers cost
    (the README quotes it) would be gone after the first --analyze-only.
    The prior block is carried forward and marked, so the file still says
    what the paid run cost and that this copy was recomputed from cache.
    """
    if not analyze_only:
        return new_usage
    prior_usage = (prior or {}).get("usage") or {}
    if not prior_usage.get("requests"):
        return new_usage
    return dict(prior_usage, reanalyzed_from_cache=True)


def _read_results() -> dict | None:
    path = RESULTS / "results.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _guard_results(new: dict) -> None:
    """Refuse to replace a larger completed run with a smaller one.

    results.json costs real money to produce. A `--pilot` run, or a test
    pointed at this directory, would otherwise silently overwrite a full
    run with 10 rows of noise. Overwriting with an equal or larger sample
    is fine: that is a legitimate re-run.
    """
    path = RESULTS / "results.json"
    if not path.exists():
        return
    try:
        old = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return
    old_n, new_n = old.get("n_scored", 0), new.get("n_scored", 0)
    if new_n < old_n:
        backup = RESULTS / f"results.superseded-{old_n}rows.json"
        if not backup.exists():
            backup.write_text(json.dumps(old, indent=2))
        sys.exit(
            f"Refusing to overwrite results.json: it holds {old_n} scored "
            f"rows and this run has only {new_n}.\n"
            f"The existing run was copied to {backup.name}.\n"
            "Delete or move results.json yourself if you really mean to "
            "replace it."
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true",
                    help="score 10 rows and estimate full-run cost")
    ap.add_argument("--analyze-only", action="store_true",
                    help="recompute metrics from cache, make no API calls")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--token-budget", type=int, default=2_000_000)
    args = ap.parse_args()

    rows = load_corpus()
    if args.pilot:
        rows = rows[:10]
    elif args.limit:
        rows = rows[: args.limit]

    client = JevClient(CACHE, token_budget=args.token_budget)

    if args.analyze_only:
        responses = {}
        for r in rows:
            from client import Cache
            hit = client.cache.get(
                Cache.key(client.model, r["text"], questions_for(r["probe"]))
            )
            if hit:
                responses[r["row_id"]] = hit
        print(f"Loaded {len(responses)} cached responses.")
        errors = {}
    else:
        if not has_api_key():
            sys.exit(
                "No API key set.\n\n"
                "  export TYPESAFE_AI_API_KEY=...\n\n"
                "Phase 1 cannot produce calibration numbers without it. The "
                "harness and corpus are ready; only the scoring pass is blocked."
            )
        print(f"Scoring {len(rows)} rows ({args.workers} workers)...")
        responses, errors = score_rows(rows, client, args.workers)

    if errors:
        print(f"\n{len(errors)} rows failed (surfaced, not nulled):")
        for rid, e in list(errors.items())[:5]:
            print(f"  {rid}: {e}")

    u = client.usage
    print(f"\nUsage: {u.requests} requests, {u.cache_hits} cache hits, "
          f"{u.input_tokens:,} in + {u.output_tokens:,} out "
          f"= {u.total_tokens:,} tokens")

    if args.pilot and u.requests:
        per_row = u.total_tokens / u.requests
        full = load_corpus()
        print(f"\nPilot estimate: {per_row:,.0f} tokens/row "
              f"-> ~{per_row * len(full):,.0f} tokens for {len(full)} rows.")

    if not responses:
        print("\nNothing scored; no metrics to compute.")
        return

    report = analyze(rows, responses)
    report["usage"] = carry_forward_usage(
        {
            "requests": u.requests,
            "cache_hits": u.cache_hits,
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "failed_rows": len(errors),
        },
        _read_results(),
        args.analyze_only,
    )

    _guard_results(report)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "results.json").write_text(json.dumps(report, indent=2))
    diagram = reliability_diagram(report, RESULTS / "reliability.png")

    print(f"\nWrote {RESULTS / 'results.json'}")
    if diagram:
        print(f"Wrote {diagram}")

    g = report.get("gate", {})
    print(f"\nGATE: {'PASS' if g.get('passed') else 'FAIL'}")
    for f in g.get("failures", []):
        print(f"  - {f}")
    if not g.get("passed"):
        print("\nPer the build spec: stop and rethink before Phase 2.")


if __name__ == "__main__":
    main()
