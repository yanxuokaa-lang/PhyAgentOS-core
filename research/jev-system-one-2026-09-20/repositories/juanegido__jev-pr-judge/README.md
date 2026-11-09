# PR Judge

[![CI](https://github.com/juanegido/jev-pr-judge/actions/workflows/ci.yml/badge.svg)](https://github.com/juanegido/jev-pr-judge/actions/workflows/ci.yml)

A demo of TypeSafe's System One primitives (the Jev model) judging whether a GitHub pull
request actually does what it claims — a fast, cheap, typed verdict for developers running
coding agents, instead of a slow LLM-as-judge prompt chain.

## Why System One fits here

- **One call, not a chain.** Every question runs in parallel against one bounded state; there's
  no multi-turn prompting and no waiting on a chain of chat completions.
- **Typed answers, not parsed text.** Scores, yes/no probabilities, and a labeled choice come
  back as numbers and enums code can use directly — no JSON-mode prompt engineering, no regexes
  over free text.
- **Policy lives in code, not in the prompt.** Weights, thresholds, and hard rules are plain
  TypeScript in `src/lib/judge/policy.ts`, reviewable and unit-tested like any other business
  logic. The model answers questions; your code decides.
- **Cheap enough to run on every PR.** One parallel call per pull request, not a slow
  multi-step agent loop, makes it practical to run as a CI gate rather than an occasional
  audit.

## Setup

1. Install dependencies: `npm install`
2. Copy the environment template (checked in as `env.example`):
   ```bash
   cp env.example .env.local
   ```
3. Get a TypeSafe API key at [typesafe.ai](https://typesafe.ai) and set `TYPESAFE_API_KEY` in
   `.env.local` (or `.env`; both are gitignored).
4. Optionally set `GITHUB_TOKEN` (a classic or fine-grained GitHub token) to raise GitHub's
   rate limit and read private repositories you have access to.

## Run

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), paste a pull request URL, pick a profile,
and click Judge.

## Use it as a GitHub Action

PR Judge also runs as a GitHub Action: it judges the current pull request and posts one sticky
comment with the verdict (updating it in place on later pushes rather than piling up comments).

```yaml
name: PR Judge
on:
  pull_request:
    types: [opened, synchronize, reopened, edited]

permissions:
  pull-requests: write
  contents: read

jobs:
  judge:
    runs-on: ubuntu-latest
    steps:
      # No checkout needed: the action reads the PR through the GitHub API.
      - uses: juanegido/jev-pr-judge@v1
        with:
          typesafe-api-key: ${{ secrets.TYPESAFE_API_KEY }}
          profile: balanced
          fail-on: none
```

### Inputs

| Input | Default | Description |
| --- | --- | --- |
| `typesafe-api-key` | *(required)* | TypeSafe API key used to call System One. |
| `github-token` | `${{ github.token }}` | Token used to read the pull request and post the comment. |
| `profile` | `balanced` | One of `balanced`, `hotfix`, `refactor`, `docs`. |
| `comment` | `true` | Post/update a sticky PR comment. Always writes to the job summary as well. |
| `fail-on` | `none` | One of `none`, `send_back`, `human_review`. Fails the step when the decision is at least this severe (`human_review` also fails on `send_back`). |
| `pr-number` | *(event's PR)* | Override the pull request number to judge. |

### Outputs

| Output | Description |
| --- | --- |
| `decision` | `approve`, `human_review`, or `send_back`. |
| `composite` | Composite score, `0`–`1` with two decimals. |
| `model-verdict` | The model's own verdict choice. |
| `model-verdict-confidence` | Confidence of the model's verdict, `0`–`1` with two decimals. |
| `hard-rule-hits` | Comma-separated ids of any hard rules that fired. |
| `comment-url` | URL of the posted/updated comment; empty if `comment` is `false`. |

Pull requests from forks do not receive repository secrets, so `typesafe-api-key` is empty and
the step fails for fork PRs unless the maintainer reruns it with access to the secret.

The action only reads the pull request through the GitHub API — it never checks out or executes
the pull request's code.

## CLI usage

```bash
npx tsx scripts/judge.ts <pr-url> [--profile balanced|hotfix|refactor|docs] [--json]
```

Add `--dump-request` to print the exact `{ model, state, questions }` payload the app sends to
`POST /v1/systemone` without calling the API — handy for pasting into the TypeSafe playground.
A captured example lives at `examples/nextjs-pr-1.request.json`.

`scripts/judge.ts` loads `.env.local` and then `.env` itself (no `dotenv` dependency, same
precedence as Next.js), so it works the same way whether you run it standalone or through the
web app.

## Evaluation

`scripts/evaluate.ts` and `scripts/report.ts` measure how PR Judge behaves on real, historical
pull requests from a public repository, against two independent reference labels: **merge
outcome** (merged vs. closed-unmerged — a noisy proxy for quality) and **deterministic,
regex-based proxies** (`src/lib/eval/proxies.ts`) computed from the diff itself, independent of
merge outcome, for the Noul flags a pattern can approximate. See
[`evaluation/README.md`](./evaluation/README.md) for how to reproduce it and what it costs.

### Results: 50 closed PRs from `excalidraw/excalidraw`

Full tables in [`evaluation/REPORT.md`](./evaluation/REPORT.md) (14 merged, 36 unmerged; all 16
questions). The short version:

- **The red flags separate cleanly where a proxy exists.** `claims_tests_without_evidence`
  averaged 0.64 when the regex proxy fired vs. 0.03 when it did not (precision 1.00, recall 0.63
  at the 0.5 threshold); `unmentioned_debt` 0.71 vs. 0.11 (precision 1.00, recall 0.75). The one
  PR with a proxy-detected secret scored 0.87.
- **The security flags stayed quiet where they should.** Excalidraw has no SQL and no
  migrations; `sql_injection_risk` and `destructive_migration` averaged 0.03 with a maximum of
  0.04 across all 50 PRs — zero false alarms. `touches_auth` reached 0.94 on exactly one PR, a
  71-file revert that did touch auth paths; the path-only proxy fired on four, which is the
  expected gap between "an auth-sounding file changed" and "auth behavior changed".
- **Policy decisions are monotone with merge outcome.** Of the PRs the balanced profile approved,
  50% were merged; human_review 29%; send_back 11%. The model's own verdict shows the same
  ordering (48% / 13% / 0%).
- **The test-evidence rubric is the dimension that moves.** Mean 2.57 / 3 on merged PRs vs.
  1.44 on unmerged, and the gap survives splitting by maintainer status. Reviewer effort runs the
  other way (2.39 vs. 1.76): the merged PRs are mostly maintainers' features, and they are harder
  to review — which is why effort is shown but kept out of the composite.
- **The evaluation fixed the evaluator twice.** In the first run the naive `leftover_debug`
  proxy fired on three PRs the model scored at ~0.07; all three were proxy false positives
  ("debugger-friendly" in Markdown prose, a code comment, a CLI script whose job is to print). In
  the second run the model gave 0.68 to a PR that deleted two test cases inside an existing file,
  and the code-fact rule missed it because it only counted whole-file removals. Both times the
  code changed; the model did not.
- **Cost of the sample:** ~11k input tokens and ~1.7 s per PR, 566k tokens for all 50. Going
  from 11 to 16 questions added about 9% to input tokens — the state is sent once, the
  questions ride along.

What it does *not* show: with only 2 merged PRs from non-maintainers, there is no evidence either
way on whether the judge separates quality once authorship is held constant. Merge outcome is a
noisy label, the proxies are regexes, large PRs were judged on truncated diffs, and thresholds
were not tuned on this data. Every caveat is spelled out in the report.

## How the questions are designed

The heart of this demo is `src/lib/judge/questions.ts`: five **scores** (concrete, ordered
rubrics — four of which feed the composite, plus `reviewer_effort`, which does not), ten
**nouls** (yes/no red flags with explicit true/false criteria), and one **choice** (the model's
own verdict). Each instruction is self-contained — question IDs are never sent to the model, and
questions can't see each other's answers, so nothing beyond the bounded state and that one
instruction string informs an answer. See the primitive docs this design follows:

- [`score`](https://docs.typesafe.ai/primitives/score.md)
- [`noul`](https://docs.typesafe.ai/primitives/noul.md)
- [`choice`](https://docs.typesafe.ai/primitives/choice.md)
- [Composite scoring pattern](https://docs.typesafe.ai/patterns/composite-scoring.md)
- [JavaScript SDK](https://docs.typesafe.ai/sdk/javascript.md)

### Code facts vs. model judgments

Not everything PR Judge reports comes from the model. `src/lib/judge/code-facts.ts` computes a
small set of **code facts** — deterministic, regex- and path-based counts like test files removed,
test cases disabled, migration files touched, and auth-related paths touched — directly from the
pull request's full diff, before any truncation. These facts are handed to the model as
`code_facts` in the state (see `buildJudgeState` in `src/lib/judge/state.ts`), so the model reasons
from observed evidence instead of re-deriving it from a possibly-truncated patch, and the policy
layer can also use them directly, with no model call at all (see the code-fact rule below).

The split is deliberate: anything a regex or path pattern can answer on its own (does this path
look like a test file? does this path look like a migration?) is computed in code, not judged.
Judgments (nouls and scores) are reserved for questions that need semantic understanding a pattern
can't provide — whether a query is actually vulnerable to injection, whether a migration is safely
reversible, whether removed tests were justified by the PR's own description.

### Hard rules

A handful of Noul answers bypass the composite entirely and are checked in `src/lib/judge/policy.ts`:

- `possible_secret >= 0.7` → **send_back** (block), regardless of profile.
- `claims_tests_without_evidence >= 0.8` → **send_back** (block).
- `sql_injection_risk >= 0.7` → **send_back** (block).
- `breaking_change_unflagged >= 0.75` → at least **human_review** (never approved outright).
- `touches_auth >= 0.7` → at least **human_review**.
- `destructive_migration >= 0.7` → at least **human_review**.
- `test_deletion_unjustified >= 0.7` → at least **human_review**.
- **Code-fact rule** (no model call): if `code_facts.test_files_removed` is non-empty or
  `code_facts.test_cases_disabled > 0`, and `test_deletion_unjustified >= 0.5` → at least
  **human_review**. The lower threshold (0.5 instead of 0.7) is deliberate: when the deterministic
  facts already establish that tests were removed or disabled, a lower model probability is enough
  to warrant a human look.

## Adding a profile

Profiles live in `PROFILE_WEIGHTS` in `src/lib/judge/policy.ts`, as weights over four
normalized dimensions (`scope`, `tests`, `safety`, `description`) that must sum to 1 — a unit
test in `policy.test.ts` checks this for every profile. Add an entry there and to
`PROFILE_LABELS`, then add the profile's id to `PROFILES` in `src/lib/judge/types.ts`. No change
to the questions or the API route is needed: profiles only affect how the same answers are
weighted, which is why switching profiles in the UI recomputes instantly with no re-inference.

## Honest caveats

- **Typed output guarantees the interface, not the truth.** A `score` of 3/3 for test evidence
  means the model committed to that rubric level with some confidence — it does not mean the
  tests are actually good. Treat every answer as a strong, cheap signal, not ground truth.
- **Thresholds are starting points.** The hard-rule cutoffs (e.g. `possible_secret >= 0.7`) and
  the `approve` / `human_review` / `send_back` composite bands were picked to be reasonable
  defaults, not calibrated against your team's pull requests. Watch the flags on real PRs and
  adjust `policy.ts` accordingly.
- **State is truncated for large diffs.** Per-file patches are capped and the total patch budget
  is bounded (see `src/lib/judge/state.ts`); on large pull requests the model is judging a
  partial diff, and the UI's "State sent to model" panel tells you what was cut.
