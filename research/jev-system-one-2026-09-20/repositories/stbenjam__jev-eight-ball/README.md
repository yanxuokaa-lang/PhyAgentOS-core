# Jev Eight Ball

Ask a yes/no question. TypeSafe Jev chooses one of the 20 classic eight-ball answers, and its answer emerges from dark blue liquid in a triangular layout. No random fallback or generated prose. This is a toy for fun, not a prediction system.

## Run

Requires Node.js 22 or newer. No runtime dependencies or install step.

```sh
cp .env.example .env
# Set OPENROUTER_API_KEY in .env, or connect one in the page settings.
npm start
```

Open http://localhost:3002. The app serves only on loopback. API keys remain on the server; `.env` is excluded from Git. The latest 30 questions and answers stay in server memory and disappear on restart. Your question is sent to OpenRouter/TypeSafe to choose an answer. Each submission makes one billable API request; simply opening the page makes no model calls.

## How it works

`jev.mjs` calls OpenRouter's native `POST https://openrouter.ai/api/alpha/decisions` endpoint with model `~typesafe/jev-latest`. The user's question is data, and the 20 answers are the allowed typed choices. The response must select one of those choices; invalid responses and provider failures display an error without substituting an answer. The UI reports answer-choice confidence, actual request latency, and the returned model. Model confidence, where shown, is confidence in the answer choice, not a probability that a future event will happen.

The model alias can change versions; the alpha Decisions API may change. The actual returned model identifier is retained in history. This app does not generate free-form advice.

## Local API

- `GET /api/state`: key configuration status, busy status, and recent history. Never returns the key.
- `POST /api/ask`: `{ "question": "Should I order pizza?" }`.
- `POST /api/history/clear`: `{}` clears server-side question and answer history.
- `POST /api/settings`: `{ "apiKey": "..." }` replaces the in-memory key.

POST bodies require `Content-Type: application/json`. Only one model request can run at a time.

```sh
npm test
```
