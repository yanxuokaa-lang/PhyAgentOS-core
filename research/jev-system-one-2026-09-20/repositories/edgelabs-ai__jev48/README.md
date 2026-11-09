# Jev48: Open Jev Reproduction and Benchmark

**Jev48 is an open, auditable reproduction of TypeSafe's Jev decision model, built by
ChatGPT in one weekend and evaluated across six public benchmarks.** It includes the
2B checkpoint, benchmark code, frozen receipts, model card, and complete results.

An **Edge Labs AI** measured experiment. Independent and not affiliated with TypeSafe.

[Benchmark report](https://getedge.cc/jev48/) ·
[Model release](https://github.com/edgelabs-ai/jev48/releases/tag/v1.0.0) ·
[Results and methodology](RESULTS_PUBLIC.md) ·
[Machine-readable project guide](llms.txt)

**How close can ChatGPT get to Jev in one weekend?**

TypeSafe released Jev, a System One model: unstructured state in, typed probability distributions out, without autoregressive answer generation.

This repository is an auditable experiment. ChatGPT was given the goal, public internet research, open-source code, and external compute. It is allowed to reuse any public work it finds. The challenge is **not** “rebuild Jev from scratch.” It is:

> Given 48 hours and everything public on the internet, how much of Jev can an AI agent reproduce?

## Naming

- Experiment/repository: **Jev48** / `jev48`
- Derivative checkpoint, **only if a fine-tuned candidate wins selection**: **`jev48-2b`**
- If the untouched public base wins, Jev48 remains an experiment/result and no upstream checkpoint is rebranded as ours.
- Jev48 is independent and not affiliated with TypeSafe.

## Status

**Open-model experiment and six public Jev benchmark comparisons published.**

The frozen open-model experiment completed on Modal. The dev-only gate selected the
`soft-lr3e-6` derivative, and the locked test/OOD receipts passed the release audit.
Private Jev access was unavailable, so the direct same-row comparison remains unrun.
Instead, the frozen derivative was evaluated zero-shot on the pinned public
`LocalLLaMA/typed-decisions` benchmark, which publishes an independently measured Jev
1.13.0 aggregate row. See [`RESULTS_PUBLIC.md`](RESULTS_PUBLIC.md). No Jev output has
been used for training or model selection.

Five additional zero-shot comparisons were subsequently added without changing the
model: all 2,000 PhishNChips v5.2 emails and all 231 public JevBench v1.2.2
tasks. Jev48 produced higher phishing ranking AUROC (0.769 vs source-published 0.689),
while its fixed 0.5-threshold accuracy remained materially worse (50.0% vs 62.6%).
The AUROC comparison is aggregate and unpaired, not a parity claim. It tied Jev on all
48 public easy-tier JevBench tasks but trailed on the complete public suite. See
[`RESULTS.md`](RESULTS.md) and [`receipts/`](receipts/). Row-level predictions are
withheld from the public package because the benchmark inputs carry source-specific terms.
The complete six-suite registry and all audited exclusions are in
[`BENCHMARK_REGISTRY.md`](BENCHMARK_REGISTRY.md).

## Public benchmark results

| Benchmark | Evaluated cases | Jev | Jev48 | Delta | Comparison |
|---|---:|---:|---:|---:|---|
| Typed decisions | 2,000 | 72.7% | 57.7% | -15.0 pts | Aggregate / unpaired |
| PhishNChips v5.2 | 2,000 | 62.6% | 50.0% | -12.6 pts | Aggregate / unpaired |
| JevBench public v1.2.2 | 231 | 86.6% | 69.7% | -16.9 pts | Paired outcomes |
| BTZSC pilot | 300 | 75.3% | 83.3% | **+8.0 pts** | Aggregate / unpaired |
| Code review | 480 | 99.0% | 81.9% | -17.2 pts | Repeated Jev reference |
| CLASH conflicts | 1,289 | 98.6% | 0.0% | -98.6 pts | Aggregate / unpaired |

These are all six eligible reproducible public suites: 6,300 evaluated decisions or
cases, with one suite win for Jev48. On PhishNChips, Jev48 also recorded higher ranking
AUROC (0.769 vs. the source-published Jev result of 0.689), despite its lower fixed
0.5-threshold accuracy. Full methodology, metric definitions, source pins, limitations,
and receipts are in [`RESULTS_PUBLIC.md`](RESULTS_PUBLIC.md),
[`RESULTS.md`](RESULTS.md), and [`receipts/results/`](receipts/results/).

## What ChatGPT chose

After auditing the emerging OSS ecosystem, ChatGPT selected [`Mapika/decider`](https://github.com/Mapika/decider) as the strongest public starting point and pins it at:

```text
repo:   Mapika/decider
commit: b08acf787d5d1f718a8c36c4677960f43772c7be
model:  Mapika/decider-2b
weights revision: 4a0e86782adfdb7393e04b8ec9f6b939dca09273
```

That choice is part of the experiment. A capable agent should use public prior art rather than deliberately reimplement it.

### What Jev48 actually changes

The pinned starting model already trains on many hard-label decision and preference datasets. Jev48 adds one controlled experiment aimed at probability quality:

> **Do not collapse multiple human judgments into one winner. Train on the empirical distribution of human votes.**

We aggregate expert MT-Bench judgments over real model responses into distributions such as:

```text
Conversation A preferred   0.60
Conversation B preferred   0.20
Tie                        0.20
```

During development we compare, from the exact same base checkpoint:

```text
hard-majority labels
vs.
soft human-vote distributions
```

Same model, replay data, loss family, benchmark, and candidate-selection rules. Only
the selected soft-label winner was evaluated on locked rows, so the final locked
result is not a causal hard-vs-soft ablation.

## Evaluation design

There are two locked evaluation axes.

### 1. Human preference calibration

`lmsys/mt_bench_human_judgments`, pinned at revision:

```text
ee34b9d273a7a35e4415c87678526c56c471098c
```

The input contains anonymous real model conversations; model identities are hidden from the decision model. Multiple expert votes are aggregated into an empirical target distribution.

The 80 MT-Bench question IDs are assigned outcome-blind to:

```text
50 train
10 dev
10 calibration
10 locked test
```

All judgments for one question ID stay in one split.

### 2. Broad transfer

17 public tasks explicitly marked held-out/evaluation-only by the pinned `decider` training registry. Candidate order is randomized deterministically without using labels.

Per task:

```text
10 calibration rows
40 locked OOD rows
```

This directly attacks the failure mode seen in prior Jev-like work: in-domain parity that disappears on new tasks.

## Integrity rules

These are enforced in code:

1. **Jev outputs are never used for training.**
2. **Candidate selection reads dev only.**
3. **Temperature is fitted after selection on calibration only.**
4. **Locked `test` / `ood` are evaluated only after candidate selection.**
5. **The public starting model and Jev48 see identical frozen rows.** A future live
   Jev run must use those same rows to qualify as paired.
6. **Every benchmark file is hashed before any future live Jev query.**
7. **If no fine-tune passes the predeclared dev gate, the public base remains the selected reproduction.** No forced win.
8. **Starting code/weights and related work are disclosed.**

See [`INTEGRITY.md`](INTEGRITY.md).

## Run it

### Local tests

```bash
python -m pip install -e '.[dev]'
pytest
```

### Full GPU experiment

```bash
python -m pip install 'modal>=1.5,<2'
modal setup
modal run modal_app.py
```

The run:

1. builds and hashes the MT-Bench vote dataset;
2. builds the pinned transfer/regression/replay suites;
3. benchmarks untouched `decider-2b` on dev;
4. trains one hard-majority and three soft-vote candidates;
5. selects using dev only;
6. benchmarks the selected model and base on the locked suite;
7. fits each system's temperature on identical calibration rows;
8. persists raw predictions, configs, model weights, hashes, and reports.

### Add the live Jev comparison

Create the secret **locally**. Do not paste it into chat.

```bash
modal secret create jev48-secrets TYPESAFE_API_KEY=YOUR_KEY
# or: modal secret create jev48-secrets OPENROUTER_API_KEY=YOUR_KEY
modal run modal_jev.py --run-name <existing-run-name>
```

The separation is deliberate: model selection and locked open-model evaluation finish before any live Jev result exists. The Jev run is resumable after every successful row.

## Outputs

The final run produces:

```text
results/selection.json
results/final/base.raw.jsonl
results/final/base.calibrated.jsonl
results/final/jev48.raw.jsonl
results/final/jev48.calibrated.jsonl
results/final/jev.raw.jsonl                 # if live Jev is run
results/final/jev.calibrated.jsonl
results/final_report.md
results/final_report.json
results/bootstrap-*.json
site/index.html
```

The public result page is generated from `final_report.json`; marketing numbers are not manually typed into the page.

## The claim

No claim is hard-coded in advance.

Possible honest outcomes include:

- “ChatGPT got within X points of Jev in a weekend.”
- “The public starting point was already surprisingly close; human-vote training improved calibration by Y.”
- “The easy parts were reproducible quickly; Jev kept a large transfer advantage.”
- “Our fine-tuning made it worse, so the public base won selection.”

The strongest wording is generated **after** the locked receipts exist.

## Related work

This project is not the first open Jev-like implementation. See [`RELATED_WORK.md`](RELATED_WORK.md). The most important public references discovered during the challenge include:

- TypeSafe Jev
- Mapika/decider
- jaredpalmer/kev
- TianyuCodings/NanoJev
- TheoLeeCJ/SemIf / openjev
- razorback16/openjev
- daseinlabs/open-jev

The novelty claim here is deliberately narrow: **the 48-hour agent experiment,
frozen open-model evaluation, independent aggregate comparison, and empirical
human-vote probability supervision**, not invention of the System One model class.

## License

Jev48's original code is MIT. Upstream models/code/datasets retain their own licenses. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
