# jev-sandbox

I built this repo to test a practical question: **when can a small decision
model do the job I'd otherwise give an LLM?**

[Jev](https://docs.typesafe.ai/introduction) is TypeSafe's decision model. You
send it data and typed questions; it returns answers and probabilities rather
than text to parse. These tests use **Choice** questions (pick a named option)
and **Nouls** (score a yes/no question from 0 to 1).

I tested email triage and gluten detection in ingredient lists. Each experiment
records the setup, results, limits, and what I'd try next.

## What I learned

- **Email routing looks promising.** With separate questions about why an
  email might matter and some recipient context, Jev decided 121 of 129
  emails outright. None of the emails it called routine disagreed with the
  existing classifier. This still needs a fresh sample.
  [Email results →](experiments/02-reasons-to-care/RESULTS.md)
- **On ingredient lists, Jev held up against a production LLM request.** I
  found no listed-gluten misses from Jev or Claude Opus 4.8 in the 996-label
  comparison. In this test, Jev's median response was 17× faster, at an
  estimated 240× lower cost.
  [Side-by-side results →](experiments/05-llm-side-by-side/RESULTS.md)
- **Instructions explained most disagreements.** Adding the LLM's caution
  policy for vague ingredients raised verdict agreement from 76% to 90%.
  Whether that policy is useful is a separate question.
  [Policy results →](experiments/06-vague-ingredients/RESULTS.md)
- **Missing text was harder than garbled text.** Both models called some
  truncated labels `safe` after the cut removed the gluten ingredient.
  [Damaged-label results →](experiments/04-ocr-noise/RESULTS.md)
- **Check what you're scoring against.** An email-classifier outage and
  incomplete food-database tags both made good answers look wrong.
  [Reference-label audit →](experiments/03-gluten-labels/RESULTS.md)

> **Not medical advice.** The gluten experiments test model behavior, not
> whether a food is safe to eat. `safe` is an experimental output label, not a
> recommendation for someone with celiac disease.

## What's here

| Path | Contents |
| --- | --- |
| [`experiments/`](experiments/README.md) | Six experiments, each with questions, data instructions, and results |
| `lib/` | Shared client, runner, and scoring for agreement, confidence thresholds, latency, cost inputs, and error bounds |
| `protocols/` | Detailed procedures for individual experiments |
| `scripts/` | Dataset preparation |
| [`.claude/skills/typesafe-ai/`](.claude/skills/typesafe-ai/AUDIT.md) | A pinned, audited copy of TypeSafe's agent skill |

## Try it

Requires Node 24+ (runs TypeScript directly; no build step).

```sh
npm ci --ignore-scripts
cp .env.example .env    # add a key from https://console.typesafe.ai/keys
npm test
node --env-file=.env experiments/01-email-triage/run.ts             # synthetic fixtures
node --env-file=.env experiments/03-gluten-labels/run.ts --public    # 3,300 public labels, ~$0.12
```

[Experiment 05](experiments/05-llm-side-by-side/README.md) also needs
`ANTHROPIC_API_KEY` (use a dedicated, spend-capped key) and a local checkout of
the scanner it compares against. Cost estimates use the rates recorded in the
results, not a guarantee of current pricing.

`@typesafe-ai/sdk` is pinned to an exact, audited version. Update it
deliberately, not with a version range.

## Data and privacy

The scripts are public; private inputs and raw responses are not.

- Private datasets live in gitignored `data/real/` directories. Their results
  contain aggregates only—no real email examples or recipient context.
- Raw responses live in gitignored `raw/` directories.
- Public datasets are committed under `data/public/` with license notes.
- Default runs use fixtures: synthetic emails or, for experiment 03, a small
  subset of the public labels. `--real` and `--public` are explicit opt-ins.
