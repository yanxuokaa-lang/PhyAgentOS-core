# ASSAY-001 — TypeSafe Jev: calibration and type safety, independently verified

**Verdict:** on CLINC150, Jev's chosen-option probabilities were calibrated (ECE 0.0204); on Banking77 they were not (ECE 0.0936, systematically overconfident). Across 8,576 responses there were zero type errors. Full write-up: https://donttrustme.ai/assay-001.html

- `PROTOCOL.md` — frozen 2026-09-17 before any query (`FREEZE.sha256`). `AMENDMENT-1.md` (before the run), Amendment 2 (after, in `REPORT.md`).
- `corpus/` + `CORPUS.sha256` + `PINS.txt` — Banking77 (GitHub PolyAI-LDN/task-specific-datasets @ 57ec275d) and CLINC150 `plus` (HF clinc/clinc_oos @ 155b9c71), hashed before the first call.
- `harness/run.py` — one Choice question per item, null option descriptions, every request/response logged. `harness/score.py` — deterministic scorer. `harness/controls.py` — positive controls.
- `raw/run/<corpus>/responses.jsonl` — every request and response, verbatim, sealed (`responses.sha256`). `raw/smoke/` — the 3-item connectivity checks, excluded from scoring.
- `scores/` — Pan's scores under the frozen rule (`jev-frozen-*`) and Amendment 2 (`jev-*`), plus controls.
- `rescore-tifa/` — the independent re-score: `rescore.py` written from `rescore/SPEC-FOR-INDEPENDENT-SCORER.md` on a different base model, blind; its outputs matched every field.
- `REPORT.md`, `GATE.md`.

## Re-run the scoring yourself
```
python3 harness/controls.py                      # scorer must go red and green first
python3 harness/score.py banking77 --sum-tol 0.02
python3 harness/score.py clinc150  --sum-tol 0.02
python3 rescore-tifa/rescore.py raw/run/banking77/responses.jsonl <(python3 -c "import json;print(json.dumps(json.load(open('corpus/banking77/categories.json'))))")
```
Re-running the *model* needs a TypeSafe key in `~/.config/typesafe/api_key`; that produces a new run, not this one.

A result applies to the artifacts and criteria examined. It is not a statement about Jev on any other task, corpus, or day.

ASSAY — a JourdanLabs verification practice · assay.jourdanlabs.com
