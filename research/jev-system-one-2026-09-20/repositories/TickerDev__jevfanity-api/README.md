# Jevfanity

A tiny profanity + moderation API powered by **Jev** and deployed on **Cloudflare Workers**.

One request to Jev evaluates multiple moderation categories in parallel and returns a probability for each one.

## Hosted version

A public instance is available at [api.jevfanity.app](https://api.jevfanity.app).

The hosted API is free for the time being. Please use it responsibly and do not abuse the service, evade rate limits, or send unnecessary automated traffic. Availability and free access are not guaranteed and may change as usage and operating costs evolve.

```bash
curl -X POST https://apijevfanity.app/v1/moderate \
  -H "Content-Type: application/json" \
  -d '{"text":"your message here","level":"medium"}'
```

## API

### `POST /v1/moderate`

```json
{
  "text": "your message here"
}
```

Optional:

```json
{
  "text": "your message here",
  "level": "medium",
  "threshold": 0.75,
  "categories": ["profanity", "slur", "harassment"]
}
```

Moderation levels:

- `low`: Allows isolated f-bombs, casual swearing, and mild insults; flags extreme or dangerous content.
- `medium`: PG-13-style moderation and the default level.
- `strict`: Child-oriented moderation that flags any profanity, slur, targeted abuse, threat, or age-inappropriate sexual language.

Supported categories:

- `profanity`
- `slur`
- `harassment`
- `threat`
- `sexual`

Example response:

```json
{
  "flagged": true,
  "score": 0.97,
  "level": "medium",
  "threshold": 0.75,
  "categories": {
    "profanity": 0.97,
    "slur": 0.03,
    "harassment": 0.12,
    "threat": 0.01,
    "sexual": 0.02
  },
  "flagged_categories": ["profanity"],
  "model": "jev-1.13.0",
  "usage": {
    "input_tokens": 320,
    "output_tokens": 40
  },
  "processing": {
    "estimated_tokens": 14,
    "chunks": 1,
    "max_tokens_per_chunk": 100,
    "unicode_confusable_tokens": 0
  }
}
```

`flagged` is true when at least one selected category violates the chosen level's policy with a score that meets or exceeds the confidence threshold.

## Setup

```bash
npm install
cp .dev.vars.example .dev.vars
```

Put your TypeSafe key in `.dev.vars`:

```env
TYPESAFE_API_KEY=...
```

Then:

```bash
npm run dev
```

## Deploy

Store the TypeSafe key as a Cloudflare Worker secret:

```bash
npx wrangler secret put TYPESAFE_API_KEY
```

Optional: protect the public Jevfanity endpoint with your own bearer token:

```bash
npx wrangler secret put JEVFANITY_API_KEY
```

Then deploy:

```bash
npm run deploy
```

If `JEVFANITY_API_KEY` is configured, clients must send:

```http
Authorization: Bearer YOUR_JEVFANITY_API_KEY
```

## Example

```bash
curl -X POST https://jevfanity.app/v1/moderate \
  -H "Content-Type: application/json" \
  -d '{"text":"this is fucking awful","level":"medium"}'
```

## Browser usage

```js
const result = await fetch("https://jevfanity.app/v1/moderate", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    text: message,
    level: "medium",
  }),
}).then((response) => response.json());

if (result.flagged) {
  console.log(result.flagged_categories);
}
```

## Why multiple questions?

Jev's Noul primitive returns the probability that a yes/no proposition is true. Jevfanity asks one focused question per moderation category rather than asking one broad question like "is this bad?"

That gives applications both:

```json
{
  "flagged": true
}
```

and the underlying category probabilities for custom policy decisions.

## Notes

- The default threshold is `0.75`.
- The default moderation level is `medium`.
- Override the deployment default with `DEFAULT_LEVEL` set to `low`, `medium`, or `strict`.
- Override the deployment default with `DEFAULT_THRESHOLD` in `wrangler.jsonc`.
- Clients can supply a request-specific threshold from `0` to `1`.
- The Worker limits input to 10,000 characters per request.
- Text is split into chunks of at most 100 whitespace-delimited tokens with a 10-token overlap. Category scores are the maximum score across all chunks.
- Unicode text is allowed. Tokens made from lookalike Unicode characters are also compared in normalized form so disguised profanity or slurs can be evaluated by meaning and context. Unicode characters alone never cause a flag.
- The API allows 20 moderation requests per minute for each client IP in each Cloudflare location. A limited request returns `429` with `Retry-After: 60`.
- IP-based rate limiting means users on the same shared network may share a limit bucket. Use an authenticated user or API-key identifier instead when the API gains per-user authentication.
- CORS is open by default. Tighten `Access-Control-Allow-Origin` before using a browser-facing production deployment with sensitive data.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, development, and pull request guidance.

## License

Jevfanity is available under the [MIT License](LICENSE).
