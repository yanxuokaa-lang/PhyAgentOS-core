# postgres-Jev

Natural-language predicates for PostgreSQL using Jev through OpenRouter. The TypeScript/Tailwind dashboard is a playground for the same row judgments.

```sql
SELECT * FROM people p
WHERE jev(p, 'could explain a technical product to a beginner');
```

See [extension setup and SQL examples](extension/README.md). For fast searches, `jev_prepare()` batches the selected candidate rows before the `WHERE jev(...)` scan. A bare scalar call evaluates uncached rows individually; it does not silently scan unrelated table rows.

## Run the dashboard

```sh
npm install
cp .env.example .env
npm run dev
```

Set `OPENROUTER_API_KEY` in `.env`. Open http://localhost:4317. The model defaults to `~typesafe/jev-latest`. Keys stay server-side.

- With `DATABASE_URL` pointing to PostgreSQL with Jev installed, the demo sends candidate rows to `jev_evaluate()` in PostgreSQL and executes a real `WHERE jev(...)` query over those judgments. PostgreSQL calls OpenRouter.
- Without `DATABASE_URL`, the dashboard calls the same model from TypeScript. This keeps the hosted demo usable without a database.
- Without an OpenRouter key, only the limited offline example rules work, marked Demo.

The local demo database is optional. Docker is only one way to run PostgreSQL, not a frontend dependency.

Generated datasets include fictional people with contrasting experience and constraints, geographic descriptions, and sensor readings whose meaning depends on operating context. Example prompts demonstrate semantic judgments rather than simple keyword matching. The model remains probabilistic; SQL should handle exact conditions and arithmetic.

## Connect Supabase locally

Click **Connect Supabase** and supply only your project URL and API key. The local server discovers readable tables/views exposed in the project's **public Data API schema**, fetches their rows, and refreshes them on every search. Results show the source table and full record. The key must permit schema discovery and table reads; hidden schemas/tables cannot be discovered. Some projects require a privileged key for schema discovery; keys with elevated privileges can bypass RLS.

The demo loads up to 500 rows shared across discovered tables, with at most 100 tables and 500 KB of record data. It reports when table samples are capped; it does not claim to scan every row in a large database. Connections are read-only. Credentials stay in the local session memory until disconnect, restart, or expiry. Loaded records are sent to OpenRouter when searched. The public hosted demo does not accept database credentials; its connection button links to local setup.

A Supabase URL/key does not install SQL functions. To run `WHERE jev(...)` directly in your own database, follow the extension setup separately.

## Validation

```sh
npm test
npm run build
TEST_DATABASE_URL=postgresql://... npm run test:extension
```

Application code uses TypeScript/TSX and Tailwind. The extension uses SQL/PLpgSQL. JavaScript and HTML outputs are generated build artifacts. See [validation results](VALIDATION.md).

## Vercel

Deploy with `vercel --prod`. Set `OPENROUTER_API_KEY` as a sensitive production environment variable. Set `DATABASE_URL` only if a reachable database with Jev installed is available. Local environment files are excluded from uploads. Cache state is local to each application instance or PostgreSQL connection, respectively, and can reset when those restart.
