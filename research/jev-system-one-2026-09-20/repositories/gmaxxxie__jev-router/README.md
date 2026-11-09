# jev-router

**Per-prompt model routing for [Pi](https://github.com/earendil-works/pi-mono), driven by [Jev](https://docs.typesafe.ai) (TypeSafe System One).**

Every prompt is classified by Jev and served by the cheapest model that can handle it, at a thinking depth adapted to the task — instead of running everything on the frontier model. The decision costs ≈ **$0.00002** and ≈ **0.9 s**.

Adapted from [0xNatoshi/jev-codex-router](https://github.com/0xNatoshi/jev-codex-router) (the Codex Router edition) to Pi: **no local server, no LiteLLM, no format conversion.** The extension calls the local `jev` CLI and switches the session model with Pi's own API, reusing the `openai-codex` (ChatGPT subscription) login Pi already has.

## How it works

```
prompt ──▶ before_agent_start
             ├─ ~/.local/bin/jev @state -q {tier, depth} -j     ← one batched decision
             ├─ policy: tier → model, depth (confidence gate)
             └─ pi.setModel(...) + pi.setThinkingLevel(...)
                   └──▶ the turn runs on the routed model, natively
```

The model catalog already ships the triptych (`gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-6-astra`), so no provider or gateway setup is involved — routing is a model switch on the provider you are already logged into.

## Routing policy

| Tier | Model | Thinking | Use for |
|---|---|---|---|
| ⚡ luna | `gpt-5.6-luna` | **always max** | Mechanical / clearly scoped: renames, formatting, small fixes |
| 🧠 sol | `gpt-5.6-sol` | adaptive (Jev) | Standard implementation, known patterns |
| 🌍 terra | `gpt-5.6-terra` | adaptive (Jev) | Spare lane, unused by default |
| 🚀 astra | `gpt-6-astra` | adaptive (Jev) | Hard / ambiguous: architecture, cross-cutting changes, complex debugging |

When Jev's tier confidence is below the gate (`0.5`, tunable) the router **does not downgrade**: the turn falls back to the **middle tier (sol)** with a minimum depth of `medium`, and the decision is logged as a hold. Over-routing only costs tokens; misrouting costs quality — so uncertainty leans to the heavier model.

**Fail-open**: any Jev error/timeout keeps the current model and logs the failure; the turn always proceeds.

## Operations

| Action | How |
|---|---|
| Watch decisions | `tail -f ~/.pi/agent/jev-router-live.jsonl` |
| On / off | `/jev-router on` · `/jev-router off` (kill switch = `~/.pi/agent/jev-router.off`) |
| Shadow mode (decide + log, don't switch) | `/jev-router shadow` · `/jev-router shadow off` |
| Last 5 decisions | `/jev-router tail` |
| Show policy | `/jev-router policy` |
| Status line | footer: `jev-router: ⚡ luna:max (hold)` |
| Tune | `~/.pi/agent/jev-router.json` |

Start in **shadow mode** for a few days: decisions are logged, nothing changes, and the log is your calibration source.

## Install

```bash
# from a checkout
bash install.sh

# or as a Pi package (if the repo is reachable)
pi install git:github.com/gmaxxxie/jev-router
```

Restart Pi (or `/reload`), pick an `openai-codex` model, then `/jev-router shadow` or `/jev-router on`.

**Requirements**: the `jev` CLI at `~/.local/bin/jev` (TypeSafe key already configured there) and a Pi `openai-codex` login (`/login openai-codex`). Routing only applies while the active model's provider is `openai-codex` — other providers are left untouched.

## Config (`~/.pi/agent/jev-router.json`)

```json
{
  "confidenceGate": 0.5,
  "onlyProvider": "openai-codex",
  "timeoutMs": 10000,
  "excerptChars": 4000,
  "tiers": {
    "luna": { "model": "gpt-5.6-luna", "depth": "max", "glyph": "⚡" },
    "sol":  { "model": "gpt-5.6-sol",  "depth": null,  "glyph": "🧠" },
    "astra": { "model": "gpt-6-astra", "depth": null,  "glyph": "🚀" }
  },
  "hold": { "tier": "sol", "minDepth": "medium" }
}
```

`depth: null` means "use Jev's adaptive depth"; a string pins the tier's thinking level. Illegal values are ignored and fall back to the defaults. `jevBin` can override the CLI path.

## Measured (2026-09-19)

| Prompt | Route | Confidence | Latency | Verification |
|---|---|---|---|---|
| "rename `temp1` to `userId`" | ⚡ luna + **max** | 1.00 | 829 ms | session file confirms the answering model was `gpt-5.6-luna` |
| ambiguous rename request | 🧠 hold → sol + medium | 0.36 | 1031 ms | gate held as designed |
| deadlock analysis | 🚀 astra + **xhigh** | 0.99 | 971 ms | astra answered |
| injected Jev failure | fail-open | — | — | turn completed on the current model |

One decision ≈ 500 input tokens ≈ **$0.00002**.

## Differences from the Codex Router edition

- **No local server / LiteLLM / provider registration** — the extension calls `jev` directly and switches the Pi session model. The gateway (official / OpenRouter) is inherited from the `jev` CLI config, single source of truth.
- **No Codex-dry tandem** (GLM/deepseek substitutes when ChatGPT usage is exhausted) — in Pi that is a `/model` switch to another provider; unported by design.
- **No `service_tier: priority`** — Pi's provider config does not expose it, so luna runs at standard speed with max thinking.
- **Granularity is per user prompt (one agent run)**, not per API call: Pi's agent loop does not switch models mid-run.
- **Scope guard**: only acts while the session model belongs to `onlyProvider`.

## Tests

```bash
node --experimental-strip-types tests/policy.test.ts   # or: npm test
```

16 pure-logic tests over the routing policy: depth clamping, fixed vs adaptive depth, the confidence gate and hold behavior, unknown/missing answers, and config merging.

## License

MIT
