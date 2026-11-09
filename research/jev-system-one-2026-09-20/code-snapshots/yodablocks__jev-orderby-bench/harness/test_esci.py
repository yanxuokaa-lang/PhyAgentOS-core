"""Offline test of the ESCI runner: fake graded corpus, mock Jev, every
report section present, gate evaluated, no network, no key.

Run: python3 harness/test_esci.py
"""
import json, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import client as C
import run_esci as R

GRADES = ["I", "C", "S", "E"]


class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        state = body["state"]
        assert isinstance(state, dict) and "query" in state and "product" in state, state
        # The fake product title carries its grade so the mock can be graded-ish.
        grade = GRADES.index(state["product"]["title"][0])
        p = [0.03, 0.12, 0.45, 0.93][grade]
        answers = {}
        for qid, q in body["questions"].items():
            if q["type"] == "noul":
                answers[qid] = {"type": "noul", "noul": round(1 - p if "negat" in qid else p, 2)}
            elif q["type"] == "choice":
                opts = list(q["criteria"])
                pick = ["irrelevant", "complement", "substitute", "exact"][grade]
                probs = {o: (0.7 if o == pick else 0.1) for o in opts}
                answers[qid] = {"type": "choice", "choice": pick, "confidence": 0.7, "probabilities": probs}
            else:
                n = len(q["criteria"])
                rev = "nothing to do" in q["criteria"][-1]
                val = (n - 1 - grade) if rev else grade
                answers[qid] = {"type": "score", "score": float(val), "confidence": 0.8}
        out = json.dumps({"model": "mock", "answers": answers,
                          "usage": {"input_tokens": 200, "output_tokens": 20}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


def main():
    srv = HTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    C.ENDPOINT = f"http://127.0.0.1:{srv.server_port}/v1/systemone"
    import os; os.environ["TYPESAFE_AI_API_KEY"] = "test"
    rows = []
    for q in range(4):
        for g, k in zip(GRADES, (2, 2, 4, 4)):
            for i in range(k):
                rows.append({"row_id": f"q{q}{g}{i}", "probe": "esci", "query_id": q,
                             "text": {"query": f"query {q}", "product": {"title": f"{g} product {i}"}},
                             "label": g == "E", "grade": GRADES.index(g), "esci": g,
                             "choice_label": g, "stratum": g, "label_confident": True})
    tmp = Path(tempfile.mkdtemp())
    cl = C.JevClient(tmp / "c.sqlite")
    resp, errs = R.score_rows(rows, cl, workers=2)
    assert not errs and len(resp) == len(rows), errs
    assert cl.usage.requests == len(rows)
    hit = cl.cache.get(C.Cache.key(cl.model, rows[0]["text"], R.questions()))
    assert hit and len(hit["answers"]) == 6, hit
    print(f"PASS  scored {len(rows)} rows, 1 request each, 6 questions per request")
    rep = R.analyze(rows, resp)
    for k in ("boolean", "negation_invariant", "paraphrase_control", "choice", "score", "gate"):
        assert k in rep, k
    assert rep["score"]["grade_monotonic"] is True
    assert rep["score"]["ranking_vs_grade"]["inversion_rate"] == 0.0
    assert rep["score"]["within_query_vs_grade"]["n_queries"] == 4
    assert rep["boolean"]["ranking_vs_grade"]["inversion_rate"] == 0.0
    assert rep["choice"]["accuracy"] == 1.0
    assert rep["score"]["rubric_ordinality"]["mean_abs_mirror_error"] == 0.0
    # The mock is deliberately miscalibrated (every E row gets 0.93 and is
    # right every time), so the gate must fail on ECE and on nothing else:
    # ranking, ordinality and negation are all perfect by construction.
    fails = rep["gate"]["failures"]
    assert not rep["gate"]["passed"] and fails, rep["gate"]
    assert all("ECE" in f for f in fails), fails
    assert not any("inversion" in f or "negation" in f or "resolution" in f for f in fails), fails
    print(f"PASS  gate evaluated: fails only on the mock's known miscalibration ({len(fails)} ECE conditions)")
    print(f"PASS  graded metrics: score inversion vs grade {rep['score']['ranking_vs_grade']['inversion_rate']}, "
          f"within-query {rep['score']['within_query_vs_grade']['mean_inversion_rate']}, monotonic, mirror 0")
    assert R.negate(R.BOOL_Q).startswith("Is this product NOT "), R.negate(R.BOOL_Q)
    print("PASS  negation derived mechanically:", R.negate(R.BOOL_Q)[:60])
    srv.shutdown()
    print("\nall esci tests passed")


if __name__ == "__main__":
    main()
