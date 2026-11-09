# Jev

An unofficial Go client for [TypeSafe](https://typesafe.ai)'s System One Jev model.

> Currently in **alpha** stage, expect breaking changes and potential bugs.

The client sends a `state` plus a set of typed **questions** and gets back one
typed **answer** per question. Question ids are programmer handles: you build a
question, keep the value, and read its answer back from the result without
string keys or type assertions.

See the [TypeSafe documentation](https://docs.typesafe.ai/) for details on the 
API and the Jev model.

## Install

```sh
go get github.com/mhmdkzr/jev
```

Requires Go 1.27 or newer (see `go.mod`). The `jev` package has no
dependencies outside the standard library.

## Quickstart

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/mhmdkzr/jev"
)

func main() {
	client, err := jev.NewClient(jev.WithAPIKey(os.Getenv("JEV_API_KEY")))
	if err != nil {
		log.Fatal(err)
	}

	isUrgent := jev.Noul("is_urgent", "Does this convey urgency?").
		True("Explicitly time-sensitive").
		False("No urgency expressed")

	department := jev.Choice("department", "Which team should handle this?").
		Option("billing", "Payments, invoicing, refunds").
		Option("technical", "Bugs, outages, integrations").
		Option("sales", "Pricing, upgrades, new accounts")

	frustration := jev.Score("frustration", "How frustrated is the customer?").
		Level("Calm").
		Level("Frustrated").
		Level("Very angry")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	result, err := client.NewRequest().
		WithContext(ctx).
		State("Help! My payouts have been failing for 3 days.").
		Question(isUrgent).
		Question(department).
		Question(frustration).
		Send()
	if err != nil {
		log.Fatal(err)
	}

	noul, err := result.Get(isUrgent)
	if err != nil {
		log.Fatal(err)
	}
	
	departmentAnswer, err := result.Get(department)
	if err != nil {
		log.Fatal(err)
	}
	
	frustrationAnswer, err := result.Get(frustration)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(noul.Yes)                // 0.95
	fmt.Println(departmentAnswer.Choice) // billing
	fmt.Println(frustrationAnswer.Score) // 1.04
}
```

The example above lives in [`examples/basic`](./examples/basic).

## Questions

A `Question` is one of three types. All three take an id you choose and
`instructions` (a `string`, or a `jev.Value` built with `jev.JSON` for
structured instructions). Answers come back under the same id.

Structured JSON is accepted anywhere the API documents an entry: instructions,
Choice option descriptions, Score levels, and Noul true/false descriptions.
Use `jev.Null()` for an explicitly undescribed entry (it is rejected for state
and instructions).

```go
structured := jev.Noul("is_urgent", jev.MustJSON(map[string]any{
	"question": "Is this time-sensitive?",
	"focus":    "Look for explicit deadlines.",
}))
```

### Noul — yes/no

Returns the probability the answer is yes.

```go
isUrgent := jev.Noul("is_urgent", "Does this convey urgency?").
	True("Explicitly time-sensitive").
	False("No urgency expressed")
```

`True` and `False` are optional descriptions of what a yes and a no mean. Each
may be a string or a structured `jev.Value`:

```go
isUrgent := jev.Noul("is_urgent", "Does this convey urgency?").
	True(jev.MustJSON(map[string]any{
		"what":     "Explicitly time-sensitive",
		"examples": []string{"ASAP", "by end of day"},
	})).
	False("No urgency expressed")
```

### Choice — one of a set

Returns the chosen option and the full probability distribution.

```go
department := jev.Choice("department", "Which team should handle this?").
	Option("billing", "Payments, invoicing, refunds").
	Option("technical", "Bugs, outages, integrations").
	Option("sales", "Pricing, upgrades, new accounts")
```

`Option` takes at most one optional text description (omit it to send `null`).
For a structured description, use `OptionValue`:

```go
department := jev.Choice("department", "Which team should handle this?").
	OptionValue("billing", jev.MustJSON(map[string]any{
		"what":    "Payments, invoicing, refunds",
		"not_for": "Order tracking or account access",
	})).
	Option("technical", "Bugs, outages, integrations").
	Option("sales")
```

Option keys must be unique and each option may carry a single description;
`Send` rejects duplicates and extra descriptions.

### Score — degree along a rubric

Returns a probability-weighted value across ordered levels. At least two levels
are required.

```go
frustration := jev.Score("frustration", "How frustrated is the customer?").
	Level("Calm").
	Level("Frustrated").
	Level("Very angry")
```

Each level may also be a structured `jev.Value`:

```go
prScope := jev.Score("pr_scope", "How focused is this pull request?").
	Level(jev.MustJSON(map[string]any{
		"summary": "One change, clearly stated",
		"signals": []string{"A single fix or feature"},
	})).
	Level("Several independent changes bundled together")
```

## Reading answers

Read each answer with `Result.Get`, which infers the concrete answer type from
the question. The type is tied to the question at compile time, so an answer
can never be read as the wrong type:

```go
type NoulAnswer struct {
	Yes float64 // probability the answer is yes, from 0 to 1
}

type ChoiceAnswer struct {
	Choice        string             // highest-probability option
	Probabilities map[string]float64 // option -> probability, sums to 1
	Confidence    float64            // certainty derived from Probabilities
}

type ScoreAnswer struct {
	Score         float64                 // probability-weighted value across levels
	Legend        map[string]jev.Value    // level number -> description
	Probabilities map[string]float64      // level -> probability, sums to 1
	Confidence    float64
}
```

A legend description may be a string or structured JSON. Use `Value.String()`
for text, `Value.Text()` to test for a string, and `Value.Decode(&out)` for
structured values.

```go
noul, err := result.Get(isUrgent) // NoulAnswer inferred
if err != nil {
	log.Fatal(err)
}

choice, err := result.Get(department)
if err != nil {
	log.Fatal(err)
}

score, err := result.Get(frustration)
if err != nil {
	log.Fatal(err)
}

fmt.Println(noul.Yes)
fmt.Println(choice.Choice, choice.Confidence)
fmt.Println(score.Score, score.Legend["2"].String())
```

`Send` guarantees every requested question is answered, so `Get` cannot fail
for a question and result that came from the same request. A `Result` is bound
to the exact questions that produced it, so reading a question against the
wrong result returns an error rather than a zero value.

Token usage and the model that ran are read through methods:

```go
result.Model()              // "jev-latest" (empty if the server omits it)
result.RequestID()          // "req_..." from x-typesafe-request-id, for support

usage := result.Usage()
usage.Reported              // true when the API included usage
input, ok := usage.Input()   // (426, true); ok is false if not reported
output, _ := usage.Output()  // 73
```

## State

`State` accepts a `string` for plain text, or a `jev.Value` for structured state
such as chat logs, records, or application state. `jev.JSON` encodes eagerly, so
an unmarshalable or nil value is reported immediately:

```go
result, err := client.NewRequest().
	State("Help! My payouts are failing.").
	Question(question).
	Send()

state, err := jev.JSON(map[string]any{
	"document": "I was charged twice. Please fix this ASAP.",
	"tier":     "enterprise",
})
if err != nil {
	log.Fatal(err)
}

result, err = client.NewRequest().
	State(state).
	Question(question).
	Send()
```

A `Value` snapshots its input, so mutating the original map or slice after
building it cannot change the request or race with `Send`. State is required and
must not be blank; an empty or whitespace-only string (or a `Value` that encodes
to `null`) is rejected before any request is sent.

## Client options

`NewClient` requires an API key; every other option has a default.

```go
client, err := jev.NewClient(
	jev.WithAPIKey(os.Getenv("JEV_API_KEY")), // required
	jev.WithModel(jev.ModelLatest),           // default: jev-latest
	jev.WithBaseURL(jev.DefaultBaseURL),      // default: https://api.typesafe.ai
	jev.WithHTTPClient(http.DefaultClient),   // default: 60s timeout
	jev.WithMaxRetries(3),                    // default: 3
	jev.WithRetryWait(500*time.Millisecond),  // default: 500ms; 0 disables waiting
)
```

`jev.ModelLatest` and `jev.ModelPreview` are aliases that move when a new
release ships; pin a versioned id such as `jev-1.13.0` to keep results stable.
The response's `model` reports the versioned id that answered. Override the
model for a single request with `Request.Model`:

```go
result, err := client.NewRequest().
	Model("jev-1.13.0").
	State("Help!").
	Question(question).
	Send()
```

## Models

List the models and aliases available to the account with `Models`. Versioned
ids are accepted by `WithModel` whether or not they appear in the list.

```go
result, err := client.Models(ctx)
if err != nil {
	log.Fatal(err)
}
for _, model := range result.Models() {
	fmt.Println(model.Name, model.ReleaseDate, model.Description)
}
```

## Errors and retries

`Send` retries network errors and retryable statuses (`429`, `529`, and `5xx`)
with exponential backoff and jitter, honoring a `Retry-After` header. Each
logical request carries a stable `Idempotency-Key` that is reused across
retries, so a retried request is not evaluated twice.

Non-2xx responses return an `*APIError`. Branch on the sentinel that matches
the status with `errors.Is`, or inspect the `*APIError` directly:

```go
result, err := client.NewRequest().State(state).Question(question).Send()
if err != nil {
	switch {
	case errors.Is(err, jev.ErrAuth): // 401/403: missing or invalid API key
	case errors.Is(err, jev.ErrInvalidRequest): // 400/422: failed validation
	case errors.Is(err, jev.ErrRateLimit): // 429: rate limit exceeded
	case errors.Is(err, jev.ErrOverloaded): // 529: temporarily overloaded
	}

	var apiErr *jev.APIError
	if errors.As(err, &apiErr) {
		fmt.Println(apiErr.StatusCode, apiErr.Message, apiErr.RequestID, string(apiErr.Body))
		fmt.Println(apiErr.Unauthorized(), apiErr.Unprocessable(), apiErr.Retryable())
	}
}
```

`NewClient` returns `jev.ErrMissingAPIKey` when no API key is configured.
`Send` returns `jev.ErrNilClient`, `jev.ErrNilContext`, or `jev.ErrInvalidValue`
for a nil client, a nil context, or an uninitialized `Value`.

## License

MIT
