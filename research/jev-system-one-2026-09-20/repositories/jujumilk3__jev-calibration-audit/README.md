# jev-calibration-audit

An independent, API-only audit of the calibration of TypeSafe AI's **Jev**, a
"System One" decision model that answers pre-defined questions over a text
`state` with probability distributions instead of generated text.

Not affiliated with TypeSafe AI. No model weights, no fine-tuning, no
distillation — every number here comes from public HTTP calls and public
datasets.

## Why

Jev is sold on calibration: the probability it returns is supposed to mean what
it says. Independent measurements published so far disagree with each other, and
none of them report confidence intervals:

| Source | n | Result |
|---|---|---|
| MMLU probe (Archer Hume) | 1,200 | ECE 0.031 — near calibrated |
| difficulty sweep (SamuelSacco) | 800 | under-confident, log-odds slope 2.1–2.6 |
| spam (Enron-derived) | 19,528 | good at the extremes, over-confident mid-range |
| phishing, post-cutoff data | 2,000 | ECE 0.154 — over-confident |

The same model looks under-confident on one corpus and over-confident on
another. Contamination, label noise and difficulty are all plausible causes and
nobody has separated them. TypeSafe publishes no reliability curve and does not
document how its `confidence` field is computed.

This repository measures **what the probability means**, not just whether the
argmax is right:

1. sign of the calibration error across domains
2. probabilistic coherence — does `P(A)` from a Noul match the two-option Choice?
3. invariance — option order, label wording, irrelevant distractor options
4. interference — does asking 30 questions about one state change each answer?
5. hedging vs resolution — Murphy decomposition, accuracy-controlled comparison
6. Korean, where no quantitative evaluation exists at all

## Results

Seven experiments, ~7,000 API calls, under one US dollar. Full write-up in
[FINDINGS.md](FINDINGS.md); raw per-call records in `results/raw/`.

| # | Question | Answer |
|---|---|---|
| 1 | What happens when the abstain option is removed? | Accuracy 0.950 → **0.000** on unanswerable items, stereotype rate 0.03 → **0.79**, at 0.79 confidence. ECE 0.023 → **0.793** |
| 2 | Does Korean break calibration? | No. Accuracy falls 6.5 points on identical items, confidence falls with it, ECE unchanged (0.076 vs 0.075). Instruction language is irrelevant |
| 3 | Is the probability a property of the judgement? | No. Complements sum to 0.71–1.42; a Noul and a two-option Choice over the same question differ by 0.125 on average |
| 4 | Option-order bias? | **None.** Mean shift 0.005, zero argmax flips in 400 — unlike the LLM-judge literature |
| 5 | Do bundled questions interfere? | No. 16 questions vs 1: confidence shifts 0.008, answers flip 0.4%, latency +14 ms. Holds under adversarial neighbours |
| 6 | Are identical requests cached? | No. 50 identical requests gave 15 distinct answers; the cookbook `uid` trick adds variance rather than revealing it |
| 7 | Latency from Seoul | p50 280 ms, p95 397 ms for one question |

The state-blind control matters for anyone benchmarking this model: shown the
options with the question removed, it still scores 0.38–0.46 against a chance
rate near 0.15.

## Layout

```
src/jev_audit/
  client.py      direct api.typesafe.ai client, retries, Noul/Choice/Score helpers
  preflight.py   version, caching, latency and a Korean smoke probe
  data.py        MMLU-ProX parallel loader, KoBBQ loader
  runner.py      thread pool over one client, append-only JSONL recorder
  probes.py      fixed bilingual probe set for the drift ledger
  drift.py       daily fixed-probe run
  metrics.py     ECE, Brier, Murphy decomposition, bootstrap CI, noise floor, RPS
  experiments/
    parallel_ko_en.py   same items in both languages, plus mixed and state-blind arms
    abstention.py       KoBBQ with and without the unknown option
    coherence.py        one judgement asked four ways
    interference.py     one question alone vs bundled with 10 and with 5 hostile
results/         committed outputs
data/            downloaded datasets (gitignored)
```

## Running

```bash
uv sync
cp .env.example .env        # fill in JEV_API_KEY

uv run python -m jev_audit.preflight
uv run python -m jev_audit.experiments.parallel_ko_en -n 1000
uv run python -m jev_audit.experiments.abstention -n 600
uv run python -m jev_audit.experiments.coherence -n 400
uv run python -m jev_audit.experiments.interference -n 250

uv run python -m jev_audit.drift          # one ledger entry
uv run python -m jev_audit.drift --show   # print the series
```

### Drift ledger

TypeSafe's stated policy is that a published benchmark "retires the moment it is
published", and the version aliases move. A fixed probe set run on a schedule is
the only way to see the model change under you, and it cannot be backfilled
later. Ten probes a day costs well under a dollar a month.

```
0 9 * * *  cd /path/to/jev-calibration-audit && /path/to/uv run python -m jev_audit.drift
```

## Method notes

Rules the measurements have to follow, or the numbers mean nothing:

- report ECE against a **noise floor**, not against zero — at n=60 a perfect
  model still scores ≈0.045, so small-n claims in either direction are noise
- bin-based ECE plus bootstrap CIs; check the spread before trusting bins, since
  a saturated distribution collapses them
- ECE is not comparable across models at different accuracies — control for it
- log every response's `model` field; aliases move
- include a **state-blind baseline** (empty or irrelevant state) in every set,
  because multiple-choice items are partly solvable without the state
- `confidence` is undocumented, so all metrics are computed from `probabilities`

## Datasets

Public sets only, licence checked before use. The Korean work leans on
`naver-ai/kobbq` (MIT, 81k items, includes an explicit "unknown" option) and
`li-lab/MMLU-ProX` (MIT, the same 11,759 items in Korean and English, which is
what separates a translation artefact from a genuine language effect). Sets
whose cards state no licence are not redistributed here.

## Licence

MIT for the code. Datasets keep their own licences; results are reported, not
redistributed.
