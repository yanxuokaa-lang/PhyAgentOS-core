# Conviction

[Open the demo](https://conviction-kappa.vercel.app) · [Current state](CURRENT.md) · [Evaluation evidence](docs/comparison/validation.md)

The demo opens without a Vercel account. Live actions share a limited daily allowance; the recorded benchmark is always available. [Browse the source on GitHub](https://github.com/matiassemelman/conviction).

A small venture diligence workspace with TypeSafe Jev and a side-by-side comparison against GPT-5.6 Luna and Terra. Inspect three assumptions about a fictional startup, read the sources behind each judgment, surface conflicts and add a note to see what changes.

## How we built it

Conviction grew out of a conversation between Matias and Codex on September 16–18, 2026. Matias wanted a small MVP he could show, with minimal code and a clear structure. We chose a venture-analysis workspace: inspect a startup’s claims, preserve conflicting sources and decide what to ask next.

Matias set the direction and asked for the next capabilities as the demo took shape. Codex turned those decisions into specs, code, tests and deployments. Separate agents reviewed the implementation against the spec and project standards. At Matias’s request, Jev also contributed bounded judgments during planning, design and review; those outputs remain advisory evidence alongside the actual tests and browser checks.

```text
Conversation and scope
    ↓
Fictional case + live Jev judgments
    ↓  Browser testing exposed evidence leaking between sources
One source per request
    ↓
Inspectable execution trace
    ↓
Same-case comparison: Jev / Luna / Terra
    ↓  Frozen labels, repeated measurements, independent review
Private Vercel release
    ↓  Shared usage limits and public access checks
Public demo + source repository
```

### The conversation behind the changes

These are summaries of the requests and decisions, rather than a transcript.

| What came up | What we built or changed |
| --- | --- |
| Keep the MVP small enough to demonstrate and understand. | One fictional startup, three assumptions, original source text and a bounded note input. Follow-up questions come from application rules. |
| Use Jev in the product and involve it throughout development. | A server-side adapter for typed source judgments, plus separate advisory receipts for development stages. Credentials stay outside the repository and browser. |
| The analysis finished too quickly to see what happened. | A trace that stays visible after completion: actual request bodies, validated responses, timings, retries and the rules applied to the answers. |
| Compare Jev with Luna and Terra on cost, latency and correctness. | The same source boundaries and rubric for all three, independent results and failures, and a separate labeled benchmark. Matias enabled access to the requested OpenAI models before evaluation. |
| Deploy the comparison on Vercel. | A standard Next.js runtime, first released privately with real production API checks. The earlier Sites release remains separate. |
| Let anyone try the sample and inspect its code. | Public demo and GitHub source, with shared live-usage limits and protected old deployment URLs. |
| A first-time visitor sees an unexplained report after one click. | Start with a specific payment claim and the original sources; show the finding and its evidence before technical details, then explain what changes after a new note. |

### What testing changed

The first implementation put several sources into shared request context. Browser testing showed judgments borrowing evidence from another source. We changed the request boundary: each source gets its own request, containing the three assumption questions, and added a regression test. The original statements remain visible even when they disagree. [MVP validation](docs/validation.md)

The comparison review caught a different problem: after an early provider failure, the benchmark counted cases it had never sent as API failures. We separated completed, failed, unavailable and unmeasured cases. Both reviewers reproduced the correction. [Comparison review](docs/comparison/validation.md#final-review)

The recorded evaluation finished with 48/48 label matches for each model across 16 synthetic cases repeated three times. Jev had the lowest median latency and estimated cost in that sample. That result leaves relative accuracy on harder or real diligence material open. The delivered version passed 33 deterministic tests; the reports distinguish those checks from model measurements and owner acceptance.

We used the project-local AI Hero workflow for specifications, implementation and review. This README uses the compact structural views from HumanLayer’s [`visual-pr`](.agents/skills/visual-pr/SKILL.md) to explain the development. The conversation’s durable record is the [MVP spec](.scratch/mvp/spec.md), [trace spec](.scratch/trace/spec.md), [comparison spec](.scratch/comparison/spec.md) and their validation reports.

## Run locally

Requires Node 24 and npm. From `web/`, run `npm ci`, copy `.env.example` to `.env.local`, set your TypeSafe and OpenAI keys plus the quota-store credentials there, and run `npm run dev`. Use the printed local URL. Never commit `.dev.vars` or `.env*` files.

1. Read the question: **Have three Northstar customers paid?** The introduction explains the fictional company, the exact claim and the three source documents.
2. Read the founder update, finance note and pilot interviews, then click **Review the evidence**.
3. Inspect the finding, named source judgments and the question to ask next. The original quotations remain visible directly below.
4. Under **Add information and review again**, load the fictional weekly-usage note. Read or edit it before submitting. It concerns usage, not payments.
5. Click **Add note and review again**. **What changed in this review** compares each finding with the previous successful analysis. Added evidence does not erase the payment conflict.
6. Open **Other questions about Northstar** to inspect weekly usage or acquisition. This selection does not make a model call.
7. Open **How this result was produced** for the execution trace, or **Compare models using these sources** for live comparison and the recorded benchmark.

The latest execution trace stays visible after fast runs and includes partial failures. It records observable events, not hidden model reasoning. Reported token usage is incomplete when requests fail or retry; credentials and authorization headers are excluded. Trace details live only in component memory and clear on reset or refresh. See [trace validation](docs/trace-validation.md).

Notes live only in browser memory and are sent to TypeSafe when you analyze, and to both TypeSafe and OpenAI when you compare. Refreshing or resetting clears them. This is a fictional demonstration, not an investment recommendation. Supported by a source does not mean independently verified.

## Architecture

`web/app/page.tsx` owns the interaction. `web/components/review/evidence-review.tsx` renders the reusable claim, finding and original sources. `web/lib/review.ts` turns validated judgments into authored descriptions and before/after changes; it does not call a model or generate new factual claims. `web/lib/assessment.ts` aggregates source judgments and selects authored follow-up questions. `web/lib/server/jev.ts` calls the official TypeSafe HTTP API, checks the typed response and limits each request to one source. `web/app/api/assess/route.ts` keeps credentials on the server.

Each source gets one request containing the three independent assumption questions. Up to three requests run concurrently, with a 40-second overall timeout. At most seven logical source evaluations (21 judgments) are needed; one retry per source on 429/529 permits at most 14 HTTP attempts (42 transmitted questions). Sources are never placed together in one provider request: browser QA caught cross-source contamination in the earlier batch design. At most four notes of 2000 characters are accepted; all existing sources remain visible. Comparison runs all three models independently with the same source grouping and concurrency. OpenAI uses the same relation rubric with strict structured output and reasoning disabled. A failed model does not erase another model’s result. Case data stays in browser memory. Redis stores usage counters only; there is no vector store or autonomous agent runtime.

The production alias is public. Preview and immutable deployment URLs remain protected by Vercel Authentication, including older releases. Both live endpoints reserve a centralized usage allowance before calling models; invalid requests and quota-store failures do not reach providers.

## Model comparison

Open **Compare models using these sources**, then click **Compare current case** to run Jev, Luna and Terra on the current sources. Each result has elapsed time, estimated USD cost and its own execution trace. Free-form cases show model agreement, not accuracy. Costs use reported input/cache/output tokens and dated public rates, not billing receipts; incomplete usage is labeled.

The recorded benchmark uses 16 new synthetic cases, four per relation, frozen before the first run and repeated three times. All three models matched 48/48 labels. That ceiling on a small synthetic set does not establish equal general accuracy. Jev was faster by median and cheaper in this sample. See [method and results](docs/comparison/validation.md), [frozen labels](web/evaluation/holdout.json), and [raw receipts](docs/comparison/receipts.json).

To rerun the benchmark explicitly (144 paid provider calls), run `node --env-file=.env.local --experimental-strip-types scripts/benchmark.ts` from `web/`. Page loads never rerun it.

## Public sharing rollout

The demo is public and the centralized usage guard is active. See [current state](CURRENT.md) and [rollout evidence](docs/public-demo/validation.md). Source code and linked documentation are published in this repository.

Both live actions share a centralized allowance of 20 executions per UTC day, plus five per network in each fixed 10-minute window. A comparison counts as one execution and may call all three models. Reservations count even if a provider later fails. When a limit is reached, visitors can still read the case and recorded benchmark. These quotas limit calls; they are not a guaranteed dollar billing cap.

The quota store uses Upstash Redis’s free plan with automatic upgrades and eviction disabled. Set `KV_REST_API_URL` and `KV_REST_API_TOKEN` only in local ignored/server environment variables. Missing or unavailable quota storage pauses live inference. `DEMO_DAILY_LIMIT` accepts 1–100 (default 20). `DISABLE_LIVE_ANALYSIS=1` stops live runs; environment changes require redeployment. Both routes reserve capacity after request validation and before contacting providers.

Production must retain Vercel protection on preview and immutable deployment URLs, so earlier versions without admission control cannot become public through an old link. Only the current production alias is intended for anonymous access.

## Checks

From `web/`:

- `npm test`: behavior, source preservation, provider validation and HTTP input/error tests.
- `npm run typecheck` and `npm run lint`: application checks. The untouched generated UI catalog and its mobile hook are excluded from lint; the consumed primitives are covered by typechecking and browser QA.
- `npm run build`: production build.
- `node --env-file=.env.local --experimental-strip-types scripts/evaluate.ts`: real Jev calls on the labeled synthetic corpus and the before/after demo. Uses your provider quota. Writes non-secret receipts under `docs/jev/`.

Run `python3 scripts/check-secrets.py` from the repository root before every commit. It scans staged files for the configured key and credential-shaped strings. Production output is separately scanned before packaging.

## Scope and evidence

Implementation spec: [.scratch/mvp/spec.md](.scratch/mvp/spec.md). Current state: [CURRENT.md](CURRENT.md). TypeSafe research: [docs/typesafe-fit.md](docs/typesafe-fit.md). Live stage receipts: [docs/jev](docs/jev).

Matias selected Conviction on 2026-09-16 and authorized end-to-end planning, repository creation, implementation and code review on 2026-09-18. Self-serve flow, prepared fictional case, text notes, English UI and private hosting were selected under that delegation. Jev contributes typed judgments at planning, design, implementation/evaluation and review stages; it does not generate this application or replace deterministic checks and independent code review.

The live corpus is small and synthetic. Initial prompt: 10/11; the conflicting-statements case needed a clearer rubric. These results are iteration evidence, not an estimate of general investment-analysis accuracy. See [the validation and review report](docs/validation.md) for current results and limits.

## Provenance

Project-local AI Hero skills are pinned to `mattpocock/skills` revision `959a8e9f1edc3adbe2f7e3054bb6fbefa6696260` (see `AGENTS.md` for the full canonical revision). Official TypeSafe skill installed through `npx skills` on 2026-09-18 and recorded in `skills-lock.json`.

The original Sites scaffold retains its provided UI primitives; the runtime is now standard Next.js for Vercel. The former hosting manifest is archived in docs/sites-hosting-archive.json. Vulnerable scaffold dependencies were updated together to compatible patched releases; no forced dependency overrides were used.

Conviction is a portfolio hypothesis for the Loop3 opportunity, not a Loop3 commission or a validated buyer request.
