# EDcheck

Semantic validation for [Zod](https://zod.dev) schemas, powered by [TypeSafe Jev](https://docs.typesafe.ai/introduction).
Validate meaning, not just structure.

> **v0.1.0.** Server-only semantic validation for Zod 4. See [CHANGELOG.md](CHANGELOG.md).

## The idea

Zod tells you `"asdfasdf"` is a valid 8-character string. EDcheck tells you it is not a person's name.

| Layer    | Owns                                            | Runs                              |
| -------- | ----------------------------------------------- | --------------------------------- |
| Zod 4    | shape: types, `min`, `max`, `regex`, `refine`   | client + server                   |
| EDcheck  | meaning: plausibility, coherence, relevance     | **server only**                   |
| Jev      | calibrated yes/no probabilities                 | TypeSafe API or Vercel AI Gateway |
| Your app | thresholds, severity, when to validate, secrets | your code                         |

EDcheck does not wrap or re-export Zod. Your existing schema stays the schema. Semantic rules are
attached on the server, compiled into atomic Jev questions, batched into **one request per object**,
and mapped to `pass | warning | fail`.

## Install

Requires Node ≥ 20. Zod is a peer dependency.

```sh
yarn add @edteam/edcheck zod
```

## Client: keep the Zod schema

```ts
// shared/user.ts — plain Zod, safe to import in the browser
import { z } from "zod";

export const User = z.object({
  fullName: z.string().min(2).max(100),
  bio: z.string().min(10).optional(),
});
```

## Server: bind rules and parse

EDcheck must run on the server (your API route). Calling `createEDcheck` or `safeParse` in a
browser throws `EDcheckEnvironmentError`.

```ts
import { createEDcheck, semantic, typesafeProvider } from "@edteam/edcheck";

import { User } from "../shared/user";

const edcheck = createEDcheck({
  provider: typesafeProvider({ apiKey: process.env.TYPESAFE_API_KEY! }),
});

const UserSemantic = edcheck.define(User, {
  rules: {
    fullName: semantic("A plausible full name for a real person"),
    bio: semantic({
      intent: "Meaningful professional biography",
      valid: "Describes the person's professional background coherently",
      invalid: "Meaningless, irrelevant or clearly unrelated text",
      severity: "warning",
    }),
  },
});

export async function POST(request: Request): Promise<Response> {
  const input = await request.json();
  const result = await UserSemantic.safeParse(input, { signal: request.signal });
  return Response.json(result);
}
```

`result.success` is `false` only when an issue has `severity: "error"`. `result.issues` is one
array: Zod issues first, then semantic issues. When shape passed, `result.data` is `z.output` of
the schema even if a semantic rule failed.

## Thresholds

`DEFAULT_THRESHOLDS` is `{ pass: 0.7, fail: 0.7 }`, derived from
`test/eval/baseline.json` (`jev-1.13.0`, `2026-09-18T03:42:43.213Z`). The
warning band is collapsed: `p ≥ 0.7` passes and `p < 0.7` fails. Override on
the instance, schema or rule to restore a warning range. Provenance and the
recalibration loop live in [`docs/calibration.md`](docs/calibration.md).

- `p ≥ pass` → pass (no issue)
- `fail ≤ p < pass` → warning
- `p < fail` → fail

Precedence: rule > schema > instance > defaults.

Run evaluations (skipped without a key) with `yarn eval`. To refresh the
baseline: `EDCHECK_WRITE_BASELINE=1 yarn eval`.

## Score rules

Use a Noul rule when the question is yes/no. Use a Score rule when the value sits on an ordered
scale and each level should map to its own outcome:

```ts
semantic({
  kind: "score",
  intent: "How well does the description explain the software project?",
  levels: [
    { label: "meaningless", description: "Random, spam-like or unrelated text", outcome: "fail" },
    { label: "vague", description: "On topic but too vague to act on", outcome: "warning" },
    {
      label: "clear",
      description: "Explains what to build or which problem to solve",
      outcome: "pass",
    },
  ],
});
```

The winning level is the highest probability (ties take the lowest index). If `confidence` is
below `minConfidence`, the outcome becomes `warning` even when that level was a pass or a fail.

`minConfidence` precedence is rule > schema > instance > `DEFAULT_MIN_CONFIDENCE` (`0.6`,
provisional until `evaluation-harness` calibrates it). Score issues carry `score`, `confidence`,
`level` and `minConfidence`; they never carry `probability` or `thresholds`.

## Failure policy

If the provider is down, times out, or returns a malformed response:

- `open` (default): one `semantic_unavailable` **warning** per surviving rule. `success` is unchanged.
- `closed`: the same issues with `severity: "error"`.

```ts
createEDcheck({ provider, policy: "closed", timeoutMs: 8000 });
```

## Context

Context is meaning for Jev, not a prompt. It travels only in `state.context` and never in
`instructions` or `criteria`.

A context is a non-empty string or an object. A string becomes `{ notes: [that string] }`. The
object may use reserved keys `domain`, `purpose`, `audience`, `locale`, `channel` (strings),
`notes: string[]`, and any open keys your app needs (`tenant`, `plan`, …).

Attach it at four levels. More specific wins; `notes` accumulate:

```ts
const edcheck = createEDcheck({
  provider,
  context: { domain: "software services", locale: "es-BO" },
});

const Project = edcheck.define(schema, {
  context: { purpose: "create_project", audience: "client" },
  nodeContext: {
    address: { channel: "web" },
  },
  rules: {
    fullName: semantic({
      intent: "A plausible full name for a real person",
      context: "As written on the ID",
    }),
  },
});
```

Merge rules:

- Levels apply in order: instance → schema → node ancestors (root first) → rule.
- Structured keys shallow-merge; the most specific level wins.
- `notes` concatenate in that same order and never override a structured key.
- `{}` is a no-op: `state` has no `context` key.

Identical effective context stays **one request**. Distinct rule (or node) contexts split into
one request per group, each with only that group's fields. `locale` is data for the model, not a
filter — it does not change instructions, criteria, or which rules run. The top-level state key
`context` is reserved; a rule or `nodeContext` path starting with `context` is rejected.

## Cross-field rules

A field rule judges one value. Cross-field rules judge several declared paths together and still
ride in the same provider request:

```ts
const PersonSemantic = edcheck.define(Person, {
  rules: { fullName: semantic("A plausible full name for a real person") },
  crossField: [
    {
      paths: ["age", "occupation"],
      rule: semantic({
        intent: "The `occupation` is plausible for someone of the given `age`",
        invalid: "The `occupation` requires more years than the `age` allows",
        id: "occupation_age_coherence",
      }),
    },
  ],
});
```

Backticked path-like tokens in `intent`, `valid` and `invalid` must be declared paths. An
undeclared reference such as `` `salary` `` is `EDcheckConfigError` with code `unknown_reference`.
Tokens with spaces or punctuation (`` `N/A` ``) are ignored.

A warning or fail emits **one issue per declared path**, identical except for `path`. Every issue
carries `paths` (all declared paths) and the same `ruleId` so forms can place the error and code
can deduplicate. `undefined`/`null` on any declared path skips the rule without an issue. Arrays
are out of v1: a declared path on or through `z.array` is rejected at `define`.

## Cancellation

Every `safeParse` accepts `signal` and `timeoutMs`. A cancelled parse rejects with
`EDcheckAbortError` and never emits a result. Timeout is a provider failure, not a cancellation.

## Validate one field

`bound.node("fullName")` returns a memoized handle for on-blur style checks. It runs the same
rules, context and outcome mapping as a whole-object parse, restricted to that path. Cross-field
rules run on submit unless every declared path sits under the node; inspect `node.ruleIds` to see
coverage.

```ts
const FullName = bound.node("fullName");

async function onBlur(value: string) {
  const controller = new AbortController();
  const result = await FullName.safeParse(value, { signal: controller.signal });
  return result;
}
```

A new keystroke should abort the previous controller. The library does not supersede in-flight
calls: a shared server instance must not cancel another request's work.

## Providers

| Route              | When to use                       | Install                       | Auth                                |
| ------------------ | --------------------------------- | ----------------------------- | ----------------------------------- |
| `typesafeProvider` | Direct TypeSafe API               | none beyond `edcheck`         | `TYPESAFE_API_KEY`                  |
| `gatewayProvider`  | Vercel AI Gateway (billing, OIDC) | `yarn add ai @ai-sdk/gateway` | `AI_GATEWAY_API_KEY` or Vercel OIDC |

`ai` and `@ai-sdk/gateway` are optional peers. They load on the first `evaluate` via a dynamic
`import()`. A TypeSafe-direct install never pulls them in.

On Vercel, omit `apiKey` and Gateway resolves OIDC itself:

```ts
import { createEDcheck, gatewayProvider, providerFromEnv, semantic } from "@edteam/edcheck";

const viaGateway = createEDcheck({
  provider: gatewayProvider(), // AI_GATEWAY_API_KEY or OIDC
});

const viaEnv = createEDcheck({
  provider: providerFromEnv(), // TYPESAFE_API_KEY wins if both are set
});
```

`providerFromEnv({ prefer?: "typesafe" | "gateway" })` reads the environment at call time.
Default preference is `"typesafe"` so a dual-key setup stays on the route that needs no optional
peer. Empty strings count as unset.

## Observability

`createEDcheck({ hooks })` accepts optional `onRequest`, `onResponse` and `onError` callbacks.
Each fires exactly once per provider request. A parse that makes no request fires nothing. EDcheck
never writes to stdout, stderr or `console`.

| Field                           | Meaning                                                       |
| ------------------------------- | ------------------------------------------------------------- |
| `parseId`                       | One id per `safeParse` call                                   |
| `requestId`                     | One id per provider request (use as a span id)                |
| `requestIndex` / `requestCount` | Group position and how many requests this parse planned       |
| `provider`                      | `provider.name`                                               |
| `entry`                         | `"object"` (or `"node"` when node validation is used)         |
| `ruleIds`                       | Question ids in this request                                  |
| `durationMs`                    | Provider latency for the terminal event                       |
| `outcomes`                      | `pass` / `warning` / `fail` per rule, before severity mapping |
| `kind`                          | `"provider"` / `"abort"` / `"unexpected"` on `onError`        |

Aggregate a parse by waiting for `requestCount` terminal events that share a `parseId`. OpenTelemetry-style:

```ts
createEDcheck({
  provider,
  hooks: {
    onRequest: (event) => {
      tracer.startSpan("edcheck.evaluate", {
        attributes: { "edcheck.request_id": event.requestId, "edcheck.parse_id": event.parseId },
      });
    },
    onResponse: (event) => {
      spanFor(event.requestId)?.setAttribute("edcheck.model", event.response.model);
      spanFor(event.requestId)?.end();
    },
    onError: (event) => {
      spanFor(event.requestId)?.recordException(event.error);
      spanFor(event.requestId)?.end();
    },
  },
});
```

Hook failures are swallowed and never logged: test your hooks; EDcheck will not tell you they
threw. Events carry the same `request` / `response` references the provider saw, including
`state`. Strip `event.request.state` before export if you need redaction.

## Testing your app

`mockProvider()` is part of the public API so application tests stay offline:

```ts
import { createEDcheck, mockProvider, semantic } from "@edteam/edcheck";

const provider = mockProvider({ answers: { fullName: 0.12 } });
const bound = createEDcheck({ provider }).define(User, {
  rules: { fullName: semantic("A plausible full name for a real person") },
});
```

## Development

Requires Node ≥ 20 and Yarn.

```sh
yarn install
yarn verify        # lint + typecheck + test + build
```

Work is spec-driven with [OpenSpec](https://github.com/Fission-AI/OpenSpec):
`openspec/constitution.md` (contract) → `openspec/changes/<change>/` (work) → `openspec/specs/` (truth).
Agent rules: [`AGENTS.md`](./AGENTS.md). Original brief: [`docs/pdr-v0.1.md`](./docs/pdr-v0.1.md).

## License

MIT © EDlabs / EDteam
