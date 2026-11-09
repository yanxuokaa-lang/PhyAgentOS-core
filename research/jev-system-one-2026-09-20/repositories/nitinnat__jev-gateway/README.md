# Jev Gateway

A small local HTTP service for TypeSafe AI's Jev through [Vercel AI Gateway](https://vercel.com/docs/ai-gateway/modalities/evaluation). It uses AI SDK 7's `experimental_evaluate` and fixes the model to `typesafe-ai/jev`. Projects send a state and typed questions; the service returns Jev's answers and provider metadata. A TypeSafe API key is not used.

## Start

Create a [Vercel AI Gateway key](https://vercel.com/docs/ai-gateway/authentication-and-byok). Copy `.env.example` to `.env` and set `AI_GATEWAY_API_KEY`. Docker Compose reads this file automatically. `.env` is ignored by Git and excluded from the image.

```sh
docker compose up -d --build
curl http://127.0.0.1:8787/health
```

## Evaluate

```sh
curl -sS http://127.0.0.1:8787/v1/evaluate \
  -H 'content-type: application/json' \
  -d '{
    "state": {
      "query": "How are refresh tokens rotated?",
      "passage": "Each used refresh token is replaced with a new one."
    },
    "questions": {
      "relevant": {
        "type": "boolean",
        "instructions": "Does the passage help answer the query?"
      }
    }
  }'
```

`state` can be a string, object, or array. `questions` is a nonempty map of named `boolean`, `choice`, or `score` questions in [AI SDK evaluation format](https://vercel.com/docs/ai-gateway/modalities/evaluation). The response contains `answers` and, when supplied by Vercel, `providerMetadata`. The service makes one Jev call per HTTP request. Its errors return JSON with HTTP 400 for malformed input or 502 for an upstream failure.

Python projects can call the same endpoint with their usual HTTP client. Docker projects can join the gateway's network and use `http://jev-gateway:8787/v1/evaluate`:

```yaml
services:
  app:
    networks: [default, jev]

networks:
  jev:
    external: true
    name: jev-gateway
```

Keep the questions and decision thresholds in each calling project. The service deliberately does not decide what a probability means for your workflow. Its published port binds to `127.0.0.1`; it has no caller authentication, so do not expose it to the public internet.

## Development

```sh
docker run --rm -v "$PWD:/app" -w /app node:22-alpine sh -c 'npm ci && npm test'
```

See [Vercel's evaluation docs](https://vercel.com/docs/ai-gateway/modalities/evaluation) for the current question types and response contract. This project is not affiliated with TypeSafe AI or Vercel.
