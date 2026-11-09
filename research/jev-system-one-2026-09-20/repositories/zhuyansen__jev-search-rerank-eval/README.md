# jev-search-rerank-eval

**Does a TypeSafe Jev rerank beat embedding search? Measured, with the judge-bias removed.**

A graded relevance evaluation over the [Agent Skills Hub](https://agentskillshub.top) catalog
(33,047 skills, MCP servers and coding-agent tools; snapshot 2026-09-18) with 164 real
Chinese / English / mixed queries, 9,831 labelled (query, skill) pairs, and a bake-off of:

- **`ash-0.4.0`** — the keyword ranker that ships in the [`ash` CLI](https://www.npmjs.com/package/@agentskillshub/cli), run byte-for-byte via [`ash_ranker.mjs`](src/jse/rankers/ash_ranker.mjs)
- **`bm25`** — BM25 over the same metadata (latin words + CJK bigrams)
- **`bge-m3`** — dense retrieval with BAAI/bge-m3 (local) · **`text-embedding-3-small`** — dense retrieval via OpenRouter
- **`jev-score(X@30)`** — a [TypeSafe Jev](https://typesafe.ai) `score` rerank of system X's top 30, one API call per query
- **`rrf(…)`** — reciprocal-rank-fusion hybrids

Metric: **NDCG@10** on graded labels (0–3), plus MRR and P@3 (relevant = label ≥ 2), with
paired bootstrap 95 % confidence intervals over queries.

## TL;DR

| claim | evidence |
|---|---|
| **Jev as a standalone reranker does not beat a good embedding ranker.** | `jev-score(bge-m3@30)` − `bge-m3` = +0.012 NDCG@10, CI [−0.013, +0.037]. Judged by an unrelated model only, it is **−0.028** [−0.052, −0.004]. |
| **Jev fused with the embedding ranking is the best system, and that survives removing Jev from the judging.** | `rrf(bge-m3, jev@30)` − `bge-m3` = **+0.090** [+0.077, +0.104]; under LLM-only labels **+0.064** [+0.052, +0.077]. |
| **The apparent Jev advantage under Jev's own labels is judge circularity, and it is measurable.** | The same comparison reads +0.053 under Jev-only labels, +0.012 under merged labels, −0.028 under LLM-only labels. |
| **The shipped keyword ranker's problem is recall, not ordering.** | Reranking `ash`'s top-30 with bge-m3 makes it *worse* (−0.026). recall@10 of relevant items: ash 0.497, bge-m3 0.708. |
| **On a weak lexical candidate list, Jev is the better reranker.** | `jev-score(ash@30)` − `bge-m3(ash@30)` = +0.060 [+0.043, +0.078]; +0.037 under LLM-only labels. |

Jev's value here is as a **second signal**, not as the ranker — the same shape as using a
zero-shot model's probability as one feature next to a trained model.

## Results

Jev model: `typesafe/jev-1.13-20260917` (the only id seen across labelling and evaluation).

### Overall (164 queries, frozen final labels)

| system                 | ndcg@10 | mrr   | p@3   | Δ NDCG@10 vs ash (95 % CI) |
|:-----------------------|--------:|------:|------:|:---|
| **rrf(bge-m3,jev@30)** | **0.864** | 0.980 | 0.951 | +0.255 [+0.221, +0.290] |
| jev-score(bge-m3@30)   | 0.785 | 0.953 | 0.862 | +0.176 [+0.138, +0.213] |
| bge-m3                 | 0.774 | 0.872 | 0.768 | +0.165 [+0.133, +0.199] |
| text-embedding-3-small | 0.759 | 0.839 | 0.734 | +0.151 [+0.117, +0.186] |
| rrf(ash,bge-m3)        | 0.729 | 0.820 | 0.685 | +0.120 [+0.100, +0.141] |
| jev-score(ash@30)      | 0.642 | 0.843 | 0.711 | +0.034 [+0.008, +0.059] |
| bm25                   | 0.633 | 0.687 | 0.575 | +0.024 [−0.013, +0.060] |
| ash-0.4.0 (shipped)    | 0.609 | 0.684 | 0.520 | — |
| bge-m3(ash@30)         | 0.583 | 0.753 | 0.616 | −0.026 [−0.049, −0.002] |

Jev reranking moves the *top* of the list a lot (MRR 0.872 → 0.953, P@3 0.768 → 0.862 on the
merged labels) while NDCG@10 barely moves — it promotes one strong hit and reshuffles the rest.
Under LLM-only labels even the P@3 gain disappears (−0.043), which is why the fusion, not the
rerank, is the result to trust.

### Robustness to the choice of judge

Jev is both a labeller and a system under test, so every system is re-scored under three label
sets. A claim about Jev only counts if it survives `llm_only`, the set Jev had no part in.
(`python -m jse robustness`, no API calls — full tables in [`results/robustness.md`](results/robustness.md).)

| system                 | final | llm_only | jev_only |
|:-----------------------|------:|---------:|---------:|
| rrf(bge-m3,jev@30)     | 0.864 | 0.871 | 0.845 |
| jev-score(bge-m3@30)   | 0.785 | 0.779 | 0.781 |
| bge-m3                 | 0.774 | 0.807 | 0.729 |
| text-embedding-3-small | 0.759 | 0.806 | 0.700 |
| rrf(ash,bge-m3)        | 0.729 | 0.767 | 0.677 |
| jev-score(ash@30)      | 0.642 | 0.648 | 0.627 |
| bm25                   | 0.633 | 0.686 | 0.568 |
| ash-0.4.0              | 0.609 | 0.657 | 0.549 |
| bge-m3(ash@30)         | 0.583 | 0.612 | 0.543 |

| a − b (Δ NDCG@10) | final | llm_only | jev_only |
|:---|:---|:---|:---|
| jev-score(bge-m3@30) − bge-m3 | +0.012 [−0.013, +0.037] | **−0.028** [−0.052, −0.004] | +0.053 [+0.026, +0.081] |
| rrf(bge-m3,jev@30) − bge-m3 | **+0.090** [+0.077, +0.104] | **+0.064** [+0.052, +0.077] | +0.116 [+0.101, +0.132] |
| rrf(bge-m3,jev@30) − jev-score(bge-m3@30) | +0.079 [+0.062, +0.096] | +0.092 [+0.075, +0.109] | +0.063 [+0.046, +0.081] |
| jev-score(ash@30) − bge-m3(ash@30) | +0.060 [+0.043, +0.078] | +0.037 [+0.019, +0.055] | +0.083 [+0.066, +0.103] |
| bge-m3 − text-embedding-3-small | +0.014 [−0.007, +0.036] | +0.000 [−0.018, +0.019] | +0.028 [+0.002, +0.056] |

The 30-query hand-adjudicated core subset agrees with the full set within ±0.02 NDCG@10 for
every system (e.g. rrf(bge-m3,jev@30) 0.863 vs 0.864; ash 0.609 vs 0.609).

### NDCG@10 by query form

`syn` = Chinese synonym of a scenario title (80 queries) · `en` = English (45) · `mix` = mixed script (38)

| system                 |    en |   mix |   syn |
|:-----------------------|------:|------:|------:|
| ash-0.4.0              | 0.697 | 0.649 | 0.539 |
| bm25                   | 0.714 | 0.614 | 0.595 |
| text-embedding-3-small | 0.837 | 0.695 | 0.744 |
| bge-m3                 | 0.814 | 0.758 | 0.756 |
| jev-score(bge-m3@30)   | 0.830 | 0.790 | 0.755 |
| rrf(bge-m3,jev@30)     | 0.892 | 0.849 | 0.853 |

The shipped ranker's gap is concentrated in Chinese synonym queries (0.539 vs 0.756), the defect
class its own maintainers' sweep had already named; English is much closer. bge-m3 beats
text-embedding-3-small on mixed-script queries (0.758 vs 0.695) and ties elsewhere. Train (87)
and heldout (77) splits score within 0.05 of each other for every system.

## What this means for `ash`

1. **Fix recall first.** No reranker — Jev or embedding — can help a candidate list that misses
   half the relevant items, and `ash` returns nothing for 3 of 164 queries. The cheapest lever
   stays the one the CLI already uses (curated Chinese synonyms), because the CLI is a
   zero-dependency tool that cannot ship a 1024-dim × 33K index (≈135 MB).
2. **A hybrid is the realistic server-side upgrade**: `rrf(ash, bge-m3)` recovers +0.120 without
   touching the keyword ranker, and would fit the existing Pro-tier RPC path.
3. **Jev is worth adding only on top of semantic candidates, and only fused**: +0.06 to +0.09
   NDCG@10 for one ~$0.0002 call per query (328 rerank calls cost $0.066 here). As a standalone
   reranker it is not better than bge-m3 and should not be sold as such.

## How the labels were made

1. **Queries** — the 164-case golden set the `ash` CLI is tuned against
   (`data/queries.json`: `{sc, form, q, split}`; `sc` is an expected *scenario slug* used only
   for stratified reporting, never as relevance ground truth).
2. **Pooling** — union of each retriever's top-30 (ash, BM25, bge-m3, text-embedding-3-small),
   capped at 60 per query, ordered so items proposed by more retrievers survive the cap:
   **9,831 (query, skill) pairs**, 51–60 per query. 6,718 pairs were proposed by a single
   retriever; 171 by all four.
3. **Judge 1 — Jev** (`typesafe/jev-1.13-20260917`, OpenRouter `/alpha/decisions`): one `score`
   question per candidate, 25 candidates per call, legend *Irrelevant / Marginally related /
   Relevant / Exactly what was asked for*. $0.069.
4. **Judge 2 — `anthropic/claude-haiku-4.5`**, temperature 0, one pair per call, same 0–3 scale,
   a different model family so the two judgements are independent. $2.37.
5. **Agreement**: exact 53.1 %, within one level 98.0 %, quadratic-weighted κ **0.71**. The
   disagreement is systematic: Haiku sits one level above Jev on the 1↔2 boundary (1,768 pairs
   Jev = 1 / Haiku = 2). Only 201 pairs (2 %) differ by two or more levels.
6. **Adjudication** — a 30-query core subset, stratified by form × split (seed 7), where every
   ≥ 2-level disagreement was read and graded by hand (by Claude, in one sitting, from the same
   metadata the systems see): 30 pairs. The hand grade sided with Jev 18 times, with Haiku twice,
   and fell between them 10 times. Most Haiku over-grades were tag/keyword overlap without
   intent match (instructional design ≠ UI design, a QA test manager ≠ 知识库问答, Telegram ≠
   Discord); Jev's misses were genuine matches it under-rated (a "write like a human" tool, a
   self-hosted mem0 server).
7. **Final label** = hand adjudication if present; else the shared label when the judges agree
   (5,224 pairs); else the **un-rounded mean**, e.g. 1.5 (4,577 pairs). It is deliberately not
   rounded: rounding half up would adopt the more generous judge on every 1/2 split. NDCG takes
   fractional gains; the binary cut for MRR/P@3 stays at ≥ 2.
8. `data/labels_final.jsonl` was frozen before any system was scored and is never edited.

## Caveats

- **Judge circularity** is handled by the robustness table above, not assumed away. Read the
  `llm_only` column as the conservative estimate for anything involving Jev.
- **Both judges are language models.** There is no human-labelled subset beyond the 30
  adjudicated pairs; a human study would be the natural next step.
- **Pooling bias**: all four retrievers contributed top-30 lists, so none is disadvantaged
  relative to the others, but a system retrieving outside the pool would be under-scored
  (unlabelled = 0, the standard assumption). The Jev rerankers only reorder pooled lists.
- **Metadata-level relevance only**: name, author, truncated description, tags and curated
  Chinese scenario keywords — exactly what `ash` searches. README text is not in the index.
- **Query mix** skews to Chinese scenario synonyms (80/164) because the set came from the CLI's
  own sweep; per-form results are reported for that reason.
- Two catalog rows had lone UTF-16 surrogates (the index truncates descriptions by JS string
  length and can split an emoji); they are sanitised at load.

## Reproduce

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q                                  # 28 tests
.venv/bin/python -m jse robustness                   # re-scores cached runs, no API key needed

export OPENROUTER_API_KEY=...                        # env only; never written to disk
.venv/bin/python -m jse pool                         # ~30 min first time (bge-m3 over 33K docs), ~$0.03
.venv/bin/python -m jse label                        # Jev judge, ~$0.07
.venv/bin/python -m jse label --judge2               # Haiku judge, ~$2.4, ~35 min
.venv/bin/python -m jse adjudicate-export            # writes data/adjudicate_todo.jsonl for hand grading
.venv/bin/python -m jse freeze                       # -> data/labels_final.jsonl (+ agreement stats)
.venv/bin/python -m jse eval --out results           # all systems (~$0.07); --local-only needs no API
```

Total API spend for everything in this repo: **≈ $2.6**. Frozen artifacts (`data/*.jsonl`,
`data/search-index.json.gz`, `results/runs.json`) are committed, so scoring and the robustness
analysis reproduce without any API access. Every response's `model` field is recorded.

## License and attribution

MIT. The scoring functions in `src/jse/rankers/ash_ranker.mjs` are copied verbatim from
[`@agentskillshub/cli`](https://github.com/zhuyansen/agentskillshub-cli) v0.4.0 (MIT) so the
evaluation measures the ranker that actually ships. Catalog data © the respective repository
authors, via the public search index. Not affiliated with TypeSafe.
