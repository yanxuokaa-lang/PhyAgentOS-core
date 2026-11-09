# WikiRace — AI Showdown

A live, screen-recording-ready Wikipedia race between GPT-5.6 Sol and Jev.

Both racers:

- begin at the same canonical Wikipedia article;
- may only choose links present on their current page;
- receive the same maximum candidate-set size and selection criteria;
- start concurrently with no artificial delay;
- expose wall-clock time, model-call time, hops, calls, and the route.

## Run locally

```bash
cd /Users/ainz/projects/wikirace
npm install
cp .env.example .env
# Add OPENAI_API_KEY to .env.
# TYPESAFE_API_KEY is optional here if it already exists in ~/.config/jev-browser/.env.
npm run dev
```

Open <http://127.0.0.1:4173>.

## Configuration

- `OPENAI_API_KEY` — required for GPT-5.6 Sol.
- `TYPESAFE_API_KEY` — required for Jev. The server also checks the existing jev-browser config at `~/.config/jev-browser/.env`.
- `PORT` — defaults to `4173`.

Public-demo guardrails (races run on the host's API keys):

- `MAX_RACES_PER_IP_PER_HOUR` — defaults to `3`.
- `MAX_RACES_PER_DAY` — defaults to `100`.
- `MAX_CONCURRENT_RACES` — defaults to `2`.
- `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` — optional. Set both to keep
  per-IP and daily counts across restarts. Unset, the limits live in memory and
  reset with the process, which is fine locally but not on a host that sleeps.

Secrets remain on the server and are never sent to the browser.

## Tests

```bash
npm test
```

## Scoring optimality

`bench/shortest.mjs` finds the shortest path **in the graph the racers see** —
live rendered HTML, main namespace, first 255 links per page:

```bash
node --env-file=.env bench/shortest.mjs "Coffee" "Artificial intelligence"
node --env-file=.env bench/shortest.mjs --score bench/results-gpt-none.json
```

This is not Six Degrees of Wikipedia. That tool runs BFS over a full SQL dump
counting every link including navboxes, at a past snapshot. The two graphs
differ enough to matter: on `Coffee -> Bennett` the dump's 5-hop optimum uses
five edges, and not one of them exists in the rendered pages the racers read.

## Race format

Wikipedia article links are read from the rendered article HTML in the order the page displays them, filtered to main-namespace articles, and capped at 255 candidates per hop (Jev's per-question ceiling, applied equally to both racers). Each model makes exactly one judgment per hop over the identical candidate list. Batching the candidates would multiply a per-call latency difference into a wall-clock difference created by the harness rather than the models. A direct link to the target is followed without a model call.
