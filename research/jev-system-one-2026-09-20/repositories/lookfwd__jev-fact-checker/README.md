# tweet-factcheck

Fact-check a tweet with **TypeSafe / Jev** (a System One model). Jev doesn't
browse or "know" facts — it returns **typed, calibrated judgments** about text
you give it. So this app follows the standard fact-checking pipeline and lets
code and Jev each do what they're good at:

```
tweet
  │  split into sentences                         (code)
  ▼
sentences ──►  "is this a check-worthy claim?"    (Jev · Noul)
  │  keep the claims
  ▼
claim  ──►  search Wikipedia for evidence         (code — Jev can't browse)
  │
  ▼
(claim, passage) ──► "supports / contradicts /     (Jev · Choice,
                       says nothing?" + confidence   citation-check pattern)
  │  aggregate stances × confidence
  ▼
verdict:  likely true · likely false · disputed · not enough evidence   (code)
```

**Grounded by design.** Every verdict reflects *only the evidence retrieved*
(Wikipedia by default), shown with Jev's confidence and clickable sources —
never a bare "TRUE." `not enough evidence` is a normal outcome. Jev judges the
*claim-vs-evidence relationship*, not truth in the abstract.

## Setup

```bash
npm install
cp .env.example .env      # then put your Jev key in TYPESAFE_API_KEY
```

## Use

```bash
# No key needed — stubs Jev with local heuristics, still hits Wikipedia:
npm run dry -- --sample

# Live (needs TYPESAFE_API_KEY in .env):
npm run factcheck -- --sample
npm run factcheck -- "The Eiffel Tower is in Berlin. Water boils at 100C at sea level."
echo "Mount Everest is the tallest mountain on Earth." | npm run factcheck --

# Options: --threshold <0..1>  --max-claims <n>  --limit <passages>  --json
npm run factcheck -- --help

# JSON out: use -s so npm's banner doesn't pollute stdout:
npm run -s factcheck -- --sample --json
```

The `--dry-run` stub only does word overlap, so it is deliberately dumb (it will
call "Eiffel Tower in Berlin" *supported*). That contrast is the point: the live
model reads the evidence and should mark it **likely false**.

## Web UI

A minimal browser UI over the same pipeline. The key stays server-side; the
server binds to localhost only and streams progress + the report as NDJSON.

```bash
npm run serve            # live Jev, http://127.0.0.1:3000
npm run serve:dry        # stubbed Jev (no key), same UI
```

Open http://localhost:3000, paste a tweet (or "Load sample"), and check.
Files: `src/server.ts` (zero-dependency `node:http`) + `public/` (static page).

## Layout

| File | Role |
| --- | --- |
| `src/jev.ts` | Jev question definitions + engine (`LiveJev` via SDK, `StubJev` for dry-run) |
| `src/wikipedia.ts` | Evidence retrieval (Wikipedia Action API, no key) |
| `src/pipeline.ts` | Sentence split → claim detection → stance → verdict aggregation |
| `src/render.ts` | Terminal report |
| `src/cli.ts` | Arg parsing / entry point |
| `src/types.ts` | Shared types |
| `src/server.ts` | Web UI server (zero-dep `node:http`, localhost, streams NDJSON) |
| `public/` | Web UI page (`index.html`, `styles.css`, `app.js`) |

## Cost

Jev bills input tokens only (~$0.042 / million; output free). A tweet is a
handful of calls and a fraction of a cent — the report prints exact token usage.

## Known limits & next steps

- **Intro-only recall.** Evidence is the Wikipedia *intro* extract, so a claim
  whose refutation lives deeper in an article comes back `not enough evidence`
  rather than `likely false` (e.g. "Great Wall visible from the Moon" — the
  "Artificial structures visible from space" article debunks it, but not in its
  intro). Fetch full article bodies and/or rank passages to fix recall.
- **Broader evidence** — add a web search API (Tavily/Serper) alongside Wikipedia
  for breaking-news claims; `retrieveEvidence` is the single seam to extend.
- **Tweet URLs** — fetch tweet text from a URL (needs the X API or a scraper).
