# JevRouter

**Drop-in decision / routing layer powered by [TypeSafe Jev](https://typesafe.ai) (System One).**

Jev returns **only typed decisions** — `Choice`, `Noul` (yes-probability), `Score` — **no text generation**. Your code owns control flow; JevRouter asks atomic questions and applies confidence gates.

```ts
import { defineRoutes, defineModelTiers } from "jevrouter";

const router = defineRoutes([
  { name: "billing", description: "Payments, refunds, invoices" },
  { name: "support", description: "Bugs and product help" },
  { name: "other", description: null },
]);

const { route, action, confidence, probabilities } = await router.route(
  "I was charged twice — please refund",
);
// action === "assign" | "review"
```

## Why JevRouter?

| | **Semantic Router** | **RouteLLM** | **JevRouter** |
|---|---|---|---|
| Job | Intent / tool / semantic routes | Strong-vs-cheap LLM routing | **Both**, one API |
| Model | Embeddings + similarity | Router classifier / LLM | **Jev System One** (typed decisions) |
| Outputs | Top route / score | Model tier | `Choice` + optional `Noul`/`Score` + **confidence gates** |
| Hallucination surface | Embedding drift, threshold tuning | Router errors | Constrained options — no free-form text |

Use JevRouter when you want **calibrated probabilities and confidence** on the request path (tens–hundreds of ms class for Jev), without parsing JSON from a chat model.

### Two modes

1. **Intent / tool / semantic routes** — `defineRoutes` → Jev `Choice` (+ optional `Noul` in-domain gate, `Score` annotation).
2. **Strong-vs-cheap LLM routing** — `defineModelTiers` → `Choice` `{strong, weak, refuse}` + `Score` difficulty (RouteLLM-style).

## Install

```bash
pnpm add jevrouter
# includes @typesafe-ai/sdk
```

Node **20+**, ESM.

Set `TYPESAFE_API_KEY` for live calls. Without it, JevRouter uses a **deterministic offline mock** (keyword heuristics) so demos and CI work with zero secrets.

### Alternate clients (not required)

- **Vercel AI SDK** — `experimental_evaluate` with `typesafe-ai/jev` (when available in your AI SDK version).
- **Raw HTTP** — `POST https://api.typesafe.ai/v1/systemone` with `Authorization: Bearer $TYPESAFE_API_KEY`.

JevRouter talks through a thin `JevProvider` interface: the default implementation prefers `@typesafe-ai/sdk`, then falls back to HTTP. Tests inject a mock provider.

## Quickstart

```bash
cp .env.example .env   # optional: add TYPESAFE_API_KEY
pnpm install
pnpm demo              # mock if no key, live if set
pnpm test && pnpm build
```

### Intent routing

```ts
import { defineRoutes } from "jevrouter";

const router = defineRoutes(
  [
    { name: "billing", description: "Payments, refunds, invoices" },
    { name: "technical", description: "Bugs, API errors" },
    { name: "other", description: null }, // explicit catch-all
  ],
  {
    model: "jev-latest", // or pin: "jev-1.13.0"
    policy: { minConfidence: 0.6, minSelectedProb: 0.7, minMargin: 0.15, minChars: 12 },
    gateNoul: {
      instructions: "Is this an in-domain support message?",
      minYes: 0.5,
    },
  },
);

const result = await router.route(userMessage);
if (result.action === "assign") {
  await handlers[result.route](userMessage);
} else {
  console.info("review", result.reason); // short_input | low_margin | ...
  await escalateToHuman(result);
}
```

### Model tier routing

```ts
import { defineModelTiers } from "jevrouter";
import { selectOpenRouterModel } from "jevrouter/adapters/openrouter";

const tiers = defineModelTiers({
  strong: "openai/gpt-4o",
  weak: "openai/gpt-4o-mini",
});

const sel = await selectOpenRouterModel(tiers, userMessage);
if (!sel.openrouterModel) {
  // refused or review-with-fallback=none
} else {
  // call OpenRouter / LiteLLM with sel.openrouterModel
}
```

## Production hardening (1.1+)

Jev can be **overconfident on junk** (`"??"`, emoji-only, `"help"` → conf≈1). From **1.1.0**, JevRouter applies a **policy layer independent of model confidence**:

```ts
import { defineRoutes, productionPolicy, demoPolicy } from "jevrouter";

const router = defineRoutes(routes, {
  policy: productionPolicy(), // library default in 1.1.0
});

const { action, reason, margin, entropy } = await router.route(userMessage);
// reason?: "short_input" | "low_margin" | "multi_intent" | "refuse" | ...
```

### Recommended production policy

| Gate | Default (`productionPolicy`) | Effect |
|------|------------------------------|--------|
| `minChars` / `minTokens` | 12 / 2 | Ultra-short → `review` (`short_input`) **before** calling Jev |
| emoji / punct / empty | on | Force review (`short_input` / `empty_input`) |
| `minConfidence` / `minSelectedProb` | 0.6 / 0.7 | Classic confidence gate |
| `minMargin` (top-1 − top-2) | 0.15 | Ambiguous two-way ties → `low_margin` |
| `maxNormalizedEntropy` | 0.85 | Flat distributions → `high_entropy` |
| `detectMultiIntent` | true (`defineRoutes`) | Dual keyword hit across routes → `multi_intent` |
| `maxChars` / `onMaxChars` | 16000 / `truncate` | Huge pastes truncated (or `review` if configured) |

**Model tiers:** same short-input / margin / entropy gates; `refuse` → `review` (`reason: "refuse"`). Multi-intent is off by default for tiers.

**Demos / migration from 1.0:** pass `policy: demoPolicy()` to disable short-input and margin gates (loose 1.0-style behavior).

### Tradeoffs

- Raising `minChars` blocks more junk but may review valid short intents (`"refund"`).
- Raising `minMargin` sends more ambiguous tickets to humans (safer, more review load).
- `detectMultiIntent` is a **cheap heuristic** (no extra Jev call) — disable if your route descriptions share too many tokens.

## Confidence gates

Defaults live inside `productionPolicy()` (override via `policy` or legacy `thresholds`):

| Condition | Result |
|-----------|--------|
| Pre-flight input quality fails | `action: "review"` + `reason` (often without calling Jev) |
| `confidence ≥ minConfidence` **and** selected `probability ≥ minSelectedProb` **and** margin / entropy OK | `action: "assign"` |
| otherwise | `action: "review"` + `reason` |

Additional rules:

- Optional **Noul gate**: if yes-probability < `minYes`, force `review` (`noul_gate`).
- Model tier **`refuse`**: always `action: "review"` (`refuse`).
- Unknown Choice labels are coerced to the best known option and forced to `review` (`unknown_label`).

Tune on **your** labelled traffic; pin a versioned model id (`jev-1.13.0`) once calibrated — `jev-latest` can move.

## Public API

| Export | Purpose |
|--------|---------|
| `defineRoutes(routes, opts?)` | Intent/tool router → `.route(query)` |
| `defineModelTiers({strong, weak, refuse?}, opts?)` | Model router → `.selectModel(query)` |
| `productionPolicy` / `demoPolicy` / `resolvePolicy` | Safety policy presets |
| `preflightInputGate` / `postDecisionGate` | Gate helpers |
| `decideAction` / `resolveThresholds` | Legacy confidence helpers |
| `DEFAULT_MIN_CONFIDENCE` / `DEFAULT_MIN_SELECTED_PROB` | Gate defaults (0.6 / 0.7) |
| `createMockProvider` / `createTypesafeProvider` / `resolveProvider` | Provider plumbing |
| `hasLiveApiKey` | Detect live API key (env or options) |
| `choiceQuestion` / `noulQuestion` / `scoreQuestion` | Wire-format builders |
| `asLangChainRouter` / `dispatchRoute` | LangChain helpers (`jevrouter/adapters/langchain`) |
| `selectOpenRouterModel` / `toLiteLLMModelMap` | OpenRouter / LiteLLM helpers |

Result shapes:

```ts
// route()
{ route, probabilities, confidence, action: "assign" | "review", reason?, margin?, entropy?, noul?, score?, model? }

// selectModel()
{ tier: "strong" | "weak" | "refuse", modelId, refuse, action, reason?, margin?, entropy?, confidence, probabilities, difficulty?, model? }
```


## Design rules

- **Code owns control flow** — Jev never emits prose to execute.
- **Atomic questions only** — one Choice for the route/tier; optional Noul/Score alongside.
- **Model pin configurable** — default `jev-latest`.
- **No secrets in repo** — `.env.example` only; CI uses mocks.

## Scripts

| Script | Description |
|--------|-------------|
| `pnpm build` | Compile `src/` → `dist/` |
| `pnpm test` | Vitest with mocked client (no API key) |
| `pnpm demo` / `jevrouter` | CLI demo (mock or live) |
| `pnpm example:routes` / `example:models` / `example:mock` / `example:combined` | Examples |
| `pnpm bench` | **Synthetic** DEMO comparison table — not real accuracy |

## Limits (honest)

- Jev is **not** a generative model — wrong tool if you need free-form answers.
- Routing quality depends on **clear option descriptions** and calibrated thresholds.
- The offline mock is for **CI/demos**, not production accuracy.
- `bench/` prints **labelled-as-demo synthetic figures** — do not cite as real benchmarks vs Semantic Router or RouteLLM.
- English tends to work best per TypeSafe guidance; other languages vary.

## Publish later

This tree is ready to zip and hand off. When you want it public:

```bash
# add a GitHub remote yourself, then:
git remote add origin git@github.com:YOU/jevrouter.git
git push -u origin main
pnpm publish --access public
```

## License

MIT
