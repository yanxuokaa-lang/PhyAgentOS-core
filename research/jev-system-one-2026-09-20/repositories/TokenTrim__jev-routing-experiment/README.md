# Jev as an LLM router on RouterArena

Can [TypeSafe's **Jev**](https://docs.typesafe.ai/) decision model route queries across a pool of LLMs
cost-efficiently? This repo runs Jev as a router on [**RouterArena**](https://github.com/RouteWorks/RouterArena)
(ICLR 2026, [arXiv:2510.00202](https://arxiv.org/abs/2510.00202)) and scores it with RouterArena's own
offline scorer, so the numbers are directly comparable to the public leaderboard.

Jev is not a text model. It returns typed decisions (Choice / Score / Noul) with calibrated
probabilities and confidence in a single forward pass, billed on input tokens only (~$0.042/1M, output
free). That makes it a natural fit for routing: one structured call picks a model.

> **Headline:** on **LLMRouterBench**'s 13-model flagship pool (GPT-5, Claude-4, Gemini-2.5-Pro,
> DeepSeek, Qwen3-235B…), a Jev-difficulty + retrieval router **beats the best single model** — 62.4%
> vs 60.3% accuracy at lower cost, or best-single accuracy at **33% lower cost** — evaluated by lookup
> on precomputed answers (no inference). Honest caveat: the gain comes from the retrieval evidence; a
> **no-Jev ablation matches it**, so Jev's difficulty signal did not add measurable value here. Details
> below. A separate zero-cost RouterArena pilot (3 cached models) is further down.

## LLMRouterBench — beating the best single model on a modern flagship pool

[LLMRouterBench](https://github.com/ynulihao/LLMRouterBench) ships precomputed, scored answers for a
performance-cost pool of **13 flagship models** across many datasets, so a router is evaluated purely by
**lookup — zero inference cost**. We route the **8 datasets where all 13 models are present** (aime,
livemathbench, gpqa, hle, livecodebench, mmlupro, simpleqa, arenahard): **11,668 queries**, split 50/50
into a dev half (for retrieval evidence + model costs) and a held-out **eval half (5,835 queries)**.

The router: for each eval query, retrieve similar **dev** queries and read each model's accuracy on them
(kNN evidence); Jev rates the query's difficulty on a frozen rubric; selection trades predicted success
against cost, with Jev's difficulty setting how much cost to tolerate. Nothing from the eval split and no
ground-truth score ever enters Jev or the selection.

| On the eval half (5,835 queries, 13-model pool) | Accuracy | Cost/1k | vs best-single |
|---|---|---|---|
| **Jev difficulty + evidence** (best acc ≤ best-single cost) | **62.4%** | $26.73 | **+2.1 pts, 15% cheaper** |
| Jev difficulty + evidence (match best-single acc) | 60.3% | $21.09 | **33% cheaper** |
| Evidence only — no-Jev ablation | 62.4% | $26.69 | +2.1 pts (≈ identical to Jev) |
| best single model (gpt-5) | 60.3% | $31.55 | — |
| oracle (cheapest correct model per query) | 82.6% | $4.83 | upper bound |
| gpt-5 / gemini-2.5-pro / qwen3-235b (single) | 59.9 / 60.2 / 55.4% | 31.7 / 55.7 / 0.76 | reference |

![LLMRouterBench frontier](results/llmrb_frontier.png)

**What's real:** the router genuinely beats the best single model on **both** axes — more accurate than
gpt-5 at lower cost, and it can match gpt-5's accuracy at a third of the cost. That's a legitimate
routing win on a current, strong pool, at zero inference cost.

**What Jev did and didn't do (honest ablation):** the win is driven by the **retrieval evidence**, not
Jev. The no-Jev ablation lands on the same frontier (and is slightly cheaper at the cost-sensitive end),
so Jev's difficulty signal was **largely redundant** with neighbour evidence on this benchmark — it
shifts where on the frontier you sit, not how far out the frontier reaches. We report it that way rather
than attributing the gain to Jev. A large **oracle gap remains** (82.6% vs 62.4%): most queries are
answered by only a few models, and neither router reliably recalls them — a model-recall problem, not a
difficulty-estimation one.

Total Jev spend for this experiment: **~$0.13** (5,835 difficulty calls). Reproduce: download
LLMRouterBench's `bench-release`, then `jev-router llmrb-run`.

### The RouterArena pilot (separate, 3 cached models)

The earlier pilot below is a smaller, separate experiment on RouterArena's 3 cached models. The full
8,400-query RouterArena run over a strong pool would need candidate-model inference budget; the harness
and validated scorer are ready for it.

## Pilot results — routing 100 cached RouterArena queries

100 fixed examples from RouterArena Sub_10 (seed `20260917`), routed among the three models RouterArena
ships cached answers for. Answers and correctness come from that cache, so **no candidate LLM is
called** — the only paid call is the router's own decision. Each router sees only the request text plus
three frozen capability labels; cached answers and ground truth never enter a router's input.

| Router / model (100-example Sub_10 pilot) | Accuracy | Answer $/1k | Routing $/1k | Total $/1k | Arena ×100 | Decision latency |
|---|---|---|---|---|---|---|
| **Jev — difficulty rubric** (TypeSafe System One) | **69.5%** | 0.083 | 0.032 | 0.115 | **69.7** | median **311 ms** |
| **Jev — capability labels** | 67.1% | 0.100 | 0.025 | 0.125 | 67.4 | median 320 ms |
| **GLiClass** (`gliclass-instruct-large-v1.0`, hosted demo) | 69.1% | 0.092 | ~0 | 0.092 | 69.3 | median 1.46 s |
| gemini-2.0-flash-001 — cheapest **and** best-fixed (hindsight) | 77.1% | 0.048 | — | 0.048 | 77.1 | — |
| gpt-4o-mini | 64.1% | 0.090 | — | 0.090 | 64.7 | — |
| claude-3-haiku-20240307 | 57.1% | 0.185 | — | 0.185 | 57.7 | — |

![Pilot: accuracy vs cost](results/pilot_accuracy_vs_cost.png)

**Defining difficulty helped Jev.** Giving Jev an explicit, frozen difficulty rubric (easy / medium /
hard, with concrete anchors — see below) instead of bare capability labels raised routed accuracy from
67.1% to **69.5%** *and* lowered answer cost ($0.100 → $0.083/1k), because Jev graded 58% of queries
"easy" and sent them to the cheap-and-strong model. Jev's difficulty grades: 58 easy, 33 medium, 9 hard.
This is the router's best configuration here and edges out GLiClass, still at median ~311 ms and 100/100
with zero failures. **Total Jev spend across both runs: under $0.006.**

**But no router beat the best single model.** On this pool `gemini-2.0-flash-001` is both the cheapest
and the most accurate model, so any routing that sends work elsewhere loses ground. Every router beat
the two weaker single models but none matched gemini (77.1%). Routing only pays off when no single model
dominates the pool — a property of this small three-cheap-model pool, not of the routers. The difficulty
rubric helped precisely because it concentrated more "easy" traffic on the dominant model.

**Frozen difficulty rubric** (model-agnostic; *not* derived from RouterArena's own difficulty labels):
easy = a single fact recall or one-step lookup; medium = two to four dependent reasoning steps in one
domain; hard = long multi-step reasoning, specialized knowledge, or code that must run.

Caveats, stated plainly:
- This is a **100-example Sub_10 subset** over a **three-cheap-model pool** (the only models with free
  cached answers). It is **not** comparable to official full-8,400 leaderboard entries.
- GLiClass ran on a **free hosted demo**; its latency includes network and queue time and we make no
  production cost or savings claims from it. Jev latency is from its live API.
- Single-model answer latency is not measured (answers are cached); only the live routing decision is.

Reproduce: `jev-router jev-pilot && jev-router jev-pilot-report` (Jev, needs `TYPESAFE_API_KEY`);
`jev-router gliclass-pilot && jev-router gliclass-report` (GLiClass, needs `pip install ".[pilot]"`).

## The full harness (RouterArena, 8,400 queries)

The pilot pool is capped by what is free to score. The interesting question — can Jev beat the
leaderboard frontier — needs a strong, diverse pool, which means paying for the selected model's answer
per query (RouterArena ships cached answers for only three models). That run has not been made; the
harness for it is complete and validated:

- **Scorer parity:** our Arena score reproduces RouterArena's `compute_scores.py` to 4 decimals. The
  all-`gpt-4o-mini` prediction over the full 8,400 scores accuracy **59.2%**, **$0.091/1k**, Arena
  **60.2** (identical under our aggregate and their script).
- **Routers:** always-cheapest, best-fixed, similarity-kNN (Avengers-Pro style), jev-direct,
  jev-hybrid (retrieved dev evidence + per-model capability profiles + calibrated quality vs expected
  cost), a jev-hybrid-nojev ablation, and selective-jev.
- **Estimated cost** of the full run (Jev arms + ablation + dev grid): **$35–70** (Jev routing < $1;
  embeddings local/free; the rest is selected-model answers).

RouterArena leaderboard reference (snapshot `routeworks.github.io/leaderboard`, **2026-09-17**, β=0.10),
for context — these are *other routers*, not Jev:

| Router | Accuracy | Cost/1k | Arena |
|---|---|---|---|
| Paix2 (combined leader) | 79.7 | $0.27 | 77.6 |
| Sqwish (top accuracy) | 79.8 | $0.70 | 76.2 |
| RouteLLM | 47.0 | $0.27 | 48.1 |
| GPT-5 (single model) | 74.0 | $10.02 | 64.3 |

## How it works

Each router chooses one model per query from a frozen pool. We generate only the **selected** model's
answer per query, then score it with RouterArena's own rule-based metrics (MCQ exact-match,
`math_equal`, chess, ROUGE/F1/METEOR, LiveCodeBench execution — no LLM judge). Cost uses RouterArena's
`model_cost.json`.

- **jev-direct / jev pilot** — one Jev Choice over the pool from the query text and capability labels.
- **jev-hybrid** — retrieve similar dev queries, hand Jev compact per-model capability profiles plus
  that evidence, and get a per-model predicted-quality Score in one call; select by **calibrated**
  quality vs **expected** answer cost (output length estimated from dev, never from the unseen answer).
- **jev-hybrid-nojev** — the identical pipeline with Jev replaced by the dev prior, to attribute gains.
- **selective-jev** — the cheap kNN router handles confident cases; escalate to Jev when the margin is
  small.

RouteLLM and RouterDC numbers are taken from the leaderboard rather than re-run.

### Evaluation integrity

RouterArena is evaluation-only. No router component is trained, fit, or tuned on RouterArena data. The
development set (`configs/devset.yaml`) is drawn from **disjoint** public benchmark splits, rendered
with RouterArena's own templates, and every dev prompt is deduped by exact string against the 8,400
test prompts at build time. A test (`tests/test_data_isolation.py`) asserts a query's ground truth
never reaches a router. Prompts, profiles, thresholds, and the pool are frozen before any scored run.

## Reproduce

```sh
git clone https://github.com/RouteWorks/RouterArena && git -C RouterArena checkout cff9659
pip install -e ".[dev,pilot]"
cp .env.example .env                # set TYPESAFE_API_KEY (and CANDIDATE_API_KEY for the full run)
pytest -q                           # verify the scorer reproduces RouterArena's own (offline)

jev-router jev-pilot                 # Jev routing pilot (100 cached queries)
jev-router jev-pilot-report
jev-router gliclass-pilot            # GLiClass comparison pilot
jev-router gliclass-report
```

## Attribution and license

- Code: Apache-2.0 (`LICENSE`).
- RouterArena (Apache-2.0): dataset, cached answers, scorer, `model_cost.json`. Clone it as above.
- Jev / TypeSafe: closed API, https://docs.typesafe.ai/ .
- GLiClass: `knowledgator/gliclass-instruct-large-v1.0` (Apache-2.0), run via the public
  `knowledgator/GLiClass_SandBox` Space. Unaffiliated with TypeSafe.
- Avengers-Pro (arXiv:2508.12631), RouteLLM (Apache-2.0), RouterDC — see the harness for how each is used.
