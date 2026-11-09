# 🦎 Lizard

**No cortex required.**

A browser agent driven by deterministic code and [Jev](https://typesafe.ai)
(TypeSafe's System One model) — with **zero LLM calls** in the loop.

Jev decides, code acts. Every decision Jev returns is an integer or an enum,
never text, so the action space is closed by construction: it cannot invent an
element that isn't on the page or emit a malformed selector.

```bash
uv sync && uv run playwright install chromium
cp .env.example .env          # add your TypeSafe key
uv run python scripts/run.py https://www.amazon.in \
  "find a wireless headphone under Rs 2000 delivered within 2 days"
```

```
1. type    searchbox "Search Amazon.in"                conf=0.90
2. scroll                                              conf=0.50
3. click   "Apply the filter Get It in 2 Days"         conf=0.73
4. click   "Zebronics Thunder (2026 Upgrade)"          conf=0.63
5. done                                                → new tab followed

verified: PASS — ₹749 is within the ₹2,000 limit
```

Nobody told it Amazon has a delivery filter. It read the page, found the
control that satisfied "within 2 days", and used it.

![Lizard running on Amazon](docs/hud.png)

The HUD is injected as real DOM, so Playwright's own video capture records
it. Green box and tag mark the chosen element and its confidence; faint
dashed boxes mark everything it was allowed to choose from; the panel shows
the compute/network split and every signal from that single call.

## Status

- [x] Perception layer — page → prunable, typed action space
- [x] Jev client — pooled, typed answers
- [x] Decision loop — 7-question fan-out, deterministic guards
- [x] Deterministic constraints — prices and dates never touch the model
- [x] Trace logger — JSONL, one line per decision
- [x] Overlay / HUD — decisions painted onto the page, captured on video
- [x] Compute vs network split — measured, not estimated
- [x] Jev-selected search terms — fanned-out yes/no per candidate word
- [x] Extractive answers — the answer is located, never composed
- [x] CAPTCHA detection — stops, does not attempt to bypass

## Runs

```bash
uv run python scripts/run.py https://github.com/langchain-ai/langchain \
  "find the contributing guidelines document for this project"

uv run python scripts/run.py https://www.amazon.in \
  "find a wireless headphone under Rs 2000 delivered within 2 days"

# with the on-page HUD, recorded to video, holding 900ms per decision
uv run python scripts/run.py https://www.amazon.in "<task>" \
  --video videos --dwell 900

# race it against an LLM agent (needs ANTHROPIC_API_KEY)
uv run python scripts/race.py https://github.com/langchain-ai/langchain \
  "find the contributing guidelines document" --headed --video videos
```

## Perception benchmarks

Measured on live pages, 1440x900 viewport:

| site | elements | after dedupe | kept | named | tokens | $/call |
|---|---|---|---|---|---|---|
| GitHub repo | 200 | 182 | 182 | 100% | 2186 | $0.000092 |
| Python docs | 250 | 131 | 131 | 100% | 1833 | $0.000077 |
| Amazon search | 395 | 358 | 255 | 100% | 4628 | $0.000194 |
| HN front page | 230 | 183 | 183 | 83% | 2232 | $0.000094 |

A 30-step task costs roughly **$0.0034**.

```bash
uv run python scripts/probe_perception.py
```

## Where the time actually goes

The API's proxy returns `x-envoy-upstream-service-time`, so the split is
measured rather than inferred. One Amazon run, 5 steps, from Bengaluru:

| | ms | share |
|---|---|---|
| Jev compute | 576 | **4%** |
| Network (India ↔ US) | 1,708 | 13% |
| Page loads | 10,914 | **83%** |
| wall | 13,198 | |

Median compute per decision: **118 ms**.

The model is 4% of the run. Making it faster would change almost nothing —
the bottleneck left the model and became the internet. That is the whole
argument for a System One model in an agent loop.

## Measured latency (from India, Sept 2026)

TypeSafe claims 70–500ms. What I actually measured, and where it goes:

| | ms |
|---|---|
| DNS | 3 |
| TCP connect (1 RTT) | 251 |
| TLS handshake (+1 RTT) | 254 |
| request + compute + response | ~350 |
| **fresh connection per call** | **1066** |
| **pooled connection** | **349** |

One network round-trip to the US is ~250ms, so **model compute is ~100ms** —
consistent with TypeSafe's claim. The rest is the Indian Ocean.

**Reusing the TLS connection is a 3x win** (1066ms → 349ms) and is a single
line of client config. It is the difference between the model being faster
than a page load and slower than one.

### Extra questions are genuinely free

| questions | ms |
|---|---|
| 1 | 368 |
| 5 | 369 |
| 15 | 356 |

They evaluate in parallel, so there is no reason to ask one thing at a time.
Fan out everything you might need in a single call.


## The demo reel

```bash
uv run python scripts/demo.py              # all five, recorded to videos/
uv run python scripts/demo.py --only amazon --headed
```

| demo | steps | thinking | cost | result |
|---|---|---|---|---|
| stacked | 11 | 1112 ms | $0.00210 | five constraints, one filter at a time — **₹1,598, PIN + 2-day verified** |
| asyncio | 5 | 270 ms | $0.00072 | `"If a timeout occurs, it cancels aw and raises TimeoutError."` |
| amazon | 3 | 269 ms | $0.00077 | pTron Studio Pro — **₹799 verified against the ₹2000 limit** |
| pydocs | 7 | 691 ms | $0.00141 | `awaitable asyncio.gather(*aws, return_exceptions=False)` |
| github | 3 | 603 ms | $0.00075 | crossed to docs.langchain.com unprompted |
| wikipedia | 2 | 359 ms | $0.00096 | Kolkata Metro |
| pypi | 2 | 88 ms | $0.00010 | detected a bot challenge and stopped |

**The model is 3–5% of elapsed time in every run.** Page loads are the rest.

Each clip lands in `videos/<name>/` as a single `.webm`. The overlay is real
DOM, so Playwright's own capture records it — no screen recorder needed.

## Why the HUD shows two numbers

Each decision costs `compute + network`, and they are measured separately —
the API's proxy returns `x-envoy-upstream-service-time`, so the split is
read, not inferred.

| | typical |
|---|---|
| Jev compute | **~100 ms** |
| Bengaluru ↔ US round trip | **~250 ms** |

TypeSafe serves from the US and has no Indian PoP, so a call from here pays
a quarter-second of distance before the model does anything. That is physics,
not the model: the same call from a US host would be ~100 ms end to end.

Two consequences worth knowing:

- **Connection pooling is worth 3x.** A fresh TLS handshake costs two extra
  round trips. Unpooled, decisions took a measured 1066 ms; pooled, 349 ms.
  It is one line of client config and it is the difference between the model
  being faster than a page load and slower than one.
- **Fan-out is free, and so is a big action space.** 1 question 368 ms,
  15 questions 356 ms. A 5-option choice 63–116 ms of compute, a 255-option
  choice 81–127 ms. There is no reason to ask one thing at a time, and no
  reason to keep the action space small.

## What it cannot do

- **No dropdowns or menus.** A `<button>` that opens a sort menu is not a
  field to type into and not a link to follow; GitHub's "Sort by" defeats it.
- **No vision.** Accessibility-tree only. Canvas-heavy or unlabelled sites defeat it.
- **No synthesis.** Answers are extracted spans, never composed prose.
- **Weak multi-hop reasoning.** There is no reasoner in the loop. The
  Wikipedia game - reach article B from article A using only links - looks
  like an ideal long-running demo and is not: it needs a *plan* ("head
  toward Biology to reach Photosynthesis"), and without one the agent
  wanders into Wikipedia's own meta-pages. Hierarchical drill-down, where
  each step is locally obvious, is the shape that suits a System One model.
- **Long runs over-filter.** Stacking five constraints reaches 11 steps and
  verifies all of them, but the agent keeps applying filters past the point
  of usefulness ("Free Shipping", "3 & above") rather than opening a result.
- **Query wording is the soft spot.** Search terms are *selected* from the
  user's own words by a fanned-out yes/no per word — never generated. It
  handles "which words name the thing" well; it is not a query writer.
- **Bot challenges end the run.** By design — PyPI's search is behind one,
  and the agent stops rather than attempting to get past it.

## Where a run's wall-clock time actually goes

A demo run looked slow — 11 steps taking 80 seconds — so it got measured
rather than guessed at. The result was not flattering:

| | before | share | after |
|---|---|---|---|
| **our own deliberate sleeps** | **41.6 s** | **69%** | **16.9 s** |
| page loads (really the network) | 15.1 s | 25% | 15.2 s |
| Jev compute + network | 3.9 s | 6% | 7.4 s |
| wall | 60.5 s | | 39.5 s |

The loop slept 900 ms after every action and then waited for
`networkidle` with a 3.5 s timeout. On an ad-heavy page the network never
goes idle, so that timeout was paid in full every step — 5.3 seconds of
sleeping per action, while the model accounted for 2%.

Replacing it with a `MutationObserver` that resolves once the DOM has been
quiet for 500 ms cut the waiting by 60% and the wall clock by a third.
There is a real tradeoff underneath: a 220 ms quiet period was faster
still but perceived pages mid-transition, and run quality visibly dropped.

The honest reading of the original "the model is 2% of runtime" is that it
was true, and most of the other 98% was our own `sleep()`.

## Two fixes worth knowing about

**Wording drove a whole failure mode.** The `scroll` action was described as
"Scroll down to reveal more of the page", which reads as correct whenever the
element you want is below the fold — on a filter sidebar, most of them. The
agent would target the right filter at good confidence and then scroll toward
it, repeatedly, until the budget ran out. It never needed to: the executor
clicks by selector and the browser scrolls the element into view itself, so a
listed off-screen element is exactly as clickable as a visible one. Rewriting
`scroll` as "only useful for elements *not* already in the list" removed the
scrolling entirely.

**One word undid ten steps.** The agent clicked a bare "Clear" link and wiped
every filter it had applied. The guard matched "Clear all" and "Clear filters"
but not "Clear" on its own.

## Confidence is load-bearing

The signals are not decoration. `done` is a *claim*, and a hesitant one gets
rejected: on Amazon the agent first called the task complete while still on
the search-results page, with `complete` at 0.43. The loop pushed it one
level deeper, onto the product page, where the price could actually be
checked. Ungated, that run would have "succeeded" without ever verifying
the constraint it was given.
