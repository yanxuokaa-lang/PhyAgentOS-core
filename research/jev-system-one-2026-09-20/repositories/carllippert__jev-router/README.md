# jev-router

Express with no routes. [Jev](https://typesafe.ai) picks which handler runs.

There is no `GET /users/:id`. Clients hit the origin. Method, path, and body are evidence. You register **English + a named function**. Jev’s Choice key is `function.name` so the payload stays small.

```ts
import express from 'express'
import { JevRouter } from 'jevexpress'

const api = JevRouter()

function listUsers(_req, res) {
  res.json({ users: [] })
}

function createUser(req, res) {
  res.status(201).json({ user: req.body })
}

api.handle('List users. Collection read; no body required.', listUsers)
api.handle('Create a user from JSON with name and/or email.', createUser)

const app = express()
app.use(express.json())
app.get('/health', (_req, res) => res.json({ ok: true }))
app.use(api)
```

What Jev sees:

```json
{
  "listUsers": "List users. Collection read; no body required.",
  "createUser": "Create a user from JSON with name and/or email.",
  "none_of_the_above": "The request does not match any registered handler."
}
```

These can all run `listUsers`:

```bash
curl http://localhost:3000/users
curl http://localhost:3000/please-list-the-people
curl -X POST http://localhost:3000/ -H 'content-type: application/json' \
  -d '{"please":"list people"}'
```

`handle` takes two arguments only: the intent string, then the function. There is no id and no path. Inline arrows have no `.name` — use `function listUsers(...)`.

## Install

```bash
npm install jevexpress express
```

Node 20+. Jev is called through OpenRouter’s [Decisions API](https://openrouter.ai/typesafe/jev-1.13), not chat completions:

```bash
export OPENROUTER_API_KEY=sk-or-...
```

Default model is `typesafe/jev-1.13`. Pass `model: '~typesafe/jev-latest'` to track current Jev.

## How it works

1. `handle(intent, namedFn)` — no route table.
2. Every request except `GET /health` becomes `{ method, path, query, contentType, body }`.
3. One Choice over the function names + `none_of_the_above`. The sentences are the criteria.
4. `confidence < 0.65` or `none_of_the_above` → **404** with the probability dump.
5. Otherwise that function runs. Jev cannot invent a new handler.

Headers: `X-Jev-Handler` (the function name), `X-Jev-Confidence`, `X-Jev-Model`.

Put **auth in front** of `app.use(api)`.

## Options

```ts
JevRouter({
  minConfidence: 0.65,
  model: 'typesafe/jev-1.13',
  apiKey: process.env.OPENROUTER_API_KEY,
  skipPaths: ['/health'],
})
```

## Limits

- Choice is capped at **255** options (254 handlers + `none_of_the_above`).
- Typical Jev latency is ~70–500ms.
- URLs are not the interface.
- Body is truncated (~4k chars). Do not minify handler names away.

## Demo

```bash
export OPENROUTER_API_KEY=sk-or-...
npx tsx examples/demo.ts
```

## License

MIT — [github.com/carllippert/jev-router](https://github.com/carllippert/jev-router)
