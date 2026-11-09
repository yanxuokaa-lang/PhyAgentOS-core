# fast-jev (OpenCode plugin)

[![CI](https://github.com/nrdz-labs/fast-jev-opencode/actions/workflows/ci.yml/badge.svg)](https://github.com/nrdz-labs/fast-jev-opencode/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Prunes stale tool calls and bulky results from OpenCode V2 model requests using
TypeSafe's [Jev](https://docs.typesafe.ai). Runs through the `context` hook.

Main guarantees:

- Rewrites only the outgoing request: stored history, `/compact` and automatic
  compaction are untouched.
- Fails open — a missing key, timeout, transport/HTTP error, malformed answer or
  unreadable config leaves the request unmodified.
- Leaves the live turn and the configured protected tool calls in place by
  default.
- Reuses prior decisions across requests and reloads.

## Install

OpenCode loads every plugin folder under its config directory (global
`~/.config/opencode/plugins/`, or per project `.opencode/plugins/`):

```sh
git clone https://github.com/nrdz-labs/fast-jev-opencode.git \
  ~/.config/opencode/plugins/fast-jev
cd ~/.config/opencode/plugins/fast-jev
cp config.example.json config.json   # optional: the compiled defaults apply
```

There is nothing to build and no runtime dependency — only `node:` builtins and
its own files. Development scripts need Node and Bun (see
[`CONTRIBUTING.md`](CONTRIBUTING.md)).

The Jev key is read from `TYPESAFE_API_KEY`, then from
`~/.config/opencode/.env` (the file the `jev` CLI uses; read per request). Put it
there or in the server environment, then restart so the server picks it up:

```sh
opencode service restart
```

Without a key the plugin stands down and logs the reason (fail-open).

The shipped defaults and `config.example.json` are observe-only
(`enabled: true, dryRun: true`): decisions are scored and logged and the request
is left untouched. Going live means `"dryRun": false` in `config.json`. See
[`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) for every field and override.

## Usage

Nothing to turn on once `dryRun` is off: the plugin is active for every session
and project. Edit `config.json` and save — it is re-read on mtime change, so
edits apply to the next request without a restart.

`/jev-prune` reports the current state: enabled/dry-run, cached decisions, how
many would be dropped at the current `keepThreshold`, and the last run's drops,
truncations, saved percentage and latency. It is a report, not a trigger —
pruning happens per model request and cannot rewrite one already dispatched.
Send any message to have the next request prune.

## Compatibility

Built and validated against OpenCode **v2.0.7**: the runtime fixture pins a real
`context` hook payload from that version, and CI type-checks the SDK contracts
against `@opencode/plugin` **2.0.7** and **2.0.8**
([`CONTRIBUTING.md`](CONTRIBUTING.md), [`tests/fixtures/README.md`](tests/fixtures/README.md)).

## Docs

- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — all fields, defaults,
  environment overrides, logs and troubleshooting.
- [`docs/DESIGN.md`](docs/DESIGN.md) — the Jev questions, thresholds and
  guardrails behind the defaults, and where this diverges from upstream.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — setup, checks, fixtures and PR rules.
- [`CHANGELOG.md`](CHANGELOG.md) — release history.
- [`SECURITY.md`](SECURITY.md) — what is read and written, and how to report.
- [`config.example.json`](config.example.json) — a copyable observe-only config.

## License

MIT — see [`LICENSE`](LICENSE). This is the OpenCode counterpart of the Claude
Code [`fast-jev-compaction`](https://github.com/tamaratran/fast-jev-compaction)
plugin; the vendored library keeps its own MIT license in
[`vendor/fast-jev-compaction/LICENSE`](vendor/fast-jev-compaction/LICENSE).
