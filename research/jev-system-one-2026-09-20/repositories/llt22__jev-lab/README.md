# Awesome Jev Lab

> A curated map of **Jev / TypeSafe System One** resources, real-world use cases, and reproducible benchmarks.

**Independent community project. Not affiliated with or endorsed by TypeSafe.**

**English** | [简体中文](README.zh-CN.md)

[![Tests](https://img.shields.io/badge/tests-38%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Model](https://img.shields.io/badge/tested-jev--1.13.0-blueviolet)](https://docs.typesafe.ai/models)
[![Zero deps](https://img.shields.io/badge/lab-stdlib%20only-orange)](scripts/)

Jev turns natural-language state into typed decisions: **Noul** for yes/no, **Choice** for selecting an option, and **Score** for ordered ratings. This repository combines an ecosystem guide with independent tests, raw artifacts, and the scripts needed to reproduce them.

## Contents

- [Start here](#start-here)
- [Official resources](#official-resources)
- [SDKs and integrations](#sdks-and-integrations)
- [Curated use cases](#curated-use-cases)
- [Reproducible benchmarks](#reproducible-benchmarks)
- [Run the lab](#run-the-lab)
- [Research archive](#research-archive)
- [Contributing](#contributing)

## Start here

| Goal | Best entry point |
| --- | --- |
| Understand Jev in five minutes | [TypeSafe Quick Start](https://docs.typesafe.ai/introduction/quickstart) |
| Choose an architecture pattern | [Official patterns](https://docs.typesafe.ai/patterns) |
| See where people are using it | [Curated use cases](#curated-use-cases) |
| Check claims against measurements | [Jev Lab validation report](docs/jev-validation-2026-09-18.md) |
| Reproduce the results | [Run the lab](#run-the-lab) |

## Official resources

- [TypeSafe](https://typesafe.ai) - product overview and access.
- [Documentation](https://docs.typesafe.ai/) - API concepts, guides, and reference.
- [Models](https://docs.typesafe.ai/models) - aliases, versioned model IDs, and pricing.
- [Patterns](https://docs.typesafe.ai/patterns) - fan-out, confidence-gated routing, composite scoring, and intent routing.
- [Use-case map](https://docs.typesafe.ai/concepts/use-case-map) - official task and application taxonomy.
- [TypeSafe GitHub organization](https://github.com/orgs/typesafe-ai/repositories) - official SDKs, skills, and adapters. Beware similarly named, unrelated organizations.

## SDKs and integrations

| Project | What it provides | Source |
| --- | --- | --- |
| Python SDK | Official TypeSafe API client for Python | [typesafe-ai/typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python) |
| JavaScript SDK | Official TypeSafe API client for JavaScript and TypeScript | [typesafe-ai/typesafe-sdk-js](https://github.com/typesafe-ai/typesafe-sdk-js) |
| Agent skills | Official skills for building with the System One API | [typesafe-ai/skills](https://github.com/typesafe-ai/skills) |
| System One adapter | Run the TypeSafe client contract against other LLM APIs | [typesafe-ai/system-one-adapter-python](https://github.com/typesafe-ai/system-one-adapter-python) |
| Vercel AI Gateway | `typesafe-ai/jev` through AI SDK's evaluation API | [Vercel announcement](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway) |
| LangChain | Python and JS integration, model routing, and tool-risk middleware | [Integration guide](https://blog.langchain.com/building-a-harness-with-jev/) |
| OpenRouter | Hosted access to `typesafe-ai/jev` | [Model page](https://openrouter.ai/typesafe-ai/jev) |
| Cline browser harness | Jev-driven browser actions over structured DOM observations | [cline/plugins/jev-browser](https://github.com/cline/plugins/tree/main/plugins/jev-browser) |

## Curated use cases

These are representative projects and first-hand reports, not endorsements. Evidence labels distinguish inspectable implementations from author-reported results. See the [full 28-case audit](docs/jev-round5-supplement-2026-09-19.md) for broader coverage and caveats.

### Agents and interfaces

- [Cline Jev Browser](https://github.com/cline/plugins/tree/main/plugins/jev-browser) - browser action selection with a bounded loop and explicit review states. **Open source.**
- [Jev Voice Browser](https://github.com/moritzkremb/jev-voice-browser) - voice intent and browser target selection while speech is still streaming. **Open source demo.**
- [jev-experiments](https://github.com/dabit3/jev-experiments) - a collection of predictive UI, routing, and decision experiments. **Open source experiments.**

### Search, screening, and routing

- [TypeSafe Screening MCP](https://github.com/masa-med-ai/typesafe-screening-mcp) - screens PubMed titles and abstracts against clinical criteria. **Open source; first-hand run reported.**
- [ERP, knowledge-base, and mail search](https://x.com/bigfarmer666/status/2101114327722008829) - parallel retrieval with Jev reranking and disambiguation. **Author-reported production use.**
- [Edge k3s decision pipeline](https://x.com/maro_kt/status/2101130758635258226) - separates deterministic code, typed decisions, and general LLM reasoning. **Author-reported field test.**

### Quality gates and real-time control

- [AI content scoring](https://x.com/noahxops/status/2101135688217538790) - scores generated variants before publishing. **Author-reported experiment.**
- [Sprite Fusion level generation](https://www.spritefusion.com/blog/generating-game-level-in-real-time-with-jev) - chooses the next terrain segment from bounded candidates. **Published demo with timings.**

### More directories

- [awesome-jev](https://github.com/ckaraca/awesome-jev) - a broader project and integration list.
- [outjev.lol](https://outjev.lol) - community projects labeled as products, demos, or experiments.
- [Jev Lab community survey](docs/jev-x-use-cases-2026-09-18.md) - source-audited index with risks and selection criteria.

## Reproducible benchmarks

All numbers below come from this repository's pilot datasets. They are observations, not production guarantees.

| Question | Result | Evidence |
| --- | --- | --- |
| Does 1 to 20-question fan-out add latency? | No growth observed; P50 stayed around **1.4 s** | [Report](docs/jev-validation-2026-09-18.md) / [raw artifact](artifacts/fanout-jev-1.13.0-2026-09-18.json) |
| What did 108 requests cost? | Approximately **$0.0044** | [Validation report](docs/jev-validation-2026-09-18.md) |
| Were decisions repeatable? | **100% decision agreement** across 3 x 36 support cases | [Stability report](artifacts/support-routing-v1-repeat-stability-2026-09-18.md) |
| Did Jev beat a simple baseline? | No; keyword rules scored **97.2% vs 91.7%** on an easy pilot set | [Baseline](artifacts/support-routing-v1-keyword-baseline.md) |
| Is top-1 probability enough for a safety gate? | No; failed cases had confidence 0.04-0.16 while top-1 probability reached 0.58 | [Confidence study](docs/jev-round3-2026-09-18.md) |
| Did full-path latency match sub-100 ms claims? | No; this environment measured roughly **1.5 s end to end** | [Validation report](docs/jev-validation-2026-09-18.md) |

Practical takeaways:

1. Pin the versioned model ID after tuning thresholds; aliases can move.
2. Gate on the API's `confidence`, not only the largest answer probability.
3. Treat probabilities near 0.5 as uncertainty, not an automatic "no".
4. Test CJK workloads separately; official documentation says English performs best.
5. Keep raw inputs, outputs, errors, and retries so a result can be audited.

## Run the lab

The test suite and comparison scripts use only the Python standard library. API benchmarks require a TypeSafe key.

```sh
cp .env.example .env
python3 -m unittest discover -s tests

# Support routing and a deterministic keyword baseline
python3 scripts/evaluate_support.py --run-name support-routing-v1
python3 scripts/evaluate_keyword_baseline.py

# Fan-out latency and confidence-gated escalation
python3 scripts/benchmark_fanout.py
python3 scripts/evaluate_confidence_escalation.py
```

Repository layout:

```text
docs/       Source-audited reports and research notes
evals/      Versioned benchmark datasets
scripts/    Reproducible evaluators and comparison tools
artifacts/  Raw JSON outputs and generated reports
tests/      Offline unit tests
experiments/ Runnable integration experiments
```

## Research archive

| Topic | Reports |
| --- | --- |
| Benchmarks and calibration | [Initial validation](docs/jev-validation-2026-09-18.md) · [Confidence gates](docs/jev-round3-2026-09-18.md) |
| Agent control and reasoning supervision | [Thinking supervision](docs/jev-thinking-supervision-2026-09-18.md) · [Ecosystem cross-check](docs/jev-round4-2026-09-19.md) |
| Official claims and integrations | [Official/platform audit](docs/jev-round4-supplement-2026-09-19.md) |
| Integration experiments | [json-render + Jev](docs/json-render-jev-2026-09-19.md) |
| Community adoption | [First-hand use cases](docs/jev-round5-2026-09-19.md) · [28-case audit](docs/jev-round5-supplement-2026-09-19.md) · [Community survey](docs/jev-x-use-cases-2026-09-18.md) |
| Round 6 survey | [Evaluators, clone wave, and scale evidence](docs/jev-round6-2026-09-20.md) |
| Round 7 survey | [Competitor narrative checked, open-implementation selection map](docs/jev-round7-2026-09-20.md) |

## Contributing

Independent replications, counterexamples, and new datasets are especially valuable. Read [CONTRIBUTING.md](CONTRIBUTING.md), [suggest a resource](https://github.com/llt22/jev-lab/issues/new?template=resource-suggestion.yml), or [share a benchmark result](https://github.com/llt22/jev-lab/issues/new?template=benchmark-result.yml) without changing code.

This repository is research material. Do not treat a single-run probability as production accuracy or permission to execute an action. Prices, versions, and ecosystem status reflect the capture dates in each report.

No open-source license has been declared yet. Until one is added, standard copyright restrictions apply.
