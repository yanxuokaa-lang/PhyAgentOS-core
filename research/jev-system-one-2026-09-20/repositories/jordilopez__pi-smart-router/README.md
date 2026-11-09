# pi Smart Router

A [Pi coding-agent](https://github.com/earendil-works/pi-coding-agent) extension that registers a custom provider, `pi-smart-router`, with a single model `pi-smart-router/auto`. Each prompt is classified locally (no extra LLM calls) and routed through a **four-tier** resolver to the best configured **backend model** through Pi's model registry.

The router's classification model and its execution model are separate concerns: the router uses deterministic local heuristics, or an optional configured classifier (an LLM or TypeSafe Jev), to choose a backend, while the selected backend LLM performs the actual work. The `fast` backend is **not** used as a judge unless you explicitly configure it as the classifier.

```
pi -e ./src/index.ts
# then: /model pi-smart-router/auto
```

> **Note:** The default configuration, examples, and testing have only used the `opencode-go` provider. Other providers *may* work but are untested; the session header injection (`x-opencode-session`) is currently `opencode-go`-specific.

## The four tiers (recommended policy)

All routes use pi's built-in `opencode-go` provider (auth: `OPENCODE_API_KEY`, `pi auth opencode-go`, or `/login opencode-go`). Pi's footer keeps showing `pi-smart-router/auto`; the `[pi-smart-router]` route log line identifies the actual backend used for each turn.

| Tier | Route | Backend | Intent |
|---|---|---|---|
| cheap | `cheap-code` | `opencode-go/mimo-v2.5` | Trivial work: greetings, quick questions, mechanical low-risk tasks (renames, formatting, imports, boilerplate, simple CRUD, test scaffolds). Score-driven via `cheapMax` (0.18) plus explicit mechanical-task rules. **Not local** - mimo-v2.5 is a cheap hosted code model. |
| fast | `fast` | `opencode-go/deepseek-v4-flash` | Greetings, quick questions, trivial lookups. |
| balanced | `balanced` | `opencode-go/gpt-5.6-luna` (exact lowercase ID) | The everyday default: normal coding, reviews, multi-file edits. |
| powerful | `powerful` | `opencode-go/kimi-k3` | Genuinely difficult work only: architecture/system design, root-cause debugging, race conditions/concurrency, security vulnerabilities, hard performance bottlenecks, formal proofs/algorithmic reasoning, cross-cutting refactors. |

**Kimi is dramatically more expensive** (an order of magnitude above the other tiers) and is deliberately hard to reach:

- The default `mediumMax` threshold is **0.80**, so only the highest complexity scores reach the powerful tier without explicit rules.
- Explicit powerful rules use **high-confidence phrases only** (e.g. "root cause", "race condition", "system design", "security vulnerability", "performance bottleneck", "formal proof") - never generic words like `analyze`, `debug`, `design`, or `implement`.
- `powerful` is **never** in `fallbacks`; the default fallback chain is `fast` → `cheap-code`.
- Ordinary code-looking prompts are **not** dumped onto cheap-code; they flow through the score tiers to balanced. The only cheap-code rule is scoped to explicit mechanical-task phrases.

## How it works

1. `streamSimple` is called by Pi for `pi-smart-router/auto`.
2. Once per **turn**, the prompt/context is classified locally into features and a weighted **complexity score** (0-1) is computed. The classifier estimates prompt and context tokens, detects code and reasoning signals, counts keyword-group matches, and records whether tools or images are present. It does not call any LLM, inspect the quality of a previous answer, or predict success semantically.
3. A resolver picks a **route** (see [Routing decision order](#routing-decision-order)). Each route maps to a backend `provider/modelId`. When a classifier is configured its verdict selects the tier; otherwise the score is compared with configurable thresholds. Explicit high-confidence rules override both.
4. The request is delegated to the backend provider via `modelRegistry.getProvider(...).streamSimple(...)`, with auth (`apiKey`/`headers`/`baseUrl`) resolved through `modelRegistry.getApiKeyAndHeaders(...)`. All stream events are forwarded unchanged.
5. Tool-call continuations **reuse the turn's route decision** - the backend never changes mid-turn.

### Declared context window of `pi-smart-router/auto`

`pi-smart-router/auto` is a **virtual model** - it is never contacted and has no real context window of its own. Its registered `contextWindow` (1M, mirroring the configured 1M-context backends) exists only for Pi core's view of the router: the UI display and compaction triggering. A smaller declared value would make Pi compact conversations long before the backends were actually full.

Actual per-turn fit is enforced separately and per backend: the resolver checks estimated context tokens against each backend model's own `contextWindow * 0.8` (see [Compatibility checks](#routing-decision-order)). If you add backends with smaller windows than 1M, routing stays correct, but the declared 1M makes compaction timing optimistic.

### How the local complexity score is formed

The classifier is intentionally lightweight and deterministic. It extracts signals from the latest user prompt and the current context, normalizes them to 0–1, then combines them with configurable weights:

- **Prompt size** - an estimated token count using `characters / 4`, normalized against `maxPromptTokens`.
- **Context size** - an estimated count including the system prompt, messages, tool-call arguments, and images. This has a deliberately low default weight so a long-running session does not automatically become a powerful-tier request.
- **Code likelihood** - code-related words and patterns such as fenced code, declarations, file paths, stack traces, and code punctuation.
- **Reasoning likelihood** - reasoning and evaluation language such as “compare”, “why”, “trade-off”, “root cause”, “design”, and “review”.
- **Keyword signal** - matches across reasoning, architecture, debugging, performance, and security keyword groups.
- **Tool signal** - only tools beyond a typical bare Pi coding session baseline (about eight tools) raise this signal. The standard tool set is session state, not prompt difficulty, and does not consume the cheap-tier score budget.
- **Image signal** - whether images are present. This is normally weighted at zero because image support is enforced separately by backend capability checks.

**Injected skill bodies are excluded.** When a skill is invoked, Pi materializes the full `SKILL.md` into the conversation as a `role: "user"` message wrapped in a `<skill name="...">...</skill>` block. The classifier strips those blocks before scoring, so the request is judged on what the user actually wrote — not on the skill's code samples and reasoning prose. Without this, a long code-heavy skill (for example `frontend-ui-engineering`) would saturate the code and reasoning signals and force otherwise trivial requests onto the powerful tier. The stripping is applied consistently to the prompt, rule matching, and the heuristic score.

When a configured classifier (TypeSafe Jev or an LLM) builds its bounded transcript, the skill body is likewise removed — but replaced with a one-line `[skill invoked: <name>]` marker (mirroring `[image omitted]` / `[tool call: ...]`), so the classifier still knows a skill was invoked without the body eating its per-message character budget.

The weighted result is clamped to 0–1 and compared with `cheapMax`, `simpleMax`, and `mediumMax`. With the defaults, scores up to `0.18` target cheap-code, scores through `0.35` target fast, scores up to `0.80` target balanced, and higher scores target powerful. Cheap-code is additionally reachable at any score through explicit mechanical-task rules. These are approximate signals, not a model's semantic assessment of whether it can solve the task.

## Install

### Try it for one session

Run the extension directly without installing it:

```sh
pi -e /path/to/pi-smart-router/src/index.ts
```

### Install globally for your user

Install the package into Pi's global settings (the default; do not use `-l`):

```sh
pi install /path/to/pi-smart-router
```

For this repository:

```sh
pi install /Users/jordi/development/routerrific/pi-smart-router
```

Verify the installation:

```sh
pi list
pi --list-models | grep pi-smart-router
```

After installation, start Pi normally. You no longer need `-e`:

```sh
pi
```

If your `~/.pi/agent/settings.json` contains an `enabledModels` allowlist, add the router explicitly or it will be hidden from the model selector:

```json
{
  "enabledModels": [
    "pi-smart-router/auto",
    "opencode-go/deepseek-v4-flash",
    "opencode-go/mimo-v2.5",
    "opencode-go/gpt-5.6-luna",
    "opencode-go/kimi-k3"
  ]
}
```

Use `pi install -l /path/to/pi-smart-router` only for a project-local installation. Global installs are recorded in `~/.pi/agent/settings.json`; project-local installs are recorded in `.pi/settings.json`.

The extension loads as plain TypeScript (Pi loads extensions via jiti) - no build step. `zod` is a runtime dependency; TypeScript and Vitest are only needed for development.

## Configuration files

Two-file layout:

| File | Purpose |
|---|---|
| `~/.pi/agent/models.json` or `<project>/.pi/models.json` | Standard Pi backend providers/models (untouched; the `opencode-go` catalog is built into pi) |
| `~/.pi/agent/pi-smart-router.json` | Global routing config |
| `<project>/.pi/pi-smart-router.json` | Project routing config (**only loaded when the project is trusted**) |

**Precedence:** project config (if trusted and present) > global config > built-in defaults. A config file that exists replaces the lower-priority one entirely (no deep merge).

Built-in defaults (used when no config file exists) mirror the recommended policy: `fast` → `opencode-go/deepseek-v4-flash`, `cheap-code` → `opencode-go/mimo-v2.5`, `balanced` → `opencode-go/gpt-5.6-luna`, `powerful` → `opencode-go/kimi-k3`; defaultRoute `balanced`; fallbacks `["fast", "cheap-code"]`.

Routes are only resolved when actually selected - backends that don't exist or aren't configured do **not** break the extension; they're skipped and the fallback chain takes over. But **invalid config files fail loudly on load** (see [Troubleshooting](#troubleshooting)).

## Config schema (pi-smart-router.json)

```jsonc
{
  "version": 1,                       // required, must be 1
  "defaultRoute": "balanced",         // required; must exist in routes
  "routes": {
    "<name>": {
      "model": "provider/modelId",    // required, must contain "/"
      "reasoning": "preserve",        // optional: preserve|off|low|medium|high
      "maxTokens": 32000,             // optional output cap (must fit the model)
      "emoji": "🎯"                   // optional footer glyph (max 8 code points)
    }
  },
  "classifier": {
    "weights": {                      // complexity score weights (0-1)
      "promptTokens": 0.1,
      "contextTokens": 0.05,          // deliberately low: long sessions must not
                                      // inflate later prompts into the powerful tier
      "codeLikelihood": 0.25,
      "reasoningLikelihood": 0.35,
      "keywordSignal": 0.15,
      "toolSignal": 0.1,
      "imageSignal": 0                // kept at 0; image support is enforced by
                                      // capability checks, not the complexity score
    },
    "thresholds": {
      "cheapMax": 0.18,                // score <= cheapMax  -> cheap tier (cheap/cheap-code/low-cost/economy)
      "simpleMax": 0.35,               // <= simpleMax       -> fast tier (fast/simple/...)
      "mediumMax": 0.8                // <= mediumMax       -> balanced tier; above -> powerful tier
    },
    "maxPromptTokens": 4000,          // prompt analysis truncation limit
    "maxContextTokens": 100000        // context analysis limit
  },
  "classifier": {                     // optional classifier (see "Classifier" below)
    "model": "typesafe-ai/jev",      // set to enable classification; omit for heuristic-only
    "timeoutMs": 1500
  },
  "rules": [                          // optional, evaluated by priority (desc)
    {
      "id": "hard-debugging",         // required, unique
      "priority": 100,
      "match": {                      // all specified conditions must hold
        "anyKeywords": ["root cause", "race condition"],  // any of these (escaped literal phrases)
        "allKeywords": ["memory", "leak"],                // all of these
        "minPromptTokens": 10,
        "minComplexity": 0.5,
        "code": true,               // prompt looks code-related
        "reasoningRequired": true,  // prompt looks reasoning-heavy
        "hasTools": true,           // tools attached to the context
        "hasImages": true           // images in the context
      },
      "route": "powerful"           // must exist in routes
    }
  ],
  "fallbacks": ["fast", "cheap-code"],  // tried in order after defaultRoute; NEVER include "powerful"
  "observability": {
    "showRouteStatus": true,          // emit the concise decision log line (route/backend/score/turn)
    "logDecisions": false             // emit the detailed decision log (adds rule, reason, explanation)
  }
}
```

User keywords in rules are matched as **escaped literal phrases** (case-insensitive, whitespace-flexible); no arbitrary regex from config is evaluated.

## Routing decision order

For each new turn (re-classified only on `turn_start`):

1. **Explicit rules**, highest `priority` first. A matching rule is used only if its route resolves to an available + compatible backend; otherwise evaluation continues.
2. **Complexity thresholds** (cheap → fast → balanced → powerful): score ≤ `cheapMax` (default `0.18`) → route named `cheap`/`cheap-code`/`low-cost`/`economy`; ≤ `simpleMax` (default `0.35`) → `fast`/`simple`/...; ≤ `mediumMax` → `balanced`/...; above `mediumMax` → `powerful`/.... Alias matching is exact-name first, then name-segment match (e.g. `my-cheap-code-route` matches the cheap tier, but `fastest` does not match `fast`). If the tier route doesn't exist or is unavailable, fall through to `defaultRoute`. When a classifier is configured, this score-derived tier is skipped entirely and the classifier's verdict (or `defaultRoute` on failure) applies (see below).
3. **`defaultRoute`**.
4. **`fallbacks`**, in order.
5. **Any available route** (declaration order).
6. If nothing is available: stream error `NO_FALLBACK_AVAILABLE`.

**Compatibility checks** before a route is accepted:

- images in context require the backend model to list `"image"` in `input` (all four opencode-go models support images)
- estimated context tokens must fit `contextWindow * 0.8` (opencode-go models offer ~1M context, so this rarely binds)
- explicit `reasoning` (`low|medium|high`) requires `model.reasoning`
- route `maxTokens` must not exceed `model.maxTokens`
- the model/provider must exist and have configured auth

## Classifier (optional LLM / TypeSafe Jev)

The heuristic classifier is fast, free, and blind to meaning — prompts near a
tier boundary can land on the wrong side. When a classifier is configured
(`classifier.model`), it classifies **every** new turn instead: the heuristic
score does not select the tier. Without a configured model, the heuristic
thresholds apply as before.

- **Backends** (`classifier.model`):
  - A `typesafe-ai/...` ref (e.g. `typesafe-ai/jev`) is served by the
    `@typesafe-ai/sdk` directly — a fast System One **Choice** judgment over
    `cheap`/`fast`/`balanced`/`powerful`. **This requires `TYPESAFE_API_KEY` in
    the environment** (see [TypeSafe Jev setup](#typesafe-jev-setup)). Without
    it the classifier is treated as unavailable and the heuristic thresholds
    apply instead (the router does not fall back to `defaultRoute` for a
    missing key).
  - Any other `provider/modelId` is called as a one-shot LLM
    (`maxTokens: 4`, `temperature: 0`).
- **What happens:** the classifier sees a bounded recent transcript (≤ ~2000
  tokens) plus the heuristic's own signals and returns a tier. The verdict
  determines the route (it may promote *or* demote, including to `powerful`).
- **Rules win first:** explicit rules are never second-guessed.
- **Unavailable backend is not a failure:** a `typesafe-ai/*` classifier with no
  `TYPESAFE_API_KEY` is detected up front and routes through the heuristic
  tiers, exactly as if no classifier were configured (no per-turn call, no
  timeout). The key is read from the process environment, so export it before
  starting Pi; changing it requires a restart.
- **Failure is not guessed:** timeout (`timeoutMs`, default 1500), auth/stream
  error, or an unparseable answer mean the router skips the tier step and uses
  `defaultRoute` (then the fallbacks chain) — never a heuristic tier.
- **Never:** the classifier cannot point at the router itself
  (`pi-smart-router/*` is rejected at config load).
- **Cost:** one classifier call per new turn (tool-call continuations reuse the
  cached decision).

```jsonc
{
  "classifier": {
    "model": "typesafe-ai/jev",   // omit to use heuristic thresholds only
    "timeoutMs": 1500
  }
}
```

### Why route with Jev

The score thresholds are fast, free, and blind to meaning — semantically equal
prompts land on opposite sides of a boundary ("could you review my changes?"
vs. "analyze this diff"). Jev is a judgment model, not a chat model:

- **Semantic tier choice.** It reads a bounded transcript plus the user request
  and returns one of `cheap`/`fast`/`balanced`/`powerful` with a probability —
  fixing boundary misrouting that keywords cannot.
- **Sub-second and cheap.** One System One Choice call per new turn, no
  multi-step reasoning; tool-call continuations reuse the cached decision.
- **Verdict is final, any tier.** Unlike the old band heuristic it may promote
  *or* demote, including to `powerful` — which is otherwise hard to reach.
- **Bounded context.** The classifier sees the four-tier rubric, a ~2000-token
  recent transcript, and the heuristic's own signals; the transcript is
  untrusted input and is never allowed to be the whole program.
- **Fail-safe.** Missing key → heuristic thresholds; timeout/error/unparseable
  answer → `defaultRoute`; explicit rules always win first; the router can
  never classify itself into a loop (`pi-smart-router/*` is rejected).

Data note: each classified turn sends the bounded transcript (not the full
conversation, not files) to TypeSafe, and usage is billed to your TypeSafe
account. Omit `classifier.model` to stay fully local.

### TypeSafe Jev setup

1. Create a key at [console.typesafe.ai](https://console.typesafe.ai) and export
   it **in the environment that runs Pi** (do not paste it into config files):

   ```sh
   export TYPESAFE_API_KEY="..."   # ~/.zshrc / ~/.bashrc, or a launcher
   ```

2. Configure the router to use it (global `~/.pi/agent/pi-smart-router.json` or a
   trusted project `.pi/pi-smart-router.json`):

   ```jsonc
   { "classifier": { "model": "typesafe-ai/jev", "timeoutMs": 1500 } }
   ```

3. Start Pi and confirm the classifier ran: the footer shows
   `… · classifier` (plus `· <ms>/<in>i/<out>o` once the backend reports
   stats), and the route log line carries `classifier=<tier>`. If you instead
   see `threshold` in the footer, the router did not find a usable key and fell
   back to heuristics.

> **`/typesafe login` is not enough for the router.** The
> [`pi-typesafe`](https://github.com/DevMortimer/pi-typesafe) extension (`pi
> install npm:pi-typesafe`) stores its key in `~/.pi/agent/pi-typesafe/auth.json`
> and is only needed for its own `typesafe_evaluate` tool. The router always
> reads `TYPESAFE_API_KEY` from the environment. Set both if you want the tool
> *and* Jev routing.

Optional: `timeoutMs` bounds the call (default 1500). On timeout the router uses
`defaultRoute` (`balanced` by default) rather than guessing a tier.

The route log line includes `classifier=<verdict>` for classifier-decided turns
(or `classifier=-`); the footer status briefly shows `router: classifying…` while
the call is in flight.

## Turn stability

- The route decision is cached per turn. Within a turn (e.g. tool-call continuations) the **same backend is reused**; only classification/route resolution is skipped - every stream request still delegates to the backend.
- `turn_start` resets the cache. A message-based heuristic (new user prompt after tool results) is kept as fallback safety.
- The backend is never switched after the first stream event; failures after content has been emitted surface as stream errors, not fallbacks.

## Adaptive routing and future upgrades

The router has one limited, opt-in adaptive feature: an **optional classifier** (a small LLM or TypeSafe Jev). When `classifier.model` is configured it classifies every turn and its verdict is final (any tier); explicit rules still win first. It does not retry failed work or observe answer quality. The broader router still has no success/failure feedback loop:

- A backend that is unavailable or incompatible is skipped **before streaming** and the normal fallback order is used.
- Once streaming begins, the selected backend is fixed for the turn. Backend errors are surfaced as stream errors; they are not retried on another route.
- If a user sends a follow-up, that is a new turn and is classified from the new context. A follow-up such as “find the root cause” may naturally score higher, but that is not escalation memory.
- A successful response is not validated by the router. It cannot tell whether a code change is correct unless the user or a later tool result makes that visible in a new request.

Possible future upgrades, deliberately not enabled by the current implementation:

1. **Retry with escalation** - after a pre-output backend failure, retry on the next stronger route (`fast` → `balanced` → `powerful`). This needs safeguards for partial output, duplicate tool calls, cancellation, retry limits, and additional cost. Retrying after partial output is especially risky because the user may already have seen an incomplete answer.
2. **Cross-turn escalation memory** - remember repeated backend errors, failed tests, or unsuccessful attempts and raise a session's minimum tier for subsequent turns. This would need explicit reset/decay rules so one transient failure does not make every later prompt expensive.
3. **Signal-based escalation** - promote when a turn reaches a configurable number of tool calls, repeated tool errors, a context-compaction event, or another observable difficulty signal. Tool-call continuations would need a clear policy for whether the current turn can switch models or only the next turn can.
4. **Fast-LLM pre-classification** - *now available* by setting `classifier.model` to an LLM or TypeSafe Jev ref (see above). It adds latency/cost and sends prompt/context data to an additional model; on failure the router uses `defaultRoute`, and recursive `pi-smart-router/*` refs are rejected at config load.
5. **Model-aware routing** - have either local rules or an optional classifier evaluate “is this task suitable for model X?” rather than only assigning a generic complexity score. Capability checks would still remain authoritative for context windows, images, reasoning, and output limits.

Until one of these policies is implemented, users should treat the route status as the backend selected **before** the turn starts, not as a live assessment of how well the task is progressing.

## Route visibility in Pi's UI

- **Footer status** - after each route decision the footer shows the active backend and how the tier was chosen, e.g. `🎯 balanced · opencode-go/gpt-5.6-luna · threshold`, `⚡ fast · opencode-go/deepseek-v4-flash · classifier`, or `💎 powerful · opencode-go/kimi-k3 · classifier`. When the classifier reports usage, its cost is appended: `· 742ms/350i/47o`. The heuristic complexity score is intentionally omitted (it does not select the tier when a classifier is configured); it remains in the log line. The leading glyph is the route's configured `emoji`, or the built-in glyph for the standard route names (⚡ fast, 🪙 cheap-code, 🎯 balanced, 💎 powerful). Custom routes without an `emoji` fall back to `↳`. On a new turn it briefly shows `router: classifying…` until the decision replaces it, and it is cleared when the session shuts down. This is enabled by default and does not depend on `logDecisions`.
- **No transcript noise** - route decisions are intentionally *not* appended to the transcript; the footer status is the single source of that information. For the full detail (reason, explanation, matched rule), check the log file below.
- **Footer model unchanged** - Pi's normal footer model remains `pi-smart-router/auto`; the footer status line above is where you see which backend actually served the turn.

## Observability (log file)

Diagnostics are written to a **log file, never to stdout/stderr** - raw console output from an in-process extension is painted directly over the pi TUI and corrupts the input line. One log line is emitted per route decision (never includes prompt text) and names the **actual backend**. With the default `showRouteStatus: true` the concise line is logged:

```
[2026-02-14T10:12:33.001Z] [pi-smart-router] route=balanced backend=opencode-go/gpt-5.6-luna score=0.42 turn=3 session=a1b2c3d4
```

Setting `logDecisions: true` switches to the detailed line, which adds the matched rule, decision reason, and explanation:

```
[2026-02-14T10:12:33.001Z] [pi-smart-router] route=balanced backend=opencode-go/gpt-5.6-luna score=0.42 turn=3 session=a1b2c3d4 rule=- reason=threshold detail="Complexity 0.42 (balanced tier) -> route 'balanced'"
```

The log file defaults to `<tmpdir>/pi-smart-router.log` (e.g. `/tmp/pi-smart-router.log` on macOS/Linux) and can be redirected with the `PI_SMART_ROUTER_LOG` environment variable (a leading `~` is expanded; `~user` forms are not):

```sh
PI_SMART_ROUTER_LOG=~/.pi/agent/logs/pi-smart-router.log pi
```

The `session=` prefix (first 8 characters of the Pi session id) disambiguates parallel pi sessions appending to a shared log file. Config-load diagnostics on `session_start` and config errors are also logged to the file; config errors additionally surface as a `ctx.ui.notify` toast in the TUI, and router-originated stream failures are prefixed with their error code (e.g. `BACKEND_AUTH_MISSING: ...`) in the stream error message. No raw prompt data is ever logged or stored in entries.

## Selecting the router

After a global installation:

```sh
pi
# in the TUI: /model pi-smart-router/auto
# or from the shell:
pi --model pi-smart-router/auto
```

When running directly from the repository, include the extension path:

```sh
pi -e ./src/index.ts --model pi-smart-router/auto
```

## Troubleshooting

- **`400 MissingSessionID: Request is missing x-opencode-session`** - Console Go (opencode-go) requires a session header to route requests efficiently. The router forwards Pi's **stable session id** (captured on `session_start` from `ctx.sessionManager.getSessionId()`) as the `x-opencode-session` header on every opencode-go request, so the value stays constant across prompts and tool continuations. If the caller already supplies its own `x-opencode-session` header or `options.sessionId`, that explicit value wins and is forwarded as-is. The header is only injected for `opencode-go` - other providers are untouched.
- **`No credentials configured for provider 'opencode-go'`** - auth missing. Run `pi auth opencode-go`, set `OPENCODE_API_KEY`, or use `/login opencode-go`.
- **`Model not found in registry: provider/modelId`** - the route references a model Pi doesn't know. Check spelling (model IDs are exact and lowercase, e.g. `gpt-5.6-luna`) and run `pi --list-models opencode-go` to see the catalog.
- **`No compatible backend model available for any configured route`** - every route failed the availability/compatibility checks (missing auth, model missing, context window too small for the current conversation, etc.).
- **Config error at startup** - pi-smart-router.json is invalid (bad JSON, unknown route reference, duplicate rule id, malformed `provider/modelId`, wrong `version`). Fix the file; the message names the offending path.
- **Kimi (powerful) shows up more than expected** - check your `mediumMax` (default 0.80) and your rules; the policy deliberately keeps kimi-k3 rare and out of the fallback chain.

## Limitations

- Routing is **per turn, not per tool call**: tool-call continuations keep the turn's route even if the intermediate prompt looks different.
- Token counts are **heuristics** (`chars/4`, images ≈ 512 tokens); treat thresholds as approximate.
- Classification is local heuristics by default (keywords/patterns) with no semantic understanding; configuring `classifier.model` adds a semantic judgment via an LLM or TypeSafe Jev. The `fast` route is an execution backend, not a classifier or judge.
- Routing does not currently evaluate answer quality, test outcomes, tool-loop length, or whether a task is “succeeding” after it starts.
- `reasoning: "off"` cannot force-disable thinking on providers that always think; it only avoids requesting reasoning. `preserve` keeps the session's thinking level.
- Backend availability is evaluated when the decision is made; a backend that dies mid-turn surfaces as a stream error (no mid-turn failover).
- Retry-with-a-stronger-model and signal-based escalation are future design options, not current behavior.

## Development

```sh
npm install
npx tsc --noEmit   # typecheck (resolves pi packages via tsconfig paths)
npx vitest run     # unit tests (classifier, route resolver, config, stream contract)
```

The typecheck/tests resolve `@earendil-works/pi-ai` / `@earendil-works/pi-coding-agent` from the installed Pi CLI (see `tsconfig.json` paths and `vitest.config.ts`); override with `PI_PACKAGE_DIR` if your Pi install lives elsewhere.
