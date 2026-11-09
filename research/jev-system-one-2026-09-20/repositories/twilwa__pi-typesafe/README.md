# pi-typesafe

A Jev coding sidecar for Pi: four pre-flight hazard checks before `bash`, `write`,
and `edit`, and four diff-quality checks after successful `write` and `edit`.
Questions share one TypeSafe System One request per phase. Jev returns typed
values; this extension applies thresholds and writes fixed feedback text.

**Advisory mode is the default.** It records assessments and appends qualifying
feedback after execution without blocking tools. Blocking requires explicit
opt-in; explicit shadow mode records assessments without changing model-visible
results. All three modes use the same checks.
Missing credentials or any judge failure always leaves the tool untouched.

## Try it

Use Node.js 24 and **Pi 0.85.1** (`@earendil-works/pi-coding-agent`). Pi itself
requires Node >=22.19.0; this repository uses Node 24 to run TypeScript tests
without a build step.

```sh
npm ci
npm run check
pi -e ./src/extension.ts
```

With no key, the extension loads and does nothing. To enable evaluation, export
`TYPESAFE_API_KEY` in Pi's environment, or copy `.env.example` to `.env`, enter the
key locally, and load it before starting Pi:

```sh
set -a
. ./.env
set +a
pi -e ./src/extension.ts
```

Pi does not automatically load this repository's `.env`. Local `.env` files are
ignored by git; never commit credentials. The extension creates the existing
`src/typesafe.ts` client only when a nonblank key is configured. Configuration is
read when the extension loads; restart/reload it after changing configuration.

For a real-session trial, use a disposable Git repository, set `sidecar` to this
checkout's absolute path, and launch:

```sh
sidecar=/absolute/path/to/pi-typesafe
mkdir jev-playground
cd jev-playground
git init
pi -e "$sidecar/src/extension.ts"
```

Ask Pi to implement a small function and a test. Qualifying feedback appears in
tool results, and assessments are recorded in the session's `jev-assessment`
custom entries. To record assessments without model-visible feedback, use:

```sh
PI_JEV_CONFIG='{"mode":"shadow"}' pi -e "$sidecar/src/extension.ts"
```

Pi still needs its normal coding-model credentials for an interactive task.
Alternatively, `pi install /absolute/path/to/pi-typesafe` installs the package;
`package.json` declares `src/extension.ts` under `pi.extensions`. Avoid loading it
both through installation and `-e`, which would judge each operation twice.

## Modes and configuration

Set `PI_JEV_CONFIG` to a JSON object. Omitted fields use these defaults:

| Field                         | Default                                       | Meaning                                                                         |
| ----------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------- |
| `mode`                        | `"advisory"`                                  | Evaluate, record, and append qualifying feedback after execution                |
| `model`                       | `TYPESAFE_DEFAULT_MODEL`, then `"jev-latest"` | Model requested from TypeSafe                                                   |
| `timeoutMs`                   | `750`                                         | Total budget per handler, including context collection; allowed range 1–5000 ms |
| `checks.<id>.enabled`         | `true`                                        | Include this question in its batch                                              |
| `checks.<id>.confidence`      | See below                                     | Minimum returned confidence required to act, inclusive                          |
| `checks.<critic-id>.minScore` | `1`                                           | Critique only scores strictly below this, on a 0–2 scale                        |

| Mode       | Pre-flight behavior                                      | Post-execution behavior                                           |
| ---------- | -------------------------------------------------------- | ----------------------------------------------------------------- |
| `shadow`   | Record every validated assessment; allow execution       | Record the rubric; return no patch                                |
| `advisory` | Record hazards; allow execution                          | Append qualifying hazard warnings and low-scoring rubric feedback |
| `blocking` | Refuse qualifying hazards with `{ block: true, reason }` | Append low-scoring rubric feedback for executed edits/writes      |

Blocking does not set `terminate`, so the agent can revise its next tool call.
Advisory warnings arrive **after** execution and cannot prevent side effects.
High rubric scores and uncertain assessments do not add feedback. All result
patches contain only `content`, retaining the original text/images and leaving
`details`, `isError`, and `usage` unchanged, including earlier middleware changes.

Example: opt into blocking, disable credential checking, raise the test-weakening
confidence threshold, and flag partially implemented changes more often:

```sh
export PI_JEV_CONFIG='{
  "mode": "blocking",
  "timeoutMs": 750,
  "checks": {
    "credentials": { "enabled": false },
    "weakensTests": { "confidence": 0.97 },
    "implementation": { "confidence": 0.85, "minScore": 1.5 }
  }
}'
```

Every check can be disabled with `checks.<id>.enabled: false`. Disable a whole
phase by disabling its four checks; with all eight disabled, no context is read
and no API request is made. Unknown fields/checks, invalid JSON, invalid modes,
and out-of-range values disable the judge instead of guessing a policy.
`confidence` must be 0–1 and `minScore` must be 0–2. `TYPESAFE_BASE_URL` overrides
the default `https://api.typesafe.ai` only when it is a valid HTTPS URL; HTTP is
refused without a loopback exception because the API key is sent to that endpoint.

## Checks

The authoritative question wording, ordered rubric descriptions, fixed feedback,
and defaults are together in [`src/checks.ts`](src/checks.ts).

Pre-flight uses **Choice** with string labels `"true"` and `"false"`. A hazard
qualifies only when the selected label is `"true"` and its returned `confidence`
is at least the configured threshold. A high probability of true alone is not
enough. These are initial policy choices, not calibrated coding-domain guarantees.

| Check ID            | What it asks                                                                                                              | Confidence | Disable                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------- |
| `destructive`       | Destroys user data, discards uncommitted work, or irreversibly removes resources; ordinary source replacement is excluded | 0.95       | `checks.destructive.enabled: false`       |
| `credentials`       | Reads, exposes, modifies, or transmits actual secrets; placeholders and variable names alone are excluded                 | 0.95       | `checks.credentials.enabled: false`       |
| `outsideRepository` | Writes outside the Git root, including shell redirection or symlink targets; read-only actions are excluded               | 0.95       | `checks.outsideRepository.enabled: false` |
| `weakensTests`      | Skips, deletes, disables, or weakens tests/assertions to hide a failure; legitimate requirement changes are excluded      | 0.90       | `checks.weakensTests.enabled: false`      |

The critic uses **Score**, with three descriptive levels: a clear problem (0),
partial compliance (1), and an appropriate implementation (2). Scores are
probability-weighted means and can be fractional. All four default to confidence
**>=0.80** and score **<1.00** before feedback is injected.

| Check ID         | Dimension                                                              | Disable                                |
| ---------------- | ---------------------------------------------------------------------- | -------------------------------------- |
| `style`          | Matches surrounding naming, formatting, and structure                  | `checks.style.enabled: false`          |
| `implementation` | Implements the intended step rather than replacing it with TODOs/stubs | `checks.implementation.enabled: false` |
| `errorHandling`  | Handles or propagates errors rather than suppressing failures          | `checks.errorHandling.enabled: false`  |
| `taskScope`      | Supports the stated task without unrelated changes                     | `checks.taskScope.enabled: false`      |

## Failure behavior and latency

Missing/blank key, bad configuration, authentication errors, rate limits,
connection errors, malformed responses, unavailable context, timeouts, and
cancellation return `undefined`. A failure while recording an assessment or
logging also cannot block execution. The complete asynchronous judging path is
caught because Pi treats an uncaught `tool_call` error as a tool refusal.

Each handler uses a 750 ms best-effort budget, propagates `ctx.signal`, and
disables SDK retries. A fetch that ignores abort is released after a short
cancellation-settlement window; normal abort-aware transports are cancelled.
Repository discovery explicitly sends SIGTERM, escalates to SIGKILL after a
bounded grace period, and waits for the child exit when the operating system can
deliver those signals. It cannot force termination of a process stuck in
uninterruptible kernel I/O. Session shutdown/reload cancels outstanding work and
clears snapshots. Each pre-flight and critic has its own budget: a write may cost
two requests, and Pi preflights sibling tools sequentially. These costs
accumulate; this is not a zero-overhead service. Synchronous work such as Pi's
assessment persistence and JavaScript scheduling under host load can overrun the
configured time; state and advisories are committed only if the final deadline
and cancellation checks accept the handler.

Incoming provider responses are stream-limited to 64 KiB before SDK parsing.
The exact limit is accepted; an over-limit response fails open.

Failures are quiet by default. `NODE_DEBUG=pi-jev` enables fixed debug messages
without keys, prompts, source, SDK bodies, or raw error text. SDK logging is
explicitly off even if `TYPESAFE_LOG_LEVEL` is set.

The SDK does not validate responses at runtime. [`src/verdict.ts`](src/verdict.ts)
validates the whole requested batch before applying any answer: model/usage,
answer IDs, kinds, finite ranges, declared Choice labels, complete probability
keys, distributions, and Score legends/consistency. Live `jev-1.13.0` returned
independently rounded scores and probabilities (e.g. score 1.99 with a rounded
expected value of 2.00); consistency tolerances account for two-decimal rounding.
A malformed answer causes the entire batch to abstain.

## Data and scope

Enabling a key sends the selected tool's input, latest user task text, working
directory/Git root, and bounded target-file context to TypeSafe in **every mode**,
including shadow. For writes, the critic compares snapshots before and after the
operation; for edits it also receives Pi's `details.diff`. The current file
supplies surrounding style. The extension does not scan the repository or read
environment variables for task context.

Local budgets are 16,000 bytes for serialized tool input, 8,000 bytes for the
latest user message, 12,000 bytes per target file, 48,000 bytes for serialized
state, and 64 KiB for the provider response. Oversized inputs are skipped rather
than silently truncated. Files must be regular, text, and resolve inside the Git
repository. Git's discovered metadata paths, including the worktree `.git`
marker, Git directory, common directory, and aliases resolving into them, are
classified but never read. Missing-path resolution follows dangling symlinks,
including relative targets, chains, and symlinked parents, before classifying a
new destination. It has a local cap of 256 component steps; resolution errors
abstain. Missing files are represented as absent. No Git root means abstention.
Snapshot/advisory maps hold at most 128 tool calls and are cleared on session
lifecycle changes. Missing/mismatched snapshots skip critique.

This is a path-based model assessment, not deterministic containment or a
security boundary. Tool input or source can itself contain credentials; a
credential question does not redact them before upload. Only use a key with
source/tasks approved for that endpoint. An ancestor can be replaced between
path assessment and reading, and hardlinks or bind mounts can alias storage that
originated elsewhere. Those cases require an execution/read boundary anchored to
directory handles or equivalent platform containment and are not solved here.
Pi's edit diff can also contain context supplied by the tool result even when this
extension did not read an external snapshot. Shell indirection, missing context,
prompt injection, later input-mutating extensions, and concurrent writes to the
same file can invalidate a judgment. The task context is the latest user message,
not a reconstruction of all prior authorizations. `user_bash`, PowerShell, custom
tools, and other extensions' direct actions are outside this first implementation.
Failed writes/edits receive no rubric critique.

Valid assessments are saved with `pi.appendEntry("jev-assessment", ...)`, outside
model context. Entries contain the returned model, request ID when available,
phase/call ID, mode, policy version, thresholds, score/choice/confidence and
probabilities, state hash, request latency, and token usage. They contain no raw
state. Pi's ordinary session history may separately contain its usual source and
tool messages. To inspect assessments in a session JSONL file:

```sh
jq 'select(.type == "custom" and .customType == "jev-assessment") | .data' SESSION.jsonl
```

## Validation and measured evidence

```sh
npm run check             # format, lint, strict project types, tests
npm run test:unit         # mocked transport and real Pi extension loader
npm run test:integration  # existing SDK smoke test; loads optional .env
npm run smoke:jev         # optional live six-batch synthetic sidecar trial
```

`npm run check` passes offline without a key; the existing live SDK test skips
when its key is absent. No existing test was weakened. Unit coverage includes
blocking/confidence boundaries, batched question shapes, all three modes,
content preservation, failures, malformed fields, missing keys, cancellation,
non-cooperative transport timeouts, Git-child reaping, response-size boundaries,
Git-metadata exclusion, context limits, and snapshot cleanup.

Measured on this host on **2026-09-17**, using `npm run smoke:jev`, Node 24.21.0,
the default 750 ms budget, and a tiny synthetic function replacement:

| Batch               | Whole-handler times (ms), three requests | Input/output tokens per request |
| ------------------- | ---------------------------------------- | ------------------------------- |
| Four hazard Choices | 204, 174, 94                             | 1044 / 124                      |
| Four rubric Scores  | 110, 62, 128                             | 1115 / 61                       |

All six batches validated, returned model **`jev-1.13.0`**, and left both hooks
unchanged in shadow mode. The fixture received no qualifying hazards or low
scores. The preceding trial exposed the rounding behavior above and correctly
abstained on two critic responses before the validator correction. These samples
are integration evidence, not latency percentiles, billing measurements,
calibration results, or proof that Pi completes coding tasks better. Interactive
self-correction, representative coding accuracy, false-block rates, larger-state
latency, and account cost/quotas remain unverified.

Pi's shipped declaration dependencies include JSON import-attribute errors and a
missing optional provider type under TypeScript 6/NodeNext. `skipLibCheck` skips
checking dependency declaration internals; this project's source/tests/scripts
remain strict and typechecked against Pi's real declarations.

## Verified contracts and sources

Verified against the installed **Pi 0.85.1 release**, its bundled
`docs/extensions.md`, shipped extension `.d.ts` files, and extension examples.
The [versioned Pi docs](https://github.com/earendil-works/pi/blob/d981de1229ef899957bbe968bc8dcda02a21f477/packages/coding-agent/docs/extensions.md)
document the default TypeScript factory, mutable pre-execution inputs, blocking
return contract, and middleware-style result patches. This extension uses
`isToolCallEventType`, `isEditToolResult`, and `isWriteToolResult`; it does not use
unreleased prompt-patching APIs.

TypeSafe access reuses [`src/typesafe.ts`](src/typesafe.ts), the thin wrapper over
**`@typesafe-ai/sdk` 0.6.0**. [System One](https://docs.typesafe.ai/api) accepts
`state`, named `questions`, and `model`; the SDK returns typed answers, model,
and usage. [Choice](https://docs.typesafe.ai/primitives/choice) returns a selected
label, option probabilities, and confidence. [Score](https://docs.typesafe.ai/primitives/score)
uses 2–10 ordered descriptions and returns their expected position, legend,
probabilities, and confidence. [Noul](https://docs.typesafe.ai/primitives/noul)
returns only the probability of yes; it has no separate confidence field.
[Confidence](https://docs.typesafe.ai/confidence) summarizes the probability
distribution, not a guarantee of correctness for one prediction.

The [primitives overview](https://docs.typesafe.ai/primitives), fetched during
implementation on 2026-09-17, states that questions share a budget of **around
32,000 tokens**, roughly 150,000 English-text characters, with no separate
question-count limit. Treat that as approximate documentation, not a byte limit
or account guarantee. The extension's smaller byte caps are local policies.
Questions cannot see each other's answers or their own IDs; every question's
instructions include its full decision and evidence references. The
[batching pattern](https://docs.typesafe.ai/patterns/fan-out) motivates shared-state
calls; it does not guarantee constant latency. Published SLA, latency percentiles,
model-alias stability, account quotas, and a billing contract were not established.
