# jev-cold-start-prior

**Can a TypeSafe Jev prior, read from a README on day one, tell which new agent-skill repos
will gain stars — and how many labels does a trained model need to catch up?**

Two parts:

| part | status | what it answers |
|---|---|---|
| **Retrospective proxy** (this repo, results below) | done, n = 1,132 | Directional: does the day-one prior rank repos by later popularity, vs day-one metadata and vs a model *trained* on the same README text? |
| **Prospective test** (running in [Agent Skills Hub](https://agentskillshub.top)'s sync) | first outcomes 2026-10-02 | The clean version: prior vs **star count at entry**, 14-day outcome, no look-ahead |

## Why a proxy

The obvious experiment — rebuild each repo's star count on the day we first saw it and 14 days
later — can no longer be done after the fact:

- GitHub's `GET /repos/{owner}/{repo}/stargazers` now returns **404** for every repo, including
  `octocat/Hello-World` (authenticated, 2026-09-18). GraphQL returns `stargazerCount` but an empty
  `stargazers` list. [`src/jcp/stars.py`](src/jcp/stars.py) is the route we built for it.
- Star-history services rebuild from GitHub's public event firehose; OSSInsight marks its own data
  *severely degraded since 2026-05-01* (a repo with 157 stars shows 1).

So the retrospective target is **stars today, adjusted for how long each repo has existed**, and
the strongest real baseline — the star count at entry — is missing. That baseline is exactly what
the prospective part records.

## Results (retrospective proxy)

**Sample**: every repo the Agent Skills Hub catalog first saw 16–75 days before 2026-09-18 that was
created at most 14 days before being seen (genuinely new, not a backfill), has a README over 300
characters and fewer than 3,000 stars — **1,132 repos**, median 17.5 stars.

**Target**: `log1p(stars today)` residualised on `log(days since creation)`.

**Jev prior**: one `/alpha/decisions` call per repo (`typesafe/jev-1.13-20260917`, $0.085 total),
eight typed questions over name, description, category, age and a 3,000-character README excerpt.
Star counts and README star badges are **excluded** from the state.

### Ranking quality (Spearman ρ with the target, bootstrap 95 % CI)

| predictor | needs labels? | ρ | 95 % CI | AUC (top 25 %) | top-10 % precision |
|:--|:--|--:|:--|--:|--:|
| TF-IDF ridge **+ Jev answers** | 900 | **0.559** | [0.52, 0.60] | 0.762 | 0.372 |
| TF-IDF ridge on README | 900 | 0.524 | [0.48, 0.57] | 0.752 | 0.354 |
| metadata ridge + Jev answers | 900 | 0.482 | [0.43, 0.52] | 0.727 | 0.319 |
| Jev: all answers (ridge) | 900 | 0.467 | [0.42, 0.51] | 0.714 | 0.301 |
| **Jev: `will_gain` alone (zero-shot)** | **0** | **0.435** | [0.38, 0.48] | 0.695 | 0.265 |
| Jev: `showcase` (has demo/screenshots) | 0 | 0.324 | [0.27, 0.37] | 0.666 | 0.239 |
| metadata ridge (README/description length, category, age) | 900 | 0.240 | [0.19, 0.29] | 0.612 | 0.159 |
| README length | 0 | 0.126 | [0.07, 0.19] | 0.530 | 0.133 |
| Jev: `rides_trend` (built for Claude Code/MCP/…) | 0 | **−0.077** | [−0.13, −0.02] | 0.460 | 0.027 |

Trained models use 5-fold out-of-fold predictions (≈900 training labels per fold).

| paired Δρ | Δ | 95 % CI |
|:--|--:|:--|
| (TF-IDF + Jev) − TF-IDF | **+0.035** | [+0.005, +0.067] |
| (metadata + Jev) − metadata | +0.242 | [+0.197, +0.298] |
| Jev answers (ridge) − TF-IDF | −0.057 | [−0.102, −0.009] |

### How many labels until a trained model matches Jev's zero-shot prior?

Held-out 300 repos, 20 random splits, Spearman ρ:

| labelled repos | TF-IDF (trained) | TF-IDF + Jev (trained) | Jev `will_gain`, zero-shot |
|--:|--:|--:|--:|
| 0 | — | — | **0.435** |
| 25 | 0.307 | 0.297 | |
| 50 | 0.378 | 0.387 | |
| 100 | 0.421 | 0.465 | |
| 200 | 0.461 | 0.500 | |
| 400 | 0.499 | 0.531 | |
| 800 | 0.520 | 0.557 | |

**A trained text model needs roughly 100–200 labelled repos to match one zero-shot Jev
question**, and once it has them, adding the Jev answers as features still helps at every size.

### Reading it

1. **Zero-shot, Jev is the best thing available** — ρ 0.435 with no labels, vs 0.24 for a model
   trained on day-one metadata. For a brand-new catalog or category with no history, that is the
   whole point of a prior.
2. **With enough labels, a trained model wins, and Jev is best used as a feature** — the same
   shape as the [Titanic test](#related) (Jev 0.830 vs LR 0.843, combined 0.854) and the
   [search rerank eval](https://github.com/zhuyansen/jev-search-rerank-eval) (Jev alone ≈ bge-m3,
   fused +0.09 NDCG@10).
3. **Most of the signal is in one direct question** (`will_gain`, 0.435) and in whether the README
   **shows** the thing working (`showcase`, 0.324). Jev's judgements of maturity, clarity, ease of
   install and novelty are near zero.
4. **"Built for the current wave" predicts *fewer* stars** (ρ −0.077): Jev says 95 % of these repos
   ride a current wave (Claude Code / MCP / OpenClaw add-ons), so it is the *common* case, not the
   distinguishing one — and the ones that don't are rarer and do better.

## Caveats — why this is directional, not a verdict

- **No star count at entry.** The strongest real-world baseline is missing; the prospective part
  exists to supply it. Until then, do not read these numbers as "Jev beats star count".
- **Today's README, not day one's.** Authors of repos that take off tend to improve their README,
  so part of what every README-based predictor sees is a *consequence* of popularity. This inflates
  Jev and TF-IDF alike; it does not favour one of them.
- **Exposure adjustment is linear in log-age.** Repos first seen 16 vs 75 days ago had very
  different time to accumulate stars; residualising removes the first-order effect only.
- **Possible model knowledge.** `jev-1.13-20260917` was released after some of these repos
  existed; we cannot rule out that it has seen some of them.
- **README text is not redistributed.** `data/sample_meta.jsonl` has names, dates, stars,
  README length and SHA-1; the excerpts stay local because third-party READMEs carry mixed
  licenses. The Jev and metadata results reproduce from what is committed; TF-IDF needs the text.

## Prospective part (running)

A post-sync step in Agent Skills Hub
([`backend/cold_start_priors.py`](https://github.com/zhuyansen/agent-skills-hub/blob/main/backend/cold_start_priors.py),
table from migration `023_cold_start_priors.sql`) scores every genuinely new repo within 3 days of
first sight with **the same eight questions**, stores the star count at that moment, and reads
`stars_at_14d` two weeks later. The first cohort (150 repos) was scored on 2026-09-18; first
outcomes land 2026-10-02. That comparison — prior vs star count at entry — will be added here.

## Reproduce

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/python -m jcp.analyze        # needs data/sample.jsonl (README text) for the TF-IDF rows
# to rebuild the sample and priors (needs catalog DB access and an OpenRouter key in the env):
.venv/bin/python -m jcp.sample
OPENROUTER_API_KEY=... .venv/bin/python -m jcp.prior   # ~$0.085 for 1,132 repos
```

## Related

- [jev-search-rerank-eval](https://github.com/zhuyansen/jev-search-rerank-eval) — Jev as a search
  reranker, with judge-circularity controls.
- Titanic sanity check (not a repo): Jev zero-shot AUC 0.830 vs logistic regression 0.843; LR with
  Jev's probability as a feature 0.854. Same pattern as here.

MIT. Not affiliated with TypeSafe.
