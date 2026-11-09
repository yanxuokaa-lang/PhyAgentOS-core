# judgement

**Jev decisions, ready for agents and scripts.**

[![CI](https://github.com/Mentioum/judgement/actions/workflows/ci.yml/badge.svg)](https://github.com/Mentioum/judgement/actions/workflows/ci.yml)
[![Go Reference](https://pkg.go.dev/badge/github.com/Mentioum/judgement.svg)](https://pkg.go.dev/github.com/Mentioum/judgement)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Go library and CLI for TypeSafe AI's System One API. Use Jev to classify records,
evaluate yes/no questions, and score content against rubrics from your own code.
No runtime dependencies beyond the Go standard library.

This is an independent, unofficial client. It is not affiliated with TypeSafe AI.
Jev returns structured decisions; your agent writes the scripts and controls the
workflow. Judgement does not generate or execute model-supplied code.

TypeSafe is the only implemented provider today. The CLI keeps provider calls
behind a small internal adapter so another provider can be added without
rewriting input handling or batching. A custom base URL supports compatible
TypeSafe endpoints; it does not translate other providers' APIs.

## Install

Download the archive for your operating system and architecture from
[GitHub Releases](https://github.com/Mentioum/judgement/releases/latest).
Choose `arm64` for Apple Silicon or other ARM machines, or `amd64` for Intel/AMD
64-bit machines. Extract it and put `judgement` (`judgement.exe` on Windows) in a
directory on your `PATH`. These binaries do not require Go. Releases include
`checksums.txt` for verifying downloads.

For Go users (Go 1.23 or newer):

```sh
go install github.com/Mentioum/judgement/cmd/judgement@latest
```

Or build a local checkout:

```sh
go build -o bin/judgement ./cmd/judgement
./bin/judgement describe
```

Set `TYPESAFE_API_KEY` through your environment or secret manager. Get a key from
the [TypeSafe console](https://console.typesafe.ai). The CLI never prompts for
credentials and does not read `.env` files automatically.

## One request, three kinds of decision

Save this as `request.json`:

```json
{
  "state": "I was charged twice. Please refund the extra payment today.",
  "questions": {
    "refund_requested": {
      "type": "noul",
      "instructions": "Does the customer request a refund?"
    },
    "team": {
      "type": "choice",
      "instructions": "Which team should handle this ticket?",
      "criteria": {
        "billing": "Payments and refunds",
        "support": "Product problems",
        "other": "None of the listed teams fits"
      }
    },
    "urgency": {
      "type": "score",
      "instructions": "How urgent is the request?",
      "criteria": ["No deadline", "This week", "Today"]
    }
  }
}
```

```sh
# Offline: catch malformed requests without credentials or API charges.
judgement validate --input request.json

# Network: retain answers, probabilities, confidence, model, and token usage.
judgement evaluate --input request.json > result.json
jq '.answers.team | {choice, confidence, probabilities}' result.json
```

| Primitive | Output | Typical use |
| --- | --- | --- |
| Noul | Probability of yes, between 0 and 1 | Verification, filters, conditions |
| Choice | Selected label, probability distribution, confidence | Routing, classification, candidate selection |
| Score | Expected numeric score, rubric legend, distribution, confidence | Ranking, severity, quality scoring |

Instructions and criterion descriptions accept strings, objects, arrays, or
null. Scores use an ordered list of at least two levels; the result may fall
between level indices. Multiple question types can share a single state.
Explicit null state is accepted for compatibility with the current JavaScript
SDK; the general HTTP and Python documentation are narrower, so prefer concrete
state. Input and question shapes are checked locally; server limits and model
quality still require evaluation on your own data.

## Built for agents

* `describe` returns the command contract, JSON Schema, authentication details,
  and exit codes in one machine-readable response.
* `schema` exposes a standalone JSON Schema for request construction.
* Success output is JSON; batch output is JSONL. Errors use JSON on stderr.
* Full responses are preserved, including new fields and large JSON integers.
* Files and stdin avoid shell quoting for long content and structured rubrics.
* Bounded concurrent batches preserve order and associate results with IDs.
* Deadlines include retries. Interrupts cancel in-flight requests and backoff.
* Authentication is environment-only. Remote error bodies are not echoed.

Read the [agent workflow guide](docs/agents.md) for validation, batching, retries,
and confidence-based routing. See [CLI details](docs/cli.md) for exact contracts.

```sh
judgement describe
judgement schema > request.schema.json
judgement models

# Reuse a questions file with plain-text state from a pipeline.
cat ticket.txt | judgement evaluate --state-file - --questions examples/questions.json

# Use a specific model to keep evaluated thresholds reproducible.
judgement evaluate --input request.json --model jev-1.13.0 --timeout 30s
```

## Process a dataset

Each JSONL line is a request, or an envelope with `id` and `request`:

```json
{"id":"ticket-42","request":{"state":"Please refund me","questions":{"refund":{"type":"noul","instructions":"Is a refund requested?"}}}}
```

```sh
judgement batch --input examples/batch.jsonl --concurrency 4 > results.jsonl
```

Each output line contains `index`, optional `id`, and either `result` or `error`.
Individual failures do not stop other records. Exit status is 1 if any record
fails. Order matches input, with bounded windows of up to `--concurrency`
records. This command is a client-side convenience; each record is an API call.

## Use from Go

```go
client, err := judgement.NewClient(judgement.Config{
    APIKey:     os.Getenv("TYPESAFE_API_KEY"),
    Timeout:    30 * time.Second,
    MaxRetries: 2,
})
if err != nil {
    return err
}
result, err := client.Evaluate(ctx, judgement.Request{
    State: "Please refund the duplicate charge.",
    Questions: map[string]judgement.Question{
        "refund": judgement.Noul("Is a refund requested?"),
        "team": judgement.Choice("Which team should handle this?", map[string]any{
            "billing": "Payments and refunds",
            "support": "Product problems",
        }),
    },
})
if err != nil {
    return err
}
fmt.Println(*result.Answers["refund"].Noul)
```

The [complete Go example](examples/go/main.go) includes imports and executable
error handling. `ListModels` discovers model names; `EvaluateRaw` and
`ListModelsRaw` preserve the entire JSON response. The client is reusable across
goroutines; keep request maps unchanged while calls are in progress. Zero
`MaxRetries` disables retries in the library; the CLI defaults to two retries.

## Development

```sh
go test -race ./...
go vet ./...
go build ./...
```

Tests use local HTTP servers and need no API credentials. They cover request
serialization, structured criteria, retries, cancellation, error redaction,
redirect handling, numeric precision, and batch ordering. Live service behavior
has not been verified with an API key for this initial release.

CI checks Go 1.23 and the current stable toolchain on Linux, macOS, and Windows.
Tagged versions build downloadable binaries with checksums through the release
workflow. See the [packaging and release guide](docs/releases.md),
[contributing](CONTRIBUTING.md), [security](SECURITY.md), and the
[changelog](CHANGELOG.md).

## API reference and scope

Implemented against TypeSafe's published documentation, checked September 18,
2026: [HTTP API](https://docs.typesafe.ai/api),
[models](https://docs.typesafe.ai/models),
[structured rubrics](https://docs.typesafe.ai/primitives/advanced), and
[SDK types](https://github.com/typesafe-ai/typesafe-sdk-js/blob/v0.6.0/src/types.ts).

Coverage includes the documented evaluation endpoint, model listing, all three
question types, structured descriptions, model selection, and complete response
data. Jev's current input is text/JSON; this client does not add media input,
text generation, fine-tuning, or code execution.

MIT licensed.
