# mcp-typesafe

> Structured, calibrated AI judgments as MCP tools — TypeSafe's System One models (Jev) inside any agent.

An [MCP](https://modelcontextprotocol.io) server that exposes the full [TypeSafe](https://docs.typesafe.ai) System One API — plus a set of higher-level tools built on top of it — to AI agents and applications.

> **Unofficial project** — not affiliated with, endorsed by, or sponsored by TypeSafe. See [Disclaimer](#disclaimer).

Instead of generating text that a program then has to parse, the server answers typed questions about a piece of state and returns structured values your code can branch on directly: probabilities, choices, rubric scores, and calibrated confidence. No text generation, no parsing.

```text
MCP client (agent, app)  ──▶  mcp-typesafe (12 tools)  ──▶  api.typesafe.ai (System One / Jev)
```

## Why this exists

LLMs are excellent at reading and writing text, but three things are consistently slow, unreliable, or impossible for them:

- **Scale** — an agent cannot read 500 search results, support messages, or log lines without burning context, budget, and patience.
- **Calibration** — "how sure are you?" from a text generator is not a probability you can threshold on.
- **Independence** — a model reviewing its own output is neither independent nor consistent.

TypeSafe's System One models return fast (~100 ms), calibrated, structured answers at a small fraction of the cost of an LLM call, which makes them usable as *primitives* inside loops, pipelines, and agent harnesses. This server packages those primitives as MCP tools — including higher-level tools that do the batching, chunking, aggregation, and thresholding for you.

## Features

- **Full System One API surface** — `choice`, `score`, and `noul` questions against a shared state, with structured instructions/criteria, all evaluated in parallel in a single call.
- **Bulk tools that beat reading lists** — filter, rank, and classify hundreds of items per call; inputs are chunked and fanned out server-side and come back as compact verdicts with raw probabilities.
- **Calibrated selection with rejection** — pick one candidate out of many with a skim → verify two-pass flow, or return *"none of these"*.
- **Stability sampling** — re-run a judgment N times and measure the spread before acting on it.
- **Independent verification batteries** — groundedness, consistency, compliance, share-safety, tool-call validation, and claim checking, each in one call.
- **Structure & hygiene** — pairwise duplicate/entity clustering and typed field extraction into fixed option sets.
- **Fast enough for tight loops** — most tool calls are a single TypeSafe request, typically ~100 ms.
- **Two transports** — `stdio` for local MCP clients, `SSE` for shared/remote use, with structured logging (stdout/stderr/file) and graceful shutdown.
- **Single static binary** — Rust, no runtime dependencies.
- **Sensible agent ergonomics** — the server advertises detailed usage instructions to clients, validates inputs before spending tokens, and returns raw probabilities so callers can re-threshold at will.

## Tools

| Tool | What it does |
| --- | --- |
| `systemone` | Evaluate one state against any typed questions in a single call |
| `list_models` | List the models/aliases your account can send |
| `filter_items` | Which of N items match a criterion (probability per item) |
| `rank_items` | Order N items by a query against ordered levels |
| `classify_items` | Bucket N items into categories |
| `choose_one` | Pick the best candidate, with two-pass verification and rejection |
| `stability_check` | Sample a judgment N times; report mean/spread |
| `verify_output` | Groundedness, consistency, compliance, share-safety, custom checks |
| `verify_tool_calls` | Pre-flight tool-call relevance and schema conformance |
| `check_claims` | supported / contradicted / unverified per claim |
| `dedupe_items` | Duplicate/entity-match pairs and clusters |
| `extract_fields` | Pull fields into fixed option sets |

### Core

**`systemone`** — the primitive everything else builds on. Send a `state` (string, object, or array) and a map of typed questions:

```json
{
  "state": "My card was charged twice for order A-104.",
  "questions": {
    "double_charge": { "type": "noul", "instructions": "Does the message say the card was charged twice?" },
    "tone": {
      "type": "choice",
      "instructions": "What is the tone?",
      "criteria": { "calm": "Neutral, matter-of-fact", "upset": "Frustrated or angry" }
    },
    "severity": {
      "type": "score",
      "instructions": "How severe is the issue?",
      "criteria": ["No impact", "Some impact", "Major impact"]
    }
  }
}
```

Returns the API response with per-question answers — `choice` + `probabilities` + `confidence`, `score` + `probabilities` + `confidence`, or `noul` (probability the question is true) — plus token `usage`.

**`list_models`** — the model names/aliases your account can use, with descriptions and release dates.

### Bulk sifting

These tools exist so an agent never has to read a long list itself. Items are referenced by index (`items[0]`, `items[1]`, …); large inputs are chunked into multiple TypeSafe calls and merged server-side.

- **`filter_items`** — one yes/no judgment per item against your criterion.
  Returns `{threshold, matched_count, matched: [[index, probability], …], probabilities: [per item]}`.
  Re-threshold freely: the full probability vector is always returned.
- **`rank_items`** — one rubric score per item against a natural-language query and your ordered levels (2–10).
  Returns `{level_count, top: [{i, score, normalized, confidence}], ranked: [indices best-first]}`.
- **`classify_items`** — one choice per item over your category set.
  Returns `{buckets: {category: [indices]}, items: [{i, choice, confidence}]}`.

### Selection & stability

- **`choose_one`** — pick the best candidate (plan, tool, answer, model) for a request. Pass 1 skims all candidates by their descriptions; pass 2 re-asks over a shortlist with fuller details and adds an absolute *"does it fit"* probability per candidate. If the best fit lands below `min_fit`, the result is rejected (`choice: null`) instead of forcing a winner.
- **`stability_check`** — run the same questions several times (2–20 samples) and report how much each answer moves: mean/std/min/max for `noul` and `score`; option means, modal share, and confidence for `choice`. A fresh throwaway value is added to object states so every sample is an independent draw.

### Verification

Checks are phrased so a **high probability means the check passes**; the response's `failed` array lists every check below `flag_threshold`.

- **`verify_output`** — one battery over a draft answer, summary, message, or code snippet: share-safety (credentials/secrets/personal data) always; groundedness and consistency against `sources` when provided; compliance against `instructions` when provided; plus custom checks.
- **`verify_tool_calls`** — before executing a batch of tool calls: is each tool appropriate for the request, and do its arguments conform to the tool's parameter schema? Unknown tools and tools without a schema are reported as `warnings`.
- **`check_claims`** — classify each claim against evidence as `supported` / `contradicted` / `unverified`, with a global `evidence` and/or per-claim sources.

### Structure & hygiene

- **`dedupe_items`** — one pairwise judgment per item pair (up to 64 items): *"same real-world entity?"*. Pairs at or above the threshold become edges; connected components become clusters.
  Returns `{threshold, edge_count, edges: [[i, j, probability], …], clusters: [[indices], …]}`.
- **`extract_fields`** — one choice per field over caller-supplied option sets, for normalized, code-consumable values (status, category, currency, date parts, …). Include a `"not stated"` option when absence is possible; normalization and arithmetic stay in your code.

## Getting started

Requires a recent Rust toolchain (edition 2024, rustc ≥ 1.85).

```bash
cargo build --release
```

Get a TypeSafe API key from <https://console.typesafe.ai/keys>, then either export it:

```bash
export TYPESAFE_API_KEY=ts-...
```

or pass it per invocation with `--typesafe-api-key`.

### stdio (local clients)

Point any MCP client at the binary:

```json
{
  "mcpServers": {
    "typesafe": {
      "command": "/absolute/path/to/mcp_typesafe",
      "env": { "TYPESAFE_API_KEY": "ts-..." }
    }
  }
}
```

### SSE (shared / remote)

```bash
./target/release/mcp_typesafe --bind 0.0.0.0:3391 -t sse --typesafe-api-key ts-...
# SSE endpoint:  http://<host>:3391/sse
# POST endpoint: http://<host>:3391/message
```

Or use the provided `start.sh`, which launches the release binary on port 3391 with SSE and reads the key from `TYPESAFE_API_KEY`.

### CLI reference

| Flag | Env | Default | Description |
| --- | --- | --- | --- |
| `-t, --transport <stdio\|sse>` | — | `stdio` | Transport mode |
| `--bind <ADDR>` | — | `127.0.0.1:8000` | SSE listen address |
| `--sse-path <PATH>` | — | `/sse` | SSE stream endpoint |
| `--post-path <PATH>` | — | `/message` | SSE message endpoint |
| `--typesafe-api-key <KEY>` | `TYPESAFE_API_KEY` | — | TypeSafe API key (required for tool calls) |
| `--typesafe-base-url <URL>` | `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` | API base URL (staging, mocks) |
| `--log-destination <stdout\|stderr\|file>` | — | `stderr` | Where logs go (`stdout` is rejected on stdio transport) |
| `--log-file <NAME>` | — | `mcp-typesafe.log` | Log file name when `file` is selected |
| `--log-level <LEVEL>` | `RUST_LOG` | `info` | Log verbosity |

## Example workflows

```text
200 search results
  → filter_items("mentions a breaking change in v2")
  → rank_items("relevance to the migration question")
  → read only the top 5 yourself
```

```text
Draft answer
  → verify_output(sources=…, instructions=…)
  → if "grounded" is in failed: revise before sending

Planned tool calls
  → verify_tool_calls(request, calls, tools)   → execute only the clean ones
```

```text
8 candidate plans
  → choose_one(request, candidates)            → choice + calibrated confidence
  → if rejected: ask the user instead of guessing
```

## Design notes

- **Chunking.** Bulk tools split work into calls of at most 200 questions and roughly 64,000 characters of state, then merge results by item index. A 450-item filter is three TypeSafe calls, not 450.
- **Limits.** Bulk tools accept up to 1,000 items; `dedupe_items` up to 64 (pairwise); `choose_one`, `classify_items`, and any `choice` criteria up to 255 options; `stability_check` 2–20 samples.
- **Thresholds with defaults.** `filter_items` 0.5, `dedupe_items` 0.75, `choose_one.min_fit` 0.3, verification `flag_threshold` 0.5, `rank_items.top_k` 10 — all overridable, and raw probabilities are always returned so callers can re-threshold without re-asking.
- **Absolutes vs. relatives.** Per-item questions (`filter_items`, `stability_check`) are absolute — every item can score low. `choose_one` and `classify_items` are relative — exactly one option wins. Pick deliberately.
- **Calibrated, not authoritative.** Low confidence or a mid-range `noul` means "do not guess": route to review, clarification, or escalation.
- **Keep arithmetic in code.** Jev is a judgment engine, not a calculator — don't ask it to count, compare dates, or compute totals. Extract components with questions and calculate elsewhere.

## Invariants

Formal contracts every tool upholds — the properties that keep the thin wrappers safe to compose (rationale and usage notes in *Design notes* above):

- **One question, one judgment.** Each item, claim, or candidate is judged against exactly one criterion, independently of every other item in the same call. There is no cross-item influence.
- **The model judges; the server computes.** The API returns probabilities and selections. Every threshold, ordering, count, mean, spread, and cluster is derived deterministically in Rust — the model never decides membership in a result set.
- **Raw probabilities always survive.** Every derived field — `matched`, `failed`, `buckets`, `ranked`, `clusters`, `mean`, … — ships alongside the raw probabilities it was computed from, so callers can re-threshold without re-asking.
- **Absolutes vs. relatives.** `noul` questions are absolute: one probability per item, and any number of items (including none) can pass. `choice` questions are relative: exactly one caller-supplied option wins, and answers are drawn from the caller-supplied option space.
- **Index alignment.** Results reference inputs by index and preserve input order. Chunking and batching are invisible: semantics are identical whether an input fits one upstream call or many.
- **Verification reads "higher = passes".** Every check is phrased as a positive property; `failed` is exactly the set of checks below the caller's `flag_threshold`.
- **Independent samples.** `stability_check` re-asks the same questions without mutating the caller's state; object states receive a fresh internal token per draw so samples are not correlated.
- **Stateless, read-only, one credential.** No tool writes files, executes code, or stores data between calls; the only egress is the TypeSafe API under a single API key — one boundary, uniform permissions across all tools.
- **Fail fast.** Inputs and caps (items, options, samples, characters) are validated before any upstream call; violations return typed errors and never partial results.

## Testing

Two ready-made test documents describe complete, executable runs that exercise the server and the TypeSafe feature set end to end. Both are written as instructions *for the model under test* — hand the file (or its contents) to any MCP-capable LLM that has this server configured, and it will narrate each step, check the expected outcomes, and produce a final report.

| Document | Scope | What it exercises |
| --- | --- | --- |
| [`TEST_SUITE_SIMPLE.md`](TEST_SUITE_SIMPLE.md) | Fast smoke/coverage suite — 15 tests (T01–T15) | Every tool and question type: `systemone` (choice/score/noul/parallel), `list_models`, `filter_items`, `rank_items`, `classify_items`, `dedupe_items`, `choose_one` (pick + reject-all), `stability_check`, `extract_fields` (incl. not-stated), `verify_output` (all standard checks + custom + negative probe), `verify_tool_calls` (relevant pass + irrelevant fail), `check_claims` (supported/contradicted/unverified). Ends with a PASS/FAIL report table. |
| [`TEST_LONG.md`](TEST_LONG.md) | Deep end-to-end pipeline test with real data volume | Fetch a Wikipedia page → split into 20+ factual sentences → `classify_items` (domains) → `dedupe_items` → `filter_items` → `rank_items` → `systemone` (all three question types in parallel) → `extract_fields` → `stability_check` → `check_claims` (trust filter) → `choose_one` (format pick) → `verify_output` (quality gate) → a full verified study guide with provenance, trust notes, and markdown tables. |

Notes: both suites expect a valid `TYPESAFE_API_KEY` and a live API connection. `TEST_LONG.md` additionally needs a URL-fetch tool for its source page (any available fetch tool works).

## Development

- Single-file server: `src/main.rs`, built on the [rmcp](https://crates.io/crates/rmcp) Rust MCP SDK.
- The whole tool surface is exercised end-to-end against a mock TypeSafe API (via `--typesafe-base-url`), including chunking, aggregation, and validation-error paths.
- Run with `RUST_LOG=debug` for verbose tracing; `-t sse` + curl for transport-level checks.
- Release history: [CHANGELOG.md](CHANGELOG.md).

## Notes

- TypeSafe documentation: <https://docs.typesafe.ai> · Playground: <https://console.typesafe.ai/playground>
- Jev accepts text only: a string, a JSON object, or an array of text values.
- MCP protocol revision served: `2024-11-05`.

## Sponsorship & support

mcp_typesafe is a one-man project by Stav Katsoulis — code, docs, and releases are all done in one person's limited time. Bug reports and well-formed issues are always free and welcome. If you need something specific and soon — tuning for your workload, special one-off work — requests are taken on at a price: open an issue describing the work, and send an email to discuss. This is also the most direct way to make further development happen faster.

## Acknowledgements

Built on TypeSafe's System One API — thanks to the TypeSafe team for the platform. See the [TypeSafe documentation](https://docs.typesafe.ai/introduction) for details on the models and API this server exposes.

## AI disclosure

This software is developed by a very experienced human (i.e. me) with some assistance from open-source LLM models (GLM & DeepSeek). The human author leads the development — i.e. actually writing and/or correcting the code — along with the technical direction, the ideas, testing, and extensive debugging over a long time. If you are not happy with partially AI-developed code, this software is not for you.

## Disclaimer

This is an **independent, unofficial project**. It is not affiliated with, endorsed by, sponsored by, or otherwise connected to TypeSafe or the makers of System One, and it is not owned, maintained, or supported by them.

The code in this repository is independently written client software that communicates with TypeSafe's publicly documented API. It contains no TypeSafe technology, model weights, or proprietary materials.

"TypeSafe", "System One", "Jev", and related names, logos, and product designations are trademarks or registered trademarks of their respective owners. They are used in this repository for identification and interoperability purposes only — to describe what this software is designed to work with — and such use does not imply any endorsement, sponsorship, or affiliation.

Use of the TypeSafe API through this server is subject to TypeSafe's own terms of service. All other trademarks and trade names are the property of their respective owners.

## License

Licensed under the [Apache License, Version 2.0](LICENSE) — see [LICENSE](LICENSE) for the full text.
