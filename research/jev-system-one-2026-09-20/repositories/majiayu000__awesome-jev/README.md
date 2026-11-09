# Awesome Jev

[![Checks](https://github.com/majiayu000/awesome-jev/actions/workflows/checks.yml/badge.svg)](https://github.com/majiayu000/awesome-jev/actions/workflows/checks.yml)

Selected open-source projects, SDKs, tutorials, and evaluations for Jev, TypeSafe’s System One model.

[Browse website](https://majiayu000.github.io/awesome-jev/) · [简体中文](README_zh.md) · [Contributing](CONTRIBUTING.md) · [Sources](SOURCE.md)

A community-maintained list, unaffiliated with TypeSafe. Inclusion is a reading recommendation, not a certification of safety, accuracy, or production readiness.

**[Browse all resources](catalog/FULL.md)** — Projects, tools, tutorials, and articles organized by category.

## How to use this list

[Read the bilingual getting-started guide](guides/start.md#english) · [Run the offline ticket-routing example](examples/README.md#english)

1. New to Jev? Start with the documentation and launch article below to understand its decision tasks.
2. Integrating it? Choose an [SDK](taxonomy/sdks.md), then follow the [routing](patterns/routing.md) or [verification](patterns/verification.md) guide.
3. Looking for examples? Browse the selections below or the [complete directory](catalog/FULL.md). See [dated updates](updates/README.md) for recent changes.

## Contents

- [Getting started](#getting-started)
- [SDKs and integrations](#sdks-and-integrations)
- [Agent tools](#agent-tools)
- [Browser automation](#browser-automation)
- [Applications and games](#applications-and-games)
- [Evaluations and open implementations](#evaluations-and-open-implementations)
- [Articles and Chinese resources](#articles-and-chinese-resources)
- [Before using these projects](#before-using-these-projects)
- [Field notes and gotchas](#field-notes-and-gotchas)
- [Further reading](#further-reading)

## Getting started

Jev returns choices, scores, and condition judgments for software to act on. A valid output format does not guarantee a correct judgment.

- [Documentation](https://docs.typesafe.ai/) - API reference, quick start, and examples.
- [Model limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md) - Known limitations documented for Jev 1.13.
- [Launch article](https://typesafe.ai/blog/introducing-system-one-models-and-jev) - TypeSafe’s introduction to Jev and its intended uses.
- [Playground](https://console.typesafe.ai/) - TypeSafe console for trying the API.

## SDKs and integrations

- [typesafe-sdk-js](https://github.com/typesafe-ai/typesafe-sdk-js) - Official JavaScript and TypeScript client.
- [typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python) - Official Python client.
- [system-one-adapter-python](https://github.com/typesafe-ai/system-one-adapter-python) - Compare Jev and language models through the same decision interface.
- [TypeSafe skills](https://github.com/typesafe-ai/skills) - Official guidance for coding agents using Jev.
- [Vercel AI Gateway](https://vercel.com/ai-gateway/models/jev) - Gateway model page; check the provider for current access and pricing.
- [Cloudflare Workers AI](https://developers.cloudflare.com/ai/models/typesafe/jev/) - Cloudflare’s model documentation.
- [vercel/eve](https://github.com/vercel/eve) - Agent framework with a Jev evaluation integration; Jev is one part of the project.
- [vercel-labs/ai-cli](https://github.com/vercel-labs/ai-cli) - Command-line tools with a Jev evaluation integration.

## Agent tools

- [jev-router](https://github.com/gargpratyush/jev-router) - Choose models for Claude Code and Codex tasks; requires Node.js 20.12+, a Jev key, and the corresponding logged-in CLI.
- [jev-review — devagrawal09](https://github.com/devagrawal09/jev-review) - Code review workflow with a dashboard.
- [jev-review — NiazMorshed2007](https://github.com/NiazMorshed2007/jev-review) - Local code review through an MCP plugin.
- [foreman](https://github.com/thruwire/foreman) - Use Jev to monitor a coding agent’s work.
- [jev-mcp](https://github.com/jkudish/jev-mcp) - Expose Jev checks and search through MCP tools.
- [jev-belay](https://github.com/valentynkit/jev-belay) - Claude Code Stop hook that checks transcript evidence for unverified completion claims; errors allow the turn to end.
- [jev-commit](https://github.com/valentynkit/jev-commit) - Git commit-message hook that compares the message with the staged diff and checks for possible credentials.
- [jev.nvim](https://github.com/valentynkit/jev.nvim) - Neovim plugin that scores functions against a natural-language question and lists results in quickfix.

## Browser automation

- [jev-ultrafast](https://github.com/browser-use/jev-ultrafast) - Select browser actions and DOM elements with Jev; use a language model for text entry.
- [typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) - Use OCR text to help Jev select computer actions.

## Applications and games

- [notra](https://github.com/usenotra/notra) - A project with Jev-based feature-flag routing.
- [jev-trader](https://github.com/jarrodwatts/jev-trader) - Trading experiment that requests a decision for each Monad block; inclusion does not establish profitability.
- [typesafe-mario](https://github.com/fhshaik/typesafe-mario) - Game agent using structured emulator state.
- [jev-skip](https://github.com/valentynkit/jev-skip) - Browser extension that uses Jev to identify potential sponsor segments from YouTube captions.
- [jev-plays-pokemon-red](https://github.com/valentynkit/jev-plays-pokemon-red) - PyBoy game agent where code handles routing and arithmetic and Jev selects among actions at decision points.
- [jev-drone](https://github.com/RomanSlack/jev-drone) - Drone simulation using Jev in MuJoCo.

## Evaluations and open implementations

- [jev-rerank-bench](https://github.com/anessbelbati/jev-rerank-bench) - A reranking benchmark; inspect its dataset and method before applying the results.
- [jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) - A phishing-classification comparison, including cases where Jev underperforms.
- [Janus](https://github.com/FirasSX914/Janus) - Measure a confidence threshold on your data, then route between smaller and larger models.
- [jevlike](https://github.com/vinnylarouge/jevlike) - An open option-scoring implementation, not TypeSafe’s model weights.
- [OpenJev / SemIf](https://github.com/TheoLeeCJ/SemIf) - An independent implementation inspired by Jev, not the official model.
- [TypeSafe workflow evaluations](https://evals.typesafe.ai/) - Vendor evaluations; read how reference answers and comparisons are constructed.

## Articles and Chinese resources

- [Every / Mike Taylor](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds) - A small-sample hands-on evaluation, not a general accuracy guarantee.
- [OrcaRouter Chinese introduction](https://www.orcarouter.ai/zh-CN/blog/jev-typesafe-system-one-what-we-know) - An overview of the product and available evidence.
- [Baoyu’s Chinese explanation](https://x.com/dotey/status/2100109937237987823) - An explanation of Jev’s uses; this is commentary, not an independent benchmark.
- [jev-report](https://github.com/HackSing/jev-report) - A Chinese report and reproduction materials; repository existence was checked on 2026-09-19, but its results have not been reproduced here.

## Before using these projects

- Valid output can still be wrong; evaluate on your own examples first.
- Separate distinct intents instead of forcing a compound request into one category.
- Keep exact arithmetic and date calculations in code.
- Measure confidence thresholds on your actual data instead of copying example values.
- Record model versions, inputs, test conditions, and failures when comparing latency, cost, or accuracy.
- Enforce tool permissions in code and provide human review for uncertain decisions.

See [model limitations](taxonomy/critique-limits.md) and [evaluation methods](taxonomy/benchmarks-replicas.md). These are usage recommendations; this repository has not independently reproduced every listed project.


## Field notes and gotchas

Sharpest public pitfalls; full bilingual list in [guides/gotchas.md](guides/gotchas.md).

- Valid format is not correct judgment — read [model limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md).
- One demo win is not a reproduction guarantee ([Pac-Man follow-up](https://x.com/ephraimduncan/status/2100554620254752981)).
- Small-sample speed/cost writeups are not universal accuracy claims ([Every](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds)).
- Open replicas are not official weights; negative results (e.g. [phishing-bench](https://github.com/anisselbd/jev-phishing-bench)) stay listed.
- Featured-card checks are scoped: see [guides/featured-review.md](guides/featured-review.md).

## Further reading

- [Resource categories](SUMMARY.md).
- [Practical guides](SUMMARY.md#使用方法).
- [Known limitations](taxonomy/critique-limits.md).
- [Field notes and gotchas](guides/gotchas.md).
- [Dated updates](updates/README.md).
- [Research notes](research/00-overview.md).

## Contributing

Suggest projects, correct descriptions, or share documented failures using the [contribution guide](CONTRIBUTING.md).
