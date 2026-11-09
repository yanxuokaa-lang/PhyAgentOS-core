# jev_playground

Measure what Jev can actually do before you build on it.

![What this lane has proven so far](visual/hero.jpg)

## TL;DR

**We set out to wire Jev into omp and shipped FOUR REGEXES WITH NO JEV CALL IN THEM.**
Five surfaces, five cheap wins (cost-benefit, not capability)
([ruling](docs/demos/upstream-repro/RULING-authored-vs-real-20260919.md)): (1) a two-line
domain regex on phishing, **+27 points**; (2) flat mid-tier pricing on routing — Jev
**+90.2% more expensive**; (3) prompt length on tier choice, **2 of 3** sessions; (4)
keep-everything on compaction, **7× fewer mistakes**; (5) four regexes on tool-call harm.

**The fifth is the cleanest.** Held-out split, corpus neither scoring pane authored:
the shipped rule has recall **12/12** and FP **0/38** on the committed corpus —
`node work/omp-harm-rule/verify-claim.mjs` exits 0
([receipt](docs/demos/upstream-repro/harm-rule-claim-repro-20260919.md)).
**Do not say 0/40 for the rule** — that denominator is unreproducible
([R34](NEGATIVE_EVIDENCE.md); two benign cases were never committed). Live Jev
**11/12**, historical FP **0/40** (misses r3, `git push --force origin main`); a
dumber keyword list **5/12**, historical FP **0/40**. The FP column is **not**
like-for-like. Ship the classifier; drop Jev from `tool_call`
([head-to-head](docs/demos/upstream-repro/toolcall-headtohead-20260919.md)).
**Jev was not bad** — 11/12 is strong in isolation. Cost-benefit, not capability.

**Five-link chain — only what this tip can verify.** Links 1–4 are lab/corpus
receipts. Link 5 is **NOT VERIFIABLE** as working-dogfood.

1. **earns** — 12/12, FP **0/38**, verify-claim exits 0
   ([harm-rule-claim-repro-20260919.md](docs/demos/upstream-repro/harm-rule-claim-repro-20260919.md)).
   Historical **0/40** is unreproducible; **NO-CLAIM** on the missing two.
2. **registered** — `extensions:` list, loader glob `*.{ts,js}`; lab `jev-lab`
   ([harm-rule-shipped-20260919.md](docs/demos/upstream-repro/harm-rule-shipped-20260919.md)).
3. **fires** — both directions on luna and sol in lab
   ([harm-rule-shipped-20260919.md](docs/demos/upstream-repro/harm-rule-shipped-20260919.md)).
4. **fires correctly (lab)** — **0/17** unique-command divergence vs the frozen scorer
   ([harm-rule-conformance-20260919.md](docs/demos/upstream-repro/harm-rule-conformance-20260919.md),
   `bb4fa4f`). Lab shapes ≠ every profile.
5. **working-profile dogfood — NOT VERIFIABLE / OPEN.** Receipt
   [harm-rule-promoted-20260919.md](docs/demos/upstream-repro/harm-rule-promoted-20260919.md)
   (`6c9c8fc`) **exists on this tip**. It is one driven first-contact probe, not
   multi-row live logger traffic on a working profile. **Do not publish RUNS ON
   REAL WORK.** Organic precision is unmeasured
   ([harm-rule-realtraffic-20260919.md](docs/demos/upstream-repro/harm-rule-realtraffic-20260919.md)).
   Jev ledger **0 promoted**.

**Silent-register rule.** A module with valid syntax and no `pi.on` never fires —
indistinguishable from a hook that sees nothing. The co-presence bar is observer
decisions next to a bridge row in the same session
([harm-rule-shipped-20260919.md](docs/demos/upstream-repro/harm-rule-shipped-20260919.md)).
Observer **(B) id-join is a mechanism MET at n=1 lab** (`a2e2035`;
[omp-jev-observer-id-join-20260919.md](docs/demos/upstream-repro/omp-jev-observer-id-join-20260919.md)):
`toolCallId` stored; defaulted `context.dcgVerdict` deleted from the makeRecord
path. Residual: `createObserver` / `installObserver` still defaults
`context.dcgVerdict ?? 'unknown'` on the gate path. **Working-profile dogfood
OPEN.** Do not publish working-dogfood
([`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md)).

**22 Jev repos appeared in launch week. We ran all of them; everything passed, and that proved
nothing.** Substituting a well-formed RANDOM judge left 254 of 305 tests green (83%)
([receipt](docs/demos/upstream-repro/random-judge-substitution-20260919.md)), and exactly one
test across six repos scores Jev against a label it did not supply (same receipt). A suite that
passes a coin flip is plumbing, not validation.

**So we built oracles instead: preregistered bars, data we did not author, seven candidates.**
Three were measured both ways and all three fell the same direction: authored success,
real-data miss: a gate at 0/20 false positives authored vs 3/20 held-out, foreman supervision
at AUC 1.000 on vignettes vs 0.750 on 186,449 real windows, jev-review at 12/12 authored pairs
vs AUC 0.625 on 22 real diffs
([ruling](docs/demos/upstream-repro/RULING-authored-vs-real-20260919.md)).

**Under the finding sits the finding: prevalence decides deployability.** 30 stuck windows in
186,449 is 0.016%. At that base rate the measured separator implies ~1 false alarm per 2,300
true catches at any threshold that catches anything
([receipt](docs/demos/upstream-repro/foreman-supervision-adoption-20260919.md)). Nobody publishes
a base rate next to their accuracy, including us until this week: eight ledger rows now carry one
([receipt](docs/demos/upstream-repro/prevalence-retrofit-20260919.md)).

**A second prevalence, now public, on the tool_call surface we would actually gate.** Error
rate on allowed commands is **3.95%** (frozen split **4.01%**) — **40×** the 0.1% kill line —
on **216k** dcg decisions, frozen split **36,955** train / **41,500** held-out, zero API
([receipt](docs/demos/upstream-repro/toolcall-groundtruth-corpus-20260919.md)). Join yield is
**36.8%**; the miss class is `js-bash-<uuid>` foreign ids, so a logger must capture command
text at decision time. Pane 3 withdrew the revert-predicate as INVALIDATED; `isError` survived.
Fail-open is verified at `dcg-guard.ts:599-610`. Lab observer: session
co-presence **MET** (10 sessions); id-join **mechanism MET at n=1**
(`a2e2035` stores `toolCallId`; 1 nonempty id, 1 join; defaulted
`context.dcgVerdict` deleted from the makeRecord path). Residual:
`createObserver` / `installObserver` still defaults
`context.dcgVerdict ?? 'unknown'` on the gate path. **Working-profile
dogfood OPEN** — no multi-row live logger on a working profile. Do not
fold that into the harm-rule win. See
[`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

**What Jev IS good at, stated fairly.** Ties a TF-IDF classifier trained on ~14,800 in-domain
labels at zero labels (McNemar p=0.677), holds 0.97–0.99 under shift where that classifier
collapses to 0.70 ([receipt](docs/demos/upstream-repro/judgment-quality-20260919.md)); 96.5% on
prompt injection with context
([receipt](docs/demos/upstream-repro/jev-sec-bench-20260918.md)); beats skillranker's
always-abstain control 5× on their own corpus
([receipt](docs/demos/upstream-repro/skillranker-corpus-measured-20260919.md)).

**Scoreboard, present tense:** 25 verdict rows (7 cleared, 9 held, 8 ruled out, **0 promoted**),
31 dead-end ledger entries each with a reopen condition, 12 gate stages green. Tool_call
**RULE WINS** — ship the classifier, drop Jev (cost-benefit). Observer (B)
mechanism MET at n=1 lab; working-profile dogfood **OPEN**. Proven vs WIP seams:
[`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md). The product is the
ruling plus the evidence for everything ruled out.

**What you get.** Three tools that run offline with no API key, and read your own logs:

| Tool | Answers | Verdict it produced |
|---|---|---|
| [`demos/usage-shape`](demos/usage-shape) | Which token lever is worth attacking? | 98.878% of tokens are re-sent context |
| [`demos/routing-backtest`](demos/routing-backtest) | Would a cheaper-model router have paid? | 0.0447%. Candidate ruled out |
| [`demos/retransmit-whatif`](demos/retransmit-whatif) | How much is the top lever worth? | Upper bound only, with residual |

**The table above is reproducible on your own machine in about 20 seconds.** On a corpus of 4,619
real agent sessions, context retransmission dominates and model output is 0.140% of tokens, which
kills three whole classes of cost intervention on that workload before anyone writes code.

## What we learned about using Jev

Seven findings from live calls against `api.typesafe.ai`, each with what it means for the next
implementation. Every one is measured here, and the limits are stated because most of them cost us
a retraction to learn.

- **The measurement is the asset, not the model's prior.** Given a measured usage shape in its
  state, Jev derives the consequence that follows from it. Withhold that shape and ask the same two
  questions, and the verdict flips: `router_pays` moves from 0.21 to 0.59 and the lever it picks
  drops from 0.75 to 0.49 confidence. **Apply it by spending the effort on the measurement and
  giving Jev the state; a judgment model does not discover the lever for you.**
- **Framing leaks through the criteria, not just the state.** A criterion worded
  *"reduce the number of turns, since each re-sends the whole context"* teaches while it asks. The
  answer then tracks your implication rather than the evidence. **Apply it by stripping rationale
  out of criterion text, and by running the same question with your evidence withheld as a control.**
- **Output moves on state content that has nothing to do with the question.** Adding three
  provenance fields to a request shifted `noul` from 0.26 to 0.36 with the question unchanged.
  **Apply it by pinning the exact request bytes and versioning them, the way you would a prompt.**
- **Agreement from a model shown your own summary is same-origin and counts once.** It is not
  independent confirmation, however much it reads like it. **Apply it by treating concurrence as a
  consistency check on your reasoning, never as a second source.**
- **A handful of calls characterises nothing.** Across three runs with three slightly different
  states the same question returned 0.21, 0.26 and 0.36. **Apply it by putting the bar in the tool
  rather than in a caution.** The A/B harness here refuses a relative verdict until an arm has at
  least ten zero-spread samples (`compaction/ab/verdict.ts`), `--verdict` exits 2 below that bar, and
  twenty-one historical citations of single-run verdicts are annotated as retracted rather than
  quietly left standing.
- **The typed surface is the reason to use it.** Requests are `{model, state, questions}` with
  `noul` for a probability and `choice` for a ranked set, and both admit a real none-equivalent.
  That is what makes an abstention expressible instead of inferred from a low score. **Apply it by
  designing the question so "none of these" is a first-class answer.**
- **It is fast and cheap enough to run on every item.** Measured 743 to 773 ms per call at 523 to
  629 input tokens. An independent public write-up reports 0.35 to 0.52 s medians against 1.68 to
  4.85 s for a general model at comparable agreement. **Apply it where per-item judgment was
  previously too slow or too expensive to attempt, and not where a deterministic rule already
  works.**

The full retraction, with both sides of the framing test, is in
[`docs/demos/jev-probe/NOTE-framing-leak.md`](docs/demos/jev-probe/NOTE-framing-leak.md).

### The twenty-two upstream Jev repos: what each one tests, and where we are

These are cloned in this tree and gitignored. They are **not ours**: they are TypeSafe's and the
community's, and each already asks a question we would otherwise re-ask badly. Derive the list with
`for d in */; do [ -d "$d/.git" ] && echo $d; done`; the purposes below are quoted from each repo's
own README, not inferred from its name.

`RUN` means we executed it here and compared its output to its claims. `BLOCKED` names the
obstacle. Everything else is untouched, which is the honest state.

|Repo|The question it answers|State|Next action|
|---|---|---|---|
| `jev-spam-eval` | does a plain-English question beat a classifier trained on labels | **RUN** — both headlines reproduce ([receipt](docs/demos/upstream-repro/lingspam-20260918.md), [OOD](docs/demos/upstream-repro/jev-spam-eval-ood-20260918.json)) | fetch the other three datasets; check the out-of-distribution claim |
| `jev-rerank-bench` | can Jev rerank thirty search results usefully | **RUN** — headlines reproduce; two scripts crash ([receipt](docs/demos/upstream-repro/jev-rerank-bench-20260918.json)) | raise `nevir` beyond one run; upstream report filed for the crash |
| `jev-phishing-bench` | Jev against LLMs on phishing, with a stated **net floor** | **RUN** — floor reproduces exactly ([receipt](docs/demos/upstream-repro/phishing-20260918.md)) | the LLM comparison arms need an Anthropic key we do not hold |
| `s1-rs` | typed System One decisions in Rust, `examples/triage.rs` offline | **RUN**: both examples, offline, via a linux/amd64 container ([receipt](docs/demos/upstream-repro/s1-rs-20260918.md)) | the blocker was a platform mismatch, routed around; `RCH-E327` is still unfixed upstream |
| `jev-router` | per-turn model routing for Claude Code and Codex | **RUN** (pane 3): 58/58 ([receipt](docs/demos/upstream-repro/router-savings-inverts-20260919.md)) | upstream owns routing; ours narrows to the `blockedBy` histogram |
| `jev-sec-bench` | blind security benchmarks | **RUN**: Go TUI builds and renders; 3 committed result sets | it replicates our framing-leak effect at n=662, with the opposite lesson ([receipt](docs/demos/upstream-repro/jev-sec-bench-20260918.md)) |
| `jev-agent-failure-benchmark` | can a cheap decision model find what broke an agent | **RUN**: 20/20 with `uv run --extra dev pytest` ([receipt](docs/demos/upstream-repro/agent-failure-benchmark-20260918.md)) | its leakage test is one of the two that silently skip on a fresh clone |
| `jev-ultrafast` | a browser agent driven by Jev | action-choice smoke run: 20/20 top-1, 0/10 false advance, $0.0003 ([receipt](docs/demos/upstream-repro/jev-ultrafast-action-choice-20260919.md)) | class A only; live browser path still unrun |
| `fast-jev-compaction` | continuous context compaction with Jev | **RUN**: 29/29 tests; live run 21 messages to 7, 87.1% chars saved ([receipt](docs/demos/upstream-repro/compaction-retention-oracle-20260919.md)) | it owns the core; ours keeps only the omp adapter and replay harness |
| `jev-review` | Jev for code review | **RUN**: 13/13 offline, zero skipped ([receipt](docs/demos/upstream-repro/jev-review-real-diffs-20260919.md)) | it already ships the refusal-to-score state we had to retrofit into our gates |
| `typesafe-sdk-js` | the JavaScript client we and everyone else calls Jev through | **RUN** — 189/189 pass with 8 unhandled errors; timeout crash has a committed repro ([repro](docs/demos/upstream-repro/sdk-js-timeout-crash-repro.mjs)) | report upstream |
| `typesafe-sdk-python` | the Python client and control for the above | **RUN** — 534 pass / 50 skipped, zero errors ([receipt](docs/demos/upstream-repro/sdk-python-20260919.md)) | evidence that the JS leak is a defect |

Rows with unsupported numeric state were removed rather than preserved as numbers without a committed reproduction or receipt. See the P2-27 claim-disposition audit for the deletion decision.

**What running one actually taught us.** On Ling-Spam a question with **no labels** scores 0.9857
and a TF-IDF classifier with **2,300 labels** scores 0.9941, and their errors are mirror images:
the question makes 2 false negatives and 39 false positives, the classifier makes 40 and 1. An
elaborated *"structured criteria"* question scored **worse** than the plain one, 0.9701 against
0.9857, so elaboration is not free. Averaging the question with the classifier beats both at 0.9983.

**Elaboration costs accuracy in two of three paired tests, and the third is only directional.** Across
three comparisons on two corpora, with exact McNemar on the paired cases:
Ling-Spam plain 98.57% against structured 97.01% (**-1.56pp, p=1.4e-9**); modern mail category 97.00%
against urgency-and-authority criteria 96.68% (-0.32pp, **p=.50, directional only**); and a
**names-only** question at 98.58% against category 97.00% (**+1.58pp, p=.0064**), the shortest
question winning outright. This is a **confirmation, not a discovery**: `jev-spam-eval`'s own README
already notes its headline came from a question *"written after reading the mistakes in 1,000 sampled
emails"*, which is the same effect seen from the tuning side. Falsifier, stated by its author:
pre-register the prompts, use a fresh held-out source, and test paired; the inversion must vanish or
reverse consistently.
[`docs/demos/upstream-repro/criteria-inversion-20260918.md`](docs/demos/upstream-repro/criteria-inversion-20260918.md)
Receipt:
[`docs/demos/upstream-repro/lingspam-20260918.md`](docs/demos/upstream-repro/lingspam-20260918.md).

**What asking outside changed, and it is not flattering.** TypeSafe's own dashboard puts Jev at
**67.8% aggregate against 74.1% for the best comparator**, and **61.8% against 79.1%** on invoice
processing. Nothing this lane had written about Jev mentioned that it trails on aggregate. Any claim
here about where Jev wins has to sit beside that.

**The gap worth taking, from an independent benchmark.** `jev-benchmark` scores Jev at 91.7% on agent
tool-call risk with **ECE 0.0505**, and its author states plainly that two model versions are *"not
separable at this sample size"* (n=60). Re-analysing their shipped results shows why the question is
still open: **confidence is exactly `1.000` on 40 of 60 cases**, with 0 of 5 misses landing there. So
the confidence is honest where it saturates and carries almost no signal to route on, and settling
that needs a larger n than anyone has run. That is a concrete improvement on published work, in our
own domain.

**A stranger-readable summary of every upstream run lives at
[`docs/demos/upstream-repro/README.md`](docs/demos/upstream-repro/README.md)**: one line per repo,
each linked to the receipt that produced it.

**Four of twenty-two are now run, and running them produced things we could not have produced
ourselves.** `jev-rerank-bench`'s headline reproduces from its committed cache (Jev rubric 0.692
against Cohere Pro 0.691, inside noise at p=.910), while a fresh `nevir_eval` over 1,383 pairs gives
Jev **+4.2 points at p=.002**: one benchmark, one result inside noise and one real. Its
`determinism.py` and `batching.py` crash with a `KeyError` naming a document id when the actual cause
is an absent corpus file, reported at
[`docs/upstream/jev-rerank-bench-missing-docs-file-reads-as-empty.md`](docs/upstream/jev-rerank-bench-missing-docs-file-reads-as-empty.md)
rather than patched. `jev-phishing-bench`'s keyless floor reproduces exactly.

**The rule that produced:** run the upstream question before writing our own. Nineteen of the
twenty-two sat untouched while this lane built and re-graded demos of its own, and the first one run
returned a reproducible finding in ten minutes.

## What you can run

Each tool takes one command, reads your own logs, and writes a receipt that states its denominator
before any share. No API key. No network.

## The omp extensions

Six installable omp packages, each mined from one upstream Jev repo. Every one is
**observe-only**: it writes a decision row and changes nothing the agent does. The column that
matters is the last one — whether a model call earns its place on that surface, decided by
measurement rather than preference.

| extension | mined from | offline tests | live-proven | calls Jev? |
|---|---|---|---|---|
| [`omp-harm-rule`](work/omp-harm-rule/) | the tool_call corpus | 12/12 recall, 0/38 FP | yes, working profile | **no** — four regexes beat it 12/12 to 11/12 |
| [`omp-jev-preaction`](work/omp-jev-preaction/) | `preaction-abstention` policy | 6/6 incl. a false-positive arm | yes, `jev-lab` | **no** — deterministic patterns only |
| [`omp-jev-observer`](work/omp-jev-observer/) | the observe-and-log seam | 7/7 | yes, `jev-lab` | yes |
| [`omp-jev-review`](work/omp-jev-review/) | `jev-review` | 6/6 | yes, `review_scored` | yes — no regex for "this refactor changed a default" |
| [`omp-jev-rerank`](work/omp-jev-rerank/) | `jev-rerank-bench` | 7/7 | yes, `{ordered: 0.91}` | yes, **one** question — measurement killed the other two |
| [`omp-jev-failure`](work/omp-jev-failure/) | `jev-agent-failure-benchmark` | 5/5 | yes, `failure_classified` | yes, **one** multiclass question — chosen for coherence, NOT accuracy: on 9 fresh hold-out cases both framings tied 8/9 and the impossible-answer defect did not reappear |

Eleven more `omp-jev-*` taste packages exist under [`work/taste-loop/`](work/taste-loop/) as
**unpromoted observe-only scaffolds**. They are not in the table above: not wired to working
profiles, not live-proven, not promoted. See [Status](#status).

Two of six contain **no model call at all**, and that is the most useful thing this lane has
produced. The harm gate was decided by putting four regexes, a live model and a dumb baseline on
the same held-out split and reading the result: the regexes won by one recall point at zero cost
and zero latency. A judge earns its seat where a rule cannot be written — and nowhere else.

All six share one typed caller, [`work/jev-client`](work/jev-client/), because every hand-rolled
request body in this repo was wrong at least once (`{questions: […], context}` → HTTP 400;
`.probability` instead of `.noul` → undefined). The API key lives in Infisical; see
[`.env.example`](.env.example) for the exact command, because "the key is missing" was reported
three times and was wrong three times.

### `work/omp-harm-rule/` — the model lost, so we shipped the regexes

```bash
work/omp-harm-rule/install-harm-rule.sh --check default   # verify without writing
work/omp-harm-rule/install-harm-rule.sh default           # install into an omp profile
```

Four regular expressions that flag destructive-shaped bash commands, logged and never blocked.
**It contains no Jev call.** We built it by putting a language model and a dumb baseline on the
same task, scoring all three on a held-out, time-ordered split of 216k real tool decisions, with
the scoring done by a pane that authored none of them:

| | recall | false positives | can you re-run it? |
|---|---|---|---|
| **deterministic rule** | **12/12** | **0/38** | recall **yes**; FP **yes, committed corpus** |
| Jev | 11/12 | 0/40 | **no** — needs a live model |
| dumb baseline | 5/12 | 0/40 | recall **yes**; FP **historical only** |

**The rows do not share a denominator.** The rule's `0/38` is what a committed corpus supports
today; the historical rows were scored against 40 benign cases, two of which are now lost. So
this table is *not* a like-for-like false-positive comparison any more, and the recall column
(12/12 vs 11/12 vs 5/12) is the part that still compares cleanly.

~~~bash
node work/omp-harm-rule/verify-claim.mjs      # exits 0, 12/12 recall and 0/38 FP
~~~

The verifier imports the shipped rule and reproduces the committed **12/12** positive and **0/38**
benign result. The original **0/40** denominator is not recoverable: two historical benign cases
were never committed. We publish the smaller denominator rather than reconstructing them silently.
Receipt: [harm-rule-claim-repro-20260919.md](docs/demos/upstream-repro/harm-rule-claim-repro-20260919.md).

A mutated copy of the rule (777 -> 778) drops recall to 10/12, proving the verifier detects
rule breakage. The Jev and dumb-baseline rows remain historical measurements, not offline reruns.

The recall column is real and you can check it now; a mutated copy of the rule (`777`→`778`)
drops it to 10/12, which is how we know the harness detects a broken rule rather than always
agreeing.

One recall point, at zero cost, zero latency and zero network. That is the whole reason the model
is not in the shipped artifact — and it is the fifth surface in this repo where the cheap thing
matched or beat the model.

It is observe-only **by construction**, which you can check rather than trust:

```bash
# prints a reassuring line and exits 0 when the file is clean
grep -qE '\b(block|deny|abort|reject)\b' work/omp-harm-rule/harm-rule.ts \
  && echo "FOUND a block path" || echo "observe-only: no block path"
```

Two things about that command, both learned the hard way on a fresh clone:

- **`grep -c … # 0` was the published form and it exits `1`.** Zero matches *is* grep's failure
  status, so our proof-of-no-block-path returned failure on success. A reader checking exit
  codes would have concluded the opposite of what the command demonstrates.
- **The `\b` and `-E` are load-bearing.** A substring form (`grep -c 'block'`) matches the word
  inside comments and reports nonzero on a file with no block path at all.

Both were found by running, not reading — the first on a fresh clone by pane 2, the second by
pane 3 while grading the installer.

The installer backs up your `config.yml` before touching it, never overwrites that backup on a
re-run, and prints the exact rollback line. Every decision row it writes carries the command it
judged, so a fire is always quotable — we learned that the hard way and
[retracted a published claim](NEGATIVE_EVIDENCE.md) that said otherwise.

Installed is not firing. After some real work:

```bash
grep -rho '"kind":"harm_[a-z]*"' ~/.omp/profiles/default/agent/sessions/ | sort | uniq -c
```

You will see three kinds, and the third one exists because of a defect we shipped:

| kind | meaning |
|---|---|
| `harm_pass` | the rule ran and matched nothing |
| `harm_fire` | the rule ran and matched |
| `harm_error` | **the rule could not run** — no score is recorded |

Until `6f3ac8f` there were only two. A classifier that threw produced `score: 0`, which the
`>= 0.5` test read as **`harm_pass`** — a crash was recorded as a command measured and found
safe, and every count we publish buckets on `kind`. We found it by auditing the one published
surface where such a default could reach a reader, and then measured the damage rather than
assuming it: **54 rows audited, 0 contaminated**; on the working profile, 32 decision rows with
**0** non-null errors. It had never fired in production. If you are counting rows, count
`harm_error` separately — it is neither a pass nor a fire.

On our own machine the live fires so far are **all self-generated probe shapes**
(`chmod -R 777 /etc/nonexistent-*`), so we claim no precision figure from live traffic yet: n=16
with our own test commands in it supports no interval in either direction.

### `ensemble/` — should you average two scorers, or just use the better one?

```bash
python3 ensemble/run_all.py
```

Runs in about a second. Needs one upstream clone first, because this repo does not redistribute
their 5.7 MB of scores, and the script prints the exact `git clone` if it is missing. Averaging
two scorers is folk wisdom;
these four pairs show when it pays and when it costs you:

| pair | phi (error correlation) | accuracy gap | averaging gained |
|---|---|---|---|
| plain question + logistic regression | +0.035 | 0.0 pp | **+1.25 pp** |
| Jev + TF-IDF (phishing, n=5,733) | +0.107 | 4.2 pp | **+0.38 pp** |
| with-context + without-context (n=662) | +0.343 | 6.8 pp | **-0.60 pp** |
| logistic regression + naive Bayes | **+0.526** | 0.8 pp | **-0.14 pp** |

**Two conditions, not one.** Averaging paid only when the scorers failed on *different items* and
were *close in accuracy*. Row three is the one that cost us a published rule: phi well under 0.5,
and it still lost: no amount of decorrelation at 9% disagreement beats a 6.8-point accuracy
gap. Point `ensemble/decorrelation.py` at your own two scorers before you build the ensemble.

Four points do not locate a boundary, and [`ensemble/README.md`](ensemble/README.md) says so at
more length than this summary does.

### `compaction/` — a context-compaction hook for omp, and what it actually saves

Install it into any repo and omp asks it before compacting a session
([`compaction/README.md`](compaction/README.md) has the three commands). Measured by replaying
**real transcripts omp wrote during real work**, not fixtures, all passing six invariant checks:

| session | tool calls | requests | chars before → after | saved |
|---|---|---|---|---|
| a small one | 10 | **0** | 44,819 → 44,819 | **0%** |
| `UdsFeatureUnion` | 9 | 1 | 155,837 → 104,443 | 32% |
| `MirrorAgentsSurvey` | 15 | 1 | 249,949 → 188,661 | 24% |
| `OmpExtensibility` | 15 | **0** | 253,465 → 253,465 | **0%** |
| `PortFleetComposite` | 108 | 1 | 501,502 → 6,084 | **98%** |
| `PortOmpIdleDispatch` | 98 | 1 | 291,909 → 12,911 | **95%** |

**Not a rate. The shape is LENGTH.** A third of the sample saved nothing because
everything in those sessions was pinned: a call is protected when it or its result sits in the
last six messages, so a seven-message transcript is untouchable no matter how many tools it ran
(`OmpExtensibility`: 15 calls, all 15 pinned). Measured across **1,653 real sessions** at default
settings: **1,415 (86%)** have at least one call the hook could ask about, **98 (6%)** are
entirely pinned, **87 (5%)** exceed Jev's state budget. Six sessions is a sample, not a
distribution.

Run it against your own history:

```bash
npm --prefix compaction run replay -- ~/.omp/**/agent/sessions/**/<a session>.jsonl
```

**The hook has never reduced a live session.** Every firing in a running omp has returned
passthrough, because the only way we could force one on demand produced a transcript with no tool
calls. The numbers above are the replay harness on real data, which is the strongest evidence
available and is not the same claim.

### `demos/usage-shape` — where does your agent spend go?

```bash
node demos/usage-shape/bin/shape.mjs ~/.claude/projects
```

`~/.claude/projects` is where Claude Code keeps session logs. If you do not use Claude Code, pass
your own `.jsonl` files or a directory of them; the tool takes either and reports how many files and
sessions it actually read.

Measured on one machine, 2026-09-18, over 4,626 files / 4,619 sessions / 488,724 billed turns,
models `claude-opus-5` (408,265 turns), `claude-opus-4-8` (49,842), `claude-fable-5` (15,658) and six
others:

| Share of tokens | Lever | Reduce it by |
|---:|---|---|
| **98.878%** | retransmitted context (cache read) | fewer turns, or less parked in context |
| 0.980% | context first-write | reading less into context at all |
| 0.140% | model output | asking for less output |
| 0.002% | fresh input | shorter prompts |

Mean context re-sent per turn: **341,496 tokens**. Those four figures are **measurements** over the
stated corpus, re-derivable by the command above, and the run that produced them is committed at
[`docs/demos/jev-probe/census-20260918.json`](docs/demos/jev-probe/census-20260918.json) with its
own denominator and skip counts. A reviewer looked for it under `demos/usage-shape/runs/` and found
nothing, which is fair: the receipt was real and undiscoverable from the tool's own directory.

A separate and weaker claim: weighting them by *assumed* relative rates (cache read 0.1x input,
output 5x input) puts retransmission near **84% of cost**. That is an **estimate under assumed
rates, not a measured bill**. The rates are unattributed here and no invoice was observed. It is
labelled because a reviewer caught it sitting beside the measurements with no class distinction,
where it read as measured fact.

### `demos/routing-backtest` — would a cheaper-model router have paid?

```bash
cd demos/routing-backtest
npm run backtest -- fixtures/real-excerpt-t1-t6.jsonl --out runs/try.json
```

On 30 classifiable turns it measured **0.0447%** savings, and the candidate was **ruled out**. The
verdict is scoped on purpose: it answers *same-turn price substitution*, not turn elimination.

21 tests, and **7/7 planted mutations caught**. Three of those were real holes found under a suite
that was already green, one of them directly beneath the published figure. Reproduce that claim with
`npm run mutate`: it plants seven named mutations one at a time, requires the baseline green first,
restores every file and compares by sha256, and exits non-zero if any mutation survives.

### `demos/retransmit-whatif` — how much is the top lever worth?

An upper bound on per-turn retransmission reduction, with an explicit residual row that reconciles
to zero, and its assumptions stated in both README and receipt: a reduction removes `cacheRead * r`
only, while turns, model behaviour, retrieval quality and tool behaviour all stay unchanged.

A reviewer graded it **rung-2 fail as a demo** ("deterministic calculator; no judgment model
needed") and kept it as an instrument. Its bound does **not** cover turn elimination. Citing it as
though it did would repeat the exact scoping defect the backtest already made once.

## Install

~~~bash
git clone https://github.com/JYeswak/jev_playground.git
cd jev_playground
# Maintainer-only: fetch primary mirrors; readers can skip this block for offline tools.
./scripts/sync-docs.sh          # fetches the primary sources; safe to re-run
./scripts/sync-docs.sh --check  # verifies every mirrored byte against MANIFEST.tsv
~~~

No API key needed to install, and none to run any tool above.

## What it does

- Mirrors the primary Jev sources locally, so every claim here cites bytes you can re-fetch
- Adjudicates candidate ideas against a rung ladder, and records the ones that die
- Ships the measurement tools that killed them, so you can re-run the kill on your own data
- Keeps a dead-end ledger with a reopen condition on every entry

## How it works

Each candidate climbs a rung ladder. A candidate that fails a rung is ruled out with a receipt, and
the reason lands in [`NEGATIVE_EVIDENCE.md`](NEGATIVE_EVIDENCE.md) together with the condition that
would reopen it. `docs/demos/STATUS.tsv` is the machine-readable state of record, one row per
candidate, and `./scripts/lane-status.sh` exits non-zero if any verdict cites a receipt that does
not exist.

Claims carry a class. A measurement over a stated corpus, a benchmark on a stated denominator, a
statistical mean, a negative-control result and an estimate under assumed rates are five different
things, and mixing them is how a number gets believed harder than it earned.

## Quick start

Three commands from a stranger clone. No API key.

```bash
git clone https://github.com/JYeswak/jev_playground && cd jev_playground
./scripts/quickstart.sh
bash foundation/gates.sh
```

`gates.sh` runs `scripts/bootstrap-compaction.sh` when stage 40's deps are missing (`compaction/node_modules` and the pinned `fast-jev-compaction` sibling). That step uses the network once and does not commit `node_modules`. You can run the bootstrap yourself first if you want the fetch to be visible:

```bash
./scripts/bootstrap-compaction.sh
```

Proven vs WIP OMP/Jev seams, with claim levels: [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) (**0 promoted**).

Then the five questions, from committed bytes:

```bash
./scripts/quickstart.sh
```

```
quickstart: five questions, answered from committed bytes. No install, no network, no API key.

=== Q1. Would routing cheap turns to a cheaper model have saved money?
    NO. On this fixture routing would have COST YOU MORE: $0.011106 actual
    vs $0.012933 routed — 16.4% worse, on 6 of 6 turns.

=== Q2. Can that demo's tests still fail, or are they decoration?
    YES — mutations: 7/7 caught.

=== Q3. How much of a coding agent's context is resent every single turn?
    98.878% of all tokens are cache reads: context resent, not new work.
    Denominator, stated: 488,724 turns across 4,619 sessions in 4,626 files, 0 unparsable.
    Basis matters here: 98.878% against all tokens, 99.017% against billed input only.

=== Q4. Which lever is that spend actually in, and does the accounting close?
    cacheRead: 80.1% of 1,013,018 tokens over 18 assistant turns.
    Unreconciled: 0 tokens.

=== Q5. What does a Jev judgment actually look like?
    top_lever: chose "fewer_turns" at confidence 0.7
      fewer_turns      0.78
      shorter_prompts  0.15
      cheaper_model    0.05
      shorter_output   0.02

5 of 5 questions answered.
```

**Q1 answers "no", and that is the point.** Routing would have cost 16.4% *more* on this repo's own
fixture. A runner that could only print `PASS` could never tell you that, which is exactly what the
first version of this script did, until a non-author pane graded it
`ENABLER-in-product-clothes` and named what to build instead.

**The savings figure is no longer what this demo is for.** A reviewing pane ran `jev-router` and
`jev-codex-router` (58/58 tests, plus a routing backtest on its own sessions) and ruled ours should
**narrow**: upstream owns per-turn routing, so what is worth keeping here is the **`blockedBy`
histogram**, which says *which policy constraint* stops a turn from routing, and the multi-shape
harness behind it. A savings percentage derived from our own price assumptions is the part upstream
already does better. It is retired as a claim rather than deleted as code.
[`docs/demos/upstream-repro/routers-20260918.md`](docs/demos/upstream-repro/routers-20260918.md)

Every number is derived at runtime from the receipt the tool just wrote; none is hardcoded. Every demo
is zero-dependency: no install, no network, no key, no state from this lane. Measured from a frozen
clone of a pinned commit, which is the environment the gate suite below fails in, and a receipt missing
a field the answer depends on exits 1 rather than printing a branch it did not measure.

### Answer them on your own logs

```bash
./scripts/quickstart.sh --mine              # defaults to ~/.claude/projects
./scripts/quickstart.sh --mine /path/to/logs
```

Nothing is uploaded and no key is used. On the author's machine that is 4,626 session files, and the
shape answer comes back personal: **4,619 sessions, 488,724 billed turns, 98.9% of tokens
retransmitted context, a mean 341,496 retransmitted tokens per turn, 0 unparsable lines.**

**It exposed a limit we would never have found on the fixture, and then we fixed it.** The router
backtest *could not answer* on a real Claude Code corpus: it returned `EMPTY_CLASSIFIABLE_SET`,
because those logs carry tokens and a model string but **no cost field at all**, which is what the
reader needs. Recorded as a refuted hypothesis (`NEGATIVE_EVIDENCE.md` `R20`), because the README
implied the fixture shape generalises and 4,626 real files falsified that.

It answers now, and only on rates **you** supply:

```bash
node demos/routing-backtest/bin/adapt-claude.mjs --print-price-template > prices.json
# fill in your provider's rates, then:
JEV_PRICES=prices.json ./scripts/quickstart.sh --mine
```

```
converted 47,428 of 55,794 assistant turns; 8,366 refused
  no rate supplied for claude-fable-5 (7454 turns) — add it to your sheet
  no rate supplied for claude-opus-4-8 (669 turns) — add it to your sheet
  no rate supplied for <synthetic> (24 turns) — add it to your sheet
The backtest REFUSED the converted data: NO_CHEAP_CANDIDATES: no turn qualifies for the cheap scenario
```

**That refusal is the answer, not a failure.** Under the demo's 20,000-token cheap-model budget, and
with cache creation counted toward the context a turn occupies, **not one of 47,428 turns fits** — on
a corpus where every turn carries a large cached prefix, cheap-model routing has nothing to route.

**This repo ships no rates.** Claude Code records no cost, so every dollar is *computed* from your
sheet plus two declared rules — cache multipliers, and
`context = input + cache_read + cache_creation`. A model missing from your sheet is refused and
named, never priced by guess; `<synthetic>` is not a model and gets no number. A sheet that still
carries the template's `REQUIRED:` provenance placeholders is **refused outright**, because a
computed dollar figure must name where its rates came from.

**Both declared rules were forced by failures, and the second by a non-author.** My first attempt
counted only raw `input_tokens`, every turn qualified as cheap, and the backtest rejected the run —
`NO_BASELINE_CANDIDATES`. I then declared `input + cache_read`, and a reviewing pane ruled that
incomplete: a prefix being *written* to cache still occupies the window. **Its floors fired against
the authors twice, in opposite directions.**

Then the gate suite, which is a different thing with a different answer:

```bash
bash foundation/gates.sh
```

```
PASS 10-fixture-integrity (0s)
PASS 20-receipt-freshness (1s)
PASS 30-no-secrets (0s)
PASS 40-omp-compact-replay (0s)
PASS 50-house-gates (1s)
PASS 60-staged-deletion-lane (3s)
PASS 70-tests-registry-sync (0s)
PASS 80-lane-instrument-selftests (17s)
PASS 90-sidecar-verifier-wrapper (0s)
PASS 95-numerals-ratchet (0s)
PASS 96-verdict-status-agreement (0s)
PASS 97-readme-counts (0s)
gates: ALL GREEN
```

Thirteen stages. Each has a planted bad input that turns it red, listed in [`GATES.md`](GATES.md),
because a gate that cannot fail is not a gate. Re-derive the count from `foundation/gates.d/`; a
number written here goes stale silently, and this one already did once, when it claimed seven
stages and nine existed.

**Stage 40 no longer requires a pre-seeded `node_modules`.** A fresh clone used to fail that
stage on `compaction typecheck failed`. The README's previous fix (`npm install --prefix
compaction`) is **insufficient**: `package.json` depends on `file:../fast-jev-compaction`, which
this repo does not vendor, so npm leaves a dangling symlink and `tsc` still fails. Measured
2026-09-19 on a clean public-repo checkout (`NEGATIVE_EVIDENCE.md` R32). `scripts/bootstrap-compaction.sh`
clones the sibling at the EVAL.md pin, builds `dist/` (git does not carry it), then npm-installs.
Stage 40 runs that script when the ready-check fails.

**`ALL GREEN` is still not what every stranger gets.** Stages 50 and 60 wrap foundry house
gates and need `LOOP_KIT` (default `$HOME/Developer/foundry/loop-kit`). A machine without that
kit exits 3 on stage 50 — instrument unreachable, not a content fail. The 2026-09-18
"eleven of twelve" measurement was taken on a machine that already had foundry; it understated
the sibling-clone hole and overstated how far a random clone goes green. Measure the audience
you are describing.

## Command reference

| Command | Effect | Needs a key? |
|---|---|---|
| `bash foundation/gates.sh` | every wired stage; stage 40 bootstraps compaction deps if missing | no |
| `bash foundation/gates.sh --selftest` | every stage against its planted bad input | no |
| `bash scripts/verify-frozen.sh [ref]` | runs the suites in a clone pinned to a commit | no |
| `./scripts/lane-status.sh` | renders `docs/demos/STATUS.tsv`, verifies every cited receipt | no |
| `node demos/usage-shape/bin/shape.mjs <dir>` | lever census over session logs | no |
| `cd demos/routing-backtest && npm test` | 21 tests | no |
| `cd demos/routing-backtest && npm run mutate` | 7 planted mutations, restore and compare | no |
| `node scripts/jev-probe.mjs --replay` | decodes a recorded Jev response, no network | no |
| `node scripts/jev-probe.mjs` | one live Jev call | **yes** |

The live call reads `TYPESAFE_API_KEY` from the environment and is meant to be run through a secret
manager so the key never reaches a file:

```bash
infisical run --projectId=42b194c3-89d7-4ebb-895f-dd77ddf005ba --env=prod -- node scripts/jev-probe.mjs
```

## Verify it yourself

```bash
bash foundation/gates.sh --selftest    # every stage proves it can go red
bash scripts/verify-frozen.sh          # suites run against committed bytes, not your worktree
cd demos/routing-backtest && npm run mutate
```

`verify-frozen.sh` exists because every green reported during development was measured in a worktree
that three agents were editing at once. It adds a git worktree pinned to a commit, runs the suites
there, and `cmp`s the executables. Its first run failed and found three stages that pass locally and
cannot pass from a clone, which is how the fresh-clone caveat above got measured instead of assumed.

### What a genuinely fresh clone does, measured 2026-09-19 at `fb137d2`

Pane 2 cloned the public repo to a temp dir and ran every command this README offers, taking
each exit code **unpiped**. Six returned `1`, and none of them because the thing they test is
broken:

| command | rc | why |
|---|---|---|
| `install-harm-rule.sh --check default` | 1 | actionable: create a profile/config, run `install-harm-rule.sh <profile>`, then rerun `--check <profile>` |
| the observe-only grep (old `-c` form) | 1 | zero matches is grep's failure status; the published proof now uses the `-q` form and prints a success message |
| `foundation/gates.sh` | 1 | actionable: run `br sync --import-only` from the repository root to create `.beads/*.db`, then rerun gates |
| `compaction/install-jev-compact.sh --check` | 1 | actionable: run `./scripts/bootstrap-compaction.sh`, then rerun the check |
| `scripts/sync-docs.sh` | 1 | maintainer-only mirror refresh; readers should skip it and use the offline tools |
| `scripts/verify-frozen.sh` | 1 | actionable: run `br sync --import-only` from the repository root, then rerun frozen verification |

Passing on a fresh clone: `usage-shape`, the routing backtest, the quickstart, the compaction
bootstrap, `gates.sh --selftest`, and the mutation arms.

**We are publishing the failures rather than quietly fixing the table.** Five of the six are
missing prerequisites we never told a reader about; one was a genuine defect in a published
proof. Receipt:
[`fresh-clone-readme-commands-20260919.md`](docs/demos/upstream-repro/fresh-clone-readme-commands-20260919.md).


## Mistakes we made

Four instruments on this page produced wrong numbers before they produced right ones. Each is
kept here because a repo that omits its own errors is asking to be trusted, and trust is not
on offer here — only receipts.

- **A guessed field name scored a constant and fabricated a null.** Three router runs read
  `r.answers.tier.distribution`; the field is `probabilities`, so every score was 0 and the
  AUC came back exactly 0.500 three times — which looks exactly like "no signal." The fix is
  procedural: open the installed declarations before claiming about an API
  ([SDK-SURFACE](docs/demos/SDK-SURFACE.md)), and make scorers throw on a missing field so
  silence can never again read as measurement.
- **A degenerate label returned NaN and nearly published as a finding.** A feasibility arm with
  only one class present yields an undefined AUC; the refusal path (HARNESS BLIND, no verdict)
  exists because that arm fired here, not as theory.
- **An invented gate nearly published "Jev abstains on everything."** A loss table scored a
  free-text gate at 0.750 with 11 of 12 abstentions; scored the way the product actually works
  (bounded Choice with an abstain option) the same run gives 0.167/0.800
  ([receipt](docs/demos/upstream-repro/skillranker-corpus-measured-20260919.md)).
- **A dead build was narrated as running, twice.** A backgrounded `cargo build` died with its
  parent shell while its stale log line looked like progress
  ([R29](NEGATIVE_EVIDENCE.md)). Rule since: check the process, not the log.
## Troubleshooting

| Symptom | Cause | Fix |

| `SyntaxError` or `Cannot find module` on any tool | node older than 20, or missing | `node --version`, then install node >= 20 |
| `gates.sh` red on `40-omp-compact-replay` | missing sibling clone or `compaction/node_modules` | `./scripts/bootstrap-compaction.sh` |
| `gates.sh` red on `50-house-gates` | no Beads database, only the tracked JSONL | `br sync --import-only` |
| `gates.sh` red on `70-tests-registry-sync` | a test file exists that `TESTS.md` does not name | add its entry to `TESTS.md` |
| `shape.mjs` reports 0 turns | logs are not a Claude Code or omp shape | check one file has `message.usage` keys |
| `jev-probe.mjs` exits 2 | no `TYPESAFE_API_KEY` in the environment | run it under a secret manager, or use `--replay` |
| `ERROR at least one session JSONL is required` | no input path given | pass a file or a directory |

## What you'll need

- `bash`, `git`, `curl`, `python3`, preinstalled on macOS and most Linux
- **`node` >= 20**, required by all three tools. Their `package.json` files declare it, and a
  machine without node fails every one of them, so check `node --version` first
- A `TYPESAFE_API_KEY` **only** for the one live call. Everything else runs without one

Runtimes, measured on an M3 Ultra: `foundation/gates.sh` about 16 s, of which stage 80 alone is 12 s;
`usage-shape` about 19 s over 4,626 files. Nothing here is instant and nothing here needs a network.

## Limitations

**Nothing has been promoted.** 25 verdict rows (7 cleared, 9 held, 8 ruled out, **0 promoted**).
That is the deliverable rather than a shortfall, and every reason lives in
[`NEGATIVE_EVIDENCE.md`](NEGATIVE_EVIDENCE.md), 31 entries, each carrying the condition that would
reopen it. One candidate died there because an MIT-licensed tool already ships its surface, which
is a reason to stop building and not a reason to build faster.

**Stage 40's fresh-clone hole has a bootstrap.** `scripts/verify-frozen.sh` may still fail on a
machine without foundry (`LOOP_KIT` for stages 50/60). That is an environment limit, not a missing
`node_modules`.

**The `~84% of cost` figure is an estimate under assumed rates**, and the rates are unattributed
here. A reader can check that assumed rates were used, not which multiplier.

**`98.878%` is a token share on one corpus.** It is not a cost share, not universal, and the census
cannot distinguish a non-billed record from an assistant turn whose usage block is missing. 1,247,069
records carried no usage block and were skipped, which the tool reports rather than hides.

**The `0.0447%` backtest answers price substitution on a fixed set of turns.** It says nothing about
turn elimination, which the same corpus shows is the dominant lever. Getting the order of the levers
wrong costs more than getting any single lever's number wrong, and this lane made that mistake before
it measured the shape.

**The live Jev probe measures implication-tracking, not lever discovery.** Given the measured shape
in its state it returns the same ranking the logs do; with that shape withheld, the verdict flips.
Agreement from a model shown a summary of your own evidence is same-origin and counts once.
`docs/demos/jev-probe/NOTE-framing-leak.md` carries the retraction and the numbers on both sides.

**Two instruments here gate nothing.** `verify-reason-numerals.sh` is deliberately hand-run, and its
hits require a human ruling; an unruled hit re-fires every run.

## Roadmap

Phase 1 candidate: a conformance suite shared by the three session-log readers, which currently
duplicate a parser between them. Two reader-shaped defects landed in one day, so the next design
step is one contract with its own suite rather than three parsers that agree by coincidence.

Unsupported today: any tool that reads a harness other than Claude Code or omp session JSONL. A tool
pointed at another shape reports zero turns, which is a visible result rather than a silent one.

## Status

**25 verdict rows, 0 promoted, with one promotion awarded and retracted the same day.** Foreman
supervision cleared its bar on authored vignettes (AUC 1.000 twice), then scored 0.750 on 186,449
real windows and was moved off rung 5 by its author. The retraction is the system working, not
failing. Verdicts and receipts: `docs/demos/STATUS.tsv`; reopen conditions:
`NEGATIVE_EVIDENCE.md` (31 entries).

**Open questions, honestly.** Class-D (does the agent's answer change?) is unmeasured: the
ablate-and-rerun harness is built and frozen, its model arms pending a quiet window. Two verdicts
are unsafe pending the same window. Everything else above ran.

**22 of 22 upstream Jev repositories have been run**, not read. That sweep produced the one
shipped-code defect on this page (a `typesafe-sdk-js` timeout that kills a default Node process)
and retracted four claims of our own, including a fabricated benchmark score and a "documented but
unbuilt CLI" that was really a 103-commit-stale clone.

**The compaction hook is installable and measured, and has never reduced a live session.** Both
halves are load-bearing: 98% and 95% on long real transcripts through the replay harness, and
every firing inside a running omp has returned passthrough.

Twelve gates run on every commit and are green. This repository is public and its history is
published as written, including local filesystem paths.

### Process doctrine, and eleven unpromoted taste packages

These two landings are **not** Jev capability claims and **not** promotions. Ledger stays
**0 promoted.**

**Process doctrine for agents** — not a result about Jev.
[The Ban Nobody Issued](docs/essays/dont-give-up.md) records that this lane invented
STOP-LIVE / deferred-registration / quiet-window-as-science-gate as reasons not to work.
Joshua did not issue that ban. Supporting:
[`dont-give-up-gaps.md`](docs/essays/dont-give-up-gaps.md),
[`dont-give-up-skill-patches.md`](docs/essays/dont-give-up-skill-patches.md).

**Eleven unpromoted observe-only product-taste packages.** Index
[`work/taste-loop/README.md`](work/taste-loop/README.md); contract
[`work/taste-loop/CONTRACT.md`](work/taste-loop/CONTRACT.md). They log whether an artifact
would feel usable to a client. They are **not** promoted, **not** working-dogfood, **not**
registered in any working profile, **not** validated on live traffic. Names from the tree:
`omp-jev-default`, `omp-jev-field`, `omp-jev-firstlook`, `omp-jev-fork`, `omp-jev-heat`,
`omp-jev-heckle`, `omp-jev-jargon`, `omp-jev-promise`, `omp-jev-skip`, `omp-jev-uncanny`,
`omp-jev-undo`. Heat is attention leftover, not taste; it is in the set because session
JSONL can label it.

## About Contributions

*About Contributions:* Please don't take this the wrong way, but I do not accept outside
contributions for any of my projects. I simply don't have the mental bandwidth to review anything,
and it's my name on the thing, so I'm responsible for any problems it causes; thus, the risk-reward
is highly asymmetric from my perspective. I'd also have to worry about other "stakeholders," which
seems unwise for tools I mostly make for myself for free. Feel free to submit issues, and even PRs
if you want to illustrate a proposed fix, but know I won't merge them directly. Instead, I'll have
Claude or Codex review submissions via `gh` and independently decide whether and how to address
them. Bug reports in particular are welcome. Sorry if this offends, but I want to avoid wasted time
and hurt feelings. I understand this isn't in sync with the prevailing open-source ethos that seeks
community contributions, but it's the only way I can move at this velocity and keep my sanity.

## License

MIT. See [`LICENSE`](LICENSE).
