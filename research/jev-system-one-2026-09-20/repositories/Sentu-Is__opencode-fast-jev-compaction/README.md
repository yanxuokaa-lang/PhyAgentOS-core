# fast-jev-compaction

Compaction that replaces the summary with Jev decisions: every tool call and
result is scored in one fast request, stale ones are dropped or truncated,
everything kept stays verbatim.

Ships three ways: a Claude Code plugin (`hooks/`, `.claude-plugin/`), an
opencode plugin (`opencode/`), and an npm library (`src/`).

## What and why

Most context compaction asks an LLM to summarize old turns. A summary is
lossy: a file path, exact error, constraint, or command can disappear even when
it matters later. This library never rewrites anything. It only deletes tool
calls and tool results Jev says are no longer needed, and it asks Jev while
showing it the whole conversation. User and assistant text stays verbatim and
in order.

The repository is an npm package (`src/`) plus two plugins that use it to
replace their host's built-in compaction summary with the original messages: a
Claude Code plugin (`hooks/`, `.claude-plugin/`) and an opencode plugin
(`opencode/`, added by this fork).

## Requirements

- Node `>=18` (see `engines` in `package.json`).
- opencode `>=1.18.31 <2.0.0` for the opencode plugin (same `engines` entry).
- A TypeSafe/OpenRouter API key (`TYPESAFE_API_KEY`; `OPENROUTER_API_KEY` is
  accepted as an alias by the install script).
- Claude Code `2.1.274+` for the hook side (function hooks are early-access).

## Quickstart

From the repo root, install the opencode plugin via the portable script
(default target: `$env:XDG_CONFIG_HOME\opencode\plugins` when
`XDG_CONFIG_HOME` is set, else `%USERPROFILE%\.config\opencode\plugins`):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-opencode-plugin.ps1
```

Confirm it is loaded: `opencode debug config` must list exactly one fast-jev
transform hook.

## Origin and relationship to upstream

This is a fork of [`tamaratran/fast-jev-compaction`](https://github.com/tamaratran/fast-jev-compaction)
— credit to the original project for the compaction core. The `src/` library
and the `hooks/` Claude Code plugin are upstream code; `opencode/` (the
opencode plugin port) is this fork's addition.

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
   stays under `maxRequestTokens` (30k by default). The same full state is
   resent with every request; requests run concurrently and their answers are
   merged.
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

## Install and usage

```sh
npm install fast-jev-compaction
export TYPESAFE_API_KEY=...
```

```ts
import { compactMessages, reductionRatio, type Message } from 'fast-jev-compaction';

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

To bring your own transport, implement `JevAsker` (one `ask(state, questions)`
method) and call `compact(messages, asker, options)`; `buildJevRequest` and
`parseJevResponse` give you the HTTP request body and response validation.
The building blocks (`collectToolCalls`, `fitState`, `batchCalls`,
`decideCall`, `applyDecisions`) are exported too.

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
claude plugin marketplace add tamaratran/fast-jev-compaction
claude plugin install fast-jev-compaction@fast-jev-compaction
```

The install prompts for the plugin options (API key, thresholds, `truncateHeadChars`,
…); leave them at their defaults to use `TYPESAFE_API_KEY` from the environment.
Restart Claude Code or run `/reload-plugins`. From then on `/compact` (and
auto-compaction) goes through Jev: the toast reads
`fast-jev-compaction: kept N/M messages, no summary (…)` when the pruned history
replaced the built-in summary, or `fallback to built-in summary (…)` when Jev
could not remove enough (short sessions, or when it fails).

To run from a checkout without installing: `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude --plugin-dir .`
from the repository root. No publishing step is required; the marketplace is
just the repo's `.claude-plugin/marketplace.json`.

## Development

```sh
npm install
npm run typecheck        # library + hook
npm test
npm run build
npm run validate:plugin  # claude plugin validate
TYPESAFE_API_KEY="$(cat ~/.typesafe_key)" npm run demo
```

The unit tests use a fake Jev and never contact TypeSafe. The demo is the live
network check. `npm run demo` auto-loads the repo-root `.env` when present
(real process env wins over `.env`; empty values count as absent). Copy
`.env.example` to `.env` and edit it to switch providers (TypeSafe defaults
vs OpenRouter) without changing any command.

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

## opencode plugin

`opencode/plugin.ts` (`FastJevCompaction`) prunes tool outputs from the
outgoing model request using TypeSafe System One ("Jev") scoring — but only
once the session's context occupancy reaches `compactAtPercent` (default 60),
and only completed/errored tool parts with output are eligible. Below the
threshold (or when occupancy is unknown) the hook is a no-op. It reuses the
`fast-jev-compaction` core. Claude Code support is unchanged.

How to register: install the bundle into your profile/global plugins dir via
`scripts/install-opencode-plugin.ps1` (or the npm package route below).
The repo deliberately ships NO project-local copy (the repo-local plugins dir
stays empty), precisely so the hook can never be registered twice.

Verify with `opencode debug config`: exactly one fast-jev transform hook must
be listed.

Config keys (`OpenCodeConfig` in `opencode/config.ts`), resolved by
`resolveOpenCodeConfig(options?, env?)` (defaults to `process.env`) with
precedence **explicit options > env var > default**. Malformed, empty, or
non-finite env values fall back to the next source (never `NaN`, never throw).
Removed port-only keys (`enabled`, `minNewEligibleChars`, `timeoutMs`,
`protectedTools`, `maxSessions`, `sessionTTLMs`, `maxJevCallsPerMessage`) are
gone entirely — neither the option nor its env var is read anymore.

| Key | Env var | Type | Default |
| --- | --- | --- | --- |
| `apiKey` | `TYPESAFE_API_KEY` | string | (none — absent → scoring throws, see below) |
| `model` | `FAST_JEV_MODEL` | string | `jev-latest` |
| `baseUrl` | `FAST_JEV_BASE_URL` | string | `https://api.typesafe.ai/v1/systemone` (core default) |
| `minReductionRatio` | `FAST_JEV_MIN_REDUCTION_RATIO` | finite number | `0.25` |
| `compactAtPercent` | `FAST_JEV_COMPACT_AT_PERCENT` | finite number | `60` (mirrors the Claude Code hook's `compactAtPercent`) |
| `goal` | `FAST_JEV_GOAL` | string | (none — derived from message text) |
| `keepThreshold` | `FAST_JEV_KEEP_THRESHOLD` | finite number | `0.5` |
| `preserveRecentMessages` | `FAST_JEV_PRESERVE_RECENT_MESSAGES` | finite number | `6` |
| `maxStateTokens` | `FAST_JEV_MAX_STATE_TOKENS` | finite number | `25000` |
| `maxRequestTokens` | `FAST_JEV_MAX_REQUEST_TOKENS` | finite number | `30000` |
| `truncateHeadChars` | `FAST_JEV_TRUNCATE_HEAD_CHARS` | finite number | `300` |

Required env: `TYPESAFE_API_KEY` (required for Jev scoring; absent → the
scoring request throws `missing API key`, `transform()` rejects, and history
is left untouched. The plugin hook catches the error, logs it, and leaves
history unchanged — fail-open at the hook boundary).

### Platform adaptations (opencode vs Claude Code)

The opencode surface is a faithful port of `src/*` + `hooks/fast-jev.ts`,
with three adaptations forced by the platform:

(a) The transformation delegates to the library `compact()` core
(`opencode/pruner.ts` is a stateless adapter: it projects opencode messages
into the library's `Message[]` shape, calls `compact()`, and maps the core
decisions back onto the native parts). Eligibility, batching, decisions, and
reduction arithmetic are the core's, not a re-implementation.

(b) `drop_call` removes the tool part and any message emptied that way
(original behavior). `drop_result` truncates the tool part's output in place
with a `[fast-jev-compaction truncated …]` marker — a platform adaptation,
since opencode parts cannot be truncated via API the way the library's own
`applyDecisions` rebuilds messages.

(c) opencode has no equivalent of the Claude Code hook's built-in-summary
fallback, so a below-ratio (`minReductionRatio`) or failed compaction leaves
history unchanged (fail-open): `transform()` throws and the hook logs the
error instead of substituting a summary.

Using this plugin sends tool call inputs and outputs from your opencode sessions to the external TypeSafe Jev (`api.typesafe.ai`) service for scoring.

### Install as an opencode plugin

Local plugins in `<configDir>/opencode/plugins/` are auto-loaded at startup —
the directory route needs no `opencode.jsonc` entry (the npm route below
does require a `plugin` array entry). From the repo root:

```powershell
# builds dist/opencode-plugin.js with the local esbuild, copies it as
# fast-jev.js into the resolved default plugins dir, and sets the user-scope env vars.
# Default target: $env:XDG_CONFIG_HOME\opencode\plugins when XDG_CONFIG_HOME is set,
# else $env:USERPROFILE\.config\opencode\plugins. Extra config roots via -ConfigDir
# (each is the dir that CONTAINS opencode\); a root that does not exist is skipped.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-opencode-plugin.ps1
# e.g. also install into another profile's config root:
# powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-opencode-plugin.ps1 -ConfigDir "D:\other-profile\config"
# re-check the install at any time (exit 0 iff all assertions pass; same -ConfigDir applies)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-opencode-plugin-install.ps1
```

Or step by step: `npm run build:plugin`, then copy
`dist/opencode-plugin.js` to `<configDir>/opencode/plugins/fast-jev.js` and
set `TYPESAFE_API_KEY`, `FAST_JEV_BASE_URL`, `FAST_JEV_MODEL` in your environment.

#### Install from npm (not published yet — pending)

The package is not published to npm yet, so this route does not work today;
use the script/directory route above. Once published, it will be:

```sh
npm install fast-jev-compaction
```

```jsonc
// opencode.jsonc
{ "plugin": ["fast-jev-compaction"] }
```

opencode resolves the plugin to `exports["./server"]` →
`dist/opencode-plugin.js`. The package declares
`engines.opencode >=1.18.31 <2.0.0`, so opencode refuses to load it on
2.x rather than silently no-op.

## Platform support

The dev scripts (`scripts/install-opencode-plugin.ps1`,
`scripts/verify-opencode-plugin-install.ps1`) are PowerShell for Windows.
On non-Windows, do the same steps manually: `npm run build:plugin`, copy
`dist/opencode-plugin.js` to `<configDir>/opencode/plugins/fast-jev.js`,
and set `TYPESAFE_API_KEY`, `FAST_JEV_BASE_URL`, `FAST_JEV_MODEL` in your
environment.

## Release status

The npm package is not published yet, so the supported install path today
is the script/directory route above — not the npm route.

## License

MIT — see LICENSE.
