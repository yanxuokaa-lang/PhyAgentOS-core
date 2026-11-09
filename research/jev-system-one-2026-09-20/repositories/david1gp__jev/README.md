# @adaptive-ds/jev

Result-based TypeScript client and command-line interface for TypeSafe System One. Send text or structured application
state with named `choice`, `score`, and `noul` questions; receive validated, typed answers, probabilities, confidence,
and token usage.

`jev` is deliberately a Result-based client. Client creation and evaluation return Results instead of throwing or
returning a promise that rejects for ordinary configuration, transport, HTTP, timeout, cancellation, or validation
failures. It is not a promise-rejection-compatible replacement for TypeSafe's official SDK.

## Quick links

- [Install](#install)
- [Library quick start](#library-quick-start)
- [Primitives and public API](#primitives-and-public-api)
- [State, questions, and batches](#state-questions-and-batches)
- [CLI](#cli)
- [Configuration and transport](#configuration-and-transport)
- [Validation and errors](#validation-and-errors)
- [Development and testing](#development-and-testing)
- [TypeSafe documentation](https://docs.typesafe.ai/)
- [API reference](https://docs.typesafe.ai/api.md)
- [GitHub repository](https://github.com/david1gp/jev)

## Install

The package targets Node.js 22+ and Bun 1.4+. The CLI executable is included in the package.

```sh
bun add @adaptive-ds/jev @adaptive-ds/result valibot
```

`@adaptive-ds/result` and `valibot` are peer dependencies and must be installed by library consumers. `@stricli/core`
is installed as the CLI's package dependency.

With npm, install the same packages:

```sh
npm install @adaptive-ds/jev @adaptive-ds/result valibot
```

Run the CLI without a local install with Bun:

```sh
bunx --package @adaptive-ds/jev jev --help
```

## Library quick start

`systemOneClientCreate` returns `Result<SystemOneClient>`. Check `success` before reading `data`; `evaluate` returns a
`PromiseResult<SystemOneResponse>` and follows the same pattern.

```ts
import { choice, systemOneClientCreate } from "@adaptive-ds/jev"

const clientResult = systemOneClientCreate({
  apiKey: process.env.JEV_API_KEY ?? "",
})

if (!clientResult.success) {
  console.error(`${clientResult.op}: ${clientResult.errorMessage}`)
  process.exitCode = 1
} else {
  const responseResult = await clientResult.data.evaluate({
    state: {
      message: "My payout has failed for three days.",
      account_tier: "pro",
    },
    questions: {
      department: choice("Which team should handle this?", {
        billing: "Payments, invoicing, or refunds",
        technical: "Bugs, outages, or integrations",
        sales: "Pricing, upgrades, or new accounts",
      }),
    },
  })

  if (!responseResult.success) {
    console.error(`${responseResult.op}: ${responseResult.errorMessage}`)
    process.exitCode = 1
  } else {
    const answer = responseResult.data.answers.department
    console.log(answer.choice, answer.probabilities, answer.confidence)
    console.log(responseResult.data.usage)
  }
}
```

The transmitted request includes the default model `jev-latest`. Provide `model` on the request to select another model:

```ts
import { noul } from "@adaptive-ds/jev"

const result = await clientResult.data.evaluate({
  state: "A customer message",
  model: "jev-latest",
  questions: { urgent: noul("Does this require urgent handling?") },
})
```

Import `noul` and `score` alongside `choice` when using those question types. TypeScript preserves question names and
criteria in the response, so `answers.department` is a `ChoiceAnswer` in the first example.

## Primitives and public API

### Question helpers

The three runtime question helpers create the exact wire shapes; they do not call the API themselves.

| Helper | Signature and semantics |
| --- | --- |
| `choice` | `choice(instructions, criteria)` returns `{ type: "choice", instructions, criteria }`. `criteria` is a non-empty record of 1–255 named options. Each option description may be a string, structured JSON value, or `null`. |
| `score` | `score(instructions, criteria)` returns `{ type: "score", instructions, criteria }`. `criteria` is an ordered array of 2–10 level descriptions; each may be a string, structured JSON value, or `null`. |
| `noul` | `noul(instructions?, criteria?)` returns `{ type: "noul", instructions }`, optionally with `criteria: { true?, false? }` or `null`; each outcome description may be a string, structured JSON value, or `null`. A request must provide instructions or criteria. It asks a yes/no question and returns the probability of yes. |

`instructions` accepts an `EntryType`: a string, `null`, a JSON-value array, or a string-keyed JSON-value object. The
library also permits omitted instructions, matching the upstream JavaScript SDK, provided a Noul request still has
criteria. `State` accepts a string, JSON-value array, or string-keyed JSON-value object; top-level `null` is rejected by
the upstream HTTP endpoint. A JSON value is a finite number, string, boolean, `null`, array, or recursively nested
string-keyed object.

Answers are validated against the question type:

- `ChoiceAnswer` has `type: "choice"`, the selected `choice`, a `probabilities` record that sums to 1 within `1e-6`,
  and `confidence` in `[0, 1]`. The selected option must have a probability.
- `ScoreAnswer` has `type: "score"`, a non-negative (possibly fractional) probability-weighted `score`, a numeric
  `legend`, matching `probabilities`, and `confidence` in `[0, 1]`. Levels are non-negative integers and the score may
  not exceed the maximum returned level.
- `NoulAnswer` has `type: "noul"`, a number in `[0, 1]`; `0` means no and `1` means yes.

### Client and schemas

The root module exports these runtime helpers and Valibot schemas:

```ts
import {
  answerSchema,
  choice,
  choiceAnswerSchema,
  choiceCriteriaSchema,
  choiceSchema,
  descriptionSchema,
  entryTypeSchema,
  jsonValueSchema,
  noul,
  noulAnswerSchema,
  noulCriteriaSchema,
  noulSchema,
  probabilityDistributionSchema,
  probabilitySchema,
  questionSchema,
  questionsSchema,
  score,
  scoreAnswerSchema,
  scoreCriteriaSchema,
  scoreSchema,
  stateSchema,
  systemOneClientCreate,
  systemOneRequestPayloadSchema,
  systemOneRequestSchema,
  systemOneResponseSchema,
  usageSchema,
} from "@adaptive-ds/jev"
```

The root type exports are `Answer`, `ChoiceAnswer`, `ChoiceCriteria`, `ChoiceQuestion`, `ChoiceResponse`, `Description`,
`EntryType`, `JsonValue`, `NoulAnswer`, `NoulCriteria`, `NoulQuestion`, `NoulResponse`, `Question`, `Questions`,
`ResultFor`, `ScoreAnswer`, `ScoreCriteria`, `ScoreLegend`, `ScoreOf`, `ScoreQuestion`, `ScoreResponse`, `State`,
`SystemOneClient`, `SystemOneClientOptions`, `SystemOneEvaluateOptions`, `SystemOneFetch`, `SystemOneRequest`,
`SystemOneRequestPayload`, `SystemOneResponse`, `SystemOneResult`, and `Usage`.

`ResultFor<Question>` maps a question to its corresponding answer type. `ScoreLegend` and `ScoreOf` are type-only
exports; all names in the import above are runtime values.

## State, questions, and batches

An evaluation request has this shape:

```ts
type SystemOneRequest<Q extends Questions = Questions> = {
  state: State
  questions: Q
  model?: string
}
```

`questions` must be a non-empty record. Name each question yourself; the response returns an answer under the same
name. The library sends all named questions in one HTTP request, which is the way to ask a batch of related questions.
The response contains the model, `answers`, and:

```ts
type Usage = {
  input_tokens: number
  output_tokens: number
}
```

The CLI additionally accepts an array of complete request objects. It evaluates those requests sequentially and returns
an array of responses in the same order. This is a CLI input convenience; it is not one API request containing an array.

## CLI

The available commands are:

```text
jev evaluate   # evaluate one request or an array of requests from JSON
jev choice     # evaluate one choice question
jev score      # evaluate one score question
jev noul       # evaluate one noul question
jev version    # print version information
```

Use `jev --help` or `jev <command> --help` for the generated help. Global `--version` and the `-V` shorthand print the
version.

### Evaluate JSON from a file or stdin

`evaluate` accepts either `--file PATH` or `--input PATH`. Omit the option or use `-` to read stdin. If both are given,
`--file` is used. Input must be non-empty JSON and may be one request or an array of requests:

```sh
export JEV_API_KEY="..."

jev evaluate --file request.json
cat request.json | jev evaluate
cat requests.json | jev evaluate --model jev-latest --timeout 60000
```

`request.json` can contain:

```json
{
  "state": "Help! My payouts have been failing for 3 days.",
  "questions": {
    "is_urgent": {
      "type": "noul",
      "instructions": "Does this convey urgency?",
      "criteria": {
        "true": "Explicitly time-sensitive",
        "false": "No urgency expressed"
      }
    }
  }
}
```

The `evaluate` flags are `--api-key`/`-k`, `--base-url`/`-b`, `--model`/`-m`, `--timeout`/`-t`, `--file`, and
`--input`. `--model` overwrites the `model` property of each object request.

### Primitive commands

Primitive commands receive JSON strings for their JSON-valued flags. Quote them for your shell:

```sh
jev choice \
  --state '"Help! My payouts have been failing for 3 days."' \
  --instructions '"Which team should handle this?"' \
  --criteria '{"billing":"Payments","technical":"Bugs or outages","sales":"Pricing or upgrades"}' \
  --name department

jev score \
  --state '"A very frustrated customer"' \
  --instructions '"How frustrated is the customer?"' \
  --criteria '["Calm","Frustrated","Very angry"]'

jev noul \
  --state '"The payout has failed for three days."' \
  --instructions '"Does this convey urgency?"' \
  --criteria '{"true":"Explicitly time-sensitive","false":"No urgency expressed"}'
```

For `choice` and `score`, `--criteria` and `--instructions` are required. For `noul`, `--criteria` is optional.
`--state` is required for every primitive command. `--name` defaults to `question`. All primitive commands also accept
the common API, model, and timeout flags shown above.

Successful CLI output is compact JSON on stdout. Failures are compact JSON on stderr, set exit status `1`, and contain
`success: false`, `op`, and `errorMessage`; safe underlying `code`, `errorData`, and `statusCode` fields are preserved when
available.

## Configuration and transport

The library requires an explicit API key; it does not read `JEV_API_KEY` itself. The CLI takes `--api-key`/`-k` first
and otherwise reads `JEV_API_KEY`. Keys are sent only as `Authorization: Bearer <api-key>` and are not printed.

Client configuration is passed to `systemOneClientCreate`:

| Option | Default | Behavior |
| --- | --- | --- |
| `apiKey` | required | Non-empty API key. |
| `baseUrl` | `https://api.typesafe.ai/v1/systemone` | Must be an HTTP(S) URL without credentials, query parameters, or a fragment. |
| `fetch` | `globalThis.fetch` | Inject a fetch-compatible function for tests or custom runtimes. |
| `timeoutMs` | `30000` | Per-attempt timeout, from 1 to 300000 ms. |
| `maxRetries` | `2` | Additional attempts for retryable failures, from 0 to 5. |
| `retryDelayMs` | `250` | Initial exponential-backoff delay, from 0 to 60000 ms. |
| `maxRetryDelayMs` | `10000` | Backoff and `Retry-After` cap, from 0 to 60000 ms. |
| `signal` | none | Client-wide `AbortSignal`. |
| `sleep` | internal timer | Inject retry sleep behavior; useful for deterministic tests. |

`evaluate(request, { signal })` also accepts a request-level `AbortSignal`. Client and request signals are both honored.
Timeouts and cancellation return a failed Result and are not retried. Network failures are retried while attempts
remain. HTTP statuses `408`, `425`, `429`, `500`, `502`, `503`, `504`, and `529` are retried; a valid `Retry-After`
header is honored up to `maxRetryDelayMs`. The default backoff doubles from `retryDelayMs` and is capped.

## Validation and errors

The client validates options, requests, JSON serialization, responses, answer names, answer kinds, probability ranges,
and probability totals. A failed Result has `success: false`, an operation name in `op`, and `errorMessage`; it may also
have `errorData`, `code`, or `statusCode` from the underlying Result library. Client creation and evaluation do not
reject their promises for these failures.

Successful API responses must contain a non-empty `answers` record, a string `model`, and non-negative integer
`usage.input_tokens` and `usage.output_tokens`. Returned answer names must exactly match the requested question names,
and each answer type must match its question. Error response text is capped at 2,000 characters and occurrences of the
configured API key are redacted before being placed in error data.

This package validates the boundary; it does not turn model output into a thrown exception. Handle every Result before
using its `data`.

## Development and testing

```sh
bun install
bun run format:check
bun run type-check
bun test
bun run build
```

Useful CLI checks from a checkout:

```sh
bun run src/cli.ts --help
bun run src/cli.ts evaluate --help
bun run src/cli.ts choice --help
bun run src/cli.ts score --help
bun run src/cli.ts noul --help
bun run src/cli.ts version --verbose
```

Transport behavior can be tested without credentials by injecting `fetch` and `sleep` into
`systemOneClientCreate`. Tests should cover request authentication and default model, validation, retryable statuses,
`Retry-After`, timeout, cancellation, response validation, and redaction.

The live integration test is opt-in and reads `JEV_API_KEY` from the process environment; it is skipped otherwise:

```sh
JEV_LIVE=1 bun run test:live
```

## Links and license

- [TypeSafe introduction](https://docs.typesafe.ai/introduction.md)
- [TypeSafe primitives](https://docs.typesafe.ai/primitives.md)
- [TypeSafe API reference](https://docs.typesafe.ai/api.md)
- [TypeSafe JavaScript SDK documentation](https://docs.typesafe.ai/sdk/javascript.md)
- [Source repository](https://github.com/david1gp/jev)
- [Issues](https://github.com/david1gp/jev/issues)

MIT © [David Siewert](https://david-siewert.com/)
