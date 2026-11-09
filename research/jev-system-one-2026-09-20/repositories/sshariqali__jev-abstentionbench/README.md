# Abstention, measured

Meta's [AbstentionBench](https://arxiv.org/abs/2506.09038) tests whether a model declines to
answer questions that have no answer. This repository runs it against Jev, a model from
TypeSafe that returns probabilities for typed questions instead of text, and compares the
result against the twenty systems Meta published numbers for.

Write-up: <https://sshariqali.github.io/jev-abstentionbench/>
Method, limitations and error log: <https://sshariqali.github.io/jev-abstentionbench/method.html>

The cached model responses are committed, so `analyze.py` regenerates every table without an
API key and without spending anything.

## Result

| | |
|---|---|
| Mean per-dataset abstention F1 | 0.855 |
| Best published | 0.760 (GPT-4o), then Gemini 1.5 Pro 0.756 and Qwen2.5 32B 0.754 |
| Rank | 1 of 20 |
| Datasets | 16 of the 31 rows in Meta's results file that permit a valid comparison |
| Questions | 5,933 |
| Cost | $0.1877 measured |
| Time | about 5 minutes at 8 concurrent workers, median 386 ms per request |

Rank 1 holds with nothing fitted at all (F1 0.779), under one global threshold (0.812), in 20
of 20 random splits, and in all 16 leave-one-dataset-out runs.

The shape of the difference matters more than the gap. All 19 published systems run precision
between 0.81 and 0.95 against recall between 0.44 and 0.71: they decline rarely, and correctly
when they do. Jev sits at 0.857 and 0.868 because its threshold is a parameter you set.

## The two sides are answering different questions

Jev is asked, directly, whether the question can be answered, and returns a probability that
code thresholds. The published models saw the bare question at temperature 0.8 with no system
prompt telling them they could decline, answered in prose, and a Llama-3.1-8B judge inferred
refusal from the text afterwards at 88% accuracy against human annotation.

One side is scored on a direct answer to "is this answerable?", then, and the other on a
judge's reading of what its prose implied about a question it was never asked. The asymmetry
runs in Jev's favour. It is the difference under examination rather than a defect in the setup,
but it belongs next to the number wherever the number appears.
[The method notes](https://sshariqali.github.io/jev-abstentionbench/method.html) list it with nine other limitations.

## The published field is from 2025

Meta's results file holds 23 model variants and the newest is o1. Nothing released in 2026
appears in it. Rank 1 of 20 is rank 1 against a field fixed in 2025, not against the current
state of the art, and nothing measured here says how a current frontier model abstains.

## Confidence on forward-looking questions

Experiment 04 tried to forecast 4-week price direction on FinTexTS. It failed; a positive
control confirmed the pipeline was sound by recovering the past move at three times the noise
floor. That negative result stands.

Each of its 3,000 requests carried one forward-looking question alongside twelve descriptive
ones about text already in the prompt, in the same call:

| question type | n | mean | sd | range | above 0.90 or below 0.10 |
|---|---|---|---|---|---|
| Forward-looking | 3,000 | 0.465 | 0.089 | 0.20–0.70 | 0.00% |
| Descriptive | 36,000 | 0.260 | 0.319 | 0.02–0.99 | 61.7% |

No forward-looking answer fell outside 0.20 to 0.80, and 97.1% sat between 0.30 and 0.70.
Tightening the band to 0.25–0.75 puts 19 of 3,000 outside it. The same model gives 62.5%
extreme answers on SQuAD 2.0 and 46.3% across the AbstentionBench battery, both descriptive.

`python experiments/06_calibration/calibration_dichotomy.py` reproduces this from the committed
caches and makes no API calls.

## Reproducing

```bash
python -m venv .venv && .venv/Scripts/activate      # or source .venv/bin/activate
pip install -r requirements.txt

python scripts/fetch_data.py
python experiments/05_abstention/build_abstention_set.py
python experiments/05_abstention/analyze.py
```

The first three steps need network access but no API key. `analyze.py` reads
`cache_abstention.json`, which is committed.

The build is deterministic (`random.Random(0)`, `PER_CELL = 200`) and should produce 5,933
questions across 22 datasets with sha256
`e457f89ecf7c3edfee0cca787552747816407566459b76cb078ef9cb4940b7fc`. A different hash means an
upstream dataset has changed since 2026-09-20, and `analyze.py` reports how many rows it could
not find in the cache.

To call the API yourself, put `TYPESAFE_API_KEY` in `.env` at the repository root and run
`run_abstention.py`. The full set costs about $0.19.

## Layout

| Path | Contents |
|---|---|
| [`docs/method.html`](https://sshariqali.github.io/jev-abstentionbench/method.html) | Every parameter, ten limitations, the robustness checks |
| `experiments/05_abstention/` | Build, run, analyze, plus the SQuAD 2.0 answer-presence test and its topicality control |
| `experiments/06_calibration/` | Forward-looking against descriptive confidence |
| `experiments/04_xforecast/` | The FinTexTS forecasting run the comparison came out of |
| `experiments/_shared/ts.py` | Client, thread-safe on-disk cache, cost helper |
| `scripts/fetch_data.py` | Pulls the third-party reference files from source |
| `docs/` | Source for the GitHub Pages write-up |

Numbering follows the working order. Experiments 01 to 03 were earlier attempts at the same
forecasting question on other datasets, reached the same conclusion, and are not published
here.

The `cache_*.json` files are committed on purpose. They hold the raw responses keyed by a hash
of the request, and they are what makes the numbers checkable offline.

## Licence

Code under MIT, see [LICENSE](LICENSE). The datasets are not redistributed and stay under
their own licences.
