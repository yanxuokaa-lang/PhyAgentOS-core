# Jev DSPy Lab

Reproducible calibration, confidence-gating, latency, and modeled-cost benchmarks
for [Jev / TypeSafe System One](https://docs.typesafe.ai/introduction) decisions
used in [DSPy](https://dspy.ai/) workflows.

This is **not** another DSPy fork. It is a companion measurement lab for
[`typesafeainate/dspy-typesafeify`](https://github.com/typesafeainate/dspy-typesafeify)
and other callers that use TypeSafe decisions inside DSPy-style pipelines.

## Why this exists

The existing `dspy-typesafeify` proof of concept is useful and its focused tests
pass, but its published benchmark:

- compares only three observed cases,
- requires both `OPENAI_API_KEY` and `TYPESAFE_API_KEY`,
- disables caching,
- reports latency and modeled cost but not dataset-level calibration,
- does not expose selective risk or a fail-closed abstention policy,
- cannot be reproduced offline from the repository.

This project fills those measurement gaps.

## Quick start

```bash
uv sync
uv run pytest -q
uv run jev-dspy-benchmark \
  --dataset fixtures/tickets.jsonl \
  --responses fixtures/typesafe_responses.jsonl \
  --output evidence/benchmark \
  --field owner \
  --threshold 0.7 \
  --bootstrap-samples 2000 \
  --seed 17
```

No API keys are required.

The benchmark writes:

- `evidence/benchmark/benchmark.json`: stable machine-readable report and gated decisions
- `evidence/benchmark/benchmark.md`: human-readable summary
- `evidence/benchmark/request_hashes.txt`: one canonical SHA-256 hash per request

The report also includes a deterministic exploratory threshold sweep from 0.0 through 1.0.
It shows how coverage, accuracy, and selective risk change across gates. The selected gate
remains the confirmatory result; do not pick the best sweep row from the same run and report
it as an independent evaluation.

## Current deterministic fixture result

The checked fixture is **synthetic**. It exercises the metric code and confidence
gate; it is not a claim about Jev model quality.

| Metric | Result |
| --- | ---: |
| Total decisions | 24 |
| Confidence gate | 0.700 |
| Answered | 18 |
| Abstained | 6 |
| Coverage | 75.0% |
| Accuracy among answered | 0.667 |
| Selective risk | 0.333 |
| Brier score | 0.4844 |
| Expected calibration error | 0.2083 |
| Latency p50 / p95 | 162.0 / 245.1 ms |
| TypeSafe input / output tokens | 21,852 / 519 |
| Average modeled cost | $0.000038 |

The latency and cost values are properties of the fixture, not observed TypeSafe
API performance. Replace the fixture with a recorded response set before drawing
model conclusions.

## Recorded live `jev-latest` result

This repository also contains a 24-case live recording from the `jev-latest`
alias. The response model reported by TypeSafe was `jev-1.13.0`. These cases are
synthetic support-ticket routing examples, so this is a recorded integration
benchmark—not a claim of general Jev model quality.

| Metric | Result |
| --- | ---: |
| Total decisions | 24 |
| Confidence gate | 0.700 |
| Answered | 23 |
| Abstained | 1 |
| Coverage | 95.8% |
| Accuracy among answered | 0.913 |
| Selective risk | 0.087 |
| Brier score | 0.1546 |
| Expected calibration error | 0.0583 |
| Latency p50 / p95 | 191.5 / 405.6 ms |
| TypeSafe input/output tokens | 11,101 / 1,328 |
| Average modeled cost | $0.000019 |

Evidence:

- [`evidence/live/jev-latest/benchmark.md`](evidence/live/jev-latest/benchmark.md)
- [`evidence/live/jev-latest-responses.jsonl`](evidence/live/jev-latest-responses.jsonl)

Every recording includes a model-aware request hash. Replaying the recording
through the offline CLI produces byte-identical JSON and Markdown reports.

## Metrics

- **Accuracy among answered:** correct answers divided by answers that passed the
  confidence gate.
- **Selective risk:** incorrect answers divided by answers that passed the gate.
- **Coverage:** answered decisions divided by all decisions.
- **Abstention rate:** gated-out decisions divided by all decisions.
- **Choice confidence:** probability assigned to the selected option.
- **Noul confidence:** probability that the answer is true.
- **Choice Brier score:** sum of squared differences between every class
  probability and its one-hot target.
- **Noul Brier score:** squared difference between true probability and the
  binary target.
- **Expected calibration error:** confidence-bucket weighted absolute difference
  between average confidence and bucket accuracy.
- **Bootstrap confidence intervals:** deterministic percentile intervals from
  resampled answered outcomes.
- **Threshold sensitivity:** coverage, accuracy, and selective risk at every 0.1 gate,
  plus the selected gate when it falls between grid points. Empty-answer gates use `null`
  rates rather than fabricating zero accuracy or risk.

Uncertain decisions are changed to `predicted: null` and `abstained: true`; the
benchmark never replaces an uncertain answer with a fabricated fallback.

## Record live decisions

First clone and install the audited DSPy integration as a sibling project:

```bash
git clone https://github.com/typesafeainate/dspy-typesafeify.git
uv pip install -e '../dspy-typesafeify[typesafe]'
```

Wrap the real TypeSafe client before passing it to `configure_typesafe`:

```python
from typesafe_sdk import TypeSafeClient
from typesafe_dspy import configure_typesafe
from jev_dspy_lab.replay import RecordingClient

recorder = RecordingClient(
    TypeSafeClient(api_key=os.environ["TYPESAFE_API_KEY"]),
    recording_path="recordings/typesafe_responses.jsonl",
)

configure_typesafe(
    client=recorder,
    model="speed_latest",
    # Keep the rest of your document builder and field configuration unchanged.
)
```

Run the DSPy predictor normally. `RecordingClient` returns the original SDK
response unchanged, records the canonical hash of its document, questions, and
selected model, serializes the response and measured latency, and skips duplicate
identical requests.

## Replay recorded decisions

```python
from jev_dspy_lab.replay import ReplayClient, load_replay_index

responses = load_replay_index("recordings/typesafe_responses.jsonl")
replay = ReplayClient(responses)
```

Pass `replay` to the same integration as the TypeSafe client. If a request is
missing, the client raises instead of fabricating a decision.

Do not commit recordings that contain private data. Synthetic fixtures are
preferred for CI.

To collect this repository’s live benchmark directly:

```bash
export TYPESAFE_API_KEY='your-key'
uv sync --group dev --group live
uv run --no-sync python scripts/run_live_benchmark.py \
  --dataset fixtures/tickets.jsonl \
  --responses evidence/live/jev-latest-responses.jsonl \
  --output evidence/live/jev-latest \
  --field owner \
  --threshold 0.7 \
  --bootstrap-samples 2000 \
  --seed 17 \
  --model jev-latest
```

The command first records each real TypeSafe response, then evaluates the
recording through the same offline replay path. It never writes the API key.

## Integrate with a DSPy signature

The upstream integration remains responsible for DSPy signature planning. This
lab stays independent of the full DSPy fork at runtime:

```python
from typing import Literal

import dspy
from typesafe_dspy import typesafeify


@typesafeify()
class TicketRouting(dspy.Signature):
    """Route a support ticket to its first-response owner."""

    ticket: dict = dspy.InputField()
    owner: Literal["api-platform", "billing", "checkout", "infra", "support-ops"] = (
        dspy.OutputField()
    )
```

Configure either `RecordingClient` for a live run or `ReplayClient` for a
reproducible offline run.

An optional sibling integration smoke check is available after installing the
audited integration:

```bash
uv pip install -e '../dspy-typesafeify[typesafe]'
uv run --no-sync python scripts/verify_integration.py
```

## Limitations

- The checked fixture is synthetic and intentionally includes miscalibration.
- Accuracy intervals are frequentist bootstrap intervals, not Bayesian posteriors.
- Selective risk is conditional on the chosen confidence threshold.
- Threshold sweeps are exploratory sensitivity checks and require independent confirmation
  before a post-hoc gate can be reported.
- Multiclass Brier scores sum over all class residuals and are not normalized by
  class count.
- Cost uses TypeSafe’s published [`$0.042 / 1M` input-token price](https://docs.typesafe.ai/models);
  output tokens are free.
- This project is independent and not affiliated with TypeSafe AI or DSPy.

## Development

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/build_fixtures.py --output-dir fixtures
```

## License

MIT. See [LICENSE](LICENSE).
