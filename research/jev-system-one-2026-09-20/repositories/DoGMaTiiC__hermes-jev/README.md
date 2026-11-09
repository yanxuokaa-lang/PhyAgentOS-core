# hermes-jev

TypeSafe **[Jev](https://docs.typesafe.ai)** (System One) decision layers for
[Hermes Agent](https://github.com/NousResearch/hermes-agent): typed decisions
(boolean / choice / score) with calibrated probabilities and confidence, served
over the Vercel AI Gateway (`typesafe-ai/jev`). Stdlib only — no Node, no SDK.

```
plugins/
├── jev-judge/          pre-tool gate (shadow/enforce) + jev_ask tool
└── jev-skill-router/   names the one skill worth loading, before the model call
```

## Install

```bash
# clone once, symlink (or copy) the plugin you want
git clone https://github.com/DoGMaTiiC/hermes-jev
ln -s "$PWD/hermes-jev/plugins/jev-skill-router" ~/.hermes/plugins/jev-skill-router
hermes plugins enable jev-skill-router

# catalogue installs (once the entries land) also work:
# hermes plugins install jev-skill-router
```

Put `AI_GATEWAY_API_KEY` (Vercel AI Gateway) in `~/.hermes/.env`. Both plugins
fail open without it — nothing breaks, nothing is sent.

## What each plugin does

| Plugin             | Surface                                                                                                         | Default           |
| ------------------ | --------------------------------------------------------------------------------------------------------------- | ----------------- |
| `jev-judge`        | `pre_tool_call` gate on `terminal`/`write_file`/`patch` (destructive? exfiltration? impact?) + `jev_ask` tool   | shadow (log only) |
| `jev-skill-router` | `pre_llm_call` — asks Jev for at most one skill from the live roster, injects a single `<skill_relevance>` line | off (opt-in)      |

Each plugin has its own README with settings, privacy notes (exactly what leaves
the machine) and verify commands.

## Shared conventions

- **Fail-open, always.** No key, timeout, HTTP error → the turn proceeds untouched.
- **Thresholds live in code**, never in the model — Jev returns probabilities, the
  plugin branches on them.
- **One JSONL line per decision** (`<HERMES_HOME>/logs/<plugin>.log`) so thresholds
  can be re-tuned against real traffic.
- **Opt-in by default**; nothing leaves the machine until a mode is switched on.

## Verify

```bash
python3 tests/test_offline.py            # in each plugin dir
hermes plugins validate plugins/jev-judge
hermes plugins doctor plugins/jev-skill-router --ci
```

## License

MIT — see `LICENSE`. Each plugin keeps its own copy.
