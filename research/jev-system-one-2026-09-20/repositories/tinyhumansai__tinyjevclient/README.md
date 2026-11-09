# TinyJevClient

`tinyjevclient` is a typed Rust client for TypeSafe AI's System One API and
Jev model. It sends shared state with independent Choice, Score, and Noul
questions, validates the provider's response against the originating request,
and returns latency, attempts, usage, and request metadata alongside the typed
answers.

The client keeps execution and policy outside the model. A Choice selects only
from caller-supplied values, a Score rates one described dimension, and a Noul
reports the probability of a yes/no condition. Callers own confidence
thresholds, escalation, state transitions, and side effects.

```rust,no_run
use std::collections::BTreeMap;
use serde_json::json;
use tinyjevclient::{Choice, Client, EvaluationRequest, Question};

# async fn run() -> Result<(), Box<dyn std::error::Error>> {
let request = EvaluationRequest::jev(
    json!({"ticket": "I was charged twice"}),
    BTreeMap::from([(
        "route".to_owned(),
        Question::Choice(Choice {
            instructions: json!("Which team should handle this ticket?"),
            criteria: BTreeMap::from([
                ("billing".to_owned(), None),
                ("technical".to_owned(), None),
            ]),
        }),
    )]),
);
let result = Client::from_env()?.evaluate(&request).await?;
println!("{:?}", result.response.answers["route"]);
# Ok(())
# }
```

The API key is read from `TYPESAFE_API_KEY` or supplied to `ClientConfig`. It is
redacted from `Debug` and never included in errors. The live example spends a
real API call:

```sh
TYPESAFE_API_KEY='<key>' cargo run -p tinyjevclient --example basic
```

Remote API roots must use HTTPS; HTTP is reserved for literal loopback IPs.
Failed evaluations retain their classified error, attempt count, and elapsed
time so reliability measurements do not lose unsuccessful work.

The repository is GPL-3.0-only and is consumed by pinned git revision.
