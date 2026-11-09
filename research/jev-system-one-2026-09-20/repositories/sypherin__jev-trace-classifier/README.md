# jev-trace-classifier

An application of **[TypeSafe Jev](https://typesafe.ai)** (a "System-One"
judgment primitive) on the public **collusion.wiki** corpus: can a small
probabilistic judgment primitive tell whether a wiki page was authored by an
**autonomous AI agent** or by a human — and how does it stack up against a
local LLM on the same task?

## The task

The [collusion.wiki](https://collusion.wiki) corpus documents a July 2026
episode in which autonomous AI agents edited a wiki. The dataset ships per-page
author labels, giving a clean binary target:

| class | meaning | pages |
|-------|---------|------|
| **agent** | author label is a non-bracketed `A…` pseudonym (an autonomous agent) | 1,026 |
| **human** | author label is a bracketed human (`[Admin2]`, `[Person22]`, …) | 3,553 |

Majority baseline (always "human"): **77.6% accuracy**. Any real classifier has
to beat that.

## The finding that frames the repo

Raw page **text carries almost no signal**. A regex hunting for "I am an AI",
"language model", "as an AI assistant", "GPT", "Claude" … scores:

```
regex baseline  n=4579  P=0.000 R=0.000 Acc=0.776 F1=0.000
```

…i.e. it finds *zero* agent tells in the prose. The agent-written pages read
like ordinary wiki prose; the agent/human split is defined by **provenance**,
not writing style. This is exactly the setting a calibrated judgment primitive
is meant for — and the benchmark shows how hard it is even then.

## Benchmark (Jev vs local LLM)

Both models answer the same question per page: *"was this written by an
autonomous AI agent?"* Scored against the per-page ground truth.

Full run: all **4,579** pages, 0 Jev errors (2 Qwen timeouts excluded).

| model | type | n | avg ms | Precision | Recall | Accuracy | F1 |
|-------|------|---|--------|-----------|--------|----------|----|
| **Jev** (`noul`) | TypeSafe System-One | 4579 | 830 | 0.257 | 0.082 | **0.741** | 0.124 |
| **Qwen3.8-Flash-Next** | local LLM (`:8001`) | 4577 | 3620 | 0.227 | 0.974 | 0.252 | 0.369 |
| regex tells | content baseline | 4579 | <1 | 0.000 | 0.000 | 0.776 | 0.000 |
| majority | always human | 4579 | 0 | 0.000 | 0.000 | 0.776 | 0.000 |

*Reading the table.* Neither model beats the 77.6% majority baseline, and they
fail in opposite directions. Qwen calls 4,394 of 4,579 pages "agent", so recall
0.974 is degenerate, not skill: its precision (0.227) sits *below* the 22.4%
agent base rate and its accuracy (0.252) is the worst in the table. Jev is the
opposite extreme — it fires on only 327 pages, catching 84 of 1,026 agents
(recall 0.082) while staying close to always-human (accuracy 0.741). The regex
and majority rows share accuracy 0.776 because the regex found *zero* agent
tells, so it predicts "human" for every page — which is exactly the always-human
majority classifier. Filled from `compare.py` output (`jev_vs_qwen_summary.json`).

## The threshold is not the story

A classifier's operating point can be tuned after the fact, so we swept Jev's
decision threshold over the collected `noul` scores (`threshold_probe.py`):

```
agent scores:  min=0.27  p10=0.38  p50=0.44  p90=0.49  max=0.62
human scores:  min=0.16  p10=0.34  p50=0.42  p90=0.48  max=0.68

 thr   Prec  Recall     F1      TP     FP   FN
 0.39  0.269  0.889  0.413    912   2474  114     <- best F1
 0.45  0.328  0.462  0.384    474    969  552
 0.50  0.257  0.082  0.124     84    243  942      <- the naive default
```

At the naive 0.5 cutoff Jev looks near-sighted (recall 0.07). Retuning rescues
recall — but only by sliding into "call everything an agent", and **precision
stays pinned at the 0.22 base rate at every threshold**. The agent and human
score distributions sit almost exactly on top of each other (both median 0.43).

That is the real finding: there is no decision threshold that separates the two
classes, because the page text simply does not carry the signal. The
agent/human split is provenance, and prose-only judges — regex, a calibrated
judgment primitive, or a local LLM — cannot recover it.

## Layout

```
ground_truth.py    # the per-page agent/human label join (the only "ground truth" logic)
baseline_regex.py  # content-only floor: regex tells -> shows text alone is blind
jev_client.py      # minimal TypeSafe Jev client (noul primitive, plain HTTP)
qwen_client.py     # local Qwen3.8-Flash-Next client (OpenAI-compatible)
compare.py         # the head-to-head harness + metrics table + JSONL dump
threshold_probe.py # sweeps the Jev decision threshold -> shows no separating cutoff
fetch_data.sh      # how to pull the collusion.wiki dumps locally
data/              # place the .jsonl.gz dumps here (not committed — see LICENSE)
```

## Usage

```bash
# 1. fetch the corpus (see fetch_data.sh; ~10 MB gz)
./fetch_data.sh

# 2. point the code at the dumps (defaults to /tmp/traces, override via env)
export COLLUSION_LABELS=data/labels.jsonl.gz
export COLLUSION_REVISIONS=/path/to/revisions.jsonl.gz

# 3. sanity-check the join
python3 ground_truth.py

# 4. the floor: prove prose alone is blind
python3 baseline_regex.py

# 5. the benchmark (needs a TypeSafe key + a local Qwen on :8001)
export TYPESAFE_API_KEY=...          # or ~/.config/typesafe/env
python3 compare.py --limit 200      # smoke first
python3 compare.py                  # full run
```

## Notes

- The corpus has **no stated license** on its page text, so raw dumps are not
  committed here. `fetch_data.sh` fetches them at runtime; only the join + code
  are open.
- Jev latency here is network-bound (~700 ms/call). Local Qwen latency depends
  on the host serving it.
- `records.jsonl.gz` is agent-only (no humans), so it cannot measure false
  positives; the eval uses `revisions.jsonl.gz` collapsed to unique pages.
