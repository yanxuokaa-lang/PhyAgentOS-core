# Jev cross-border B2B payments triage prototype

A small case-management board for the operations desk of a cross-border B2B
payments provider. Every incoming case (payment not received, returned,
wrong beneficiary details, recall, FX dispute, deducted charges, compliance
hold, funding not matched, suspected fraud, integration failure, document
request) is triaged by [Jev](https://typesafe.ai), TypeSafe's System One
decision model, called through [OpenRouter](https://openrouter.ai/typesafe).

Jev is not a chat model. You send it your application state plus a map of typed
questions and it returns typed answers with calibrated probabilities. There is
no prompt to engineer and no free text to parse. That makes it a good fit for
the triage step of a workflow: classify, prioritise, route, flag, then hand off
to deterministic rules and humans.

## Quick start (macOS, Linux)

You need Node 22.9 or newer and an [OpenRouter](https://openrouter.ai/keys) key
with a little credit. Nothing to install: the project has zero dependencies.

```bash
# Node, if you do not have it
brew install node            # or: nvm install 22 && nvm use

git clone https://github.com/maraichr/jev-triage.git
cd jev-triage
npm run doctor               # creates .env from the template on first run
```

Open `.env`, paste your key after `OPENROUTER_API_KEY=`, then:

```bash
npm run doctor               # checks Node, the key, and makes one live Jev call
npm start                    # http://localhost:3040
```

On Windows the steps are the same in PowerShell; `npm run doctor` creates the
`.env` for you so there is no `cp` versus `copy` difference.

The header badge says **LIVE via openrouter** when a key is present, or
**MOCK decider** when it is not. Mock mode uses deterministic keyword
heuristics that return the same JSON shape as Jev, so the board, the routing
rules and the UI all work offline.

Smoke test across the ten seed cases from the command line:

```bash
npm run smoke
```

## Sharing a recorded demo

`demo/jev-triage-demo.html` is a single self-contained file: the same board
with the real Jev answers from a live run embedded, replayed at their recorded
latency, plus a walkthrough panel. Send it to anyone; it opens from disk with
no server, no key and no network. New-case and preview need the live app.

To re-record after changing the questions or seed cases, run the live app,
click **Triage all intake**, then:

```bash
npm run demo                          # snapshots the server into demo/
npm run demo -- demo/snapshot.json    # rebuild the file from a saved snapshot
```

## Using it with Claude Code

The repo ships a `CLAUDE.md` with the layout, the run commands and the Jev
facts that are not obvious from the docs, plus a `.claude/settings.json` that
pre-approves the run and smoke commands and blocks reading `.env`. So:

```bash
cd jev-triage
claude
```

and ask for what you want. Prompts that work well on a first visit:

- "Run the doctor and start the server, then triage all the seed cases and tell me which one you would route differently."
- "Add a question that asks whether the client is likely to churn over this, and surface it on the card."
- "Add three seed cases about SEPA Instant rejections and one about a beneficiary bank asking for a purpose-of-payment code."

## What you see

Five-stage board: **Intake, Triaged, Assigned, In review, Resolved**.

1. Cases land in Intake from email, portal, phone or API (seeded from `data/seed-cases.json`).
2. **Run triage** (or **Triage all intake**) sends the case state to Jev with nine typed questions.
3. Jev's answers go through the routing rules in `lib/triage.js`, which set the queue, priority, SLA clock, flags and next actions. The panel shows every probability so an operator can see why.
4. Cases below the auto-route confidence threshold land in a `human_triage` queue instead of a desk.
5. **Move to ...** advances the case through the workflow. History is kept per case.

**New case** opens an intake form with a **Preview triage** button that calls Jev without saving, so you can watch the decision change as you edit the description.

## The domain

**Categories:** payment delayed, payment returned, beneficiary details error,
recall request, FX dispute, fees deducted, compliance hold, funding issue,
suspected fraud, integration failure, reporting request, onboarding and KYC,
other.

**Desks:** payment operations, treasury and FX, compliance, fraud, technical
support, client support. Plus a `human_triage` queue for low-confidence picks.

**Questions Jev answers per case:**

| Question | Type | Used for |
|---|---|---|
| category | choice | Next-action checklist, card label |
| owning_desk | choice | Queue, subject to the confidence gate |
| priority | score P4 to P1 | SLA clock |
| fraud_indicators | yes/no | Forces the fraud desk; P1 if funds are still recallable |
| compliance_touch | yes/no | Forces the compliance desk. Routing only, never a decision |
| recall_window_open | yes/no | P1 for recalls and amendments while it is open |
| time_critical | yes/no | At least P2, cutoff advice |
| partner_bank_action | yes/no | Adds the partner-bank query to next actions |
| information_complete | yes/no | Adds a go-back-to-client step first |

## The Jev call

Request, built in `lib/triage.js`:

```json
{
  "model": "~typesafe/jev-latest",
  "state": {
    "case_ref": "PAY-2026-3107",
    "client": { "name": "Tessuti Marino SpA", "segment": "mid-market", "country": "IT" },
    "payment": {
      "reference": "PMT-91120-EUR", "amount": 85000, "currency": "EUR", "rail": "SEPA",
      "status": "sent", "sent_at": "2026-09-18T09:44:00Z", "value_date": "2026-09-18",
      "payer_country": "IT", "beneficiary_country": "FR", "charge_option": "SHA"
    },
    "title": "Duplicate EUR 85k payment sent twenty minutes ago, client asks for recall",
    "description": "..."
  },
  "questions": {
    "category":           { "type": "choice", "instructions": "...", "criteria": { "recall_request": "...", "payment_delayed": "..." } },
    "owning_desk":        { "type": "choice", "instructions": "...", "criteria": { "payment_operations": "...", "fraud": "..." } },
    "priority":           { "type": "score",  "instructions": "...", "criteria": ["P4 - Routine", "P3 - Standard", "P2 - High", "P1 - Critical"] },
    "fraud_indicators":   { "type": "noul",   "instructions": "..." },
    "recall_window_open": { "type": "noul",   "instructions": "..." }
  }
}
```

Response shape:

```json
{
  "model": "typesafe/jev-1.13-20260917",
  "answers": {
    "category":           { "type": "choice", "choice": "recall_request", "probabilities": { "recall_request": 1.0 }, "confidence": 1.0 },
    "priority":           { "type": "score", "score": 2.4, "legend": { "0": "P4 ...", "3": "P1 ..." }, "probabilities": { "2": 0.46, "3": 0.54 }, "confidence": 0.54 },
    "fraud_indicators":   { "type": "noul", "noul": 0.03 },
    "recall_window_open": { "type": "noul", "noul": 0.91 }
  },
  "usage": { "input_tokens": 1760, "output_tokens": 0 }
}
```

Note on score answers: the levels are 0-indexed into your `criteria` array and
`score` is an expected value over that distribution, not an integer. The
routing takes the most probable level rather than rounding.

Routes, in `lib/jev.js`:

| Env var | Endpoint | Model |
|---|---|---|
| `OPENROUTER_API_KEY` | `POST https://openrouter.ai/api/alpha/decisions` | `~typesafe/jev-latest` |
| `TYPESAFE_API_KEY` | `POST https://api.typesafe.ai/v1/systemone` | `jev-latest` |

TypeSafe wins if both are set. The OpenRouter route is a beta path and may move.
Override with `JEV_URL` and `JEV_MODEL` if it does. Jev is not listed on
OpenRouter's `/api/v1/models` and does not answer on `/chat/completions`.

Pricing at time of writing: $0.042 per million input tokens, output free. A
triage call here is roughly 1,500 to 2,000 input tokens, so under a hundredth
of a cent per case.

## Design notes

- **Model judges, code decides.** Jev answers the fuzzy questions (what kind of case, which desk, how urgent, does this look like fraud). SLA hours, the confidence threshold, the fraud and compliance overrides and the next-action checklists are plain code in `route()` so they can be audited, unit tested and changed without touching the model.
- **Compliance is routing only.** The model can send a case to the compliance desk. It never clears a hold, never judges a screening match, and the next actions tell the operator not to discuss the reason for a hold with the client.
- **Fraud wins.** Fraud indicators force the fraud desk regardless of the category, lift priority to P2, and to P1 when the payment is still recallable. The first next action is to call the client back on a known number.
- **Confidence gating.** `owning_desk` below 60 percent confidence goes to `human_triage` rather than a desk. Tune `AUTO_ROUTE_CONFIDENCE`.
- **Everything is visible.** Each case keeps the exact request state, the questions and the full probability distributions, shown under *Raw request and response*.

## Layout

```
server.js            HTTP server, in-memory case store, workflow endpoints
lib/jev.js           Jev client: route selection, retries, error type
lib/triage.js        Question schema, routing rules, offline mock decider
public/index.html    Single-page board and case panel
data/seed-cases.json Ten realistic payment operations cases
test/smoke.mjs       Runs triage over the seed set and prints a table
scripts/doctor.mjs   Checks Node, .env, the key and makes one live Jev call
CLAUDE.md            Context for Claude Code
```

## Next steps if the prototype earns a second week

- Persist cases (SQLite) and add assignment to named users per desk.
- Feed operator overrides back as a labelled set to check Jev's calibration.
- Add a second Jev call at the *In review* stage: "is the client's ask resolved?" and "does the reply need a second pair of eyes?"
- Wire intake from a real mailbox, the client portal or the API error stream.
- Add a data-minimisation step before the call: client and beneficiary names to role tokens, references hashed, PAN detector.
