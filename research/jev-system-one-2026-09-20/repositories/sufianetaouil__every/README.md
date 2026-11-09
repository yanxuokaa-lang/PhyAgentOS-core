# every

**Ask a yes/no question of every function in a codebase. Ranked answers in seconds, for cents.**

```
$ every "catches an exception and then ignores it" ./my-api

scanned 1,842 functions in 214 files ...   3.1s   $0.03   class: body

 0.93  src/payments/webhook.py:88     handle_stripe_event
 0.88  src/auth/session.py:141        refresh_token
 0.84  src/jobs/retry.py:22           _run_once
 0.79  src/db/pool.py:57              _reconnect
 0.52  src/utils/cache.py:19          get                (below 0.75)

 4 hits >= 0.75 out of 1,842 functions
```

`every` is grep whose pattern is a question. It is **not** embedding search: it does not
find code *similar to* your words. It judges the question against **every function** and
returns the probability that the answer is yes.

It runs on [TypeSafe AI's Jev](https://typesafe.ai), a model that returns typed decisions
with probabilities instead of generating text. That is what makes judging 5,000 functions
cost about seven cents and take about fifteen seconds (measured: 1,302 functions of
`gin-gonic/gin` in 3.7 s for $0.018).

## Install

```
pip install every-cli          # installs the `every` command
export TYPESAFE_API_KEY=...      # PowerShell: $env:TYPESAFE_API_KEY="..."
every --selftest                # 20 labelled functions, one request; prints recall / false positives / AUROC
```

### No Jev access yet?

`every` needs a Jev API key. If you don't have one, **join the hosted-tier waitlist:**
https://github.com/sufianetaouil/every/discussions/1 — enough signups and we build the
hosted version (no key, no setup). Meanwhile, `examples/recorded/` has real runs you can read.

## What leaves your machine

The source of every function in the files `every` scans is sent to TypeSafe's API
(`api.typesafe.ai`) to be judged. Nothing else is sent. The local cache
`.every/cache.json` stores only `sha256(question, unit text) -> score`, never source.
Don't point `every` at code you can't send to a third party.

## Usage

```
every "<question>" <path> [--above 0.75] [--top 20] [--json] [--yes] [--no-cache]
```

Questions that work well are about **one function at a time**:

- "builds SQL by string concatenation"
- "reads request data without checking authentication"
- "returns a user record that still contains the password hash"
- "is a test that doesn't assert anything"
- "retries in a loop with no upper bound"

`every` classifies your question first. If it needs a function's callers and callees, it
includes them. If it needs whole-program data flow, results are marked
`coverage: partial` — it will not pretend.

`--json` (automatic when piping) prints `{"results": [...], "meta": {...}}`; `meta` has
tokens, cost, requests and timing. Scores are cached in `.every/` so a re-run or a
refined question only pays for what's new.

## Languages

Function-level: Python, JavaScript, TypeScript/TSX, Go, Java, Rust, C#, Ruby, PHP.
Other source files (C/C++, Kotlin, Swift, Scala, shell, SQL, …) are judged as 150-line chunks.

## How it works

1. `tree-sitter` splits the repo into functions.
2. Each function goes into **its own** Jev question (never a shared list — positional
   lookup degrades past ~16 items; embedding per question is flat to 128+).
3. ~110 questions per request, 4 requests in flight, ~$0.00001 per function
   (~300 input tokens each, measured on `psf/requests` and `gin-gonic/gin`).
4. Scores are ranked; anything within ±0.10 of the threshold is asked again and averaged.

Measured against the bundled labelled set (`every --selftest`, 10 functions that swallow
errors, 10 that don't, live `jev-latest` on 2026-09-16): **recall 10/10, AUROC 1.000**;
positives scored 0.82–0.98, negatives 0.05–0.29 — except one deliberately borderline
negative (a retry loop that discards every failure but the last) at 0.68. The default
`--above 0.75` sits in that gap. This is 20 hand-written functions, not a benchmark; it
shows the model separates the two sets, not how it will score your question.

## Limits, honestly

- One function at a time. Cross-file questions get callers/callees; whole-program
  data flow is out of scope for v1 and is labelled partial.
- The ranking is the reliable part; the absolute numbers move with the question. Broad
  questions ("makes a network request") put most of an HTTP library above 0.75; narrow
  ones put a handful. Read the top of the list and set `--above` from that.
- No explanations. Jev returns a probability, not a sentence.

MIT.
