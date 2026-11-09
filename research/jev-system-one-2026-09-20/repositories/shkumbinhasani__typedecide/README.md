<h1 align="center">TypeDecide</h1>

<p align="center">
  <strong>Typed decisions from decision models.</strong><br>
  A provider-agnostic TypeScript SDK for models that read state and return typed answers<br>
  with calibrated uncertainty — instead of generating text you have to parse.
</p>

<p align="center">
  <a href="https://github.com/shkumbinhasani/typedecide/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/shkumbinhasani/typedecide/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="status: pre-release" src="https://img.shields.io/badge/status-pre--release-f59e0b">
  <img alt="TypeScript strict" src="https://img.shields.io/badge/TypeScript-strict-3178c6">
  <img alt="runtime" src="https://img.shields.io/badge/runtime-Bun%20%C2%B7%20Node%20%C2%B7%20Edge-111827">
  <img alt="zero dependencies" src="https://img.shields.io/badge/core-0%20dependencies-10b981">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-6366f1">
</p>

> [!WARNING]
> **Not published yet.** None of these packages are on npm — the `bun add` lines below are
> what installation *will* look like. For now, clone the repo and poke at it. The API is
> still moving and the version is `0.1.0` for a reason.

```ts
const ticket = d.object({
  intent: d.choice({
    instruction: "What is the customer's main request?",
    options: { refund: "Wants money back", technical: "Needs help", other: "Neither" },
  }),
  urgent: d.probability({ instruction: "Does the customer communicate urgency?" }),
});

const { data, details } = await evaluate({ model, schema: ticket, state: message });

data.intent;                  // "refund" | "technical" | "other"  — never a parse failure
details.intent.confidence;    // 0.92
details.intent.probabilities; // { refund: 0.92, technical: 0.05, other: 0.03 }
```

- **Schemas that describe decisions**, not JSON shapes — instructions, semantic options, ordered levels.
- **Inference that actually holds.** `d.infer` gives you the union, not `string`.
- **Uncertainty is first class**, and kept out of the way of your business logic.
- **A model is a value**, not a magic string. No global registry, tree-shakeable, edge-safe.
- **Capability-checked at compile time.** A schema a model cannot serve is a type error.
- **Adapters are small.** One versioned IR in, normalized answers out.

Declare the decision once, in a Zod-like schema. TypeDecide compiles it to a
provider-neutral plan, hands that to whichever model you picked, and gives you back typed
values plus the uncertainty behind them.

```ts
import { d, evaluate } from "@typedecide/core";
import { typesafe } from "@typedecide/typesafe";

const ticketDecision = d.object({
  intent: d.choice({
    instruction: "What is the customer's main request?",
    options: {
      refund: "The customer wants money returned",
      technical: "They need technical help",
      information: "They only want information",
      other: "None of the above",
    },
  }),

  urgent: d.probability({
    instruction: "Does the customer communicate urgency?",
  }),

  severity: d.score({
    instruction: "How severe is the issue?",
    levels: ["Minor inconvenience", "Material degradation", "Critical outage"],
  }),
});

type TicketDecision = d.infer<typeof ticketDecision>;

const result = await evaluate({
  model: typesafe("jev-latest", { apiKey: process.env.TYPESAFE_API_KEY }),
  state: { message: "I got charged twice and need this fixed now." },
  schema: ticketDecision,
});

result.data.intent; // "refund" | "technical" | "information" | "other"
result.data.urgent; // number
result.data.severity; // number
```

## How decision models differ from structured output

```
Generative model:

    unstructured input
        ↓
    token generation
        ↓
    parse / validate structured output


Decision model:

    unstructured state
        ↓
    typed decision specification
        ↓
    model evaluation
        ↓
    typed values + uncertainty
```

A generative model writes tokens that you then coerce into a shape. Anything outside that
shape is a parse failure you have to handle. A decision model never generates the value in
the first place: it scores the options you declared and returns a distribution over them.
The answer is inside your type by construction, and the uncertainty is a first-class part
of the response rather than something you infer from logprobs.

This is why TypeDecide is not built on Standard Schema. Standard Schema describes
`input → validation → value | issues`. A decision schema carries instructions, semantic
option descriptions, ordered levels, and required model capabilities. Those are not
validation concerns. You can still use Zod to validate the state you feed in, or the
result you persist — it just does not define the core abstraction here.

Providers are not interchangeable in their semantics. TypeDecide normalizes what is
genuinely common and leaves the rest under `providerMetadata`.

## Install

> [!NOTE]
> Not on npm yet. This is the intended shape, not a working command.

```sh
bun add @typedecide/core @typedecide/typesafe
bun add @typedecide/openrouter   # optional, reach Jev through OpenRouter instead
bun add -d @typedecide/test-utils
```

Until then:

```sh
git clone https://github.com/shkumbinhasani/typedecide
cd typedecide && bun install && bun run check
```

| Package | Contents |
| --- | --- |
| `@typedecide/core` | schema DSL, IR, model protocol, `evaluate`, errors |
| `@typedecide/typesafe` | TypeSafe (Jev) adapter, first-party API |
| `@typedecide/openrouter` | OpenRouter adapter, reaching decision models through its decisions router |
| `@typedecide/test-utils` | mock decision model |

`@typedecide/core` has no dependencies and mentions no provider.

## Schema primitives

### `d.choice`

One option from a set you define. `options` maps the value your code receives to the
description the model reads.

```ts
d.choice({
  instruction: "What category does this belong to?",
  options: {
    safe: "No meaningful concern",
    suspicious: "Potential concern",
    unsafe: "Clear concern",
  },
});
// -> "safe" | "suspicious" | "unsafe"
```

### `d.probability`

A single claim, answered as a calibrated probability between 0 and 1.

```ts
d.probability({ instruction: "Is this request malicious?" });
// -> number
```

### `d.score`

A position on an ordered rubric. `levels` runs from the bottom of the scale upwards, and
the result is a fractional index between `0` and `levels.length - 1`.

```ts
d.score({
  instruction: "How severe is the issue?",
  levels: ["Minor inconvenience", "Material degradation", "Critical outage"],
});
// -> number, where 1.6 sits between "Material degradation" and "Critical outage"
```

A score is a position, not a category. Two different distributions can produce the same
number, so read `probabilities` alongside it when the distinction matters.

### `d.object`

Composes the rest, and nests freely.

```ts
const schema = d.object({
  intent: d.choice({ /* ... */ }),
  risk: d.object({
    malicious: d.probability({ instruction: "Malicious?" }),
  }),
});
// -> { intent: ...; risk: { malicious: number } }
```

### Structured instructions

`instruction`, option descriptions, and score levels each accept any JSON value, not just
a string. Use that when the supporting data is already structured.

```ts
d.choice({
  instruction: { question: "Which team?", focus: ["billing", "support"] },
  options: {
    billing: { what: "payments and refunds", examples: ["double charge"] },
    technical: { what: "bugs and outages", not_for: "pricing questions" },
  },
});
```

## Inference

```ts
type Decision = d.infer<typeof schema>; // the clean values
type Detail = d.details<typeof schema>; // the uncertainty
type Caps = d.capabilities<typeof schema>; // "choice" | "probability" | "score"
```

## Results and details

Application code reads `result.data`. It holds nothing but values.

```ts
result.data.intent; // "refund"
result.data.urgent; // 0.91
result.data.severity; // 1.6
```

`result.details` mirrors the same shape and holds the uncertainty, so a routing function
never has to reach past `.value` to get at a decision.

```ts
result.details.intent.confidence; // 0.92 | undefined
result.details.intent.probabilities; // { refund: 0.92, technical: 0.03, ... }

result.details.severity.level; // 2  (nearest level index)
result.details.severity.levels; // ["Minor inconvenience", ...]
result.details.severity.probabilities; // [0.05, 0.3, 0.65]
```

`confidence` is `number | undefined` on purpose. Not every provider reports one for every
primitive — TypeSafe does not report confidence for a probability answer — and inventing a
number there would be dishonest. The distribution is always present, so compute your own
statistic when you need one.

Nor is `confidence` a portable quantity. TypeSafe documents it as a statistic over the
distribution but does not publish the formula, and a future provider may define it
differently. Tune a confidence threshold against the provider you actually ship, and treat
the value in `data` as the part that carries across.

The rest of the result:

```ts
result.provider; // "typesafe"
result.model; // "jev-latest"      — what you asked for
result.resolvedModel; // "jev-1.13.0"      — what actually answered; log this
result.usage; // { inputTokens, outputTokens, totalTokens }
result.providerMetadata; // { typesafe: { requestId, answers, ... } }
result.plan; // the compiled IR that was sent
```

## A shorter form: `@typedecide/core/ask`

For code that asks a few questions about one piece of state, the schema is often the only
ceremony. `createAsk` binds a model, and binding state gives you a function that asks:

```ts
import { createAsk } from "@typedecide/core/ask";

const about = createAsk(model)(ticket);

const [urgent, team, severity] = await Promise.all([
  about("Does the customer communicate urgency?"),
  about("Which team should handle this?").oneOf({
    billing: "Payments, invoicing, refunds",
    technical: "Bugs, outages, integrations",
  }),
  about("How severe is it?").rank(["Minor", "Material", "Critical"]),
]);
```

A bare question is a probability. `.oneOf` is a choice — an array when the option names
speak for themselves, a record when they need a rubric. `.rank` is an ordered score. The
types follow: `team` is `"billing" | "technical"`, the other two are `number`.

**Questions asked in the same tick become one request.** Those three share a state, so they
compile to a single plan and a single call. Two sequential `await`s are two ticks and cost
two requests — this is the one thing to know:

```ts
await about("A?");            // request 1
await about("B?");            // request 2 — different tick

await Promise.all([about("A?"), about("B?")]);   // one request
```

### Confidence

The answer is a real primitive, so `===` and `switch` behave. Uncertainty hangs off the
question handle instead:

```ts
const tone = about("What is the tone?").oneOf(["calm", "annoyed", "furious"]);

await tone;           // "annoyed"
await tone.details;   // { kind: "choice", confidence: 0.67, probabilities: { … } }
```

Both reads share one request. Usually you do not want the number though, you want to know
whether to trust the answer — `.atLeast` puts that in the type:

```ts
const refund = await about("Is the customer asking for a refund?")
  .oneOf(["yes", "no"])
  .atLeast(0.8);
// "yes" | "no" | null

if (refund === null) sendToHumanReview();
```

The `| null` is the point: you cannot skip the check without TypeScript noticing. A bare
probability has no `.atLeast`, because no provider reports confidence for one.

### What it will not do

- **A batch shares fate.** One request means one failure — a malformed question rejects
  every question sent with it. Question keys are derived from the question text, so a
  provider error names the one at fault.
- **A handle is `PromiseLike`, not `Promise`.** It has to be lazy so `.oneOf` can refine it
  before anything is sent. `await` works, `Promise.all` works; anything demanding a real
  `Promise` needs `Promise.resolve(handle)`.
- **A handle never awaited never fires**, which is usually what you want from a lazy value
  but means a forgotten `await` is silent.
- **No nesting, no `providerOptions`, no `signal`.** Reach for `evaluate` when you need
  those; nothing about the schema or the result changes.


## State

State is any JSON value: a string, an object, or an array.

```ts
await evaluate({
  model,
  schema,
  state: {
    user: { plan: "enterprise", tenureMonths: 14 },
    message: "I got charged twice.",
    order: { id: "ord_1", total: 149 },
  },
});
```

Keep facts in the state and judgments in the schema. The adapter decides how to serialize
it for its provider.

## Architecture

```
schema DSL            d.object({ ... })
    ↓
compileSchema()
    ↓
DecisionPlanV1        provider-neutral, versioned
    ↓
model adapter         typesafe("jev-latest")
    ↓
provider request      POST /v1/systemone
    ↓
provider response
    ↓
normalized result     NormalizedAnswer per question
    ↓
typed result          result.data / result.details
```

`DecisionPlanV1` is the important boundary. Adapters never see a schema object, only the
plan, so the DSL can grow without breaking adapters and adapters cannot come to depend on
DSL internals. It is versioned from the first release.

Nested schemas flatten into dotted question keys (`risk.malicious`) in the plan, and
`evaluate` rebuilds the nesting on the way back. Field names may not contain a `.`.

## Models are objects

A model is a value you construct, not a pair of strings you pass around.

```ts
const model = typesafe("jev-latest", { apiKey });
await evaluate({ model, schema, state });
```

The model carries its provider, its id, its capabilities, and its provider-option types.
There is no global registry to populate and no initialization order to get right, which
keeps the library tree-shakeable and predictable on edge runtimes.

## Capabilities

Every primitive declares what it needs; an object schema requires the union of its
children. Every model declares what it supports. `evaluate` refuses the mismatch at
compile time.

```ts
const schema = d.object({
  category: d.choice({ /* ... */ }), // requires "choice"
  risk: d.probability({ /* ... */ }), // requires "probability"
});

const limited = someProvider("probability-only-model");

await evaluate({
  model: limited, // Type error: missing capability "choice"
  schema,
  state,
});
```

The same check runs at runtime, because JavaScript callers and widened types exist. It
throws `UnsupportedCapabilityError` naming exactly what is missing.

## Errors

All failures are subclasses of `DecisionError` with a discriminated `code`.

| Class | `code` |
| --- | --- |
| `AuthenticationError` | `authentication` |
| `RateLimitError` | `rate_limit` |
| `TimeoutError` | `timeout` |
| `InvalidRequestError` | `invalid_request` |
| `UnsupportedCapabilityError` | `unsupported_capability` |
| `ProviderError` | `provider` |

```ts
import { isDecisionError } from "@typedecide/core";

try {
  await evaluate({ model, schema, state });
} catch (error) {
  if (!isDecisionError(error)) throw error;

  switch (error.code) {
    case "rate_limit":
      await wait(error.retryAfterMs ?? 1000);
      break;
    case "unsupported_capability":
      console.error(error.capabilities);
      break;
    default:
      console.error(error.provider, error.model, error.status, error.cause);
  }
}
```

Each error keeps `provider`, `model`, `status`, `retryable`, `cause`, and the original
provider payload under `providerMetadata`.

## Testing

`mockDecisionModel` implements the same model interface, so nothing else in your code
changes.

```ts
import { mockDecisionModel } from "@typedecide/test-utils";

const model = mockDecisionModel({
  result: { intent: "refund", urgent: 0.9 },
});

const result = await evaluate({ model, schema, state });
expect(route(result.data)).toBe("billing-escalation");
```

Fields you omit get deterministic defaults — the first option, `0.5`, level `0`. Pass a
handler when the answer depends on the input:

```ts
mockDecisionModel({
  evaluate({ state, plan }) {
    return { result: { intent: inspect(state), urgent: 0.75 } };
  },
});
```

The mock records every call as `model.calls`, enforces whatever `capabilities` you declare,
and accepts fully specified `answers` when you need an exact distribution.

## Writing a provider adapter

`createDecisionProvider` handles the model object, capability validation, and metadata
namespacing. You write the translation and the transport.

```ts
import { createDecisionProvider } from "@typedecide/core";

export const acme = createDecisionProvider({
  id: "acme",

  models: {
    "model-v1": { capabilities: { choice: true, probability: true } },
  },

  fallbackModel: { capabilities: { choice: true, probability: true } },

  async execute({ modelId, plan, state, settings, providerOptions, signal }) {
    const response = await fetch("https://api.acme.dev/decide", {
      method: "POST",
      headers: { authorization: `Bearer ${settings?.apiKey}` },
      body: JSON.stringify({ model: modelId, state, plan }),
      signal,
    });

    const body = await response.json();

    return {
      answers: normalize(body),
      model: body.model,
      usage: { inputTokens: body.usage.input },
      providerMetadata: { requestId: body.id },
    };
  },
});
```

`execute` returns one `NormalizedAnswer` per plan question key:

```ts
{ kind: "choice", option: string, probabilities: Record<string, number>, confidence?: number }
{ kind: "probability", probability: number, confidence?: number }
{ kind: "score", score: number, probabilities: number[], confidence?: number }
```

Core validates that each answer matches the question it belongs to, rejects an option the
schema never declared, fills omitted probabilities with zero, and namespaces your metadata
under your provider id. The adapter protocol is versioned as `specificationVersion: "v1"`.

Pass `fallbackModel` when users should be able to pin model versions you do not enumerate.

### Provider-specific primitives

A provider can add a primitive of its own without any change to core. Build it on
`d.extension` and give it a namespaced capability:

```ts
// @typedecide/acme
import { d } from "@typedecide/core";

export const pairwise = (config: { instruction: string; pair: [string, string] }) =>
  d.extension<"left" | "right", { margin: number }, "acme:pairwise", { pair: string[] }>({
    capability: "acme:pairwise",
    instruction: config.instruction,
    payload: { pair: config.pair },
  });
```

It composes with the built-in primitives, and only models declaring `"acme:pairwise"` will
type-check against a schema that uses it.

## TypeSafe (Jev) adapter

```ts
import { typesafe } from "@typedecide/typesafe";

const model = typesafe("jev-latest", {
  apiKey: process.env.TYPESAFE_API_KEY,
  baseURL: "https://api.typesafe.ai",
  timeout: 10_000,
  maxRetries: 2,
  headers: { "x-team": "support" },
  fetch: customFetch,
});
```

`apiKey` falls back to `TYPESAFE_API_KEY` and `baseURL` to `TYPESAFE_BASE_URL`.
`jev-latest` and `jev-preview` are known ids; pinned versions such as `jev-1.13.0` are
accepted too, which TypeSafe recommends once you tune on confidence thresholds.

The mapping lives entirely inside the adapter:

| TypeDecide | Jev |
| --- | --- |
| `d.choice` | Choice |
| `d.probability` | Noul |
| `d.score` | Score |

Retries use exponential backoff on 429 and 5xx, honouring `retry-after`.

### Where Jev forced a compromise

- **A probability answer has no confidence.** Jev returns `{ noul }` and nothing else, so
  `details.<field>.confidence` is `undefined` there. Deriving one from the probability
  would look like model output without being it. `probabilities` is restated as
  `{ true: p, false: 1 - p }`, which is arithmetic rather than an extra claim.
- **Confidence is not a published formula.** TypeSafe documents it as a statistic over the
  distribution but does not disclose the computation, and does not promise stability across
  providers. Compare confidences within one provider, not across them.
- **A score is a fractional index, not a level.** `data.<field>` is the raw position; we add
  `details.<field>.level` as the rounded index for code that needs a discrete outcome.
- **Provider limits are enforced in the adapter, not in core.** Jev caps choices at 255 and
  scores at 2–10 levels. Core stays permissive and the adapter raises
  `InvalidRequestError` before the request goes out. A provider with different limits does
  not inherit Jev's.
- **Questions are independent.** Jev evaluates every question in isolation against the same
  state, so a schema cannot express one field depending on another's answer. Chain two
  `evaluate` calls for that.
- **Zero Data Retention and no-training flags are undocumented on the wire.** Rather than
  guess the field names, pass them through `providerOptions.body`, an explicit raw escape
  hatch that cannot overwrite `model`, `state`, or `questions`.

## OpenRouter adapter

OpenRouter routes decision models through a separate endpoint,
`POST https://openrouter.ai/api/alpha/decisions`. Use this adapter instead of
`@typedecide/typesafe` when you want one key and one bill across vendors.

```ts
import { openrouter } from "@typedecide/openrouter";

const model = openrouter("~typesafe/jev-latest", {
  apiKey: process.env.OPENROUTER_API_KEY,
  appTitle: "my-app",
});
```

`apiKey` falls back to `OPENROUTER_API_KEY`. Known ids are `~typesafe/jev-latest` (rolling —
the tilde is part of the id) and pinned versions such as `typesafe/jev-1.13`. Any other id
passes straight through, so a new decision model works without an adapter release.

`baseURL` is an origin, defaulting to `https://openrouter.ai`. It is not the `…/api/v1` base
you would use for chat: the decisions endpoint sits outside `/v1`, which is also why the
adapter ignores `OPENROUTER_BASE_URL`.

The adapter sends everything to the decisions endpoint and lets the router reject whatever
is not a decision model, rather than keeping an allowlist that would go stale.

`providerMetadata.openrouter` carries the dialect, the resolved model, the upstream
provider, the generation id, the reported `cost`, and the raw answers.

### Dialects

The request envelope — `{ model, state, questions }` in, `{ model, answers, usage }` out —
belongs to OpenRouter. What sits *inside* `questions` belongs to the model. Today every
decision model there is TypeSafe's, so the default **`jevDialect`** speaks noul/choice/score
and enforces Jev's limits.

A model with different primitives needs a different dialect, not a different adapter:

```ts
import type { DecisionsDialect } from "@typedecide/openrouter";
import { openrouter } from "@typedecide/openrouter";

const acmeDialect: DecisionsDialect<AcmeQuestion, AcmeAnswer> = {
  id: "acme",
  capabilities: { choice: true },
  compileQuestion: (question, { key, model }) => ({ ... }),
  normalizeAnswer: (answer, { key, plan }) => ({ kind: "choice", ... }),
};

const model = openrouter("acme/decider-v1", { dialect: acmeDialect });
```

A dialect declares the capabilities it can actually serve, and the adapter checks the plan
against them **before** sending anything. The dialect above supports only `choice`, so a
schema containing a `d.probability` fails with `UnsupportedCapabilityError` naming the
dialect, rather than a confusing error from the router.

The model id selects the dialect at compile time, through overloads on the factory:

```ts
openrouter("~typesafe/jev-latest");                      // ok, jevDialect implied
openrouter("typesafe/jev-1.14");                         // ok, an unreleased version
openrouter("acme/decider-v1");                           // Type error: dialect required
openrouter("acme/decider-v1", { dialect: acmeDialect }); // ok
```

The Jev overload matches a model *family* — `` `typesafe/jev-${string}` `` and its `~`
counterpart — not a fixed list, so a pinned version that ships tomorrow keeps working
without an adapter release. Anything outside that family has to say which dialect it speaks,
because assuming Jev's format for an unrelated vendor is exactly the bug this prevents.

The dialect's capabilities become the model's, so the check reaches `evaluate`:

```ts
const acme = openrouter("acme/decider-v1", { dialect: acmeDialect }); // { choice: true }

await evaluate({
  model: acme,        // Type error: missing capability "probability"
  schema: d.object({ urgent: d.probability({ instruction: "Urgent?" }) }),
  state,
});
```

This mirrors how TanStack AI handles one provider with several wire formats: a model-id
union per format, and factory overloads that pick the right one.

### Which adapter

Both reach the same model. `@typedecide/typesafe` talks to TypeSafe directly and exposes
first-party details such as the `x-typesafe-request-id` header. `@typedecide/openrouter`
adds OpenRouter's routing, billing and generation ids. Swapping between them changes one
line, because the schema, the plan and the result shape do not move.

## Development

```sh
bun install
bun run typecheck   # includes the type-level tests
bun test
bun run build
bun run smoke       # imports the built dist under plain Node
bun run check       # all four
```

CI runs the same commands on every push and pull request, plus two things worth having in a
library: the built output is imported under Node 20, 22 and 24, and every package is checked
with [publint](https://publint.dev) and [`@arethetypeswrong/cli`](https://arethetypeswrong.github.io)
so a broken `exports` map or a mistyped subpath fails the build rather than a user's install.

Inference behaviour is covered by type-level tests in
`packages/core/tests/types.test-d.ts`, including `@ts-expect-error` assertions proving that
an incompatible schema and model fail to compile.

## Status

Pre-release, and honest about it:

- The three core primitives, the IR, the adapter protocol and both adapters work, and are
  covered by 103 tests plus type-level tests for the inference that matters.
- The TypeSafe and OpenRouter adapters are exercised against the live API, not just mocks.
- `@typedecide/core/ask` is newer than the rest and the most likely to move.
- Nothing is published, and there is no release pipeline yet — publishing stays a deliberate
  manual step until the API settles.
- `DecisionPlanV1` is versioned from day one, so the IR is the part least likely to break
  under you.

## License

MIT
