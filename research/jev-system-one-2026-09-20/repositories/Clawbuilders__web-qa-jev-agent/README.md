# web-qa-jev-agent

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/Clawbuilders/web-qa-jev-agent)

A Cloudflare Worker that crawls a web app like a QA tester, triages what it
finds with [`typesafe/jev`](https://developers.cloudflare.com/ai/models/typesafe/jev/)
(Cloudflare's decision model — fast, cheap, calibrated yes/no, multiple-choice,
and score judgments), confirms the real ones with a vision model, and files
deduped GitHub Issues. Built as a third bonus track for ClawBuilders Episode
5, alongside [`cloudflare-code-reviewer`](https://github.com/Clawbuilders/cloudflare-code-reviewer)
and [`clawbuilders-story-agent`](https://github.com/Clawbuilders/clawbuilders-story-agent).

It's the web equivalent of what [Google's ARTEMIS](https://github.com/google/artemis)
does for Android — natural-language-driven autonomous testing — except this
one runs entirely on Cloudflare and writes its findings straight to GitHub.

## How it works

```
Cron Trigger (daily) or GET /run?token=...
  → Explorer: Browser Rendering (headless Chromium) crawls up to MAX_PAGES
    same-origin pages from TARGET_URL, collecting console errors, failed
    network requests, page errors, and a text excerpt per page
  → Fast triage: one parallel typesafe/jev call per page — "is this a real
    bug?" (Noul), "how severe?" (Score), "what kind?" (Choice)
  → Escalation gate: only pages Jev flags above ESCALATION_FLOOR go further
  → Confirm + draft: a vision model (@cf/meta/llama-3.2-11b-vision-instruct)
    looks at that page's screenshot and writes up the finding
  → Dedup: another Jev call — does this match an already-open Issue, or is
    it new?
  → Write-back: new findings become a GitHub Issue (with the screenshot
    uploaded alongside); repeat findings get a comment on the existing Issue
```

### Why Jev *and* a vision model — not just one

[`typesafe/jev`](https://developers.cloudflare.com/ai/models/typesafe/jev/)
is **text-only** — its own docs are explicit that images, audio, and video
aren't supported. It can't tell you a layout is broken from a screenshot.
What it's genuinely good at: judging the *textual* substrate of testing —
console errors, HTTP status codes, page text — fast and at
$0.042 per **million** input tokens with free output, cheap enough to run on
every single page without a second thought.

So the split is deliberate: Jev does the cheap, high-frequency triage over
every page crawled; a vision-capable model only gets called for the small
fraction of pages Jev actually flags, to look at the screenshot and write
the human-readable report. Most of a crawl's cost stays near zero; only the
real findings cost real tokens.

### Redaction, same as the other two bots

Console errors, failed request URLs, and page text all pass through a
regex secret-scrubber (`src/redact.ts`) before reaching any model or any
public GitHub Issue — a misconfigured page printing its own API key into
an error message should never end up quoted in a public bug report.

## Repo layout

- `src/index.ts` — Worker entrypoint: `scheduled()` (daily cron) and
  `fetch()` (the `/run` manual-trigger route)
- `src/explorer.ts` — the Browser Rendering crawl
- `src/triage.ts` — the per-page Jev call
- `src/escalate.ts` — the vision-model confirm + write-up
- `src/github.ts` — list/dedup/comment/create against GitHub Issues, plus
  the screenshot upload
- `src/pipeline.ts` — wires the above into one run
- `src/redact.ts` — the secret-scrubbing pass
- `wrangler.json` — Worker config (AI + Browser Rendering bindings, cron)

## Setup

### 1. Deploy

Click the **Deploy to Cloudflare Workers** button above, or clone and run
`wrangler deploy` yourself (see "Local development" below).

### 2. Enable Browser Rendering

Browser Rendering isn't on by default — enable it for your account in the
Cloudflare dashboard (**Workers & Pages → Browser Rendering**) if you
haven't used it before. Free-tier limits matter here: **10 browser-minutes
a day, 3 concurrent sessions, 6 requests/minute** — plenty for the daily
cron with a small `MAX_PAGES`, tight if you mash the manual `/run` route
repeatedly while testing. `wrangler.json`'s `MAX_PAGES` defaults to `3` and
is hard-capped at `10` in code for exactly this reason.

### 3. Accept the vision model's license

The first time any Worker on your account calls
`@cf/meta/llama-3.2-11b-vision-instruct`, Cloudflare requires you to accept
Meta's license for it — do this once in the dashboard's Workers AI model
page before your first real run, or the escalation step will fail on every
flagged page.

### 4. Create a GitHub token, and point the Worker at your repos

Create a **fine-grained personal access token** scoped to the repo you want
Issues filed in, with:

- Repository permissions → **Issues: Read and write**
- Repository permissions → **Contents: Read and write** (for uploading
  screenshots into `qa-screenshots/`)

Then set it, the target site, and the report repo, all as secrets (kept out
of the committed config on purpose — same reasoning as the other two bots):

```bash
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put GITHUB_OWNER   # e.g. your GitHub org or username
npx wrangler secret put GITHUB_REPO    # the repo name, without the owner
npx wrangler secret put TARGET_URL     # the site to crawl, e.g. https://clawbuilders.club
```

### 5. Set the run-trigger secret

```bash
npx wrangler secret put RUN_TOKEN   # any random string
```

### 6. Deploy

```bash
npm install
npm run deploy
```

### 7. Verify

```bash
curl "https://web-qa-jev-agent.<your-subdomain>.workers.dev/run?token=<RUN_TOKEN>"
```

Returns a JSON summary (`pagesVisited`, `flagged`, `filed`, `duplicates`).
Check the target repo's Issues tab — anything filed carries the
`web-qa-jev-agent` label plus a screenshot committed under `qa-screenshots/`.

## Local development

```bash
cp .dev.vars.example .dev.vars   # fill in real values, never commit this file
npm install
npm run dev   # wrangler dev --remote — Browser Rendering does NOT work in local mode
```

`npm run typecheck` runs `tsc --noEmit`.

## Schedule

The cron in `wrangler.json` (`0 14 * * *`, UTC) runs once daily. Adjust it,
or lean on the `/run` route for on-demand checks — both call the exact same
pipeline.

## Limitations (read before treating this as a real QA tool)

- **Text-only triage, vision-only confirmation.** Jev never sees pixels;
  the vision model only sees a JPEG screenshot per flagged page, not a full
  interaction trace. Subtle visual bugs a real tester would catch by
  scrolling or resizing won't be found here.
- **The crawl is shallow on purpose.** It follows same-origin links from
  `TARGET_URL` breadth-first up to `MAX_PAGES`; it doesn't fill in forms,
  log in, or click buttons beyond following `<a href>` links. Extending it
  to take real actions (matching what ARTEMIS does for Android) is a
  natural v2, not attempted here.
- **The vision model's write-up is best-effort text parsing**, not a
  strict schema — it's asked for a title line + description and that
  split is done with simple string splitting, not JSON. Good enough for a
  bonus-track demo; validate this before relying on it for anything real.
- **Free-tier Browser Rendering caps the crawl volume.** See setup step 2.
