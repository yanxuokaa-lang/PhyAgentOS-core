# Awesome Jev Examples

**English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md)

> Discover what people build with Jev, how it works, and where to learn more.

A curated index for **[TypeSafe AI’s Jev](https://docs.typesafe.ai/introduction)**, a decision model that answers Choice, Score, and Noul questions over supplied state. Independent community project; not affiliated with TypeSafe AI.

[Getting started](docs/START-HERE.md) · [All details](catalog/DETAILS.md) · [X / YouTube](catalog/MEDIA.md) · [Contributing (English)](CONTRIBUTING.md)

**72 resources:** 46 source-code projects/SDKs, 25 official guides/patterns/references, and 1 first-party engineering report. **28 additional X / YouTube leads** await review. Initial review: 2026-09-19.

Review means reading the stated source, not running or auditing the project. No examples have been reproduced here. Two official pages were only partially retrieved and are marked accordingly. Author-reported performance is not independently verified.

## Ways to use Jev

These official TypeSafe entry points cover interactive testing, direct API access, an SDK, and agent-assisted development.

- **[Playground](https://console.typesafe.ai/playground)** — Try Choice, Score, and Noul together in the browser—no local setup required. [Open Playground](https://console.typesafe.ai/playground).
- **[HTTP API](https://docs.typesafe.ai/api)** — Send `state`, `model`, and typed `questions` to `POST https://api.typesafe.ai/v1/systemone`. Check the current schema before integrating. [API reference](https://docs.typesafe.ai/api).
- **[Python SDK](https://docs.typesafe.ai/sdk/python)** — Run `pip install typesafe-sdk` for typed sync or async calls; the client reads `TYPESAFE_API_KEY` from the environment. [Python SDK guide](https://docs.typesafe.ai/sdk/python).
- **[Agent Skill](https://github.com/typesafe-ai/skills)** — Run `npx skills add typesafe-ai/skills --skill typesafe-ai` so coding agents can design requests, batch independent questions, and interpret typed answers. [Official skill](https://github.com/typesafe-ai/skills).

### Third-party access and community demos

This is a growing, non-exhaustive index—not an endorsement or ranking. We will keep collecting public Jev access providers, integrations, playgrounds, and demos with clear attribution and limitations. [Suggest another channel](https://github.com/evan87863/awesome-jev-examples/issues/new?template=resource.yml).

- **[OpenRouter](https://openrouter.ai/typesafe)** — A third-party model platform that currently lists Jev Latest and Jev 1.13; its always-latest model ID is `~typesafe/jev-latest`. [Source](https://openrouter.ai/typesafe).
- **[AIJev](https://aijev.net)** — An independent third-party playground currently included as one community example. Listing it does not imply endorsement, and its behavior is not evidence of the official service’s performance. [Source](https://aijev.net).

For direct TypeSafe access, create an API key in the [TypeSafe console](https://console.typesafe.ai/settings/keys). Provider access, pricing, model IDs, and installation commands can change; follow the linked source when you integrate.

## Start exploring

- **[Quick start](https://docs.typesafe.ai/introduction/quickstart)** — Make a first typed request in the Playground or SDK. [Details](catalog/DETAILS.md#official-quickstart)
- **[Jev Ultrafast](https://github.com/browser-use/jev-ultrafast)** — Choose a browser operation and target together from a dynamic table of page elements. [Details](catalog/DETAILS.md#browser-use--jev-ultrafast)
- **[Jev Review (devagrawal09)](https://github.com/devagrawal09/jev-review)** — Review diffs or repositories through staged risk screening, evidence selection, and severity scoring. [Details](catalog/DETAILS.md#devagrawal09--jev-review)
- **[Kill My Idea](https://github.com/monteduro/killmyidea)** — Ask parallel questions about a startup idea and combine scores into a fixed verdict. [Details](catalog/DETAILS.md#monteduro--killmyidea)
- **[neo4jev](https://github.com/jexp/neo4jev)** — Choose the next graph relationship and check whether the goal is reached in the same call. [Details](catalog/DETAILS.md#jexp--neo4jev)
- **[Janus](https://github.com/FirasSX914/Janus)** — Measure when to route between small and large models, including when routing should be rejected. [Details](catalog/DETAILS.md#firassx914--janus)
- **[Jev Chess Lab](https://github.com/denikuchero/jev-chess-lab)** — Recorded chess experiments compare Jev alone, tactical filters, and Stockfish assistance. [Details](catalog/DETAILS.md#denikuchero--jev-chess-lab)

## Browse by use case

- [Official guides & SDKs](#official) (26)
- [Browser, desktop & mobile](#browser) (8)
- [Coding agents & MCP](#agents) (8)
- [Model routing](#routing) (2)
- [Moderation, rules & safety checks](#safety) (5)
- [Retrieval & knowledge graphs](#retrieval) (1)
- [Data & observability](#data) (4)
- [Everyday automation & smart homes](#automation) (2)
- [Products & content tools](#applications) (4)
- [Games & simulations](#games) (6)
- [Evaluation & calibration](#evaluation) (5)
- [Boundary experiments](#experiments) (1)

<a id="official"></a>

## Official guides & SDKs

| Resource | Summary & details |
| --- | --- |
| [Official Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python) | Official Python client with a minimal support-ticket classification example. [Details](catalog/DETAILS.md#typesafe-ai--typesafe-sdk-python) |
| [Quick start](https://docs.typesafe.ai/introduction/quickstart) | Make a first typed request in the Playground or SDK. [Details](catalog/DETAILS.md#official-quickstart) |
| [Speculative fan-out](https://docs.typesafe.ai/patterns/fan-out) | Ask possible branches together, then let code select the relevant answers. [Details](catalog/DETAILS.md#official-fan-out) |
| [Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing) | Separate the answer from the decision to act; measure escalation thresholds on your data. [Details](catalog/DETAILS.md#official-confidence-routing) |
| [Composite scoring](https://docs.typesafe.ai/patterns/composite-scoring) | Evaluate independent dimensions and combine them with explicit weights in code. [Details](catalog/DETAILS.md#official-composite-scoring) |
| [Intent routing](https://docs.typesafe.ai/patterns/intent-routing) | Classify requests and send them to rules, specialist models, or a human. [Details](catalog/DETAILS.md#official-intent-routing) |
| [Smart home assistant](https://docs.typesafe.ai/demos/smart-home) | Evaluate home-control requests with multiple questions in a shared call. [Details](catalog/DETAILS.md#official-smart-home) |
| [Jev 1.13 known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) | Read documented weaknesses and failure modes for this specific model version. [Details](catalog/DETAILS.md#official-jev-1-13) |
| [Noul self-consistency](https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook) | Repeat insurance-claim judgments to study uncertainty and stability, not factual correctness. [Details](catalog/DETAILS.md#official-consistency-noul-cookbook) |
| [Choice self-consistency](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook) | Add an uncertain outcome to moderation and compare agreement with automation coverage. [Details](catalog/DETAILS.md#official-consistency-choice-cookbook) |
| [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions) | Compare batched and separate requests for multiple questions about one document. [Details](catalog/DETAILS.md#official-parallel-questions) |
| [Retrieval reranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe) | Shortlist with BM25, then score query–passage pairs; the example uses legal retrieval. [Details](catalog/DETAILS.md#official-rerank-typesafe) |
| [Line-by-line semantic search](https://docs.typesafe.ai/cookbooks/semantic_find) | Choose relevant document line IDs and separately check whether an answer exists. [Details](catalog/DETAILS.md#official-semantic-find) |
| [Recover document structure](https://docs.typesafe.ai/cookbooks/autoformat) | Classify wrapped lines, headings, lists, and code blocks so code can rebuild Markdown. [Details](catalog/DETAILS.md#official-autoformat) |
| [Bounded function calling](https://docs.typesafe.ai/cookbooks/function_calling) | Map function names and finite argument choices into typed decisions. [Details](catalog/DETAILS.md#official-function-calling) |
| [Agent skill selection](https://docs.typesafe.ai/cookbooks/skill_suggestion) | Rank skills, inspect a small shortlist, and allow rejection of every candidate. [Details](catalog/DETAILS.md#official-skill-suggestion) |
| [Knowledge-graph entity alignment](https://docs.typesafe.ai/cookbooks/entity_alignment) | Decide whether candidate entities should merge, remain separate, or go to human review. [Details](catalog/DETAILS.md#official-entity-alignment) |
| [RAG passage classification](https://docs.typesafe.ai/cookbooks/classifying_rag_passages) | Check relevance, contradictions, and injected instructions between retrieval and generation. [Details](catalog/DETAILS.md#official-classifying-rag-passages) |
| [Citation checking](https://docs.typesafe.ai/cookbooks/citation_check) | Confirm that a quote exists, then judge whether its context supports the claim. [Details](catalog/DETAILS.md#official-citation-check) |
| [LLM input and output checks](https://docs.typesafe.ai/cookbooks/llm_guardrails) | Use hazard questions and severity scores to pass, review, or block content. [Details](catalog/DETAILS.md#official-llm-guardrails) |
| [Structured-extraction cascade](https://docs.typesafe.ai/cookbooks/sde_cascade) | Extract with a small model, verify fields with Jev, and escalate when needed. [Details](catalog/DETAILS.md#official-sde-cascade) |
| [Date extraction](https://docs.typesafe.ai/cookbooks/date_extraction_cookbook) | Select date components from text; deterministic code handles calendar calculations and validation. [Details](catalog/DETAILS.md#official-date-extraction-cookbook) |
| [Pre-parsed value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook) | Find candidate values with regex, let Jev choose, and copy the original span. [Details](catalog/DETAILS.md#official-pre-parsed-value-extraction-cookbook) |
| [Hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification) | Navigate label trees with probabilities, tracking errors at both branches and leaves. [Details](catalog/DETAILS.md#official-hierarchical-classification) |
| [Automatic feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery) | An LLM proposes questions, Jev produces numeric features, and CatBoost feeds errors back into the loop. [Details](catalog/DETAILS.md#official-autoresearch-feature-discovery) |
| [Classification with fallback labels](https://docs.typesafe.ai/cookbooks/classification_using_confidence) | Classify annual reports by industry, falling back to a broader label when confidence is low. [Details](catalog/DETAILS.md#official-classification-using-confidence) |

<a id="browser"></a>

## Browser, desktop & mobile

| Resource | Summary & details |
| --- | --- |
| [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) | Choose a browser operation and target together from a dynamic table of page elements. [Details](catalog/DETAILS.md#browser-use--jev-ultrafast) |
| [typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) | Read a Mac interface with OCR and accessibility APIs, then let Jev choose an action. [Details](catalog/DETAILS.md#awlevin--typesafe-computer-use) |
| [Jev Browser](https://github.com/jkudish/jev-browser) | Control a browser through a library, CLI, or MCP, with budgets, recovery, and decision traces. [Details](catalog/DETAILS.md#jkudish--jev-browser) |
| [Mobile Jev](https://github.com/droidrun/mobile-jev) | Select actions on a Mobilerun Android device from the current interface state. [Details](catalog/DETAILS.md#droidrun--mobile-jev) |
| [Unclutter](https://github.com/kitze/unclutter) | Identify page clutter with Jev and reuse template rules in a browser extension. [Details](catalog/DETAILS.md#kitze--unclutter) |
| [TypeSafe Fun AdBlocker](https://github.com/realZachi/typesafe-adblock) | Classify DOM elements as ads and remove them with browser code. [Details](catalog/DETAILS.md#realzachi--typesafe-adblock) |
| [Jev for Social Media](https://github.com/socai-io/jev-social) | Let Jev choose social-media operations while socai executes them in a browser. [Details](catalog/DETAILS.md#socai-io--jev-social) |
| [Retriever AI: Jev browser-agent benchmark](https://rtrvr.ai/blog/jev-browser-agent-benchmark) | A first-party report on Jev action selection with GLM planning, including speed gains and higher total cost. [Details](catalog/DETAILS.md#rtrvr-browser-benchmark) |

<a id="agents"></a>

## Coding agents & MCP

| Resource | Summary & details |
| --- | --- |
| [Typesafe MCP](https://github.com/itsmostafa/typesafe-mcp) | Expose Jev's typed decisions to coding assistants through an MCP server. [Details](catalog/DETAILS.md#itsmostafa--typesafe-mcp) |
| [Jev MCP (jkudish)](https://github.com/jkudish/jev-mcp) | MCP tools for verification, filtering, reranking, classification, and code review. [Details](catalog/DETAILS.md#jkudish--jev-mcp) |
| [fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction) | Score tool calls and results, trim stale content, and keep retained text verbatim. [Details](catalog/DETAILS.md#tamaratran--fast-jev-compaction) |
| [Foreman](https://github.com/thruwire/foreman) | Assess whether coding work is complete, sufficiently tested, or needs human input. [Details](catalog/DETAILS.md#thruwire--foreman) |
| [Winnow](https://github.com/GhalebDweikat/winnow) | Filter large tool outputs before they enter context, with a way to restore hidden text. [Details](catalog/DETAILS.md#ghalebdweikat--winnow) |
| [Jev Review (devagrawal09)](https://github.com/devagrawal09/jev-review) | Review diffs or repositories through staged risk screening, evidence selection, and severity scoring. [Details](catalog/DETAILS.md#devagrawal09--jev-review) |
| [Jev Review MCP](https://github.com/NiazMorshed2007/jev-review) | A local MCP server supplies ongoing software-quality scores to coding agents. [Details](catalog/DETAILS.md#niazmorshed2007--jev-review) |
| [Jev MCP (blakestone-x)](https://github.com/blakestone-x/jev-mcp) | MCP tools and request recipes for classification, scoring, matching, and screening. [Details](catalog/DETAILS.md#blakestone-x--jev-mcp) |

<a id="routing"></a>

## Model routing

| Resource | Summary & details |
| --- | --- |
| [Jev Codex Router](https://github.com/0xNatoshi/jev-codex-router) | Choose a model and reasoning depth for each conversation turn using Jev. [Details](catalog/DETAILS.md#0xnatoshi--jev-codex-router) |
| [jev-router](https://github.com/gargpratyush/jev-router) | Route each new Claude Code or Codex turn to an appropriate model tier. [Details](catalog/DETAILS.md#gargpratyush--jev-router) |

<a id="safety"></a>

## Moderation, rules & safety checks

| Resource | Summary & details |
| --- | --- |
| [Tripwire](https://github.com/noelzappy/tripwire) | Check model responses before delivery, with middleware, proxy, and configurable policies. [Details](catalog/DETAILS.md#noelzappy--tripwire) |
| [jev-gates](https://github.com/rashedInt32/jev-gates) | Check coding-agent rules, scope, and completion claims, escalating when needed. [Details](catalog/DETAILS.md#rashedint32--jev-gates) |
| [pi-warden](https://github.com/DevMortimer/pi-warden) | Check edits and tool use against project rules, retry loops, and completion evidence. [Details](catalog/DETAILS.md#devmortimer--pi-warden) |
| [Safer with Jev](https://github.com/andrelandgraf/safer-with-jev) | Demonstrate content judgments combined with optional HTTPS request forwarding. [Details](catalog/DETAILS.md#andrelandgraf--safer-with-jev) |
| [Triagedy](https://github.com/m0rphtail/triagedy) | Turn JSONL security alerts into typed triage decisions in a Unix-style pipeline. [Details](catalog/DETAILS.md#m0rphtail--triagedy) |

<a id="retrieval"></a>

## Retrieval & knowledge graphs

| Resource | Summary & details |
| --- | --- |
| [neo4jev](https://github.com/jexp/neo4jev) | Choose the next graph relationship and check whether the goal is reached in the same call. [Details](catalog/DETAILS.md#jexp--neo4jev) |

<a id="data"></a>

## Data & observability

| Resource | Summary & details |
| --- | --- |
| [pg-jev](https://github.com/realZachi/pg-jev) | A PostgreSQL extension filters, ranks, and classifies rows with natural-language conditions. [Details](catalog/DETAILS.md#realzachi--pg-jev) |
| [jevQL](https://github.com/kylemclaren/jevql) | Add client-side Jev judgments to queries against standard PostgreSQL. [Details](catalog/DETAILS.md#kylemclaren--jevql) |
| [duckdb-jev](https://github.com/colliber/duckdb-jev) | Return typed judgments over tables or Parquet data from DuckDB queries. [Details](catalog/DETAILS.md#colliber--duckdb-jev) |
| [Jev Logs](https://github.com/reachjalil/jevlogs) | Score OpenTelemetry logs before routing selected records to expensive analysis. [Details](catalog/DETAILS.md#reachjalil--jevlogs) |

<a id="automation"></a>

## Everyday automation & smart homes

| Resource | Summary & details |
| --- | --- |
| [Jev for Home Assistant](https://github.com/AboveColin/HA-Jev) | Ask questions about home state and return values for Home Assistant automations. [Details](catalog/DETAILS.md#abovecolin--ha-jev) |
| [jev-shell-history](https://github.com/mrnugget/jev-shell-history) | Rank existing zsh history entries against what the user is typing. [Details](catalog/DETAILS.md#mrnugget--jev-shell-history) |

<a id="applications"></a>

## Products & content tools

| Resource | Summary & details |
| --- | --- |
| [TypeSafe AI Playground (Rust CLI)](https://github.com/markjaquith/typesafe-ai-playground) | Rust CLI experiments for private-information detection, comment review, tone, and business classification. [Details](catalog/DETAILS.md#markjaquith--typesafe-ai-playground) |
| [Jev Moderation Bot](https://github.com/brainstormity/Jev-Moderation-Bot) | Moderate Discord spam and scam links with progressively stronger actions. [Details](catalog/DETAILS.md#brainstormity--jev-moderation-bot) |
| [JEVMETER](https://github.com/ChetasLua/jevmeter) | Score video transcripts sentence by sentence and render the results as an on-screen meter. [Details](catalog/DETAILS.md#chetaslua--jevmeter) |
| [Kill My Idea](https://github.com/monteduro/killmyidea) | Ask parallel questions about a startup idea and combine scores into a fixed verdict. [Details](catalog/DETAILS.md#monteduro--killmyidea) |

<a id="games"></a>

## Games & simulations

| Resource | Summary & details |
| --- | --- |
| [1v1 Jev](https://github.com/emrickgarrett/OneVOneJev) | A browser arena uses Jev to choose a game character's actions. [Details](catalog/DETAILS.md#emrickgarrett--onevonejev) |
| [TypeSafe Mario](https://github.com/fhshaik/typesafe-mario) | Translate emulator RAM and telemetry into state for Jev to select NES controller inputs. [Details](catalog/DETAILS.md#fhshaik--typesafe-mario) |
| [Jev Plays StarCraft](https://github.com/phyous/tsai-sc) | Drive a StarCraft shareware mission from structured state and record action probabilities. [Details](catalog/DETAILS.md#phyous--tsai-sc) |
| [Jev Pong](https://github.com/ably-labs/jev-pong) | Advance the Pong ball one step per model decision to visualize response latency. [Details](catalog/DETAILS.md#ably-labs--jev-pong) |
| [jev-drone](https://github.com/RomanSlack/jev-drone) | Use Jev for situational judgments in a MuJoCo drone simulation while code handles fast control. [Details](catalog/DETAILS.md#romanslack--jev-drone) |
| [Jev Chess Lab](https://github.com/denikuchero/jev-chess-lab) | Recorded chess experiments compare Jev alone, tactical filters, and Stockfish assistance. [Details](catalog/DETAILS.md#denikuchero--jev-chess-lab) |

<a id="evaluation"></a>

## Evaluation & calibration

| Resource | Summary & details |
| --- | --- |
| [jevcal](https://github.com/abhixhek/jevcal) | Choose confidence thresholds on your own data and detect changes after model updates. [Details](catalog/DETAILS.md#abhixhek--jevcal) |
| [Janus](https://github.com/FirasSX914/Janus) | Measure when to route between small and large models, including when routing should be rejected. [Details](catalog/DETAILS.md#firassx914--janus) |
| [jev-benchmarks](https://github.com/AbdelStark/jev-benchmarks) | Evaluate probability calibration, automation coverage, latency, and resource use. [Details](catalog/DETAILS.md#abdelstark--jev-benchmarks) |
| [typesafe-ai-benchmark](https://github.com/iammrduncan/typesafe-ai-benchmark) | Compare LLM structured output and Jev on matched application tasks. [Details](catalog/DETAILS.md#iammrduncan--typesafe-ai-benchmark) |
| [jev-secret-detection](https://github.com/teyhouse/jev-secret-detection) | Use a Noul question to measure whether code snippets contain usable secret credentials. [Details](catalog/DETAILS.md#teyhouse--jev-secret-detection) |

<a id="experiments"></a>

## Boundary experiments

| Resource | Summary & details |
| --- | --- |
| [jev-llm](https://github.com/Code-Forge-AU/jev-llm) | Build a text-generation experiment by repeatedly selecting the next word from candidates. [Details](catalog/DETAILS.md#code-forge-au--jev-llm) |

## Keep the index up to date

English is the source edition. Edit `data/resources.json`, update the three translations in `data/locales/`, and regenerate all editions together. Python 3.10+; no packages or API keys required.

```sh
python3 scripts/catalog.py
python3 scripts/catalog.py --check
python3 scripts/catalog.py --search browser --lang en
```

Checks cover data, translation completeness, duplicates, generated files, and local links. They do not test remote availability or call model APIs.

See the [review methodology](docs/METHODOLOGY.md), [research log](docs/RESEARCH.md), and [contribution guide](CONTRIBUTING.md). Original annotations and scripts are [MIT-licensed](LICENSE); linked resources retain their own licenses.
