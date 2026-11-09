"""Phase 2: DuckDB scalar functions over Jev.

Gated on Phase 1. Registering these before the calibration gate passes
means semantic ORDER BY sorts by a number nobody has checked, which is the
exact silent failure the build spec is structured to prevent. `register`
refuses unless the gate passed or override=True.

Signatures follow the build spec. The struct return is settled: returning
NULL on low confidence poisons ORDER BY unpredictably (NULLs sort last in
DuckDB regardless of direction, so low-confidence rows silently clump at
one end), and returning a bare score hides the uncertainty the caller
needs to filter on. Structs expose both; jev_score_val covers the common
case where the caller has already decided to trust the score.

    jev_bool(text, question)      -> STRUCT(value BOOLEAN, prob DOUBLE)
    jev_choice(text, options[])   -> STRUCT(value VARCHAR, prob DOUBLE, confidence DOUBLE)
    jev_score(text, rubric[])     -> STRUCT(score DOUBLE, confidence DOUBLE)
    jev_score_val(text, rubric[]) -> DOUBLE

Note on jev_bool: Noul returns a probability with no separate confidence
field, so `prob` is the probability of yes and `value` is prob >= 0.5.
That matches the two-field struct in the spec.

Note on jev_score scale: Score is a probability-weighted mean over level
INDICES, so the range is 0..len(rubric)-1, not 0..1. Scores from different
rubrics are not comparable. ORDER BY across mixed rubrics is meaningless.

Requires duckdb, which is NOT needed for Phase 1:  pip install duckdb
"""

from __future__ import annotations

import json
from pathlib import Path

from client import JevClient, choice as q_choice, noul as q_noul, score as q_score


def _gate_passed(results: Path) -> tuple[bool, str]:
    f = results / "results.json"
    if not f.exists():
        return False, f"no Phase 1 results at {f}"
    try:
        g = json.loads(f.read_text()).get("gate", {})
    except json.JSONDecodeError as e:
        return False, f"unreadable results.json: {e}"
    if not g:
        return False, "results.json has no gate section"
    return bool(g.get("passed")), "; ".join(g.get("failures", [])) or "gate passed"


def register(con, client: JevClient, results_dir: Path | None = None,
             override: bool = False):
    """Register the four functions on a DuckDB connection.

    Raises unless Phase 1's gate passed. Pass override=True only to
    experiment knowingly with uncalibrated output.
    """
    # Gate first, before anything else can fail for an unrelated reason: a
    # missing duckdb should not mask an unpassed calibration gate.
    results_dir = results_dir or Path(__file__).resolve().parents[1] / "results"
    passed, detail = _gate_passed(results_dir)
    if not passed and not override:
        raise RuntimeError(
            f"Phase 1 calibration gate has not passed ({detail}).\n"
            "Semantic ORDER BY over uncalibrated probabilities sorts by a "
            "number nobody has verified, and fails silently.\n"
            "Run the calibration first, or pass override=True to proceed "
            "knowingly."
        )

    import duckdb  # noqa: F401  (imported for a clear error if missing)

    def jev_bool(text: str, question: str) -> dict:
        if text is None or question is None:
            return {"value": None, "prob": None}
        r = client.ask(text, {"q": q_noul(question)})
        p = r["answers"]["q"]["noul"]
        return {"value": p >= 0.5, "prob": p}

    def jev_choice(text: str, options: list[str]) -> dict:
        if text is None or not options:
            return {"value": None, "prob": None, "confidence": None}
        r = client.ask(
            text,
            {"q": q_choice("Which option best describes this?",
                           {o: None for o in options})},
        )
        a = r["answers"]["q"]
        return {
            "value": a["choice"],
            "prob": a.get("probabilities", {}).get(a["choice"]),
            "confidence": a.get("confidence"),
        }

    def jev_score(text: str, rubric: list[str]) -> dict:
        if text is None or not rubric:
            return {"score": None, "confidence": None}
        r = client.ask(
            text,
            {"q": q_score("Rate this against the criteria.", list(rubric))},
        )
        a = r["answers"]["q"]
        return {"score": a["score"], "confidence": a.get("confidence")}

    def jev_score_val(text: str, rubric: list[str]) -> float | None:
        """Bare score for the common ORDER BY case.

        Scale is 0..len(rubric)-1. Do not mix rubrics in one sort.
        """
        return jev_score(text, rubric)["score"]

    con.create_function(
        "jev_bool", jev_bool, ["VARCHAR", "VARCHAR"],
        "STRUCT(value BOOLEAN, prob DOUBLE)",
    )
    con.create_function(
        "jev_choice", jev_choice, ["VARCHAR", "VARCHAR[]"],
        "STRUCT(value VARCHAR, prob DOUBLE, confidence DOUBLE)",
    )
    con.create_function(
        "jev_score", jev_score, ["VARCHAR", "VARCHAR[]"],
        "STRUCT(score DOUBLE, confidence DOUBLE)",
    )
    con.create_function(
        "jev_score_val", jev_score_val, ["VARCHAR", "VARCHAR[]"], "DOUBLE",
    )
    return con
