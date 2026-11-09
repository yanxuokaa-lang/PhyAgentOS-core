# TypeSafe AI Rust SDK (community)

[![crates.io](https://img.shields.io/crates/v/typesafeai-sdk-community.svg)](https://crates.io/crates/typesafeai-sdk-community)
[![docs.rs](https://img.shields.io/docsrs/typesafeai-sdk-community)](https://docs.rs/typesafeai-sdk-community)
[![CI](https://github.com/community-ports/typesafeai-sdk-rust-community/actions/workflows/ci.yml/badge.svg)](https://github.com/community-ports/typesafeai-sdk-rust-community/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A community-built Rust SDK for the [TypeSafe AI](https://typesafe.ai) API. It is a port of the
official [Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python) with the same
primitives, wire format, retry behavior, and error semantics, in idiomatic Rust.

TypeSafe's **System One** models (Jev is the flagship) return fast, typed judgments
(probabilities, selections, and scores) that your code can consume directly instead of
generated text. Learn what TypeSafe is and how to design questions in the
[TypeSafe docs](https://docs.typesafe.ai/).

On top of the official surface, the community edition adds what the docs tell you to build
yourself: derive macros that make Rust enums and structs the questions and answers
([Typed questions](#typed-questions)), typed function calling ([Routing](#routing)), weighted
scoring you can retune without new requests ([Composite scoring](#composite-scoring)), helpers
that turn probabilities into decisions ([Decisions](#decisions)), a mock transport with
generated fixtures for tests ([Testing](#testing)), concurrent batches with the reranking and
line-search cookbooks ([Batch, rerank, and find](#batch-rerank-and-find)), state path checks,
a response cache, and an evaluation harness for choosing thresholds on your own data
([Evaluation](#evaluation)).

This repository is one Cargo workspace that publishes two crates:

| Crate | What it is |
| --- | --- |
| [`typesafeai-sdk-community`](https://crates.io/crates/typesafeai-sdk-community) | The SDK: clients, questions, answers, retries, errors. The only crate you add. |
| [`typesafeai-sdk-community-macros`](https://crates.io/crates/typesafeai-sdk-community-macros) | The `ChoiceLabels`, `ScoreLevels`, `Questions`, `Route`, and `Composite` derive macros, in [`macros/`](macros). Proc macros must be their own crate; the SDK depends on it and re-exports the derives under the default `derive` feature. |

Both crates share one version and are released together.

> This is an independent community project and is not maintained by TypeSafe AI.

## Quickstart

```toml
[dependencies]
typesafeai-sdk-community = "0.5"
tokio = { version = "1", features = ["full"] }
```

Set `TYPESAFE_API_KEY` in your environment, then:

```rust
use typesafeai_sdk_community::{Choice, Noul, Score, TypeSafeClient, json};

#[tokio::main]
async fn main() -> typesafeai_sdk_community::Result<()> {
    let client = TypeSafeClient::new()?;

    let response = client
        .system_one(json!({"document": "I was charged twice. Please help."}))
        .question("billing", Noul::new("Is this message about billing?"))
        .question(
            "tone",
            Choice::new("What is the tone of this message?")
                .option("angry", "An upset or hostile message")
                .option("calm", "A neutral or polite message"),
        )
        .question("urgency", Score::new("How urgent is this?", ["Can wait", "This week", "Today"]))
        .send()
        .await?;

    let billing = response.noul("billing").unwrap();
    let tone = response.choice("tone").unwrap();
    let urgency = response.score("urgency").unwrap();
    println!("billing={:.2} tone={} ({:.2}) urgency={:.1}", billing.noul, tone.choice, tone.confidence, urgency.score);
    Ok(())
}
```

The crate is `typesafeai-sdk-community` and imports as `typesafeai_sdk_community`. The `-community`
suffix marks it as an independent port; it is not the official `typesafe-sdk` package name.

## Typed questions

This is where the community edition goes beyond the official SDKs. Enums can be the labels of
a choice or the rubric of a score, and a struct can be a whole question set, so a request and
its answers are checked by the compiler instead of matched on strings:

```rust
use typesafeai_sdk_community::{ChoiceLabels, NoulAnswer, Questions, ScoreLevels, TypeSafeClient, TypedChoice, TypedScore};

#[derive(Clone, Copy, Debug, PartialEq, Eq, ChoiceLabels)]
enum Team {
    #[choice(describe = "Charges, invoices, refunds")]
    Billing,
    #[choice(describe = "Errors or how-to questions")]
    Support,
    #[choice(describe = "None of the above clearly apply")]
    NoMatch,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, ScoreLevels)]
enum Urgency { #[score("Can wait")] Low, #[score("This week")] Medium, #[score("Today")] High }

#[derive(Debug, Questions)]
struct Triage {
    #[choice("Which team should handle `message`?")]
    team: TypedChoice<Team>,
    #[score("How urgent is `message`?")]
    urgency: TypedScore<Urgency>,
    #[noul("Does `message` ask for a refund?")]
    refund: NoulAnswer,
    #[noul("Is `message` written in a language other than English?")]
    non_english: bool,
}

let triage = client.ask::<Triage>(state).send().await?;   // one request, all fields
match triage.team.choice {                                 // exhaustive match on a real enum
    Team::Billing => { /* ... */ }
    Team::Support => { /* ... */ }
    Team::NoMatch => { /* ... */ }
}
let p_urgent = triage.urgency.probability_at_least(Urgency::Medium);
```

Field types choose what you get back: `NoulAnswer`, `bool`, or `f64` for a noul; `ChoiceAnswer`,
`TypedChoice<T>`, or a bare `T: ChoiceLabels` for a choice; `ScoreAnswer`, `TypedScore<T>`,
`T: ScoreLevels`, or `f64` for a score; `Answer` for the raw value; and `Option<...>` of any of
them to tolerate a missing answer. A `#[choice]` attribute on a noul-shaped field is a compile
error, as is a misspelled label. Instructions and descriptions accept any expression that is
`Into<Value>`, so `json!({...})` works anywhere a string does.

Attribute reference:

| Attribute | On | Arguments |
| --- | --- | --- |
| `#[choice(...)]` | enum | `rename_all = "snake_case"` (default; also lowercase, UPPERCASE, kebab-case, camelCase, PascalCase, SCREAMING_SNAKE_CASE, none) |
| `#[choice(...)]` | variant | `label = "..."`, `describe = <expr>` |
| `#[score(...)]` | variant | `"description"` or `describe = <expr>`; defaults to the humanized variant name |
| `#[noul(...)]` | field | `"instructions"`, `name = "..."`, `when_true = <expr>`, `when_false = <expr>` |
| `#[choice(...)]` | field | `"instructions"`, `name = "..."`, `labels = ["a", ("b", "description")]` for untyped fields |
| `#[score(...)]` | field | `"instructions"`, `name = "..."`, `levels = ["low", "high"]` for untyped fields |

`Choice::of::<Team>("...")` and `Score::of::<Urgency>("...")` build single questions from an enum,
`response.choice_as::<Team>("team")` and `response.parse::<Triage>()` type an untyped response,
and everything is available on the blocking client too.

The derives come from the `typesafeai-sdk-community-macros` crate and are re-exported, so
`use typesafeai_sdk_community::{ChoiceLabels, ScoreLevels, Questions}` is all you import. They
are behind the default `derive` feature; with `default-features = false` the traits in the
`typed` module can still be implemented by hand. The macros crate itself is not meant to be
depended on directly. If you rename this crate in your `Cargo.toml` (`package = ...`), tell
the derives where to find it with `#[choice(crate = "my_alias")]`, `#[score(crate = ...)]`, or
`#[questions(crate = ...)]`.

## Decisions

The `decision` module turns probabilities into actions the way the
[confidence docs](https://docs.typesafe.ai/confidence) describe, with thresholds you own:

```rust
use typesafeai_sdk_community::decision::{Bands, Decision, Gate, Outcome};

match triage.refund.decide_with(Bands::new(0.3, 0.7)) {
    Decision::Yes => refund(),
    Decision::No => {}
    Decision::Uncertain => ask_customer(),
}
match triage.team.gate(Gate::new(0.85, 0.6)) {
    Outcome::Accept => route(triage.team.choice),
    Outcome::Review => route_and_flag(triage.team.choice),
    Outcome::Reject => manual_triage(),
}
```

Also available: `margin()` (gap between the top two labels), `top(n)`, `entropy()` and
`normalized_entropy()` on choices; `probability_at_least(level)`, `std_dev()`, and
`normalized()` on scores; `certainty()` on nouls.

## Routing

`#[derive(Route)]` is typed function calling. One choice question selects a variant; every
variant's fields are questions too, sent in the same request (the docs' speculative fan-out).
Only the winning variant is constructed:

```rust
use typesafeai_sdk_community::{NoulAnswer, Route, TypeSafeClient};

#[derive(Debug, Route)]
#[route("What does the customer want from `message`?")]
enum Intent {
    #[route(describe = "Wants money back for a charge")]
    Refund {
        #[noul("Is the full amount requested?")]
        full_amount: bool,
    },
    #[route(describe = "Wants to cancel the subscription")]
    Cancel {
        #[noul("Is this a threat rather than a decision?")]
        threat: NoulAnswer,
    },
    #[route(describe = "None of the above clearly applies")]
    Other,
}

match client.route::<Intent>(state).send().await? {
    Intent::Refund { full_amount } => refund(full_amount),
    Intent::Cancel { threat } if threat.noul > 0.7 => retain(),
    Intent::Cancel { .. } => cancel(),
    Intent::Other => escalate(),
}
```

`send_full()` returns a `Routed<Intent>` with the routing `ChoiceAnswer` (confidence, margin,
every variant's probability) and the full response, so uncertain routes can be gated the same
way as any choice. Enum attributes: `#[route("instructions", name = "route",
rename_all = "snake_case")]`; variant attributes: `#[route(label = "...", describe = ...)]`.
Branch questions are named `<label>.<field>` on the wire unless a field sets `name`.

## Composite scoring

`#[derive(Composite)]` implements the docs'
[composite scoring](https://docs.typesafe.ai/patterns/composite-scoring) pattern: score each
dimension once, combine with weights that live in code, and reweight or re-threshold without
re-running inference.

```rust
use typesafeai_sdk_community::composite::{Composite as _, Weights};
use typesafeai_sdk_community::{Composite, NoulAnswer, Questions, TypedScore};

#[derive(Questions, Composite)]
struct ChurnRisk {
    #[noul("Does `message` express intent to leave?")]   #[weight(0.5)] leaving: NoulAnswer,
    #[noul("Does `message` mention a competitor?")]      #[weight(0.2)] competitor: NoulAnswer,
    #[score("How angry is the customer?")]               #[weight(0.3)] anger: TypedScore<Anger>,
}

let risk = client.ask::<ChurnRisk>(state).await?;
let score = risk.composite();                                       // 0..1 with declared weights
let score = risk.composite_with(&Weights::from([("leaving", 1.0)])); // from config, no new request
for part in risk.breakdown() { /* name, signal, weight, contribution */ }
```

Signals are 0..1: a noul's probability, a score's expected value over its top level, `bool`,
`f64` as-is, or one label's probability with `#[weight(0.2, label = Tone::Angry)]`; `invert`
flips a signal. Missing `Option` signals are dropped and the rest renormalized. `Weights` is
serde-serializable.

## Testing

Enable the `test-util` feature for a `MockTransport` that answers from scripted responses and
records every request, so tests run the real client (retries, decoding, typed parsing) with no
network:

```rust
use typesafeai_sdk_community::testing::{MockResponse, MockTransport};

let mock = MockTransport::new();
mock.enqueue(MockResponse::rate_limited(Duration::from_millis(10)))   // first attempt
    .enqueue(MockResponse::answers().noul("billing", 0.92).choice_typed("tone", Tone::Angry));
let client = mock.client();                                            // or builder().transport(mock.clone())

let triage = client.ask::<Triage>("...").await?;
assert_eq!(triage.tone.choice, Tone::Angry);
assert_eq!(mock.requests().len(), 2);
assert_eq!(mock.last_request().unwrap().model(), Some("jev-latest"));
```

Add `#[questions(mock)]` (or `mock` on `#[route(...)]`) and the derive also generates a typed
fixture builder, so tests never spell out JSON:

```rust
mock.enqueue(Triage::mock().billing(0.92).tone(Tone::Angry).urgency(Urgency::High));
mock.enqueue(Intent::mock().refund().refund_full_amount(1.0));
```

`Recorder` wraps any transport and captures exchanges into a `Cassette` (JSON, no credentials)
that `MockTransport::replay` plays back, for tests that should track real API behavior without
calling it every run. `Transport` is public, so the same seam takes your own HTTP stack.

## Batch, rerank, and find

The API batches questions, not states: judging 500 tickets is 500 requests. `batch` runs them
with bounded concurrency, keeps every result in input order as its own `Ok`/`Err`, and when any
request is rate limited it pauses all of them until `Retry-After` elapses instead of letting
eight tasks retry into the same limit:

```rust
let outcome = client.batch::<Triage>(tickets).concurrency(8).on_progress(|p| eprintln!("{}/{}", p.completed, p.total)).run().await;
for (index, triage) in outcome.ok() { /* results[index] belongs to tickets[index] */ }
println!("{} failed, {} input tokens", outcome.failed(), outcome.usage.input_tokens.unwrap_or(0));
```

Two cookbook patterns come built on it. `rerank` asks one relevance question per candidate and
sorts (yes/no by default, or a graded rubric with `.graded(..)`); `find` puts every item in a
single request and asks which one matches, the cheaper shape when the items are small:

```rust
let hits = client.rerank("How long does a refund take?", passages).top(5).run().await?;
let found = client.find("When can I cancel?", lines).run().await?;
if let Some(index) = found.best(0.5) { /* lines[index] */ }
```

## State path checks

Questions point at parts of the state with backticked paths like `` `ticket.messages[0].text` ``.
When a field is renamed, those references silently point at nothing. Turn on the check per
call with `.check_paths()` or for every request with `ClientBuilder::check_paths(true)`, and a
request whose questions reference a path the state does not contain fails with
`Error::StatePath` before anything is sent. The mock client enables it by default, so tests
catch it.

## Response cache

Same model, same state, same questions gives the same answer, so repeated requests can skip
the API:

```rust
use typesafeai_sdk_community::cache::Cache;

let client = TypeSafeClient::builder()
    .cache(Cache::in_memory(10_000).ttl(Duration::from_secs(3600)))
    .build()?;

client.ask::<Triage>(state).cache_scope("tenant-42").await?;   // scope adds a key dimension
client.ask::<Triage>(state).refresh().await?;                  // skip the read, store the result
client.ask::<Triage>(state).no_cache().await?;                 // bypass entirely
```

Keys hash the canonical request (model, state, questions) plus the scope; `Cache::key(..)`
replaces the key function and `CacheStore` is a trait for Redis, disk, or anything else. Hits
carry `meta.from_cache` and keep the original request ID; errors and model listings are never
cached; `cache.stats()` reports hits, misses, and stores.

## Evaluation

The docs say to validate judgments and pick thresholds on your own data. `evaluate` runs a
question set over labeled examples and reports how the answers line up:

```rust
use typesafeai_sdk_community::eval::Example;

let examples = rows.into_iter().map(|(text, is_spam)| Example::new(json!({"message": text}), is_spam));
let run = client.evaluate::<Spam, bool>(examples).concurrency(8).run().await;
let report = run.binary(|spam| spam.spam.noul);
println!("{report}");                                  // Brier, log loss, AUC, ECE, calibration table
let threshold = report.best_f1.threshold;              // or best_accuracy, or scan report.thresholds
```

`run.choice(..)` gives accuracy, per-label precision/recall/F1, a confusion matrix, confidence
calibration, and `suggest_gate(0.95)`: the confidence at which everything accepted automatically
is at least 95% accurate, as a `Gate`. `run.score(..)` gives MAE, RMSE, exact and within-one
agreement. The metric functions (`eval::binary`, `choice`, `score`) also work on predictions you
already have. Reports are `Display` and `Serialize`.

## Questions

| Need | Primitive | Answer |
| --- | --- | --- |
| Whether a condition holds | `Noul` | `NoulAnswer { noul: f64 }`, the probability of "yes" |
| One of a defined set | `Choice` | `ChoiceAnswer { choice, confidence, probabilities }` |
| Degree along an ordered rubric | `Score` | `ScoreAnswer { score, confidence, legend, probabilities }` |

Instructions and criteria accept plain strings or structured JSON via the re-exported `json!`
macro. `Question::Custom` sends an arbitrary JSON object verbatim for question types this SDK
does not model yet.

```rust
use typesafeai_sdk_community::{Choice, Noul, Score, json};

let spam = Noul::new("Is this message spam?")
    .when_true("Unsolicited advertising")
    .when_false("A legitimate conversation");

let tone = Choice::new("What is the tone?").labels(["angry", "calm", "excited"]);

let urgency = Score::new(json!({"task": "How urgent is `message`?"}), ["Can wait", "This week", "Today"]);
```

## Responses

`SystemOneResponse` exposes `model`, `usage`, all `answers` keyed by question name, and typed
accessors: `noul(name)`, `choice(name)`, `score(name)`, plus `nouls()`, `choices()`, and
`scores()` iterators. `request_id()` returns the `x-typesafe-request-id` header and `meta` holds
the HTTP status and headers.

For a custom shape, decode the body into your own `serde` types with `send_as::<T>()`, or get
the undecoded bytes with `send_raw()`:

```rust
#[derive(serde::Deserialize)]
struct Answers { billing: typesafeai_sdk_community::NoulAnswer }
#[derive(serde::Deserialize)]
struct Mine { model: String, answers: Answers }

let mine: Mine = client.system_one("...").question("billing", Noul::new("Billing?")).send_as().await?;
```

## Configuration

| Option | Builder method | Environment variable | Default |
| --- | --- | --- | --- |
| API key | `api_key` | `TYPESAFE_API_KEY` | required |
| Base URL | `base_url` | `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` |
| Model | `model` | `TYPESAFE_DEFAULT_MODEL` | `jev-latest` |
| Timeout | `timeout` | none | 10 seconds |
| Retries | `retry` | none | see below |
| Headers | `header` / `headers` | none | none |
| HTTP client | `http_client` | none | a default `reqwest::Client` |

Explicit options win over environment variables; empty or whitespace-only environment values
are ignored. Every option except the API key can also be overridden per call on the request
builder (`.model(..)`, `.timeout(..)`, `.retry(..)`, `.header(..)`, `.extra_body(..)`).

```rust
use std::time::Duration;
use typesafeai_sdk_community::{RetryPolicy, TypeSafeClient};

let client = TypeSafeClient::builder()
    .api_key("sk-...")
    .model("jev-latest")
    .timeout(Duration::from_secs(20))
    .retry(RetryPolicy::default().max_retries(3))
    .header("x-team", "billing")
    .build()?;
```

## Retries

Requests are retried on connection errors, timeouts, and `408`, `429`, and `5xx` responses:
two retries after the initial attempt, exponential backoff from 0.5s to 5s with 25% jitter,
`Retry-After` / `retry-after-ms` honored, and a 30 second total budget per call. Retried
attempts carry an `X-TypeSafe-Retry-Count` header. Tune or disable this with `RetryPolicy`:

```rust
use typesafeai_sdk_community::{Error, RetryPolicy};

let policy = RetryPolicy::default()
    .max_retries(5)
    .http_statuses([429, 502, 503, 504])
    .timeout(None)
    .predicate(|error| matches!(error, Error::Api(api) if api.message().contains("overloaded")));

let none = RetryPolicy::none();
```

## Errors

Every operation returns `typesafeai_sdk_community::Result<T>`; the error is one enum:

| Variant | Meaning |
| --- | --- |
| `Error::Config` | Missing API key, invalid timeout, retry policy, or header |
| `Error::InvalidRequest` | No questions, an empty score rubric, or an unencodable body |
| `Error::Api(ApiError)` | Unsuccessful HTTP status after retries; `kind()` classifies it (`BadRequest`, `Authentication`, `PermissionDenied`, `NotFound`, `UnprocessableEntity`, `RateLimit`, `InternalServer`, `Other`), and `retry_after()`, `request_id()`, `body()`, `headers()` expose the details |
| `Error::ResponseValidation` | A `2xx` body missing required data; `field_path()` names the offending field, e.g. `answers.tone.confidence` |
| `Error::Connection` | The request never got an HTTP response |
| `Error::Timeout` | The request exceeded its timeout |

```rust
match client.system_one("...").question("q", Noul::new("?")).send().await {
    Ok(response) => { /* ... */ }
    Err(Error::Api(api)) if api.kind() == ApiErrorKind::RateLimit => {
        eprintln!("rate limited; retry after {:?}", api.retry_after());
    }
    Err(error) => eprintln!("request failed: {error}"),
}
```

## Blocking client

Enable the `blocking` feature for a synchronous client with the same API:

```toml
typesafeai-sdk-community = { version = "0.5", features = ["blocking"] }
```

```rust
use typesafeai_sdk_community::blocking::TypeSafeClient;
use typesafeai_sdk_community::Noul;

let client = TypeSafeClient::new()?;
let response = client.system_one("...").question("billing", Noul::new("Billing?")).send()?;
```

Like `reqwest::blocking`, it must not be used from inside an async runtime.

## Logging

The SDK emits `tracing` events under the `typesafeai_sdk_community` target: an `INFO` line per response
and retry, and `DEBUG` lines with headers and bodies. Credential-bearing headers are redacted;
bodies are not. Install any subscriber to see them, for example:

```sh
RUST_LOG=typesafeai_sdk_community=debug cargo run --example models
```

## Feature flags

| Feature | Default | Effect |
| --- | --- | --- |
| `derive` | yes | The `ChoiceLabels`, `ScoreLevels`, `Questions`, `Route`, and `Composite` derive macros (pulls in `typesafeai-sdk-community-macros`) |
| `rustls` | yes | TLS via rustls with the platform certificate verifier |
| `native-tls` | no | TLS via the operating system's TLS library |
| `blocking` | no | The synchronous `blocking::TypeSafeClient` |
| `test-util` | no | The `testing` module: `MockTransport`, scripted responses, fixture builders, record/replay |

## Development

```
Cargo.toml        typesafeai-sdk-community (the SDK)
src/              client, transport, questions, responses, retry, errors, typed, decision, composite,
                  batch, state, cache, eval, testing
macros/           typesafeai-sdk-community-macros (the derive macros)
tests/            offline tests against a scripted mock server; live.rs self-skips without a key
examples/         basic, typed, route, batch, models, blocking
```

Every command below runs across both crates:

```sh
cargo test --workspace --all-features   # offline; live tests self-skip without TYPESAFE_API_KEY
TYPESAFE_API_KEY=... cargo test --all-features --test live
cargo clippy --workspace --all-features --all-targets -- -D warnings
cargo fmt --all
cargo run --example typed
```

Minimum supported Rust version: 1.88.

## Related

- [TypeSafe docs](https://docs.typesafe.ai/): concepts, primitives, cookbooks, HTTP API
- [typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python): the official Python SDK this crate mirrors

## License

MIT. See [LICENSE](LICENSE).
