# Jev Atlas

An independent, evidence-first field guide to [Jev](https://typesafe.ai), TypeSafe AI's System One model.

**Live: https://jev.gorock.sh**

> Not affiliated with or endorsed by TypeSafe AI. This is independent research.

## What you can do with it

- [`/map`](https://jev.gorock.sh/map) — 31 build blueprints, organized by which property of Jev each depends on
- [`/fit`](https://jev.gorock.sh/fit) — paste a workflow, get back its Choice, Score, and Noul decision points
- [`/claims`](https://jev.gorock.sh/claims) — every claim with an evidence status; a vendor claim stays a vendor claim, no matter how often it's repeated
- [`/projects`](https://jev.gorock.sh/projects) — 15 located builds

## Connect your coding agent

```json
{"mcpServers":{"jev-atlas":{"url":"https://jev.gorock.sh/mcp"}}}
```

Five tools: `search_jev_knowledge`, `get_jev_context_pack`, `assess_jev_fit`, `get_build_blueprint`, `trace_jev_claim`.

The MCP server is read-only. It never calls Jev, accepts a TypeSafe credential, fetches arbitrary URLs, or modifies files.

No MCP client? Use [`/llms.txt`](https://jev.gorock.sh/llms.txt), [`/llms-full.txt`](https://jev.gorock.sh/llms-full.txt), or `/api/v1/*.json`.

## Run it locally

```bash
npm install && npm run dev
```

Open http://localhost:3000. No API keys needed — the repo ships with the generated research artifacts, and the `/fit` checker falls back to a rules-based result without `AI_GATEWAY_API_KEY`.

## Refresh the research (optional, costs X API credits)

```bash
npm run research:dry   # print the query plan and max spend — zero paid calls
npm run collect -- --budget-usd 3 --max-posts 750 --max-requests 50
```

Every paid request is capped by three independent hard ceilings — spend, returned posts, and request attempts — each held to a 10% safety margin below what you configure.

## Data handling

Raw and processed posts, the seen-post index, run state, and `.env` are gitignored and never committed. The derived `data/processed/analysis.json` and `research/*.md` **are** committed, and contain only links, scores, categories, and themes — never post text, enforced by `test/security.test.ts`.

## Stack

Next.js 16, React 19, Tailwind 4, MCP SDK v2, Vercel AI Gateway.

## Docs

- [JEV_ATLAS_AGENT_PLAN.md](./JEV_ATLAS_AGENT_PLAN.md) — product thesis, knowledge model, and roadmap
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) — API strategy, pricing assumptions, and known limitations

## License

MIT
