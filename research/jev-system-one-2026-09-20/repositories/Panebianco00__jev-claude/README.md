# jev — a decision layer for Claude Code

Claude Code makes dozens of judgment calls in a coding session: which library, where the file
goes, how far the refactor reaches, whether to run the destructive command, what goes in the
plan. They happen silently, they are not recorded, and nothing about them is calibrated.

This plugin routes those decisions through **[Jev](https://typesafe.ai)**, TypeSafe's System
One model, which returns a typed answer with a probability distribution instead of prose. Code
owns the policy; the model supplies the judgment; every call lands in a ledger you can read.

```
JEV decide[validation-library] -> zod   conf 0.79 - p 0.81 - margin 0.66 - stakes medium
ACTION proceed: act on this choice now; do not ask the user about it
probabilities: zod 0.81 | valibot 0.12 | hand_written_guards 0.04 | none_of_these 0.03
checks: breaks_public_api -> no (0.06) ok
```

## How it works

Three layers, because no single one of them is enough:

| Layer | What it is | Why |
|---|---|---|
| **Tools** | an MCP server exposing `decide` and `check`, always loaded | the only way to give Claude a Jev capability it can call |
| **Enforcement** | hooks on `ExitPlanMode`, `AskUserQuestion` and the plugin's own tools | instructions are persuasion; hooks are the only deterministic lever, and they fire in plan mode and inside subagents |
| **Knowledge** | the `jev-decisions` skill | how to phrase a decision so the answer means something |

What the gates actually do:

- **Plan approval** (`ExitPlanMode`) is refused until Jev has been consulted about the plan,
  and the plan is then reviewed against what you actually asked for. Your approval dialog is
  untouched — the gate never approves anything on your behalf.
- **Questions to you** (`AskUserQuestion`) are intercepted. If Jev judges that your own words
  already contain the answer — a separate "did they state this?" check, not just a confident
  guess — Claude is told the answer and continues. Anything that genuinely needs your
  preference reaches you untouched.
- **Destructive Bash commands** (`rm -rf`, force-push, `reset --hard`, `DROP`/`TRUNCATE`,
  `terraform destroy`, production deploys…) get the `risky_command` check before they run, with
  a few read-only git facts attached (is the target gitignored, was the branch ever pushed). A
  blocking finding refuses the command once, with the reason; ordinary commands never leave
  your machine.
- **Dependency installs** (`npm install <pkg>`, `pip install`, `cargo add`, `go get`…) are a
  library choice, so one is refused until Jev has been consulted that turn. Restoring a
  lockfile (`npm install`, `pip install -r`) is never gated.
- **A command Jev already said to stop on.** If Claude ran `check` on a command, got
  `confirm`, `escalate_to_user` or `revise`, and then runs it anyway, you get a permission
  prompt with Jev's finding instead of the command running silently.
- **Choices you delegated stay delegated.** "You choose the framework" is read as exactly that:
  Jev picks and flags it rather than handing the question back to you (except at high stakes).
- **Entering plan mode mid-turn** injects the plan-mode instructions immediately, instead of
  waiting for the plan gate to refuse.
- **Strict mode** adds a triage before the turn's first edit and an end-of-turn backstop. Off
  by default.

Every gate is bounded: at most two refusals per plan text, one per question set, one per
Bash command, one dependency refusal per turn. A gate can never
deadlock a session, and if Jev is unreachable everything falls through with a note that the
decision was unverified.

## Install

You need a TypeSafe API key: <https://console.typesafe.ai/keys>.

Inside Claude Code:

```
/plugin marketplace add Panebianco00/jev-claude
/plugin install jev@jev-claude
```

When the plugin is enabled, Claude Code asks for the API key (stored in your system keychain)
and the enforcement level. Restart Claude Code to load it.

Or from a shell, in one go:

```bash
claude plugin marketplace add Panebianco00/jev-claude
claude plugin install jev@jev-claude --config api_key=YOUR_KEY
```

Change either setting later with `/plugin configure jev@jev-claude`. Exporting `TYPESAFE_API_KEY`
works too, and takes precedence. Nothing is built or downloaded at install: the bundles in
`dist/` are committed. Node 20 or later must be on your `PATH`.

To update, run `/plugin marketplace update jev-claude`. Auto-update is off by default for
third-party marketplaces; you can switch it on in `/plugin` → Marketplaces.

Then `/jev:status` to confirm. Without a key the plugin still loads and every decision returns
`proceed_unverified`, so nothing breaks — it just does not decide anything.

`/jev:log` and `/jev:status` shell out, and a plugin cannot ship permission rules, so add these
to `~/.claude/settings.json` once to stop being asked:

```json
{ "permissions": { "allow": ["Bash(jev-log:*)", "Bash(jev-doctor:*)"] } }
```

For development, skip the install: `claude --plugin-dir /path/to/this/repo`.

## Configuration

Defaults are in the first column. Set them as environment variables, in `~/.claude/jev/config.json`,
or per project in `.jev.json` (same keys, camelCase).

| Variable | Default | Meaning |
|---|---|---|
| `JEV_ENFORCEMENT` | `standard` | `off` · `soft` (protocol only, no gates) · `standard` (plan + question gates) · `strict` (adds edit triage and stop backstop) |
| `JEV_AUTHORITY` | `autonomous` | `autonomous`: Jev decides and escalates when unsure. `advisory`: you confirm anything that matters |
| `JEV_ROUTER` | `stated` | `stated`: answer for you only when your words state the answer. `ledger`: never answer, only require consultation. `off` |
| `JEV_FAIL` | `open` | `open`: a Jev outage never blocks you. `closed`: only for fixable errors, and it still consumes the refusal budget |
| `JEV_CONF_AXIS` | `confidence` | which number the policy gates on: `confidence`, `top_probability` or `min` |
| `JEV_THRESHOLDS` | — | JSON, deep-merged over the defaults in `src/shared/policy.ts` |
| `JEV_BASH_GATE` | `true` | check destructive Bash commands with `risky_command` (standard and strict) |
| `JEV_DEPENDENCY_GATE` | `true` | require a consultation before a dependency install (standard and strict) |
| `JEV_RETAIN_DAYS` | `7` | how long ledgers are kept; `0` keeps only sessions active in the last hour |
| `TYPESAFE_API_KEY` / `TYPESAFE_BASE_URL` / `TYPESAFE_DEFAULT_MODEL` | — | standard TypeSafe SDK variables |

Every threshold lives in one file, `src/shared/policy.ts`, so the whole policy is one diff to
review. Each one is checked against the live model by `npm run calibrate` (see Development).

## What leaves your machine

Each decision sends a **redacted** JSON object to `api.typesafe.ai`: your request, the options
Claude wrote, the facts it gathered, and — for a plan review — the plan text. Keys, tokens, JWTs
and private keys are stripped before sending; whole files never are, because the skill tells
Claude to send extracted facts rather than file contents.

`/jev:log` shows exactly what was decided and with what confidence. `JEV_ENFORCEMENT=off`
turns the whole thing off without uninstalling.

Cost is negligible: TypeSafe bills input tokens only, around $0.0001 per decision.

## Commands

| | |
|---|---|
| `/jev:log` | the decision ledger for this session (`--all`, `--session <id>`, `--json`, `--calibration`) |
| `/jev:status` | key source, enforcement level, state directory, whether hooks are running |
| `/jev:jev-decisions` | the full guide to phrasing decisions |

## Development

```bash
npm install
npm run build          # bundles src/ into dist/*.mjs — dist is committed on purpose
npm test               # vitest, against a fake TypeSafe server; no network, no key needed
npm run typecheck
claude plugin validate . --strict

npm run calibrate      # live: every fixture through the real request path; needs a key
npm run test:live      # live: the same fixtures as a pass/fail regression suite
```

`npm run calibrate` sends the labelled cases in `test/calibration/fixtures/` to the real API
and prints, per question, the gap between its yes and no cases and whether the threshold acting
on it sits inside that gap. Raw answers go to `test/calibration/results/<model>.json`, so a
model upgrade shows up as a diff. It costs about $0.004 per full run.

`dist/` is committed so that installing the plugin never runs an install step: Claude Code
starts the MCP server with `node dist/server.mjs` and nothing else.

Layout: `src/shared/` holds everything both surfaces need (policy, question construction,
formatting, state); `src/server/` is the MCP server; `src/hooks/` is one module per hook behind
a single dispatcher; `src/cli/` is `jev-log` and `jev-doctor`.

The MCP server config is `config/mcp.json`, not `.mcp.json`. A file at the repo root would also
be read as a *project* server config, where `${CLAUDE_PLUGIN_ROOT}` does not exist — spawning a
second, broken copy that reports `Failed to reconnect to jev: CONNECTION_CLOSED` in every
session opened in this directory. See docs/DESIGN.md.

## Limits, stated plainly

"Every decision" is enforceable only where a decision becomes observable — a tool call, a plan
being approved, a question to you. Hooks cannot see the model's reasoning, so a choice made
silently in prose is caught only by the strict backstop, and only probabilistically. The gates
are bounded so they cannot trap you, which also means a determined model can exhaust them; the
ledger makes that visible. And Jev only ever sees the state Claude wrote for it, so a
lopsided state produces a lopsided answer — which is why the request carries your words
verbatim, why the option wording is itself scored, and why the plan is reviewed against what
you asked for rather than against the plan's own summary.

MIT.
