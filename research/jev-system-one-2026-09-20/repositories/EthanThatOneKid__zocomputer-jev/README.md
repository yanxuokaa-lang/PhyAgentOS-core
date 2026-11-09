# zocomputer-jev

A versioned Zo Rule for using TypeSafe AI Jev as an internal decision delegate. This repository intentionally does not duplicate Jev's skill, SDK integration, or evaluator: Zo should use the official TypeSafe skill and current TypeSafe documentation.

## What it contains

- `rule.md` — the versioned source of truth for the live Zo Rule.

The matching rule is installed in Zo's Rules settings. Keep `rule.md` synchronized with that live rule. Never put API keys or other secrets in this repository.

## Rule behavior

The rule applies when a task contains a bounded judgment that could benefit from typed evidence: classification, routing, prioritization, retry/continue/ask/stop behavior, risk, quality, verification, or choosing a tool or script.

Zo should use the official TypeSafe AI skill to formulate a minimal, redacted question for Jev, treat Jev's typed answers and probabilities as evidence, and keep implementation, authorization, side-effect control, and verification local to Zo. The user does not need to know Jev exists.

The rule is not for obvious deterministic work when Jev would add overhead. Jev must not authorize secrets, irreversible actions, external communications, financial actions, or recursive delegation.

## Official source

- [TypeSafe AI agent skill](https://docs.typesafe.ai/agent-skill)
- [TypeSafe AI documentation](https://docs.typesafe.ai/)
- [Jev on Vercel AI Gateway](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway)
