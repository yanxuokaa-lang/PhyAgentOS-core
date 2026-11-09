# Jev Plan Validator

Validate free-text (`.md`) or structured (`.json`) execution plans with [TypeSafe Jev](https://docs.typesafe.ai) (`POST /v1/systemone`) using raw `curl` + `jq` (`validate.sh`) or stdlib-only Python (`validate.py`). No SDK.

Jev judges, bash decides. One API call asks 7–9 parallel questions, then confidence-gated routing in code emits `READY` / `NEEDS_REVISION` / `BLOCKED` / `REVIEW`.

## Questions

| # | Name | Type | Meaning |
|---|------|------|---------|
| 1 | `is_executable` | noul | Concrete ordered steps, no missing deps or imaginary tools |
| 2 | `is_complete` | noul | Covers goal, testable, no major gaps |
| 3 | `is_safe` | noul | No destructive / irreversible / policy-violating actions without safeguards |
| 4 | `completeness` | score 0–4 | Vague → complete + rollback + verification |
| 5 | `risk` | score 0–4 | Safe → critical |
| 6 | `clarity` | score 0–4 | Incoherent → exact commands + expected outputs |
| 7 | `readiness` | choice | `ready` / `needs_revision` / `blocked` + confidence |
| 8 | `tools_grounded` | noul | JSON-only: every step uses allowed tools / real paths |
| 9 | `deps_sound` | noul | JSON-only: deps exist, ordered, no cycles |

`.md` plans send `state` as string (7 Qs). `.json` plans send `state` as object (9 Qs).

## Usage

```bash
export TYPESAFE_API_KEY=...
./validate.sh plans/valid.md
./validate.sh --strict plans/valid.json
./validate.sh --lenient plans/invalid.md

# tuning (env overrides beat presets)
SAFE_MIN=0.95 ./validate.sh plans/invalid.md
JEV_MODEL=jev-latest ./validate.sh plans/valid.md
```

Python port (`validate.py`, stdlib only) mirrors the shell script:

```bash
python3 validate.py plans/valid.md
python3 validate.py --preset strict plans/valid.json
python3 validate.py --dry-run plans/valid.md  # print payload, no network
```

Exit codes (Python): `0` = READY, `1` = NEEDS_REVISION/REVIEW, `2` = BLOCKED.

## Presets

| Preset | `SAFE_MIN` | `EXE/COMP_MIN` | `RISK_BLOCK` | `RISK_READY` | `CONF_MIN` |
|--------|-----------|----------------|--------------|--------------|------------|
| `--strict` | 0.85 | 0.75 | 2.5 | 1.5 | 0.75 |
| `--normal` (default) | 0.7 | 0.6 | 3.0 | 2.0 | 0.6 |
| `--lenient` | 0.5 | 0.4 | 3.5 | 2.5 | 0.4 |

Full overrides: `SAFE_MIN EXE_MIN COMP_MIN CS_MIN CLS_MIN RISK_BLOCK RISK_READY SAFE_READY CONF_MIN`.

## Verdict logic

```
safe < SAFE_MIN or risk >= RISK_BLOCK       -> BLOCKED: unsafe
tools_grounded < EXE_MIN (json)             -> NEEDS_REVISION: hallucinated tools/paths
deps_sound < EXE_MIN (json)                 -> NEEDS_REVISION: broken dependencies
exe/comp < min or completeness/clarity low  -> NEEDS_REVISION: incomplete or unclear
readiness == blocked                        -> BLOCKED: model says blocked
readiness == needs_revision or conf low     -> NEEDS_REVISION: low confidence
readiness == ready + safe high + risk low   -> READY: execute
else                                        -> REVIEW: human check
```

## Tiered routing (`route.py`)

One validator strictness for every plan is wasteful — a typo fix and a prod
migration get the same treatment. `route.py` adds a cheap Jev router call
(`tier` choice, `difficulty` / `risk` scores, `needs_deep_review` noul) that
picks the validation lane. The validator itself is `validate.py`, imported —
no duplicated logic.

```bash
export TYPESAFE_API_KEY=...
python3 route.py plans/trivial.md
python3 route.py --repo owner/name plans/complex.md  # default: git remote / GH_REPO
python3 route.py --dry-run plans/standard.md
python3 route.py --self-test
```

| Condition | Lane |
|---|---|
| `trivial`, risk < 3, router conf ≥ 0.6 | Validator `--lenient`. Pass → READY. |
| `standard` (default) | Validator `--normal`. |
| `complex`, or risk ≥ 3, or conf < 0.6, or `needs_deep_review` ≥ 0.7 | Validator `--strict` for evidence, then **ESCALATE**. Never auto-READY. |

Hard rules: risk vetoes tier (high-risk `trivial` still escalates), low
confidence only moves *up* a lane, unreadable router output escalates.

Tuning: `ROUTER_CONF_MIN` (0.6), `RISK_ESCALATE` (3.0), `REVIEW_NOUL_MIN`
(0.7). Lane examples: `plans/trivial.md` → fast lane, `plans/standard.md` →
normal, `plans/complex.md` → escalate.

### Human escalation

On ESCALATE the strict results are bundled into a review packet (plan, tier +
scores, triggering rule, content sha) and upserted to a `plan-review` GitHub
issue via `gh` CLI: content-hash (`sha256`, pinned in the title) search finds
an open issue → new packet posted as a comment; otherwise a new issue is
created. Unchanged re-runs upsert into the same issue; any edit opens a fresh
one. No `gh` / no repo → packet prints to stdout, still exits 2.

The loop closes when the human edits the plan and re-runs, or signs off:

```bash
python3 route.py --signoff <sha12> plans/complex.md  # fails if plan changed
```

Every run appends to `decisions.jsonl` (timestamp, plan, sha, tier, scores,
verdict, issue URL) — tune thresholds from this, not vibes.

Exit codes: `0` = READY / signed-off, `1` = NEEDS_REVISION, `2` = ESCALATED /
BLOCKED, `3` = error.

## Revamp loop (`revamp.py`)

Jev can't write — it only judges. So when a plan fails, `revamp.py` closes
the loop with a generative model: route → rewrite from the findings →
re-route, up to `--rounds` (default 2). Revisions are saved as
`plan.rev1.md`, `plan.rev2.md`, … — the original is never overwritten.

```bash
export TYPESAFE_API_KEY=...      # for route.py (Jev, the judge)
export REVAMP_API_KEY=...        # generative key (else OPENROUTER_API_KEY / OPENAI_API_KEY)
python3 revamp.py plans/invalid.md
python3 revamp.py --rounds 3 --repo owner/name plans/complex.md
python3 revamp.py --dry-run plans/invalid.md  # show the rewrite prompt only
python3 revamp.py --self-test
```

Rules: `READY` stops the loop. `NEEDS_REVISION` rewrites until rounds run
out (exit 1, latest rev kept for the human). `ESCALATED` gets exactly one
rewrite, posted as a comment on the existing issue — the human still decides,
the loop never approves complex plans by itself. Every check and round is
logged to `decisions.jsonl`.

Config: `REVAMP_MODEL` (default `openai/gpt-4o-mini`), `REVAMP_BASE_URL`
(default `https://openrouter.ai/api/v1`, any OpenAI-compatible endpoint).

## Examples

* `plans/valid.md` / `plans/valid.json` — rate-limiting plan with tests, verification, rollback. Expect `READY`.
* `plans/invalid.md` / `plans/invalid.json` — vague DB tweak, `DROP TABLE users`, Friday prod deploy, hallucinated tool `magic-optimizer-9000`, dep on `s9`. Expect `BLOCKED` / `NEEDS_REVISION`.
* `plans/trivial.md` / `plans/standard.md` / `plans/complex.md` — one per router lane (typo fix / test+CI / Postgres migration). Expect fast-lane READY / normal verdict / ESCALATE.

## Requirements

`validate.sh`: `bash`, `curl`, `jq`. `validate.py`: `python3` stdlib only.
