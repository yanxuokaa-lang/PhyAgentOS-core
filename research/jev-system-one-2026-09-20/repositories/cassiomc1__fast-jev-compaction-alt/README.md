# fast-jev-compaction-alt

Jev-guided, verbatim context compaction for coding agents. The package ships
with Claude Code and OpenCode integrations, a structural Responses/Codex
adapter, and a host-neutral npm API. Every tool call and result is scored,
stale history is dropped or truncated, and everything kept stays verbatim.

## What and why

Most context compaction asks an LLM to summarize old turns. A summary is
lossy: a file path, exact error, constraint, or command can disappear even when
it matters later. This library never rewrites anything. It only deletes tool
calls and tool results Jev says are no longer needed, and it asks Jev while
showing it the whole conversation. User and assistant text stays verbatim and
in order.

The repository is both an npm package (`src/`) and a set of host adapters. It
supports Claude Code (`hooks/`), OpenCode (`src/plugin.ts`), and structural
Responses/Codex items (`src/codex.ts`) without requiring a Codex/OpenAI SDK.
The Claude Code adapter uses the package to replace Claude Code's built-in
compaction summary with the original messages.

## Relationship to the original project

This repository is an independently maintained fork and extension of the
original [`tamaratran/fast-jev-compaction`](https://github.com/tamaratran/fast-jev-compaction)
project. The original repository is the upstream reference for the Jev-guided
compaction implementation; this fork preserves that core direction while
adding the Codex/Responses adapter, OpenCode integration, programming-workflow
policies, and expanded validation and regression coverage.

Use the original project when you need the upstream Claude Code/npm baseline.
Use this repository when you need the additional Codex, OpenCode, routing,
triage, autonomy, and programming-agent safeguards described below.

## Codex plugin

The repository also contains the portable Agent Plugins manifest
(`plugin.json`), the Codex compatibility manifest (`.codex-plugin/plugin.json`),
and the `fast-jev-compaction` skill. The skill is designed for coding sessions
and applies the same rules to intent routing, triage, urgency, risk, autonomy
thresholds, parallel Jev questions, and Responses/Codex item compaction.

Install it from a local marketplace when using Codex locally. For the default
personal marketplace, add an entry in `~/.agents/plugins/marketplace.json` and
then run:

```sh
codex plugin add fast-jev-compaction-alt@local-fast-jev
```

For a non-default marketplace, register its marketplace root first with
`codex plugin marketplace add <marketplace-root>` and use that marketplace's
name in the install selector.

Then restart the Codex desktop app or start a new Codex process. Enable the
plugin in the local Codex configuration if the client does not enable newly
installed local plugins automatically:

```toml
[plugins."fast-jev-compaction-alt@local-fast-jev"]
enabled = true
```

This integration exposes a reusable skill; it does not intercept or rewrite
Codex's private hidden context window. A host integration must provide a
Responses-style item list before `compactCodexItems` can compact it. If Jev is
unavailable, the normal host behavior remains authoritative and the original
payload should be preserved.

## How it works

1. Every `tool_use` is paired with its `tool_result` by `tool_use_id`. Calls in
   the first message or in the newest `preserveRecentMessages` messages are
   pinned and never touched.
2. The **state** sent to Jev is the whole conversation so far, oldest first,
   with every tool result replaced by a short note (`ok, 4213 chars (omitted)`).
   Tool inputs are included, texts are included, nothing is summarized.
3. The state is fitted into `maxStateTokens` (25k by default) in stages, each
   applied only if the previous one was not enough: tool inputs truncated to
   1000, then 200, then 60 characters; long texts abridged to head + tail,
   oldest non-pinned messages first; old non-pinned messages collapsed to a
   `[… N chars omitted …]` note; old tool calls reduced to one line each
   (`t12 Read file_path=src/a.ts → ok 480ch`); old call-less messages left
   out; runs of old call-only messages folded into one entry. If it still
   does not fit, compaction throws. Tokens are estimated without a tokenizer (a
   word per six letters, half a token per digit, ~one per other symbol),
   calibrated to land a little above the counts Jev reports.
4. For every non-pinned call Jev gets two `noul` questions: should the **call**
   stay (knowing it was made, with its input, still matters), and should the
   **result** stay verbatim (its contents are still needed and re-running the
   tool would not do).
5. Questions are split into as many requests as needed so state plus questions
   stays under `maxRequestTokens` (30k by default, under Jev's 32k request
   limit). The same full state is resent with every request; requests run
   concurrently and their answers are merged.
6. Decisions per call, against `keepThreshold`:
   - `keepResult ≥ threshold` → keep call and result;
   - else `keepCall ≥ threshold` → keep the call, truncate the result to its
     first `truncateHeadChars` characters plus a one-line note;
   - else → remove the call together with its result.
7. The message list is rebuilt: a message that loses all its content is
   removed, untouched messages are returned as the same objects, and no result
   is ever left without its call.

Jev failures, malformed answers, a missing key, or a history that cannot be
fitted throw; the caller (or the Claude Code hook) decides what to fall back to.

## Programming workflows

The default behavior is designed for repository work:

- User constraints and conversational text remain verbatim.
- Recent messages and the first message are pinned by default.
- Tool calls and tool results are decided independently, so a useful command
  can remain visible even when its large output is truncated.
- Failed test output can be kept verbatim by the Jev decision or by a host
  policy; callers should still keep their normal test and approval gates.
- Large histories are reduced in stages and never exceed the configured Jev
  state budget, unless compaction fails and the host fallback takes over.

The programming-focused regression suite covers read/grep/edit/test flows,
exact assertion failures, stale history removal, large coding transcripts, and
bounded concurrent Jev batches:

```sh
npm run test:programming
```

## Install and usage

```sh
npm install fast-jev-compaction-alt
export TYPESAFE_API_KEY=...
```

```ts
import { compactMessages, reductionRatio, type Message } from 'fast-jev-compaction-alt';

const transcript: Message[] = [
  { role: 'user', text: 'Fix the failing test. Never edit src/generated.', toolUses: [] },
  {
    role: 'assistant',
    text: '',
    toolUses: [{ tool_use_id: 'toolu_1', tool: 'Read', input: { file_path: 'src/a.ts' } }],
  },
  { role: 'user', text: '', toolUses: [], toolResults: [{ tool_use_id: 'toolu_1', text: '…file…' }] },
  // …
];

const result = await compactMessages(transcript, { preserveRecentMessages: 4 });
console.log(result.messages, result.decisions, result.stats);
if (reductionRatio(result) < 0.25) {
  // not worth it: keep the original transcript, or summarize instead
}
```

`Message` is a subset of Claude Code's `SessionMessage`, so a session transcript
can be passed in as is.

### Responses/Codex items

The package also exposes a dependency-free adapter for Responses-style
`function_call` and `function_call_output` items:

```ts
import {
  applyDecisionsToCodex,
  codexToMessages,
  compactCodexItems,
  type CodexItem,
} from 'fast-jev-compaction-alt/codex';
import { collectToolCalls } from 'fast-jev-compaction-alt';
import type { JevAsker } from 'fast-jev-compaction-alt';

const items: CodexItem[] = /* items from a Responses/Codex request */ [];
declare const asker: JevAsker;
const result = await compactCodexItems(items, asker, { preserveRecentMessages: 6 });
const calls = collectToolCalls(codexToMessages(items), 6);
const nextItems = applyDecisionsToCodex(items, result.decisions, calls, 300);
```

Unknown item types are preserved by the adapter. The returned list is a new
array, and the original request payload is not mutated; this makes it suitable
for a Codex/Responses middleware that replaces only the outgoing request.

To bring your own transport, implement `JevAsker` (one `ask(state, questions)`
method) and call `compact(messages, asker, options)`; `buildJevRequest` and
`parseJevResponse` give you the HTTP request body and response validation.
The building blocks (`collectToolCalls`, `fitState`, `batchCalls`,
`decideCall`, `applyDecisions`) are exported too.

For intent routing, triage, urgency, or risk, use the exported `askQuestions`
helper with `choice` and `score` questions. Responses are validated before use,
including selected choices, confidence, probabilities, and finite scores. For
autonomous actions, apply a local policy with `evaluateAutonomy`; it fails
closed when confidence, intent, or required risk evidence is not acceptable.
Jev provides evidence, but the local policy remains the authorization boundary.

The autonomy policy treats risk scores as normalized values from `0` (lowest
risk) to `1` (highest risk). It requires an explicit allow-list of intents and
a minimum confidence; if a maximum risk is configured, missing or invalid risk
evidence is rejected.

`apiKey` defaults to `process.env.TYPESAFE_API_KEY`. Never commit the key or
put it in a source file.

## Options

| Option | Default | Description |
| --- | --- | --- |
| `apiKey` | `TYPESAFE_API_KEY` | TypeSafe API key (`compactMessages`/`JevClient`) |
| `model` | `jev-latest` | Jev model name |
| `baseUrl` | `https://api.typesafe.ai/v1/systemone` | System One endpoint |
| `fetch` | native `fetch` | Injectable fetch implementation for tests |
| `goal` | last 3 user prompts | Ongoing task description included in the state |
| `keepThreshold` | `0.5` | Minimum keep probability for a call or result to stay |
| `preserveRecentMessages` | `6` | Newest messages never touched (the first is always kept) |
| `maxStateTokens` | `25000` | Estimated token ceiling for the state |
| `maxRequestTokens` | `30000` | Estimated ceiling for state plus one batch of questions |
| `truncateHeadChars` | `300` | Characters of a dropped tool result retained before its note |
| `maxConcurrentRequests` | `3` | Maximum concurrent HTTP requests to Jev when asking question batches |
| `requestTimeoutMs` | `15000` | HTTP request timeout in milliseconds before aborting a Jev request |

`result.stats` reports message and character counts before and after, the
per-reason decision counts, the state size in estimated tokens, which fitting
stage was needed, and the number of requests.

## Limitations

- Only tool calls and results are candidates; text messages are never removed
  or shortened in the output (they are only abridged in the state Jev sees).
- Token sizes are estimates from character counts, not a tokenizer.
- Calibration is at the request level; a probability is not a proof that a
  result is safe to delete. The assistant can always re-run the tool.
- The full state is repeated with every request, so a history near the state
  ceiling costs one request per handful of questions.

## Claude Code plugin

The repository root is a Claude Code function-hook plugin: `hooks/fast-jev.ts`
is a thin adapter that feeds `session.compact` transcripts through `src/` and
falls back to Claude Code's built-in summary on errors or insufficient
reduction. See [`hooks/README.md`](hooks/README.md) for configuration and the
Claude Code 2.1.274 type reference.

### Install in Claude Code

Function hooks are an early-access Claude Code feature (2.1.274+), so the
opt-in flag must be set wherever Claude Code runs, e.g. in `~/.claude/settings.json`:

```json
{ "env": { "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1", "TYPESAFE_API_KEY": "<your key>" } }
```

Then add this repository as a plugin marketplace and install the plugin,
either from the shell or as slash commands inside a session:

```sh
claude plugin marketplace add cassiomc1/fast-jev-compaction-alt
claude plugin install fast-jev-compaction-alt@fast-jev-compaction-alt
```

The install prompts for the plugin options (API key, thresholds, `truncateHeadChars`,
…); leave them at their defaults to use `TYPESAFE_API_KEY` from the environment.
Restart Claude Code or run `/reload-plugins`. From then on `/compact` (and
auto-compaction) goes through Jev: the toast reads
`fast-jev-compaction-alt: kept N/M messages, no summary (…)` when the pruned history
replaced the built-in summary, or `fallback to built-in summary (…)` when Jev
could not remove enough (short sessions, or when it fails).

To run from a checkout without installing: `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude --plugin-dir .`
from the repository root. No publishing step is required; the marketplace is
just the repo's `.claude-plugin/marketplace.json`.

## OpenCode plugin

The same library ships as an OpenCode plugin (`src/plugin.ts`, exported as
`fast-jev-compaction-alt/plugin` and `./server`). OpenCode has no
replace-the-transcript hook, so the port works with the two hooks OpenCode
does offer:

- `experimental.chat.messages.transform` runs the library over the messages of
  **every LLM request** (normal prompts and compactions alike) and drops or
  truncates the tool outputs Jev judges stale. The stored session is never
  rewritten; only the in-memory copy sent to the model is pruned, so every
  request pays only for the context that still matters. This is the continuous
  verbatim compaction, with no summary anywhere.
- `experimental.session.compacting` injects Jev's keep/drop lists into the
  built-in compaction prompt, so when OpenCode does summarise, the summary
  preserves what Jev scored as still needed.

### Install in OpenCode

```sh
npm install fast-jev-compaction-alt
export TYPESAFE_API_KEY=...
```

`opencode.json`:

```json
{ "$schema": "https://opencode.ai/config.json", "plugin": ["fast-jev-compaction-alt"] }
```

With options (every value also falls back to its default when omitted):

```json
{
  "plugin": [
    ["fast-jev-compaction-alt", { "keepThreshold": 0.5, "preserveRecentMessages": 6 }]
  ]
}
```

`apiKey` defaults to `process.env.TYPESAFE_API_KEY`. All library options
(`goal`, `keepThreshold`, `preserveRecentMessages`, `maxStateTokens`,
`maxRequestTokens`, `truncateHeadChars`, `maxConcurrentRequests`, `requestTimeoutMs`, plus `model`/`baseUrl`) behave as
documented above.

| Option | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Set to `false` to keep the plugin loaded but skip Jev pruning |
| `minReductionRatio` | `0` | Minimum estimated char reduction required to apply pruning to a request |
| `maxConcurrentRequests` | `3` | Maximum concurrent HTTP requests to Jev across question batches |
| `requestTimeoutMs` | `15000` | Timeout in milliseconds for Jev API requests before falling back gracefully |
| `debugFile` | `FAST_JEV_DEBUG_FILE` | Path of a JSONL file receiving one stats-only line per hook invocation (counts and decisions, never message content); proves the plugin is firing and pruning in a live session |

Failures (missing key, Jev error, oversized history) are logged with
`client.app.log` and leave the messages untouched, so the session always keeps
working. A rejected key (401/403) disables Jev pruning until OpenCode reloads,
so a bad key costs one failed request instead of one per model call. The
per-request pruning decisions are logged at `info` level when something was
dropped.

### OpenCode notes and limits

- Pruning applies to the payload sent to the model, not to the stored
  session: reopening the transcript still shows the original tool outputs.
- The transform hook fires on every request, so Jev is asked once per model
  call while tool history keeps changing (no candidates → no request, no cost).
- Contributors: the runtime only honours **in-place** mutation of
  `output.messages` (`splice`), never reassignment; `src/opencode.ts`
  (`applyDecisionsToOpenCode`) already handles this.
- See [`opencode.example.json`](opencode.example.json) for a starter config.

## Development

```sh
npm install
npm run typecheck        # library + hook
npm test
npm run test:programming # coding-agent regression scenarios
npm run build
npm run validate:plugin  # claude plugin validate
npm run release:check    # full local package and manifest gate
TYPESAFE_API_KEY="$(cat ~/.typesafe_key)" npm run demo
```

The unit tests use a fake Jev and never contact TypeSafe. The demo is the live
network check.

## Animated demo (macOS)

`demo/JevDemo` is a small native SwiftUI app that plays a scripted, dramatized
version of the compaction flow inside a Claude Code-style terminal: the tool
calls of a canned transcript are scored, results and calls Jev lets go turn red
and collapse away, and the rest stays verbatim. It never calls the API; it
exists to be screen recorded.

```sh
demo/JevDemo/build.sh   # builds demo/JevDemo/build/JevDemo.app and launches it
```

Press space in the app to replay from the start.
