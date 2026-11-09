# TypeSafe AI Go SDK

A **community** Go SDK for [TypeSafe AI](https://typesafe.ai). Standard library
only, apart from [godotenv](https://github.com/joho/godotenv) for `.env` loading.

> This is an unofficial, community-maintained SDK. It is not published, endorsed,
> or supported by TypeSafe AI — please report issues here rather than to them.
> The official SDK is [typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python),
> which this package is ported from.

## Quickstart

```
go get github.com/blazskufca/typesafe-sdk-go
```

Set `TYPESAFE_API_KEY` in your environment, then create a client and ask questions:

```go
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/blazskufca/typesafe-sdk-go"
)

func main() {
	client, err := typesafe.New()
	if err != nil {
		log.Fatal(err)
	}

	resp, err := client.SystemOne(context.Background(),
		map[string]any{"document": "I was charged twice. Please fix this ASAP."},
		typesafe.Questions{
			"category": typesafe.Choice{
				Instructions: "What is this ticket about?",
				Criteria:     map[string]typesafe.Content{"billing": nil, "technical": nil, "other": nil},
			},
		},
	)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(resp.Choices()["category"].Choice)
}
```

Learn what TypeSafe is and what it can do in the [TypeSafe docs](https://docs.typesafe.ai/).

## Questions and answers

Three question kinds, each with an answer to match:

| Question | Answer | Reads |
| --- | --- | --- |
| `Noul` | `*NoulAnswer` | `Noul` — probability of yes, 0 to 1 |
| `Choice` | `*ChoiceAnswer` | `Choice`, `Confidence`, `Probabilities` |
| `Score` | `*ScoreAnswer` | `Score`, `Confidence`, `Legend`, `Probabilities` (keyed by score level) |

Instructions and criteria take a `Content` — any value that encodes to JSON, so a
question can carry as much structure as it needs:

```go
typesafe.Noul{
	Instructions: map[string]any{"question": "Is this a duplicate charge?"},
	Criteria: &typesafe.NoulCriteria{
		True: map[string]any{"summary": "duplicated", "examples": []any{"charged twice"}},
	},
}
```

`RawQuestion` is the escape hatch for fields the API accepts before this SDK
models them; the SDK only checks that it has a nonempty `type` and leaves the
rest to the API:

```go
typesafe.RawQuestion{"type": "noul", "instructions": "Spam?", "weight": 3}
```

Answers come back three ways — pick whichever fits:

```go
// By kind.
tone := resp.Choices()["tone"]

// By kind and name, with a generic method.
tone, ok := resp.As[*typesafe.ChoiceAnswer]("tone")

// By type switch, over everything.
for name, answer := range resp.Answers {
	switch answer := answer.(type) {
	case *typesafe.NoulAnswer:
		fmt.Println(name, answer.Noul)
	case *typesafe.ChoiceAnswer:
		fmt.Println(name, answer.Choice)
	case *typesafe.ScoreAnswer:
		fmt.Println(name, answer.Score, answer.Legend)
	}
}
```

Or describe the response body with a struct of your own and get the answers as
typed fields, through the generic `SystemOneInto`:

```go
type Triage struct {
	Answers struct {
		Billing typesafe.NoulAnswer   `json:"billing"`
		Tone    typesafe.ChoiceAnswer `json:"tone"`
	} `json:"answers"`
	typesafe.ResponseMetadata
}

triage, err := typesafe.SystemOneInto[Triage](ctx, client, state, questions)
fmt.Println(triage.Answers.Tone.Choice, triage.RequestID)
```

Embedding `typesafe.ResponseMetadata` is optional; when present it is filled with
the request ID, status, headers, and the raw body.

## Configuration

Options configure a client and, with the same names, override any single call:

```go
client, err := typesafe.New(
	typesafe.WithAPIKey(key),          // or TYPESAFE_API_KEY
	typesafe.WithBaseURL(url),         // or TYPESAFE_BASE_URL
	typesafe.WithModel("jev-latest"),  // or TYPESAFE_DEFAULT_MODEL
	typesafe.WithTimeout(10*time.Second),
	typesafe.WithHeader("X-Team", "support"),
	typesafe.WithHTTPClient(httpClient),
	typesafe.WithLogger(logger),
)

resp, err := client.SystemOne(ctx, state, questions,
	typesafe.WithModel("other-model"),
	typesafe.WithTimeout(30*time.Second),
)
```

Explicit options beat environment variables, which beat any `.env` file, which
beat the defaults; empty and whitespace-only values are ignored.

### .env files

`WithDotenv` loads the SDK's variables from a `.env` file:

```go
client, err := typesafe.New(typesafe.WithDotenv())          // ./.env, ignored if absent
client, err := typesafe.New(typesafe.WithDotenv("config/.env")) // named files must exist
```

```dotenv
# .env
TYPESAFE_API_KEY="sk-..."
export TYPESAFE_DEFAULT_MODEL=jev-latest   # trailing comments are stripped
```

It is a fallback, never an override: a variable already set in the process
environment or supplied by an option is left alone, and nothing is written back
to the process environment. It applies to `New` only, not to individual calls.
Parsing is [godotenv](https://github.com/joho/godotenv)'s. Authentication, SDK
identification, `Accept`, and `Content-Type` are set by the SDK and cannot be
overridden by a header option.

### Retries

`WithTimeout` bounds a single HTTP attempt. `RetryPolicy` bounds the call:

```go
policy := typesafe.DefaultRetryPolicy() // 2 retries, 500ms–5s backoff, 30s budget
policy.MaxRetries = 5
policy.Retry = func(err error) bool { return errors.Is(err, typesafe.ErrNotFound) }

client, err := typesafe.New(typesafe.WithRetryPolicy(policy))
```

Retried by default: 408, 429, every 5xx, connection failures, and timeouts.
`Retry-After` and `retry-after-ms` are honored when the server sends them. A
retry whose delay would reach the budget is not attempted. **The zero
`RetryPolicy` disables retries** — start from `DefaultRetryPolicy()` and adjust.

Canceling the context stops a call wherever it is, retries included.

### Errors

Branch on the kind of failure with `errors.Is`, and reach for the detail with
`errors.As`:

```go
var apiErr *typesafe.APIError
switch {
case errors.As(err, &apiErr):
	fmt.Println(apiErr.Status, apiErr.Message, apiErr.RequestID())
case errors.Is(err, typesafe.ErrTimeout):
	// ...
}
```

| Sentinel | Meaning |
| --- | --- |
| `ErrAPI` | any unsuccessful response |
| `ErrBadRequest`, `ErrAuthentication`, `ErrPermissionDenied`, `ErrNotFound`, `ErrUnprocessableEntity`, `ErrRateLimit` | 400, 401, 403, 404, 422, 429 |
| `ErrInternalServer` | 5xx |
| `ErrConnection`, `ErrTimeout` | no response; timed out (implies `ErrConnection`) |
| `ErrInvalidResponse` | a 2xx body that did not match the schema |
| `ErrConfig`, `ErrInvalidQuestions` | rejected before anything was sent |

`*ResponseValidationError` names the offending field in `FieldPath`
(`answers.tone.confidence`, `models[1].name`), and `*TimeoutError` satisfies
`net.Error`.

### Logging

The SDK logs through `log/slog` and is silent unless you give it a logger with
`WithLogger` or set `TYPESAFE_LOG_LEVEL` (`debug`, `info`, `warn`, `error`,
`off`). Requests and responses are logged at debug, retries and response
summaries at info, and skipped answers at warn. Credential-bearing headers are
redacted; request and response bodies are not.

## Concurrency

A `Client` is safe for concurrent use and reuses connections through its
`http.Client`. There is nothing to close; `CloseIdleConnections` is there if you
want to release sockets early. Every call takes a `context.Context` and blocks —
for concurrency, run calls in goroutines.

## Notes for readers of the Python SDK

This is a community port of the official
[typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python),
written the way Go wants rather than transliterated:

- **One client, not two.** Go has a single concurrency model, so `TypeSafeClient`
  and `AsyncTypeSafeClient` collapse into `Client` with a `context.Context` on
  every call.
- **Options instead of keyword arguments,** shared between `New` and each call.
- **Errors, not exceptions.** The exception hierarchy becomes four error types
  and a set of sentinels for `errors.Is`, which branches on status without a
  type per status code.
- **Nothing to close.** `close()`/`aclose()` have no Go counterpart: an
  `http.Client` is not a resource that needs releasing.
- **Typed responses through generics** rather than pydantic response models. A
  custom type describes the body as a struct; the Python SDK's trick of lifting
  `answers.<name>` into a top-level field is not needed, because a nested
  `answers` struct says the same thing in plain Go.
- **`Usage` counts are plain ints.** A count the API did not report reads as 0
  rather than `None`.
- **Questions are `map[string]Question`.** Go maps are not covariant, so a
  `map[string]Noul` cannot be passed where `Questions` is expected; build the
  map as `typesafe.Questions{...}`.

## Documentation

Package documentation is on [pkg.go.dev](https://pkg.go.dev/github.com/blazskufca/typesafe-sdk-go).
Learn more in the [SDK docs](https://docs.typesafe.ai/).

## Development

```
go test ./...              # unit tests
go test -cover ./...       # with coverage
TYPESAFE_API_KEY=... go test -run Live ./...   # live API tests
```

## License

MIT
