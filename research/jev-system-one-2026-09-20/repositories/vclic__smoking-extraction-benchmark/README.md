# Smoking-history extraction benchmark

A paired comparison of TypeSafe Jev and OpenAI structured outputs on **1,000 synthetic outpatient progress notes**. Both systems receive the same note, annotation policy, candidate values, and ten typed questions. This repository contains the two benchmark CSVs, an executable evaluation program, and the measured results. It does **not** contain the program that generated the synthetic dataset.

## Results

| Metric | TypeSafe Jev 1.13.0 | OpenAI `chat-latest` |
|---|---:|---:|
| Smoking-status accuracy | 99.0% | 100.0% |
| Pack-years: all related fields correct | 93.7% | 98.7% |
| Quit date: all related fields correct | 99.3% | 100.0% |
| **Complete extraction: all 10 fields correct** | **92.4%** | **98.7%** |
| Pack-years among current/former smokers (n=600) | 89.8% | 97.8% |
| Quit date among former smokers with a date (n=222) | 97.7% | 100.0% |
| Estimated API cost for 1,000 notes | $0.18 | $24.54 |
| Mean request time | 0.405 s | 2.093 s |
| Median request time | 0.375 s | 1.782 s |
| 95th-percentile request time | 0.594 s | 3.719 s |
| Main-run wall time, 12 workers per provider* | 33.99 s | 179.31 s |

TypeSafe cost approximately **133 times less** and had **5.2 times lower mean request latency** in this run. OpenAI produced **63 more fully correct records**, a 6.3 percentage-point improvement in complete-extraction accuracy. These are pipeline-level measurements on this synthetic dataset, not general model rankings or evidence of clinical validity.

![Accuracy comparison](results/published/accuracy_comparison.png)

![Cost and runtime](results/published/cost_runtime.png)

\*The main run contains 998 notes; two successful pilot notes were reused. Accuracy, cost, and per-request latency include all 1,000. Two earlier OpenAI setup calls using a different schema are excluded. There were no retries in the included run. Wall time excludes setup, plotting, human interaction, and the gap between pilot and main run. TypeSafe's archived request timer ends at HTTP receipt; OpenAI's also includes JSON parsing and normalization. The clean runner uses the same timing boundary for both providers. Concurrent request times must not be added to infer wall time.

Costs are estimates using recorded usage and published list prices, **not billing statements**. The pricing snapshot is in [pricing.json](pricing.json): TypeSafe $0.042 per million input tokens, output free; OpenAI $5 per million input tokens and $30 per million output tokens. No cached-input tokens were reported. Credits, discounts, taxes, and setup calls are excluded. Sources: [TypeSafe pricing](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [OpenAI pricing](https://developers.openai.com/api/docs/models/chat-latest).

## Files

```text
data/
  model_inputs.csv          # ID, age, sex, encounter date, progress note
  patient_profiles.csv      # matching answer key and audit metadata
prompts/extraction_policy.txt
smoking_eval/               # shared extraction, provider calls, scoring, reporting
results/published/         # archived decisions, predictions, scores, errors, figures
docs/data_dictionary.md
tests/
pricing.json
requirements.txt
```

Each CSV contains 1,000 patients joined by `patient_id`. Notes contain quoted embedded newlines: use a CSV reader rather than splitting the file into lines. Empty CSV fields mean null; quit dates are strings that preserve year/month/day precision. **Only `model_inputs.csv` is sent to models.** The answer key is used locally for scoring, join validation, and a post-inference candidate-coverage audit. [Data dictionary and annotation rules](docs/data_dictionary.md).

## Reproduce the saved results without API calls

Requires Python 3.10 or newer. In a virtual environment:

```sh
python -m venv .venv
# Activate .venv using your shell's standard activation command.
python -m pip install -r requirements.txt
python -m smoking_eval report --out results/published
```

This checks input hashes and reconstructs every shared request, verifies the saved normalized predictions against the original typed answers, then regenerates `summary.json`, `report.md`, predictions, an error table, and accuracy/cost/runtime plots in PNG, SVG, and PDF formats. It reads the supplied `.jsonl.gz` records directly. Add `--no-plots` if Matplotlib is unavailable; scoring and HTTP calls otherwise use only Python's standard library.

The archived API logs are standardized exports: they retain every scored choice, TypeSafe's probabilities and confidence, normalized predictions, request fingerprints, token usage, timestamps, and latency. Repeated request text and provider request IDs were omitted during packaging. The input data, policy, and frozen shared code reconstruct the request content. Packaging was checked against all 2,000 original predictions; it did not rerun inference or alter the published answers.

## Run a new paired evaluation

Set `OPENAI_API_KEY` and `TYPESAFE_API_KEY` in your environment. Alternatively, copy `.env.example` to `.env`, fill it locally, and pass `--env-file .env`. Key files are gitignored; never commit them. The program does not accept keys on the command line or write authorization headers to outputs.

Validate the two input files before spending API credits:

```sh
python -m smoking_eval run --dry-run
```

Run both providers in parallel:

```sh
python -m smoking_eval run --notes data/model_inputs.csv --gold data/patient_profiles.csv --out results/my-run --workers 12
# If using a local key file, append: --env-file .env
```

The command performs inference, scoring, cost and latency aggregation, and plotting. Successful requests are saved atomically and reused when the same command is repeated. A changed input, policy, shared adapter, provider configuration, worker setting, or pricing file requires a new output directory. The archived `results/published` directory is protected from being reused as a live run. New runs under `results/` are ignored by Git by default.

Missing/failed predictions count as wrong in aggregate scores and are reported explicitly; an incomplete live run exits unsuccessfully after producing its available report. Authentication, billing, and schema HTTP errors stop new calls for that provider. Transient failures use bounded retries. A resumed run's wall span includes pauses; its request latency and wall time are distinct measurements.

Defaults are `--openai-model chat-latest` and `--typesafe-model jev-latest`. These are moving aliases: the measured TypeSafe response reported `jev-1.13.0`, while OpenAI returned only `chat-latest`. A rerun cannot guarantee the same underlying OpenAI snapshot. If you choose another model, pass a matching `--pricing` JSON with its published rates; the program refuses to silently apply another model's price. No API calls occur during `report`, tests, or `--dry-run`.

## What the comparison measures

1. A shared parser proposes numeric and date candidates from the note, including arithmetic over candidate smoking periods.
2. Each provider chooses among the **same candidate options** for the same ten questions. OpenAI uses strict JSON-schema structured outputs whose choice enums match TypeSafe's. TypeSafe probability/confidence metadata is retained but not imitated or scored for OpenAI.
3. Shared code normalizes the choices and applies policy dependencies, such as setting pack-years to zero for an explicit never-smoker and marking quit dates not applicable for current/never smokers.
4. The existing answer key scores smoking status, five pack-year fields, four quit-date fields, and their joint correctness. Numeric tolerance is ±0.1 pack-years, including numeric bounds. Other fields and nulls must match exactly.

This is a comparison of **two candidate-selection pipelines**, not unconstrained generative extraction. TypeSafe evaluates questions independently; OpenAI generates a joint answer. The identical choice schema improves comparability without making the architectures equivalent. Both providers see annotation rules but no gold labels, evidence spans from the answer key, or scenario tags. The adapter and prompts were frozen before full inference; reported errors were not used to tune them. Raw pre-normalization scores, per-class metrics, confusion matrices, positive pack-year error, and subgroup scores are in [summary.json](results/published/summary.json).

## Dataset and limitations

The cohort contains 300 current, 300 former, 250 never, and 150 unknown smoking-status cases, ages 50–80. Administrative sex is balanced 500 female/500 male. These design choices are not population prevalence estimates. All patients are fictional; no real patient records were used.

Notes were generated compositionally from authored fragments across 16 routine outpatient contexts and 12 formatting families. There are 35 relative quit-date cases, 50 histories with multiple smoking rates, and 20 notes containing intentional misspellings, plus missing information, ranges, lower bounds, relapses, stale entries, and distractors. The dataset-generation code is intentionally not included. The fixed CSV bytes and hashes are the reproducible benchmark artifact.

The frozen candidate parser omits the correct pack-year candidate for **five patients**: `SYN0107`, `SYN0419`, `SYN0562`, `SYN0681`, and `SYN0815`. These failures remain in both models' scores; their shared candidate constraints cap attainable complete-extraction accuracy at 99.5%. The parser was preserved during cleanup rather than repaired after inspecting the results. Coverage details are recorded in `summary.json`.

The benchmark and evaluation software were developed in the same project with AI assistance. These short, repeated templates do not represent the full diversity of real EHR text. The experiment is one run per provider, lacks independent clinician adjudication, and does not include a held-out real-world validation cohort. No confidence intervals or significance claims are presented; ordinary independent-patient intervals would ignore template dependence. Do not tune on these labels and describe a subsequent evaluation on the same cases as held out. Clinical deployment, longitudinal reasoning, and production throughput require separate validation.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests check saved-run replay, identical request reconstruction, normalization, scoring, candidate arithmetic, credential-safe error handling, and offline execution/resume using mocked provider calls.

## Planned arXiv preprint

A manuscript describing this benchmark and comparison is planned. **No arXiv submission or identifier exists yet.** After submission, this section will link to the preprint and add its citation, authors, and the exact code/data commit used in the paper. Until then, link to this repository and specify the commit rather than citing a nonexistent paper.

Repository: [vclic/smoking-extraction-benchmark](https://github.com/vclic/smoking-extraction-benchmark).
