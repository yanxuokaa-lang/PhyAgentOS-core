# Jev Realtime Code Check

A VS Code / Cursor extension that checks your local Git changes against
your own coding rules, using [TypeSafe AI](https://docs.typesafe.ai)'s
**Jev** model. It watches your diff, not your whole repo — only the rules
relevant to the file types you actually touched get sent, and only *new*
violations introduced by your change are flagged.

📺 **Demo video:** https://youtu.be/goVDTUd7-J0

## What it does

- Reads a directory of Markdown rule files (default `jev/`), one `#`
  heading per rule.
- Each rule file can declare which files it applies to via a frontmatter
  header:
  ```md
  ---
  applies_to: **/*.ts, **/*.tsx
  ---
  ```
  A Python-only diff never loads your TypeScript rules; a `.tsx` change
  only loads your React rules. No frontmatter means "applies to
  everything."
- Collects the combined staged + unstaged diff for tracked files
  (`git diff HEAD`), plus surrounding file content, as context.
- Sends one `choice` question per applicable rule to Jev in as few
  requests as possible — batched adaptively by measured payload size (not
  a fixed count), since diff/file context size varies far more than rule
  count does.
- For anything Jev flags as a **violation**, a smaller follow-up request
  asks two more questions per violation: a `score` question rating
  **severity** (Minor → Moderate → Major → Blocking), and a `choice`
  question picking which specific added block of code is responsible.
- Real line numbers for that block come from parsing the diff's own hunk
  headers — never invented by the model. Clicking a violation jumps
  straight to that file/line; it also shows up as a Problems-panel
  diagnostic.
- Results are grouped in the sidebar by outcome (Violations and errors on
  top and expanded; Compliant/Not applicable collapsed at the bottom,
  since with hundreds of rules those are mostly noise, not signal), sorted
  within Violations by severity.
- Works offline too: with no API key configured, a labeled **OFFLINE
  MOCK** mode runs simple heuristics instead of a live call, so you can
  still see the UI flow.

## Three ways it runs

1. **Automatically, whenever code changes settle** — opt-in
   (`jevCodeCheck.autoAnalyzeOnSave`, off by default with an explicit
   consent dialog). Debounced to fire once edits pause for ~1s, so it
   naturally fires when an LLM agent finishes a burst of edits, not
   mid-stream. This is backed by a filesystem watcher, not just editor
   events — an external tool (an AI coding agent, a formatter, anything)
   writing files directly to disk is picked up even if that file was never
   opened in an editor tab, which a plain "on save" hook would miss.
2. **Manually** — **Jev: Analyze changes** command, or the sync icon in
   the sidebar's title bar.
3. **In CI, on a pull request** — `scripts/review-pr.ts` runs the identical
   rule-matching + Jev pipeline against a PR's committed diff (base...HEAD)
   and posts a GitHub review comment on each violation it can localize to a
   file/line. See `.github/workflows/jev-review.yml`. It reuses the same
   `src/` modules as the editor extension — no separate implementation to
   keep in sync. Requires the `TYPESAFE_API_KEY` secret; re-runs on the
   same PR don't repost a comment already there for the same rule. Skips
   fork PRs (no `pull_request_target`, to avoid running PR code with
   base-repo secrets).

## Why "rules as data"

Rules are just Markdown you write and version-control like any other
project file — no plugin code, no schema beyond a heading and an optional
frontmatter line. This repo ships **479 example rules across 11 file
types** as a starting point/stress test (TypeScript, React/TSX, CSS, Sass,
Markdown, Python, Go, JSON, YAML, HTML, and shell), each with a Good/Bad
code example, spanning style/convention, language-specific "gotchas" (real
semantic footguns — `.forEach` not awaiting async, YAML's `NO` parsing as
`false`, Go's pre-1.22 loop-variable capture), and per-language performance,
security, and UI/accessibility best practices (path traversal, ReDoS,
`shell=True` injection, SQL string-building, focus-visible styles, layout
shift, touch target size, and more):

| File | Applies to | Rules |
|---|---|---|
| `jev/typescript.md` | `**/*.ts` | 139 |
| `jev/python.md` | `**/*.py` | 56 |
| `jev/css.md` | `**/*.css` | 47 |
| `jev/go.md` | `**/*.go` | 42 |
| `jev/shell.md` | `**/*.sh` | 29 |
| `jev/markdown.md` | `**/*.md` | 29 |
| `jev/html.md` | `**/*.html` | 35 |
| `jev/react.md` | `**/*.tsx` | 33 |
| `jev/scss.md` | `**/*.scss` | 28 |
| `jev/yaml.md` | `**/*.yml`, `**/*.yaml` | 21 |
| `jev/json.md` | `**/*.json` | 20 |

Delete what you don't need, edit anything, or write your own — a rule file
is just:

~~~md
---
applies_to: **/*.ts
---

# No console statements
Code must not contain `console.log`, `console.debug`, or `console.info`
calls. Use a proper logger, or remove them before committing.

Good:
```ts
logger.info("Config loaded", { path });
```

Bad:
```ts
console.log("Config loaded", path);
```
~~~

## Install

```bash
npm run install:extension
```

Builds, packages, and installs into whichever of `cursor`/`code` is on your
PATH, in one step. Or manually: `npm run package` produces a `.vsix`, then
Extensions view → `...` → **Install from VSIX...**.

The extension ships with **no rules** — that's intentionally left to
whoever installs it. If your workspace has no `jev/` directory yet, the
sidebar's empty state is clickable and runs **Jev: Create example rule**,
which scaffolds a single starter `jev/example.md` (`applies_to: **/*`) to
edit from, rather than requiring you to write the format from scratch.

## Setup

1. Command Palette → **Jev: Set Jev API key** (stored in VS Code
   SecretStorage; alternatively set `TYPESAFE_API_KEY` in the launching
   environment). Without a key, results are labeled **OFFLINE MOCK**.
2. Open the **Jev Code Check** icon in the Activity Bar.
3. Run **Jev: Analyze changes**, or enable automatic analysis via
   **Jev: Toggle automatic analysis for this workspace** (opt-in, with an
   explicit confirmation dialog explaining what gets sent).

## Configuration

| Setting | Default | Description |
|---|---|---|
| `jevCodeCheck.rulesDir` | `jev` | Directory of `*.md` rule files, relative to the workspace root. |
| `jevCodeCheck.autoAnalyzeOnSave` | `false` | Opt-in: analyze as you edit and on save (throttled to 1/sec). |
| `jevCodeCheck.debounceMs` | `1200` | Inactivity delay before auto-analysis; floored at 1000ms. |
| `jevCodeCheck.maxDiffChars` | `20000` | Diff text cap sent to Jev; excess is disclosed, not silently dropped. |
| `jevCodeCheck.maxFileContextChars` | `8000` | Per-file content cap. |
| `jevCodeCheck.maxTotalContextChars` | `40000` | Total file-context cap across all changed files. |
| `jevCodeCheck.maxRulesPerRequest` | `20` | Upper bound on rules per request; actual batches are sized smaller automatically if diff/file context is large. |

## Project layout

```
src/                  Extension source (TypeScript)
test/                 Unit tests (node:test)
jev/                  Rule files for this repo's own code (dogfooding)
demo-fixture/         Small React app + jev/ rules for a guided before/after demo
playground.ts         Scratch file for exercising rules against real edits
```

## Development

```bash
npm install
npm run typecheck
node --import tsx --test test/*.test.ts
npm run package        # produces the .vsix
```

See `INSTALL.md` for a step-by-step install/demo walkthrough, and
`demo-fixture/BEFORE_AFTER.md` for a guided edit → violation → revert
script.
