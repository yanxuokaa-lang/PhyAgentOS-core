# hermes-jev-context-engine

Lossless Hermes context compaction via the TypeSafe / Jev API.

This is a Python port of the MIT-licensed TypeScript plugin
[`tamaratran/fast-jev-compaction`](https://github.com/tamaratran/fast-jev-compaction),
packaged as a Hermes **context engine plugin** named `jev`.

Unlike the built-in `ContextCompressor` (which writes a *summary* — lossy and
can propagate a wrong diagnosis as settled fact), `JevEngine` keeps everything
verbatim: Jev scores each tool call and its full output, and the engine either
keeps them, head-truncates the result, or drops both — never rewrites.

## Install

```bash
cd ~/projects/hermes-jev-context-engine
./install.sh
```

This creates one symlink:

```
~/.hermes/hermes-agent/plugins/context_engine/jev
  -> ~/projects/hermes-jev-context-engine/jev
```

Re-running `./install.sh` is safe (idempotent). To uninstall:

```bash
./install.sh --uninstall
```

## Activate (NOT done by this card)

After install, the engine is loaded but **inactive**. To turn it on, set in
`~/.hermes/config.yaml`:

```yaml
context:
  engine: jev
  jev:
    keep_threshold: 0.5          # P(call/result) at or above this is kept
    preserve_recent_messages: 6  # newest N messages are pinned (never compacted)
    max_state_tokens: 25000      # Jev state budget — staged fitting targets this
    max_request_tokens: 30000    # one request's state + questions budget
    truncate_head_chars: 300     # chars of dropped result to retain
```

The `context.jev.*` block is optional; all keys fall back to upstream defaults.

The `TYPESAFE_API_KEY` env var must be set for the engine to ask Jev. The
key is read from the process env, never written to disk or logged.

## Tests

```bash
cd ~/projects/hermes-jev-context-engine
python3 -m pytest tests/ -q
```

62 tests, no network, no paid API, no Hermes tree on PYTHONPATH. They cover:

* the OpenAI <-> internal adapter (pairing, orphan handling, round-trip)
* token estimation calibrated against upstream's `Math.ceil` semantics
* tool-call collection (pairing + pinning)
* staged state fitting (every stage name, throws when impossible)
* question batching (one request, multiple, no-room)
* decision logic (three `decide_call` branches)
* `apply_decisions` (drops, truncates, object identity preservation)
* `compact` end-to-end with a fake asker
* the HTTP client (request building, response parsing, error mapping)
* the `JevEngine` (token tracking, `should_compress`, fallback paths)
* Hermes-side ABC conformance (skipped without `agent` on PYTHONPATH;
  the loader exercises the real path at engine-load time)

## Independent verification

The unit suite is hermetic and was twice green against a **wrong** contract:
first when `compress()` was `async def` (Hermes calls it synchronously, so every
compaction raised `TypeError: 'coroutine' object is not iterable`), then when
the adapter rewrote the system prompt into a `user` turn and injected synthetic
`user` messages between an assistant `tool_call` and its result.

Neither defect is visible from inside the suite. `verification/` holds the
scripts that caught them — they drive the engine through Hermes' **real plugin
loader**, in Hermes' **real OpenAI message format**, calling `compress()` exactly
as Hermes does:

```bash
cd ~/.hermes/hermes-agent
./venv/bin/python ~/projects/hermes-jev-context-engine/verification/verify_jev_engine.py
./venv/bin/python ~/projects/hermes-jev-context-engine/verification/check_sysprompt.py
./venv/bin/python ~/projects/hermes-jev-context-engine/verification/check_invariants.py
```

| Script | Asserts |
|---|---|
| `verify_jev_engine.py` | no orphaned call/result either way, system prompt kept, fallback path raises nothing with no API key, live path reduces |
| `check_sysprompt.py` | the role sequence in equals the role sequence out |
| `check_invariants.py` | system message byte-identical, no consecutive same-role, each `tool_call` immediately followed by its result, caller's list not mutated, idempotent on a second pass, tiny transcripts survive |

Last run (commit `39b9f0a`): all clean, `problems=NONE` on both paths,
62.1% char reduction on the live path, 62/62 unit tests green.

**Run these after any change to the adapter or the engine.** A green `pytest`
alone has not been sufficient on this codebase.

## Known fragility

The symlink lives **inside** `~/.hermes/hermes-agent/`, which is a git
checkout. Anything that wipes that directory tree (`git clean -fdx`, a
reinstall that recreates `plugins/context_engine/`) removes the symlink.
`install.sh` is idempotent so re-running restores it.

The right long-term fix is an upstream PR making
`plugins/context_engine/__init__.py` honour `$HERMES_HOME/plugins` like the
sibling loaders (`plugins/memory`, `plugins/cron_providers`, `providers`).
That is a separate card.

## File map

```
hermes-jev-context-engine/
├── jev/                        # the engine package
│   ├── __init__.py             # re-exports JevEngine
│   ├── plugin.yaml             # loader metadata
│   ├── _types.py               # Message, ToolCall, CallDecision, …
│   ├── adapter.py              # OpenAI <-> internal bidirectional
│   ├── state.py                # estimate_tokens, fit_state, collect_tool_calls
│   ├── compact.py              # decide_call, apply_decisions, batch_calls, compact
│   ├── request.py              # build_jev_request, parse_jev_response, JevHttpClient
│   └── engine.py               # JevEngine (Hermes ContextEngine subclass)
├── tests/                      # 51 tests, hermetic, no network
│   ├── conftest.py
│   ├── test_adapter.py
│   ├── test_state.py
│   ├── test_state_fitting.py
│   ├── test_compact.py
│   ├── test_request.py
│   └── test_engine.py
├── install.sh                  # one-symlink install (idempotent)
└── README.md
```

## Safety

* The engine never auto-activates. `context.engine` stays `compressor` until
  the operator flips it.
* Any Jev failure (HTTP error, malformed answer, missing key, state that
  cannot be fitted) is caught and the engine falls back to a deterministic
  local trim, logging the reason. The session is never taken down by a
  compaction error.
* `TYPESAFE_API_KEY` is read from the environment; it is never logged,
  written to a file, or returned by any helper.
