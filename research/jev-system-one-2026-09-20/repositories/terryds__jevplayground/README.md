# Jev Playground

A browser-only testbed for [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), TypeSafe AI's decision model, running through the [Vercel AI Gateway](https://vercel.com/docs/ai-gateway/modalities/evaluation).

**Live: https://jevplayground.terrydjony.com**

Jev is not a chat model. You give it some *state* (a ticket, a transcript, a JSON record) and a set of typed *questions*; it answers all of them in one parallel pass with probabilities attached:

| Question type | You define | You get back |
|---|---|---|
| `boolean` | instructions, optional true/false criteria | `probability` |
| `choice` | named options with descriptions | `choice` + probability per option |
| `score` | ordered levels, lowest to highest | interpolated `score` + probability per level |

## What the playground does

- Paste your AI Gateway API key, pick a preset (work or fun), press **Evaluate**
- Build boolean / choice / score questions against plain-text or JSON state
- See verdicts, probability bars, latency, token usage, and estimated cost
- Set an auto-accept threshold to see which answers would need human review
- Inspect the raw request and response, or copy an AI SDK / curl snippet
- **Share** a result as an image, or as a link that reopens the same setup

## Your API key

There is no backend. The page calls `https://ai-gateway.vercel.sh/v4/ai/evaluation-model` directly from your browser. Your key is sent only there, is kept in memory unless you tick **Remember** (then it goes to `localStorage`), and is never included in shared images or links.

Get a key from the Vercel dashboard under **AI Gateway → API Keys**.

## Run locally

It is a single static file with no build step:

```bash
npx serve public        # or: python3 -m http.server -d public 5173
```

## Deploy

```bash
npx wrangler deploy     # Cloudflare Workers static assets, see wrangler.jsonc
```

## How it talks to the gateway

Vercel documents evaluation models as AI SDK 7+ only (`experimental_evaluate`). This page makes the same HTTP call the `@ai-sdk/gateway` provider makes:

```
POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model
Authorization: Bearer <key>
ai-gateway-protocol-version: 0.0.1
ai-gateway-auth-method: api-key
ai-model-id: typesafe-ai/jev

{ "state": ..., "questions": { ... } }
```

The SDK also sends an `ai-evaluation-model-specification-version` header. It is left out here because the gateway's CORS preflight does not allow it from browsers, and the endpoint works without it.
