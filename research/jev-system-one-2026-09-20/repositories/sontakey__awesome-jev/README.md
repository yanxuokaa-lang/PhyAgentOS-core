# Awesome Jev

**Public projects that use [Jev](https://typesafe.ai/), TypeSafe AI's System One model.** Unofficial. Not affiliated with TypeSafe AI.

Jev does not chat, write code, or see images. It returns Choice, Score, or Noul answers with probabilities. Your code decides what happens next.

[![CC BY 4.0](https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey.svg)](LICENSE)
[![catalog](https://img.shields.io/badge/catalog-55_entries-111.svg)](data/use-cases.json)
[![updated](https://img.shields.io/badge/updated-2026.09.19-0a0.svg)](docs/research-method.md)

## Contents

- [Action-taking projects](#action-taking-projects) (14)
- [Model and skill routing](#model-and-skill-routing) (5)
- [Email and inbox routing](#email-and-inbox-routing) (1)
- [MCP and agent bridges](#mcp-and-agent-bridges) (3)
- [Official cookbooks and patterns](#official-cookbooks-and-patterns) (4)
- [Official SDKs and adapter](#official-sdks-and-adapter) (3)
- [Official docs, skill, and launch demos](#official-docs-skill-and-launch-demos) (4)
- [Platform integrations](#platform-integrations) (1)
- [Community clients](#community-clients) (5)
- [Installable agent skills](#installable-agent-skills) (3)
- [Other awesome-Jev lists](#other-awesome-jev-lists) (9)
- [Related, not TypeSafe Jev](#related-not-typesafe-jev) (3)
- [Quick start](#quick-start)
- [Evidence](#evidence)
- [Details](#details)
- [Contributing](#contributing)
- [Credits](#credits)

Related open reproductions sit in [Related, not TypeSafe Jev](#related-not-typesafe-jev). They are not Jev use cases. Unbuilt ideas are in [docs/ideas.md](docs/ideas.md), not in the catalog count.

## Action-taking projects

- [Jev Ultrafast browser agent](https://github.com/browser-use/jev-ultrafast) — Uses Jev to pick the next browser operation and target from an indexed DOM; a small LLM only types text. Maintained by [Browser Use](https://github.com/browser-use). `demo-inspected` <!-- catalog:jev-ultrafast -->
- [TypeSafe Mario](https://github.com/fhshaik/typesafe-mario) — Uses Jev to choose NES controller macros from emulator RAM JSON, not screenshots. By [@fhshaik](https://github.com/fhshaik). `code-inspected` <!-- catalog:typesafe-mario -->
- [TypeSafe Computer Use](https://github.com/awlevin/typesafe-computer-use) — OCRs a Mac screen, then Jev chooses the next UI action and the code clicks. By [Aaron Levin](https://github.com/awlevin). `code-inspected` <!-- catalog:typesafe-computer-use -->
- [Jev Review](https://github.com/devagrawal09/jev-review) — Runs staged Jev judgments over git diffs or a local codebase and shows them on a dashboard. By [Dev Agrawal](https://github.com/devagrawal09). `code-inspected` <!-- catalog:jev-review -->
- [pg-jev](https://github.com/realZachi/pg-jev) — PostgreSQL helpers that filter, sort, or classify rows with Jev. By [@realZachi](https://github.com/realZachi). `code-inspected` <!-- catalog:pg-jev -->
- [pi-warden](https://github.com/DevMortimer/pi-warden) — Asks Jev whether a Pi agent tool call is irreversible or off-task before it runs. By [Ryan Joshua](https://github.com/DevMortimer). `demo-inspected` <!-- catalog:pi-warden -->
- [Foreman](https://github.com/thruwire/foreman) — Uses the official Python SDK so a software-factory supervisor can judge worker steps. Maintained by [ThruWire](https://github.com/thruwire). `code-inspected` <!-- catalog:foreman -->
- [beadsort](https://github.com/harrymunro/beadsort) — Uses Jev to label beads issues from their text. By [Harry Munro](https://github.com/harrymunro). `demo-inspected` <!-- catalog:beadsort -->
- [JEVMETER](https://github.com/ChetasLua/jevmeter) — Scores transcript sentences with Jev, then renders an edited video. By [Chetas Lua](https://github.com/ChetasLua). `demo-inspected` <!-- catalog:jevmeter -->
- [blink](https://github.com/ellipsis-dev/blink) — Walks the filesystem and uses Jev to score which files match a natural-language query. Maintained by [ellipsis.dev](https://github.com/ellipsis-dev). `code-inspected` <!-- catalog:blink-code-search -->
- [neo4jev](https://github.com/jexp/neo4jev) — Walks a Neo4j graph by asking Jev which neighboring relationship to follow. By [Michael Hunger](https://github.com/jexp). `demo-inspected` <!-- catalog:neo4jev -->
- [semdecide](https://github.com/sharziki/semdecide) — Turns Jev judgments into Unix pipeline exit codes or JSON. By [Sharvil Saxena](https://github.com/sharziki). `demo-inspected` <!-- catalog:semdecide -->
- [Jev Search](https://github.com/superagents-lab/jev-search) — Uses Jev to choose search sources and time ranges from a plain-language request, then rank the returned results. Maintained by [SuperAgents Lab](https://github.com/superagents-lab). `code-inspected` <!-- catalog:jev-search -->
- [Jev for social media](https://github.com/socai-io/jev-social) — Uses Jev to choose the next read-only social media operation from a changing list of concrete targets. Maintained by [socai-io](https://github.com/socai-io). `code-inspected` <!-- catalog:jev-social -->

## Model and skill routing

- [jev-router](https://github.com/gargpratyush/jev-router) — Uses Jev to pick a model for each Claude Code or Codex request. By [Pratyush Garg](https://github.com/gargpratyush). `code-inspected` <!-- catalog:jev-router -->
- [Jev Codex Router](https://github.com/0xNatoshi/jev-codex-router) — Classifies each Codex Router turn with Jev, then code picks model, effort, and tier. By [@0xNatoshi](https://github.com/0xNatoshi). `code-inspected` <!-- catalog:jev-codex-router -->
- [SkillRanker](https://github.com/Dicklesworthstone/skillranker) — Ranks which agent skill fits the next step from live session context. By [Jeff Emanuel](https://github.com/Dicklesworthstone). `code-inspected` <!-- catalog:skillranker -->
- [Official skill-suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion) — Two Jev requests rank 182 Hermes skills and may suggest none. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `documented-example` <!-- catalog:cookbook-skill-suggestion -->
- [Jev Agent Skill Router](https://github.com/GodsBoy/jev-agent-skill-router) — Routes over a skill catalogue with Jev Choice and Noul gates; it does not load the skills. By [Dewaldt Huysamen](https://github.com/GodsBoy). `code-inspected` <!-- catalog:jev-agent-skill-router -->

## Email and inbox routing

- [Jev email intent workflow](https://github.com/GiesN/typesafe-jev-workflow) — LangGraph demo that classifies mocked emails as invoice or general with Jev. By [@GiesN](https://github.com/GiesN). `code-inspected` <!-- catalog:email-jev-langgraph -->

## MCP and agent bridges

- [Jev MCP (jkudish)](https://github.com/jkudish/jev-mcp) — MCP tools that verify claims, screen content, and rank candidates with Jev. By [Joey Kudish](https://github.com/jkudish). `code-inspected` <!-- catalog:jev-mcp -->
- [typesafe-mcp](https://github.com/itsmostafa/typesafe-mcp) — Community MCP that exposes TypeSafe System One to Claude or Codex. By [@itsmostafa](https://github.com/itsmostafa). `demo-inspected` <!-- catalog:typesafe-mcp -->
- [y0usaf/typesafe-mcp](https://github.com/y0usaf/typesafe-mcp) — One MCP evaluate(state, questions) tool that POSTs to the TypeSafe API. By [Sami Ansari](https://github.com/y0usaf). Announced by [@realy0usaf](https://x.com/realy0usaf). `code-inspected` <!-- catalog:y0usaf-typesafe-mcp -->

## Official cookbooks and patterns

- [Official function-calling cookbook](https://docs.typesafe.ai/cookbooks/function_calling) — Maps a natural-language trading request onto typed functions and closed-set arguments. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `documented-example` <!-- catalog:cookbook-function-calling -->
- [Official LLM guardrails cookbook](https://docs.typesafe.ai/cookbooks/llm_guardrails) — Screens an LLM input or output for hazards, then code chooses pass, review, block, or support. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `documented-example` <!-- catalog:cookbook-guardrails -->
- [Official citation-check cookbook](https://docs.typesafe.ai/cookbooks/citation_check) — Checks whether a quote's context supports a claim. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `documented-example` <!-- catalog:cookbook-citation-check -->
- [Official intent-routing pattern](https://docs.typesafe.ai/patterns/intent-routing) — Classifies a request, then code routes to deterministic logic, a specialist LLM, or a human. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `documented-example` <!-- catalog:pattern-intent-routing -->

## Official SDKs and adapter

- [TypeSafe Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python) — Official Python client for POST /v1/systemone. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `code-inspected` <!-- catalog:official-sdk-python -->
- [TypeSafe JavaScript SDK](https://github.com/typesafe-ai/typesafe-sdk-js) — Official TypeScript/JavaScript client with inferred answer types. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `demo-inspected` <!-- catalog:official-sdk-js -->
- [System One Adapter (Python)](https://github.com/typesafe-ai/system-one-adapter-python) — Drop-in TypeSafeClient.system_one backed by OpenAI or Anthropic instead of Jev. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `code-inspected` <!-- catalog:official-system-one-adapter -->

## Official docs, skill, and launch demos

- [TypeSafe documentation](https://docs.typesafe.ai/llms.txt) — Live docs for the System One model, primitives, API, cookbooks, and demos. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `documented-example` <!-- catalog:official-docs -->
- [Official TypeSafe agent skill](https://github.com/typesafe-ai/skills) — SKILL.md that teaches agents to design System One workflows from the live docs. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `code-inspected` <!-- catalog:official-skills -->
- [Introducing System One Models and Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) — Launch post (2026-09-15) covering RLCD, pricing, workflow evals, and Doom and Wikipedia-race videos. By Diogo Almeida. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `author-claim` <!-- catalog:official-launch-blog -->
- [Smart home assistant demo](https://docs.typesafe.ai/demos/smart-home) — Official demo that evaluates smart-home requests with speculative questions and an LLM fallback. Maintained by [TypeSafe AI](https://github.com/typesafe-ai). `documented-example` <!-- catalog:demo-smart-home -->

## Platform integrations

- [Vercel AI Gateway + AI SDK evaluate](https://ai-sdk.dev/docs/ai-sdk-core/evaluation) — Jev as typesafe-ai/jev on AI Gateway, plus AI SDK 7 experimental_evaluate. Maintained by [Vercel](https://github.com/vercel). `documented-example` <!-- catalog:vercel-ai-gateway-jev -->

## Community clients

- [ruby_llm-typesafe](https://github.com/kieranklaassen/ruby_llm-typesafe) — TypeSafe structured-output provider for RubyLLM 2. By [Kieran Klaassen](https://github.com/kieranklaassen). `demo-inspected` <!-- catalog:ruby-llm-typesafe -->
- [TypeSafeAI.Net](https://github.com/Hawxy/TypeSafeAI.Net) — Unofficial .NET SDK for TypeSafe AI. By [@Hawxy](https://github.com/Hawxy). `demo-inspected` <!-- catalog:typesafeai-net -->
- [typesafe-sdk-go](https://github.com/Tangerg/typesafe-sdk-go) — Dependency-free Go client for the TypeSafe System One API. By [@Tangerg](https://github.com/Tangerg). `code-inspected` <!-- catalog:typesafe-sdk-go-tangerg -->
- [JevSwiftSDK](https://github.com/NSStudent/JevSwiftSDK) — Dependency-free Swift package for the System One HTTP API. By [@NSStudent](https://github.com/NSStudent). `code-inspected` <!-- catalog:jev-swift-sdk -->
- [typesafe-sdk (Ruby)](https://github.com/joshmn/typesafe-sdk) — Ruby gem client for the TypeSafe System One API. By [@joshmn](https://github.com/joshmn). `code-inspected` <!-- catalog:typesafe-sdk-ruby -->

## Installable agent skills

- [building-with-jev skill](https://github.com/dbreunig/building-with-jev-skill) — Community skill for writing Jev programs (Claude plugin and skills.sh). By [Drew Breunig](https://github.com/dbreunig). `code-inspected` <!-- catalog:building-with-jev-skill -->
- [jev-axi](https://github.com/shiftynick/jev-axi) — CLI and skill for log triage, diff review, untrusted-text screening, and ranking. By [Nicholas Underwood](https://github.com/shiftynick). `code-inspected` <!-- catalog:jev-axi -->
- [advocaat](https://github.com/pithings/advocaat) — Small TypeScript ask() client plus an agent skill over Jev. Maintained by [PiThings](https://github.com/pithings). `code-inspected` <!-- catalog:advocaat -->

## Other awesome-Jev lists

- [awesome-jev-by-typesafe (Anil-matcha)](https://github.com/Anil-matcha/awesome-jev-by-typesafe) — Independent Jev list with examples and prompts (highest star count among lists in this sweep). By [Anil Chandra Naidu Matcha](https://github.com/Anil-matcha). `demo-inspected` <!-- catalog:list-anil-matcha -->
- [awesome-typesafe (AbdelStark)](https://github.com/AbdelStark/awesome-typesafe) — Official plus community directory with an independent disclaimer. By [@AbdelStark](https://github.com/AbdelStark). `demo-inspected` <!-- catalog:list-abdelstark -->
- [awesome-jev (yibie)](https://github.com/yibie/awesome-jev) — Category field guide that requires actual Jev use. By [@yibie](https://github.com/yibie). `demo-inspected` <!-- catalog:list-yibie -->
- [awesome-jev (AnotiaWang)](https://github.com/AnotiaWang/awesome-jev) — Bilingual EN/ZH awesome list (CC0). By [Andy Wang](https://github.com/AnotiaWang). `demo-inspected` <!-- catalog:list-anotia -->
- [awesome-jev (hellogumbo)](https://github.com/hellogumbo/awesome-jev) — Directory claiming hundreds of entries, plus awesomejev.com. Maintained by [GUMBO](https://github.com/hellogumbo). `author-claim` <!-- catalog:list-hellogumbo -->
- [awesome-jev (rhc98)](https://github.com/rhc98/awesome-jev) — Auto-judged catalog: README says Jev curated the list. By [@rhc98](https://github.com/rhc98). `author-claim` <!-- catalog:list-rhc98 -->
- [awesome-jev (cobanov)](https://github.com/cobanov/awesome-jev) — Source-backed list that publishes dated research notes alongside each review. By [Mert Cobanov](https://github.com/cobanov). `demo-inspected` <!-- catalog:list-cobanov -->
- [awesome-jev-projects (logicrw)](https://github.com/logicrw/awesome-jev-projects) — Bilingual ecosystem radar with a published site and automatic GitHub sync. By [@logicrw](https://github.com/logicrw). `demo-inspected` <!-- catalog:list-logicrw -->
- [awesome-jev (AppitStudio)](https://github.com/AppitStudio/awesome-jev) — Directory split into Jev-powered apps, developer resources, and small inspectable workflows. Maintained by [AppitStudio](https://github.com/AppitStudio). `demo-inspected` <!-- catalog:list-appitstudio -->

## Related, not TypeSafe Jev

- [OpenJev](https://github.com/TheoLeeCJ/openjev) — Community open-weight attempt at the System One shape. Not api.typesafe.ai. By [Theodore Lee](https://github.com/TheoLeeCJ). `author-claim` <!-- catalog:openjev -->
- [jevlike](https://github.com/vinnylarouge/jevlike) — Another community reproduction of the System One interface. By [@vinnylarouge](https://github.com/vinnylarouge). `author-claim` <!-- catalog:jevlike -->
- [jevmlx](https://github.com/bnsd55/jevmlx) — Jev-style parallel constrained decisions for MLX models on Apple Silicon. By [@bnsd55](https://github.com/bnsd55). `demo-inspected` <!-- catalog:jevmlx -->


## Quick start

1. Docs index: [docs.typesafe.ai/llms.txt](https://docs.typesafe.ai/llms.txt)
2. Python: `uv add typesafe-sdk` · JS: `npm install @typesafe-ai/sdk` (need `TYPESAFE_API_KEY`)
3. Agent skill: `npx skills add typesafe-ai/skills --skill typesafe-ai` or Claude Code plugin `typesafe@typesafe-ai`
4. HTTP: `POST https://api.typesafe.ai/v1/systemone`

## Evidence

| Badge | Meaning |
| --- | --- |
| `code-inspected` | README plus relevant source or example files were read |
| `demo-inspected` | A documented demo, cookbook run, or live page was inspected |
| `documented-example` | Official docs/cookbook/changelog |
| `author-claim` | Author or press described it; implementation not fully inspected |
| `proposed` | Not built; see [skill opportunities](docs/skill-opportunities.md) |

Vendor speed and cost charts are not remeasured here. Treat launch-week latency and “N users” claims as marketing unless a source is marked inspected.

## Details

Actions, caveats, and sources for every entry: [docs/catalog.md](docs/catalog.md) (generated from [data/use-cases.json](data/use-cases.json)).

How the sweep was done: [research method](docs/research-method.md). Skill-shaped gaps: [skill opportunities](docs/skill-opportunities.md).

This list is smaller than auto-generated directories on purpose. It includes a full public `typesafe-ai` org inventory (10 repos: 4 product, 3 supporting, 3 unrelated forks), evidence badges, and action-taking projects first.

Gaps: the first X lane used indexed web pages (`web_search`/`web_extract` of x.com; native `x_search` was unavailable). A 2026-09-17 native `x_search` rerun added two catalog entries. Google SERP was unavailable. No TypeSafe inference in this sweep.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs need a public source, an evidence level, and creator credit. Run `python3 scripts/validate.py`.

## Credits

README format inspired by [Awesome Claude Skills](https://github.com/ComposioHQ/awesome-claude-skills) from [ComposioHQ](https://github.com/ComposioHQ). That list's prose, branding, logos, and affiliate links are not copied here.

Each project credits its author or maintainer from public README, package, or repository metadata. Other [awesome-Jev lists](#other-awesome-jev-lists) are listed as lists; their curators are credited there. This catalog does not claim those projects were all found independently of those lists.

TypeSafe, Jev, and System One are marks of TypeSafe AI.

## License

Original curation is [CC BY 4.0](LICENSE). Upstream code and docs keep their own licenses.

Updated 2026-09-19.
