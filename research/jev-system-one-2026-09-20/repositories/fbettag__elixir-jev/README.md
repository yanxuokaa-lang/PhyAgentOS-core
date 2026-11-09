# Jev for Elixir

[![CI](https://github.com/fbettag/elixir-jev/actions/workflows/ci.yml/badge.svg)](https://github.com/fbettag/elixir-jev/actions/workflows/ci.yml)

Typed semantic judgments and pattern matching, backed by TypeSafe's hosted Jev
or a persistent local Laya model. Version 0.2 adds bounded execution, offline
model preparation, strict validation, and replay. Not yet published to Hex.

```elixir
import Jev.DSL

semantic_case message, min_probability: 0.85 do
  option(:refund, "A request to return money", decision) ->
    Refunds.start_review(message, decision)

  option(:support, "A request for technical help") ->
    Support.route(message)

  option(:other, "Anything else") ->
    Inbox.store(message)

  uncertain(decision) ->
    Review.enqueue(message, decision)

  failed(error) ->
    {:retry, error.code}
end
```

The macro collects descriptions into **one Choice request** and runs only the
selected body. It performs no inference at compile time or inside Elixir guards.
At least two distinct labels, one `uncertain` branch, and one `failed` branch are
required. `option/3` binds the complete decision; `option/2` discards it. Labels
must be literal strings or atoms. Use `instructions: "..."` to override the
default selection instruction. `use Jev` also imports the macro.

## Try it

Requires Elixir 1.16+ and OTP supported by your Elixir installation. On Nix:

```sh
nix-shell
mix deps.get
mix test
mix run examples/semantic_case.exs
mix run examples/triage.exs mock
```

Add the GitHub dependency to your Mix project:

```elixir
{:jev, github: "fbettag/elixir-jev", branch: "main"}
```

Commit your `mix.lock` to pin the resolved revision. For local development, use:

```elixir
{:jev, path: "../elixir-jev"}
```

## Ordinary pattern matching

The function API is independent of the macro:

```elixir
question = Jev.choice("What does the customer need?",
  refund: "Return money for a purchase",
  support: "Help fixing a problem",
  other: "Something else"
)

case Jev.decide(message, question, min_probability: 0.85) do
  {:ok, :refund, decision} -> {:refund_review, decision}
  {:ok, label, decision} -> {:route, label, decision}
  {:uncertain, decision} -> {:human_review, decision}
  {:error, error} -> {:retry, error.code}
end
```

`decide/3` defaults to `min_probability: 0.8`. The threshold applies to the
selected label's probability, or the winning yes/no probability for Noul.
A separate `min_confidence` option applies only to Choice. Thresholds need
evaluation on your own examples; these defaults do not guarantee correctness.

Tied choices and a Noul of exactly 0.5 are always uncertain. A confident `:other`
is an ordinary successful result, distinct from uncertainty and provider failure.
No retry, cloud fallback, or action execution happens automatically.

## Batch questions and match across answers

```elixir
questions = [
  intent: Jev.choice("Which team should handle this?",
    billing: "Invoices and payments",
    technical: "Bugs and outages",
    other: "Anything else"
  ),
  urgent: Jev.noul("Does the customer describe a blocking problem?"),
  frustration: Jev.score("How frustrated is the customer?",
    ["Calm", "Frustrated", "Very angry"]
  )
]

case Jev.evaluate(%{message: message}, questions) do
  {:ok, %{answers: %{
    intent: %Jev.Answer.Choice{value: :billing, probability: p},
    urgent: %Jev.Answer.Noul{yes_probability: urgency}
  }}} when p >= 0.85 and urgency >= 0.9 ->
    :priority_billing

  {:ok, response} ->
    {:review, response}

  {:error, error} ->
    {:retry, error.code}
end
```

Questions in a batch are independent; a question cannot consume another
question's answer. Dependent stages require separate calls.

| Answer | Fields |
| --- | --- |
| `Jev.Answer.Choice` | `value`, `probability`, `probabilities`, `confidence`, `raw` |
| `Jev.Answer.Noul` | `value` (boolean), `probability` (winning side), `yes_probability`, `raw` |
| `Jev.Answer.Score` | `value` (expected level), `probabilities`, `legend`, `confidence`, `raw` |

Scores use zero-based levels and can lie between them. Use `evaluate/3` and
ordinary numeric guards for Scores; `decide/3` supports Choice and Noul.
Score distribution/legend keys remain strings, as in the upstream JSON API.

Question IDs and Choice labels preserve the atoms or strings you supplied.
Response strings are mapped only to those predefined labels, never converted to
new atoms. Invalid labels, missing or unexpected answers, wrong types, invalid
probabilities, and mismatched Score legends return `:invalid_response`.
Small distribution-sum differences from Laya's four-decimal rounding are accepted.

`Jev.Response` retains `model`, `provider`, `usage`, extra provider `metadata`,
the JSON `request`, and `raw` response. `Jev.Decision` retains that response, the
selected answer, and the applied policy. Laya's extra Noul confidence is kept in
`raw`; it is not treated as TypeSafe's Choice/Score confidence statistic.

## TypeSafe

The default adapter calls `POST https://api.typesafe.ai/v1/systemone` using
`jev-1.13.0` by default. Supply a secret through `TYPESAFE_API_KEY` or
`TYPESAFE_API_KEY_FILE`. Both are read at request time. Do not put keys in source.

```sh
mix run examples/triage.exs typesafe
```

```elixir
Jev.decide(message, question,
  provider: {Jev.Providers.TypeSafe, max_retries: 2},
  timeout: 30_000,
  model: "jev-1.13.0"
)
```

Adapter options: `api_key`, `api_key_file`, `url`, `connect_timeout` (10 seconds),
and `receive_timeout` (60 seconds), `max_response_bytes` (4 MiB), and
`max_retries` (zero by default, at most five). `plug` supports `Req.Test` in tests.
An explicit key takes precedence over the environment; otherwise environment
keys precede a configured key file. Use a fixed upstream model version when
model stability matters.

HTTP 401/403 becomes `:authentication`, 429/529 becomes `:rate_limited` with
`details.retry_after`, other unsuccessful statuses become `:http`. Transport
timeouts are `:timeout`; connection failures are `:transport`. Redirects are
disabled. Opt-in retries cover HTTP 429, 500, 502, 503, 504, and 529, respect
`Retry-After`, and share the total deadline. Transport timeouts are never retried
automatically. Retried requests may incur additional usage. Provider error bodies
are excluded; oversized bodies return `:response_limit`.

## Local Laya

Install the hashed Python 3.13 dependencies and prepare a model **before deployment**.
TypeSafe-only applications do not need Python or weights:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r priv/requirements-laya.lock
mkdir -p .jev-models
.venv/bin/python priv/prepare_laya.py --model multilingual --output .jev-models/multilingual
mix run examples/triage.exs laya
```

Preparation pins the Hugging Face revision, copies the checkpoint into a new
bundle, and writes its SHA-256 manifest. Add `--offline` to prepare from an
already cached snapshot. Existing bundles are never overwritten. Available
checkpoints are `english`, `multilingual`, and `typed-decisions`. Review the
upstream model license before distributing weights.

Put the worker under your application supervisor:

```elixir
children = [
  {Jev.Laya.Worker,
   name: MyApp.Laya,
   python: "/absolute/path/to/venv/bin/python",
   model_dir: "/absolute/path/to/models/multilingual",
   device: "cpu",
   startup_timeout: 60_000}
]

Supervisor.start_link(children, strategy: :one_for_one)

Jev.decide(message, question,
  provider: {Jev.Providers.Laya, worker: MyApp.Laya},
  timeout: 5_000
)
```

Startup verifies the manifest, loads the fixed checkpoint with Hugging Face
networking disabled, and performs real warm-up inference before reporting ready.
`Jev.Laya.Worker.status(MyApp.Laya)` reads readiness without waiting behind
inference. Include worker startup time in your application's deployment budget.
Model loading or warm-up failure prevents successful startup.

Each worker serves one checkpoint with one admission slot. Concurrent requests
return `:busy` before inference mailbox dispatch. Requests exceeding the model's
instruction, option, or state token budgets return `:context_limit`, avoiding
silent truncation. Use multiple named workers if your application needs several
models; no model router or inference pool is started globally.

The effective request records the model and revision. An explicit `model:` must
match the worker. Optional top-level `lang:` is a provenance annotation; it does
not select a different checkpoint. Choose `multilingual` for mixed-language input.
The example accepts `LAYA_PYTHON` and `LAYA_MODEL_DIR` environment variables.

A timeout or caller exit closes the Port and stops the worker. Its permanent
supervisor child restarts and warms it again. The Python reader observes Port EOF
even during inference. Address supervised workers by registered name across
restarts. Unexpected exits return `:worker_exit`; absent workers return
`:worker_unavailable`. Python stdout is reserved for framed JSON; logs use stderr.

Laya runs its own weights, not Jev's. Interface compatibility does not imply equal
accuracy, confidence calibration, or context capacity. Evaluate representative
examples before relying on thresholds. This library does not implement native Nx
inference.

## Execution limits

Every evaluation has a total `timeout:` of 60 seconds by default. Provider
preparation, dispatch, HTTP retries, inference, and decoding consume that budget.
Caller cancellation stops its provider task. The application allows at most 64
concurrent provider tasks; configure the cap before application startup:

```elixir
config :jev, :max_concurrency, 32
```

Overload returns `:busy`. There is no inference backlog. Default request limits
are `max_request_bytes: 1_048_576`, `max_questions: 64`, and `max_options: 128` per
question. JSON is normalized before dispatch, and colliding atom/string keys are
rejected. Unknown core options and invalid question declarations raise;
request limits and provider failures return `%Jev.Error{}`.

Custom `Jev.Provider` implementations can implement optional `prepare/2` to
resolve defaults captured in recordings. Callbacks run in isolated supervised
tasks and must not rely on the caller's process identity. Provider exceptions are
sanitized into `:provider_exception` without exposing exception messages.

## Recording and replay

```elixir
{:ok, response} = Jev.evaluate(message, questions)
:ok = Jev.Recording.write(response, "decision.json")

Jev.evaluate(message, questions,
  provider: {Jev.Providers.Replay, path: "decision.json"}
)
```

You may also pass a `Jev.Decision` to `write/2`. Recording is explicit and refuses
to overwrite existing files. Files use mode `0600` and a 16 MiB size limit.
Recordings include input content and answers, so protect their storage. Provider
configuration and credentials are excluded. Replay restores recorded defaults and
requires an exact effective request match, including model, revision, language,
state, and question definitions, then validates the response through the decoder.
It makes no model calls. You can change thresholds when replaying `decide/3`.

## Tests and observability

```elixir
provider = {Jev.Providers.Mock, handler: fn request ->
  # Return the upstream JSON shape, with string keys.
  {:ok, fixture_for(request)}
end}
```

Mock also accepts `response: raw_response` or `error: %Jev.Error{...}`. There is
no shared mock state, so concurrent ExUnit tests remain isolated. The test suite
uses Req.Test for HTTP and the actual Python Port protocol with a tiny fake model.
It requires `python3` but does not download models or make external API calls.

Telemetry events `[:jev, :evaluate, :start]`, `:stop`, and `:exception` expose
provider and question count. Stop events include duration in native time units,
status, and either model/usage or an error code. `[:jev, :decision]` counts
accepted and uncertain decisions. `[:jev, :retry]` reports attempts and delay in
milliseconds. `[:jev, :laya, :ready]` and `[:jev, :laya, :stopped]` include checkpoint
identity. Normal metadata excludes state, answers, credentials, and raw responses.
Avoid putting sensitive data in telemetry handlers or custom provider logs.

```sh
mix format --check-formatted
mix compile --warnings-as-errors
mix test --warnings-as-errors
python3 -m unittest discover -s test -p 'test_*.py'
mix dialyzer
mix docs --warnings-as-errors
mix run scripts/package_smoke.exs
```

The package smoke test builds a Hex package from the publication whitelist,
extracts it, and compiles and runs a fresh production consumer. It checks that
Python runtime files and the license are present and weights, virtual
environments, and tests are excluded. This validates packaging without publishing
to Hex.

GitHub Actions defines Linux and macOS checks, including Elixir 1.16/OTP 26 and
Elixir 1.18/OTP 28. See the [latest CI runs](https://github.com/fbettag/elixir-jev/actions).
For a production rollout, also measure accuracy and abstention on your own labeled
data, run a sustained load test on deployment hardware, and start with shadow
traffic. Synthetic fault tests and live smoke calls do not establish those results.
See [CHANGELOG.md](CHANGELOG.md) for the 0.1 migration changes.

## License

[MIT](https://github.com/fbettag/elixir-jev/blob/main/LICENSE), matching [Aquila](https://github.com/fbettag/aquila).
Model weights and third-party dependencies retain their own licenses.

References: [TypeSafe API](https://docs.typesafe.ai/api),
[confidence semantics](https://docs.typesafe.ai/confidence),
[Laya](https://github.com/NandhaKishorM/laya),
and the [Probably language inspiration](https://probably-lang.southpolesteve.workers.dev/).
