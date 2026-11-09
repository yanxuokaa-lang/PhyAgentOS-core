# AskJev MCP

An MCP server for [TypeSafe's](https://typesafe.ai) System One API (Jev). You hand it an array of
choice/description pairs and some state; it makes the `POST /v1/systemone` call and returns the
typed answer — the selected option, the probability of every option, and a confidence score.

Built on TypeSafe's official [`@typesafe-ai/sdk`](https://docs.typesafe.ai/sdk/javascript), so the
wire format, retries and error classes are theirs rather than reimplemented here.

## Tools

| Tool | What it does | Returns |
| --- | --- | --- |
| `ask_choice` | Pick one option from a set | `choice`, `probabilities`, `confidence` |
| `ask_noul` | Yes/no question | `noul` (0–1 probability of yes) |
| `ask_score` | Rate against ordered levels | `score`, `legend`, `probabilities`, `confidence` |
| `ask` | Several typed questions over one state, in a single call | `answers` keyed by your ids |
| `list_models` | Models this account can use | `models[]` |

Every answer also carries the resolving `model` and token `usage`. Every tool takes an optional
`model` to override the server default for that call.

**`score` is in legend-index units, not 0–1.** With three levels it runs 0–2, and it can land
between levels — `1.03` against `["Calm", "Frustrated", "Very angry"]` means "Frustrated". Round it
to name a level; divide by `levels.length - 1` first if you want a fraction.

`ask_choice` needs at least 2 options and `ask_score` at least 2 levels; fewer is rejected by the
input schema before any API call. Within one `ask`, question ids must be unique.

Prefer `ask` when you have more than one question about the same state — TypeSafe bills per input
token, so batching reuses the state instead of resending it per question.

## Install

Node 20+ (the v2 SDK's floor).

```bash
npm install
npm run build
```

Built on SDK v2 (`@modelcontextprotocol/server`), serving protocol revision **2026-07-28** via
`serveStdio`. Clients that still open with the 2025 `initialize` handshake are served too — the
entry point handles both eras, so older hosts keep working.

## Configure

Set `TYPESAFE_API_KEY`. Optional: `TYPESAFE_BASE_URL` (default `https://api.typesafe.ai`) and
`TYPESAFE_DEFAULT_MODEL` (default `jev-latest`), both read by the SDK. `TYPESAFE_MODEL` is this
server's older name for the model default and still wins when set.

Claude Code:

```bash
claude mcp add askjev --env TYPESAFE_API_KEY=sk-... -- node /home/cb/TOOLBOX/MCP/AskJev-MCP/dist/index.js
```

Or in `mcp.json` / `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "askjev": {
      "command": "node",
      "args": ["/home/cb/TOOLBOX/MCP/AskJev-MCP/dist/index.js"],
      "env": { "TYPESAFE_API_KEY": "sk-..." }
    }
  }
}
```

## Usage

`ask_choice` — options are either plain strings or `{option, description}` pairs. Descriptions are
the rubric and usually improve the answer:

```json
{
  "state": "Help! My payouts have been failing for 3 days.",
  "instructions": "Which team should handle this?",
  "options": [
    { "option": "billing", "description": "Payments, invoicing, refunds" },
    { "option": "technical", "description": "Bugs, outages, integrations" },
    "sales"
  ]
}
```

```json
{
  "type": "choice",
  "choice": "technical",
  "probabilities": { "billing": 0.08, "technical": 0.85, "sales": 0.07 },
  "confidence": 0.82,
  "model": "jev-1.13.0",
  "usage": { "input_tokens": 312, "output_tokens": 48 }
}
```

`ask` — batch mixed question types over one state:

```json
{
  "state": { "ticket": "Help! My payouts have been failing for 3 days." },
  "questions": [
    { "id": "dept", "type": "choice", "instructions": "Which team?",
      "options": ["billing", "technical", "sales"] },
    { "id": "urgent", "type": "noul", "instructions": "Does this convey urgency?",
      "criteria": { "true": "Explicitly time-sensitive", "false": "No urgency expressed" } },
    { "id": "frustration", "type": "score", "instructions": "How frustrated is the customer?",
      "levels": ["Calm", "Frustrated", "Very angry"] }
  ]
}
```

`state` accepts a string or any JSON structure (chat logs, records, application state).

## Confidence

`confidence` is a separate axis from the answer: the answer tells you *what*, confidence tells you
*whether to act*. Gate on it — act automatically above your threshold, route to a human below it.

## Errors

API failures come back as `isError` tool results carrying the status and body.

Retries are the SDK's `RetryPolicy` defaults: `408`, `429` and `500`–`599` plus connection and
timeout failures, 2 retries after the first attempt, 500ms backoff doubling to 5s with 25% jitter,
honoring `Retry-After` and `retry-after-ms` up to 60s. Per-attempt timeout is 10s with no total
budget.

Invalid arguments are rejected by the input schema before any request is made, and surface as a
protocol error rather than an `isError` result.

## Layout

- `src/schemas.ts` — zod input schemas and the mapping from caller-friendly options/levels to the
  SDK's `criteria`
- `src/index.ts` — MCP server and tool registration; `buildServer()` is the per-connection factory
  `serveStdio` pins to each connection
- `scripts/lib/mcp-client.mjs` — the SDK client the harness scripts share, negotiating the era with
  `mode: 'auto'`

## Testing against the brncx-skills vault

`scripts/vault-test.mjs` runs real notes from `40-RESOURCES` through the server over stdio — the
same path a client takes, so it exercises the MCP layer and not just the HTTP client.

Each note becomes one batched `ask` call with three questions: a **choice** (primary topic, drawn
from the vault's own tag taxonomy), a **noul** (is it actionable?), and a **score** (how deep?).
The note's hand-written `tags:` act as ground truth, so the script reports how often Jev's pick
agrees with yours, split by whether confidence cleared 0.6.

```bash
export TYPESAFE_API_KEY=$(grep -oP '(?<=TYPESAFE_API_KEY=")[^"]+' ~/.bashrc)

node scripts/vault-test.mjs --n 8 --dry   # show the extracted state, call nothing
node scripts/vault-test.mjs --n 8         # send to Jev
node scripts/vault-test.mjs --n 20 --dir /mnt/d/OBS/brncx-skills/30-CLIENTS
```

Only the title and TL;DR are sent, not the whole note — roughly 700 input tokens per note for all
three questions. Adjust the `TOPICS` table at the top of the script to change the taxonomy; each
entry maps an option to the vault tags that count as a match.

## Benchmarking the vault's content scorer

`scripts/content-scorer-bench.mjs` compares the vault's `content-scorer` skill against Jev on the
two dimensions that are judgment calls rather than counts.

`seo_content_analyzer.py score` computes Humanity (30%) and Specificity (25%) from a phrase
blacklist and regex counts — 55% of the composite. This script asks Jev the same two questions as
`score` questions, then checks which scorer better separates what you published from what you left
in draft, using the `status:` frontmatter as ground truth.

```bash
export TYPESAFE_API_KEY=$(grep -oP '(?<=TYPESAFE_API_KEY=")[^"]+' ~/.bashrc)

node scripts/content-scorer-bench.mjs --n 24 --dry   # list the sample, call nothing
node scripts/content-scorer-bench.mjs --n 24         # score it
node scripts/content-scorer-bench.mjs --n 30 --out rows.json
```

Three scorers are reported: `analyzer` (today's composite), `jev` (Jev's two dimensions alone), and
`hybrid` (Jev for judgment, the analyzer's arithmetic for structure/SEO/readability). The headline
metric is AUC — the chance a random published document outscores a random draft, where 0.5 is a
coin flip.

`--words` caps how much of each document is sent (default 1200); `sd` in the summary is the spread
of a dimension across the sample, which is how a saturated dimension gives itself away.

**Result on 30 marketing documents:** no scorer separated published from draft — analyzer AUC 0.52,
Jev 0.52, hybrid 0.49. `status: draft` turns out not to be a quality label, so this corpus can't
settle the question. What it did confirm is the saturation: analyzer Specificity has sd 3.1 around
a mean of 99, versus sd 15.8 for Jev's.

### Grading sheet

To benchmark against real quality labels instead of publish status:

```bash
node scripts/make-grading-sheet.mjs --n 30     # writes the sheet into the vault
# fill the grade column in Obsidian: ship / fix / scrap
node scripts/content-scorer-bench.mjs --labels
```

`make-grading-sheet.mjs` draws a sample balanced on publish status and spread across content type
(at most `--max-per-type` from any one folder), shuffles it, and writes it to
`99-TMP/content-grading-sheet.md` with no scores and no `status:` — grading blind is the point, so
the labels stay independent of what the analyzer thought. `grading-key.json` in the repo root holds
the mapping back to paths and is what `--labels` reads; it is gitignored, since it lists paths and
titles from a private vault.

With `--labels` the bench reports two splits, `ship` vs `scrap` and `ship` vs `fix+scrap`. Rows left
blank in the sheet are dropped, so a partly-filled sheet still runs.

## Status

All five tools are verified working against the live API over stdio, on both the 2026-07-28 and
2025 eras, including the error paths (bad key → `401` as an `isError` result; bad arguments →
schema rejection; missing `TYPESAFE_API_KEY` → refuses to start).

What is not covered:

- **No automated tests.** There is no `npm test`. The three scripts under `scripts/` are live
  integration checks that cost API tokens, which makes them useful by hand and useless in CI.
- **`@typesafe-ai/sdk` is pre-1.0** (`0.6.0` at time of writing), so expect breaking changes on
  upgrade. The dependency is range-pinned to `^0.6.0` for that reason.
- **`ask_noul` ignores `confidence`.** The API returns none for noul questions, so unlike choice
  and score there is no gate to threshold on — only the `noul` probability itself.
