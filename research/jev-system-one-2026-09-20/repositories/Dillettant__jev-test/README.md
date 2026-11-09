# Jev Playground

A small Next.js demo of [TypeSafe](https://docs.typesafe.ai/introduction/quickstart)'s **Jev** System One model.
Enter some text (the *state*) and a set of typed questions — `noul` (yes/no probability),
`choice` (one of a set, with its distribution), `score` (position on ordered levels) — and see
Jev's typed answers visualized, plus the raw request/response.

## Run

```bash
export JEV_TEST_KEY=...   # your TypeSafe API key (TYPESAFE_API_KEY also works)
npm install
npm run dev               # http://localhost:3000
```

## How it's wired

- `src/app/api/systemone/route.ts` — server route that calls `client.systemOne(...)` with
  `@typesafe-ai/sdk`. The API key stays on the server.
- `src/lib/typesafe.ts` — server-only client, reads `JEV_TEST_KEY`.
- `src/lib/presets.ts` — the three demo scenarios (support triage from the quickstart,
  product review, inbox assistant) and the editor → API question conversion.
- `src/components/` — question editor, answer visualizations, playground page.
