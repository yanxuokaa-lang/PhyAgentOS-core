# JevExplore

[![Watch interactive setup](docs/demo/setup-preview.png)](docs/demo/setup.mp4)

[Watch the setup wizard and a live Jev run](docs/demo/setup.mp4).

[![Watch the non-interactive CLI](docs/demo/noninteractive-preview.png)](docs/demo/noninteractive.mp4)

[Watch the AI-friendly JSON workflow](docs/demo/noninteractive.mp4).

A TypeScript command-line tool that uses Playwright and real TypeSafe Jev judgments
to explore an application's observed action space. It saves a resumable checkpoint,
JSON graph, offline HTML graph, and coverage report. By default, four browser workers
explore branches while up to eight Jev requests run concurrently. Exploration stops
when no eligible work remains or you interrupt it; run budgets are optional.

## Quick start

Requires Node.js 24 and pnpm 11.5.0.

```sh
pnpm install --frozen-lockfile
pnpm explore
```

In a terminal, `pnpm explore` opens an interactive wizard built with
[@clack/prompts](https://github.com/bombshell-dev/clack). It guides you through the
starting URL, optional scope/login/form settings, parallelism, and where to save
configuration and reports. Keep the defaults or customize them, then save for later
or start exploring. Missing Chromium can be installed from the wizard.

The wizard uses `TYPESAFE_API_KEY` from your environment, or accepts a masked key
for the current process. The key is never written to the configuration. You can
also finish setup without a key and set the environment variable later. `.env`
files are not loaded automatically.

Without a key, completing the questions saves the config for later. With a key,
the final menu lets you start immediately, save for later, or cancel.

To reopen the wizard or prefill the starting URL:

```sh
pnpm explore setup
pnpm explore setup http://localhost:5173
```

For scripts and CI, install Chromium and use a URL or saved configuration directly:

```sh
pnpm exec playwright install chromium
pnpm explore https://your-test-app.example --output output/my-run
pnpm explore --config explore.local.json
```

Setup requires an interactive terminal. Existing config files and exploration
checkpoints are preserved; use a new filename/folder or resume a saved run with
`pnpm explore --config explore.local.json --resume`. Relative paths are resolved
from the directory where you run the CLI.

Open `output/my-run/graph.html` directly in a browser. Select a node to inspect all
its actions, blockers, probabilities, and observed transitions. Search by URL or
page title. Only observed transitions have destinations.

## AI agents, scripts, and CI

Use `--json` for a prompt-free run with one JSON result on stdout. It works even
when an agent allocates a terminal. Set `TYPESAFE_API_KEY` in the child process
environment and install Chromium once with `pnpm exec playwright install chromium`.
Use `pnpm --silent` to keep the package manager's output out of the JSON stream.

```sh
# Discover all configuration fields and defaults.
pnpm --silent explore --schema

# Validate config without a browser, API key, network requests, or file writes.
pnpm --silent explore --config explore.local.json --dry-run --json

# Explore and resume using the same output directory.
pnpm --silent explore --config explore.local.json --json
pnpm --silent explore --config explore.local.json --resume --json
```

Pass a JSON config on stdin with `--config -`. An agent can supply the JSON directly
through its subprocess API; this shell example works in PowerShell and POSIX shells:

```sh
echo '{"url":"http://localhost:5173","outputDir":"output/agent-run"}' | pnpm --silent explore --config - --json
```

For non-interactive setup, write a config object with at least `url`, or generate
a resolved config with `pnpm --silent explore http://localhost:5173 --dry-run` and
save stdout to a new config file. Defaults remain four browser workers, eight Jev
requests in parallel, and no run budgets. CLI URL, `--root`, and `--output` override
the corresponding saved values. `--non-interactive` disables prompts while keeping
human-readable output; `--json` and `--dry-run` also disable prompts automatically.

JSON results include `stopReason`, state/transition counts, `errorCount`, usage,
remaining work, and absolute report paths. Exit codes are **0** for a run without
recorded errors, **1** for invalid arguments/configuration or startup failure,
**2** for recorded run errors, and **130** for interruption. Check `stopReason` and
the reports for coverage: reaching a configured budget can still exit 0. JSON
errors use `{ "type": "error", "ok": false, "exitCode": 1, "error": { "message": "..." } }`.
See the [automation contract](docs/project-guide.md#non-interactive-cli) for details.

## Controlled proof of concept

```sh
pnpm test:poc             # Deterministic classifier substitute, two runs
pnpm test:live            # Real Jev calls, two runs; API key required
pnpm test:live:extended   # Ten expanded real-Jev fixture scenarios
pnpm verify              # Format, lint, types, build, deterministic tests
```

Each live command creates a new `output/live-*` directory and writes measurements.
It fails its process when expectations are not met. The initial fixture covers
navigation, a portal-rendered native modal, a required search form, and cycles.
The initial real-Jev gate passed before the expanded fixtures were added.
See [verification results](docs/verification.md) for measured results and defects
found during development.

To inspect the fixture manually, run `pnpm fixture` and visit
`http://127.0.0.1:4173`. The fixture uses only controlled local UI behavior except
for its deliberately excluded write action.

## Configuration and resuming

Copy [the example](config/explore.example.json) into `explore.local.json`, customize
it, then run:

```sh
pnpm explore --config explore.local.json
pnpm explore --config explore.local.json --resume
```

Input keys match, in priority order: candidate key, CSS locator, HTML `name`, label,
accessible-name approximation, then input type. Values are bounded by
`maxInputVariants`. For example, `"inputs": { "q": ["orchid", "fern"] }` explores
two search terms. Input generation never supplies credentials or sensitive values.

Worker counts and tuning settings have no fixed upper bounds. Override
`browserWorkers` and `jevConcurrency` to suit your machine and API capacity.
Shared backend reset mode automatically uses one browser worker so branches cannot
reset each other's data. Jev requests still run concurrently.

State, depth, action, duration, and Jev request budgets are disabled by default.
Set `maxStates`, `maxDepth`, `maxActions`, `maxDurationMs`, or `jevBudget` when you
want a bounded run; omit them or set them to `null` for no cap. Input sampling,
context size, and operation timeouts keep configurable efficiency defaults.

The optional `root` selector must match exactly one element. It scopes only initial
discovery; later changes receive full-page extraction, including portal modals and
controls outside the initial subtree. State identity always uses the broader page.

To resume blocked inputs, add the missing values and use `--resume`. Keep previous
input values in their original positions and append new variants: replay references
their keys and indices without persisting their values. Supply the same starting
URL, identity configuration, model, and authentication state. A changed session or
backend can make replay fail; the tool records that failure and does not act against
the wrong source state. Use a new output directory for an incompatible baseline.

Ctrl+C finishes checkpointing and closes browser contexts. On a hard crash, an
action whose intent was persisted without an outcome is marked interrupted and
is never retried automatically. Pending work can still resume. Use one explorer
process per output directory; browser concurrency is managed inside that process.

## Example applications

The [examples directory](examples/README.md) contains three independently runnable apps: a five-page static site, a React/Vite project tracker with its own backend, and a marketing/dashboard/API platform. Start them with `pnpm example:small`, `pnpm example:medium`, or `pnpm example:big`. Each folder includes setup instructions and a video walkthrough. These apps have not been run through JevExplore.

## Structure

| Location                                  | Responsibility                                               |
| ----------------------------------------- | ------------------------------------------------------------ |
| `apps/cli`                                | CLI argument parsing and shutdown                            |
| `apps/fixture`                            | Controlled application and verification scenarios            |
| `packages/explorer/src/browser.ts`        | Isolated contexts, replay, readiness, execution, observation |
| `packages/explorer/src/extraction.ts`     | Candidate evidence and normalized semantic DOM               |
| `packages/explorer/src/context.ts`        | Bounded context construction                                 |
| `packages/explorer/src/jev.ts`            | Validated HTTP adapter, retries, concurrency, cache, budget  |
| `packages/explorer/src/classification.ts` | Typed Jev questions and decision composition                 |
| `packages/explorer/src/policy.ts`         | Readiness, dependencies, and execution eligibility           |
| `packages/explorer/src/scheduler.ts`      | Traversal, limits, resumption, progress                      |
| `packages/explorer/src/persistence.ts`    | Atomic incremental checkpoints                               |
| `packages/explorer/src/export.ts`         | JSON, HTML, and coverage reports                             |

The structure and tooling follow applicable conventions inspected in
[CorieW/ultimate-project-template](https://github.com/CorieW/ultimate-project-template)
at commit `9f7de3d884c2e2794b9fc1ee995214c9ef3bacdc`: pnpm, Node 24, ESM TypeScript,
`apps/` and `packages/` boundaries, shared `config/`, ESLint, Prettier, and Vitest.
CorieW packages, databases, deployment infrastructure, and monorepo task caching
were omitted because this tool does not need them.

See [the project guide](docs/project-guide.md) for all limits, policy configuration,
the programmatic API, identity behavior, and coverage limitations.
