"""The hard probe: graded product relevance (Amazon ESCI).

Same harness, same metrics, same gate as the 20 Newsgroups run, on a
corpus where the ranking target is a 4-level human grade rather than a
sampling stratum. What this adds over run_calibration.py:

  * jev_score is ranked against the human grade I < C < S < E directly,
    so "ordinal inversion" here is measured, not proxied.
  * within-query ranking: ORDER BY on product search happens inside one
    query's result list, so inversions are also computed per query and
    averaged. That is the number a shopper would see.
  * jev_bool is E-vs-rest, with S as the human-labeled near miss.

Run:
    python3 harness/corpus_esci.py            # once, needs the two parquet files
    python3 harness/run_esci.py --pilot       # 10 rows + cost estimate
    python3 harness/run_esci.py               # full run
    python3 harness/run_esci.py --analyze-only
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

import metrics as M
from client import BudgetExceeded, JevClient, choice, has_api_key, noul, repo_root, score
from run_calibration import carry_forward_usage, negate, reliability_diagram

DATA = repo_root() / ".data" / "esci"
CORPUS = DATA / "corpus.jsonl"
CACHE = repo_root() / ".data" / "jev-calibration" / "responses.sqlite"
RESULTS = Path(__file__).resolve().parents[1] / "results"
OUT = RESULTS / "esci.json"

GRADE_NAMES = ["I", "C", "S", "E"]           # index == grade, low -> high

# The rubric follows the ESCI label definitions in order I, C, S, E. Each
# level describes a concrete situation and stands on its own.
RUBRIC = [
    "The product has nothing to do with the query.",
    "The product does not fulfil the query itself, but it goes with a "
    "product that does (an accessory, part, or companion item).",
    "The product partly fulfils the query: it is the right kind of item "
    "but not exactly what was asked for, differing in a stated attribute "
    "such as brand, model, size, colour, or quantity.",
    "The product is exactly what the query asks for, including every "
    "attribute the query states.",
]
SCALE_MAX = len(RUBRIC) - 1

CHOICE = {
    "exact": "Exactly what the query asks for, including every stated attribute.",
    "substitute": "The right kind of item but not exactly what was asked: a "
                  "stated attribute such as brand, model, size, colour or "
                  "quantity differs.",
    "complement": "Does not fulfil the query itself but goes with a product "
                  "that does: an accessory, part, or companion item.",
    "irrelevant": "Nothing to do with the query.",
}
CHOICE_TO_ESCI = {"exact": "E", "substitute": "S", "complement": "C", "irrelevant": "I"}

BOOL_Q = ("Is this product exactly what the shopper's query asks for, "
          "including every attribute the query states (brand, model, size, "
          "colour, quantity)?")
PARAPHRASE_Q = ("Would this product satisfy the shopper's query precisely, "
                "with nothing the query specifies left unmet?")


def questions() -> dict:
    """Every judgment for one row, asked in a single request. State is the
    JSON object {query, product}; questions reference it by name."""
    return {
        "bool": noul(BOOL_Q),
        "bool_negated": noul(negate(BOOL_Q)),
        "bool_paraphrase": noul(PARAPHRASE_Q),
        "choice": choice("How does `product` relate to the shopper's `query`?", CHOICE),
        "score": score("How well does `product` satisfy the shopper's `query`?", RUBRIC),
        "score_reversed": score("How well does `product` satisfy the shopper's `query`?",
                                list(reversed(RUBRIC))),
    }


def load_corpus() -> list[dict]:
    if not CORPUS.exists():
        sys.exit(f"No corpus at {CORPUS}. Run: python3 harness/corpus_esci.py")
    return [json.loads(l) for l in CORPUS.open() if l.strip()]


def score_rows(rows, client, workers=4):
    out, errors = {}, {}
    qs = questions()

    def one(row):
        return row["row_id"], client.ask(row["text"], qs)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, r): r for r in rows}
        for i, fut in enumerate(as_completed(futures), 1):
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
            if i % 25 == 0:
                print(f"  {i}/{len(rows)} ({client.usage.total_tokens:,} tokens, "
                      f"{client.usage.cache_hits} cached)", flush=True)
    return out, errors


def within_query(values, grades, qids) -> dict:
    """Pairwise inversion against the grade, computed inside each query
    and averaged over queries. This is the ORDER BY a shopper sees."""
    per = []
    for q in sorted(set(qids)):
        sel = [i for i, x in enumerate(qids) if x == q]
        if len(sel) < 2:
            continue
        r = M.pairwise_inversions([values[i] for i in sel], [grades[i] for i in sel])
        if r["comparable_pairs"]:
            per.append(r["inversion_rate"])
    per = np.array(per)
    return {
        "n_queries": int(len(per)),
        "mean_inversion_rate": float(per.mean()),
        "median_inversion_rate": float(np.median(per)),
        "worst_query_inversion_rate": float(per.max()),
        "queries_over_0.15": int((per > 0.15).sum()),
    }


def analyze(rows, responses) -> dict:
    by_id = {r["row_id"]: r for r in rows}
    paired = sorted(((by_id[rid], responses[rid]) for rid in responses if rid in by_id),
                    key=lambda pr: pr[0]["row_id"])
    report: dict = {
        "corpus": "Amazon ESCI, US, small_version, test split, human-graded E/S/C/I",
        "n_corpus": len(rows), "n_scored": len(paired),
        "n_queries": len({r["query_id"] for r in rows}),
        "grade_order": GRADE_NAMES,
        "label_counts": dict(Counter(r["esci"] for r in rows)),
        "score_scale": {"levels": len(RUBRIC), "range": [0, SCALE_MAX]},
    }
    if not paired:
        return report

    def ans(resp, key):
        return resp.get("answers", {}).get(key, {})

    y = np.array([row["label"] for row, _ in paired], float)          # E vs rest
    g = np.array([row["grade"] for row, _ in paired], float)          # 0..3
    qids = [row["query_id"] for row, _ in paired]
    p = np.array([ans(r, "bool").get("noul", np.nan) for _, r in paired])
    ok = ~np.isnan(p)

    # ---- Boolean: E vs rest ----
    if ok.sum():
        report["boolean"] = {
            "n": int(ok.sum()),
            "brier": M.brier(p[ok], y[ok]),
            "decomposition": M.brier_decomposition(p[ok], y[ok]),
            "ece": M.ece(p[ok], y[ok], n_bins=10, adaptive=True),
            "ece_fixed_bins": M.ece(p[ok], y[ok], n_bins=10, adaptive=False)["ece"],
            "ranking": M.rank_metrics(p[ok], y[ok]),
            # The probability of "exact" ranked against the 4-level grade:
            # a well-behaved P(E) should still order S above C above I.
            "ranking_vs_grade": M.rank_metrics(p[ok], g[ok]),
            "within_query_vs_grade": within_query(p[ok], g[ok], [q for q, o in zip(qids, ok) if o]),
            "ranking_vs_grade_excluding_C": M.rank_metrics(p[ok & (g != 1)], g[ok & (g != 1)]),
            "sort_key_resolution": M.sort_key_resolution(p[ok]),
            "mean_prob_by_grade": {
                GRADE_NAMES[k]: float(p[ok & (g == k)].mean()) for k in range(4) if (ok & (g == k)).any()
            },
        }

    # ---- Invariants ----
    p_neg = np.array([ans(r, "bool_negated").get("noul", np.nan) for _, r in paired])
    both = ok & ~np.isnan(p_neg)
    if both.sum():
        report["negation_invariant"] = M.negation_symmetry(p[both], p_neg[both])
    p_par = np.array([ans(r, "bool_paraphrase").get("noul", np.nan) for _, r in paired])
    par = ok & ~np.isnan(p_par)
    if par.sum():
        d = np.abs(p[par] - p_par[par])
        report["paraphrase_control"] = {
            "n": int(par.sum()), "mean_abs_diff": float(d.mean()),
            "median_abs_diff": float(np.median(d)),
            "p95_abs_diff": float(np.percentile(d, 95)), "max_abs_diff": float(d.max()),
        }
        nv = report.get("negation_invariant", {}).get("mean_abs_violation")
        if nv is not None and d.mean() > 0:
            report["paraphrase_control"]["negation_to_paraphrase_ratio"] = float(nv / d.mean())

    # ---- Choice: 4-way ESCI classification ----
    correct, confs, pred, true = [], [], [], []
    for row, r in paired:
        a = ans(r, "choice")
        if "choice" not in a:
            continue
        pr = CHOICE_TO_ESCI.get(a["choice"], "?")
        pred.append(pr); true.append(row["esci"])
        correct.append(1.0 if pr == row["esci"] else 0.0)
        confs.append(a.get("confidence", np.nan))
    if correct:
        correct = np.array(correct); confs = np.array(confs, float)
        mc = ~np.isnan(confs)
        conf_mat = {t: dict(Counter(pp for tt, pp in zip(true, pred) if tt == t)) for t in GRADE_NAMES}
        report["choice"] = {
            "n": int(len(correct)),
            "accuracy": float(correct.mean()),
            "confusion_true_to_pred": conf_mat,
            "brier_on_confidence": M.brier(confs[mc], correct[mc]),
            "ece_on_confidence": M.ece(confs[mc], correct[mc], n_bins=10),
            "decomposition": M.brier_decomposition(confs[mc], correct[mc]),
        }

    # ---- Score: ranked against the human grade ----
    sc = np.array([ans(r, "score").get("score", np.nan) for _, r in paired])
    m = ~np.isnan(sc)
    if m.sum():
        report["score"] = {
            "n": int(m.sum()),
            "observed_range": [float(sc[m].min()), float(sc[m].max())],
            "mean": float(sc[m].mean()),
            "ranking_vs_label": M.rank_metrics(sc[m], y[m]),
            # The measured (not proxied) graded ranking.
            "ranking_vs_grade": M.rank_metrics(sc[m], g[m]),
            "within_query_vs_grade": within_query(sc[m], g[m], [q for q, o in zip(qids, m) if o]),
            # C ("complement") is placed between I and S by the KDD Cup gain
            # order, but whether it is truly an ordinal step is arguable, so
            # the graded ranking is also reported with C rows removed.
            "ranking_vs_grade_excluding_C": M.rank_metrics(sc[m & (g != 1)], g[m & (g != 1)]),
            "within_query_vs_grade_excluding_C": within_query(
                sc[m & (g != 1)], g[m & (g != 1)],
                [q for q, o, gg in zip(qids, m, g) if o and gg != 1]),
            "sort_key_resolution": M.sort_key_resolution(sc[m]),
            "mean_score_by_grade": {
                GRADE_NAMES[k]: float(sc[m & (g == k)].mean()) for k in range(4) if (m & (g == k)).any()
            },
        }
        means = report["score"]["mean_score_by_grade"]
        if all(k in means for k in GRADE_NAMES):
            report["score"]["grade_monotonic"] = bool(
                means["I"] < means["C"] < means["S"] < means["E"])
        sc_rev = np.array([ans(r, "score_reversed").get("score", np.nan) for _, r in paired])
        mr = m & ~np.isnan(sc_rev)
        if mr.sum():
            mirrored = SCALE_MAX - sc_rev[mr]
            resid = np.abs(sc[mr] - mirrored)
            report["score"]["rubric_ordinality"] = {
                "n": int(mr.sum()),
                "mean_abs_mirror_error": float(resid.mean()),
                "median_abs_mirror_error": float(np.median(resid)),
                "p95_abs_mirror_error": float(np.percentile(resid, 95)),
                "mean_error_as_scale_fraction": float(resid.mean() / SCALE_MAX),
                "correlation_with_mirror": float(np.corrcoef(sc[mr], mirrored)[0, 1])
                    if len(np.unique(sc[mr])) > 1 and len(np.unique(mirrored)) > 1 else float("nan"),
            }

    # ---- gate: same thresholds, fixed before this corpus was chosen ----
    gate = M.Gate()
    b = report.get("boolean", {})
    gate.check(
        ece_val=b.get("ece", {}).get("ece"),
        inversion=b.get("ranking", {}).get("inversion_rate"),
        resolution=b.get("decomposition", {}).get("resolution"),
        negation=report.get("negation_invariant", {}).get("mean_abs_violation"),
        score_inversion=report.get("score", {}).get("ranking_vs_grade", {}).get("inversion_rate"),
        choice_ece=report.get("choice", {}).get("ece_on_confidence", {}).get("ece"),
    )
    report["gate"] = {"passed": gate.passed, "failures": gate.failures,
                      "thresholds": {"max_ece": gate.max_ece,
                                     "max_inversion_rate": gate.max_inversion_rate,
                                     "min_resolution": gate.min_resolution,
                                     "max_negation_violation": gate.max_negation_violation}}
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--token-budget", type=int, default=1_500_000)
    args = ap.parse_args()

    rows = load_corpus()
    if args.pilot:
        rows = rows[:10]
    if args.limit:
        rows = rows[: args.limit]
    client = JevClient(CACHE, token_budget=args.token_budget)

    if args.analyze_only:
        from client import Cache
        responses = {}
        qs = questions()
        for r in rows:
            hit = client.cache.get(Cache.key(client.model, r["text"], qs))
            if hit:
                responses[r["row_id"]] = hit
        print(f"Loaded {len(responses)} cached responses.")
        errors = {}
    else:
        if not has_api_key():
            sys.exit("No API key set (TYPESAFE_AI_API_KEY in .env or exported).")
        print(f"Scoring {len(rows)} rows ({args.workers} workers)...")
        responses, errors = score_rows(rows, client, args.workers)

    if errors:
        print(f"\n{len(errors)} rows failed (surfaced, not nulled):")
        for rid, e in list(errors.items())[:5]:
            print(f"  {rid}: {e}")
    u = client.usage
    print(f"\nUsage: {u.requests} requests, {u.cache_hits} cache hits, "
          f"{u.input_tokens:,} in + {u.output_tokens:,} out = {u.total_tokens:,} tokens")
    if args.pilot and u.requests:
        per_row = u.total_tokens / u.requests
        print(f"Pilot estimate: {per_row:,.0f} tokens/row -> ~{per_row * len(load_corpus()):,.0f} "
              f"tokens for the full corpus (~${per_row * len(load_corpus()) * 0.042 / 1e6:.3f})")
    if not responses:
        print("\nNothing scored.")
        return

    report = analyze(rows, responses)
    prior = json.loads(OUT.read_text()) if OUT.exists() else None
    report["usage"] = carry_forward_usage(
        {"requests": u.requests, "cache_hits": u.cache_hits, "input_tokens": u.input_tokens,
         "output_tokens": u.output_tokens, "failed_rows": len(errors)},
        prior, args.analyze_only)
    if prior and prior.get("n_scored", 0) > report["n_scored"]:
        sys.exit(f"Refusing to overwrite {OUT.name}: it holds {prior['n_scored']} rows, "
                 f"this run has {report['n_scored']}. Move it aside if you mean it.")
    RESULTS.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    reliability_diagram(report, RESULTS / "reliability_esci.png")
    print(f"\nWrote {OUT}")

    b, s, c = report.get("boolean", {}), report.get("score", {}), report.get("choice", {})
    print(f"\njev_bool (E vs rest): Brier {b.get('brier', float('nan')):.4f}  ECE {b.get('ece', {}).get('ece', float('nan')):.4f}"
          f"  AUC {b.get('ranking', {}).get('auc', float('nan')):.4f}  inversion {b.get('ranking', {}).get('inversion_rate', float('nan')):.4f}"
          f"  vs grade {b.get('ranking_vs_grade', {}).get('inversion_rate', float('nan')):.4f}"
          f"  within-query {b.get('within_query_vs_grade', {}).get('mean_inversion_rate', float('nan')):.4f}")
    print(f"  mean P(E) by grade: {b.get('mean_prob_by_grade')}")
    print(f"jev_score vs human grade: inversion {s.get('ranking_vs_grade', {}).get('inversion_rate', float('nan')):.4f}"
          f"  spearman {s.get('ranking_vs_grade', {}).get('spearman', float('nan')):.4f}"
          f"  within-query {s.get('within_query_vs_grade', {}).get('mean_inversion_rate', float('nan')):.4f}"
          f"  monotonic {s.get('grade_monotonic')}  mirror err {s.get('rubric_ordinality', {}).get('mean_abs_mirror_error', float('nan')):.3f}")
    print(f"  mean score by grade: {s.get('mean_score_by_grade')}")
    print(f"jev_choice 4-way: accuracy {c.get('accuracy', float('nan')):.4f}  conf ECE {c.get('ece_on_confidence', {}).get('ece', float('nan')):.4f}")
    print(f"negation {report.get('negation_invariant', {}).get('mean_abs_violation', float('nan')):.4f}"
          f"  paraphrase {report.get('paraphrase_control', {}).get('mean_abs_diff', float('nan')):.4f}")
    print(f"\nGATE: {'PASS' if report['gate']['passed'] else 'FAIL'}")
    for f in report["gate"]["failures"]:
        print("  ", f)


if __name__ == "__main__":
    main()
