# The Jev Oracle

A browser-based Magic 8 Ball that sends each question to TypeSafe Jev as one closed `Choice` question over the twenty classic responses. The Next.js API route keeps the TypeSafe key on the server and returns the highest-probability response to the animated ball UI.

## Run locally

Requirements: Node.js 20 or newer and a TypeSafe API key.

```bash
pnpm install
cp .env.example .env.local
```

Put your key in `.env.local`:

```dotenv
TYPESAFE_API_KEY=your_real_key
```

Then run:

```bash
pnpm dev
```

Open [http://localhost:3002](http://localhost:3002). This project uses port 3002
locally because port 3000 may already be reserved by an SSH tunnel.

## Checks

```bash
pnpm test
pnpm lint
pnpm build
```

## Deploy to Vercel

Import this Git repository into Vercel and add `TYPESAFE_API_KEY` as an environment variable for Production, Preview, and Development. No other Vercel-specific configuration is required.

The API key is only read in `app/api/ask/route.ts`; it is never exposed to browser code.

## TypeSafe design

- State is a named object containing the user's question and the playful oracle setting.
- One `Choice` question contains all twenty classic outcomes.
- Each criterion describes when its phrase is the best semantic fit.
- Application code takes the maximum value from Jev's returned probability distribution and maps the stable choice id to the classic display text.
- This low-stakes experience always reveals the top choice; it displays probability as “signal strength” instead of treating it as factual certainty.

References: [TypeSafe JavaScript SDK](https://docs.typesafe.ai/sdk/javascript) and [Choice primitive](https://docs.typesafe.ai/primitives/choice).
