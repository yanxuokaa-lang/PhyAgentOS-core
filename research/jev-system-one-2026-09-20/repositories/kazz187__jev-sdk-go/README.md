# jev-sdk-go

[![CI](https://github.com/kazz187/jev-sdk-go/actions/workflows/ci.yml/badge.svg)](https://github.com/kazz187/jev-sdk-go/actions/workflows/ci.yml)
[![Go Reference](https://pkg.go.dev/badge/github.com/kazz187/jev-sdk-go.svg)](https://pkg.go.dev/github.com/kazz187/jev-sdk-go)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Go client for [TypeSafe AI](https://typesafe.ai)'s System One API and its
model, Jev. Send a state and typed questions; get back typed answers and
probabilities your code can act on directly.

Jev never leaves the set of answers you defined, and tells you how probable
each one was. This package carries that guarantee into the type system: a
choice over your `Team` enum yields a `Team`, the compiler checks the `switch`
you write on it, and a question that could not have been answered is an error
before anything is sent.

It requires **Go 1.27** and is written against it: generic methods make every
call read left to right (`client.Ask(ctx, state, q)`, `batch.Add(name, q)`),
`encoding/json/v2` handles the wire format, and the tests run on the in-memory
`httptest.NewTestServer` under `testing/synctest`, so retry timing is exact
and takes no wall-clock time. No dependencies outside the standard library.

> Unofficial. Defaults for timeouts, retries, and headers match the official
> Python and TypeScript SDKs. Requires an API key from TypeSafe
> (`TYPESAFE_API_KEY`).

```sh
go get github.com/kazz187/jev-sdk-go
```

## Quick start

```go
type Team string

const (
	Billing   Team = "billing"
	Technical Team = "technical"
	Other     Team = "other"
)

// Declare questions once, at package level.
var route = jev.Choice("Which team should handle this ticket?",
	jev.Opt(Billing, "charges, invoices, refunds, subscriptions"),
	jev.Opt(Technical, "bugs, outages, integrations"),
	jev.Opt(Other, nil), // nil when the name speaks for itself
)

client, err := jev.New() // reads TYPESAFE_API_KEY

answer, err := client.Ask(ctx, ticket, route) // answer is jev.ChoiceAnswer[Team]
if err != nil {
	return err
}

switch team, sure := answer.Sure(0.9); {
case !sure:
	return escalate(ticket, answer.Ranked())
case team == Billing:
	return refundQueue(ticket)
default:
	return assign(ticket, team)
}
```

## The three questions

| Constructor | Answer | Use for |
| --- | --- | --- |
| `jev.Noul(q)` / `jev.Noul(q, jev.NoulCriteria{True, False})` | `NoulAnswer{P}` | a two-outcome question; ask one per label when labels can overlap |
| `jev.Choice(q, jev.Opt(v, desc)...)` / `jev.OneOf(q, v...)` | `ChoiceAnswer[T]{Value, Probs, Confidence}` | exactly one of a set you define, returned as your own string type |
| `jev.Score(q, levels...)` | `ScoreAnswer{Value, Probs, Levels, Confidence}` | a degree along ordered levels; the answer can land between them |

`Sure(threshold)` is available on noul and choice answers. `Nearest()` and
`Likeliest()` map a score back to a level. Low confidence is **not** an error:
thresholds are policy and live in your code.

`Confidence` is the API's own field, how peaked the distribution is. It is not
a calibrated probability that the answer is right; use `Probs[Value]` or `P`
for that.

Instructions, option descriptions, score levels, and noul criteria are all
`jev.Content`: a string, or anything that encodes as a JSON object or array.
Reach for structure when a sentence keeps failing to separate two options.

```go
jev.Choice("Which department does this product belong to?",
	jev.Opt(Sporting, map[string]any{
		"Cycling": []string{"Bike Bottles & Cages", "Helmets"},
		"Fitness": []string{"Yoga Mats"},
	}),
	jev.Opt(Drinkware, "Everyday water bottles, travel mugs, tumblers"),
	jev.Opt(Other, nil),
)
```

## Many questions, one request

Independent questions about the same state belong in one batch. They run in
parallel on the model and cost one call. `Add` is a generic method, so each
handle carries the answer type of its question.

```go
b := client.Batch(review)
spam     := b.Add("spam", jev.Noul("Is this review spam or advertising?"))
intent   := b.Add("intent", intentQ)                                 // *jev.Handle[jev.ChoiceAnswer[Intent]]
severity := b.Add("severity", jev.Score("How severe?", "None", "Mild", "Serious"))

resp, err := b.Run(ctx) // resp.Model, resp.Usage, resp.RequestID, resp.Latency, resp.Answers

s, err := spam.Get()     // jev.NoulAnswer
i, err := intent.Get()   // jev.ChoiceAnswer[Intent]
v, err := severity.Get() // jev.ScoreAnswer
```

The names you pass to `Add` are the names on the wire and in
`resp.Answers`, so logs and support tickets read the same as your code. If
one answer does not fit its question, `Run` returns an error wrapping
`jev.ErrMalformedAnswer` along with the response, and the other handles can
still be read.

`b.Model("jev-1.13")` pins a model for one batch. `b.Extra(fields)` adds
top-level request fields this package does not model.

## When the API moves first

`jev.Raw` sends a `Spec` exactly as given and hands the answer back
undecoded. `Spec.Extra` carries question fields this package predates;
`RawAnswer.Extra` keeps answer fields it does not know.

```go
h := b.Add("rank", jev.Raw(jev.Spec{
	Type:         "rank", // a kind this package predates
	Instructions: "Rank these passages by relevance",
	Extra:        map[string]any{"beam_width": 4},
}))
raw, err := h.Get() // jev.RawAnswer; read raw.Extra["order"] yourself
```

## Errors

One sentinel per status the official SDKs distinguish, matched with
`errors.Is`. Rate limits, overload, 408, and 5xx are retried; the rest are
not, because a retry cannot fix them.

| Status | Sentinel | Retried |
| --- | --- | --- |
| 400 | `ErrBadRequest` | no |
| 401 | `ErrAuthentication` | no |
| 403 | `ErrPermissionDenied` | no |
| 404 | `ErrNotFound` | no |
| 408 | – | yes |
| 422 | `ErrUnprocessable` | no |
| 429 | `ErrRateLimit` | yes |
| 529 | `ErrOverloaded`, `ErrInternalServer` | yes |
| other 5xx | `ErrInternalServer` | yes |

Below HTTP: `ErrConnection` for a request that never got a response, and
`ErrTimeout` (which also matches `ErrConnection`) for one that ran out of
time. A 2xx body that does not match the API contract is a `*ResponseError`
matching `ErrInvalidResponse`. Before any request: `ErrInvalidRequest`,
`ErrNoAPIKey`, `ErrInvalidConfig`, `ErrNotRun`, `ErrBatchUsed`.

```go
var apiErr *jev.APIError
if errors.As(err, &apiErr) {
	log.Printf("%d %s request=%s fields=%v", apiErr.StatusCode, apiErr.Message, apiErr.RequestID, apiErr.Fields)
}
```

## Configuration

Explicit options win over environment variables, which win over the
defaults, the same precedence as the official SDKs.

| Option | Environment | Default |
| --- | --- | --- |
| `WithAPIKey` | `TYPESAFE_API_KEY` | required |
| `WithBaseURL` | `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` |
| `WithModel` | `TYPESAFE_DEFAULT_MODEL` | `jev-latest` |
| `WithLogger` | `TYPESAFE_LOG_LEVEL` | no logging |
| `WithTimeout` (per attempt) | | 10s |
| `WithMaxRetries`, `WithRetryPolicy` | | 2 retries, 500ms to 5s backoff with 25% jitter, honors `Retry-After` up to 60s, 30s total budget |
| `WithHeader`, `WithUserAgent`, `WithHTTPClient` | | |
| `WithProvider`, `WithMiddleware` | | |

Once `WithAPIKey` is given, `TYPESAFE_API_KEY` is not read at all, so an
empty key is `ErrNoAPIKey` rather than a silent fall back. The
`*http.Client` you pass is never modified; per-attempt timeouts go through
the request context.

Every request carries `User-Agent`, `X-TypeSafe-SDK`, and
`X-TypeSafe-Runtime`, and retries carry `X-TypeSafe-Retry-Count`, as the
official clients do. Credential headers are redacted from debug logs.

`Provider` and `Middleware` are small interfaces, so metrics, caching, rate
limiting, or an alternative backend can be plugged in without touching call
sites. `Client.Models` lists the account's models through `GET /v1/models`.
To reach Jev through Vercel AI Gateway instead, see the next section.

## Vercel AI Gateway

Jev is also served by [Vercel AI Gateway](https://vercel.com/ai-gateway/models/jev)
as `typesafe-ai/jev`, in the AI SDK's evaluation-model dialect rather than
TypeSafe's. `WithVercelAIGateway` switches the wire format; questions,
answers, batches, errors, and retries are unchanged.

```go
client, err := jev.New(jev.WithVercelAIGateway()) // reads AI_GATEWAY_API_KEY
```

| Option | Environment | Default with the gateway |
| --- | --- | --- |
| `WithAPIKey` | `AI_GATEWAY_API_KEY` | required |
| `WithBaseURL` | | `https://ai-gateway.vercel.sh/v4/ai` |
| `WithModel` | | `typesafe-ai/jev` (`TYPESAFE_DEFAULT_MODEL` is not read; gateway ids differ) |

Noul questions travel as the gateway's `boolean` kind and come back as
`NoulAnswer`. Choice and score confidence is read from the gateway's
`providerMetadata.typesafe.confidence`. `Batch.Extra` fields are sent as
top-level request fields, which is where `providerOptions` goes.
`RequestID` is the `x-vercel-id` header. `Client.Models` is not available
through the gateway (`ErrNoModelList`).

## Testing

`jevtest` is a rule-based fake. A question that matches no rule fails the
request, so a missing rule becomes a test failure instead of a silent "no".

```go
fake := jevtest.New().
	On(jevtest.Instructions("spam"), jevtest.Yes(0.02)).
	On(jevtest.Kind(jev.KindChoice), jevtest.Pick("refund", 0.93)).
	On(jevtest.State("broken"), jevtest.Level(2, 0.8))

client, _ := jev.New(jev.WithProvider(fake))
// ... exercise your code, then inspect fake.Calls()
```

Matchers: `Any`, `Instructions`, `Kind`, `Option`, `State`, `All`, `Not`.
Answers: `Yes`, `Pick`, `Level`, `Fail`.

## What the types do not buy you

A `ChoiceAnswer[Team]` is guaranteed to hold one of your `Team` values.
Nothing here guarantees it holds the right one. Before `Sure(0.9)` is allowed
to decide anything expensive, label a few hundred real inputs, run them
through, and count how often the answers above that line were actually right.
If 0.9 turns out to mean 70% in your domain, the number that needs changing
is in your code, and you can change it without touching a question or paying
for another request.

## License

MIT
