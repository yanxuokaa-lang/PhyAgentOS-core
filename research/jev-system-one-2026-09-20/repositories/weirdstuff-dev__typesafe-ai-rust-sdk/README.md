# typesafe-ai

Unofficial Rust SDK for the [TypeSafe AI](https://typesafe.ai) API, ported from the
[official JavaScript SDK](https://github.com/typesafe-ai/typesafe-sdk-js).

```rust,no_run
use indexmap::IndexMap;
use typesafe_ai::questions::noul;
use typesafe_ai::{ClientConfig, RequestOptions, SystemOneRequest, TypeSafeClient};

#[tokio::main]
async fn main() -> Result<(), typesafe_ai::Error> {
    // Reads TYPESAFE_API_KEY from the environment if `.api_key(...)` is omitted.
    let client = TypeSafeClient::new(ClientConfig::new())?;

    let mut questions = IndexMap::new();
    questions.insert("billing".to_owned(), noul("Is this about billing?", None));

    let result = client
        .system_one(
            SystemOneRequest::new("I was charged twice. Please help.", questions),
            RequestOptions::default(),
        )
        .await?;

    println!("{:?}", result.answers["billing"].as_noul());
    Ok(())
}
```

See `examples/basic.rs` for a fuller walkthrough covering `noul`, `score`, and `choice`
questions, and `client.models().list(...)`.

## Configuration

`ClientConfig` is a builder; every field falls back to an environment variable, then an SDK
default:

| Builder method   | Environment variable    | Default                    |
| ---------------- | ------------------------ | --------------------------- |
| `.api_key(...)`  | `TYPESAFE_API_KEY`       | *(required)*                |
| `.base_url(...)` | `TYPESAFE_BASE_URL`      | `https://api.typesafe.ai`   |
| `.default_model(...)` | `TYPESAFE_DEFAULT_MODEL` | `jev-latest`            |
| `.log_level(...)` | `TYPESAFE_LOG_LEVEL`    | `warn`                      |

## Design notes vs. the JavaScript SDK

This is a from-scratch Rust port, not a binding. A few things intentionally differ because
Rust's type system can't express what TypeScript does here:

- **Answers are an enum, not per-key generics.** The JS SDK infers `answers.billing.noul`'s
  type from the `billing` question at compile time via structural generics. Rust has no
  equivalent for a heterogeneous map keyed by string literals, so `SystemOneResult::answers` is
  an `IndexMap<String, Answer>` where `Answer` is a tagged enum; use `.as_noul()`, `.as_score()`,
  or `.as_choice()` to pull out the variant you expect.
- **`EntryType` collapses to `serde_json::Value`.** The JS SDK narrows question state and
  instructions to `string | object | array | null` at the type level (excluding bare numbers and
  booleans). Rust uses a plain `Json = serde_json::Value` alias instead; the server, not the
  client, is the source of truth for what's actually a valid entry.
- **No browser guard.** The JS SDK refuses to run in a browser by default (it would leak the API
  key) unless `dangerouslyAllowBrowser` is set. That doesn't apply to a compiled Rust binary, so
  it's omitted.
- **Cancellation uses `tokio_util::sync::CancellationToken`** in place of `AbortSignal`, passed
  via `RequestOptions.cancellation`.
- **No `withResponse()`/`asResponse()`.** The JS SDK's `APIPromise` exposes the raw `Response`
  and request ID alongside the parsed body. This SDK returns `Result<T, Error>` directly;
  `Error::Api` still carries `request_id`, `status`, and `headers` for failed requests.
