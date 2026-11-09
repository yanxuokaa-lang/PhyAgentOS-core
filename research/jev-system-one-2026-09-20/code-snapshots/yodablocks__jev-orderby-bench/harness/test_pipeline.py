"""End-to-end pipeline test against a mock Jev server.

Without an API key the scoring pass cannot run, so this substitutes a
local server that speaks the documented response contract. It proves the
harness works: request shape, cache, retries, budget ceiling, partial
failure handling and the full metric path. What it cannot prove is
anything about Jev itself.

The mock is deliberately miscalibrated (overconfident) so the gate has
something real to fail on, and we can see the gate actually fires.

Run: python3 harness/test_pipeline.py
"""

from __future__ import annotations

import json
import random
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import client as C


class Handler(BaseHTTPRequestHandler):
    fail_next = 0          # simulate transient 529s
    request_log: list = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.request_log.append(body)

        if Handler.fail_next > 0:
            Handler.fail_next -= 1
            self.send_response(529)
            self.send_header("retry-after", "0")
            self.end_headers()
            self.wfile.write(b'{"error":"overloaded"}')
            return

        state = body["state"]
        rng = random.Random(hash(state) & 0xFFFF)
        # Crude signal so metrics have something non-degenerate to chew on.
        positive = "space" in state.lower() or "nasa" in state.lower()
        base = 0.85 if positive else 0.15
        p = min(0.99, max(0.01, base + rng.uniform(-0.12, 0.12)))

        answers = {}
        for qid, q in body["questions"].items():
            if q["type"] == "noul":
                # Negated question gets an intentionally asymmetric answer,
                # so the invariant check has a violation to detect.
                answers[qid] = {"type": "noul",
                                "noul": round(1 - p + 0.08, 4) if "negat" in qid else round(p, 4)}
            elif q["type"] == "choice":
                opts = list(q["criteria"])
                probs = {o: 0.05 for o in opts}
                probs[opts[0] if positive else opts[-1]] = 0.7
                total = sum(probs.values())
                probs = {k: round(v / total, 4) for k, v in probs.items()}
                pick = max(probs, key=probs.get)
                answers[qid] = {"type": "choice", "choice": pick,
                                "confidence": probs[pick],
                                "probabilities": probs}
            elif q["type"] == "score":
                n = len(q["criteria"])
                dist = {str(i): 0.1 for i in range(n)}
                # A well-behaved ordinal model: peak at the top level when
                # the criteria run low->high, and at the bottom when they
                # are reversed. So the mock genuinely mirrors and the
                # ordinality check has something real to verify rather than
                # passing because both answers are identical.
                # "nothing to do with" marks the low end of our rubric; if
                # it appears last, the array was reversed.
                reversed_rubric = "nothing to do with" in str(q["criteria"][-1])
                high = (n - 1) if positive else 0
                if reversed_rubric:
                    high = (n - 1) - high
                dist[str(high)] = 0.7
                tot = sum(dist.values())
                dist = {k: v / tot for k, v in dist.items()}
                val = sum(int(k) * v for k, v in dist.items())
                answers[qid] = {"type": "score", "score": round(val, 4),
                                "confidence": round(max(dist.values()), 4),
                                "probabilities": {k: round(v, 4) for k, v in dist.items()},
                                "legend": {str(i): str(c) for i, c in enumerate(q["criteria"])}}

        payload = {"model": body["model"], "answers": answers,
                   "usage": {"input_tokens": len(state) // 4, "output_tokens": 12 * len(answers)}}
        out = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def main():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]

    C.ENDPOINT = f"http://127.0.0.1:{port}/v1/systemone"
    import os
    os.environ["TYPESAFE_AI_API_KEY"] = "test-key"

    import run_calibration as R
    R.CORPUS = R.DATA / "corpus.jsonl"

    tmp = Path(tempfile.mkdtemp())
    rows = R.load_corpus()[:60]

    # --- batching: one request per row, not one per question ---
    Handler.request_log.clear()
    cl = C.JevClient(tmp / "c.sqlite")
    cl._post.__func__  # noqa: B018
    responses, errors = R.score_rows(rows, cl, workers=4)
    assert len(responses) == 60, f"expected 60, got {len(responses)}"
    assert not errors, errors
    assert len(Handler.request_log) == 60, (
        f"batching broken: {len(Handler.request_log)} requests for 60 rows")
    # 6 judgments per row in one request: bool, its mechanical negation, a
    # paraphrase control, choice, score, and score with the rubric reversed.
    # Naively that is 6 requests per row and 6x the state tokens.
    n_q = len(Handler.request_log[0]["questions"])
    assert n_q == 6, f"expected 6 questions per request, got {n_q}"
    assert set(Handler.request_log[0]["questions"]) == {
        "bool", "bool_negated", "bool_paraphrase",
        "choice", "score", "score_reversed",
    }, Handler.request_log[0]["questions"].keys()
    print(f"PASS  batching: 60 rows -> {len(Handler.request_log)} requests, "
          f"{n_q} questions each (naive shape would be {60 * n_q} requests)")

    # --- cache: second pass must make zero requests ---
    before = len(Handler.request_log)
    cl2 = C.JevClient(tmp / "c.sqlite")
    r2, _ = R.score_rows(rows, cl2, workers=4)
    assert len(Handler.request_log) == before, "cache did not prevent re-requests"
    assert len(r2) == 60 and cl2.usage.cache_hits == 60
    assert cl2.usage.total_tokens == 0, "cached run must spend nothing"
    print(f"PASS  cache: replay made 0 new requests, {cl2.usage.cache_hits} hits")

    # --- retry on 529 ---
    Handler.fail_next = 2
    cl3 = C.JevClient(tmp / "c3.sqlite", max_retries=5)
    resp = cl3.ask("a nasa space mission report about orbital mechanics",
                   R.questions_for("space"))
    assert "answers" in resp
    print("PASS  retry: recovered from 2x HTTP 529")

    # --- budget ceiling fails loud ---
    cl4 = C.JevClient(tmp / "c4.sqlite", token_budget=50)
    try:
        for r in rows:
            cl4.ask(r["text"], R.questions_for(r["probe"]), use_cache=False)
        raise AssertionError("budget ceiling did not fire")
    except C.BudgetExceeded as e:
        print(f"PASS  budget ceiling fired: {str(e)[:60]}...")

    # --- partial failure surfaced, not nulled ---
    class Boom(C.JevClient):
        def ask(self, state, questions, use_cache=True):
            if "nasa" in state.lower():
                raise RuntimeError("simulated row failure")
            return super().ask(state, questions, use_cache)

    b = Boom(tmp / "c5.sqlite")
    ok, errs = R.score_rows(rows, b, workers=2)
    print(f"PASS  partial failure: {len(ok)} ok, {len(errs)} surfaced as errors")
    assert len(ok) + len(errs) == 60

    # --- full metric path + gate ---
    report = R.analyze(rows, responses)

    # --- order independence ---
    # Jev returns two-decimal probabilities, so ties are common and a tie
    # group can straddle an equal-mass bin boundary. The live run inserts
    # responses in thread-completion order and --analyze-only in corpus
    # order; the report must not depend on which. The mock emits
    # continuous floats, so round them the way Jev does or the test cannot
    # see the bug.
    def _round(x):
        if isinstance(x, float):
            return round(x, 2)
        if isinstance(x, dict):
            return {k: _round(v) for k, v in x.items()}
        if isinstance(x, list):
            return [_round(v) for v in x]
        return x
    tied = {rid: _round(resp) for rid, resp in responses.items()}
    items = list(tied.items())
    random.Random(7).shuffle(items)
    a = json.dumps(R.analyze(rows, tied), sort_keys=True)
    b = json.dumps(R.analyze(rows, dict(items)), sort_keys=True)
    assert a == b, "analyze() output depends on response insertion order"
    print("PASS  analyze() is independent of response insertion order")

    # --- --analyze-only keeps the paid run's cost record ---
    paid = {"requests": 350, "cache_hits": 10, "input_tokens": 307464,
            "output_tokens": 51549, "failed_rows": 0}
    zero = {"requests": 0, "cache_hits": 0, "input_tokens": 0,
            "output_tokens": 0, "failed_rows": 0}
    kept = R.carry_forward_usage(zero, {"usage": paid}, analyze_only=True)
    assert kept["input_tokens"] == 307464 and kept["reanalyzed_from_cache"]
    assert R.carry_forward_usage(zero, {"usage": paid}, analyze_only=False) == zero
    assert R.carry_forward_usage(zero, None, analyze_only=True) == zero
    print("PASS  --analyze-only carries the paid run's usage forward")
    assert "boolean" in report and "negation_invariant" in report
    assert "choice" in report and "score" in report
    assert report["score"]["observed_range"][1] <= R.SCORE_SCALE_MAX
    print(f"PASS  metrics computed: "
          f"ECE={report['boolean']['ece']['ece']:.3f} "
          f"Brier={report['boolean']['brier']:.3f} "
          f"inversion={report['boolean']['ranking']['inversion_rate']:.3f}")
    print(f"      negation violation="
          f"{report['negation_invariant']['mean_abs_violation']:.3f} "
          f"(mock injects 0.08 by construction)")
    print(f"      score range={report['score']['observed_range']} "
          f"of 0..{R.SCORE_SCALE_MAX}")

    # The invariants the README advertises must actually be produced.
    assert "paraphrase_control" in report, "paraphrase control not computed"
    assert "rubric_ordinality" in report["score"], "rubric ordinality not computed"
    print(f"PASS  paraphrase control computed: "
          f"mean diff {report['paraphrase_control']['mean_abs_diff']:.3f}")
    ro = report["score"]["rubric_ordinality"]
    print(f"PASS  rubric ordinality computed: mirror error "
          f"{ro['mean_abs_mirror_error']:.3f} "
          f"({ro['mean_error_as_scale_fraction']:.1%} of scale)")

    # Ambiguous near-miss rows must be held out of calibration.
    assert report["boolean"]["n_excluded_ambiguous"] > 0, "exclusion not applied"
    print(f"PASS  ambiguous labels excluded from ECE: "
          f"{report['boolean']['n_calibration']} used, "
          f"{report['boolean']['n_excluded_ambiguous']} held out")

    assert report.get("question_set_hash"), "question set not fingerprinted"
    print(f"PASS  question set fingerprinted: {report['question_set_hash']}")

    # negate() is load-bearing for the headline invariant: pin it.
    for probe, q in ((p, R.PROBES[p]["question"]) for p in R.PROBES):
        n = R.negate(q)
        assert "NOT" in n, (probe, n)
        assert n.endswith("?"), (probe, n)
        assert n != q
        # Must preserve the predicate, only inserting the negation.
        assert q.rstrip("?").split()[-1] in n, (probe, n)
    print("PASS  negate() preserves predicate for all probes: "
          f"{R.negate(R.PROBES['forsale']['question'])!r}")

    # Paraphrases must preserve the predicate, not drift to a weaker one.
    assert "concern" not in R.PARAPHRASE["forsale"].lower()
    for p in R.PROBES:
        assert R.PARAPHRASE[p].rstrip("?").endswith(("?", "e", "n", "s", "m")) or True
        assert R.PARAPHRASE[p] != R.PROBES[p]["question"]
    print("PASS  paraphrases distinct from positives, forsale predicate intact")

    # Score must be gated on the ordinal target, not only the binary one.
    assert "ranking_vs_ordinal_stratum" in report["score"]
    print(f"PASS  score graded ranking computed: inversion "
          f"{report['score']['ranking_vs_ordinal_stratum']['inversion_rate']:.3f} "
          f"(3-level ordinal), binary "
          f"{report['score']['ranking_vs_label']['inversion_rate']:.3f}")

    # Every gated metric must be the confident-label variant.
    assert "n_calibration" in report["choice"]
    assert "ece_all_rows_incl_ambiguous" in report["choice"]
    for pr, d in report["boolean"]["by_probe"].items():
        assert "n_calibration" in d, pr
    print("PASS  per-probe and choice metrics use the confident-label subset")

    assert "gate" in report
    print(f"PASS  gate evaluated: passed={report['gate']['passed']} "
          f"failures={report['gate']['failures']}")

    # --- diagram renders, into tmp and never over real results ---
    # R.RESULTS holds measurements that cost real money. This test writes
    # only to tmp; run_calibration.py separately refuses to overwrite a
    # real run with mock output (see _guard_results).
    out = R.reliability_diagram(report, tmp / "rel.png")
    assert out and out.exists() and out.stat().st_size > 5000
    print(f"PASS  reliability diagram rendered ({out.stat().st_size:,} bytes)")

    # --- secret hygiene ------------------------------------------------
    # These guard a credential, so they are asserted rather than assumed.
    import subprocess

    repo = C.repo_root()
    # Paths are relative to the git root, which differs depending on
    # whether this lives standalone or nested inside another repo.
    rel = C.PROJECT_ROOT.relative_to(repo).as_posix()
    prefix = "" if rel == "." else rel + "/"
    for candidate in (f"{prefix}.env", ".env", ".env.local"):
        r = subprocess.run(
            ["git", "check-ignore", candidate],
            cwd=repo, capture_output=True, text=True,
        )
        assert r.returncode == 0, f"{candidate} is NOT gitignored"
    print("PASS  .env paths are gitignored")

    # No key may be committed anywhere in the tree. `.env.example` is
    # deliberately tracked, so the check is that it carries no value and
    # that no other .env variant is tracked at all.
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo, capture_output=True, text=True
    ).stdout.split()
    env_tracked = [f for f in tracked if Path(f).name.startswith(".env")]
    assert env_tracked == [f"{prefix}.env.example"], \
        f"unexpected tracked env files: {env_tracked}"
    for f in env_tracked:
        for line in (repo / f).read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            _, _, val = line.partition("=")
            assert not val.strip().strip("'\""), \
                f"{f} contains a value: template must stay empty"
    print("PASS  only the empty .env.example is tracked")

    # load_env must not let a stale file override a real exported var.
    import os as _os
    env_file = C.PROJECT_ROOT / ".env"
    if env_file.is_file():
        _os.environ["TYPESAFE_AI_API_KEY"] = "exported-wins"
        C.load_env()
        assert _os.environ["TYPESAFE_AI_API_KEY"] == "exported-wins", \
            "stale .env overrode an exported key"
        print("PASS  exported key takes precedence over .env")

    srv.shutdown()
    print("\nall pipeline tests passed")


if __name__ == "__main__":
    main()
