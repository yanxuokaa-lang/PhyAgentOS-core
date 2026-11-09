# Last Exit

**One gate. One good lie.** There is something alive in your cargo. Convince the inspector there isn't.

[Play at gate.fade.tools](https://gate.fade.tools) · [Findings](evaluation/REPORT.md) · [How it works](https://gate.fade.tools/design)

![Inspector Kade at the checkpoint](public/assets/checkpoint.png)

A small cyberpunk encounter built by Dan Doca. Type your own cover story, slide over a manifest, offer a bribe, and live with the inspector's decision. Inspired by the tension of the Nomad border crossing in Cyberpunk 2077; this is an original setting, character and artwork, not a mod or affiliated release.

## Can you fool him?

In a frozen batch of **100 scripted crossings**, smugglers escaped **29/90** times and honest shipments passed **10/10**. Consistent cover stories passed 10/10; undeclared personal lawn-mower stories passed 0/10. A contradictory opening followed by a corrected cover passed 6/10.

The batch made 596 Jev requests across 298 turns. Median local HTTP reply time was **537 ms** (p95 664 ms), including two sequential model calls but excluding browser paint and typing. Estimated input-token cost was **$0.057 for all 100 crossings**, at $0.042/million input tokens. Public hosting adds network and database overhead; these are local evaluation timings, not a hosted speed promise.

These were **50 authored variants, each repeated twice**, on `jev-1.13.0`, not 100 independent human players or a model accuracy benchmark. The current request alias is `jev-latest`, so future outcomes may change. Raw fictional transcripts, requests, responses, usage and timings are in [evaluation/](evaluation/). The frozen engine SHA-256 is `6bf0c1c5ec54d54d08365974563ada875b7814b9c5b76f5012acfdd23e92b632`.

## What is AI, and what is game code?

Each player reply makes two Jev calls: one reads the player's statements into typed observations; the other selects an available action. The guard sees the conversation, papers and evidence he has discovered. He never sees the hidden cargo or scenario flag.

Dialogue lines are authored. Scans and searches have deterministic consequences. Code prevents asking the same question action twice and requires physical document/bribe controls; saying “I handed you the papers” does not change inventory. Jev chooses what to do within those rules. Seven player turns maximum.

Zero repeated question actions is a code guarantee, not proof of model memory. Some runs still misread an internal-heater explanation as a heat-location mismatch. A believable lie getting through is an intended game outcome; this is not a security or calibration benchmark. See the [detailed limitations](evaluation/FINDINGS.md).

## Run locally

Node.js 24 recommended. The local game server uses only Node's standard library; install dependencies for hosted tests/deployment.

```sh
npm ci
npm start
```

Open `http://127.0.0.1:9442`. Connect a TypeSafe key at `/setup.html`, or set `TYPESAFE_API_KEY`. Setup persists it in the ignored `.local/typesafe-key` file so it survives restarts. Never commit that file. Local inference has a persistent **$0.25** allowance in `.local/spend.json`; deleting the ledger would reset accounting.

```sh
npm test
# Hosted transaction tests against a dedicated Neon database; no model calls:
node --env-file=.env.local scripts/migrate.mjs
node --env-file=.env.local --test tests/hosted.test.mjs
```

`scripts/stress.mjs` runs paid scripted playthroughs against the local server. Review its plan and budget before running it. Published evaluation receipts can be audited without spending credits.

## Public hosting and budget

Vercel serves `public/` and `api/index.mjs`; Neon stores sessions, rate counters and spend reservations. Configure `DATABASE_URL`, `TYPESAFE_API_KEY`, and a random `SESSION_SECRET` as server-side environment variables. Apply `db/schema.sql` using `scripts/migrate.mjs` before deployment. Production uses budget `public-v1`; previews use `preview-v1`.

The initial public allowance is **$1 of estimated model input cost total**, with no automatic refill. Each full reply reserves the maximum permitted cost before inference using a database transaction. Concurrent requests share that balance. Successful calls refund the unused reservation; uncertain failures keep it. There are 12 new crossings and 60 replies per IP per hour, using a keyed hash rather than storing the IP. These limits deter casual abuse; they are not a DDoS defense. Hosting charges and changes to provider pricing are outside this model-cost allowance.

When credits run out, the game pauses and links to a GitHub request to reopen the checkpoint. Increase `last_exit.budget.cap_nano` for `public-v1` to refill (1 USD = 1,000,000,000 units), preserving `used_nano`. To pause immediately, set `enabled` to false. Never reset spent balance to refill. A first release can be contained with this switch; subsequent releases can also roll back via Vercel.

Replies are sent to TypeSafe. Fictional transcripts are stored for a four-hour session, become inaccessible after expiry and are deleted on the next new crossing. Keep personal information out of the game. First-party daily counters record page views, crossings started, saved replies and outcomes, separated by production/preview budget. They contain no visitor identifier, dialogue or referrer. Page views count successful client loads, including reloads and our own visits, not unique people; the visit endpoint uses the existing temporary hashed-IP rate limiter (60 per hour). Counters survive session expiry and begin at this update, without backfilling earlier activity. They are private to the database; no public analytics endpoint or third-party tracker is installed. Keys stay server-side and are excluded from exported receipts. Budget reservation records contain only IDs, timestamps and cost accounting.

## Credits

Code: MIT. Scene: original AI-generated artwork. Fonts: Rajdhani and DM Sans, distributed with their SIL Open Font Licenses in `public/fonts/`. Jev is a TypeSafe AI product. This independent experiment is not endorsed by TypeSafe or CD PROJEKT RED.
