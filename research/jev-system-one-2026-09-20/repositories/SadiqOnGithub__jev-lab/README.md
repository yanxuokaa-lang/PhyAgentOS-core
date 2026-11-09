# jev-lab

Live tests for [TypeSafe Jev](https://docs.typesafe.ai) through
[OpenRouter's Decisions API](https://openrouter.ai/~typesafe/jev-latest).

Jev is **not a chat model**. It does not write sentences, essays, or
explanations. You send a `state` plus typed questions; it returns calibrated
probabilities: yes/no (`noul`), a pick from options you define (`choice`), or a
position on an ordered rubric (`score`).

## Ask Jev (`make ask`)

This is the interactive command. You set a **state** once, then keep asking
questions against it. Jev answers with a **number**, not a paragraph.

```bash
make ask
```

1. Paste the state (ticket, claim, JSON). End with an empty line.
2. At the `? ` prompt, type questions. The session stays open.

```
? Is this urgent?                         yes/no (noul) → 0.92
? /choice Which team?
options (comma-separated): billing,technical,sales
? /score How frustrated?
levels (comma-separated, low to high): Calm,Frustrated,Very angry
? /state                                  replace the state
? /print                                  show the state
? /help
? /quit
```

`0.92` means “very likely yes.” There is no written rationale.

One-shot (no session):

```bash
pnpm exec tsx src/run.ts ask --state "ticket text" --noul "Is this urgent?"
pnpm exec tsx src/run.ts ask --state "..." --choice "Which team?" --options billing,technical,sales
pnpm exec tsx src/run.ts ask --state "..." --score "How bad?" --levels "Low,Moderate,High"
```

## Setup

```bash
make install
cp .env.example .env   # then paste your OpenRouter API key
```

- `OPENROUTER_API_KEY` — from https://openrouter.ai/keys
- `JEV_MODEL` — optional. Default `~typesafe/jev-latest` (currently Jev 1.13).
  Pin with `typesafe/jev-1.13` if you need a fixed version.

The key already used by `../agentic-ai` works. Jev is billed on OpenRouter at
**$0.042 / M input tokens**, output free. Typical cases here cost well under a
cent.

## Canned cases

```bash
make help         # this list
make              # every case
make list         # ids
make ask          # interactive question (see above)
make smoke        # one case (also: route, verify, account, count, math)
make json         # raw responses
```

| id | What it tests |
|---|---|
| `smoke` | Support-ticket triage: noul + choice + score in one call |
| `route` | Next-tool pick for an agent loop (the intended use) |
| `verify` | Claim vs evidence, a guardrail-style check |
| `account` | Structured JSON state instead of a prose blob |
| `count` | Documented weak spot: counting |
| `math` | Documented weak spot: arithmetic |

`count` and `math` are TypeSafe's own jaggedness notes, not quality demos.
Keep counting and arithmetic in code; ask Jev semantic questions.

## Layout

```
src/
  client.ts    OpenRouter POST /api/alpha/decisions
  ask.ts       Interactive / CLI typed question
  cases.ts     Scenarios
  format.ts    Terminal report
  run.ts       CLI
  types.ts     Request / response shapes
```

This is a separate endpoint from `/api/v1/chat/completions`. Setting
`OPENROUTER_MODEL=typesafe/jev-1.13` on a chat client will not work.
