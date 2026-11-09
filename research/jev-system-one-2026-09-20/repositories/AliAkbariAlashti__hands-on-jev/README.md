# hands-on-jev

**A live playground for [Jev](https://docs.typesafe.ai), TypeSafe's "System One" model.**

A normal LLM call gets you back text that your app then has to parse. Jev skips that step: you send it `state` (the text or facts to evaluate) plus one or more `questions`, and it returns a **typed, probability-scored judgment** — not prose. This repo explains that model in plain language, then lets you run all three question types against the real API and watch the typed answers come back.

## Run it

```bash
npm install
cp .env.example .env   # then paste your TYPESAFE_API_KEY in
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`). The Express server on `:8787` handles `/api/run` and is the only thing that ever sees your API key — it never reaches the browser.

Get a key at [typesafe.ai](https://docs.typesafe.ai).

## What's here

- A short explainer on `state`, `questions`, and the three primitives.
- A gallery of 12 examples, four per primitive, spanning support, moderation, recruiting, e-commerce, guardrails, and more. Click any card to open it, edit the state or criteria, and run it against the live model.

| Primitive | Answer shape | Examples |
|---|---|---|
| **Choice** | selected label + probability per option | support routing, content tagging, chatbot intent, recipe cuisine |
| **Noul** | single yes/no probability | human escalation, spam/scam link, PII presence, LLM jailbreak attempt |
| **Score** | probability-weighted position on a rubric | bug severity, resume-to-role fit, review sentiment, essay argument strength |

Every open panel's state, instructions, and criteria are editable — change the text, add or remove options/levels, and re-run against the live model. Source data for all examples lives in [`src/examples.ts`](src/examples.ts).

See [`server/index.ts`](server/index.ts) for the generic `/api/run` route (built on `client.systemOne()` from `@typesafe-ai/sdk`) and [`src/main.ts`](src/main.ts) for the panel logic.

## Why this exists

A hands-on, minimal example of building with Jev — meant to be cloned, read end to end in a few minutes, and poked at. No framework ceremony, no unnecessary abstraction.
