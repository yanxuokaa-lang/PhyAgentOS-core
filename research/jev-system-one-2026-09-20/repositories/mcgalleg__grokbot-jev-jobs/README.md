# grokbot-jev-jobs

Scores public job postings against a resume using
[TypeSafe AI's Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
through the [Vercel AI Gateway](https://vercel.com/docs/ai-gateway/modalities/evaluation),
then applies through a dashboard **Apply** button that webhooks
**Grok Bot (Resume Rudy)** to fill ATS forms and write status back.

Jev is an evaluation model, not a text model. You give it a state and a set of
typed questions; it returns choices, scores and boolean probabilities with
calibrated confidence, in roughly half a second, for $0.042 per million input
tokens with output tokens free. That makes it cheap enough to read every
plausible posting every day.

This repo is **public** (`mcgalleg/grokbot-jev-jobs`, renamed from `jev-job-search`):
anything personal lives in the git-ignored `profile/` and in Vercel env vars,
never in code.
The Vercel project is `grokbot-jev-jobs`. Production hosts:

- [https://jev-job-search.vercel.app](https://jev-job-search.vercel.app) — legacy primary
- [https://grokbot-jev-jobs.vercel.app](https://grokbot-jev-jobs.vercel.app) — alias

Local checkout on Mike’s machine: `/home/mike/Projects/grokbot-jev-jobs`.

## Architecture

```
Public feed ──► ingest ──► jev triage ──► ATS describe ──► jev score ──► Neon
                                                                    │
Dashboard Apply ──► apply_attempts + applies ──► POST Rudy webhook ─┘
                         ▲
                         ├── GET/POST /api/webhooks/rudy-apply (secret-gated status + write-back)
                         └── POST /api/rudy/page-brain         (secret-gated Jev calls mid-apply)
```

Two Jev uses, do not mix them up:

1. **This app** — title triage and full-text scoring via the AI Gateway.
2. **Rudy (production apply)** — a sparse page-brain that scans for knock-outs
   *before* a heavy ATS fill. It is not there to make fill faster. Rudy calls
   it on the deployment, so it always runs the code released from `master`.

## The funnel

Each stage is cheaper than the one after it, so expensive work only touches
postings that survived the cheap work.

| Stage | What runs | Input | Typical survival |
|---|---|---|---|
| 0. Ingest | deterministic code | ~1.46M postings from the feed | 5.6% |
| 1. Triage | jev, title only | title, company, location | 10.3% |
| 2. Describe | ATS APIs | survivors only | 65% (rest expired or unsupported) |
| 3. Score | jev, full text | resume + targets + description | all; pre-sales auto-ignored |

**Stage 0** applies only hard facts: location, and the recruiter flag. Anything
that is a judgement call is left to jev, because a title regex misses "Member of
Technical Staff, Customer Engineering" and catches "Product Manager, Payroll".

Seniority is deliberately *not* screened here. The feed's `skill_level` tag is a
keyword guess, and on a 250-posting sample of rows it rejected, jev kept none —
but it was throwing away ~7,100 postings feed-wide on a judgement it is not
qualified to make. `pnpm ingest --drop-junior-levels` opts back in.

**Stage 1** judges titles against the summary and only two sections of
`targets.md` — "Roles I want" and "What makes a role a weak match" — because a
title says nothing about pay or location policy. On 600 postings that cut tokens
41% and agreed with the full-profile call 96.5% of the time. Rename either
heading and triage falls back to sending the whole file.

**Stage 3** asks fourteen atomic questions and combines them in code
(`lib/jev/score.ts`), rather than asking one vague "is this a good fit". The
weights stay inspectable and tunable without re-prompting. Three results are
rules rather than weights:

- **Pay** is the exception to asking Jev. `lib/salary.ts` finds stated ranges in
  code, over the full description, Jev only picks which one is this role's pay,
  and code compares it with the floor in `targets.md`.
- **Pre-sales** roles are auto-ignored. Jev answers where in the customer
  lifecycle the role works; when its top choice is pre-sales, scoring writes the
  dashboard's own Ignore label, so a wrong call is one click to undo.
  `pnpm purge:presales` is the backfill for rows scored before this existed.
- **Hard blockers** are four separate questions — clearance, a specific degree,
  relocation, non-US work authorization — and the worst one scales the score down.

## Data source

Job data comes from
[Feashliaa/job-board-aggregator](https://github.com/Feashliaa/job-board-aggregator),
which publishes ~1M postings daily as gzipped chunks on GitHub Pages. **We read
it as a feed; we never run their scraper.** Their data repo is force-pushed on
every run with no history, so this project's database is the only durable
record of what has been seen and scored.

The feed carries no job descriptions. Those are fetched from the applicant
tracking system for postings that survive triage.

| Platform | Strategy | Requests | Concurrency |
|---|---|---|---|
| Greenhouse | whole board, cached per company | 1 per company | 8 |
| Lever | whole board, cached per company | 1 per company | 8 |
| Ashby | whole board, cached per company | 1 per company | 4 |
| Workday | per posting; no board endpoint carries text | 1 per posting | 3 |
| BambooHR, iCIMS, Paylocity | not wired up | — | — |

Postings on a platform with no fetcher are moved to an `unsupported` stage rather
than left pending, so they are not re-read every night. They are terminal until
someone writes the fetcher: currently 315 of them, Paylocity and BambooHR.

Two platform quirks are handled rather than papered over. Greenhouse customers
who white-label the board onto their own domain drop the board token from the
URL and keep the id in `?gh_jid=`; the feed's company field supplies the token.
Workday answers **403** both when it is throttling and when a requisition has
been withdrawn, so a 403 is retried and only then classified as expired.

Postings vanish constantly. The feed keeps jobs for 30 days, so roughly a third
of fetches find the posting already pulled. That is counted as `expired`, not as
an error — and so is a 404 on a *board* endpoint, which means the company's board
is gone or its slug never matched. Both are dead ends, not faults, and counting
them as errors would bury the real ones in the nightly summary.

## Apply → Rudy → write-back

There is no manual Applied toggle. **Apply** on the dashboard starts an
automated application; only Rudy’s secret-gated callback may mark a posting
Applied.

```
unset ──Apply──► applying ──callback──► applied | failed | blocked | skipped
                   ▲                         │
                   └──────── retry ──────────┘
```

1. The UI **Apply** click creates an apply attempt (`applying`) and POSTs a
   webhook to Rudy with the job URL, ATS, universal CV/cover *paths*, and a
   `callbackUrl`.
2. Rudy fills the ATS (Ashby, Greenhouse, Workday, Lever, and similar) and, in
   production, **submits for real**.
3. Rudy POSTs `POST /api/webhooks/rudy-apply`. That route is gated by
   `RUDY_CALLBACK_SECRET` (`Authorization: Bearer` or `x-rudy-secret`) and sets
   `applied` | `failed` | `blocked` | `skipped`. A later `applied` for the same
   `attemptId`+`jobUrl` overwrites `blocked` / `failed` / `skipped` (truth
   wins — e.g. a confirmation email after a race). Those statuses never
   overwrite an existing `applied`.
4. Before Submit, Rudy can `GET /api/webhooks/rudy-apply?attemptId=` or
   `?jobUrl=` with the same Bearer secret and read `{ status, detail, attemptId }`.
   Abort if the attempt is already terminal.
5. The list polls every in-flight Apply in one `getApplyStatuses` read
   (~2.5s) and refreshes the route only when a pointer leaves `applying`.
   The button shows a single **Applying** spinner — no second spinner on the
   row. `blocked`, `failed`, and `skipped` keep the row on **Open** with
   **Retry**, and a short plain-language `detail` under the title (knock-out
   reason, webhook error, skip reason). `applied` is terminal.

A second Apply while status is `applying` is refused. `ensureApplySchema()`
creates the Neon tables on read and write, so a fresh database does not 500:

| Table | Role |
|---|---|
| `apply_attempts` | ledger: one row per Apply click; partial unique index locks one in-flight attempt per job URL |
| `applies` | current pointer the dashboard joins; callback matching is `attemptId === this row` |

**Ignore** is still a local “not interested” mark. It hides the row from
**Open** and toggles clear. It does not talk to Rudy. Starting Apply clears a
prior Ignore so the in-flight row stays visible.

### Production apply policy (Rudy)

Documented here so a later reader knows what Apply actually does. No secrets.

- **Efficient fill:** one browser runner, autofill, batch screening. A second
  runner on the same posting is a race — re-check knock-out immediately before
  Submit and abort if `GET /api/webhooks/rudy-apply` already shows a terminal
  status.
- **Sparse Jev page-brain:** a knock-out scan *before* the heavy fill — visa /
  sponsorship, clearance, relocate, onsite / multi-day office. Then classify
  the outcome. Jev is used for an ambiguous next-action only, not to go faster.
  Browser fill dominates wall clock. See [Page brain](#page-brain).
- **Example:** a San Francisco 5-days/week onsite role vs a Lakewood, CO remote
  candidate is `blocked`, with a short plain reason under the title.

Production incidents and the overwrite/GET contract are in
`data/apply-efficiency-learnings.md`.

### Page brain

Rudy asks for small Jev judgments mid-apply by calling the deployment:

```
POST /api/rudy/page-brain
Authorization: Bearer $RUDY_CALLBACK_SECRET          (or x-rudy-secret)
x-vercel-protection-bypass: $VERCEL_AUTOMATION_BYPASS_SECRET

{ "mode": "knock-out", "question": "...", "options": ["Yes", "No"] }
```

It answers `{ mode, answers, confidence, inputTokens, costUsd, latencyMs }`.
Every mode also accepts optional `ats` and `url`.

| Mode | Send | Read from `answers` |
|---|---|---|
| `knock-out` | `question`, `options` (may be empty), optional `pageSummary`, `candidateFacts` | `truthfulOption` — the option to select, or `null` when the facts do not settle it; `hardKnockOut` (+ `…Probability`) — whether that truthful answer disqualifies |
| `next-action` | `pageSummary`, `visibleActions` | `nextAction`; `safeToClick` / `safeToClickTrue` for that button; `destructive` — true when code vetoed it (Cancel, Withdraw, Delete…) |
| `field-map` | `neededKey` (e.g. `linkedinUrl`), `fieldLabels`, optional `pageSummary` | `fieldLabel` — the field to fill, or `null` when none fits: skip it |
| `outcome` | `pageSummary`, optional `emailEvidence` | `outcome` — `applied`, `failed`, `blocked` or `still_working` |

`400` is a bad request, with every problem named. `503` is a setup problem on
our side, such as no candidate facts configured. `502` is Jev failing after
retries. Warm calls take 200–400ms. Each Jev attempt times out at 8s rather than
the pipeline's 30s, because the first call on a cold deployment has been seen to
hang and then succeed on retry.

Knock-out answers from the candidate facts in the profile (`PROFILE_FACTS`, see
[Your profile](#your-profile)); a request may override them with
`candidateFacts`. Safety is judged per button and the destructive word list is
applied in code, so a pick is never made safe by the page's own wording.

Every call is logged to `page_brain_calls` in Neon: mode, a summary of the input
(never the facts), answers, tokens, cost and latency. Rows before 2026-09-19 were
imported from the old local `data/apply-page-brain-log.jsonl`.

The logic is in `lib/apply-page-brain.ts` (Jev calls) and `lib/page-brain.ts`
(validation and code-side decisions, unit-tested). `pnpm apply:page-brain` runs
the same thing locally for debugging a prompt change, logged with source `cli`:

```bash
echo '{"question":"Do you need sponsorship?","options":["Yes","No"]}' \
  | pnpm apply:page-brain --mode knock-out
```

### Universal CV and cover

Every apply uses the same two files. There is no per-company cover letter.
`output/` is git-ignored; the deployment never opens the PDFs. The webhook
payload sends *local filesystem paths* for the machine that runs Rudy:

- Resume: `/home/mike/Projects/grokbot-jev-jobs/output/mike-gallegos-cv.pdf`
- Cover: not used in production Apply (resume/CV only)

Do not commit those files or paste resume text into this repo.

### Env vars (names only)

| Env var | Direction | What it is |
|---|---|---|
| `RUDY_APPLY_WEBHOOK_URL` | outbound | Where Apply POSTs the request |
| `RUDY_APPLY_WEBHOOK_SECRET` | outbound | `Authorization: Bearer …` on that POST |
| `RUDY_CALLBACK_SECRET` | inbound | Shared secret Rudy must send on GET/POST `/api/webhooks/rudy-apply` and POST `/api/rudy/page-brain` |
| `APP_BASE_URL` | outbound | Preferred public origin used to build `callbackUrl` |
| `VERCEL_AUTOMATION_BYPASS_SECRET` | inbound | Vercel Deployment Protection bypass so Rudy can reach the callback and page brain without a session cookie |

`callbackUrl` is derived in this order: `APP_BASE_URL`, then
`NEXT_PUBLIC_APP_URL`, then `https://$VERCEL_URL` (injected on Vercel), then
`http://localhost:3000`. Set `APP_BASE_URL` in production so Rudy writes back
to the stable host (legacy primary `https://jev-job-search.vercel.app`), not a
per-deployment URL.

The dashboard is behind **Vercel Authentication**, so Rudy cannot present a
session cookie. `/api/webhooks/rudy-apply` is gated by `RUDY_CALLBACK_SECRET`
instead. To get past Vercel Authentication itself, set
`VERCEL_AUTOMATION_BYPASS_SECRET`; the payload's `callbackUrl` then includes
`?x-vercel-protection-bypass=…`. Rudy can also send that value as the
`x-vercel-protection-bypass` header.

See `.env.example` for the full list. Never commit real secret values.

## Setup

```bash
pnpm install
vercel link                 # project grokbot-jev-jobs
vercel env pull .env.local  # DATABASE_URL, AI_GATEWAY_API_KEY, CRON_SECRET, Rudy apply secrets
pnpm check:jev              # one live call: confirms the key, prints latency + cost
```

Secrets live only in Vercel project settings and in `.env.local`, which is
git-ignored. `vercel env pull` brings down the Neon URL, `CRON_SECRET` and the
profile, so a fresh clone with access to the project is ready to run.

### Two ways to reach the AI Gateway, two budgets

Worth knowing, because it is easy to think one budget covers everything:

| Where | Authenticates with | Budget |
|---|---|---|
| Local CLI | `AI_GATEWAY_API_KEY` from `.env.local` | api-key budget, $25/mo |
| The deployment | `VERCEL_OIDC_TOKEN`, injected automatically | project `grokbot-jev-jobs`, $25/mo |

`AI_GATEWAY_API_KEY` is deliberately **not** in the Vercel project environment —
a deployed function does not need it, and a long-lived key in the environment is
worse than an OIDC token that Vercel mints per deployment. The consequence is that
the api-key budget does not cap the nightly run; the project budget is what does.
Both are set, and `vercel ai-gateway budgets ls` shows them side by side.

A one-off `scripts/migrate-to-neon.mts` and the SQLite layer under `lib/db/index.ts`
remain from the move off local storage. Nothing in the running system uses them —
delete both, and `data/`, once you no longer want the local copy as a backup.

### Your profile

`profile/` and `output/` are **git-ignored on purpose** — they hold a CV, cover
letters, a salary floor and work-authorization facts, and git history is hard to
scrub. The repo is public, so this is not optional.

| File | Env var | What it is |
|---|---|---|
| `profile/summary.md` | `PROFILE_SUMMARY` | ~200 words on the candidate, for the cheap title pass |
| `profile/resume.md` | `PROFILE_RESUME` | the full CV as markdown, for deep scoring |
| `profile/targets.md` | `PROFILE_TARGETS` | what a good role looks like, incl. any salary floor |
| `profile/facts.md` | `PROFILE_FACTS` | *optional* — checkable facts for Apply screening questions: work authorization, sponsorship, clearance, relocation. Only the page brain reads it |

`lib/profile.ts` reads the env var first and falls back to the file. Locally you
edit the markdown; the deployment reads the env vars, because a build from GitHub
never sees git-ignored files. `profile/` is in `.vercelignore` so that a CLI deploy
and a git deploy behave identically — otherwise only one of the two paths would
ever be exercised.

A fresh clone therefore does **not** need the markdown files: `vercel env pull`
brings the profile down from the project, and the pipeline runs off the env vars.
Write the files only if you want to edit a profile, or if you have no access to
the Vercel project.

**After editing any of them, push them up** (`facts.md` is pushed when it exists):

```bash
pnpm profile:push        # copies the files into the Vercel project env
vercel deploy --prod     # or push to the connected branch
```

Forgetting this means the nightly run keeps scoring against the previous profile,
which is silent. `/api/cron/probe` reports where each part came from
(`env` / `disk` / `missing`) so the state is at least observable.

## Running it

```bash
pnpm dev                               # dashboard on localhost:3000
pnpm pipeline --limit 200              # run the whole funnel by hand
vercel crons run /api/cron/pipeline    # or trigger the real scheduled run now
```

Or a stage at a time:

```bash
pnpm ingest   --chunks 4               # feed -> postgres, applying the stage 0 screen
pnpm ingest   --since 2026-09-17T00:00:00Z   # or only what is new
pnpm triage   --limit 500              # jev on titles
pnpm triage   --ats Workday --limit 500 # or target one platform
pnpm describe --limit 500              # ATS descriptions
pnpm score    --limit 200              # jev on resume vs description
pnpm report   --top 20                 # ranked list in the terminal
```

All of these hit the same Neon database the deployed dashboard reads, and run the
same `lib/stages` code the cron does — there is no separate local database and
nothing to sync.

`pnpm describe` is not called `pnpm fetch` because `pnpm fetch` is a built-in
pnpm command. `pnpm publish` and `pnpm deploy` are taken for the same reason.

Every stage writes a row to the `runs` table with token counts and cost, so spend
is auditable without opening the Vercel dashboard. `pnpm report` reads that table;
it does not add to it.

Two diagnostics, neither of which touches pipeline state:

```bash
pnpm check:jev    # one live gateway call: confirms the key, prints latency and cost
pnpm check:ats    # fetches a few real postings from each wired ATS, plus URL parsing
```

And a few more:

```bash
pnpm test                     # unit tests: apply lifecycle, Rudy auth, page-brain validation
pnpm score --redo             # rescore everything after a change to scoring or targets.md (~$1.20)
pnpm purge:presales           # dry run: which open rows Jev reads as pre-sales; --apply ignores them
pnpm apply:page-brain --mode knock-out < payload.json   # the page brain, locally
```

## Tuning it

Three files control quality, in descending order of leverage.

1. **`profile/targets.md`** — what a good role looks like. This is the single
   biggest lever. Jev reads it as the definition of a match.
2. **`lib/jev/score.ts`** — the fourteen questions and the composite weights.
3. **`profile/summary.md`** — the compact profile used for title triage, kept
   short so the cheap pass stays cheap.

## Where it stands

The first full pass, September 2026:

| | |
|---|---|
| Scanned from the feed | 1,461,580 |
| Kept by the stage 0 screen | 81,329 (5.6%) |
| Kept by jev triage | 8,362 (10.3%) |
| Descriptions fetched | 5,442 |
| Expired before we could read them | 2,508 |
| On an ATS with no fetcher | 315 |
| Scored | 5,442, mean 2.48, max 7.91 |
| Scoring 6.0 or above | **160** |
| Total jev spend | $2.91 |

## Reading the dashboard

One row per scored posting, ranked by fit. The pay floor in `targets.md` is
checked in code against a pay range the posting states (Jev only picks which
range is the pay), and a range below it shows as the **Under floor** badge. A
posting that states no range is never marked under the floor. One column comes from the feed rather than from jev:

- **Posted** is the job board's own `updated_at` where the feed carries it, and
  otherwise the date the aggregator first saw the posting, which is an upper bound
  on its age. The tooltip says which of the two you are looking at.

### Working the list

**Apply** starts an automated application (see [Apply → Rudy → write-back](#apply--rudy--write-back)).
The button is the only spinner. Failed / blocked / skipped stay on **Open** with
**Retry** and a one-line `detail` under the title.

The score is taken at face value. There is deliberately no thumbs up/down and no
agreement metric — grading jev's ranking against your own is a bigger project
than this is, and the tool is only useful if reading it is cheaper than reading
the job boards. If the ranking does look wrong, the lever is the wording in
`targets.md` followed by a rescore, not a weight in `lib/jev/score.ts`.

The list renders the 400 highest-scoring rows for a tab and says so when it has
cut; the cap only has to stay clear of the strong count.

## Deployment

Everything runs on Vercel. Nothing needs to be run by hand.

```
Vercel Cron (15:00 UTC daily)
   -> /api/cron/pipeline   maxDuration 800s, guarded by CRON_SECRET
        ingest   differential: only postings first seen since the last run
        triage   jev on titles
        describe ATS descriptions
        score    jev on resume vs description
   -> Neon Postgres <- the dashboard reads the same database
```

### Why a daily run fits in one function

The backfill was 81k postings and took about an hour. A *daily* run is not that,
and the difference is the whole design:

| | |
|---|---|
| Full feed scan (59 chunks, 73MB gzipped) | **13s** on Vercel, 39s locally — measured |
| A whole cron pass with nothing new to do | **12.8–14.3s** — measured |
| Postings with `first_seen` in the last 24h | ~31,000 feed-wide — measured |
| Surviving the stage 0 location screen | ~1,750/day — projected |
| Surviving triage, so needing a description and a score | ~190/day — projected |
| Wall clock on a normal day | ~5 min against an 800s ceiling — projected |
| Cost | ~$0.15/day — projected |

The measured rows are from real runs; the projected ones scale the first full pass
by the observed daily intake and have not yet been seen on a live day, because the
upstream feed had not refreshed while this was being built.

800s is generally available on Pro. Every stage gets a share of the remaining
budget and stops cleanly when it runs out; because each one selects only
unprocessed rows and commits per row, stopping early costs time, never work, and
the next run continues where it left off.

### The differential

The feed republishes all ~1.4M postings every day. `first_seen` is what makes the
daily run cheap: the ingest skips anything first seen before the last successful
run, less an hour of slack for clock skew. That turns ~81,000 upserts into
~1,750.

The window is a cron concern, not a CLI one. `GET /api/cron/pipeline?full=1`
overrides it for a recovery run; from the CLI, `pnpm ingest` scans everything by
default and `--since <iso>` narrows it.

Cron delivery is best effort and can miss or duplicate a run, so every stage is
idempotent and reconciliation-based: the window is always "since the last
successful ingest", never "since yesterday", so a missed night is picked up the
following one.

### Three things that were verified rather than assumed

- **ATS fetching works from a datacenter IP.** Workday 403s aggressively and was
  the main risk to running this on Vercel at all. Twelve live postings across
  Greenhouse, Lever, Ashby and Workday returned identical byte counts from
  `iad1` and from a residential connection, and faster.
- **Vercel Cron reaches the function past Deployment Protection.** This one
  matters because the failure is silent: protection answers an external request
  with a 302, and cron treats a 3xx as a completed invocation, so a protected
  cron path would appear to succeed every night while doing nothing. Cron's own
  invocations are exempt and arrive carrying the `CRON_SECRET` bearer token.
  `/api/cron/probe` runs nightly and records a row in `runs` purely so that this
  stays observable if the setting ever changes.
- **The profile reaches the function.** `lib/profile.ts` is read inside triage and
  score, so a deployment without it fails on the first posting it judges and not
  a moment earlier — which is exactly how it got shipped once. Confirmed on a
  build made from GitHub, with `profile/` absent from both the repo and the
  bundle: the probe reports all three parts sourced from `env`, and a live triage
  of three postings returned zero errors.

### Deploying

The Vercel project `grokbot-jev-jobs` is connected to `mcgalleg/grokbot-jev-jobs`
(public), production branch `master`. Pushing to `master` builds and promotes
automatically; branches and pull requests get preview deployments.

```bash
git push                 # code changes
pnpm profile:push        # profile changes — env vars, not files (see "Your profile")
vercel deploy --prod     # still works, for a deploy without a commit
```

The two are not interchangeable in one respect: a code change needs a push, a
profile change needs `profile:push` *and* a rebuild, because the profile travels
as environment variables rather than as files in the repo.

### Access

**Vercel Authentication** on `all` deployments: the dashboard is tied to your
Vercel account, with no auth code in the app and no shared password. External
requests get a 302, including to the cron path. Cron is exempt and carries
`CRON_SECRET`. Resume Rudy's write-back and page-brain calls are not a
session: they use `RUDY_CALLBACK_SECRET` plus, when needed, the Vercel automation
bypass (see [Apply → Rudy → write-back](#apply--rudy--write-back)). `.vercelignore` keeps
`output/`, `profile/` and `data/` out of the build context.

## Stack

Next.js 16 App Router, React 19, Tailwind 4, shadcn/ui (Base UI),
AI SDK 7 `experimental_evaluate`, Neon Postgres via `@neondatabase/serverless`.

One database, one schema (`lib/db/pg-schema.ts`), including `apply_attempts`,
`applies` and `page_brain_calls`. The four pipeline stages live in `lib/stages/`
and are called by both the cron route and the CLI, so the scheduled run and a
hand-run cannot drift apart. Apply lifecycle lives in `lib/apply.ts` /
`lib/apply-server.ts`; the page brain in `lib/page-brain.ts` /
`lib/apply-page-brain.ts`.

Every Jev call goes through `askJev` in `lib/jev/model.ts`: one model id, one
30s timeout, and one retry layer that only repeats 429s, 5xx, timeouts and
dropped connections. It also absorbs an AI SDK check that rejects a Choice when
two rounded probabilities tie, which would otherwise mark a posting as an error.

## Known limits

- `experimental_evaluate` is experimental and may change in a patch release.
  The `ai` version is pinned at 7.0.105.
- Jev's published limits are 1,200 requests a minute and 250,000 tokens a
  second, and TypeSafe notes they can change without notice. A full rescore ran
  at concurrency 12 without a rate-limit error.
- The Gateway serves Jev only under the moving alias `typesafe-ai/jev`; a pinned
  version (`jev-1.13.0`) is not found. Thresholds such as triage's 0.35 were
  tuned against the current model and should be rechecked when it changes.
- Workday is the tightest ATS limiter and runs at concurrency 3, about 2 postings
  per second. It is the only platform that costs one request per posting.
- Job descriptions are untrusted text. Jev cannot generate, so the worst case is
  a skewed score, but every instruction still says to treat the posting as
  evidence rather than instructions.
- The upstream feed is one person's hobby project. `pnpm ingest` warns if the
  manifest is more than three days stale.
- The aggregator's company datasets are CC BY-NC. Personal use is fine.
- Cron delivery is best effort: Vercel may skip or repeat an invocation and does
  not retry a failed one. The stages are idempotent and the ingest window is
  anchored to the last successful run, so a missed night self-heals — but a run
  that fails is only visible in the `runs` table and the Vercel logs.
- The apply webhook payload still names a `source` of `jev-job-search` in code
  (`lib/apply.ts`). Rudy keys off the event and paths, not the display name.
