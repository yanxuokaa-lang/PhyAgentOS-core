# pi-jeev

A bounded TypeSafe Jev decision tool for [Pi](https://pi.dev).

Jev is a System One model. It evaluates narrow typed questions against supplied evidence. It is not an agent and does not replace the model that gathers evidence, creates options, or executes work.

## What it does

`jev_decide` compares two to eight plausible actions after deterministic rules have run. The caller supplies:

- observed facts;
- explicit constraints;
- known unknowns;
- balanced evidence for and against every option;
- the consequence level of a wrong recommendation.

One TypeSafe request evaluates the choice, evidence sufficiency, and support for every candidate in parallel. Local policy then returns one of three states:

- `recommend`: the low or medium-stakes result cleared every configured threshold;
- `abstain`: the evidence, support, probability, or margin was too weak;
- `review_required`: the decision was marked high stakes.

The extension never executes the selected action. `abstain` and `review_required` deliberately return `recommendation: null`.

## Install

Clone the repository into Pi's global extension directory and install development dependencies without lifecycle scripts:

```sh
git clone https://github.com/shishiv/pi-jeev ~/.pi/agent/extensions/jev
cd ~/.pi/agent/extensions/jev
npm ci --ignore-scripts
git config core.hooksPath .githooks
```

Add the extension to `~/.pi/agent/settings.json`:

```json
{
  "extensions": ["+extensions/jev/index.ts"]
}
```

Then reload Pi and enable Jev:

```text
/reload
/jev on
```

`/jev on` and `/jev off` update `~/.pi/agent/jev.json`. Every idle Pi process using the same agent directory observes that global setting. A busy process applies the change after its current response settles.

## Agent contract

Use Jev only when direct evidence and deterministic rules leave at least two materially plausible options whose difference requires semantic judgment.

Do not use it for arithmetic, exact lookup, authorization, security policy, known state transitions, or execution of an already selected action. Keep those decisions in code or in the governing human and project rules.

Example input:

```json
{
  "question": "Which support team should receive this request?",
  "context": {
    "observed": ["The customer reports a duplicated charge and requests a refund."],
    "constraints": ["Choose the team responsible for the reported problem."],
    "unknowns": []
  },
  "options": [
    {
      "id": "billing",
      "action": "Route to billing.",
      "evidenceFor": ["The request concerns a charge and refund."],
      "evidenceAgainst": []
    },
    {
      "id": "shipping",
      "action": "Route to shipping.",
      "evidenceFor": [],
      "evidenceAgainst": ["No delivery problem is reported."]
    }
  ],
  "stakes": "low"
}
```

The extension canonicalizes option order before transmission. This prevents the caller's preferred ordering from becoming the wire order. Structured fields keep observations, constraints, unknowns, and advocacy distinct.

## Decision policy

The current conservative seed policy is:

| Stakes | Top probability | Margin over runner-up | Evidence sufficiency | Candidate support | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| `low` | 0.60 | 0.12 | 0.55 | 0.55 | Recommend only when all pass |
| `medium` | 0.75 | 0.20 | 0.70 | 0.65 | Recommend only when all pass |
| `high` | n/a | n/a | n/a | n/a | Always require review |

These are application policy, not universal TypeSafe thresholds. Change them only against labeled evaluations and the cost of wrong actions.

## Privacy and failure behavior

Only the explicit tool input is sent to `https://api.typesafe.ai/v1/systemone` with `jev-latest`. The extension does not collect files, conversation history, or other tool results automatically.

The API key is read from `TYPESAFE_API_KEY` or Pi's `.env`. It is not included in tool arguments or results. Requests have a 15-second deadline, reject redirects, limit bodies and responses, and never retry automatically.

Malformed responses, incomplete answer sets, inconsistent probability distributions, missing credentials, cancellation, and network errors return errors rather than recommendations.

## Development

The project targets Node 26 and TypeScript 7.

```sh
npm ci --ignore-scripts
npm run check
```

`npm run check` runs typechecking, Oxlint with the local anti-slop plugin, and the unit suite with one worker. The repository uses a tracked pre-commit hook through `core.hooksPath=.githooks`. Checks are local; the repository does not use GitHub Actions.

Two opt-in evaluations exercise behavior against live services:

```sh
npm run eval:live
npm run eval:agent
```

`eval:live` runs labeled clear, ambiguous, constrained, and high-impact cases three times each. It also proves that reversing caller option order produces the same request. Results are written under ignored `eval/results/`.

`eval:agent` runs isolated Pi turns for one semantic decision and one deterministic calculation. It checks that the agent calls Jev only for the semantic decision. Both commands consume external model quota.

The initial local V2 run passed 6 of 6 labeled cases across 18 Jev calls. It used 18,678 input tokens and completed the TypeSafe calls in 5.8 seconds total. This is a seed evaluation, not proof of broad domain accuracy.

## Design references

The integration follows TypeSafe's current guidance:

- [Introduction](https://docs.typesafe.ai/introduction)
- [How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)
- [Confidence](https://docs.typesafe.ai/confidence)
- [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
