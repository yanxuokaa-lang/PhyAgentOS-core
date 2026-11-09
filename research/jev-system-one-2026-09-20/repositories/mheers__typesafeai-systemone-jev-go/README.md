# jev-go

[![Go Reference](https://pkg.go.dev/badge/github.com/mheers/typesafeai-systemone-jev-go.svg)](https://pkg.go.dev/github.com/mheers/typesafeai-systemone-jev-go)
[![Go version](https://img.shields.io/github/go-mod/go-version/mheers/typesafeai-systemone-jev-go)](https://github.com/mheers/typesafeai-systemone-jev-go/blob/main/go.mod)
[![CI](https://github.com/mheers/typesafeai-systemone-jev-go/actions/workflows/ci.yml/badge.svg)](https://github.com/mheers/typesafeai-systemone-jev-go/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/mheers/typesafeai-systemone-jev-go)](LICENSE)

A Go client for the TypeSafe System One API — typed judgments your code can act
on, instead of generated text your code has to parse.

TypeSafe's System One models, starting with **Jev**, turn natural language and
application state into structured answers: a choice from options you define, a
score along levels you describe, or the probability that a yes/no statement is
true. Code owns the workflow; the model supplies programmable common sense
where ordinary code would need semantic understanding. `jev-go` is an
independent Go SDK for that API, written by hand against the
[vendored OpenAPI specification](openapi/README.md), with no third-party
dependencies.

```go
response, err := client.SystemOne(ctx, jev.SystemOneRequest{
	State: ticket,
	Questions: jev.Questions{
		"department": jev.Choice{
			Instructions: "Which team should handle this?",
			Criteria: jev.Choices{
				"billing":   "Payment or subscription issues",
				"technical": "Bugs or integration problems",
				"sales":     "Pricing or account questions",
			},
		},
		"is_urgent": jev.Noul{
			Instructions: "Does this message convey urgency or time-sensitivity?",
		},
	},
})
// department.Choice == "billing", urgency.Noul == 0.99
```

## Installation

```bash
go get github.com/mheers/typesafeai-systemone-jev-go
```

Requires Go 1.23 or newer. The package name is `jev`.

Set your API key once, from the [TypeSafe console](https://console.typesafe.ai/keys):

```bash
export TYPESAFE_API_KEY=...
```

```go
import "github.com/mheers/typesafeai-systemone-jev-go"

client, err := jev.NewClient() // reads TYPESAFE_API_KEY, TYPESAFE_BASE_URL, ...
if err != nil {
	log.Fatal(err)
}
```

## Quickstart

The complete program from [examples/quickstart/main.go](examples/quickstart/main.go):

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	jev "github.com/mheers/typesafeai-systemone-jev-go"
)

func main() {
	client, err := jev.NewClient()
	if err != nil {
		if os.Getenv(jev.EnvAPIKey) == "" {
			log.Fatalf("set %s to run this example: %v", jev.EnvAPIKey, err)
		}
		log.Fatal(err)
	}

	ticket := "Hi, I've been trying to connect my Stripe account for 3 days and it keeps failing. " +
		"I'm losing sales. Please help ASAP."

	response, err := client.SystemOne(context.Background(), jev.SystemOneRequest{
		State: ticket,
		Questions: jev.Questions{
			"department": jev.Choice{
				Instructions: "Which team should handle this?",
				Criteria: jev.Choices{
					"billing":   "Payment or subscription issues",
					"technical": "Bugs or integration problems",
					"sales":     "Pricing or account questions",
				},
			},
			"frustration": jev.Score{
				Instructions: "How frustrated is the customer?",
				Criteria:     []any{"Calm, just stating facts", "Frustrated but civil", "Very angry, strong language"},
			},
			"is_urgent": jev.Noul{
				Instructions: "Does this message convey urgency or time-sensitivity?",
			},
		},
	})
	if err != nil {
		log.Fatal(err)
	}

	department, _ := response.Choice("department")
	frustration, _ := response.Score("frustration")
	urgency, _ := response.Noul("is_urgent")

	fmt.Printf("department:  %-10s (confidence %.2f)\n", department.Choice, department.Confidence)
	fmt.Printf("frustration: %.2f          (confidence %.2f, legend %v)\n", frustration.Score, frustration.Confidence, frustration.Legend)
	fmt.Printf("is urgent:   %.2f\n", urgency.Noul)
	fmt.Printf("model:       %s\n", response.Model)
	fmt.Printf("usage:       %d input tokens, %d output tokens\n", response.Usage.InputTokens, response.Usage.OutputTokens)
}
```

## The three primitives

| Question | You provide | You get back |
| --- | --- | --- |
| `Noul` | A yes/no statement | `Noul` probability, 0 to 1 |
| `Choice` | A map of options to descriptions | `Choice`, `Probabilities`, `Confidence` |
| `Score` | An ordered list of level descriptions | `Score`, `Legend`, `Probabilities`, `Confidence` |

Every answer is constrained to what you supplied: a `Choice` is always one of
your options, and a `Score` always lands on your rubric. Answers are also
independent, so adding or removing questions never changes the others.

### Noul — is this true?

Use a Noul when the probability itself is the signal: routing on "does this
report a bug?", thresholding on "is this message abusive?", escalating on
"is this urgent?".

```go
jev.Noul{
	Instructions: "Does this message convey urgency?",
	Criteria: &jev.NoulCriteria{ // optional: sharpen what yes and no mean
		True:  "Explicitly time-sensitive",
		False: "No urgency expressed",
	},
}
```

A value near 0.5 means the model gives both outcomes similar probability — not
medium intensity. When a judgment has a spectrum, use a Score instead.

### Choice — which of these?

Give the complete list of options and describe when each applies. Add an
`"other"` option when the list might not cover every input; the model cannot
pick an option you did not supply.

```go
jev.Choice{
	Instructions: "Which team should handle this?",
	Criteria: jev.Choices{
		"billing":   "Payment or subscription issues",
		"technical": "Bugs or integration problems",
		"sales":     "Pricing or account questions",
		"other":     nil, // no extra description needed
	},
}
```

### Score — how much?

Levels are ordered from lowest to highest and must describe concrete
situations that stand on their own. The answer is the probability-weighted
position, so it can land between levels. Two or more levels give the most
useful answers.

```go
jev.Score{
	Instructions: "How frustrated is the customer?",
	Criteria:     []any{"Calm, just stating facts", "Frustrated but civil", "Very angry, strong language"},
}
```

Instructions and criteria accept structured JSON too — useful when a question
has several parts:

```go
jev.Noul{
	Instructions: map[string]any{
		"task":   "Decide whether the customer is requesting a refund.",
		"policy": "Refunds are eligible within 30 days of delivery.",
	},
}
```

## Reading answers

Answers are typed. Use the accessors for one answer, or the grouped maps to
walk all answers of one kind:

```go
department, ok := response.Choice("department") // ChoiceAnswer, bool
urgency, ok := response.Noul("is_urgent")       // NoulAnswer, bool
frustration, ok := response.Score("frustration") // ScoreAnswer, bool

for name, choice := range response.Choices() {
	fmt.Println(name, choice.Choice, choice.Probabilities, choice.Confidence)
}
for name, score := range response.Scores() {
	fmt.Println(name, score.Score, score.Legend)
}
```

`Confidence` summarizes how peaked the distribution is, from 0 to 1. It tells
you how strongly the model preferred its answer, not whether the answer is
correct: use thresholds to decide when to act automatically and when to send a
case to a person.

```go
if department.Confidence < 0.5 {
	// Ambiguous choice: queue for human review instead of auto-routing.
}
```

`response.Answers` exposes everything, including answers whose kind this SDK
version does not model, preserved as `UnknownAnswer` so a newer API cannot
silently drop data.

## Ask many questions in one call

Every question in a request is evaluated against the same state, in parallel,
and cannot see the other answers. Asking more questions barely changes latency
and costs only the extra question tokens, so ask everything the code might
need — including speculative questions whose answers you may ignore.
[examples/triage/main.go](examples/triage/main.go) shows the pattern:

```go
response, err := client.SystemOne(ctx, jev.SystemOneRequest{
	State: report,
	Questions: jev.Questions{
		"is_bug_report":   jev.Noul{Instructions: "Does this report a bug or outage?"},
		"severity":        jev.Score{Instructions: "How severe is the impact?", Criteria: severityLevels},
		"frustration":     jev.Score{Instructions: "How frustrated is the reporter?", Criteria: frustrationLevels},
		"reproducibility": jev.Score{Instructions: "How reproducible is the report?", Criteria: reproducibilityLevels},
	},
})

// Combine the answers with weights your code owns.
score := 0.5*severity.Score + 0.2*frustration.Score + 0.3*reproducibility.Score
```

When a later judgment needs an earlier answer as *context* (to fetch new state
or pick new options), make a second call. Otherwise ask both now and combine in
code.

## Async, batching, and streaming

TypeSafe evaluates every question of a request in one response, so there is no
token stream inside a call. The concurrency wrappers work one level up, across
whole calls:

```go
// One call in the background while the rest of the workflow runs.
future := client.SystemOneAsync(ctx, request)
// ... do other work ...
response, err := future.Result()
```

```go
// Many independent calls with bounded concurrency, delivered as they finish.
results, err := client.StreamSystemOne(ctx, requests,
	jev.WithStreamConcurrency(8), // calls in flight (default 4)
	jev.WithStreamOrdered(true),  // emit in input order instead of completion order
	jev.WithStreamCallOptions(jev.WithCallTimeout(30*time.Second)),
)
if err != nil {
	return err
}
for result := range results {
	if result.Err != nil {
		log.Printf("request %d failed: %v", result.Index, result.Err)
		continue
	}
	department, _ := result.Response.Choice("department")
	fmt.Println(result.Index, department.Choice)
}
```

The channel closes when every call has finished. Cancelling `ctx` fails the
in-flight calls with `ctx.Err()`, stops the stream, and releases the workers —
cancel it if you stop reading early. A request that fails validation is
reported as a `StreamResult` with `ErrInvalidRequest` and does not affect the
other calls. [examples/batch/main.go](examples/batch/main.go) shows both
wrappers, and the CLI's `batch` command streams a JSON array of requests.

## State

`State` may be a string, or structured data as a `map[string]any`, `[]any`, or
any struct that marshals to an object. Name the relevant parts of structured
state in each instruction with backticked paths:

```go
state := map[string]any{
	"ticket": map[string]any{
		"subject": "Duplicate charge",
		"messages": []any{
			map[string]any{"from": "customer", "text": "I was charged twice for order A-104. Please refund the duplicate."},
		},
	},
	"order": map[string]any{
		"id":      "A-104",
		"charges": []any{map[string]any{"amount_usd": 49}, map[string]any{"amount_usd": 49}},
	},
	"refund_policy": "Duplicate charges are eligible for a refund.",
}

response, err := client.SystemOne(ctx, jev.SystemOneRequest{
	State: state,
	Questions: jev.Questions{
		"refund_requested": jev.Noul{
			Instructions: "Does `ticket.messages[0].text` request a refund?",
		},
		"policy_supports_refund": jev.Noul{
			Instructions: "Does `refund_policy` support the request in `ticket.messages[0].text`, given `order.charges`?",
		},
	},
})
```

## Configuration

```go
client, err := jev.NewClient(
	jev.WithAPIKey("..."),                      // or TYPESAFE_API_KEY
	jev.WithBaseURL("https://api.typesafe.ai"), // or TYPESAFE_BASE_URL
	jev.WithModel(jev.ModelJevLatest),          // or TYPESAFE_DEFAULT_MODEL
	jev.WithTimeout(10*time.Second),            // per attempt
	jev.WithHTTPClient(myHTTPClient),           // custom transport, proxy, ...
	jev.WithHeader("X-Request-Source", "myapp"),
	jev.WithLogger(slog.Default()),
)
```

Explicit options take precedence over environment variables, which take
precedence over defaults. Per-call options override the client for one call:

```go
response, err := client.SystemOne(ctx, request,
	jev.WithCallTimeout(30*time.Second),
	jev.WithCallRetryPolicy(jev.RetryPolicy{}), // disable retries for this call
	jev.WithCallHeader("X-Trace-ID", traceID),
)
```

### Environment variables

| Variable | Configures | Default |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | API key (required) | — |
| `TYPESAFE_BASE_URL` | API root | `https://api.typesafe.ai` |
| `TYPESAFE_DEFAULT_MODEL` | Model for requests that do not name one | `jev-latest` |
| `TYPESAFE_LOG_LEVEL` | SDK logging on stderr: `debug`, `info`, `warning`, `error`, `off` | silent |

Logging never includes request or response bodies, and the API key is never
logged.

## Command line

The `jev` command exposes the same API from a shell:

```bash
go install github.com/mheers/typesafeai-systemone-jev-go/cmd/jev@latest

jev models
jev noul --state "Wire transfer failed, please help" \
    --instructions "Does this message convey urgency?"
echo "The delivery is three days late." | jev score \
    --instructions "How frustrated is the customer?" \
    --level Calm --level Frustrated --level "Very angry"
jev choice --state "The API returns 500s" \
    --instructions "Which team should handle this?" \
    --option billing=Payments --option technical
jev ask --questions questions.json --state "My invoice is wrong"
jev batch --file requests.json --concurrency 4 | jq .
```

```
$ jev noul --state "Wire transfer failed, please help" --instructions "Does this message convey urgency?"
answer  noul  0.98
```

| Command | Purpose |
| --- | --- |
| `models` | List the models available to the account |
| `noul`, `choice`, `score` | Ask one typed question with flags |
| `ask` | Ask a JSON object of questions (the wire format) about state |
| `batch` | Stream a JSON array of requests, one NDJSON result per line |

Common flags: `--state`, `--state-file`, `--state-json`, `--model`,
`--timeout`, and `--json` for the raw response; `batch` adds `--file`,
`--concurrency`, and `--ordered`. The state can also be piped on stdin, and
`-` means stdin for `--questions`, `--state-file`, and `--file`. Exit codes are
0 on success, 1 on a request failure, and 2 on a usage problem.

## Cookbook examples

The [examples](examples) directory has runnable programs for the patterns from
the TypeSafe cookbooks:

| Example | Pattern |
| --- | --- |
| [quickstart](examples/quickstart) | Noul, Choice, and Score in one call |
| [triage](examples/triage) | Composite scoring with weights your code owns |
| [guardrails](examples/guardrails) | One request per hazard, thresholds as policy |
| [rerank](examples/rerank) | One Score question per candidate passage |
| [extraction](examples/extraction) | Regex candidates, model selection, verbatim copy |
| [batch](examples/batch) | `SystemOneAsync` and `StreamSystemOne` |

## Models

`jev-latest` is the most recent stable release and the default.
`jev-preview` may move ahead between releases. Pin a versioned ID such as
`jev-1.13.0` when thresholds are tuned against a specific release — the
response's `Model` field reports the versioned ID that answered, so you can
log which model produced each result.

```go
models, err := client.ListModels(ctx)
for _, model := range models.Models {
	fmt.Println(model.Name, model.ReleaseDate, model.Description)
}
```

## Errors

Every failure is a typed error, inspectable with `errors.As`:

```go
response, err := client.SystemOne(ctx, request)
switch {
case err == nil:
	// use response
case errors.Is(err, jev.ErrTimeout):
	// the per-attempt timeout or context deadline elapsed
default:
	var rateLimit *jev.RateLimitError
	var auth *jev.AuthenticationError
	var unprocessable *jev.UnprocessableEntityError
	var apiErr *jev.APIError
	switch {
	case errors.As(err, &rateLimit):
		time.Sleep(rateLimit.RetryAfter) // server's requested wait, if any
	case errors.As(err, &auth):
		log.Println("check TYPESAFE_API_KEY")
	case errors.As(err, &unprocessable):
		log.Println("fix the request:", unprocessable.Message)
	case errors.As(err, &apiErr):
		log.Printf("request failed: %v (request_id=%s)", err, apiErr.RequestID)
	}
}
```

| Error | Meaning |
| --- | --- |
| `ErrNoAPIKey`, `ErrInvalidConfiguration`, `ErrInvalidRequest` | The SDK refused to send: fix the configuration or request |
| `APIError` and its subtypes (`BadRequestError`, `AuthenticationError`, `PermissionDeniedError`, `NotFoundError`, `UnprocessableEntityError`, `RateLimitError`, `InternalServerError`) | The API returned a non-2xx status. `Message`, `Body`, `StatusCode`, and `RequestID` carry the details |
| `InvalidResponseError` | A 2xx response could not be decoded — usually a proxy or a newer API version |
| `TimeoutError` / `ErrTimeout` | An attempt exceeded its timeout |
| `ConnectionError` | The request never got an HTTP response |

### Retries

The client retries transient failures with jittered exponential backoff,
honoring `Retry-After` and `retry-after-ms`. The defaults match TypeSafe's
official SDKs:

| Setting | Default |
| --- | --- |
| `MaxRetries` | 2 |
| `BackoffInitial` / `BackoffMax` | 500ms / 5s |
| `BackoffJitter` | 0.25 |
| `HTTPStatuses` | 408, 429, and every 5xx |
| `RetryOnConnectionError`, `RetryOnTimeout` | enabled |
| `TotalTimeout` | 30s per call, including delays |

Customize by copying the default policy, or disable retries with
`jev.RetryPolicy{}`:

```go
policy := jev.DefaultRetryPolicy()
policy.MaxRetries = 5
policy.TotalTimeout = time.Minute
client, err := jev.NewClient(jev.WithRetryPolicy(policy))
```

## Timeouts

Each attempt gets its own timeout (10s by default), independent of the retry
budget. Contexts flow through every call, so `context.WithTimeout` composes
with retries and aborts a call — including while backing off — as soon as the
caller gives up.

## Forward compatibility

The API may add fields and question or answer kinds before this SDK models
them. There are three escape hatches:

```go
// 1. Send request fields this SDK does not know about.
request.Extra = map[string]any{"beam_width": 4}

// 2. Ask question kinds this SDK does not model.
question := jev.RawQuestion{
	"type":         "multinomial",
	"instructions": "Which labels apply?",
	"criteria":     []any{"a", "b", "c"},
}

// 3. Receive answer kinds this SDK does not model: they arrive as
//    jev.UnknownAnswer with the raw JSON preserved.
```

## API surface

- `Client` — `SystemOne`, `SystemOneAsync`, `StreamSystemOne`, `ListModels`, `ListModelsAsync`, `Model`, `BaseURL`
- Questions — `Noul`, `Choice`, `Score`, `RawQuestion`, `NoulCriteria`, `Choices`, `Questions`
- Answers — `SystemOneResponse` (`Noul`, `Choice`, `Score`, `Nouls`, `Choices`, `Scores`, `Answer`), `NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`, `UnknownAnswer`, `Answers`, `Usage`
- Concurrency — `Future[T]` (`Done`, `Result`, `Wait`), `StreamResult`, `StreamOption`s (`WithStreamConcurrency`, `WithStreamOrdered`, `WithStreamCallOptions`)
- Models — `ModelMetadata`, `ModelsResponse`, `ModelJevLatest`, `ModelJevPreview`, `ModelJev1130`
- Configuration — `Option`s, `CallOption`s, `RetryPolicy`, `DefaultRetryPolicy`
- Command — `cmd/jev`
- Errors — see above

Full reference: [pkg.go.dev](https://pkg.go.dev/github.com/mheers/typesafeai-systemone-jev-go).

## Specification conformance

`openapi/typesafe-openapi.json` vendors TypeSafe's published OpenAPI 3.1
specification. The SDK types are hand-written against it, and the test suite
checks them against the examples and required fields in the spec, so drift
shows up as a failing test.

## Development

```bash
gofmt -l .          # formatting
go vet ./...        # static checks
go test ./...       # unit tests, no network
go run ./cmd/jev help   # the CLI
go run ./examples/quickstart
```

End-to-end tests run against the live API only when `TYPESAFE_API_KEY` is set,
and are skipped otherwise:

```bash
go test -run TestE2E -v ./...
```

CI runs formatting, vet, and tests with the race detector on the two most
recent Go releases.

## License

MIT — see [LICENSE](LICENSE). © Marcel Heers.

This is an independent, community-maintained SDK. It is not affiliated with or
endorsed by TypeSafe AI. TypeSafe and Jev are trademarks of their respective
owners.
