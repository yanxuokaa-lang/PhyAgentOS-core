# explore-typesafe-ai

Evaluating [TypeSafe](https://docs.typesafe.ai)'s System One model **Jev** on five hospital tasks over 1,000 synthetic FHIR patients. Claude models write the pipeline, author the scenarios, review escalations as System Two and answer the same questions as an LLM baseline.

**Report:** https://si618.github.io/explore-typesafe-ai

| Scenario | Primitives | Cases |
| --- | --- | --- |
| 1. Ward deterioration huddle: NEWS2 in code, plus Jev reading the nursing note | Noul, Score, Choice | 20 hand + 80 generated |
| 2. Discharge medication reconciliation: per-medication extraction plus regimen verification (v1, and decomposed v2/v2.1) | Choice (fan-out), Noul, Score | 20 hand + 80 generated |
| 3. Post-discharge patient inbox: routing with a confidence gate | Choice, Score, Noul | 20 hand + 80 generated |
| 4. Note search: lay questions over a patient's 10 most recent notes, labelled by regex | Noul, Choice | 300 queries (and 2,922 single-note requests) |
| 5. ML features: Jev judgments on one note as features for predicting acute care | Score, Noul, Choice | 1,000 patients |

Hand-written cases have labels written by Claude Opus 5. Generated cases have labels known by construction and are split into `dev` (threshold tuning) and `test` (reporting). Every label set was committed before its first model run. Also included: a blinded Claude Sonnet 5 System Two review, a Claude Haiku 4.5 baseline, and an independent label sample from a different model family (`data/independent_labels/`).

## Layout

```
data/synthea-r4/          raw Synthea bundles for the original 100 patients (FHIR R4, gzipped)
data/synthea-r4-extra/    raw bundles for the other 900 (not committed; from release cohort-1000)
data/fhir-r5/             per-patient clinical snapshots with recent notes, FHIR R5 (validated)
data/cohort.json          cohort summary used to assign patients to scenarios
data/fhir-r5-scenarios/   hand-case inputs as FHIR R5 Observation / DocumentReference / Communication
data/scenarios/           case definitions + reference labels (hand, generated, s4, s5)
data/independent_labels/  blinded label packet, independent labels, provenance and agreement
results/                  raw Jev and Haiku answers, timing, usage; System Two packet and review; evaluations
src/explore_typesafe/     pipeline
report/                   static narrative pages copied into the site
docs/                     generated Zensical site source (do not edit by hand)
```

## Reproduce

```bash
uv sync

# Cohort: the original 100 are committed; fetch the other 900 to rebuild snapshots
gh release download cohort-1000 -p 'synthea-r4-extra-seed619.tar' -O - | tar -x -C data
uv run python -m explore_typesafe.fhir            # R4 -> R5 snapshots + cohort.json
uv run python -m explore_typesafe.scenario_fhir   # hand-case inputs as R5 bundles

# Cases and labels (committed before any model run)
uv run python -m explore_typesafe.generate        # 80 generated cases per scenario 1-3
uv run python -m explore_typesafe.s4_search       # note-search queries
uv run python -c 'from explore_typesafe.s4_search import write_note_cases; write_note_cases()'
uv run python -m explore_typesafe.s5_features     # feature-scenario notes and outcomes

# Model runs
export TYPESAFE_API_KEY=...
uv run python -m explore_typesafe.run             # every run in run.RUNS on jev-1.13.0 (4,722 requests)
uv run python -m explore_typesafe.haiku           # Claude Haiku 4.5 baseline via `claude -p`
uv run python -m explore_typesafe.escalate        # System Two review packet
# review packet -> results/system_two_review.json (done by a blinded Claude agent)

# Evaluation and report
uv run python -m explore_typesafe.evaluate        # hand cases -> results/evaluation.json
uv run python -m explore_typesafe.evaluate2       # generated, s4, s5, Haiku -> results/evaluation2.json
uv run python -m explore_typesafe.independent_labels   # packet and agreement (see data/independent_labels/README.md)
uv run python -m explore_typesafe.report          # renders docs/
uv run zensical serve
```

`run.py` and `haiku.py` accept run names to rerun a subset, for example `uv run python -m explore_typesafe.run s4_search`.

Synthetic data only. This is not clinically validated.

## Licence

[MIT](LICENSE), Copyright (c) 2026 Simon McKenna.

The cohort under `data/` is [Synthea](https://github.com/synthetichealth/synthea) output.
Synthea itself is Apache-2.0 and its generated data carries no use restrictions; the
files here are output, not Synthea source.
