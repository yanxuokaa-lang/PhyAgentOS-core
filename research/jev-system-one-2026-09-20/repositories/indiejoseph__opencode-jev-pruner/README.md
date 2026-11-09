# opencode-jev-pruner

OpenCode port of [tamaratran/jev-pruner](https://github.com/tamaratran/jev-pruner):
trim noisy `bash` output with TypeSafe Jev **after the command runs, before
the model sees it**. Fail-open: any error leaves the original output untouched.

```
bash runs -> 10k-token gate -> archive full output -> chunk -> Jev noul per chunk vs history -> rewrite with markers + recovery footer
```

## Scorers: Jev, Jev-Zen, or Zen chat

Default is `scorer: "jev-zen"`: native TypeSafe Jev served through Zen
(`https://opencode.ai/zen/v1/systemone`, model `jev-1.13-free`). It needs **no
key at all** and returns real calibrated `noul` probabilities — same judging
quality as the TypeSafe API, $0 cost.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-jev-pruner"]
}
```

That's the whole setup. Alternatives via plugin options
(`{ "package": "opencode-jev-pruner", "options": {...} }`):

- `scorer: "jev"` — TypeSafe API directly (`TYPESAFE_API_KEY` or `apiKey`
  option, `model` default `jev-latest`). Use this if Zen's free Jev is ever
  rate-limited or unavailable.
- `scorer: "zen-chat"` — relevance judged by a Zen chat model (`zenModel`
  default `deepseek-v4-flash-free`). Needs a Zen key: `zenApiKey` option →
  `OPENCODE_API_KEY` env → the `opencode` entry in opencode's `auth.json` (so
  `/connect` users need no extra setup). This judge is an approximation: the
  `>0.1`-keeps safety net still applies and unparseable scores fall back to
  keep, but retention is less precisely calibrated than with real Jev.

Notes on `jev-zen`:

- The endpoint only accepts the exact id `jev-1.13-free` (override with
  `jevZenModel`; aliases like `jev-latest` are rejected). The paid
  `jev-1.13` requires a Zen key — set `zenApiKey`/`OPENCODE_API_KEY` or
  connect via `/connect` and it is picked up from `auth.json`.
- Each scoring request sends the full state (up to `maxStateTokens`) to the
  model. Consider lowering `maxStateTokens` (e.g. `12000`) and
  `maxScoringRequests` to cut latency.
- Quota/overload (429/529) is retried with exponential backoff (honoring
  `Retry-After` up to 15s, `maxRetries` default 3, `retries` visible in
  diagnostics). Anything still failing fails open — the original output is
  left untouched.

## Install

Local dev:

```
# .opencode/plugins/jev-pruner.ts -> re-export or copy plugin/jev-pruner.ts
export { default } from "/path/to/opencode-jev-pruner/dist/plugin/jev-pruner.js"
```

npm (after publish):

```json
{ "$schema": "https://opencode.ai/config.json", "plugin": ["opencode-jev-pruner"] }
```

## Options

Passed as plugin options object (`{ "package": "opencode-jev-pruner", "options": {...} }`):

| option | default | notes |
|---|---|---|
| `apiKey` | `TYPESAFE_API_KEY` | TypeSafe key (jev scorer) |
| `model` | `jev-latest` | Jev model (jev scorer) |
| `scorer` | `jev-zen` | `jev-zen`, `jev`, or `zen-chat` (`zen` = legacy alias of `zen-chat`) |
| `jevZenModel` | `jev-1.13-free` | exact Zen Jev id; aliases rejected |
| `zenApiKey` | `OPENCODE_API_KEY` → auth.json | Zen key (paid `jev-1.13`, `zen-chat`) |
| `zenModel` | `deepseek-v4-flash-free` | chat model for zen scorer |
| `zenBaseUrl` | `https://opencode.ai/zen/v1` | OpenAI-compatible endpoint |
| `scorerTimeoutMs` | `60000` | per-request timeout (zen scorer) |
| `minTokens` | `10000` | floor, cannot go lower |
| `chunkLines` | `20` | lines per Jev decision chunk |
| `chunkChars` | `0` | optional char target instead of line grouping |
| `keepThreshold` | `0.5` | min noul to keep (`>0.1` also keeps) |
| `maxStateTokens` | `25000` | Jev state budget shared by history+output |
| `maxScoringRequests` | `11` | additional Jev calls beyond the first |
| `maxRetries` | `3` | transport retries per scoring request on 429/529, then fail open |
| `maxChars` | `0` | rendered cap incl. markers; 0 = chunk pruning only |
| `diagnostics` | `false` | log decision JSON via `client.app.log` |

## Behavior (mirrors upstream)

- `bash` only. Pass-through <=10k estimated tokens, binary, JSON/XML/YAML/diff,
  `cat|bat|jq|yq|git diff|git show|diff|base64|openssl`, reference docs/source/disassembly.
- First/last chunks, diagnostics/results (warnings, failures, test totals,
  artifact paths) and unscored chunks always kept.
- Full stdout archived to `.opencode/fast-jev-output/bash-<callID>.txt`
  (self-gitignored) before the first Jev request; footer points there.
  Secret-looking commands/output are pruned without archiving (re-run to recover).
- History comes from `client.session.messages()` mapped to the shared
  `ConversationMessage` shape; current call's result is excluded so output
  isn't duplicated in Jev state. History is partitioned across requests, a keep
  vote in any segment keeps the chunk.

## Layout

- `src/` — verbatim reusable engine (`jev`, `output`, `history`, `retention`, `secrets`)
- `plugin/jev-pruner.ts` — `tool.execute.after` adapter (jev/zen scorer selection)
- `plugin/llm-asker.ts` — `JevAsker` over OpenAI-compatible chat completions
- `plugin/zen-auth.ts` — Zen key lookup (option → env → auth.json)
- `plugin/opencode-history.ts` — SDK message mapper
- `tests/` — mapper, gate, scorer, and auth tests
