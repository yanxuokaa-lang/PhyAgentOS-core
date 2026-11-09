# results/

`results.json` and `reliability.png` are the output of one full scoring
run of `harness/run_calibration.py`: 360 rows, `jev-1.13.0`, question set
`60658e143af92016`. The headline table in the top-level README is read
from this file, so the two should never disagree; if they do, the JSON is
the record and the README is stale.

`usage` inside the JSON is the cost of the run that produced it (350
fresh requests, ~359k tokens). `--analyze-only` recomputes every metric
from the cached responses and carries that block forward unchanged, so a
free re-analysis does not erase what the paid run cost.

`esci.json` and `reliability_esci.png` are the hard probe (Amazon ESCI,
306 rows, 30 queries); `shapes.json` the request-shape comparison.

Nothing here contains corpus text or raw model responses. Those live in
`.data/jev-calibration/` (gitignored); see the top-level README for why.
