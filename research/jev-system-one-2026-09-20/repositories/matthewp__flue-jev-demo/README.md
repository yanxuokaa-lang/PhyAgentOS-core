# Flue + Jev through Cloudflare AI Gateway

A standalone Cloudflare-targeted Flue example. Application AI requests go through the Worker's `AI` binding and its default AI Gateway:

- Flue chat turns use `cloudflare/openai/gpt-4o-mini`.
- Typed routing uses TypeSafe Jev (`typesafe/jev`).
- There are no application API keys or account-ID environment variables.

This project uses the published npm packages `@flue/runtime@2.0.8` and `@flue/vite@2.0.8`; it is not part of the Flue monorepo.

## The agent

`useJevRouter()` turns a typed question map into a validated `route_with_jev` Flue tool. The agent can call Jev and receive structured choices, probabilities, and confidence without treating Jev as its chat model:

```ts
'use agent';

import { useModel } from '@flue/runtime';
import { type JevQuestion, useJevRouter } from '../flue-jev.ts';

const supportQuestions = {
  intent: {
    type: 'choice',
    instructions: 'Which support team should handle this request?',
    criteria: {
      billing: 'Charges, refunds, subscriptions, invoices, and payment methods',
      technical: 'Bugs, outages, errors, configuration, and integrations',
      human: 'Ambiguous, sensitive, abusive, or explicitly asks for a person',
    },
  },
  isUrgent: {
    type: 'noul',
    instructions: 'Does this request need immediate attention?',
    criteria: {
      true: 'The customer is blocked, losing money, or reporting an active outage',
      false: 'The request can safely follow the normal support queue',
    },
  },
} as const satisfies Record<string, JevQuestion>;

export function SupportAgent() {
  useModel('cloudflare/openai/gpt-4o-mini');
  useJevRouter(supportQuestions);

  return `
    Route incoming support requests.
    Call route_with_jev with the user's request as state.
    Report the selected team, urgency, confidence, and Jev model.
  `;
}
```

See the complete [`SupportAgent`](src/agents/support.ts) and [`useJevRouter()` implementation](src/flue-jev.ts).

## Install and run

```sh
cd flue-jev-demo
pnpm install
pnpm dev
```

That is all the application configuration required. Wrangler uses your normal Cloudflare login and provides `env.AI` from [`wrangler.jsonc`](wrangler.jsonc):

```jsonc
{
  "ai": {
    "binding": "AI"
  }
}
```

If this machine has never authenticated Wrangler, run `pnpm exec wrangler login` once. The selected Cloudflare account needs AI Gateway credits for the third-party models.

If Wrangler belongs to more than one account, add that account's non-secret `account_id` to `wrangler.jsonc` before starting Vite. The server starts at the URL Vite prints, normally `http://localhost:5173`.

## Try Jev directly

Run one authenticated Jev request and print the result with one command. This uses Wrangler's existing login, so it does not persist or require an API-token environment variable. When multiple accounts are available, the first run asks which account to use and saves the choice in the gitignored `.wrangler-account` file:

```sh
pnpm demo
```

Pass a different request as an argument:

```sh
pnpm demo -- "The app has been down for an hour and production is blocked."
```

The underlying route can also be called directly:

```sh
curl -sS http://localhost:5173/api/route \
  -H 'content-type: application/json' \
  -d '{"state":"I was charged twice for order A-123 and need the money back today."}'
```

Internally it runs:

```ts
await env.AI.run('typesafe/jev', { state, questions });
```

The response contains the typed intent, urgency, probabilities, confidence, Jev version, and usage.

## Run the complete Flue agent

Submit a message:

```sh
curl -X POST http://localhost:5173/agents/support/demo-1 \
  -H 'content-type: application/json' \
  -d '{"kind":"user","body":"I was charged twice for order A-123 and need the money back today."}'
```

Then stream the durable conversation:

```sh
curl -N http://localhost:5173/agents/support/demo-1
```

Flue automatically registers its Cloudflare binding provider because `vite.config.ts` selects only the `cloudflare` provider. The chat model and the `route_with_jev` tool both call `env.AI.run(...)` with the default gateway, so both appear in the AI Gateway logs.

## Verify

The tests mock the Worker binding and make no paid calls:

```sh
pnpm test
pnpm check:types
pnpm build
```

Credential-free health check while dev is running:

```sh
curl http://localhost:5173/api/health
```

Deploy with:

```sh
pnpm deploy
```

## Files

- `wrangler.jsonc` — Worker configuration, AI binding, and Flue Durable Object migration.
- `vite.config.ts` — Flue plus the official Cloudflare Vite plugin; only the `cloudflare` provider is bundled.
- `src/flue-jev.ts` — typed `env.AI.run('typesafe/jev', ...)` client, Flue tool factory, and `useJevRouter()` hook.
- `src/agents/support.ts` — support-routing agent using `cloudflare/openai/gpt-4o-mini`.
- `src/app.ts` — explicit Hono route map.

## References

- [Cloudflare Jev model](https://developers.cloudflare.com/ai/models/typesafe/jev/)
- [AI Gateway Workers binding](https://developers.cloudflare.com/ai-gateway/usage/worker-binding-methods/)
- [Flue Cloudflare models](https://flueframework.com/docs/guide/models/#cloudflare-workers-ai-cloudflare-only)
