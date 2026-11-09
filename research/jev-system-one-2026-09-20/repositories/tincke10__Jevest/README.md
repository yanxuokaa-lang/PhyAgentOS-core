# Jevest

Automated PR review pipeline using **Jev** (TypeSafe AI) as a millisecond
decision layer over an LLM reviewer: it decides what to review, how much,
and what to publish.

Full design and scope: [docs/SPEC.md](docs/SPEC.md).

Status: phase 0/1 skeleton — hexagonal domain + decision-port adapters
(`fake`, `recorded`, `typesafe`), config-driven confidence bands.

## Environment
Set these as environment variables (never commit them):
`TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL` (optional), `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.
The live TypeSafe test runs only when `TYPESAFE_API_KEY` is present.

## Phase 0 spike

`pnpm spike` runs the three hunk serializers from `datasets/hunks.jsonl`
through a DecisionPort and reports **H0** (SPEC §4): can Jev flag a code
defect with recall ≥ 0.85 and F1 ≥ 0.75? Below that, the project pivots
before phase 1 starts.

Modes (`--mode`, auto-detected if omitted — `replay` if fixtures exist
under `tests/fixtures/spike/`, else `dry-run`):
- `dry-run` — no API key needed; `FakeDecisionAdapter` with seeded
  pseudo-random answers. Exercises the pipeline; metrics are meaningless.
- `live` — real Jev calls (`TYPESAFE_API_KEY` required).
- `record` — `live`, wrapped to save fixtures for replay.
- `replay` — fixtures only, no network, no key required.

Once `TYPESAFE_API_KEY` is set, record real answers and see H0:
```sh
TYPESAFE_API_KEY=... pnpm spike --mode record
```

Writes `reports/spike-<timestamp>.json` (gitignored) and `.md` (kept).

**H0 failed** (SPEC §4.1, 2026-09-19): Jev can't judge whether a hunk has a
defect. The project pivoted — Jev now only answers surface/recognition
questions, never "does this have a bug?" (SPEC §4.2).

## Phase 0b: surface-profile spike (H0')

`pnpm profile:label` derives AST ground truth (`change_kind`,
`touches_public_api`, `touches_error_handling`, `touches_async`,
`touches_io`) for every hunk via the TypeScript compiler API, writing
`datasets/profile-labels.jsonl`.

`pnpm spike:profile` runs that question set (default serializer
`raw-diff`) and reports **H0'** (SPEC §4.2): choice accuracy ≥ 0.90 on
`change_kind`, F1 ≥ 0.85 on each noul, median confidence ≥ 0.5. Same
`--mode`/`--limit`/`--seed`/`--batch-size` flags as `pnpm spike`; fixtures
under `tests/fixtures/spike-profile/`. **H0' does not block phase 1b** —
if it fails, the hunk-profile stage falls back to path/size metadata.

## Phase 1a: finding-filter spike (H1, blocking)

`pnpm filter` runs the filter question set (`is_real_defect`, `severity`,
`is_style_only`, `actionable`) over a findings dataset and reports **H1**
(SPEC §4.2, the central hypothesis): recall of real findings kept ≥ 0.95
and noise discarded ≥ 0.40. **If H1 fails, Jev does not filter findings.**

```sh
pnpm filter --findings <path> [--batch-size N] [--mode live|record|replay|dry-run]
```

`datasets/findings.jsonl` doesn't exist yet (produced by the reviewer
pipeline); `tests/fixtures/findings-synthetic.jsonl` (14 hand-labeled
records, real and noise, all four severities) stands in for smoke-testing
the filter runner until then. Same four modes as `pnpm spike`; fixtures
under `tests/fixtures/filter/`. The report's `judge` slot is `undefined`
until the LLM-judge baseline (H6) is merged in.

## Running tests
```sh
pnpm install && pnpm test && pnpm typecheck
```
