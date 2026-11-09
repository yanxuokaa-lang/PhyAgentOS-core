# Ask Jev: an Open WebUI Tool for TypeSafe's System One model

Lets an Open WebUI chat model send typed questions to [Jev](https://docs.typesafe.ai/api)
and get back **calibrated probabilities** instead of a guess.

Jev is a classifier, not a text generator. It never answers open-ended questions — it
answers *typed* questions (yes/no, choice, score) about a *state* you give it. This tool's
job is to make the chat model construct a well-formed `{state, questions}` payload and to
render the answer back in a form the model can reason over.

## What this is good for

| Use it for | Why |
|---|---|
| A defensible probability or score | An LLM's "0.8 urgency" is a vibe; Jev's is RL-calibrated, with a distribution and a confidence behind it. |
| A structured decision, fast | Jev emits typed JSON in one shot instead of generating it token by token — TypeSafe reports up to 200x faster inference and 400x lower cost than an LLM producing the same answer. |
| Labelling many items at once | `jev_classify_batch` fans out in parallel — far cheaper and more consistent than having the model label 200 rows itself. |
| Rubric grading / eval scoring | The same scorer applied identically to every item. |
| Prototyping Jev questions | Iterate on wording, criteria and thresholds conversationally before hardcoding them into a real harness. |

## What this is *not* for

**Model routing and guardrails.** Those belong in an Open WebUI **Filter** function
(`inlet`/`outlet`) or a **Pipe**, not a Tool. A Tool is invoked *by* the LLM, after the
LLM has already loaded the context and spent a turn deciding to call it — so wrapping
Jev as a Tool spends ~2 LLM turns to save one classification, and Jev's "200x faster,
400x cheaper" argument evaporates. A Filter runs *before* the model sees the message,
which is where Jev actually pays for itself. This repo is the classification instrument;
the Filter is the natural follow-up.

## Install

1. Open WebUI → **Workspace → Tools → +**
2. Paste the contents of [`ask_jev.py`](ask_jev.py), save.
3. Open the tool's **valves** (gear icon) and set `JEV_API_KEY`.
4. Enable the tool on a model, or per-chat via the **+** menu.

Requires Open WebUI ≥ 0.4.0. No extra pip packages — `aiohttp` and `pydantic` already
ship with Open WebUI.

> Workspace Tools execute arbitrary Python on your server. Read the file before installing it.

## Tools exposed to the model

| Tool | Jev question type | Returns |
|---|---|---|
| `jev_yes_no(question, state)` | `noul` | probability 0–1 plus a yes/no verdict at the 0.5 threshold |
| `jev_classify(question, options, state)` | `choice` | chosen option, confidence, full distribution |
| `jev_score(question, levels, state)` | `score` | weighted score, closest level, confidence, distribution |
| `ask_jev(questions, state)` | any mix | one answer per question — **one** Jev request, evaluated in parallel |
| `jev_classify_batch(question, options, items)` | `choice` × N | a results table and a tally |

`ask_jev` is the escape hatch: several questions about the same state in a single
request is how Jev is meant to be used, so the docstring steers the model there whenever
it has more than one thing to ask.

### Where `state` comes from

Resolved in this order:

1. the `state` argument, if the model passed one;
2. otherwise the text of any **attached files**;
3. otherwise the last `CONTEXT_MESSAGES` **chat messages** (so "is this thread urgent?" works
   without re-pasting anything);
4. otherwise an error telling the model what to supply.

Content over `MAX_STATE_CHARS` is truncated — head-first for explicit text and files,
tail-first for conversation history, since the recent turns are the relevant ones.

## Valves (admin settings)

| Valve | Default | Purpose |
|---|---|---|
| `JEV_API_KEY` | `""` | TypeSafe API key, sent as the Bearer token. **Required.** |
| `JEV_BASE_URL` | `https://api.typesafe.ai` | Override for OpenRouter, a proxy, or a self-hosted gateway. |
| `JEV_ENDPOINT_PATH` | `/v1/systemone` | Path appended to the base URL. OpenRouter needs `/api/alpha/decisions`. |
| `JEV_MODEL` | `jev-latest` | Pin a version, e.g. `jev-1.13.0`. Via OpenRouter: `typesafe/jev-1.13`. |
| `REQUEST_TIMEOUT` | `30` | Per-request timeout, seconds. |
| `MAX_RETRIES` | `3` | Retries on 429 / 529 / 5xx / timeout / network error. |
| `BACKOFF_FACTOR` | `0.75` | `factor * 2^attempt` + jitter; a `Retry-After` header wins when present. |
| `MAX_STATE_CHARS` | `24000` | Cap on the state sent to Jev. |
| `CONTEXT_MESSAGES` | `12` | Trailing chat messages used when no state is given. |
| `BATCH_CONCURRENCY` | `8` | Parallel requests during batch classification. |
| `BATCH_MAX_ITEMS` | `200` | Rejects oversized batches instead of melting your rate limit. |
| `RAW_JSON_OUTPUT` | `false` | Return Jev's raw JSON instead of the formatted summary. |

### Using OpenRouter instead of TypeSafe directly

OpenRouter serves Jev through its **Decisions API**, not the OpenAI-compatible
`/chat/completions` endpoint - so changing `JEV_BASE_URL` alone is not enough, the path
differs too. Set three valves:

| Valve | Value |
|---|---|
| `JEV_API_KEY` | your OpenRouter key (`sk-or-v1-...`) |
| `JEV_BASE_URL` | `https://openrouter.ai` |
| `JEV_ENDPOINT_PATH` | `/api/alpha/decisions` |
| `JEV_MODEL` | `typesafe/jev-1.13` |

The request and response bodies are otherwise the same `{state, model, questions}` /
`{answers, usage}` shapes, so nothing else changes. OpenRouter additionally returns
`usage.cost`, which the tool appends to the footer when present.

Note the endpoint is `https://openrouter.ai/api/alpha/decisions` - there is no `/v1` in
it. OpenRouter's own API reference renders it as `/api/v1/api/alpha/decisions`, which is a
docs-generator artifact and 404s.

401/403 and 422 are **not** retried — a bad key or a malformed body will not get better
on the second attempt, so the tool returns an actionable message instead.

## Example exchanges

**Multi-question triage** — the model calls `ask_jev` once:

```
**Is this urgent?** -> **yes** (probability 0.95)
**Which team should handle it?** -> **billing** (confidence 0.81)
  billing 88% | technical 12%

_Jev jev-1.13.0 | tokens in/out: 318/34_
```

**Scoring:**

```
**How frustrated is the customer?** -> **1.05/2** - closest level: "Frustrated" (confidence 0.92)
  1 Frustrated 95% | 2 Very angry 5%
```

**Batch:**

```
| # | Item | Answer | Confidence |
|---|---|---|---|
| 1 | Payouts have been failing for 3 days | billing | 0.81 |
| 2 | The dashboard 500s on load | technical | 0.94 |

Tally: billing: 1, technical: 1
Model: jev-latest | tokens in/out: 612/68
```

## Tests

```bash
python test_ask_jev.py
```

55 offline checks — no network, no pytest. They cover payload construction for all three
question types, rendering, state resolution and truncation, argument coercion (small models
routinely pass JSON *strings* where a dict is expected, so every entry point parses both),
validation limits (2–255 choice options, 2–10 score levels), the retry loop and error
mapping against a fake session, batch fan-out with a partial failure, and status events.

What they do **not** cover: the real API. For that, set `JEV_API_KEY` and run:

```bash
python smoke_live.py
```

which sends one real multi-question request and prints what comes back.

## Licence

MIT
