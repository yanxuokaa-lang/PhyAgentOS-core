# ts-jev-cost-calculator

Estimate, **before you send a request**, how many input and output tokens a TypeSafe System One / Jev API call will use, what it will cost in USD, and whether it fits the context limits. After the call, read the **real** cost from the API response with one command.

- Two identical commands: `ts-jev-cost-calculator` and the short alias `tscost`.
- A one-line Python API: `estimate(request).cost_usd`.
- Self-contained and offline: no API key, no network call, nothing is sent anywhere.
- Median input-token error below 1%, aggregate cost error below 0.5% (see [Accuracy](#accuracy)).

> **Independent project.** This tool is not affiliated with, endorsed by, sponsored by, or otherwise connected to TypeSafe or the makers of the Jev model. See [Disclaimer](#disclaimer-and-trademarks).

## Install

Python 3.9 or newer. One command, nothing to configure:

```bash
git clone https://github.com/StefanoITA/ts-jev-cost-calculator.git
sh ts-jev-cost-calculator/install.sh          # picks uv, pipx or pip automatically
```

Or with the tool you already use:

```bash
uv tool install ./ts-jev-cost-calculator      # uv (isolated, on PATH)
pipx install ./ts-jev-cost-calculator         # pipx (isolated, on PATH)
pip install ./ts-jev-cost-calculator          # inside a virtualenv
```

The only dependency, `tokenizers`, ships prebuilt wheels for Linux, macOS and Windows. The package bundles the fitted model and the proxy tokenizer (about 7 MB), so it works offline and on servers without internet access. To deploy on a server, copy the folder (or a wheel built with `uv build`) and run the same command. Check the installation with `tscost info`.

## Command line

```bash
tscost estimate request.json                 # full request {state, model, questions}, or a bare questions map
tscost estimate - < request.json             # from stdin
tscost estimate request.json --calls 100000  # project the cost over a volume
tscost estimate request.json --json          # machine-readable output
tscost estimate request.json -q              # prints only: input_tokens output_tokens cost_usd
tscost estimate request.json --conservative  # adds the 90th-percentile error as a safety margin
tscost estimate request.json --price 0.05    # use a different price per million input tokens
tscost text "Any text at all"                # estimated tokens of a text (or - for stdin)
tscost usage response.json                   # real cost from an API response (reads usage.input_tokens)
tscost info                                  # active mode, price, limits
```

Example:

```
$ tscost estimate request.json --calls 100000
input_tokens   ~      505   (base 259 + state 67 + 3 questions 187)
output_tokens  ~       72   (free)
cost           ~ $0.0000212 per call   -> $2.1192 for 100000 calls
mode           proxy   (expected error: median 0.7%, p90 2.4%)
rate limit     up to 1200 calls/min (documented limits; your account may differ)
```

Exit codes: `0` ok, `2` the request exceeds a context limit (a warning names which one), `1` invalid input.

## Try it in one minute

The `examples/` folder has a complete request (`request.json`, a fictional customer message), the response the API returned for it (`response.json`, recorded on 2026-09-17) and a small script that runs the whole cycle offline:

```bash
tscost estimate examples/request.json --calls 100000   # estimate before sending
tscost usage examples/response.json                    # real cost from the recorded response
python examples/quickstart.py                          # same thing from Python, prints the estimate error
```

## Python

```python
from ts_jev_cost_calculator import estimate, count_tokens, actual_cost

e = estimate({"state": state, "model": "jev-latest", "questions": questions})
e.input_tokens        # estimated input tokens (billed)
e.output_tokens       # estimated output tokens (free)
e.cost_usd            # estimated cost of one call
e.ok                  # False when a context limit would be exceeded
e.cost_for(100_000)   # projection over a volume
e.max_calls_per_minute()
e.to_dict()           # everything above, for logs or JSON

count_tokens("any text")                       # estimated tokens of a text
actual_cost(response_json)["cost_usd"]         # real cost from an API response
estimate(request, conservative=True)           # adds the 90th-percentile error as a margin
estimate(request, price_usd_per_mtok=0.05)     # different price
```

`estimate()` accepts either a full request or the bare `questions` map used in the TypeSafe Playground.

## Accuracy

Measured against 751 real API responses (recorded on 2026-09-17, model `jev-1.13.0`), spanning 270 to 65,000 input tokens, 1 to 100 questions per request, all question types, plain-text and structured states, English and Italian text, and a wide range of request shapes. Error is |estimate − real| / real. These tables describe the accuracy of this estimator, not the performance of the service. The fitting set overlaps with this evaluation set; the cross-validated figures (median 0.7%, p90 2.4%) are the "expected error" that `tscost estimate` prints, and are within 0.2 points of the numbers below.

### By mode

| Mode | Requirement | Input tokens: median | p90 | max | Aggregate cost error | Output tokens: median | p90 |
|---|---|---|---|---|---|---|---|
| **proxy** (default) | `tokenizers` importable | **0.87%** | **2.53%** | 5.64% | **+0.36%** | 1.92% | 5.88% |
| features (fallback) | none | 1.88% | 6.62% | 22.6% | +0.76% | 3.17% | 7.61% |

Aggregate cost error is the error on the total cost of all 751 requests, which is what matters for a budget: individual errors partly cancel out.

### By request size (proxy mode)

| Real input tokens | Requests | Median | p90 | Max | Aggregate cost error |
|---|---|---|---|---|---|
| < 500 | 294 | 0.63% | 1.73% | 4.03% | −0.63% |
| 500 – 1,000 | 95 | 1.14% | 3.35% | 5.64% | −0.83% |
| 1,000 – 2,500 | 106 | 1.18% | 2.86% | 5.21% | −0.28% |
| 2,500 – 5,000 | 83 | 1.05% | 3.05% | 5.64% | +0.22% |
| 5,000 – 10,000 | 63 | 1.26% | 2.78% | 4.37% | +0.61% |
| 10,000 – 65,000 | 110 | 0.78% | 2.81% | 5.20% | +0.43% |

### By number of questions (proxy mode)

| Questions per request | Requests | Median | p90 | Max |
|---|---|---|---|---|
| 1 | 281 | 0.63% | 2.40% | 5.64% |
| 2 – 4 | 180 | 0.94% | 2.45% | 5.20% |
| 5 – 10 | 123 | 1.02% | 3.18% | 4.69% |
| 11 – 25 | 110 | 1.03% | 2.38% | 3.72% |
| 26 – 50 | 43 | 0.76% | 2.15% | 3.85% |
| 51 – 100 | 14 | 0.57% | 3.17% | 3.98% |

### By question types and state type (proxy mode)

| Subset | Requests | Input median | Input p90 | Output median | Output p90 |
|---|---|---|---|---|---|
| noul only | 225 | 0.69% | 2.77% | 4.55% | 7.69% |
| choice only | 92 | 1.11% | 2.98% | 3.89% | 6.98% |
| score only | 58 | 0.47% | 2.53% | 5.88% | 18.2% |
| mixed types | 376 | 0.85% | 2.35% | 1.40% | 4.80% |
| plain-text state | 384 | 0.89% | 2.69% | 4.25% | 5.88% |
| structured (JSON) state | 367 | 0.86% | 2.40% | 1.24% | 6.58% |

Output tokens are free on the current price list, so their error does not affect cost; they matter only for rate-limit and latency planning. For an expensive batch, run one real call first and compare with `tscost usage`.

## Tests

General offline tests (no API key, no network) cover the Python API, the command line, the limits and the example files:

```bash
pip install pytest && pytest
```

Nothing runs automatically in this repository: no CI, no hooks, no background jobs.

## How it works

The calculator is a purely statistical model of the token counts that the API itself reports in the `usage` field of its responses; it uses no knowledge of the service's internals. It serializes the request into a text form that, empirically, tracks the reported counts best (the state as-is or as indented JSON, each question as indented JSON), counts tokens with a bundled open-source proxy tokenizer (Qwen 2.5, Apache-2.0), and applies a linear correction fitted on 1,364 measured requests: a fitted per-request base offset of about 259 tokens plus coefficients for the character features on which the proxy and the reported counts differ (digits, uppercase, non-ASCII text, long words, structure counts). Output tokens follow a second linear model on the number and kind of questions, options and levels. Everything is derived from the requests the author sent and the `usage` counts the API returned for them.

If `tokenizers` cannot be imported, the tool falls back to a dependency-free regression on character features (the "features" row above) and says so in `tscost info`.

Known limits:

- Calibrated on `jev-1.13.0` with the list price published on the provider's public documentation on 2026-09-17 ($0.042 per million input tokens, output free). A new model version or price changes the numbers; the price can be overridden with `--price`, the model needs a refit.
- Non-Latin scripts, code, and highly repetitive text were not part of the calibration and may fall outside the stated error band.
- The context thresholds at which the tool warns (32,768 tokens for state plus the longest question; 65,536 in total) reflect the request budget described in the public documentation at the time of writing. Check the official documentation for current limits.

## Disclaimer and trademarks

This is an independent, community-made, open-source tool. It is **not** affiliated with, endorsed by, sponsored by, or in any way officially connected to TypeSafe, the TypeSafe AI service, the Jev model, or any of their owners, subsidiaries or affiliates. "TypeSafe", "Jev", "System One" and any related names, logos and marks are trademarks or registered trademarks of their respective owners, are used here solely to identify the service the tool works with (nominative use), and no trademark rights are claimed. The project name is descriptive; it does not imply endorsement.

All figures in this tool are **estimates** derived from the author's own measurements of public API responses. They are not official pricing, billing or quota information. The only authoritative source for what you are charged is your provider's invoice and the `usage` field in your own responses. Prices, limits and tokenization can change at any time without notice; the author has no control over them and no obligation to update this tool.

Using this tool does not change or replace the terms you have accepted with your provider; every user remains solely responsible for their own compliance with those terms. The tool provides no access to the service and contains no credentials. The software is provided "as is", without warranty of any kind, and the author accepts no liability for any decision, cost or loss arising from its use. The author will promptly rename the project or remove content at the request of a rights holder. See [DISCLAIMER.md](DISCLAIMER.md) and [LICENSE](LICENSE).

## Issues, contributions, security

Bug reports and questions are welcome through the issue templates. Please never paste API keys, real customer data or the pricing terms of your own contract, and keep in mind that this project cannot answer questions about the service itself. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md); rights holders will find a takedown section in [DISCLAIMER.md](DISCLAIMER.md).

## License

MIT License, see [LICENSE](LICENSE). Third-party components: the bundled proxy tokenizer is the tokenizer of Qwen/Qwen2.5-7B (Alibaba Cloud), Apache License 2.0; see [NOTICE](NOTICE). No code or data from TypeSafe is included; the fitted coefficients are the author's own work.
