<div align="center">

<h1>jev-starter</h1>

<p><strong>Production-ready patterns for building probabilistic decision workflows with <a href="https://typesafe.ai/">TypeSafe AI Jev</a>.</strong></p>

<p>
  <a href="https://www.npmjs.com/package/jev-starter"><img alt="npm version" src="https://img.shields.io/npm/v/jev-starter?logo=npm"></a>
  <a href="https://github.com/hamakyo/jev-starter/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/hamakyo/jev-starter/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/hamakyo/jev-starter/releases/latest"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/hamakyo/jev-starter"></a>
  <a href="https://www.npmjs.com/package/jev-starter"><img alt="Node version" src="https://img.shields.io/node/v/jev-starter"></a>
  <a href="https://github.com/hamakyo/jev-starter/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/hamakyo/jev-starter"></a>
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5.7%2B-3178C6?logo=typescript&logoColor=white">
</p>

<p><strong>English</strong> · <a href="./README.ja.md">日本語</a></p>

</div>

> **Status:** `jev-starter@0.1.1` is published on [npm](https://www.npmjs.com/package/jev-starter/v/0.1.1) with provenance, and [`v0.1.1`](https://github.com/hamakyo/jev-starter/releases/tag/v0.1.1) is available as a GitHub Release. This repository is also enabled as a GitHub template. The `main` branch may contain unreleased changes intended for a later version.

`jev-starter` is not another Jev SDK wrapper. The official `@typesafe-ai/sdk` already provides a typed client. This project focuses on the layer applications still need around the model: **decision contracts, policy thresholds, fallbacks, evaluation, and production examples**.

## What this project is for

Jev returns structured answers that software can act on. A production application usually needs more than a model call:

```text
application state
      |
      v
  Jev decision
      |
      v
 typed probabilities
      |
      v
 decision policy
   /      |       \
  /       |        \
auto   fallback   human review
```

The goal of this repository is to make that pattern reusable and measurable.

## Install

The published package requires Node.js 20 or newer:

```sh
pnpm add jev-starter
```

This repository pins pnpm 9.15.4 for contributor and CI commands. Consumers may use another compatible package manager; the runtime package is ESM and exposes its public API from `jev-starter`.

## Design principles

- **Official SDK underneath.** Use `@typesafe-ai/sdk` rather than duplicating TypeSafe transport or response types.
- **Separate inference from policy.** Jev estimates; application code decides what confidence is sufficient for an action.
- **Side effects stay with the host application.** The starter returns an action recommendation; it does not silently execute business operations.
- **Uncertainty is a first-class path.** Low-confidence decisions must have an explicit fallback or review route.
- **Confident negatives are not uncertainty.** Binary judgments should support two-sided thresholds so a low `P(true)` can be treated differently from an ambiguous result.
- **Evaluate before automating.** Thresholds should be selected from task-specific data, not copied from examples.
- **Observable by default.** Model, latency, confidence/probabilities, selected policy path, and outcome should be measurable.

## Repository layout

```text
src/
  core/           decision contracts and engine
  policies/       reusable threshold / routing policies
  providers/      Jev and deterministic mock providers
  observability/  decision events and metrics hooks

evals/
  fixtures/       labeled JSONL datasets
  metrics/        accuracy, calibration, risk/coverage, latency, cost
  runners/        Jev, baseline, comparison, and cascade runners

examples/
  support-routing/
  agent-decision-gate/
  llm-judge/
  rag-evaluator/  showcase: RAG diagnosis + Jev/LLM cascade evaluation

docs/
  architecture.md
  decision-contract.md
  evaluation.md
  rag-evaluator.md
  roadmap.md
```

## Core flow

```ts
import { choice } from "@typesafe-ai/sdk";
import { DecisionEngine, JevProvider, defineDecision } from "jev-starter";

const questions = {
  category: choice("What is this ticket about?", {
    billing: null,
    technical: null,
    other: null,
  }),
};

const ticketRouting = defineDecision({
  id: "support.ticket-routing",
  version: "1",
  questions,
  policy: {
    kind: "confidence",
    question: "category",
    autoThreshold: 0.9,
    fallbackThreshold: 0.65,
  },
});

const state = { ticket: { subject: "Duplicate charge", body: "I was charged twice." } };
const signal = new AbortController().signal;
const engine = new DecisionEngine(new JevProvider());
const result = await engine.decide(ticketRouting, state, {
  signal,
  timeout: 10_000,
});

switch (result.route) {
  case "auto":
    // host application performs the approved side effect
    break;
  case "fallback":
    // optional LLM / secondary classifier path
    break;
  case "review":
    // human review or queue
    break;
}
```

The example above uses the published package import. For a source checkout, run `pnpm build` before resolving that package entry; repository examples may instead import from `./src/index.js`. The clean-install package check exercises the same `exports` entry. `result.answers` contains the complete typed answer map, including choice/score confidence and probabilities or a noul probability. The engine only returns the route; the host application owns every side effect. Provider/API failures and malformed SDK responses reject and do not produce a `DecisionOutcome`.

## Reference examples

- [Support routing](examples/support-routing/README.md)
- [Agent decision gate](examples/agent-decision-gate/README.md)
- [LLM judge guard](examples/llm-judge/README.md)
- [RAG evaluator showcase](examples/rag-evaluator/README.md)

## Evaluation target

The starter should make it easy to answer a practical migration question:

> For this classification or decision task, how much traffic can Jev automate at an acceptable error rate compared with the current baseline?

The offline harness implements accuracy, confusion matrices, per-label precision/recall/F1, Brier score, weighted ECE, coverage/risk threshold sweeps, binary-band sweeps, risk-coverage/AURC, latency, failures, usage, comparison, and cascade reports. Reports distinguish successful-only accuracy from all-row accuracy and retain combined cascade legs for latency, usage, and model-specific cost. Cost is calculated only from an explicitly supplied versioned pricing snapshot; otherwise it is reported as `unavailable`.

```sh
pnpm eval:offline
pnpm eval:live      # requires TYPESAFE_API_KEY; opt-in only
```

## Showcase: RAG evaluator

RAG evaluation is the repository's first full showcase rather than a minimal classification demo. The basic answer-level mode is runnable offline and keeps retrieval and generation judgments separate.

```text
Question --------------------+
Retrieved contexts ----------+----> Jev atomic judgments
Generated answer ------------+              |
Reference answer (optional) -+              v
                                    typed probabilities
                                             |
                                             v
                                    deterministic diagnosis
```

The evaluator keeps retrieval and generation failures separate and reports accuracy, Brier score, and weighted ECE for each available Jev component:

- chunk relevance;
- context sufficiency;
- evidence conflict;
- answer relevance;
- groundedness;
- contradiction;
- reference-based correctness when available.

The final diagnosis is composed in TypeScript instead of asking Jev one large opaque question. The comparison modes are **Jev-only**, **baseline judge**, and **Jev -> fallback judge cascade** on the same labeled dataset. The fixture baseline currently exposes only its final diagnosis/confidence, so its component metrics are omitted rather than copied from Jev. Claim extraction remains a host/LLM extension point and is not implemented in basic mode.

See [RAG evaluator showcase](docs/rag-evaluator.md) for the detailed design.

## Documentation

- [Architecture](docs/architecture.md)
- [Decision contract](docs/decision-contract.md)
- [Evaluation](docs/evaluation.md)
- [RAG evaluator showcase](docs/rag-evaluator.md)
- [Upstream compatibility](docs/compatibility.md)
- [Public API review](docs/public-api.md)
- [Release checklist](docs/release-checklist.md)
- [Distribution status](docs/distribution-options.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](docs/roadmap.md)

## Upstream

The official JavaScript/TypeScript SDK is [`@typesafe-ai/sdk`](https://github.com/typesafe-ai/typesafe-sdk-js). It currently exposes typed `systemOne()` requests and `noul`, `choice`, and `score` question/response shapes.

Future npm versions, tags, and GitHub Releases remain explicit approval-gated operations performed through the documented release workflow. That policy applies to future releases; `v0.1.1` is already public.

## License

[MIT](LICENSE) © 2026 hamakyo.
