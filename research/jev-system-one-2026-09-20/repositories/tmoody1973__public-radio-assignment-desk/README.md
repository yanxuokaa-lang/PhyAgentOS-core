# Public Radio Assignment Desk

A live editorial workbench for public-radio producers. Select a station, explore
NPR CDS stories, read reporting and transcripts, listen in a persistent player,
and ask TypeSafe Jev to recommend editorial next steps.

An independent, experimental **MIT-licensed** code demo—not an automated editor,
an NPR content license, or an endorsement by NPR or TypeSafe. See [LICENSE](LICENSE)
and [content rights and attribution](NOTICE.md). Bring your own authorized API keys.

The About this demo page (`/#about`) explains the decision model in plain English,
with practical workflows for assignment editors, reporters, producers, and digital
editors, plus limitations, experimental thresholds, and data handling.
The How to use page (`/#how-to`) walks through morning-meeting ranking, explains
the three equally weighted scores, and provides priority and search examples.
In Edit newsroom priorities, preview an example before explicitly applying it;
applying clears prior assessments and manual assignments without running inference.

## Run locally

Requires Node.js 24 or newer and pnpm.

```sh
git clone https://github.com/tmoody1973/public-radio-assignment-desk.git
cd public-radio-assignment-desk
pnpm install
cp .env.example .env.local
# Add your own authorized CDS and TypeSafe credentials to .env.local.
pnpm dev
```

Open http://localhost:5180. Put TYPESAFE_API_KEY and NPR_CDS_TOKEN in .env.local.
The CDS token may also come from the local file saved by npr-cds-mcp setup.
Do not prefix secrets with VITE_. The app uses the live Jev model only.

## Workflow

- Search for a station by name, call letters, city, or exact CDS ID.
- Choose My station, NPR, or up to four selected station IDs for the wire.
- Choose Today (midnight Eastern), the last 24 hours, past week, or past two weeks.
  Rolling windows use exact timestamps; results exclude future publications.
  Load up to 24, 48, or 96 newest available stories, not an exhaustive archive.
- Edit the general public-radio priorities for the selected station.
- Work the wire to assess stories with Jev; stop cancels pending browser work.
- Open a story to read its body/transcript, inspect the assessment, and override
  its editorial lane.
- Assessments include suggested topics, format fit, a next reporting action,
  local follow-up potential, practical listener-service value, and editorial review flags.
  Choose one newsroom task: morning meeting, local reporting, listener service,
  segment candidates, or check before using. Tasks organize and rank candidates;
  weak signals are labeled rather than silently discarded. Strict matching is
  optional. Topic, format, audio, date, and search boundaries still narrow results.
  Unassessed stories are distinct from assessed low-scoring candidates and never
  presented as confirmed matches. Selecting a task or topic assesses the loaded
  wire's unassessed stories; later changes reuse completed judgments.
  Same-source refresh preserves manual assignments
  for retained stories and assessments with unchanged title, teaser, and date.
- Search the loaded wire by meaning, then narrow by topic or audio availability.
  Jev reads available article/transcript text to rank each candidate. A result
  needs at least 2/4 relevance; this is a demo threshold, not validated accuracy.
  Failed and unsearched stories are never presented as irrelevant. Stop keeps
  completed results. Only an explicit search runs inference; typing does not.
- Play or queue audio. The persistent player continues across story and station
  changes, with seek, skip and playback-speed controls.

Only station selection and editorial priorities are saved in browser storage.
Story text and audio URLs stay in memory for the current session. Audio is streamed
from the original source, never downloaded or stored by this app. Content shows
source links, credits, and CDS rights notes; a station picker does not change
the rights associated with the configured CDS account.

## How it works

The build bundles npr-cds-mcp 0.8.4 into .mcp/server.cjs. A server-side MCP client
starts that server over STDIO for each request, invokes only allowlisted
read-only tools, and closes it. This uses the published server's story extraction
and station lookup behavior. No MCP write tools are exposed.

POST /api/cds supports stations, stories, and story actions. POST /api/judge
retrieves source reporting by CDS ID and submits a fixed 26-question rubric to
jev-latest. The browser cannot choose upstream URLs, model names, or question sets.

Rubric: public-service value, station relevance, timeliness, confirmed local
connection, evidence sufficiency, editorial lane, 12 topic checks, four review
flags, format, next step, local reporting potential, and listener-service value. Insufficient evidence is
routed to editor review. Model confidence is not a measured accuracy score.
Lane suggestions do not grant broadcast rights or confirm local impact.
The cost estimate uses the upstream demo's $0.042 per million input tokens;
it is an estimate, not a billing statement. Measured model latency excludes CDS
retrieval; end-to-end batch throughput includes retrieval.

POST /api/search retrieves each candidate by ID and uses three fixed Jev
questions: semantic relevance, direct subject match, and local follow-up
potential. The interface runs up to three requests concurrently and displays
search usage separately from assessment metrics. No vector database, embeddings,
or second model is used. Search covers only the loaded wire; it is not an NPR
archive index. Snippets are source excerpts, not model-generated explanations.
Suggested topics and review flags use a 0.65 model-probability threshold. Editors
should validate these thresholds against their own labeled examples before
relying on them operationally. No flag is a clearance to publish or broadcast.

## Deploy your own copy

Import this repository into your own Vercel project with Node.js 24. The included
configuration builds the frontend and bundles the MCP server for the API functions.

Set production secrets NPR_CDS_TOKEN and TYPESAFE_API_KEY. Also configure
UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, and RATE_LIMIT_SALT using
the [Redis setup guide](docs/redis-setup.md). **Production API requests fail closed
without shared usage protection.** Local development can use per-process limits.
Optionally set
NPR_CDS_HOME_STATION to the credential owner's station ID (default s921). Do not
change this credential owner in response to a visitor's station selection.

```sh
pnpm typecheck
pnpm test
pnpm build
```

Deploy only after confirming your own content permissions and environment settings.
Use a preview to test real Redis counters and live endpoints before sharing a
production URL. A build alone does not verify credentials or content access.

The public endpoints share minute/day request allowances, return HTTP 429 when
exhausted, and pause assessment/search batches on allowance or availability errors.
DEMO_API_ENABLED=false is a deploy-time kill switch. Request limits are not a
guaranteed spending cap; set provider and hosting alerts too.

The public endpoints are intended for this demonstration and incur provider
usage when visitors assess stories. OpenRouter and the old comparison proxy are
not used. No VITE_ENGINE setting is needed.

## Verification

```sh
node scripts/smoke-test.mjs http://localhost:5180
```

This checks input guards, exact station-ID lookup, live story retrieval, and
article/transcript access and publication windows. It does not run paid inference
unless --judge or --search is added. Parser and date-window tests:

```sh
pnpm test
```
These deterministic tests cover assessment parsing, search, date windows, task
ranking/filtering, and mocked usage protection. They do not call paid providers.
The server is a browser demonstration and does not publish content to CDS.

## Sharing and contributing

Use the [peer-pilot checklist and invitation draft](docs/peer-pilot.md) for a small
newsroom trial. The About page includes a copy-only feedback form. Set optional
public VITE_FEEDBACK_URL to a feedback form or mailto link if desired. Nothing is
sent automatically, and no shared editorial board or database is provided.

See [CONTRIBUTING](CONTRIBUTING.md) and [SECURITY](SECURITY.md). Credentials, local
deployment metadata, generated bundles, legacy scraped data, and publisher media
are excluded from version control. Each operator is responsible for their own
permissions to display, stream, and analyze content.

Based on the original [News Desk Dealer demo](https://github.com/elvisun/newsjack/tree/main/demos/news-desk-dealer).
CDS integration: [npr-cds-mcp](https://www.npmjs.com/package/npr-cds-mcp).
Not affiliated with or endorsed by NPR.
