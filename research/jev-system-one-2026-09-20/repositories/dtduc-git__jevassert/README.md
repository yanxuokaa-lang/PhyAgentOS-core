# jevassert

[![CI](https://github.com/dtduc-git/jevassert/actions/workflows/ci.yml/badge.svg)](https://github.com/dtduc-git/jevassert/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/jevassert.svg)](https://pypi.org/project/jevassert/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Regression tests for [Jev](https://typesafe.ai) question packs: assert
**accuracy, calibration and cost** in CI, with recordings so runs are
deterministic, free and rate-limit free.

> Independent community tool. Not affiliated with TypeSafe AI.

Jev returns typed decisions with probabilities, which means two things your
normal test suite cannot check: *does the decision match the labels*, and
*does the stated probability mean what it says*. jevassert checks both — and
never calls the model during `check`, because CI should run on a recording.

```
record  →  predictions.jsonl  →  check  (offline, deterministic)  →  exit 0/1/2
```

## Quickstart

```sh
uvx jevassert record examples/demo-triage -o triage.jsonl   # needs TYPESAFE_API_KEY
uvx jevassert check  examples/demo-triage -p triage.jsonl --failures
```

`record` calls Jev once per case (concurrently, with retries) and writes one
JSONL line per case — model version, usage, latency, answers. `check` replays
that file: no API key, no network, same result every time.

Re-record when the pack questions, the gates or the model version change, then
compare:

```sh
uvx jevassert record examples/demo-triage -o triage-next.jsonl
uvx jevassert compare examples/demo-triage --a triage.jsonl --b triage-next.jsonl
```

## Benchmarking other backends

The same pack, runner and metrics can record a **general-purpose LLM** instead
of Jev, through TypeSafe's official
[system-one-adapter](https://github.com/typesafe-ai/system-one-adapter-python):
same questions, same golden cases, no TypeSafe key involved. This is how the
`results/` baselines in [jev-packs](https://github.com/dtduc-git/jev-packs) are
produced — one ground truth, several backends.

```sh
pip install 'jevassert[adapter]'   # optional extra; brings the provider SDKs

# any OpenAI-compatible endpoint (Ollama, vLLM, gateways)
uvx jevassert record packs/sms-spam -o sms-qwen.jsonl \
  --backend openai --model qwen2.5:7b --base-url http://localhost:11434/v1

# Claude (needs ANTHROPIC_API_KEY)
uvx jevassert record packs/sms-spam -o sms-claude.jsonl \
  --backend anthropic --model claude-haiku-4-5
```

Adapter recordings use structured outputs in probabilities mode, normalize the
distributions and allow two corrective retries on malformed output — the same
settings for every LLM backend, so comparisons are like for like. Cost is
priced at `check` time, not record time:

```sh
# self-hosted endpoint: free
uvx jevassert check packs/sms-spam -p sms-qwen.jsonl --input-price 0 --output-price 0
# hosted API at list price
uvx jevassert check packs/sms-spam -p sms-claude.jsonl --input-price 1 --output-price 5
```

`check` reports the models actually present in the recording (not the pack's
pinned version) and prices both input and output tokens.

## Packs

A pack follows **spec v0** (canonical:
[jev-packs/SPEC.md](https://github.com/dtduc-git/jev-packs/blob/master/SPEC.md)):

```
examples/demo-triage/
  pack.yaml     # state contract, questions, optional threshold floors
  cases.jsonl   # {"id", "state", "expect"} per line
  gates.yaml    # optional — jevassert quality gates
```

Questions are the SPEC shapes — `noul`, `choice` (`options`), `score`
(`levels`) — and every closed set must include the label `unknown` (Jev cannot
abstain). Score levels may carry `level_descriptions` so the API gets
situational text instead of bare keys:

```yaml
questions:
  queue:
    type: choice
    instructions: Which team should handle this message?
    options: {billing: ..., technical: ..., unknown: Cannot tell.}
  urgency:
    type: score
    instructions: How soon does this need a human response?
    levels: [low, normal, high, unknown]
    level_descriptions:
      low: No stated impact or time pressure; can wait.
      high: Stated impact or time pressure; needs a response today.
```

`thresholds` in the pack are the author's recommended operating point
(per-label probability floors; labels without a floor always go to review).

Gates live in `gates.yaml`, so the quality contract is explicit:

```yaml
min_accuracy: 0.85
max_ece: 0.15
max_cost_per_case_usd: 0.001
max_p95_latency_ms: 800
min_coverage_at_precision: {precision: 0.9, min_coverage: 0.6}
min_accuracy_ci_lower: 0.8          # bootstrap CI lower bound (n small-safe gate)
per_question:
  queue: {min_accuracy: 0.9, max_ece: 0.1}
```

## What `check` reports

- **accuracy** per question and overall, with a **bootstrap 95% CI**
  (`--bootstrap N`, default 1000; `0` disables)
- **ECE** — expected calibration error of the decision probability, equal-mass
  bins (meaningful with a few hundred items; small packs get a warning)
- **Brier** — for Noul questions
- **coverage** — accept when `p >= threshold`: how much you automate, at what
  precision
- **author thresholds** — auto-accept coverage under the pack's own floors
- **threshold suggestion** — `--target-precision 0.95` finds the highest-coverage
  cut that still reaches that precision
- **cost and latency** — dollars per case and p50/p95, from the recording
- **`--failures`** — every mismatch with expected/got/probability and the state

`check` warns when the recording's model version differs from `pack.tested`,
when cases are missing or extra, and when `tested` is still null.

Exit codes: `0` all gates pass, `1` a gate failed, `2` usage/IO error.
`--junit FILE` writes JUnit XML; `--report FILE` writes a markdown report
(the spec's `evidence.md`); `--json` prints machine-readable metrics.

## GitHub Action

```yaml
- uses: dtduc-git/jevassert@v0
  with:
    pack: examples/demo-triage
    predictions: triage.jsonl
    report: jevassert-report.md
```

Record outside CI (or as a scheduled job), commit the predictions file, and
the Action enforces the gates on every pull request.

## Commands

| command | what it does |
|---|---|
| `jevassert record PACK -o FILE [--model M] [--backend typesafe\|openai\|anthropic] [--base-url URL] [--resume] [--rpm N] [--dry-run] [--shuffle-options SEED] [--repeat N]` | call the backend for every case, write predictions JSONL |
| `jevassert check PACK -p FILE [--failures] [--bootstrap N] [--target-precision P] [--input-price X] [--output-price Y] [--partition dev\|test]` | compute metrics, evaluate gates, exit 0/1/2 |
| `jevassert compare PACK --a A --b B` | paired accuracy deltas + exact McNemar p-value |

`record` extras: `--dry-run` estimates tokens/cost from the pack without sending
anything; `--resume` retries only cases that errored; `--rpm` paces requests;
`--shuffle-options` records a robustness pass with permuted Choice option order
(Score levels stay ordinal) — compare it against the base recording; `--repeat N`
records N independent rounds (`FILE-r2.jsonl`, ...) and prints the discordant
decision count across rounds.

`check --partition dev|test` evaluates only one deterministic hash-split half
(`--partition-seed`, `--partition-ratio`) — tune thresholds on dev, then verify
on test without fooling yourself.

Environment: `TYPESAFE_API_KEY` (record only), `TYPESAFE_BASE_URL` (override
the endpoint, e.g. a local Jev-compatible replica), `OPENAI_API_KEY` (only when
the `openai` adapter backend points at a hosted endpoint), `ANTHROPIC_API_KEY`
(`anthropic` adapter backend).

## Reading the numbers

- Accuracy on <30 items per question is noisy (±19pp at n=10). Prefer packs
  with 100+ items per question before gating on tight thresholds, and let
  `--bootstrap` show the CI — gate on `min_accuracy_ci_lower` when n is small.
- ECE needs a few hundred items to be meaningful; with small n the bins
  collapse to per-item gaps. Treat it as a smoke signal, not a measurement.
- Stability: record twice and `compare` — the flip rate is your run-to-run
  noise floor. Question wording, option order and model version all move it;
  `--shuffle-options` isolates the option-order effect and `--repeat N` prints
  the flip rate automatically.
- Threshold tuning: suggest on one half, verify on the other —
  `check --target-precision 0.95 --partition dev`, then `--partition test`.
  (CIs are percentile bootstrap; with heavily tied probabilities the ECE CI can
  be slightly skewed.)

## Scope

- Backend-neutral: anything that speaks the System One request/response shape.
- File-based and offline-first: no server, no database, no telemetry.
- Not a labeling tool, not a dashboard, not an observability product.

`jevassert.packs` is the reference loader/validator for SPEC v0 and is meant
to be imported by other tools (jev-table, packs CI).
