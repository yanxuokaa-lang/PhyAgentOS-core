# JEValuate

Auto-marks thousands of maths scripts against a teacher-style rubric with
[Jev](https://docs.typesafe.ai) (TypeSafe's System One model), and measures
agreement with human annotators.

![Replay of the recorded run, then the breakdown of one script where Jev and the human annotator disagree](docs/demo.gif)

## Results

Full run, 2,054 scripts, `jev-1.13.0`, 2026-09-19:

| | |
|---|---|
| Method sound — agreement with human label | **96.6%** |
| First wrong step — exact match, on the 1,084 scripts that contain an error | 64.7% |
| First wrong step — agreement over all scripts (includes "no error" on both sides) | 79.2% |
| Right answer reached by a wrong method — caught | 35 of 48 |
| Mark out of 3 — exact match with the mark the human labels imply | 96.1% |
| Final answer (judged by code) — agreement | 99.0% |
| Flagged for teacher review | 79 (3.8%) |
| Time | 89 s at concurrency 16 (23 scripts/s) |
| Cost | $0.25 (5.9M input tokens) |

"Agreement" means agreement with a single human annotator per script, not ground
truth. The review flag earns its place: the 79 flagged scripts agree with the human
63% of the time, the other 1,975 agree 97.9% of the time.

Ablation on a 200-script sample: passing code-verified arithmetic checks to Jev
made no measurable difference (method 96.5% with, 96.0% without; first error 83.0%
with, 84.5% without — within noise at n=200).

## How it marks

One Jev call per script, all rubric questions answered in parallel:

- **Code** judges the final answer and checks every `a op b = c` it can parse.
- **Jev** judges whether each step is valid given the steps before it, whether the
  method as a whole is sound, and which category the first error falls into.
- **Code** turns that into marks (1 answer + 2 method), the first failing step
  (first step under 0.5), and a review flag (method probability 0.3–0.7).

## Data

[MR-GSM8K](https://huggingface.co/datasets/Randolphzeng/Mr-GSM8K) (Apache-2.0):
grade-school maths problems, each with a step-by-step attempt and human labels for
answer correctness, method correctness, the first wrong step, and the reason.
`bun run prep` keeps 2,054 of the 2,999 rows: it drops rows with no numeric answer
key (593, a defect in the source data), program-of-thought attempts that are code
rather than prose (222), rows with no reference solution (97), and attempts longer
than 20 steps (33).

The attempts were **written by language models, not students**. The mistakes are
the kind students make (wrong operation, misread question, unjustified assumption);
the tidy prose is not. The human labels are never shown to Jev — they are only
used to score it.

## How the page works

- **Mark all** replays the recorded full run (`public/index.json`,
  `public/results.json`) at the speed it actually ran.
- **Run live (50)** and **Mark this script live** call Jev for real.

## Commands

```sh
bun install
bun run smoke            # one real Jev call — run this first
bun run prep             # download + normalise MR-GSM8K -> public/scripts.json
bun run eval             # mark everything -> public/results.json, public/index.json
bun run eval --limit 200 # sample; add --no-arithmetic for the ablation
bun run eval --mock      # fake results for UI work, no API key (tagged MOCK DATA)
bun run dev
bun run test
```

Set `TYPESAFE_API_KEY` in `.env.local` for local runs, and as an environment
variable in Vercel for the deployed `/api/mark` route. The key is only read
server-side. The model is pinned to `jev-1.13.0` in `lib/types.ts`.

Design: `docs/superpowers/specs/2026-09-19-jevaluate-design.md`.
