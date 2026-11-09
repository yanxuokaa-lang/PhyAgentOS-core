# jev-model-router

A cost-optimized model router for [OpenRouter](https://openrouter.ai), using [TypeSafe's Jev](https://typesafe.ai) to classify each request and pick the cheapest model that can actually handle it.

Distributed as `jev-model-router`; imported as `model_router` (`from model_router import Router`) -- the PyPI/repo name and the Python import name differ, same as e.g. `scikit-learn` installs as `sklearn`.

## What's different here

There are already several Jev-based routers ([awesomejev.com](https://awesomejev.com) lists a dozen+ as of this writing). Most of them route across a small, hand-curated list of 5-10 models pinned in a config file — you add a new model by editing YAML.

This one reads OpenRouter's **live, full catalog** (hundreds of models) on every routing decision, cached with a short TTL. Nothing is hardcoded. Jev never sees the model list — it only classifies the *request* (domain, complexity) — and a deterministic scoring function in this library ranks the live catalog against that classification. When OpenRouter adds a model, this router picks it up automatically.

It's also a **Python library**, not a proxy: `pip install`, `import`, call a function. No server process to run, no client to repoint at a different base URL.

## How it works

```
prompt + constraints (needs_vision, min_context_tokens, max_price_per_1k_tokens)
   │
   ▼
[1] OpenRouterCatalog.fetch() + .filter()   -- pure code, no AI, cached GET /models
   │   drops models that fail hard constraints
   ▼
[2] JevClassifier.classify(prompt)          -- one Jev call, ~100ms, no text generation
   │   5 narrow questions: domain, complexity, needs_long_context,
   │   needs_vision, latency_sensitive -- never sees the model list
   ▼
[3] scorer.rank()                           -- pure code, no AI
   │   ranks the live candidates by blended (prompt+completion) price,
   │   targeted to a price-percentile derived from classified complexity
   ▼
RoutingDecision(model_id, ranked, profile, raw_jev_response)
```

If the Jev call fails, the router falls back to `rank_cheapest_first` -- a pure cost-based ranking with no fabricated classification -- rather than blocking or guessing. This is configurable (`fail_open` / `fail_closed`).

## Quick start

```bash
pip install -e ".[dev]"
export TYPESAFE_API_KEY=...      # console.typesafe.ai
export OPENROUTER_API_KEY=...    # openrouter.ai/keys
```

```python
from model_router import Router

with Router() as router:
    decision = router.choose_model("Fix this off-by-one bug in my Python loop")
    print(decision.model_id)          # e.g. "mistralai/codestral-2508"
    print(decision.profile.domain)    # "code"
    print(decision.profile.complexity_score)  # 0.71 (of 0-2)
```

Or route and complete in one call:

```python
with Router() as router:
    result = router.complete("What is the capital of France?")
    print(result.completion)
```

## Constraints

Hard requirements the catalog filter applies before Jev is ever called (so an impossible constraint never wastes a classification call):

```python
from model_router import Router, RoutingConstraints

with Router() as router:
    decision = router.choose_model(
        "Describe what's in this image",
        constraints=RoutingConstraints(needs_vision=True, min_context_tokens=32_000),
    )
```

## What data goes where

The prompt text is sent to TypeSafe's Jev API for classification. It is also sent to OpenRouter only when you call `.complete()` (to the model that was chosen). Fetching the model catalog (`.choose_model()`'s first stage) sends no prompt data at all -- it's a plain `GET` of OpenRouter's public model list.

## Configuration

| `Config` field | Env var | Default |
|---|---|---|
| `typesafe_api_key` | `TYPESAFE_API_KEY` | required |
| `openrouter_api_key` | `OPENROUTER_API_KEY` | required |
| `catalog_cache_ttl_seconds` | -- | `600` |
| `on_classifier_error` | -- | `"fail_open"` (or `"fail_closed"`) |
| `confidence_threshold` | -- | `0.5` |
| `weight_complexity_match` | -- | `0.9` |
| `weight_domain` | -- | `0.1` |

## Testing

```bash
pytest                                          # unit tests only, no API keys needed
TYPESAFE_API_KEY=... pytest                     # also runs the real-Jev integration test
TYPESAFE_API_KEY=... OPENROUTER_API_KEY=... python eval/routing_eval.py  # manual, billed sanity check
```

## Status

Built and validated against the live Jev and OpenRouter APIs, twice (once before and once after the blended-pricing change below). `eval/routing_eval.py` result, most recent run, 8 labeled prompts across all 4 domains:

| Prompt | Domain (confidence) | Complexity | Model chosen |
|---|---|---|---|
| "What is the capital of France?" | factual_lookup (1.00) | 0.00 | `inclusionai/ling-3.0-flash-vl:free` |
| "Summarize this sentence: 'The cat sat on the mat.'" | factual_lookup (1.00) | 0.02 | `inclusionai/ling-3.0-flash-vl:free` |
| "Write a haiku about autumn leaves." | creative (1.00) | 0.67 | `qwen/qwen-plus-2025-07-28` |
| "Fix this off-by-one bug in a Python for-loop..." | code (1.00) | 0.71 | `mistralai/codestral-2508` |
| "Design a distributed rate limiter..." | code (1.00) | 1.99 | `openai/gpt-5.3-codex` |
| "Prove that the square root of 2 is irrational..." | math_reasoning (1.00) | 1.20 | `moonshotai/kimi-k2-thinking` |
| "Here's a 40-step logic puzzle..." | math_reasoning (1.00) | 1.98 | `openai/o3-pro` |
| "Translate 'good morning' into Portuguese." | factual_lookup (0.93) | 0.01 | `inclusionai/ling-3.0-flash-vl:free` |

**8/8 decisions matched expectations.** Domain confidence stayed 0.93-1.00 across all cases. Trivial requests correctly landed on a free model; the two genuinely hard prompts (distributed rate limiter design, 40-step logic puzzle) correctly escalated to frontier reasoning models (`gpt-5.3-codex`, `o3-pro`) at the top of the complexity scale (1.98-1.99 of 2.0) -- this is the exact case a min-max pricing bug found in code review would have gotten wrong (see commit history for the fix).

This is a small, directional harness (8 hand-labeled prompts), not a formal benchmark -- it demonstrates the pipeline works end-to-end against real APIs, not a rigorous cost-savings claim. See `docs/superpowers/` for the design spec and implementation plan this was built from, including the full review history (2 Critical bugs found and fixed before merge).

## About this project

This was built end-to-end with [Claude Code](https://claude.com/claude-code), including the architecture decisions, the bug found and fixed in the pricing formula (an earlier version silently routed mid-complexity requests to ~67x the catalog median price -- caught in review before it shipped), and this README. If that's a dealbreaker for you, several alternatives exist on [awesomejev.com](https://awesomejev.com) -- `gargpratyush/jev-router` in particular has real production traction as a proxy-based alternative.

## License

MIT
