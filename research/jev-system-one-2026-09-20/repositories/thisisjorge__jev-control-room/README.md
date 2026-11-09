# Jev Control Room

Decide first. Generate less.

A visual control room for **TypeSafe Jev**, built around a simple idea: AI does not always need to generate text. For routing, gating, scoring, and agent control, the useful output is often a typed decision plus uncertainty.

> State in → **Choice / Score / Boolean** → confidence policy → act, review, or keep manual.

![Status](https://img.shields.io/badge/Jev-TypeSafe_AI-c8ff4d?labelColor=11151b)
![AI SDK](https://img.shields.io/badge/AI_SDK-7-ffffff?labelColor=11151b)
![Next.js](https://img.shields.io/badge/Next.js-16.3-ffffff?labelColor=11151b)

## Why this exists

Jev is accessed through Vercel AI Gateway. Unlike a normal language-model workflow that generates prose or JSON and then parses it, the AI SDK's experimental evaluation API returns typed decisions for declared questions.

This repo is intentionally **not another chatbot**. It demonstrates where a decision model fits inside software.

## What the demo includes

- **Support Triage** — route, priority, human-review gate
- **Lead Qualification** — fit, urgency, sales-ready gate
- **Agent Router** — act, reason, ask, retry, or stop
- **Code Review Gate** — merge state, risk, more-tests gate
- **Workflow Guard** — continue, retry, pause, or escalate
- Confidence-aware policy engine
  - `>= 85%` → `AUTO`
  - `60–84%` → `REVIEW`
  - `< 60%` → `MANUAL`
- Browser-local history (`localStorage`)
- Raw provider-response inspector
- Lightweight per-instance request throttling for the public API route
- Gateway default routing for the public/Hobby demo; per-request ZDR can be enabled on supported Pro and Enterprise plans
- Automatic **demo mode** when no Gateway key is configured; the public deployment runs in DEMO mode
- LIVE errors stay errors; they never fall back to demo output

## Stack

- Next.js 16.3+
- React 19
- TypeScript
- Vercel AI SDK 7 (`experimental_evaluate`)
- Vercel AI Gateway
- TypeSafe Jev (`typesafe-ai/jev`)
- Plain CSS — no UI framework required

## Run locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

To run LIVE evaluations, create `.env.local` from `.env.example` and add your own server-side `AI_GATEWAY_API_KEY`. Never commit the key.

### Live Jev mode

Create an AI Gateway API key in Vercel and put it in `.env.local`:

```bash
AI_GATEWAY_API_KEY=your_key_here
```

The mode reads `NOT RUN` before evaluation, `LIVE` only after a successful Gateway response, and `LIVE ERROR` when a Gateway call fails. A valid key and an AI Gateway account able to service requests are both required. A configured but invalid key is an error, not a trigger for DEMO mode.

For a public deployment, also set a small AI Gateway budget/usage limit. The included in-memory throttle is only a lightweight abuse guard, not a distributed production rate limiter.

Without a key, the interface remains usable in **DEMO MODE** with deterministic local mock decisions. Demo output is labeled `DEMO` and `typesafe-ai/jev (simulated)`; it is never represented as a real Jev response.

## The core call

```ts
import { experimental_evaluate as evaluate } from 'ai';

const result = await evaluate({
  model: 'typesafe-ai/jev',
  state: 'The customer says they were charged twice.',
  questions: {
    route: {
      type: 'choice',
      instructions: 'Choose the best support queue.',
      criteria: {
        billing: 'Charges, payments, invoices, refunds',
        technical: 'Bugs, access, integrations',
      },
    },
    urgency: {
      type: 'score',
      instructions: 'How urgent is this case?',
      criteria: [
        'Low: can wait',
        'Normal: needs attention',
        'High: meaningful customer impact',
        'Critical: immediate severe impact',
      ],
    },
    humanReview: {
      type: 'boolean',
      instructions: 'Should a human review before an irreversible action?',
    },
  },
});
```

## Policy design

The app uses the **least confident head** as policy confidence instead of averaging confidence across questions. If any head lacks a usable confidence signal, the policy is `MANUAL`. Choice and Score use TypeSafe's provider-specific confidence metadata when present; Choice can fall back to its selected-option probability. Boolean uses the probability of the chosen true/false outcome. These signals are not interchangeable or guaranteed to be calibrated.

Do not copy these thresholds blindly into production. Calibrate them using labeled examples from the workflow you are actually automating.

## Architecture

```text
Application state
      │
      ▼
 TypeSafe Jev
      │
 ┌────┼─────┐
 ▼    ▼     ▼
Choice Score Boolean
 └────┼─────┘
      ▼
Confidence policy
      │
 ┌────┼────────┐
 ▼    ▼        ▼
AUTO REVIEW  MANUAL
```

## Project structure

```text
app/
  api/evaluate/route.ts   # Gateway + Jev call
  globals.css             # control-room visual system
  layout.tsx
  page.tsx                # client dashboard
lib/
  demo.ts                 # explicit offline/demo mode
  normalize.ts            # Jev answer → UI decision
  policy.ts               # confidence gate
  presets.ts              # use-case presets
  questions.ts            # Choice / Score / Boolean schemas
  types.ts
tests/
  decision-policy.test.mjs # confidence normalization and policy boundaries
```

## Validation

Run `npm test`, `npm run typecheck`, and `npm run build` before deployment.

On September 18, 2026, a synthetic Support Triage LIVE request returned Choice, Score, and Boolean decisions from `typesafe-ai/jev`, including TypeSafe confidence metadata and a REVIEW policy. The server reported evaluation-call latency separately from total API time. Earlier billing and Hobby-plan ZDR rejections remained explicit errors without demo fallback; deterministic DEMO behavior and policy thresholds were tested separately.

## References

- TypeSafe AI: https://typesafe.ai
- Vercel announcement: https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway
- Jev on AI Gateway: https://vercel.com/ai-gateway/models/jev
- Vercel AI SDK: https://ai-sdk.dev

## License

MIT
