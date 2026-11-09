# Jev playground

Public BYOK web playground for **TypeSafe Jev (System One)**.

GPT and Claude write. Jev decides. Threshold in code. Fail closed on thin confidence.

Visitors paste their own `TYPESAFE_API_KEY`. The playground does not ship a key, does not read a server-side `TYPESAFE_API_KEY` for visitor traffic, and does not persist keys on the server.

Article (placeholder, not live yet): `https://example.com/your-article-url`

## What it is

Jev is TypeSafe's System One model: unstructured state in, typed **Choice**, **Score**, or **Noul** out. It does not write prose or code.

This app is a set of operator work orders:

1. Coding agent tool-call gate (`allow` / `allow_with_confirm` / `deny` + Noul "changes production")
2. Coding agent model-tier (`fast` / `reasoning` / `human` + Score undo-difficulty)
3. PR / review gate
4. Salesforce / CRM case routing (Choice + Score + Noul SLA)
5. Slack triage (interrupt vs digest)
6. Publish vs hold on agent output
7. Recruiting screen (bounded; never auto-reject on low confidence)
8. Primitives playground (freeform state + mix Choice / Score / Noul)

Each run shows state in, question config, live answers with probabilities and confidence, a suggested code branch, and the request/response JSON.

## Get a key

Early access is real. A pasted key can still fail if you are on the waitlist or the key is not enabled.

1. Waitlist / site: https://typesafe.ai
2. Console / keys: https://console.typesafe.ai
3. Docs: https://docs.typesafe.ai

## Setup

Node 20+ (Node 22 used in CI-style local builds).

```bash
pnpm i
pnpm dev
```

npm works too:

```bash
npm i
npm run dev
```

Open http://localhost:3000. Paste a TypeSafe key in Settings. Default model is `jev-1.13.0` (toggle `jev-latest` when you want the moving alias).

```bash
pnpm build
```

No `.env` is required. `.env.example` exists only to say: do not put a visitor key there.

## BYOK security

- Key storage: `sessionStorage` by default. Optional "Remember on this device" uses `localStorage`. Wipe clears both.
- The browser sends the key as `Authorization: Bearer …` to `/api/systemone`.
- That Next.js route forwards the visitor-supplied header into `@typesafe-ai/sdk` (`TypeSafeClient.systemOne`). It does not log the key, does not persist it, and does not fall back to `process.env.TYPESAFE_API_KEY`. The SDK stays on the server so the browser bundle never constructs `TypeSafeClient`.
- Direct browser calls to `https://api.typesafe.ai` were probed at build time. CORS preflight did not return `Access-Control-Allow-Origin` for arbitrary origins, so the tiny proxy exists. If TypeSafe later opens CORS, the proxy can be removed.
- Never commit secrets. `.env*` is gitignored except `.env.example`.

## UI

Operator dispatch board, not a chat window.

- Top: key, persist/wipe, model pin.
- Left (horizontal chips on mobile): eight work orders.
- Center: paper "state in" ticket, primitive config, **Run gate**, decision slip (branch + probabilities + suggested TypeScript), request/response JSON.

Empty or invalid keys fail with a visible error. There is no silent success path.

## SDK

Official package: [`@typesafe-ai/sdk`](https://www.npmjs.com/package/@typesafe-ai/sdk) (not a bare `typesafe` package).

Verified client shape:

```ts
import { choice, noul, score, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient({
  apiKey, // visitor key from the request header
  defaultModel: "jev-1.13.0",
  logLevel: "off",
});

const response = await client.systemOne({
  state,
  model: "jev-1.13.0",
  questions: {
    category: choice("What is this ticket about?", {
      billing: "Payment issues",
      technical: "Bugs",
    }),
    urgent: noul("The message conveys urgency"),
    intensity: score("How blocked?", ["Low", "Medium", "High"]),
  },
});
```

## Known blockers

- **CORS:** TypeSafe HTTP API did not advertise an open `Access-Control-Allow-Origin` for this origin, so live calls go through `/api/systemone`.
- **Waitlist / early access:** many visitors will not have a working key. The UI says so and points at typesafe.ai / console.typesafe.ai.
- **SDK:** `@typesafe-ai/sdk@0.6.0` matches docs (`TypeSafeClient`, `systemOne`, `choice` / `score` / `noul`). Browser use requires `dangerouslyAllowBrowser`; this app keeps the SDK on the server instead.
- **No baked demo key:** without a visitor key, examples render and validate, but System One does not run.

## Deploy

Production is currently https://jev-playground-pbt1.netlify.app.

`netlify.toml` pins `@netlify/plugin-nextjs` and builds with `pnpm build` (publish `.next`). GitHub continuous deploy may need the repo linked in the Netlify UI if pushes to `main` are not building yet.

Do not set `TYPESAFE_API_KEY` in the host environment for visitor traffic.

Vercel also works with the App Router as-is.

## License

MIT. See `LICENSE`.
