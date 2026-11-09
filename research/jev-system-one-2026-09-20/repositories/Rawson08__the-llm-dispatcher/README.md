# the-llm-dispatcher

**An LLM router that sits in front of every model call. It uses [Jev](https://typesafe.ai), TypeSafe's
System One decision model, to judge each request and dispatch it to the cheapest model and the lowest
reasoning effort that will do the job, so you stop paying frontier prices for routine work.**

It comes in two shapes that share one decision engine:

1. **An API proxy.** OpenAI-compatible. Point any client at it with `model: "auto"` and it routes
   across the providers you hold API keys for: Anthropic, OpenAI, OpenRouter, and any
   OpenAI-compatible server you declare, including local ones.
2. **CLI wrappers.** `llm-dispatcher claude` and `llm-dispatcher codex` launch the real Claude Code
   or Codex CLI, keep their existing subscription login, and choose the model and effort for each
   turn. No API key is involved. This mode has real restrictions; read
   [CLI wrappers](#cli-wrappers-claude-code-and-codex-with-a-subscription) before using it.

Two implementations with identical behaviour, sharing one catalog and one `.env`:

| | TypeScript (`ts/`) | C# (`csharp/`) |
|---|---|---|
| Runtime | Node 20.12+ | .NET 10 |
| Anthropic | official `@anthropic-ai/sdk` | official `Anthropic` NuGet |
| Jev | official `@typesafe-ai/sdk` | HTTP API (no official C# SDK yet) |
| OpenAI-compatible providers | built-in `fetch` | `HttpClient` |
| Tests | `npm test` (node:test) | `dotnet test` (xunit) |

## Why Jev and not another LLM?

Routing with an LLM costs a slow, expensive call before the real call. Jev returns typed answers
with calibrated probabilities in a few hundred milliseconds for $0.042 per million input tokens,
with free output. A routing decision on a typical request costs well under a hundredth of a cent
and adds roughly 250 to 400 ms. The decision is data, not prose, so the policy lives in ordinary
code you can read, test, and tune.

## How a decision is made

1. **Code extracts facts**: token estimate, whether images or tools are present, requested
   `max_tokens`, the last user message, the system prompt, and recent turns.
2. **Jev answers five questions in one call** (`ts/src/judge.ts`, `csharp/Dispatcher/Judge.cs`):
   - `task` (choice): coding, writing, conversation, analysis, math, extraction, summarization, creative, agentic, other
   - `difficulty` (score 0 to 4): trivial, routine, moderate, hard, frontier
   - `reasoning` (score 0 to 3): none, light, substantial, deep
   - `stakes` (yes/no probability): would a subtly wrong answer be costly?
   - `output_size` (score 0 to 2): short, medium, long
3. **Policy turns answers into a tier and an effort** (`policy.ts`, `Policy.cs`):
   - `need = 0.55·difficulty/4 + 0.30·reasoning/3 + 0.15·stakes` selects tier 1, 2 or 3
   - high stakes never routes to the economy tier
   - low confidence on difficulty bumps one tier up, because Jev said "I'm not sure"
   - effort follows the reasoning score, floored at `high` for hard tasks, `max` only for hard, deep, high-stakes work
   - if Jev is unreachable the fallback is deliberately conservative: frontier tier, high effort
4. **Catalog filter and ranking**: drop models that lack vision or tools the request needs or
   whose context or output caps are too small, keep those whose effective tier meets the need
   (a model's `strengths` lift it one tier for that task), and pick the cheapest by expected cost.
   Effort is snapped to the nearest level the chosen model supports. A local model priced at zero
   wins its tier automatically.
5. **The provider call** carries the effort the right way: `output_config.effort` for Anthropic,
   `reasoning_effort` for OpenAI-compatible APIs, `reasoning.effort` for Codex. Anthropic requests
   are translated to and from the Messages API, including tools, tool results, images, and streaming.

Every response includes a `dispatcher` object and `x-dispatcher-*` headers with the decision,
the rationale, and estimated cost versus a baseline model. Nothing about your prompts is stored;
the ledger keeps tokens, models, and dollars only.

## Quick start

```bash
cp .env.example .env      # paste your keys; the file is git-ignored
```

You need `TYPESAFE_API_KEY` (create one at https://console.typesafe.ai). For the API proxy you also
need at least one provider: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, or an
enabled local provider in `models.json`. The CLI wrappers need no provider key at all.

### TypeScript

```bash
cd ts
npm install
npm run route -- "Write a limerick about tabs versus spaces"   # dry run: decision only
npm run serve                                                   # proxy on http://localhost:8787
npx tsx src/cli.ts claude                                       # Claude Code, routed per turn
npx tsx src/cli.ts codex                                        # Codex, routed per turn
```

### C#

```bash
cd csharp
dotnet run --project Dispatcher -- route "Write a limerick about tabs versus spaces"
dotnet run --project Dispatcher -- serve
dotnet run --project Dispatcher -- claude
dotnet run --project Dispatcher -- codex
```

### Use the proxy from any OpenAI client

```bash
curl http://localhost:8787/v1/chat/completions \
  -H "content-type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"Explain CAP theorem in two sentences."}]}'
```

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8787/v1", api_key="unused-unless-DISPATCHER_API_KEY-is-set")
r = client.chat.completions.create(model="auto", messages=[{"role": "user", "content": "hi"}])
print(r.model, r.model_extra["dispatcher"])
```

Streaming works (`"stream": true`). Requests that name a concrete catalog model such as
`anthropic/claude-sonnet-5` are forwarded unchanged and marked `passthrough`, unless
`DISPATCHER_ROUTE_ALL=1`.

## Providers: one OpenRouter key, local models, or direct keys

Every model in `models.json` belongs to a provider. Three are built in and keyed by env var:

| Provider | Key | What it reaches |
|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | Claude models directly |
| `openai` | `OPENAI_API_KEY` (and optional `OPENAI_BASE_URL`) | OpenAI models directly |
| `openrouter` | `OPENROUTER_API_KEY` | Every `openrouter/*` entry: Claude, GPT, DeepSeek, Gemini, Qwen, and anything else you add |

**A single OpenRouter key is the simplest setup.** The catalog ships OpenRouter mirrors of the
frontier models at the same list prices, so one key gives the dispatcher the whole range from
DeepSeek Flash to Opus 5. Add any OpenRouter model by copying an entry and changing `model` to
its OpenRouter slug.

**Local models** work through any OpenAI-compatible server. Declare the endpoint under
`providers` and reference it from models:

```json
"providers": {
  "ollama": { "baseUrl": "http://localhost:11434/v1", "apiKeyEnv": null, "enabled": true }
},
"models": [
  { "id": "ollama/qwen3:8b", "provider": "ollama", "model": "qwen3:8b", "name": "Qwen3 8B (local)", "tier": 1,
    "price": { "input": 0, "output": 0 }, "context": 32768, "maxOutput": 8192, "vision": false, "tools": true, "effort": [] }
]
```

The catalog ships Ollama and LM Studio examples with `"enabled": false` so a machine without a
local server never routes to one. Flip it to `true` once the server is running. A zero price means
the local model wins its tier whenever the request qualifies, and the ledger then reports the
avoided cloud cost as savings. Be honest with the `tier`: a small local model belongs in tier 1
even though it is free.

Local models cannot be used by the CLI wrappers, because those route only among models the
wrapped CLI's own service offers.

## CLI wrappers: Claude Code and Codex with a subscription

```bash
llm-dispatcher claude [any claude args]     # e.g. llm-dispatcher claude --resume
llm-dispatcher codex  [any codex args]      # e.g. llm-dispatcher codex exec "fix the failing test"
```

Each wrapper starts a loopback proxy on `127.0.0.1`, launches the real CLI pointed at it, and exits
when the CLI exits. The CLI keeps its own login, tools, permissions, sessions, and keybindings.

**How it stays inside each CLI's supported configuration.**

- Claude Code is pointed at the proxy with `ANTHROPIC_BASE_URL` and gets a **Dispatcher** row in its
  `/model` picker via `ANTHROPIC_CUSTOM_MODEL_OPTION`. Both are documented Claude Code variables.
  Anthropic's gateway documentation states that with only a base URL set and no gateway credential,
  the saved claude.ai login remains the active credential and its usage limits apply. The proxy
  forwards Claude Code's own headers unchanged, including the OAuth capability header, to
  `api.anthropic.com` (or to whatever `ANTHROPIC_BASE_URL` you already had).
- Codex gets a temporary `model_providers.dispatcher` entry with `requires_openai_auth = true`, a
  documented Codex option meaning "use my existing OpenAI login for this provider". The proxy
  forwards Codex's own headers to the ChatGPT Codex backend for subscription logins, or to the
  platform API for API-key logins.

**What the proxy changes.** On the first request of each fresh user turn it asks Jev the five
questions, then rewrites `model` and the effort field. Tool-loop continuations reuse that turn's
decision so the model never changes mid-task. Auxiliary calls with no tools (session titles,
summaries) go to the cheapest model. Requests that name a concrete model are forwarded untouched,
so picking a model in `/model` pauses routing and picking **Dispatcher** resumes it. When routing
down to a model that rejects a field the CLI composed for a stronger one, the proxy removes or
folds it: adaptive thinking and effort for Haiku, mid-conversation operator messages for Sonnet
and Haiku, `minimal` effort for Codex.

**Seeing the decision.** Claude Code's UI shows the model it asked for, never the one that
answered, so the wrapper installs a status line (unless you already have one, or set
`DISPATCHER_NO_STATUSLINE=1`) that reads, for example,
`⚡ claude-haiku-4-5 (math, jev p=0.98) · my-project · 8% context`. Codex has no status line; the
last decision is written to a status file in your temp directory and every decision is appended to
the ledger. Set `DISPATCHER_DEBUG=1` to print each proxy decision to stderr.

### Restrictions of the CLI wrappers

Read these before relying on the wrappers.

1. **You are still bound by Anthropic's and OpenAI's terms.** The wrappers use only documented
   configuration surfaces of the official CLIs and forward each CLI's own credentials to the same
   service, without reading, storing, or logging them. They do not let anything other than the
   official CLI use your subscription. Do not expose the loopback proxy beyond your machine, do not
   point other clients at it, and do not share the account. If either company changes its terms or
   its CLI's behaviour, the wrapper may stop being appropriate or stop working. That judgement is yours.
2. **Only the models your subscription offers, from the same vendor.** The Claude wrapper routes
   among Claude models only; Anthropic explicitly does not support routing Claude Code to non-Claude
   models through a gateway. The Codex wrapper routes among the OpenAI models available to your
   ChatGPT plan. Local models, OpenRouter, and cross-vendor routing are API-proxy features only.
3. **Savings are quota, not dollars.** A subscription has usage limits weighted by model. Routing
   routine turns to Haiku or Luna stretches those limits; it does not lower your bill. The ledger's
   dollar figures for wrapped sessions are estimates of what the same tokens would have cost at
   API prices, useful for comparison only.
4. **Your prompts go to TypeSafe.** The text of each fresh user turn, the system prompt excerpt,
   and recent messages are sent to Jev for the routing decision. Tool outputs are not, and no
   prompt text is stored locally. If that is unacceptable, do not use either mode.
5. **A key in your shell overrides the login.** If `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set
   in the environment that launches the wrapper, the CLI will use and bill that key instead of your
   subscription. The wrapper strips keys it loaded from `.env` for exactly this reason, but a key you
   exported yourself is treated as your deliberate choice.
6. **The CLIs' request formats are not public contracts.** Fresh-turn detection, effort fields, and
   the model picker hook depend on how Claude Code 2.1 and Codex 0.15 behave today. A CLI update
   can break routing; when it does, requests still go through untouched or fail loudly, they are
   never silently sent to a stronger model than the CLI asked for.
7. **Effort control is what the CLI exposes.** The wrapper sets Anthropic's `output_config.effort`
   or OpenAI's `reasoning.effort`; it cannot grant a model capabilities its provider does not offer.
   Codex will warn that model metadata for `dispatcher-auto` was not found; that warning is
   cosmetic.
8. **Prompt caching is per model.** Switching models between turns forfeits cache reuse on the next
   request. For long agentic sessions where cache matters more than model choice, pick a concrete
   model in the picker and let the wrapper stand aside.
9. **Not affiliated.** This project is not affiliated with, endorsed by, or supported by Anthropic,
   OpenAI, or TypeSafe.

## Endpoints (API proxy)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/chat/completions` | OpenAI-compatible completion; `model: "auto"` routes |
| POST | `/v1/route` | Decision only, no upstream call. Cheap way to see what the dispatcher would do |
| GET | `/v1/models` | `the-llm-dispatcher/auto` plus every model with a usable provider |
| GET | `/stats` | Ledger totals: spend, baseline spend, Jev spend, savings, per model, per task |
| GET | `/health` | Liveness and whether Jev routing is enabled |

Per-request overrides go in the body under `dispatcher_options`:

```json
{ "model": "auto", "messages": [...], "dispatcher_options": { "min_tier": 2, "max_tier": 3, "baseline": "openai/gpt-6-astra" } }
```

## The catalog

`models.json` at the repo root is shared by both implementations. Each entry has a provider,
the provider's model string, prices per million tokens, context and output caps, whether it
takes images and tools, the effort levels it accepts, and a **tier**: your belief about its
general quality (1 economy, 2 standard, 3 frontier). `strengths` lifts a model one tier for the
listed tasks; `weaknesses` lowers it. Prices were checked on 2026-09-17 against Anthropic's price
list and OpenRouter's public models API. Edit the file freely; both implementations validate it on
load. Point `DISPATCHER_CATALOG` at your own file to keep a private catalog.

Tiers are the part you should tune. They encode a quality opinion, not a measurement. Run your own
traffic through `/v1/route` for a day, look at the ledger, and move models between tiers until
the decisions match what your team would choose by hand.

## Configuration

All configuration is environment variables, loaded from `.env` in the working directory or any
parent up to three levels (so both `ts/` and `csharp/` find the repo-root file). See
`.env.example` for the full list. The dispatcher reports whether a key is present and never its value.

## Library use

TypeScript:

```ts
import { Dispatcher } from "the-llm-dispatcher";
const dispatcher = new Dispatcher();
const decision = await dispatcher.route({ model: "auto", messages });   // no upstream call
const { response } = await dispatcher.complete(request);                 // route + call + ledger
```

C#:

```csharp
var dispatcher = new Dispatcher();
var decision = await dispatcher.RouteAsync(request);
var (_, response) = await dispatcher.CompleteAsync(request);
```

## Prior art

Jev launched days before this project and several routers appeared at once. If one of these fits
you better, use it:

- [prismhq/jev-router](https://github.com/prismhq/jev-router): Python, LiteLLM transport, model choice only
- [gargpratyush/jev-router](https://github.com/gargpratyush/jev-router): wraps the Claude Code and Codex CLIs with two-tier routing; the wrapper mode here follows the same documented hooks
- [mejiasd3v/pi-jev-router](https://github.com/mejiasd3v/pi-jev-router): model plus thinking level for the Pi coding agent via Vercel AI Gateway
- [BunsDev/typesafe-router](https://github.com/BunsDev/typesafe-router): TypeScript library that picks among abstract option ids
- [tylerjharden/ailerix](https://github.com/tylerjharden/ailerix): hosted OpenRouter-style product on an Artificial Analysis Pareto frontier

the-llm-dispatcher differs in combining all of: a general OpenAI-compatible proxy, native
Anthropic and OpenAI-compatible transports with no gateway dependency, local models, model
**and** effort selection with the effort actually applied per provider, a transparent code-owned
policy with confidence gating, a cost ledger, CLI wrappers, and two first-class language
implementations.

## Caveats

- Jev's judgments are calibrated but not infallible. Keep `DISPATCHER_BASELINE` honest and watch
  `/stats`. If quality drops for a task type, raise the tier thresholds or add `strengths`.
- Anthropic's `xhigh` and `max` effort levels, forced tool choice, mid-conversation system
  messages, and sampling parameters are model-dependent; the catalog and the provider bridge
  encode what is known as of September 2026.
- The API proxy holds your provider keys. Set `DISPATCHER_API_KEY` before exposing it beyond localhost.

## License

MIT.
