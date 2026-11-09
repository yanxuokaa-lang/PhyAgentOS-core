# jev-curate

**Corpus curation with [TypeSafe Jev](https://typesafe.ai)** — run pass/fail gates on every training example, keep what passes, drop the rest with an audit trail. Uses the **live Jev API** by default (`typesafe-sdk` → `jev-latest`).

Sibling to [jev-triage](https://github.com/ThyFriendlyFox/jev-triage) (pattern #3: active learning). This repo is **pattern #1: data curation** — filter the whole corpus, not a sample.

> Filter with Jev. Train on real outcome labels. Do not treat Jev as your teacher of record.

## Quick start

```bash
pip install -e ".[dev]"
export TYPESAFE_API_KEY="sk-..."   # required unless --mock (tests only)

jev-curate check-jev   # optional smoke test

jev-curate run \
  --rubric examples/rubric.yaml \
  --input examples/corpus.jsonl \
  --output .output/run1
```

### With a Vercel AI Gateway key

Jev is also served by [Vercel AI Gateway](https://vercel.com/ai-gateway/models/jev) as `typesafe-ai/jev`. With a gateway key and no TypeSafe key, add `--gateway`:

```bash
export AI_GATEWAY_API_KEY="vck_..."
jev-curate check-jev --gateway
jev-curate run --gateway --rubric examples/rubric.yaml --input examples/corpus.jsonl --output .output/run1
```

It is the same live Jev, with the same gates and thresholds. The gateway's free tier rate-limits: rows that get HTTP 429 land in `errors.jsonl`, and a later run with `--retry-errors` picks them up.

### Outputs

| File | Contents |
|------|----------|
| `curated.jsonl` | Rows that passed **all** required gates — use for training |
| `rejected.jsonl` | Failed rows + `_curation` audit (which gate, Jev probabilities) |
| `audit.jsonl` | Per-example gate results (kept or not) |
| `errors.jsonl` | API / parse failures. A re-run skips these ids too, unless you pass `--retry-errors` |

## Rubric: gates + pass rules

Each gate is one Jev question (`noul`, `choice`, or `score`) plus a **pass** block:

```yaml
gates:
  - name: transcript_valid
    type: noul
    instructions: Coherent text, not garbled ASR?
    pass:
      min_yes: 0.75

  - name: is_ambiguous
    type: noul
    instructions: Could this belong to more than one category?
    pass:
      max_yes: 0.40   # must be "no" (low yes probability)

  - name: bucket_matches_content
    type: choice
    instructions: Best category for this message (ignore label field)
    criteria:
      billing: ...
      technical: ...
    pass:
      match_field: label      # Jev choice must match row["label"]
      min_confidence: 0.55
```

- `pass_mode: all` (default) — every **required** gate must pass.
- Set `required: false` on a gate to log it in audit without rejecting.

## Why live Jev

Curation runs at scale (~$21 per million 500-token examples at $0.042/MTok). Mock mode (`--mock`) exists **only for pytest**; production runs should call the real API so probabilities and thresholds mean something.

### Flags

| Flag | Default | Effect |
|------|---------|--------|
| `--limit N` | none | Evaluate at most N rows this run (skipped rows do not count) |
| `--concurrency N` | 1 | N parallel Jev calls; one thread writes the files |
| `--batch-size N` | 1 | N rows per Jev call; every gate is asked once per row in one request |
| `--timeout S` | 10 | Seconds to wait for one Jev call |
| `--retry-errors` | off | Re-evaluate ids that appear only in `errors.jsonl` |
| `--gateway` | off | Call live Jev through Vercel AI Gateway with `AI_GATEWAY_API_KEY` |
| `--mock` | off | Mock client, tests only |

A bad API key stops the run with one line instead of filling `errors.jsonl`.

## Batch rows in one request

`--batch-size N` sends N rows as one state and asks every gate once for each row. Jev counts the shared state once, so a batch costs fewer tokens and far fewer requests than N calls. Live, 75 rows and 150 questions took 1 request and 0.9 seconds.

[`examples/trec/`](examples/trec/README.md) filters 1,000 Hugging Face rows this way. 19 requests carried the 1,000 rows. Jev rejected 99 of 100 rows with a flipped label and 50 of 50 rows with scrambled text. It also rejected 8 source rows that were already broken, 5 of them with part-of-speech tag debris.

## Resume / scale

The pipeline skips any `id` already written to `curated.jsonl`, `rejected.jsonl`, or `errors.jsonl` (pass `--retry-errors` to re-evaluate the errored ones). Shard input JSONL by slice, run workers with distinct output dirs, merge `curated.jsonl` files downstream.

For high throughput, pass `--concurrency N`. Calls run in N threads; the output files are still written by one thread, in completion order. Respect your TypeSafe rate limit: the SDK retries 429s with backoff, but sustained 429s land in `errors.jsonl`.

## Relation to jev-triage

| Tool | Job |
|------|-----|
| **jev-curate** | Binary keep/drop + audit |
| **jev-triage** | keep / teacher queue / human queue by confidence |

Typical stack: **curate** first (cheap gates) → **triage** on what passes (expensive labeling budget).

## Development

```bash
pip install -e ".[dev]"
./verify/verify.sh        # lint, build, tests, and the repo gates — CI runs this same script
```

`agent-kit/` is the operating manual for anyone (human or agent) working on this repo; start at `agent-kit/ROUTING.md`. `ralph/` holds a Ralph loop whose goal is this README: `ralph/GOAL.md` lists each claim above with the gate that proves it, and `ralph/loop.sh` runs an agent until `./verify/verify.sh` is green.

## License

MIT
