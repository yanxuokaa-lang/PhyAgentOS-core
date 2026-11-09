# Email triage with Jev

A small script that runs [Jev](https://docs.typesafe.ai/introduction), TypeSafe's decision model, over a JSON file of emails. Jev answers four questions per email: category, importance, brand-deal, scam. The calls go through the [Vercel AI Gateway](https://vercel.com/ai-gateway) with one key.

Inspired by Riley Brown's video [*Jev: the model that can't write*](https://www.youtube.com/watch?v=o1CogAtWdBk), where he triages his inbox with Jev. This repo is that idea, run over 90 days of a real inbox and documented step by step with Claude Code. The companion repo [jev-model-router](https://github.com/az9713/jev-model-router) uses Jev to pick which LLM answers a chat message.

- **Development journey:** https://az9713.github.io/jev-email-triage/ — how the mail was fetched, the four questions, every input and output file (redacted), four mis-ranks and their causes, and 17 unknown unknowns.
- **Reliability upgrade:** https://az9713.github.io/jev-email-triage/reliability-upgrade.html — what changed, why it changed, how resumable atomic processing works, and the new evaluation evidence.

## How it works

1. `triage.mjs` reads a JSON array of `{ id, date, from, subject, snippet }`.
2. For each email it sends one `experimental_evaluate` call to `typesafe-ai/jev` with four questions:

| Question | Type | Answer |
|---|---|---|
| `category` | choice | one of `security_alert`, `receipt`, `service_notice`, `newsletter`, `personal_reminder`, `business_inquiry`, `other` |
| `importance` | score | 0 to 5 on a six-step rubric from `ignore` to `insane` |
| `brand_deal` | boolean | probability that the email is a sponsorship or brand-deal offer |
| `scam` | boolean | probability that the email is a scam or phishing |

3. It writes `<input>.triage.json` and prints a table sorted by importance.

Change the questions in the `QUESTIONS` block at the top of `triage.mjs`.

## Run it

Needs Node 20.6 or later and a Vercel AI Gateway key on the paid tier. The free tier limits Jev to a few calls.

```
npm install
echo AI_GATEWAY_API_KEY=your_key > .env
node --env-file=.env triage.mjs emails.json [--limit N] [--raw] [--resume]
```

Full runs checkpoint to a separate partial file after every email and replace the final output only after completion. `--resume` continues an interrupted full run. `--limit N` runs the first N records without writing output. `--raw` prints each full answer and metadata.

`npm test` runs the free deterministic checks and the held-out evaluation contract. `npm run eval:live` runs the same 12 cases against Jev and saves JSONL results under `eval/`.

The 41 emails from the journey came from the Gmail MCP `search_threads` tool: INBOX, last 90 days, snippets only. They are not in this repo.

## Cost

About $0.00003 per email on the gateway. The 41-email run cost about $0.001.
