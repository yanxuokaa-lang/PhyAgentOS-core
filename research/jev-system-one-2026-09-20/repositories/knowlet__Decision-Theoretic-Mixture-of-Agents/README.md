# Decision-Theoretic Mixture-of-Agents

## Latest: v1.5.0 — six tasks, a canonical request fixture, and a 192-question OpenJev head-to-head

**[Full English paper](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/download/v1.5.0/paper.en.pdf)** · **[完整繁體中文論文](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/download/v1.5.0/paper.zh-TW.pdf)** · [Versioned release](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/tag/v1.5.0)

[Inference, analysis and manuscript run](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/actions/runs/35329947656) · [Full reproducibility bundle](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/download/v1.5.0/reproducibility.zip) · [Verification](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/download/v1.5.0/verification.json) · [Checksums](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/download/v1.5.0/SHA256SUMS)

**This still does not establish a universally optimal MoA architecture, and it does not establish that either system reasons better.** On the widened pilot the three simple decision-theoretic controls keep the lowest macro objective (0.136667), and development-calibrated OpenJev 4B (0.200573) is now worse than the same-panel empirical selector (0.151094) by 0.049479 with a paired interval of [0.020833, 0.079460] that no longer includes zero. That contrast mixes selection with the ability to withhold: one added task is deferral-dominated, where a fixed-panel selector has no choice but to answer, and the gap is concentrated rather than even.

Two datasets are added from the same pinned ProEval revision: `gqa` (image-grounded short answers) and `jigsaw` (toxicity verdicts). The primary binary task pool goes from four to six, and the four earlier datasets keep their published split salt, so every previously scored case is still selected and their per-task results reproduce the v1.3 release.

## What actually ran

| Evidence layer | Executed scope | Important limit |
|---|---|---|
| v1.1 finite synthetic study | Explicit losses, correlated channels, matched controls, Bellman reference checks | Synthetic support and conditional optimality only |
| v1.2 RouterBench | 26,821 archived questions, four models, 5,398 held-out questions | Historical response selection; no new worker inference |
| v1.3/v1.4 ProEval | GSM8K, SVAMP, MMLU, StrategyQA: 5,156 questions, eight fixed model identities, 1,036 held-out questions; five pinned files including a separate DICES audit | Pool replacement is not a within-agent training trajectory |
| v1.4 OpenJev pilot | 128 test + 64 development groups from four binary datasets; two Qwen3.5 capacities; 12 strategies; 474 actual local forward passes | One neural family, small reused benchmark subset, explicit CPU-accumulation variant |
| v1.5 ProEval replay | Adds GQA and Jigsaw: 8,656 questions, eight fixed identities, 1,732 held-out questions; seven pinned files | Two more well-known benchmarks; familiarity and contamination are not excluded |
| v1.5 OpenJev pilot | 192 test + 96 development groups across six datasets; 12 strategies; 711 actual local forward passes; 4,608 paired ledger rows | Selector inference only; workers stay archived, so the panel is reused, not newly generated |

The 711 forwards are 576 primary passes, 96 reversed-order probes, 24 exact-input repeats and 15 per-worker warmups (twelve 4B shards, three 0.8B). Workers remain archived; newly generating their answers, multi-agent debate and human preference elicitation were not performed.

**296 regression tests pass with zero failures or skips.** Each of the fifteen inference shards also passes the same 11 upstream tests and 21 interface tests, and repeated executions are not counted as new unique tests. The full ProEval experiment runs twice in separate processes with all non-timing outputs compared, and every paired table is re-derived independently before publication. These are computational checks, not independent scientific replication.

## What changed in v1.5, including the failures on the way

The first attempt failed its request-hash gate although all fifteen shards succeeded: the shards and the analysis job agreed on every case, panel and split, but install different pinned `numpy` builds, so re-fitting moved the last bits of the serialized candidate error estimates and the same case hashed differently. This is the failure v1.4 patched with a ULP recovery search, whose writeup recommended shipping a canonical fixture instead.

Request text is now canonical by construction: candidate error estimates are rounded to eight decimal places before rendering, far below any decision-relevant precision. A test pins the invulnerability to a last-bit perturbation. The corrected run then failed one step later, in the reporting job, whose gate asserted that the *parent* run's conclusion was `success` while a reporting job belonging to that same run was still executing. The run after that completed every scientific step and failed only while looking up an environment variable in the release step, so the verified artifact was published by a dispatch-only workflow instead ([v1.5.0](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/tag/v1.5.0) is that artifact).

Every superseded run stays visible, and no release was overwritten.

## Actual head-to-head on 192 held-out groups

Each of the six datasets contributes 32 held-out unique groups, and both capacities see the same cases. The fixed-three empirical selector, panel majority and OpenJev see the same three acquired candidate answers. OpenJev additionally reads the task text and receives training-derived conditional candidate error estimates, never current-task gold. Bellman/static/myopic may instead acquire fewer answers, and GQA shows why that matters.

`J = wrong-answer loss (1) or deferral loss (0.25) + 0.01 × acquired worker answers`

The 0.01 is an assumed loss charge, **not dollars**. Selector compute is excluded from this headline objective and disclosed separately, which favors neural add-ons. Accuracy below is **among answered cases**, not all questions. The macro column averages the six datasets equally, so a deferral-dominated task contributes its floor to every method.

| Algorithm | J ↓ | Coverage | Accuracy among answered | Mean queries |
|---|---:|---:|---:|---:|
| Bellman | 0.136667 | 79.17% | 90.79% | 1.167 |
| Myopic / static | 0.136667 | 79.17% | 90.79% | 1.167 |
| Cumulative-score prompt control | 0.138490 | 90.10% | 89.60% | 2.000 |
| Prompt top-1 control | 0.138750 | 83.33% | 89.38% | 0.854 |
| Single model | 0.140208 | 83.33% | 89.38% | 1.000 |
| Disagreement trigger | 0.140729 | 79.17% | 91.45% | 2.094 |
| Empirical fixed-three selector | 0.151094 | 89.06% | 89.47% | 3.000 |
| Panel majority | 0.175833 | 100.00% | 85.42% | 3.000 |
| OpenJev 4B, raw | 0.191458 | 93.75% | 84.44% | 3.000 |
| OpenJev 4B, development-calibrated | 0.200573 | 77.60% | 85.23% | 3.000 |
| OpenJev 0.8B, development-calibrated | 0.207083 | 100.00% | 82.29% | 3.000 |
| OpenJev 0.8B, raw | 0.233125 | 58.33% | 83.04% | 3.000 |

The cumulative-score control is TF-IDF/ridge plus a score-prefix rule. **It is not CERA-MoA**, and its position is exploratory rather than a preregistered superiority claim. Complete 12-strategy records, including the separate matched-majority implementation, are in [summary.csv](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/download/v1.5.0/summary.csv).

### Paired uncertainty, not just the best row

Differences are first minus second; positive is worse for the first method. Intervals condition on fitted policies and the stored inference records.

| Contrast | Difference in J | 95% paired interval | 98.75% multiple-comparison interval |
|---|---:|---|---|
| 4B raw − fixed-three | +0.040365 | [+0.015625, +0.069010] | [+0.010417, +0.074219] |
| 4B calibrated − fixed-three | +0.049479 | [+0.020833, +0.079460] | [+0.013664, +0.087240] |
| 4B calibrated − Bellman | +0.063906 | [+0.035228, +0.096458] | [+0.026146, +0.106875] |
| 0.8B raw − 4B raw | +0.041667 | [−0.006510, +0.088542] | [−0.018229, +0.100260] |

Unlike v1.4, the calibrated same-panel contrast no longer crosses zero at this sample size. That is a statement about the declared objective, which charges 0.01 per acquisition and 0.25 for a withheld decision, not a statement that the neural selector reasons worse. [Exact contrasts](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/download/v1.5.0/comparisons.csv).

### Where the difference actually sits

Per-dataset objective for OpenJev 4B development-calibrated minus empirical fixed-three. Both sides acquire exactly the same three answers, so this isolates the select-or-defer decision.

| Dataset | Difference | 95% paired interval | calibrated coverage | fixed-three coverage |
|---|---:|---|---:|---:|
| MMLU | +0.078125 | [+0.015625, +0.148438] | 68.75% | 87.50% |
| GQA | +0.070312 | [−0.054688, +0.203125] | 68.75% | 59.38% |
| StrategyQA | +0.062500 | [+0.007812, +0.125000] | 75.00% | 87.50% |
| Jigsaw | +0.039062 | [−0.023633, +0.093750] | 71.88% | 100.00% |
| GSM8K | +0.031250 | [+0.007812, +0.062500] | 87.50% | 100.00% |
| SVAMP | +0.015625 | [0.000000, +0.039062] | 93.75% | 100.00% |

GQA is *deferral-dominated* under the declared loss: every candidate's archived error there exceeds 0.25, so Bellman, static and myopic withhold on all 32 held-out groups and score exactly the deferral loss. The recorded GQA answers were also produced with access to an image that this replay never sees, so the text-only prompt controls are handicapped. On that task the comparison is about whether a supplied panel can be declined.

MMLU is the largest dataset gap whose interval excludes zero. There the calibrated selector answered 68.75% of cases, 18.75 points less often than the empirical selector, and was less accurate on the cases it did answer (90.91% against 96.43%). That is a calibration and stopping result, and it is reported as one.

### Calibration and order sensitivity

For 4B, treating the highest candidate option mass as a correctness proxy gives Brier 0.233522 and ECE 0.275291. A 96-case development success calibrator gives 0.136781 and 0.061337. The raw option score was never guaranteed to estimate correctness, and this is not evidence about proprietary Jev's calibration. For the 0.8B control the same pair is 0.355898/0.441173 and 0.145989/0.037017.

The option-order probe reverses the presented actions on 48 test groups per model and flips the selected **action ID** on 42/48 for both capacities. That is not a factual failure rate: for 4B only **10/48** probes change the returned answer or the deferral decision, and the mean terminal loss barely moves (0.182292 to 0.161458). For 0.8B the changes are real and larger: **38/48** probes change the answer or deferral, with mean loss moving from 0.255208 to 0.244792. Reproduce with `audit_openjev_answer_order.py` against the published probe records.

### Selector cost and CPU

Measured selector median/p95 times per case are **22.857/33.204 seconds for 4B** and **2.332/6.249 seconds for 0.8B**, over different hosted CPU mixtures, at a mean of 437.6 input tokens each. They are not GPU or TypeSafe-service timings. Arithmetic controller evaluation is tens of microseconds per replayed case, excluding offline fitting. Adding a hypothetical selector-overhead charge from 0 to 0.1 loss units only widens the OpenJev gap, so the published conclusion is not an artifact of excluding that cost; the exclusion favors the neural side.

The unchanged upstream readout uses a disclosed CPU adapter: BF16 stored weights/outputs with FP32 accumulation for Linear/Conv1d. It is not bit-identical to native BF16. Details: [runtime amendment](OPENJEV_RUNTIME_CHANGELOG.md).

### What does and does not reproduce

Two complete executions of this same pinned pipeline were compared directly. Every symbolic control row matched exactly, because the controls are computed from the archive through the canonical fixture. The neural rows did not: 15 of 4,608 paired selector rows, covering 14 of the 192 cases, changed the selected action, and 8 of those changed the recorded loss. Hosted runner CPUs differ between machines, so near-tied option scores can cross. The paired intervals above therefore condition on one recorded execution and exclude that run-to-run component, which is the correct reading of a pilot of this size.

## What the ProEval layer found

Across 1,732 held-out binary questions, refitted Bellman, static and myopic again take identical per-case actions; the six-dataset macro J is 0.127979 against 0.170293 frozen, a refit gain of 0.042314 with a conditional 95% interval of [0.033119, 0.051476]. Most of that gain is Jigsaw, where the frozen policy was badly miscalibrated (0.352105 against 0.158026); GQA contributes exactly zero because both phases withhold. For the four earlier datasets alone the gain is 0.014952, the value published in v1.3, and their per-task results reproduce that release apart from machine-precision summation in one Brier score.

GQA is deferral-dominated and is kept in the average rather than dropped after the outcome was seen; the per-task spread and deferral rate are published in `policy_discrimination.csv`. Its pinned release also contains nine prediction cells holding a data-generation debug string instead of a model answer, of which six fall on the identities replayed here; those are treated as unparseable and counted in the source audit. The Jigsaw ground truth is an annotator toxic-fraction thresholded strictly above 0.5, a rule that reproduces the archive's own label column exactly on every comparable pair.

DICES remains quarantined from headline binary comparisons: 439/1,500 rows violate the documented common label-range filter for the selected models, and the retained 1,061 rows have only 308 exact question groups. Its all-deferral result does not validate human preference decisions.

## Reading CERA-MoA and TypeSafe Jev correctly

[CERA-MoA](https://arxiv.org/abs/2609.18779) co-trains agents and router heads, using frozen mid-layer query features, reward-aligned familiarity and cumulative-prefix allocation. It has actual agent-training evidence that this archive replay does not reproduce. Its reported open-ended aggregator selects the most familiar agent's completion, not a generative synthesis of all candidates.

[TypeSafe Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) supplies a typed probabilistic decision interface. Type-valid does not mean semantically correct, and action-choice mass is not automatically action-success probability. Our actual OpenJev results do not benchmark that proprietary model. `TheoLeeCJ/openjev` is an independent open-model logits readout, not proprietary Jev or its weights or training. [Detailed primary-source comparison](LITERATURE_v1.3.md).

The paper separates competence estimation, external utility, legal-action authorization and acquisition strategy. Conditional Bellman and approximation/margin bounds are stated with assumptions. An additional dependency proposition shows that positively priced outputs never read by a final decision cannot help under action-invariant/no-side-effect assumptions. None proves universal MoA superiority or refutes co-evolving training.

## Reproduce and inspect

A push that touches the pilot's own source runs Actions → **OpenJev versus decision-theoretic controls**: fifteen shards, the full six-dataset ProEval replay twice, the ledger gates, the independent re-derivation of every paired table, and both manuscripts. Publication is a separate dispatch-only step in this version, because the Actions token in this repository is refused permission to create releases; the publisher re-checks every checksum and gate on the artifact and refuses to overwrite an existing release.

The v1.4 publication workflows are dispatch-only now, since they rebuild an older version from a pinned historical inference run. Everything needed to re-verify this release is inside `reproducibility.zip`: the exact executed source, every shard's records, the analysis outputs and the manuscripts. No neural weights are needed to re-run the analysis. See [inference scope](RUNNING_OPENJEV.md), [population transfer](RUNNING_TRANSFER.md) and [v1.5 changes](V1.5_CHANGELOG.md).

## Earlier evidence and disclosure

[v1.4 OpenJev pilot](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/tag/v1.4.0) · [v1.3 population transfer](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/tag/v1.3.0) · [v1.2 RouterBench](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/tag/v1.2.0) · [v1.1 synthetic report](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents/releases/tag/v1.1.0)

A public GitHub technical report is not peer review, venue acceptance, arXiv deposit, DOI registration or independent replication. AI assistance was used for implementation, writing and checking. No institutional endorsement is claimed. Model weights, raw benchmark text and font files are not redistributed; third-party rights remain separate. The owner has not selected a blanket reuse license for this project.

v1.5.0 release assets were published from the verified artifact of run 35329947656 using the maintainer's GitHub credentials, because the Actions token cannot create releases in this repository; the publisher workflow and every gate it applies are in `.github/workflows/publish-v15-release.yml`.
