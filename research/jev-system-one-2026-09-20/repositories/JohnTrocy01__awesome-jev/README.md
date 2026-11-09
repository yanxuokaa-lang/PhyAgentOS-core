# Awesome Jev

Open-source projects built with [TypeSafe Jev](https://typesafe.ai), with submissions reviewed by Jev.

[Submit a project](CONTRIBUTING.md) · [How reviews work](#how-reviews-work) · [Jev Review Action](https://github.com/fatwang2/jev-review-action)

## Projects

71 projects.

### SDKs

- [advocaat](https://github.com/pithings/advocaat) — A small, type-safe client for asking AI questions about your data, powered by TypeSafe Jev\.
- [jev](https://github.com/dannote/jev) — TypeSafe Jev for OTP: reply to Jev from a GenServer and pattern match on its answer
- [jev-go](https://github.com/Gaurav-Gosain/jev-go) — Go client for TypeSafe's System One API and its model Jev: typed judgments and calibrated probabilities instead of generated text
- [jev-go](https://github.com/Stumble/jev-go) — An independent Go SDK for TypeSafe AI's Jev / System One API\.
- [jevclient](https://github.com/AboveColin/jevclient) — Async Python client for TypeSafe Jev\. Typed questions in, probabilities and choices out, no prose to parse\.
- [swift-typesafe](https://github.com/ainame/swift-typesafe) — Swift 6\.4 SDK for TypeSafe AI, following the Python SDK's 0\.6\.0 API\.
- [TypeSafe JavaScript SDK](https://github.com/typesafe-ai/typesafe-sdk-js) — Official JavaScript and TypeScript client for TypeSafe's typed decision API, with question builders and typed responses\.
- [TypeSafe Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python) — Official Python client for TypeSafe's typed decision API, with synchronous and asynchronous clients\.
- [typesafe\_sdk](https://github.com/nshkrdotcom/typesafe_sdk) — typesafe\_sdk is the Elixir SDK for TypeSafe AI and its first System One model, Jev\.
- [typesafe\_sdk\_ex](https://github.com/vinnie357/typesafe_sdk_ex) — Typesafe AI SDK in Elixir using Req
- [typesafe-ai](https://github.com/Twister915/typesafe-ai) — typesafe-ai brings TypeSafe's System One evaluation API into Rust as small, typed judgments that fit inside ordinary application code\.
- [typesafe-ai-rs](https://github.com/gilljon/typesafe-ai-rs) — An independent Rust client for the TypeSafe AI System One API, maintained at gilljon/typesafe-ai-rs\.
- [typesafe-rs](https://github.com/AbdelStark/typesafe-rs) — Evaluate a state against named questions \(noul, choice, score\) and get one typed answer per question\.
- [typesafe-sdk](https://github.com/joshmn/typesafe-sdk) — A Ruby client for the TypeSafe System One API\.
- [typesafe-sdk-go](https://github.com/Tangerg/typesafe-sdk-go) — Go SDK for the TypeSafe AI API — typed questions in, probability distributions out\.
- [typesafe-sdk-php](https://github.com/Butochnikov/typesafe-sdk-php) — PHP client for the TypeSafe AI System One API\.
- [typesafeai-dotnet-sdk](https://github.com/saibimajdi/typesafeai-dotnet-sdk) — Community \.NET SDK for the TypeSafe AI System One API — typed noul, choice, and score questions with structured, confidence-scored answers\. Not affiliated with TypeSafe AI\.
- [zio-typesafe-ai](https://github.com/jamesward/zio-typesafe-ai) — A Scala 3 / ZIO library for TypeSafe AI's Jev / System One API — a "System One model" that answers typed, atomic questions about a piece of state instead of generating text\.

### Integration

- [fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction) — Claude Code plugin that replaces the compaction summary with Jev decisions: every tool call and result is scored in one fast request, stale ones are dropped or truncated, everything kept stays verbatim\.
- [ha-conversation-jev](https://github.com/luxus/ha-conversation-jev) — Home Assistant custom conversation agent: Jev \(TypeSafe System One, jev-latest\) classifies an utterance, then either calls a light service \(v0 fast path\) or hands off to the SpaceXAI Grok conversation agent\.
- [hermes-jev](https://github.com/keeltrace/hermes-jev) — It is built for narrow, typed judgments that should not require the main generative model to improvise an answer: routing, ranking, verification, multi-question assessment, tool gating, and context-value decisions\.
- [hono-jev-router](https://github.com/yusukebe/hono-jev-router) — Hono router that uses TypeSafe Jev to match HTTP requests against natural-language route descriptions\.
- [Jev for Home Assistant](https://github.com/AboveColin/HA-Jev) — Home Assistant integration that turns Jev answers into sensors, adds four automation actions returning a probability, a choice with its distribution or a score, and provides a conversation agent for Assist that maps a spoken command onto Home Assistant's built-in intents\.
- [Jev MCP](https://github.com/jkudish/jev-mcp) — MCP server that uses TypeSafe Jev for claim verification, content screening, and semantic candidate ranking\.
- [jev-browser](https://github.com/Ying-Kai-Liao/jev-browser) — Browser automation where an LLM plans and Jev \(Typesafe System One\) decides\. Library, CLI and MCP server\.
- [jev-ego](https://github.com/romaluev/jev-ego) — TypeScript browser agent for ego lite — Jev Ultrafast's indexed action space, without Chrome, Playwright, or Browser Harness\.
- [jev-starter](https://github.com/hamakyo/jev-starter) — Typed, policy-driven decision workflows on top of TypeSafe AI Jev: confidence routing, fallbacks, evaluation, and RAG patterns for TypeScript apps\.
- [laravel-typesafe-jev](https://github.com/Butochnikov/laravel-typesafe-jev) — Unofficial Laravel integration for TypeSafe Jev AI with typed responses, async requests, scoped dependency injection, and testing fakes\.
- [pg\_typesafe](https://github.com/giuliosmall/pg_typesafe) — PostgreSQL extension that calls TypeSafe Jev from SQL for Choice, Noul, and Score, including batched detect and classify\.
- [ruby\_llm-typesafe](https://github.com/kieranklaassen/ruby_llm-typesafe) — TypeSafe structured-output provider for RubyLLM 2
- [Typesafe MCP](https://github.com/itsmostafa/typesafe-mcp) — MCP server that exposes TypeSafe Jev structured evaluations to coding agents and desktop clients\.
- [typesafe-ai-rails](https://github.com/GenieRobot/typesafe-ai-rails) — Community Rails integration for TypeSafe AI's System One API, built on the community typesafe-sdk Ruby gem\.

### Developer tools

- [blink](https://github.com/ellipsis-dev/blink) — Search a codebase with Jev using an ensemble of walkers that walk the file system to find a file\.
- [Jev Codex Router](https://github.com/0xNatoshi/jev-codex-router) — Codex proxy that uses TypeSafe Jev judgments to route coding turns to different models\.
- [Jev Review](https://github.com/devagrawal09/jev-review) — Code-review workflow that uses TypeSafe Jev structured judgments to assess changes and codebases, with a local results dashboard\.
- [Jev Review Action](https://github.com/fatwang2/jev-review-action) — Configurable GitHub Action using Jev to review directory submissions and classify pull requests, with evidence links and template-generated comments\.
- [jev-axi](https://github.com/shiftynick/jev-axi) — Command-line interface that sends typed questions to TypeSafe Jev so coding agents can gate shell commands before they run, classifying routine commands locally before any request is made\.
- [jev-belay](https://github.com/valentynkit/jev-belay) — Claude Code Stop hook that checks the transcript for evidence before trusting a "done" claim, spending one four-question Jev call only when files changed with no passing check since, and failing open on every error path\.
- [jev-code](https://github.com/devagrawal09/jev-code) — jev-code is a command-line toolkit that coding agents can delegate judgment-heavy work to\.
- [jev-commit](https://github.com/valentynkit/jev-commit) — Pre-commit hook where one Jev call judges whether the commit message matches the staged diff, flags debug leftovers and unmentioned work, and blocks only when it detects a credential\.
- [jev-curate](https://github.com/AkashPriyadarshii/jev-curate) — Synthetic dataset sifter that streams JSONL and Parquet rows through TypeSafe Jev Noul checks to disk\.
- [jev-git](https://github.com/AkashPriyadarshii/jev-git) — Sub-second Git pre-commit and pre-push reflex gate that screens staged diffs for secrets and destructive commands using TypeSafe Jev\.
- [jev-pref](https://github.com/doeixd/jev-pref) — CLI that turns project preferences from agent instruction files into jev-pref\.json rules and uses TypeSafe Jev to review code hunks, staged files, or pull requests against them, returning findings to coding agents\.
- [jev-scout](https://github.com/AkashPriyadarshii/jev-scout) — Zero-hallucination open-source repo and crate scout powered by TypeSafe AI Jev System One scoring\.
- [jev-seo](https://github.com/AkashPriyadarshii/jev-seo) — Zero-cost, agent-first SEO &amp; Generative Engine Optimization \(GEO\) search radar CLI suite and MCP server powered by DuckDuckGo and TypeSafe Jev System One\.
- [jev-superpowers](https://github.com/AkashPriyadarshii/jev-superpowers) — Systematic software development framework for AI coding agents upgraded with TypeSafe Jev System One typed decisions, zero-hallucination package vetting, and completion gates\.
- [jev\.nvim](https://github.com/valentynkit/jev.nvim) — Neovim plugin that splits the buffer into functions with Treesitter, scores each against a plain-language question with Jev, and ranks answers by probability in the quickfix window\.
- [jevkit](https://github.com/ariel-frischer/jevkit) — jevkit is a Rust CLI for TypeSafe Jev that validates Choice, Score, and Noul question sets with 13 offline lint rules before sending the request to the /api/alpha/decisions endpoint and prints the parsed answers as JSON\.
- [JevSeek](https://github.com/morcoan/JevSeek) — Desktop and CLI coding agent that uses Jev to select the next tool from user intent and recorded execution results\.
- [Leanest](https://github.com/baronunread/leanest) — Local-first test selector that uses TypeSafe Jev semantic judgments to decide which tests are safe to skip for a given code change, dropping straight into CI via its bundled GitHub Action\.
- [SemDecide](https://github.com/sharziki/semdecide) — CLI that uses TypeSafe Jev for semantic predicates, classification, scoring, and filtering in Unix pipelines\.
- [Supercov](https://github.com/supercorp-ai/supercov) — Code quality and coverage CLI for coding agents that uses TypeSafe Jev to assess source-code quality\.
- [TypeSafe AI Playground](https://github.com/markjaquith/typesafe-ai-playground) — Rust CLI with TypeSafe Jev experiments for PHI detection, code-comment review, tone analysis, and classification\.
- [Winnow](https://github.com/GhalebDweikat/winnow) — Claude Code tool-output filter that uses TypeSafe Jev to judge which blocks are relevant to the current task\.

### Search

- [hev reranker](https://github.com/hev/reranker) — Python library using Jev Noul judgments to score candidate documents for query relevance, then sort or filter the results\.
- [Jev Search](https://github.com/superagents-lab/jev-search) — Web search using Jev to choose sources, time ranges and query candidates, then rank Search1API results by relevance\.
- [neo4jev](https://github.com/jexp/neo4jev) — Neo4j graph navigation demo that uses TypeSafe Jev to select relationships and check goals during beam search\.

### Applications

- [Jev Trade](https://github.com/aowang-ai/jev-trade) — Live Hyperliquid desk: each tick Jev answers Choice questions for long/short, open/close/hold, and leverage; application code quotes or sends no order\. Documents a dry-run path; a live key sends real orders\.
- [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) — Python browser agent using Jev to select operations and DOM targets, with a separate text model for typing\.
- [jev-skip](https://github.com/valentynkit/jev-skip) — Browser extension that reads the YouTube caption track and paints a per-segment sponsor probability on the seek bar before the intro ends, with no crowd database, reporting 77% of SponsorBlock's sponsor seconds caught over 23 videos at $0\.0008 a video\.
- [jev-trader](https://github.com/jarrodwatts/jev-trader) — A TypeSafe Jev model watches the Kuru MON-USDC order book and answers buy or sell every \~300 ms\.
- [Jev-Trades](https://github.com/zadescoxp/Jev-Trades) — A Next\.js dashboard for live crypto market data and TypeSafe-powered paper trading\.
- [mobile-jev](https://github.com/droidrun/mobile-jev) — A standalone mobile agent for Mobilerun, powered by TypeSafe's Jev and the Mobilerun API\.
- [typesafe-ai-playground](https://github.com/BunsDev/typesafe-ai-playground) — A community playground for TypeSafe AI's Jev: edit classification experiments, compare A/B inputs, route conversations, extract document fields, inspect code-policy decisions, and explore games and simulations built around typed model outputs\.
- [typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) — macOS computer-use tool using Jev to choose actions from OCR and accessibility state, with a separate model for free-text writing\.
- [UI Generator Instinct Jev](https://github.com/joevidev/ui-generator-instinct-jev) — A demo app where the user describes a UI case in free text and Jev \(TypeSafe's System One model\) answers typed Choice/Noul/Score questions to pick and configure a real shadcn/ui component or page block, never generating code or copy\.
- [unclutter](https://github.com/kitze/unclutter) — Jev classifies nonessential page elements through Vercel AI Gateway or TypeSafe AI directly; the extension stores and reapplies local hiding rules by page template\.

### Games

- [jev-plays-pokemon-red](https://github.com/valentynkit/jev-plays-pokemon-red) — Pokemon Red on PyBoy where deterministic code owns the route and arithmetic, Jev picks only at branches, and every battle turn's faint prediction is scored by Brier against RAM state\.
- [PlayJev](https://github.com/OmniJev/PlayJev) — Qwen3\.5-0\.8B-Base fine-tuned on frames labelled by ten per-game search programs to play ten browser games from 448 px screenshots, reading a probability over each game's option list off one forward pass instead of generating text, and serving the Jev /v1/systemone request and response schema\.

### Research

- [LitJev](https://github.com/zhengxuyu/litjev) — Open reproduction of Jev's decision layer on Qwen models that serves the Jev /v1/systemone request and response schema \(choice, score, noul\) from a local Hugging Face checkpoint by reading option logits instead of generating text, with an MMLU-Pro direct-answer benchmark\.
- [typesafe-ai-benchmark](https://github.com/iammrduncan/typesafe-ai-benchmark) — This benchmark runs Qwen 3\.8 27B on Cerebras and TypeSafe Jev side by side across seven synthetic workloads, with a separate local Needle 3 evaluation on the same contracts\.

## Submit a project

Add up to ten project entries in a PR using the [contribution guide](CONTRIBUTING.md). Each project is reviewed independently. Source paths are optional—the reviewer looks for integration code automatically. You can also [ask for help submitting](https://github.com/fatwang2/awesome-jev/issues/new?template=submission.yml).

## How reviews work

[Jev Review Action](https://github.com/fatwang2/jev-review-action) checks source evidence, reviews the project description and setup instructions, and suggests a category. Jev supplies typed judgments; code renders the comment. Maintainers decide what gets merged.

See the [review policy](.github/jev-review.json) and [validation records](docs/reviews/README.md).

## About

An independent project by [fatwang2](https://github.com/fatwang2), not affiliated with TypeSafe. Inclusion is not a certification. [MIT licensed](LICENSE); listed projects retain their own licenses.
