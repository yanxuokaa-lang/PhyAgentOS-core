# jev-lab

Sandbox for [TypeSafe](https://docs.typesafe.ai) **Jev**: one request, several typed questions, code decides what to do.

This repo triages inbound messages. Jev returns a department (Choice), frustration (Score), urgency (Noul), and a speculative billing-dispute Noul. Routing and priority live in `src/triage.ts`. Question text and thresholds live in `src/questions.ts` so they are easy to review.

## Setup

```bash
cp .env.example .env   # paste TYPESAFE_API_KEY from https://console.typesafe.ai
npm install
npm run triage
```

Or one message:

```bash
npm run triage -- samples/calm-billing.txt
npm run triage -- --text "I was charged twice. Please fix this today."
```

`src/triage.ts` loads `.env` when that file exists; otherwise it uses `TYPESAFE_API_KEY` from the shell.

The TypeSafe agent skill is installed in `.agents/skills/typesafe-ai` and `.cursor/skills/typesafe-ai`.

## Layout

- `src/questions.ts` — questions + thresholds (edit these)
- `src/triage.ts` — CLI and composition
- `samples/` — three fixture messages

Low department confidence routes to `human_review` instead of auto-assigning a team.
