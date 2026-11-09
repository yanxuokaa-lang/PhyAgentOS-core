# kunobi-jev

[![Crates.io](https://img.shields.io/crates/v/kunobi-jev.svg)](https://crates.io/crates/kunobi-jev)
[![Docs.rs](https://img.shields.io/docsrs/kunobi-jev)](https://docs.rs/kunobi-jev)
[![CI](https://github.com/kunobi-ninja/kunobi-jev/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kunobi-ninja/kunobi-jev/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![MSRV](https://img.shields.io/badge/MSRV-1.94-blue.svg)](Cargo.toml)

Rust client for the [TypeSafe](https://docs.typesafe.ai) System One API. You send
state and typed questions to Jev, TypeSafe's decision model, and get answers your
code can act on: a label, a score or a probability, each with the numbers behind it.

Jev has three question types:

| Builder | Asks | Answer |
| --- | --- | --- |
| `noul` | a yes/no question | `noul`: probability of yes |
| `choice` / `choice_labels` | which label fits | `choice`, `confidence`, `probabilities` per label |
| `score` | where it falls on ordered levels | expected `score`, `confidence`, `legend`, `probabilities` |

A Choice takes up to 255 options and a Score between 2 and 10 levels; the client
refuses more before sending. `ScoreAnswer::normalized()` puts a score on 0 to 1 so
rubrics of different lengths can be combined, and `ranked()` orders a choice's
probabilities most likely first.

All questions in one call are answered against the same state in a single request,
and that is the cheap way to use it: the state is charged once however many questions
ride along. Measured against the live API, a 24k-token state with one question costs
24,288 input tokens and the same state with 200 questions costs 26,676, while latency
stays flat. Asking one question per call re-sends the state every time.

This is an unofficial client, maintained by Kunobi. It is not affiliated with TypeSafe.

## Install

```toml
kunobi-jev = "0.2"
```

Calls run on Tokio.

| Feature | Default | What it does |
| --- | --- | --- |
| `rustls` | yes | TLS through rustls |
| `blocking` | no | `blocking::Client`, for callers with no async runtime |
| `native-tls` | no | TLS through the platform library (OpenSSL, Secure Transport, SChannel) |
| `testing` | no | `testing::FakeSystemOne`, a scripted client for tests |

To use the platform TLS library instead of rustls:

```toml
kunobi-jev = { version = "0.2", default-features = false, features = ["native-tls"] }
```

## Quick start

Set `TYPESAFE_API_KEY`, then:

```rust
use kunobi_jev::{Client, Entry, Questions, SystemOneRequest, choice, noul, score};
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = Client::new()?;

    let mut questions = Questions::new();
    let department = questions.add(
        "department",
        choice("Which team should handle this?", [
            ("billing", "Payment or subscription issues"),
            ("technical", "Bugs or integration problems"),
            ("sales", "Pricing or account questions"),
        ]),
    );
    let frustration = questions.add(
        "frustration",
        score("How frustrated is the customer?", ["calm", "frustrated but civil", "very angry"]),
    );
    let urgent = questions.add("urgent", noul("Does the message convey urgency?"));

    let ticket = Entry::try_from(json!({
        "subject": "Stripe connection failing",
        "body": "It keeps failing for 3 days and I'm losing sales. Please help ASAP."
    }))?;
    let result = client.system_one(SystemOneRequest::new(ticket, questions)).await?;

    let department = result.answer(&department)?;
    if department.confidence >= 0.5 {
        println!("route to {}", department.choice);
    } else {
        println!("send to a human: {:?}", department.probabilities);
    }
    println!("frustration {:.2}", result.answer(&frustration)?.score);
    println!("urgent {:.2}", result.answer(&urgent)?.noul);
    Ok(())
}
```

`Questions::add` returns an `AnswerKey`, so `result.answer(&key)` hands back the
answer type that matches the question. `result.answers` holds every answer by name
if you need to walk them.

State and descriptions are an `Entry`: text, a JSON object, a JSON array, or null.
Use `Entry::from_serialize(&value)` for your own structs. Object key order is kept.

### Typed labels

Declare choice labels as an enum and match on it instead of on strings:

```rust
use kunobi_jev::{Client, Questions, SystemOneRequest, choice_of};

kunobi_jev::labels! {
    pub enum Team {
        Billing = "billing": "Payment or subscription issues",
        Technical = "technical": "Bugs or integration problems",
        Other = "other",
    }
}

async fn route(client: &Client, ticket: &str) -> kunobi_jev::Result<Option<Team>> {
    let mut questions = Questions::new();
    let team = questions.add("team", choice_of::<Team>("Which team should handle this?"));
    let result = client.system_one(SystemOneRequest::new(ticket, questions)).await?;
    Ok(result.answer(&team)?.decide(0.6))
}
```

`decide(min_confidence)` returns the label only when confidence reaches the threshold,
so unclear cases can go to a person. Scores and yes/no answers have `decide` and
`is_yes` helpers too. A label the enum doesn't know fails with `Error::UnexpectedAnswer`.

### Testing your code

Take `&dyn SystemOne` (or `impl SystemOne`) instead of `Client`. With the `testing`
feature, `FakeSystemOne` answers from a script, checks each scripted answer against the
question, and records the requests it received:

```toml
[dev-dependencies]
kunobi-jev = { version = "0.2", features = ["testing"] }
```

```rust
let jev = FakeSystemOne::new()
    .noul("billing", 0.92)
    .choice_of("team", Team::Billing, 0.81);
```

## Configuration

`Client::new()` reads the environment. `Client::builder()` sets values in code,
which take precedence.

| Builder method | Environment | Default |
| --- | --- | --- |
| `api_key` or `credential_provider` | `TYPESAFE_API_KEY` | required |
| `base_url` | `TYPESAFE_BASE_URL` | `https://api.typesafe.ai`; must be https |
| `default_model` | `TYPESAFE_DEFAULT_MODEL` | `jev-latest` |
| `timeout` | | 5 s per attempt |
| `total_timeout` | | 10 s for a whole call, retries included; `None` removes it |
| `max_concurrent_requests` | | none; shared by clones of the client |
| `retry` | | `RetryPolicy::default()` |
| `default_header` | | none |
| `http_client` | | a new `reqwest::Client` |
| `log_bodies` | | off |
| `allow_insecure_http` | | off |

Per call, you can override the timeouts, the retry policy and headers:

```rust
let models = client
    .models()
    .list()
    .timeout(Duration::from_secs(2))
    .max_retries(0)
    .with_response()
    .await?;
println!("request {:?}", models.request_id);
```

Nothing is sent until the call is awaited. Dropping the future cancels the request
and any pending retry. `total_timeout` bounds a whole call: attempts are shortened to
fit the time left, a retry is skipped when its backoff would end past the bound, and a
retry cut short by the bound returns the previous attempt's error. It defaults to 10 s, which is
two attempts and the backoff between them; pass `None` to remove it.

Both defaults are sized for how fast this model answers: measured against the live
API, a three-question request took 292 ms at the median and 728 ms at the worst of
twenty calls. A 429 whose `Retry-After` exceeds the budget is returned rather than
waited out, which is what an interactive caller wants. Batch work should raise the
budget, or remove it.

### Without an async runtime

```toml
kunobi-jev = { version = "0.2", features = ["blocking"] }
```

```rust
use kunobi_jev::blocking::Client;

let client = Client::new()?;
let models = client.models()?;
```

The blocking client owns a runtime, so it refuses to run inside one: calling it from
async code returns an error naming the async client instead of blocking that thread.

## Credentials

**Servers and CLIs** can use a TypeSafe API key from the environment or from your
secret store:

```rust
let key: String = read_from_vault()?;
let client = Client::builder().api_key(key).build()?;
```

**Apps that run on user machines must not ship a TypeSafe API key.** Anyone with the
binary can extract it. Route calls through your own backend, which holds the key,
and authenticate to it with a short-lived user token. A credential provider is asked
for a token before every attempt, so refreshed tokens are picked up on retries:

```rust,ignore
let auth = Arc::new(kunobi_auth::client::AuthClient::new(config)?);
let client = Client::builder()
    .base_url("https://jev.kunobi.example")
    .credentials_fn(move || {
        let auth = auth.clone();
        async move { auth.token().await }
    })
    .build()?;
```

Implement `CredentialProvider` directly when a closure isn't enough. The client does
not cache tokens; the provider should. A provider that fails or takes longer than
the per-attempt timeout fails the call with `Error::Credentials`, which is not
retried and never includes the token.

What the client does with credentials:

- Sends them only in the `Authorization` header, marked sensitive, over https.
  Plain `http://` is refused except for loopback hosts, including when it comes
  from `TYPESAFE_BASE_URL`. `allow_insecure_http(true)` lifts that for trusted
  private networks.
- Holds an API key as a `SecretString`, wiped on drop. The header value built for
  each request is a separate copy owned by the HTTP stack and is not wiped.
- Drops `Authorization` when a redirect leaves the original scheme, host or port.
- Never prints credentials: `Debug` shows `***`, and logs show only the scheme and
  the last four characters.
- Ignores `Authorization` set through default or per-call headers.

Environment variables are visible to child processes and to other processes of the
same user, so prefer a secret store or a provider for anything beyond local
development.

## Retries and errors

By default a call retries twice on 408, 429 and 5xx responses, connection errors
and timeouts, within the 10 s `total_timeout`. `RetryPolicy::retry_if` adds errors the
built-in rules decline; it only widens what is retried, so a predicate cannot switch
the defaults off. Backoff starts at 500 ms, doubles up to 5 s, and subtracts up to 25%
jitter. A `retry-after-ms` or `Retry-After` header of up to 60 s replaces the
backoff. Each retry sends `X-TypeSafe-Retry-Count`.

Errors are one `kunobi_jev::Error` enum:

- `Api`: a non-2xx response. `ApiError` carries the status, `kind()`, the parsed body,
  the request ID and `retry_after()`.
- `Connection` and `Timeout`: the request failed in transit. `is_connection()` is true for both.
- `InvalidRequest` and `Config`: rejected before sending, such as an empty question
  set, a score with fewer than two levels, a missing API key, or a plain-http URL.
- `Credentials`: the credential provider failed, timed out, or returned an unusable token.
- `Decode`: a 2xx body with an unexpected shape.
- `UnexpectedAnswer`: `result.answer(&key)` found no answer under that name, an answer of
  another type, or a label the key's enum doesn't know.

## When the API grows

The crate does not have to be updated first. A question field it does not model goes
through `noul(..).extra("weight", 2)`, a whole question type through
`Question::raw(json!({"type": "rank", …}))`, and a request field through
`SystemOneRequest::extra`. An answer type it does not know arrives as
`Answer::Unknown` with its JSON intact, rather than being dropped.

Model names are free-form strings: `GET /v1/models` lists the aliases but versioned
IDs work whether or not they appear there, so the crate never validates them. Aliases
move when a release ships, so pin a versioned ID such as `jev-1.13.0` if you have
tuned confidence thresholds, and read `result.model` to log which model answered.

## Logging

Each call runs in a `typesafe.request` span with OpenTelemetry-style fields:
`http.request.method`, `url.path`, `http.response.status_code`,
`http.request.resend_count`, `typesafe.request_id` and `error.type`. Each attempt logs a
summary at `info`, such as
`#3 POST /v1/systemone <- 200 in 212ms (request req_…)`, and redacted headers at
`debug`. Request and response bodies are not logged unless you call
`log_bodies(true)`: they contain the state you send, which may include personal data.

## Development

```sh
mise install
cargo test
cargo clippy --all-targets -- -D warnings
mise run deny
TYPESAFE_API_KEY=... mise run e2e      # live API tests
cargo run --example demo               # needs TYPESAFE_API_KEY
cd fuzz && cargo +nightly fuzz run parse_error_body
```

## License

Apache-2.0. This crate ports the [TypeSafe JavaScript SDK](https://github.com/typesafe-ai/typesafe-sdk-js)
(MIT); see [NOTICE](NOTICE).
