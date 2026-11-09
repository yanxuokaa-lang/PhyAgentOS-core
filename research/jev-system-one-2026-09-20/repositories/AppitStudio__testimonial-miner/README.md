# Testimonial miner

Finds quotable user praise in your Gmail mailboxes and stores it, per app, in a small
JSON database you can review before putting quotes on a website.

The workflow is ordinary code with one AI step. Code fetches mail over IMAP, throws away
newsletters, notifications and your own outbound mail, strips quoted replies and
signatures, and splits what the sender actually wrote into numbered sentences. Then one
request to TypeSafe's **Jev** model answers, for that email, all of these at once:

| Question | Type | Used for |
| --- | --- | --- |
| What kind of message is it? | Choice | reject `automated` and `business_outreach` |
| Which of our apps is it about? | Choice | grouping; falls back to app names found in the text |
| Is the sender an individual user of the app? | Noul | filter out agencies, vendors, press |
| Does it contain praise of the app or the support? | Noul | gate |
| How quotable is the praise? (4 levels) | Score | gate and ranking |
| Does it also report a problem? | Noul | review flag |
| Is it written in English? | Noul | review flag |
| Is sentence S00 / S01 / … quotable praise? | one Noul per sentence | assemble the quote verbatim |

The model never writes text. The stored quote is the sender's own sentences, selected by
the per-sentence answers and joined in order. All thresholds live in
`testimonial_miner/config.py` (`Thresholds`) and can be re-applied to the logged answers
without new model calls (`redecide`).

## Setup

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # installs typesafe-sdk and python-dotenv into .venv
cp .env.example .env         # then edit
```

`.env` needs:

- `API_KEY` – your TypeSafe key.
- `GMAIL_1_EMAIL` / `GMAIL_1_APP_PASSWORD`, `GMAIL_2_EMAIL` / `GMAIL_2_APP_PASSWORD` –
  one pair per mailbox. Use a Google **app password**, not the account password:
  1. Google Account → Security → turn on **2-Step Verification** (required).
  2. Go to <https://myaccount.google.com/apppasswords>, create one named `testimonial-miner`,
     and paste the 16 characters (spaces are fine).
  3. For a Google Workspace address (e.g. `support@appitstudio.com`) the same steps apply
     inside that account. If login still fails with `Invalid credentials`, check the Admin
     console: app passwords and IMAP access can be disabled there
     (Apps → Google Workspace → Gmail → End User Access).
- `OWN_EMAILS` (optional) – other addresses you reply from, e.g.
  `support@appitstudio.com,partnerships@appitstudio.com`. Mail *from* these is skipped,
  and so is anything from their non-public domain.

Optional: edit `apps.json` to add a one-line `description` per app and any aliases.
Descriptions help the model attribute emails that describe an app without naming it.

## Run

```bash
# First: confirm the API key and both mailbox logins (no model calls)
uv run python -m testimonial_miner check

# Trial: newest 100 messages, no model calls, shows what would be judged and why things were skipped
uv run python -m testimonial_miner scan --limit 100 --dry-run

# Trial with the model
uv run python -m testimonial_miner scan --limit 100

# Everything since 2025-03-01 (default), both mailboxes
uv run python -m testimonial_miner scan

# Later runs only fetch mail newer than the last complete run (per-account IMAP cursor)
uv run python -m testimonial_miner scan

# Review
uv run python -m testimonial_miner web                 # local dashboard at http://127.0.0.1:8765
uv run python -m testimonial_miner list
uv run python -m testimonial_miner list --app DockFlow --status candidate --min-quality 2
uv run python -m testimonial_miner list --full          # include the cleaned email body
uv run python -m testimonial_miner show <id>
uv run python -m testimonial_miner stats
```

Other flags: `--since YYYY-MM-DD`, `--account you@gmail.com`, `--full` (ignore the saved
cursor), `--rejudge` (send already-processed messages to the model again),
`--workers N` (parallel model requests, default 4), `--eml-dir DIR` (read `.eml` files
instead of Gmail; `fixtures/` has samples), `--data-dir DIR`.

### Local review dashboard

Run `uv run python -m testimonial_miner web` and open
<http://127.0.0.1:8765>. The dashboard reads `data/testimonials.json` directly and lets you
search quotes, senders, subjects, and cleaned bodies; filter by status, app, review state,
and problem signal; sort the results; inspect model scores and the original cleaned email;
and copy a quote with its attribution.

The server binds to `127.0.0.1` by default, so the private customer data stays on this Mac.
Stop it with Ctrl-C. After a later scan or `redecide`, reload the page to see the updated
database. Use `--port N` to choose another port.

## Output

Everything lives in `data/` (git-ignored):

- `testimonials.json` – the database. `items[]` holds one record per candidate or
  borderline email: sender, date, subject, `app`, `status`, the raw scores, the selected
  `quote`, the `quote_sentences` with their probabilities, and the cleaned `body`.
  Two fields are yours to edit and survive re-runs: `review` (`pending` by default;
  use e.g. `approved` / `rejected`) and `notes`.
- `classified.jsonl` – one line per message seen: either a `skip_reason` (never sent to
  the model) or the full set of answers and the decision. This is the audit trail and the
  input to `redecide`.
- `cursors.json` – per-account IMAP position for incremental runs.

### Incremental scan safety

Completed, unlimited scans save a per-account Gmail UID high-water mark together with
`UIDVALIDITY`, the configured start date, the completion time, and audit-only oldest/newest
message dates. Later normal scans request only UIDs above that mark. Gmail UIDs, rather than
email `Date` headers, are the authoritative delta boundary because message dates can be delayed
or out of order.

`--limit` and `--dry-run` intentionally do not advance the cursor, so a trial cannot skip the
older backlog. The append-only log supplies a second deduplication layer when that backlog is
scanned. If any TypeSafe request fails, or Gmail returns an incomplete header/body fetch, the
account cursor is not advanced; the next run retries the failed range while logged successes are
skipped. Cursor writes are atomic. Use `--full` only when you intentionally want to ignore the
saved UID cursor.

The data directory is created with owner-only permissions, and generated log/database/cursor
files use mode `0600`. Keep `.env` owner-readable only because it contains API and Gmail app
passwords.

## Decisions and tuning

A message is a **candidate** when the sender looks like a user (≥ 0.5), praise is present
(≥ 0.6) and the quality score is at least 1.5 on the 0–3 scale ("specific praise" or
better). Weaker evidence (praise ≥ 0.35, quality ≥ 1.0) is kept as **borderline**. Mail
classified as automated or business outreach is rejected even if it flatters the app.
Sentences with a quote probability ≥ 0.6 form the quote.

To change any of this, edit `Thresholds` in `testimonial_miner/config.py` and run:

```bash
uv run python -m testimonial_miner redecide
```

It rebuilds `testimonials.json` from the logged answers in seconds and keeps your
`review` / `notes` edits.

## Cost and limits

Jev is billed per input token, about $0.042 per million. A typical email costs
2–3 thousand tokens, so 10,000 judged emails is roughly $1. Most mail in a business
inbox never reaches the model: `stats` shows how much the header rules removed.

Things to know:

- Only inbound mail is judged. Your replies and anything you forwarded to yourself are
  skipped, and quoted text inside a reply is removed, so a compliment that only exists in
  a forwarded message will not be found.
- Jev's accuracy is best in English. Non-English candidates are kept, with `is_english`
  low, so you can check them by hand.
- Long emails are cut at 8,000 characters and 40 sentences before judging.
- The tool selects quotes; it does not decide whether you may publish them. Ask the
  sender before quoting a private email on your site.

## Where your data goes

- Gmail is read over IMAP with read-only commands. Nothing is labelled, moved, or sent.
- For every email that passes the header rules, one request goes to TypeSafe's API
  (`api.typesafe.ai`). It contains the sender's name and address, the subject, the cleaned
  sentences the sender wrote, and the app catalogue from `apps.json`. Nothing else leaves
  your machine, and the review dashboard listens on `127.0.0.1` only.
- Mail skipped by the header rules is never sent anywhere. `data/` keeps the cleaned bodies
  of judged emails on disk with owner-only permissions; treat it as personal data.

## Versions

Developed and checked on 2026-09-18 against `typesafe-sdk` 0.7.0 (`POST /v1/systemone`) and
model `jev-1.13.0`, which is what the default alias `jev-latest` resolved to on that date.
Set `TYPESAFE_MODEL=jev-1.13.0` in `.env` to pin the version while you tune thresholds; an
alias can move to a newer model whose answers differ.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```

The tests run offline and need no `.env`. They replace IMAP and the model with fakes and
cover the incremental cursor rules, the decision policy, quote assembly, app resolution, and
a full scan of the synthetic emails in `fixtures/` (header skips, quoted-reply removal,
deduplication, dry run). Scripted answers exercise the code; they say nothing about Jev's
accuracy.

For a live end-to-end check, run the same fixtures through the real model. It makes 8
requests, about 22k input tokens, well under one cent. Add `appitstudio@gmail.com` to
`OWN_EMAILS` first so the outbound fixture is skipped the way your own mail would be:

```bash
uv run python -m testimonial_miner --data-dir data-test scan --eml-dir fixtures
```

On 2026-09-18 with `jev-1.13.0` this produced 5 candidates (one per app), 3 rejected (a
license problem, agency outreach that flattered the app, and "Got it, thanks!") and 3 header
skips. Results can differ with another model version.

## License

MIT; see [LICENSE](LICENSE). Built by AppIt Studio with Claude Code. `AGENTS.md` holds the
project context, the pipeline description, and the validation notes.
