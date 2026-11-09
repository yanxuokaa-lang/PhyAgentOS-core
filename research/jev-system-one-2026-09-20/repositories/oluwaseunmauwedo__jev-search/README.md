# Jev Search

[![Jev Search homepage](public/og-home.png)](https://jev.s1.dev)

Search the web in plain language. [TypeSafe's Jev](https://typesafe.ai) chooses sources, time ranges and search terms, then ranks the results returned through [Search1API](https://www.search1api.com). You get links and snippets, with visible relevance scores and editable filters. No generated answers.

**[Try Jev Search](https://jev.s1.dev)**

Built by Search1API. This is an independent project, not an official TypeSafe product.

## How it works

1. **Understand.** Jev answers typed questions about your request. The application uses those judgments to choose a query, sources and a time range. You can override the source and time chips.
2. **Search.** Google, DuckDuckGo and Yandex search the open web. Hacker News, Reddit and GitHub each combine a Google site-restricted search with their dedicated engine (Hacker News uses the news endpoint). X, arXiv, YouTube, Wikipedia, IMDb and WeChat use vertical engines. Calls run concurrently; one failed engine does not discard another engine's results.
3. **Rank.** Jev scores each result for relevance. Results are merged by URL, ordered by relevance, engine agreement and original rank, and streamed as each lane finishes. Lower-scoring results are grouped separately. A failed source shows a warning rather than a zero-result count.

Try “TypeSafe Jev API documentation and examples”, “Jev discussions on Hacker News this week”, or “Videos about TypeSafe Jev this month”. These are plain-language requests, not hardcoded filters. Model choices and provider coverage can vary.

The application streams newline-delimited JSON from `POST /api/ask`: `intent`, `found` (progress counts), `lane` (ranked results), and `done`. Each engine has a 15-second deadline within an overall 30-second request deadline. Google may start speculatively while Jev interprets the question. Successful, non-empty engine responses are cached for 10 minutes to 6 hours, depending on the time window.

## Local development

Requires Node.js 22.12+ and pnpm 10.8.0. Obtain API keys from [Search1API](https://www.search1api.com) and [TypeSafe](https://typesafe.ai).

```bash
git clone https://github.com/superagents-lab/jev-search.git
cd jev-search
corepack enable
pnpm install --frozen-lockfile
cp .dev.vars.example .dev.vars
# Set SEARCH1API_API_KEY and TYPESAFE_API_KEY in .dev.vars.
pnpm dev
```

Open http://localhost:3030. Local development uses local Cloudflare bindings. Keep `.dev.vars` private; it is ignored by Git. `.env.example` is provided as a variable reference, but `.dev.vars` is the documented local configuration.

```bash
pnpm generate-routes
pnpm cf-typegen
pnpm test
pnpm build
pnpm exec wrangler deploy --dry-run
```

Tests mock providers and do not need API keys. Building does not call either provider. `worker-configuration.d.ts` is generated from Wrangler configuration; regenerate it after changing bindings.

## Deploy to Cloudflare Workers

The application uses TanStack Start, React and the Cloudflare Vite plugin. You need a Cloudflare account with Workers and KV enabled.

1. Run `pnpm exec wrangler login`.
2. In `wrangler.jsonc`, choose a Worker `name`. Remove `routes` to use a `workers.dev` URL, or replace `jev.s1.dev` with a domain in your Cloudflare account. Update the absolute social-card URLs in `src/routes/__root.tsx` and `src/routes/index.tsx` to match your deployment. Remove or replace the Cloudflare Web Analytics snippet in `src/routes/__root.tsx`; the committed token belongs to the hosted demo.
3. Run `pnpm exec wrangler kv namespace create jev-search-cache` and replace the `CACHE` namespace ID with the returned ID. The committed ID belongs to the hosted demo; it is not a credential.
4. Choose a unique rate-limit `namespace_id` in your account. The default limit is 30 searches per IP per minute per Cloudflare location; it is not a global spending cap. `CACHE` and `SEARCH_RATE_LIMIT` are optional; regenerate types after changing bindings.
5. Upload your own provider keys and deploy:

```bash
pnpm exec wrangler secret put SEARCH1API_API_KEY
pnpm exec wrangler secret put TYPESAFE_API_KEY
pnpm cf-typegen
pnpm test
pnpm run deploy:dry-run
pnpm run deploy
```

Wrangler can create the Worker when uploading its first secret. Provider keys stay in Cloudflare secrets and are never included in the browser bundle. Each search can make several billable provider calls. Configure provider spending limits for a public deployment; the same-origin check is a browser boundary, not authentication.

GitHub Actions validates pull requests and pushes with tests, type generation and a production build. The hosted demo deploys through Cloudflare Workers Builds when changes are pushed to `main`.

For Cloudflare's Git integration, use these settings:

| Setting | Value |
| --- | --- |
| Root directory | Repository root (`/`) |
| Production branch | `main` |
| Build command | `pnpm run build` |
| Deploy command | `pnpm exec wrangler deploy` |
| Node.js version | 22.12+ |

Cloudflare installs dependencies from `pnpm-lock.yaml`. The build creates the Worker and static assets and writes the Wrangler deployment configuration. Keep the existing provider keys in the Worker's runtime secrets; builds do not need them. For manual self-hosting, `pnpm run deploy` combines the build and deploy steps.

## Data and limitations

- Search requests go to TypeSafe and Search1API. TypeSafe also receives result titles and snippets for relevance scoring. Search1API queries the selected engines.
- Cloudflare KV stores query-derived cache keys and result snippets for the configured TTL. Removing `CACHE` disables this cache.
- The application does not record search text, inferred queries or result clicks in its own analytics.
- The hosted demo loads a [Cloudflare Web Analytics](https://developers.cloudflare.com/web-analytics/) beacon for page views, visits, referrers, country, browser and page-load metrics. It does not use cookies and does not record URL query strings, so search terms in `/search?q=` are not stored there. Self-hosters can remove the snippet in `src/routes/__root.tsx`.
- The rate limiter uses the client IP. Cloudflare Workers request logging is enabled separately in the configuration; invocation logs include request URLs, which may contain the search query.
- The page loads a font from Google Fonts. Result links lead to third-party sites.
- Relevance percentages are model judgments, not verified accuracy. Search snippets may be incorrect, incomplete or stale. Date filtering and Newest sorting prefer Search1API's `published_date`, falling back to snippet dates when unavailable. Day-only dates are displayed as calendar dates and filtered with allowance for the unknown time of day; unknown dates can remain. Selecting and ranking existing results does not verify their claims.

## Project layout

| Path | Responsibility |
| --- | --- |
| `src/lib/sources.ts` | Sources, engine mappings and time windows |
| `src/lib/candidates.ts` | Search-query candidates |
| `src/lib/typesafe.ts` | Typed intent and relevance judgments |
| `src/lib/search1api.ts` | Search provider client and engine deadlines |
| `src/lib/pipeline.ts` | Concurrent search and ranking stream |
| `src/lib/cache.ts` | Per-engine response cache |
| `src/lib/rank.ts`, `merge.ts` | Ordering, grouping and URL deduplication |
| `src/lib/use-ask.ts` | Client stream consumer |
| `src/routes/api/ask.ts` | Search endpoint, origin validation and rate limiting |
| `src/server/` | Cloudflare bindings |
| `test/` | Provider-independent regression tests |

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License and attribution

Application code is [MIT licensed](LICENSE). TypeSafe and Jev names and brand assets belong to their respective owners and are not included in this project's MIT license.

The favicon and Apple Touch Icon come from the icon links on [typesafe.ai](https://typesafe.ai/): [favicon](https://framerusercontent.com/images/aNFzSFxM4fjICmnibw7npfZjcQ.png) and [Apple Touch Icon](https://framerusercontent.com/images/kcuF2BEp5XaVfkmFB634IPRKQH0.png). Most source icons use [Simple Icons](https://simpleicons.org). Google uses the four-colour G; Yandex uses the official 2021 mark (white Я in a red circle). Interface icons use [Lucide](https://lucide.dev). For your own branding, replace the icons in `public/` and update `src/components/wordmark.tsx` and the page metadata.
