# jev-lint

Find possible contradictions, stale claims, unresolved markers, and dangling wikilinks in a Markdown knowledge base.

jev-lint is built for ordinary Obsidian vaults and structured LLM wikis. It runs mechanical checks locally, sends only selected claims (plus the page title, `updated` date, and run date for staleness checks) to [TypeSafe Jev](https://typesafe.ai/) for semantic scoring, and writes a self-contained `report.html` with the exact evidence behind every flag.

## Install

Python 3.11 or newer is required.

```bash
pipx install git+https://github.com/vayungodara/jev-lint
```

Or with uv:

```bash
uv tool install git+https://github.com/vayungodara/jev-lint
```

Set `TYPESAFE_API_KEY` in your environment. When running inside Amp, jev-lint can also use the key configured for the Jev MCP server in Amp settings.

## Use

```bash
# See the question count and cost estimate without calling Jev
jev-lint ~/path/to/vault --dry-run

# Run the checks and write report.html in the current directory
jev-lint ~/path/to/vault

# Open the report when the run finishes
jev-lint ~/path/to/vault --open

# Return the result as JSON
jev-lint ~/path/to/vault --json

# Write the report somewhere else
jev-lint ~/path/to/vault --output ~/reports/vault.html
```

The default budget is $1.00. A run is refused before any API call when its estimated uncached input cost exceeds the budget. Change the cap explicitly with `--budget USD`. `--dry-run` never refuses; it prints the estimate, notes when it exceeds the budget, and never needs an API key.

Exit status: 0 no findings, 1 findings, 2 error (including no Markdown pages found or a dry-run estimate over budget), 130 interrupted. jev-lint only overwrites a report it wrote itself.

### Real run

This is a fresh run over a personal Markdown wiki on 17 September 2026:

```text
$ jev-lint ~/brain
99 pages · 1,267 Jev questions · 16 findings
113.9s · 579,006 input tokens · $0.0243 · report.html
```

The findings comprised 2 contradiction signals, 1 stale-claim signal, 1 missing-page rule finding, and 12 unresolved-marker rule findings. These figures describe that vault and that run with version 0.1.0, not a performance guarantee. Version 0.1.1 ignores markers and links inside inline code, which removes 3 of those rule findings on the same vault.

## What it checks

**Possible contradictions.** Claim pairs are nominated from linked pages, pages under the same parent, or pages with unusually strong lexical overlap. Jev scores the exact pair. Pairs with a contradiction probability of 0.65 or more become findings. Jev's probabilities vary by a few hundredths between runs, so a pair near the threshold can appear in one run and not the next.

**Possibly stale claims.** Dated statements and claims on older pages are scored against the run date. A finding requires a probability-weighted stale score of at least 1.5 on the 0–2 scale (0 current, 1 may have changed, 2 clearly outdated) and a confidence of at least 0.5.

**Unresolved markers.** `TODO`, `FIXME`, `[?]`, and explicit unresolved comments are found locally. Markers inside code fences or inline code are ignored.

**Missing pages.** Wikilink paths, page names, titles, and aliases are resolved locally, including `[[folder/page]]`, `[[page#heading]]`, and `[[page|alias]]` forms. Links to attachments such as images and PDFs are not treated as pages.

For Vayun-style wikis with both `index.md` and a `wiki/` directory, jev-lint scans the Markdown pages under `wiki/`. Other vaults are scanned recursively from the supplied directory.

## Cost and caching

TypeSafe Jev input is priced at $0.042 per million input tokens. `--dry-run` makes a conservative token estimate from the serialized questions and makes no network request. The preflight budget considers only cache misses. Successful responses are cached in `~/.cache/jev-lint/responses.json` by a hash of the model, state, and question, so unchanged reruns avoid repeat calls. Staleness questions include the run date, so they are asked again on a new day. Delete that file to force a fresh run.

The output cost is calculated from input-token usage returned by the API. It is an estimate, not an invoice.

## How questions are built

jev-lint reads Markdown outside fenced code blocks and retains source paths, line numbers, and exact quote text. It samples up to 10 eligible claims from each page. Contradiction candidates are bounded to one claim pair for each related or high-overlap page pair. Staleness candidates come from dated claims or claims on pages whose `updated` date is more than 180 days old.

Mechanical findings never receive model probabilities in the report. Semantic findings display only probabilities and confidence values returned by Jev; unavailable values remain unavailable.

## Limits

- Semantic checks are candidate-based, not an exhaustive comparison of every sentence with every other sentence.
- A flag is a prompt to inspect the sources, not permission to rewrite a note.
- The frontmatter reader supports the common scalar, inline-list, and list forms used for titles, aliases, `up`, `related`, and `updated`; it is not a general YAML parser.
- Markdown symlinks are ignored so content outside the selected vault cannot be sent to the API.
- The cache is safe for normal single-process use. Do not run multiple jev-lint processes against the same cache simultaneously.
- The HTML report is self-contained. The public landing page is not part of the CLI runtime.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/pytest
```

The live integration test is skipped unless `TYPESAFE_API_KEY` is present. It runs only the synthetic fixture and asserts that input cost stays below $0.02.

## AI assistance

Agents wrote most of the initial implementation, tests, documentation, report design, and launch material. Vayun directed the product, supplied the reference workflow and test vault, reviewed the release requirements, and owns the final decisions. The repository includes this disclosure because provenance matters for a tool that audits other people's knowledge.

## License

MIT
