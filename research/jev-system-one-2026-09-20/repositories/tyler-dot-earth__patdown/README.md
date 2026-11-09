# patdown

Standalone CLI that lints a tree against fuzzy rules in one markdown file. Wrap it as a hook, plugin, or extension.

The judge is swappable. The default backend currently uses TypeSafe/Jev; rules and CLI commands use a provider-neutral interface.

## Install

```
npx patdown --help
pnpm add -D patdown
```

Requires Node.js >=22.22.2. The library entry is `patdown`; rule adapters import `@patdown/rules`.

## Requirements

Node.js **>=22.22.2** and pnpm **11.8.0**. CI runs checks and built-CLI smoke tests on Node 22.22.2 and Node 24. Releases through v0.2.2 require Node >=24.18.0 and use `#/` import aliases that Node 22 rejects.

## Commands

From this repo, prefer the workspace script. It builds `patdown` through Turborepo (`dependsOn: build`) and then runs the CLI from your current directory:

```
pnpm -w patdown
pnpm -w patdown -- --rules ./rules.md
pnpm -w patdown -- --rules ./packs/typescript --verbose
pnpm -w patdown -- rules
pnpm -w patdown -- ask "Is this markdown heading title case?" --input-text "# Hello World"
pnpm -w patdown -- ask "Is this urgent?" --input-text "ASAP" --verbose
pnpm -w patdown -- --yes-threshold 0.9
pnpm -w patdown -- --files src/cli.ts --files README.md
pnpm -w patdown -- --files-from changed.txt --verbose
```

Do not run `pnpm build` by hand just to exercise the CLI, and do not use bare `npx patdown` against an unpublished branch (that installs the last registry version). After a release, consumers use `npx patdown` / `pnpm add -D patdown` as usual.

Default command lints from the current directory. `rules` prints what it loaded. `ask` answers a yes/no question, no files involved. It prints `yes` or `no`; `--verbose` also shows a P(yes) shade bar, the cutoff, and how long the judge call took. The old `--noul` and `--state` flags have been replaced by a positional question and `--input-text`.

To judge piped output, use `--stdin`:

```sh
git diff --cached | pnpm -w patdown -- ask "Does this diff introduce debugging statements?" --stdin
printf 'ASAP: production is down\n' | pnpm -w patdown -- ask "Is this urgent?" --stdin
```

These send the piped content to the configured judge. Do not pipe secrets. `--stdin` reads UTF-8 text through EOF, preserving newlines; it cannot be combined with `--input-text`. Without either option, the input is an empty string. `ask` reports yes/no without treating yes as a failing exit status.

Walks up from cwd looking for `AGENTS.PATDOWN.md`. `--rules` skips that walk and uses the path you pass.

## Adapters

The default rule source parses markdown. Swap it with a module that exports `PatdownRuleSourceLive`, an Effect Layer for `PatdownRuleSource`.

```
pnpm -w patdown -- --adapter ./patdown-yaml-rules.js
```

Or in the nearest `package.json` walking up from cwd:

```
{
  "patdown": {
    "adapter": "./patdown-yaml-rules.js",
    "yesThreshold": 0.9
  }
}
```

`--adapter` wins over package.json. `--rules` is still passed to the adapter as an override path.

```
import { PatdownRuleSource } from '@patdown/rules'
import { Effect, Layer } from 'effect'

export const PatdownRuleSourceLive = Layer.succeed(PatdownRuleSource, {
  loadPatdownRules: () =>
    Effect.succeed({
      patdownRules: [
        {
          patdownRuleTitle: 'No title case',
          patdownRuleBody: 'Headings use sentence case.',
          patdownRuleGlobs: ['**/*.md'],
        },
      ],
      patdownRulesFilePath: 'yaml-rules',
    }),
})
```

Load files however you want inside `loadPatdownRules`. `@patdown/rules` exports `findPatdownRulesFilePath` if you still want to walk up for a filename.

If you wrap the CLI as a hook and already have a layer, skip discovery:

```
import { Effect } from 'effect'
import { runPatdownCli } from 'patdown'

await Effect.runPromise(runPatdownCli(PatdownRuleSourceLive))
```

See [the adapter guide](docs/rule-source-adapters.md) for the interface, a multi-file parser, resolution rules, resource lifetimes, and local development setup. Adapters execute trusted local code. Install the CLI from npm as `patdown`; adapters import `@patdown/rules` and may import `patdown` for types.

## Packs

Optional rule bundles live under [`packs/`](packs/README.md). The CLI only runs rules; packs are content you can take all of, some of, or skip:

- [`packs/typescript`](packs/typescript/) — type-safety crimes and type laundering
- [`packs/effect`](packs/effect/) — Effect v4 services, schemas, errors, time, HTTP, tests
- [`packs/anti-slop`](packs/anti-slop/) — fuzzy counterpart to [Dillon Mulroy's anti-slop](https://github.com/dmmulroy/anti-slop)

```sh
# whole pack, or a single rule file from a pack
patdown --rules ./packs/effect --files-from changed.txt --verbose
patdown --rules ./packs/typescript/do-not-launder-types-with-casts.md
```

`--rules` accepts a markdown file or a directory of rule files (every `*.md` except `README.md`). Prefer stacked, backtick-wrapped `globs:` lines; commas inside one `globs:` value are separators.

## Rules

One `# heading` per rule. Optional `globs:` and `yes-threshold:` lines sit immediately under the heading, in either order. Commas or spaces, extra `globs:` lines stack. A second `yes-threshold:` line is an error. Text above the first heading is ignored. Headings inside fenced code are ignored. Only `#` headings start rules; `##` and deeper headings stay in the rule body, so sections like `## Not allowed` and `## Exceptions` are fine.

```
# No title case
globs: **/*.md
yes-threshold: 0.9

Markdown headings must use sentence case, not title case.
```

No globs means `**/*`. Globs are relative to cwd, not to the rules file. Always skipped: `.git`, `.turbo`, `coverage`, `dist`, `node_modules`.

## Lint

Each matched file goes to the judge as "does this file violate the following patdown rule?" The evaluated text is `path:` plus the file contents. One file at a time.

A rule with no matches prints `patdown: no files matched ...` and does not fail.

```
FAIL README.md: No title case
patdown: failed
```

Exit 1 on a violation, a missing rules file, a read error, an invalid cutoff, or a judge error. Add `--verbose` to group local lint output into per-rule console blocks (file, shade bar, P(yes), elapsed). Quiet mode stays one `PASS`/`FAIL` line per judgment. Lint totals elapsed time across every rule/file pair.

```
┌ Do not launder types with casts ───────────────────────── 1✗ / 1
│
├─ apps/foo
│
│  ✗  ▓▓▓▓▓▓▓▓▒░  0.86  312ms  service.ts
└

patdown: failed (elapsed: 1840ms)
```

`--files` (repeatable) and `--files-from` restrict lint to an explicit path list intersected with each rule's globs. That is how CI should run over a pull request. See [GitHub Actions](docs/github-actions.md).

Patdown counts estimated P(yes) strictly above the cutoff as yes; for lint, yes means violation. Default cutoff is 0.85. Override it with `--yes-threshold`, package.json `patdown.yesThreshold`, or a per-rule `yes-threshold:` line. The flag wins over package.json; a per-rule value wins for that rule only. `1` is rejected because nothing can exceed it. This cutoff belongs to patdown, not the provider.

See [judge providers](docs/judge-providers.md) for custom layers and the planned Effect Decision integration.

## Large inputs and API errors

Jev has a token budget, not a fixed safe diff size. Direct testing of `jev-1.13.0` accepted a 96,768-byte synthetic diff but rejected 97,536 bytes with HTTP 400 and `max_tokens_exceeded`; a larger, low-token input still succeeded. Different text, questions, and models can move that boundary.

The Jev client reports HTTP status, recognized provider error codes, input byte count, and a TypeSafe request ID when available. It distinguishes token limits from HTTP payload, authentication, rate/quota, and server failures without printing raw response bodies. It does not silently truncate input.

See [the measured results and live probe commands](docs/jev-input-limits.md), including how to compare a separate Vercel AI Gateway integration.

## Custom output

Embedded callers can replace `PatdownOutput` instead of using the default yes/no and lint formatting. Pass an output Layer as the fourth argument to `runPatdownCli`:

```ts
import { Console, Effect, Layer } from 'effect'
import { PatdownOutput, patdownJudgmentIsYes, runPatdownCli } from 'patdown'

const JsonOutputLive = Layer.succeed(PatdownOutput, {
	writeAnswer: (judgment, _verbose) =>
		Console.log(
			JSON.stringify({
				answer: patdownJudgmentIsYes(judgment) ? 'yes' : 'no',
				yesProbability: judgment.yesProbability,
			}),
		),
	writeLintResult: (result, _verbose) => Console.log(JSON.stringify(result)),
	writeRulesDocument: (document) => Console.log(JSON.stringify(document)),
	writeNoFilesMatched: (ruleTitle) => Console.log(JSON.stringify({ skipped: ruleTitle })),
	writeLintOk: () => Console.log(JSON.stringify({ status: 'ok' })),
	writeLintFailed: () => Console.log(JSON.stringify({ status: 'failed' })),
})

await Effect.runPromise(
	runPatdownCli(
		undefined, // default rule-source discovery
		process.argv.slice(2),
		undefined, // default judge
		JsonOutputLive,
	),
)
```

The output service receives structured judgments and lint results, including probabilities even when `--verbose` is off. Your layer decides what to print, collect, or omit. Formatting does not change the cutoff or exit status. The example emits one JSON object per output event, not a single JSON document for the entire run.

This is an embedding API, not a `--format` flag or dynamically discovered output plugin. Supply any dependencies inside your output layer; its effects must handle their own failures. CLI help, argument errors, and loading/provider errors still use the CLI's existing help/stderr paths rather than this service. Install `patdown` from npm for embeddings. Custom adapters still need a matching Effect version.

## Env

With the default TypeSafe backend, `TYPESAFE_API_KEY` is required for lint and `ask`. Optional `TYPESAFE_BASE_URL` (default `https://api.typesafe.ai`) and `TYPESAFE_DEFAULT_MODEL` (default `jev-latest`).

`pnpm -w patdown` inherits `TYPESAFE_*` from your environment.

## Release

Version lives in `apps/patdown/package.json`. That is what `patdown --version` prints.

```
pnpm -w release patch
pnpm -w release minor
pnpm -w release major
```

First write and commit `releases/vX.Y.Z.md` with the next version's notes. The release command requires a clean tree and validates those notes before changing anything. It runs `pnpm check`, bumps the CLI version, commits, tags `vX.Y.Z`, and pushes to `github` and `gitea` if present. With `gh` available, it watches the matching Release workflow.

The tag workflow runs checks again, creates a GitHub Release using the checked-in notes, and publishes `patdown`, `@patdown/rules`, and `@patdown/jev` to npm. See [the release process](releases/README.md) for the metadata format and backfilling published notes.

Pull requests and pushes to `main` run `pnpm check`. That is oxlint, tests, and typecheck. Not the fuzzy linter.

## Related

Inspired by [pi-warden](https://github.com/DevMortimer/pi-warden). Same idea, inside pi.

[Abide](https://github.com/coldteadotai/abide) is a similar Jev-backed checker. It hooks into coding agents, reads project instruction files, and asks Jev whether each edit or turn broke a rule.

[Jev Review](https://github.com/devagrawal09/jev-review) is a Jev-backed diff/codebase reviewer with a local dashboard of those judgments. Patdown stays in the terminal; `--verbose` draws a P(yes) shade bar instead of a GUI.

[Dillon Mulroy's anti-slop](https://github.com/dmmulroy/anti-slop) is the Oxlint ruleset that [`packs/anti-slop`](packs/anti-slop/) rephrases for fuzzy judging. Keep the static rules for exact AST hits; use the pack for paraphrases and type-laundering that still looks clean to a linter.

Name inspired by It's Always Sunny in Philadelphia

<img width="511" height="415" alt="image" src="https://github.com/user-attachments/assets/f7c73138-3914-4fbd-9e6b-7a37d161334a" />
