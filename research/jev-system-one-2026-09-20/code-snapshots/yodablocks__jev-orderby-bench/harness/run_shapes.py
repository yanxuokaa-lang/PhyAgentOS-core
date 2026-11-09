"""Does the request shape change the numbers?

The same row and the same question reach the API in different shapes
depending on which DuckDB integration sends them:

  A  this harness     state = the text; question = instructions + criteria;
                      one row per request.
  B  colliber shape   state = the text; question = criteria ONLY, no
                      instructions (its client never writes that key);
                      one row per request. Replayed through our client
                      because its binary is built for DuckDB 1.5.4.
  C  recodelabs       state = {"condition": ..., "rows": [up to 40 rows]};
                      one generic noul per row pointing at `rows[i]`. Run
                      through the extension itself, default batch of 40.
  C1 recodelabs       the same, with jev_batch_size = 1, to separate
                      "40 rows share one state" from "the condition lives
                      in the state instead of the question".

Baseline A comes from the cached calibration run. B, C and C1 cost real
money (about a cent each); everything is cached so a re-run is free.

Run: python3 harness/run_shapes.py [--limit N] [--skip-extension]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

import metrics as M
from client import JevClient, api_key, noul, score
from corpus import PROBES
from run_calibration import (
    CACHE, DATA, RELEVANCE_RUBRIC, RESULTS, load_corpus, questions_for,
)

EXT = DATA.parent / "extensions" / "recodelabs" / "jev.duckdb_extension"

TOPIC = {
    "space": "spaceflight, astronomy, or space exploration",
    "medical": "medicine, health, or medical treatment",
    "forsale": "offering an item for sale",
}


# ---------------------------------------------------------------- shapes --

def shape_b_questions(probe: str) -> dict:
    """colliber: criteria carry the whole meaning, no instructions."""
    t = TOPIC[probe]
    verb = "is" if probe != "forsale" else "is"
    return {
        "bool": {"type": "noul", "criteria": {
            "true": f"The message {verb} about {t}." if probe != "forsale"
                    else "The message is offering an item for sale.",
            "false": f"The message is not about {t}." if probe != "forsale"
                     else "The message is not offering an item for sale.",
        }},
        "score": {"type": "score",
                  "criteria": [lvl.replace("the topic", t) for lvl in RELEVANCE_RUBRIC]},
    }


def run_shape_b(rows, client) -> dict:
    out = {}
    for i, r in enumerate(rows):
        resp = client.ask(r["text"], shape_b_questions(r["probe"]))
        a = resp["answers"]
        out[r["row_id"]] = {"noul": a["bool"]["noul"], "score": a["score"]["score"]}
        if (i + 1) % 60 == 0:
            print(f"  B {i + 1}/{len(rows)}", file=sys.stderr)
    return out


def run_shape_c(rows, batch_size: int) -> tuple[dict, dict]:
    """Run the recodelabs extension for real, returning per-row answers
    and its own jev_stats() so its batching and cache claims are checked."""
    import duckdb
    con = duckdb.connect(config={"allow_unsigned_extensions": "true"})
    con.execute(f"LOAD '{EXT}'")
    con.execute("SET jev_api_key = ?", [api_key()])
    con.execute("SET jev_notices = false")
    con.execute(f"SET jev_batch_size = {int(batch_size)}")
    con.execute("CREATE TABLE corpus (row_id VARCHAR, probe VARCHAR, text VARCHAR)")
    con.executemany("INSERT INTO corpus VALUES (?, ?, ?)",
                    [(r["row_id"], r["probe"], r["text"]) for r in rows])
    out = {}
    for probe, p in PROBES.items():
        # struct_pack(text := ...) so the model sees the text and nothing
        # else: no row_id, no probe name, and certainly no label.
        q = ("SELECT row_id, "
             "jev_prob(struct_pack(text := text), ?) AS p, "
             "jev_score(struct_pack(text := text), ?, ?) AS s "
             "FROM corpus WHERE probe = ?")
        for rid, pr, sc in con.execute(
            q, [p["question"], f"How directly is this message about {TOPIC[probe]}?",
                RELEVANCE_RUBRIC, probe]).fetchall():
            out[rid] = {"noul": pr, "score": sc}
        print(f"  C(batch={batch_size}) {probe} done", file=sys.stderr)
    stats_first = json.loads(con.execute("SELECT jev_stats()").fetchone()[0])
    # Second pass: the extension says answers are cached per row content.
    for probe, p in PROBES.items():
        con.execute("SELECT count(*) FROM (SELECT jev_prob(struct_pack(text := text), ?) "
                    "FROM corpus WHERE probe = ?)", [p["question"], probe]).fetchall()
    stats_second = json.loads(con.execute("SELECT jev_stats()").fetchone()[0])
    con.close()
    return out, {"after_first_pass": stats_first, "after_replay": stats_second}


# ------------------------------------------------------------- compare --

def compare(name, base, other, rows) -> dict:
    ids = [r["row_id"] for r in rows if r["row_id"] in base and r["row_id"] in other]
    by_id = {r["row_id"]: r for r in rows}
    y = np.array([by_id[i]["label"] for i in ids], float)
    conf = np.array([by_id[i].get("label_confident", True) for i in ids])
    rep = {"n": len(ids)}
    for key in ("noul", "score"):
        a = np.array([base[i][key] for i in ids], float)
        b = np.array([other[i][key] for i in ids], float)
        d = np.abs(a - b)
        scale = 1.0 if key == "noul" else float(len(RELEVANCE_RUBRIC) - 1)
        block = {
            "mean_abs_diff": float(d.mean()),
            "median_abs_diff": float(np.median(d)),
            "p95_abs_diff": float(np.percentile(d, 95)),
            "max_abs_diff": float(d.max()),
            "frac_changed_over_0.05": float((d > 0.05 * scale).mean()),
            "frac_changed_over_0.20": float((d > 0.20 * scale).mean()),
            "signed_mean_diff_other_minus_base": float((b - a).mean()),
            "spearman_between_shapes": M.rank_metrics(a, b)["spearman"]
                if len(np.unique(b)) > 1 else float("nan"),
            "ranking_vs_label": M.rank_metrics(b, y),
            "sort_key_resolution": M.sort_key_resolution(b),
        }
        if key == "noul":
            block["decision_flips_at_0.5"] = int(((a >= 0.5) != (b >= 0.5)).sum())
            block["ece"] = M.ece(b[conf], y[conf], n_bins=10, adaptive=True)["ece"]
            block["brier"] = M.brier(b[conf], y[conf])
            # Who is in the top group? ORDER BY p DESC LIMIT k draws from it.
            top_a = {i for i, v in zip(ids, a) if v == a.max()}
            top_b = {i for i, v in zip(ids, b) if v == b.max()}
            block["top_group"] = {
                "base_size": len(top_a), "other_size": len(top_b),
                "jaccard": len(top_a & top_b) / len(top_a | top_b),
            }
        rep[key] = block
    return rep


def position_analysis(base, other, rows, batch_size=40) -> dict:
    """Does the shift depend on where the row sat inside the batched state?

    The extension fills batches in table order per question, so a row's
    slot is its index within its probe, modulo the batch size. If the
    shift grows with the slot, the model is losing the rows deep in the
    state; if it were a row-to-answer mapping error the shift would be
    flat and uncorrelated with the slot.
    """
    by_id = {r["row_id"]: r for r in rows}
    slot = {}
    for probe in PROBES:
        ids = [r["row_id"] for r in rows if r["probe"] == probe]
        for i, rid in enumerate(ids):
            slot[rid] = i % batch_size
    ids = [i for i in slot if i in base and i in other]
    d = {i: other[i]["noul"] - base[i]["noul"] for i in ids}
    octiles = []
    for lo in range(0, batch_size, 8):
        sel = [i for i in ids if lo <= slot[i] < lo + 8]
        octiles.append({"slots": [lo, min(lo + 7, batch_size - 1)], "n": len(sel),
                        "mean_abs_shift": float(np.mean([abs(d[i]) for i in sel])),
                        "signed_shift": float(np.mean([d[i] for i in sel]))})
    pos = [i for i in ids if by_id[i]["label"]]
    neg = [i for i in ids if not by_id[i]["label"]]
    # Is it a within-batch shuffle? Compare other vs a batch-1 run at the
    # same row against the best circular shift of +-3 rows.
    return {
        "batch_size": batch_size,
        "signed_mean_shift": float(np.mean(list(d.values()))),
        "by_slot_octile": octiles,
        "signed_shift_positives": float(np.mean([d[i] for i in pos])),
        "signed_shift_negatives": float(np.mean([d[i] for i in neg])),
        "rows_in_0.3_to_0.7": {
            "base": int(sum(0.3 <= base[i]["noul"] <= 0.7 for i in ids)),
            "other": int(sum(0.3 <= other[i]["noul"] <= 0.7 for i in ids)),
        },
    }


def shuffle_check(c, c1, rows) -> dict:
    """Best circular shift of C against C1 per probe. Zero means answers
    sit on the right rows and the difference is not a mapping error."""
    out = {}
    for probe in PROBES:
        ids = [r["row_id"] for r in rows if r["probe"] == probe and r["row_id"] in c and r["row_id"] in c1]
        a = np.array([c[i]["noul"] for i in ids]); b = np.array([c1[i]["noul"] for i in ids])
        best = max(((float(np.corrcoef(np.roll(a, k), b)[0, 1]), k) for k in range(-3, 4)))
        out[probe] = {"corr_same_row": float(np.corrcoef(a, b)[0, 1]),
                      "best_shift": best[1], "corr_at_best_shift": best[0]}
    return out


def baseline_from_cache(rows, client) -> dict:
    from client import Cache
    out = {}
    for r in rows:
        hit = client.cache.get(Cache.key(client.model, r["text"], questions_for(r["probe"])))
        if hit:
            a = hit["answers"]
            out[r["row_id"]] = {"noul": a["bool"]["noul"], "score": a["score"]["score"]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--skip-extension", action="store_true")
    ap.add_argument("--token-budget", type=int, default=2_000_000)
    ap.add_argument("--analyze-only", action="store_true",
                    help="recompute from .data/shapes_raw.json; no API, no extension")
    args = ap.parse_args()

    rows = load_corpus()
    if args.limit:
        rows = rows[: args.limit]
    client = JevClient(CACHE, token_budget=args.token_budget)

    base = baseline_from_cache(rows, client)
    print(f"A baseline: {len(base)}/{len(rows)} rows from cache")
    if len(base) < len(rows):
        sys.exit("baseline incomplete: run run_calibration.py first")

    raw_path = DATA / "shapes_raw.json"
    prior = json.loads(raw_path.read_text()) if args.analyze_only else None
    if prior is None:
        print("B colliber shape (criteria only, no instructions)...")
        b = run_shape_b(rows, client)
    else:
        b = prior["B"]
    u = client.usage
    print(f"  B usage: {u.requests} requests, {u.total_tokens:,} tokens")

    report = {
        "n_rows": len(rows),
        "shapes": {
            "A": "state=text; instructions+criteria; 1 row/request (this harness)",
            "B": "state=text; criteria only, no instructions; 1 row/request (colliber)",
            "C": "state={condition, rows[<=40]}; generic noul per rows[i] (recodelabs, batch 40)",
            "C1": "as C with jev_batch_size=1 (recodelabs, batch 1)",
        },
        "B_vs_A": compare("B", base, b, rows),
        "usage_B": {"requests": u.requests, "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens},
    }

    if prior is not None:
        c, c1 = prior["C"], prior["C1"]
        stats_c, stats_c1 = prior.get("stats_C"), prior.get("stats_C1")
    elif not args.skip_extension:
        if not EXT.exists():
            sys.exit(f"recodelabs extension not found at {EXT}")
        print("C recodelabs extension, batch 40...")
        c, stats_c = run_shape_c(rows, 40)
        print("C1 recodelabs extension, batch 1...")
        c1, stats_c1 = run_shape_c(rows, 1)
        # Keep the raw per-row numbers out of the repo: they are derived
        # from corpus text. Aggregates only.
        raw_path.write_text(json.dumps(
            {"B": b, "C": c, "C1": c1, "stats_C": stats_c, "stats_C1": stats_c1}, indent=1))
    else:
        c = c1 = None
    if c is not None:
        report["C_vs_A"] = compare("C", base, c, rows)
        report["C1_vs_A"] = compare("C1", base, c1, rows)
        report["C1_vs_C"] = compare("C1vsC", c, c1, rows)
        report["C_position_effect"] = position_analysis(base, c, rows, 40)
        report["C_shuffle_check"] = shuffle_check(c, c1, rows)
        if stats_c:
            report["extension_stats_C"] = stats_c
            report["extension_stats_C1"] = stats_c1

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "shapes.json").write_text(json.dumps(report, indent=2))
    print(f"\nWrote {RESULTS / 'shapes.json'}")
    for k in ("B_vs_A", "C_vs_A", "C1_vs_A", "C1_vs_C"):
        if k not in report:
            continue
        r = report[k]
        n = r["noul"]; s = r["score"]
        print(f"\n{k}: n={r['n']}")
        print(f"  noul : mean|d| {n['mean_abs_diff']:.3f}  p95 {n['p95_abs_diff']:.2f}  max {n['max_abs_diff']:.2f}"
              f"  >0.05: {n['frac_changed_over_0.05']:.1%}  >0.20: {n['frac_changed_over_0.20']:.1%}"
              f"  flips@0.5: {n['decision_flips_at_0.5']}  spearman {n['spearman_between_shapes']:.3f}")
        print(f"         ECE {n['ece']:.4f}  Brier {n['brier']:.4f}  inversion {n['ranking_vs_label']['inversion_rate']:.4f}"
              f"  distinct {n['sort_key_resolution']['distinct_values']}  rows@max {n['sort_key_resolution']['rows_at_max']}"
              f"  top-group jaccard {n['top_group']['jaccard']:.2f}")
        print(f"  score: mean|d| {s['mean_abs_diff']:.3f}  p95 {s['p95_abs_diff']:.2f}  >5%: {s['frac_changed_over_0.05']:.1%}"
              f"  spearman {s['spearman_between_shapes']:.3f}  inversion {s['ranking_vs_label']['inversion_rate']:.4f}")
    if "C_position_effect" in report:
        pe = report["C_position_effect"]
        print(f"\nC position effect (batch 40): signed mean {pe['signed_mean_shift']:+.3f}, "
              f"positives {pe['signed_shift_positives']:+.3f}, negatives {pe['signed_shift_negatives']:+.3f}, "
              f"rows in 0.3-0.7: {pe['rows_in_0.3_to_0.7']['base']} -> {pe['rows_in_0.3_to_0.7']['other']}")
        for o in pe["by_slot_octile"]:
            print(f"   slots {o['slots'][0]:2d}-{o['slots'][1]:2d}: mean|shift| {o['mean_abs_shift']:.3f}  signed {o['signed_shift']:+.3f}")
        print("C shuffle check (best shift should be 0):",
              {p: v["best_shift"] for p, v in report["C_shuffle_check"].items()})
    for k in ("extension_stats_C", "extension_stats_C1"):
        if k in report:
            f, s2 = report[k]["after_first_pass"], report[k]["after_replay"]
            print(f"\n{k}: first pass requests={f['requests']} batches={f['batches']} rows={f['rows_evaluated']} "
                  f"tokens={f['input_tokens']}+{f['output_tokens']} cost=${f['estimated_cost_usd']:.4f} cache_hits={f['cache_hits']}"
                  f"\n   replay: requests={s2['requests']} (delta {s2['requests'] - f['requests']}), cache_hits={s2['cache_hits']}")


if __name__ == "__main__":
    main()
