# typesafe-go

[![Go Reference](https://pkg.go.dev/badge/github.com/Shubham510/typesafe-go.svg)](https://pkg.go.dev/github.com/Shubham510/typesafe-go)
[![CI](https://github.com/Shubham510/typesafe-go/actions/workflows/ci.yml/badge.svg)](https://github.com/Shubham510/typesafe-go/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Shubham510/typesafe-go)](https://github.com/Shubham510/typesafe-go/releases/latest)

An **unofficial**, community-maintained Go client for the [TypeSafe AI](https://typesafe.ai) System One API. TypeSafe currently publishes official [Python](https://docs.typesafe.ai/sdk/python) and [JavaScript](https://docs.typesafe.ai/sdk/javascript) SDKs; this package ports the same concepts to idiomatic Go so Go services can call [Jev](https://docs.typesafe.ai/concepts/system-one), TypeSafe's flagship System One model, without a Python/Node sidecar.

This project is **not affiliated with, endorsed by, or supported by TypeSafe AI**. For official documentation, see [docs.typesafe.ai](https://docs.typesafe.ai). File issues against this repository, not TypeSafe's.

**Current release:** [`v1.0.0`](https://github.com/Shubham510/typesafe-go/releases/tag/v1.0.0) (`typesafe.Version`)

Zero third-party dependencies — only the Go standard library.

## Install

```bash
go get github.com/Shubham510/typesafe-go@v1.0.0
```

Or pin any later tag:

```bash
go get github.com/Shubham510/typesafe-go@latest
```

Requires Go 1.27.1 or later (the module's `go` directive; Go's toolchain manager will fetch it automatically if your local `go` is older).

## Quick start

```go
package main

import (
	"context"
	"fmt"
	"log"

	typesafe "github.com/Shubham510/typesafe-go"
)

func main() {
	client, err := typesafe.NewClient() // reads TYPESAFE_API_KEY from the environment
	if err != nil {
		log.Fatal(err)
	}

	resp, err := client.SystemOne(context.Background(), typesafe.SystemOneRequest{
		State: "Help! My payouts have been failing for 3 days.",
		Questions: typesafe.Questions{
			"is_urgent": typesafe.Noul("Does this convey urgency?"),
		},
	})
	if err != nil {
		log.Fatal(err)
	}

	urgent, _ := resp.Noul("is_urgent")
	fmt.Println(urgent.Noul) // probability the message is urgent, 0-1
}
```

See [`examples/`](./examples) for a walkthrough combining all three question types, per-call retry overrides, error handling, and listing models.

## Primitives

TypeSafe's System One models answer three kinds of typed questions instead of generating text. See [docs.typesafe.ai/primitives](https://docs.typesafe.ai/primitives) for the full reference.

| Primitive | Use for | Constructor | Answer |
| --- | --- | --- | --- |
| **Noul** | Yes/no questions | `typesafe.Noul(instructions)` | `NoulAnswer{Noul float64}` — probability of yes |
| **Choice** | Picking one of a defined set | `typesafe.ChoiceStrings(instructions, criteria)` | `ChoiceAnswer{Choice, Probabilities, Confidence}` |
| **Score** | Rating along an ordered rubric | `typesafe.Score(instructions, levels...)` | `ScoreAnswer{Score, Legend, Probabilities, Confidence}` |

```go
resp, err := client.SystemOne(ctx, typesafe.SystemOneRequest{
	State: map[string]any{"ticket": map[string]any{"message": "I was charged twice. Please refund it."}},
	Questions: typesafe.Questions{
		"urgent": typesafe.Noul("Does `ticket.message` convey urgency?"),
		"topic": typesafe.ChoiceStrings("Which team should handle `ticket.message`?", map[string]string{
			"billing":   "Payments, invoicing, refunds",
			"technical": "Bugs, outages, integrations",
		}),
		"frustration": typesafe.Score("How frustrated does the customer sound?",
			"Calm", "Frustrated but civil", "Very angry"),
	},
})
if err != nil {
	log.Fatal(err)
}

topic, _ := resp.Choice("topic")
fmt.Println(topic.Choice, topic.Confidence)
```

Ask several independent questions about the same `State` in one call — they run in parallel server-side and cost input tokens once. See [Speculative fan-out](https://docs.typesafe.ai/patterns/fan-out).

Both `Instructions` and `Choice`/`Noul` criteria accept structured JSON (not just strings) for cases where prose is ambiguous; construct the `NoulQuestion` / `ChoiceQuestion` / `ScoreQuestion` structs directly for that. See [Advanced: structure](https://docs.typesafe.ai/primitives/advanced).

## Configuration

`NewClient` reads from `Option`s first, then environment variables, then SDK defaults:

| Env var | Option | Default |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | `WithAPIKey` | *(required)* |
| `TYPESAFE_BASE_URL` | `WithBaseURL` | `https://api.typesafe.ai` |
| `TYPESAFE_DEFAULT_MODEL` | `WithDefaultModel` | `jev-latest` |
| `TYPESAFE_LOG_LEVEL` | `WithLogLevel` | `warn` (`off`, `error`, `warn`, `info`, `debug`) |
| — | `WithTimeout` | `10s` per attempt |
| — | `WithRetryPolicy` | see below |
| — | `WithHTTPClient` | `&http.Client{}` |
| — | `WithHeader` | — |
| — | `WithLogger` | no-op |

```go
client, err := typesafe.NewClient(
	typesafe.WithAPIKey("sk-..."),
	typesafe.WithDefaultModel("jev-preview"),
	typesafe.WithTimeout(15 * time.Second),
)
```

## Retries

`DefaultRetryPolicy()` matches the official SDKs: 2 retries, exponential backoff from 500ms up to 5s with 25% jitter, retrying `408`/`429`/`5xx` and connection/timeout errors, honoring `Retry-After` / `retry-after-ms` response headers (capped at 60s), with a 30s total retry budget.

```go
policy := typesafe.DefaultRetryPolicy()
policy.MaxRetries = 5
policy.Timeout = 45 * time.Second

client, _ := typesafe.NewClient(typesafe.WithRetryPolicy(policy))

// Or override for a single call:
resp, err := client.SystemOne(ctx, req, typesafe.WithRequestRetryPolicy(typesafe.RetryPolicy{
	MaxRetries: 1,
	Timeout:    3 * time.Second,
}))
```

## Errors

```go
resp, err := client.SystemOne(ctx, req)
if err != nil {
	var rateLimit *typesafe.RateLimitError
	if errors.As(err, &rateLimit) {
		// rateLimit.RetryAfter, rateLimit.StatusCode, rateLimit.RequestID()
	}

	var apiErr *typesafe.APIError // matches any 4xx/5xx, including the typed ones above
	if errors.As(err, &apiErr) {
		log.Printf("typesafe API error %d: %s", apiErr.StatusCode, apiErr.Status)
	}

	var timeoutErr *typesafe.TimeoutError
	if errors.As(err, &timeoutErr) {
		// exceeded the per-attempt timeout after retries
	}
}
```

| Type | Meaning |
| --- | --- |
| `*BadRequestError` | 400 — malformed request |
| `*AuthenticationError` | 401 — missing/invalid API key |
| `*PermissionDeniedError` | 403 |
| `*NotFoundError` | 404 |
| `*UnprocessableEntityError` | 422 — failed server validation |
| `*RateLimitError` | 429 — has `RetryAfter time.Duration` |
| `*InternalServerError` | 5xx |
| `*APIError` | base type; every error above unwraps to it via `errors.As` |
| `*ConnectionError` | request never reached/received from the server |
| `*TimeoutError` | exceeded the per-attempt timeout |
| `*AbortError` | caller's `context.Context` was cancelled |
| `*ResponseValidationError` | 2xx response with a malformed/missing body |

## Models

```go
resp, err := client.ListModels(ctx)
for _, m := range resp.Models {
	fmt.Println(m.Name, m.Description, m.ReleaseDate)
}
```

## Why no dependencies?

The client is built entirely on `net/http` and `encoding/json`. That keeps it easy to vendor, audit, and drop into services with strict dependency policies — a reasonable default for an SDK, not just this one.

## Publishing a release

Go modules are published by **git tags**, not by uploading to a registry. Once a `vX.Y.Z` tag is on GitHub, anyone can `go get` that version; [pkg.go.dev](https://pkg.go.dev/github.com/Shubham510/typesafe-go) indexes it automatically.

### Cut a new version (maintainers)

1. Update `Version` in [`version.go`](./version.go) and add a section to [`CHANGELOG.md`](./CHANGELOG.md).
2. Commit on `main`:

   ```bash
   git add -A
   git commit -m "Release v1.1.0"
   git push origin main
   ```

3. Create an annotated tag and push it (the `v` prefix is required for Go modules):

   ```bash
   git tag -a v1.1.0 -m "v1.1.0"
   git push origin v1.1.0
   ```

4. Create a GitHub Release from that tag (optional but recommended for release notes):

   ```bash
   gh release create v1.1.0 --title "v1.1.0" --notes-file CHANGELOG.md
   ```

5. (Optional) Nudge the module proxy / pkg.go.dev if the docs page is not up yet:

   ```bash
   GOPROXY=proxy.golang.org go list -m github.com/Shubham510/typesafe-go@v1.1.0
   curl "https://proxy.golang.org/github.com/Shubham510/typesafe-go/@v/v1.1.0.info"
   # then open:
   # https://pkg.go.dev/github.com/Shubham510/typesafe-go@v1.1.0
   ```

### Versioning rules

- Follow [semver](https://semver.org/): `MAJOR.MINOR.PATCH`
- Tags must look like `v1.0.0` (leading `v`)
- Breaking API changes require a new major (`v2.0.0`, …) and usually a new module path (`…/v2`) once you leave `v1`
- Keep `typesafe.Version`, the git tag, and `CHANGELOG.md` in sync

## Contributing

Issues and PRs welcome. Run `go build ./... && go vet ./... && go test ./... -race` before submitting. This repo tracks the official SDKs' documented behavior; if TypeSafe's API changes, please link the doc page you're matching against.

## License

[MIT](./LICENSE)
