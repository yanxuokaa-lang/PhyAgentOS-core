# 🏁 Classifier Wiki Race

Watch **[Jev](https://typesafe.ai)** — TypeSafe's ultrafast System One classifier — race across
Wikipedia from one article to another, **with no LLM in the loop**. Every step shows the state
that's passed, the questions (speculative fan-out), the probabilities, and the action taken — in
real time, timed in milliseconds.

Built by [David Harvey (@dave_xt)](https://x.com/dave_xt).

## How it works

1. You paste your own **TypeSafe (Jev) API key**.
2. Pick a **start** and **destination** article (or hit **🎲 Random**).
3. On each hop the app:
   - fetches the current Wikipedia article **directly from your browser** (the MediaWiki API is
     CORS-enabled),
   - extracts the body links as a structured action space,
   - asks Jev two Choice questions — _which operation?_ and _which link?_ — in a single request,
   - clicks the winning link and repeats until it lands on the destination.

The classifier is the **only** decision-maker. There is no language-model agent loop.

## Your API key is never stored

TypeSafe does not send CORS headers, so the browser can't call it directly. Instead the request
goes through a **stateless [Hono](https://hono.dev) Cloudflare Worker** (`server/index.js`) that
forwards your one request straight to TypeSafe and streams the answer back. It is **never stored,
logged, cached, or persisted** — the key only exists for the lifetime of that single fetch. The key
also never leaves memory in the browser (it isn't written to `localStorage`).

## Develop

```bash
npm install
npm run dev          # Vite dev server; /api/systemone is proxied to TypeSafe
```

## Deploy to Cloudflare

```bash
npm run deploy       # vite build + wrangler deploy (Worker + static assets)
```

The Worker serves the built React app from `./dist` and handles `POST /api/systemone`.

## Powered by classifiers — like Bloobability

This race is the same idea behind **Bloobability**, [Blooio](https://blooio.com)'s calibrated gauge
that scores how likely a policy applies to a conversation. Try the
**[Bloobability playground](https://blooio.com/inference/bloobability/playground)**.

> Need to send messages at scale? **[Blooio](https://blooio.com)** — one HTTP API for iMessage, SMS,
> RCS & WhatsApp.

## License

MIT © David Harvey
