# Awesome Jev [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

[![Site](https://img.shields.io/badge/site-awesome--jev.xyz-111827)](https://awesome-jev.xyz) [![Curated](https://img.shields.io/badge/curated-2026-09-19-2563eb)](https://awesome-jev.xyz/?sort=newest) [![Judged](https://img.shields.io/badge/judged-2187%20repos-16a34a)](https://awesome-jev.xyz/?status=all) ![Listed](https://img.shields.io/badge/listed-1633-16a34a)

> Projects built on [Jev](https://typesafe.ai), TypeSafe AI's System One model. Curated by Jev itself.

Every repository here was collected from GitHub, then judged by Jev in a single call: is it genuinely about Jev, which category, which decision pattern, and how substantial, documented, and novel it is. Code applies the policy; nothing below was hand-picked. The full index with probabilities lives on the site, along with the [review queue](https://awesome-jev.xyz/review) of borderline cases.

This is an independent community project, not affiliated with TypeSafe AI. Jev and System One are TypeSafe AI product names.

![Pipeline: GitHub search and community lists feed candidates into code, Jev judges each repository in one call, code applies the policy with human overrides, and the README and site are published daily.](docs/diagrams/pipeline.png)

## Contents

- [Official](#official)
- [SDKs and Clients](#sdks-and-clients)
- [Integrations](#integrations)
- [Agent and Developer Tooling](#agent-and-developer-tooling)
- [Applications](#applications)
- [Games, Robotics, and Simulation](#games-robotics-and-simulation)
- [Research, Evals, and Reimplementations](#research-evals-and-reimplementations)
- [Learning](#learning)
- [Other Lists](#other-lists)
- [Other](#other)
- [How This List Is Made](#how-this-list-is-made)

## Official

Maintained by TypeSafe AI.

- [system-one-adapter-python](https://github.com/typesafe-ai/system-one-adapter-python) - Drop-in TypeSafeClient replacement backed by LLM APIs.
- [typesafe-sdk-js](https://github.com/typesafe-ai/typesafe-sdk-js) - The official TypeScript/JavaScript library for the TypeSafe API.
- [typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python) - The official Python library for the TypeSafe API.
- [skills](https://github.com/typesafe-ai/skills) - Agent skills for building with TypeSafe's System One API.

## SDKs and Clients

Language bindings, CLIs, and thin wrappers for the API.

- [jevkit](https://github.com/ariel-frischer/jevkit) - Fast Rust CLI for TypeSafe Jev: typed decisions, offline linting before you pay.
- [jevi](https://github.com/bitomule/jevi) - Ask typed questions about a text and branch on the answer. A shell front end for TypeSafe's Jev.
- [ruby_decision_model](https://github.com/obie/ruby_decision_model) - Ruby client for decision models such as Typesafe Jev.
- [jev-tree](https://github.com/reachjalil/jev-tree) - Recursive Jev choice over a taxonomy. Select from more than 255 options without breaking TypeSafe Jev's choice cap.
- [ts-jev-cost-calculator](https://github.com/StefanoITA/ts-jev-cost-calculator) - Unofficial CLI + Python estimator of tokens, cost and context limits for TypeSafe (System One / Jev) API requests. Not affiliated with TypeSafe.
- [jod](https://github.com/mateonunez/jod) - Semantic schemas over TypeSafe's Jev — validate the state locally, then project typed answers.
- [typesafe-go](https://github.com/Nibir1/typesafe-go) - Zero-dependency Go SDK for TypeSafe's System One API (Jev). Typed questions in, calibrated probabilities out — with static analyzers that catch bad question design at build time, a decision layer, batching and caching. Not affiliated with TypeSafe AI.
- [sytem-one-sdk](https://github.com/ziyu/sytem-one-sdk) - Unified interface wrapper for system one models.
- [jev](https://github.com/dannote/jev) - TypeSafe Jev for OTP: reply to Jev from a GenServer and pattern match on its answer.
- [jev-cli](https://github.com/tumf/jev-cli) - Small dependency-free CLI for TypeSafe Jev.
- [qualm](https://github.com/qddegtya/qualm) - Typed decisions from a System One model. An uncertain answer is a different type from a confident one — and the compiler makes you handle it.
- [jev-cli](https://github.com/jtsang4/jev-cli) - CLI for TypeSafe AI's Jev evaluation model — typed questions in, structured JSON answers out.
- [jev](https://github.com/model-clis/jev) - Typed judgment CLI for the Jev model (TypeSafe System One): state + questions in, calibrated answers and exit codes out.
- [kunobi-jev](https://github.com/kunobi-ninja/kunobi-jev) - Rust client for the TypeSafe System One API (Jev).
- [jev](https://github.com/okooo5km/jev) - Typed decisions from the shell: an unofficial stdlib-Python CLI and Agent Skill for TypeSafe's Jev model, via the TypeSafe API (default) or OpenRouter. Yes/no, choice and ordinal scores with calibrated probabilities, semantic grep and batch mode.

## Integrations

Jev wired into frameworks, gateways, platforms, and databases.

- [pg-jev](https://github.com/realZachi/pg-jev) - Ask your Postgres tables questions in plain language. A PostgreSQL extension powered by TypeSafe's Jev.
- [HA-Jev](https://github.com/AboveColin/HA-Jev) - Ask your house a question, get a number back. Home Assistant integration for TypeSafe Jev: typed answers as sensors, four actions for automations, and a conversation agent for Assist.
- [ruby_llm-typesafe](https://github.com/kieranklaassen/ruby_llm-typesafe) - TypeSafe structured-output provider for RubyLLM 2.
- [laravel-typesafe-jev](https://github.com/Butochnikov/laravel-typesafe-jev) - Unofficial Laravel integration for TypeSafe Jev AI with typed responses, async requests, scoped dependency injection, and testing fakes.
- [n8n-nodes-typesafe-jev](https://github.com/n3ndor/n8n-nodes-typesafe-jev) - N8n community node for TypeSafe Jev structured AI decisions.
- [jev-connector](https://github.com/juanlentino/jev-connector) - WordPress connector for the TypeSafe System One API (Jev): typed questions, confidence-scored answers, core Connectors API key management.
- [vgi-typesafe](https://github.com/Query-farm/vgi-typesafe) - A VGI worker exposing TypeSafe System One questions (choice, noul, score) to DuckDB/SQL as LATERAL-joinable table functions.
- [llama-index-jev](https://github.com/WiktorB2004/llama-index-jev) - LlamaIndex reranker + router powered by TypeSafe Jev — typed scores/choices, cheaper than LLM-as-judge.
- [EDcheck](https://github.com/edteamlat/EDcheck) - Semantic validation for Zod schemas, powered by TypeSafe Jev. Validate meaning, not just structure.
- [sql-jev](https://github.com/sashimikun/sql-jev) - Ask your SQLite tables questions in plain language: jev() predicates for Turso/libSQL, Cloudflare D1 and plain SQLite.
- [HA-SystemOne](https://github.com/AtHeartEngineer/HA-SystemOne) - Adding SystemOne APIs like Typesafe Jev to home assistant.
- [sqlite-jev](https://github.com/mgaitan/sqlite-jev) - Batched natural-language judgments for SQLite, powered by TypeSafe Jev.

## Agent and Developer Tooling

Routers, guards, reviewers, skills, and MCP servers for coding agents.

- [pi-warden](https://github.com/DevMortimer/pi-warden) - Guardrails for Pi built on pi-typesafe that steer the agent instead of interrupting you: Jev judges irreversible and off-task tool calls, detects stuck loops, checks unverified done claims, flags slop.
- [hermes-jev](https://github.com/keeltrace/hermes-jev) - Typed System One decisions, ranking, verification, and an opt-in Hermes tool gate using TypeSafe Jev.
- [pi-jev-auto-mode](https://github.com/jomatsu/pi-jev-auto-mode) - Jev (TypeSafe System One) backed auto mode for the Pi coding agent: semantically auto-approves bash, write, and edit tool calls and fails closed when a decision cannot be made.
- [jevwire](https://github.com/Brainwires/jevwire) - Jev decision layer for agents: MCP server, embeddable DecisionModel library, and an escalate-only Claude Code plugin (TypeSafe AI's Jev).
- [jev-mcp](https://github.com/Brainwires/jev-mcp) - Jev decision layer for agents: MCP server, embeddable DecisionModel library, and an escalate-only Claude Code plugin (TypeSafe AI's Jev).
- [jev-browser](https://github.com/Ying-Kai-Liao/jev-browser) - Browser automation where an LLM plans and Jev (Typesafe System One) decides. Library, CLI and MCP server.
- [codex-context-diet](https://github.com/konstantinosbotonakis/codex-context-diet) - Codex plugin: Jev-guided dieting of bulky tool results.
- [pi-typesafe](https://github.com/DevMortimer/pi-typesafe) - TypeSafe decisions for Pi: batched evaluation tool, terminal playground, and typed API for extension authors.
- [jev-axi](https://github.com/shiftynick/jev-axi) - Agent-ergonomic CLI for TypeSafe's Jev: fast calibrated judgments (pick, rate, check, rank, triage, guard) from the shell.
- [pi-extensions](https://github.com/narumiruna/pi-extensions) - A monorepo of Pi Coding Agent extensions.
- [JevRouter](https://github.com/BillionsBobby/JevRouter) - A lightweight Jev-powered router for models, tools, and subagents.
- [pi-jev](https://github.com/riposta/pi-jev) - A Jev classification layer for the Pi coding agent.
- [hersona](https://github.com/shiro-0x/hersona) - 346 reusable character attributes for AI agent personas — compose, measure, and port system-prompt personas. Build once. Keep personality everywhere.
- [jev-mcp](https://github.com/jkudish/jev-mcp) - Fast, cheap, typed judgments from TypeSafe's Jev model, as MCP tools.

## Applications

Products and features whose behavior depends on Jev decisions.

- [quackd](https://github.com/rokbenko/quackd) - One CLI for all your robots. Connect them, command them, and let them work together, each with an LLM for a brain, Jev for cheaper steps. Microduck, Open Duck Mini, LeRobot, XLeRobot, AlohaMini, ToddlerBot or any ROS base. Claude, OpenAI, Gemini, Grok, or local via Ollama or vLLM. Simulator, .duck safety contracts, MCP, memory between runs, flocks.
- [jev-ultrafast](https://github.com/browser-use/jev-ultrafast) - I. am. speed.
- [jev-search](https://github.com/superagents-lab/jev-search) - Search the web with TypeSafe's Jev: source selection, query understanding and relevance ranking. Built with Search1API.
- [typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) - Computer use for about $0.0002 a step: OCR the screen, classify the next action with TypeSafe, click. macOS.
- [jev-voice-control](https://github.com/chris-wozniczek/jev-voice-control) - Control your Mac by voice. Speech → Jev (TypeSafe AI System One model) typed decisions → macOS actions. Menu-bar Swift app.
- [VisionClaw-Agent-Public-Release](https://github.com/Huskyauto/VisionClaw-Agent-Public-Release) - Open-source multi-tenant AI agent workspace · 18 personas · 138 active capabilities · 815 platform indexes · 80 curated AI models + 1000+ OpenRouter catalog · self-hosted, BYO-keys.
- [jev-mobile](https://github.com/Friedjof/jev-mobile) - Fast structured Android control loops with TypeSafe Jev and Mobile MCP.
- [mappity](https://github.com/kortexa-ai/mappity) - Ask the map anything. Every place answers with a probability. OpenStreetMap + Mapillary + TypeSafe Jev + Cactus Needle.
- [snifftest](https://github.com/DanRWilloughby/snifftest) - A prose linter that sniffs out AI writing tells. Zero dependencies, countable rules plus one judgment model.
- [jev-skip](https://github.com/valentynkit/jev-skip) - YouTube sponsor skipper that reads the captions and decides at watch time: a probability heatmap on the seek bar, no crowd database.
- [jev-relay](https://github.com/rnjsxodyd90/jev-relay) - A typed Jev decision gate, local-voice interpreter workbench, and reproducible Jev vs Qwen research.
- [openagents](https://github.com/OpenAgentsInc/openagents) - Monorepo & docs.
- [jev-search](https://github.com/jh1373/jev-search) - Search your Obsidian vault locally and offline with no API key, then rerank the top results with Jev only after you approve exactly what gets sent. Experimental preview.

## Games, Robotics, and Simulation

Jev in a control loop.

- [heist-one](https://github.com/AbdelStark/heist-one) - Observable browser stealth game: Jev makes typed guard judgments while deterministic code owns the world.
- [jev-jstris](https://github.com/SongMarco/jev-jstris) - Jev chooses Tetris placements; a local controller plays Jstris through keyboard input.
- [jev-nethack](https://github.com/integrate-your-mind/jev-nethack) - Jev x NetHack: bounded runner, research code, and completed recording releases.
- [jev-tetris](https://github.com/Tsagaanbayr1/jev-tetris) - Real-time Tetris versus Jev, a TypeSafe decision model — spins, garbage, B2B chains, and decisions prefetched a piece ahead.
- [jev-sonar](https://github.com/meetr1912/jev-sonar) - TypeSafe Jev plays Battleship: one ~100-question typed fan-out per turn returns a calibrated hit-probability heatmap that is also the move policy.
- [jev-plays-pokemon-red](https://github.com/valentynkit/jev-plays-pokemon-red) - Pokemon Red on PyBoy: code owns the route and the arithmetic, Jev picks at branches in about 100 ms, calibration measured instead of assumed.
- [robots-world](https://github.com/DanMcInerney/robots-world) - A modular multi-robot control testbed with swappable physics, sensors, AI controllers, and impaired swarm communication.
- [spire-jev](https://github.com/enderzcx/spire-jev) - Slay the Spire 2 agent controller: planner models, Jev fast decisions, and verified multi-card turn execution.
- [last-exit](https://github.com/0x963D/last-exit) - A cyberpunk border encounter powered by TypeSafe Jev. Bluff the guard. Inspect the receipts.
- [tsai-sc](https://github.com/phyous/tsai-sc) - TypeSafe Jev controls original StarCraft shareware through keyboard and mouse with recorded action probabilities.
- [typesafe-mario](https://github.com/fhshaik/typesafe-mario) - A TypeSafe/Jev agent that plays Super Mario Bros. from structured emulator state.
- [typesafe-chess](https://github.com/TholeG/typesafe-chess) - Chess where both players are TypeSafe's Jev model: every move is a typed Choice decision.
- [jev-mine-sweeping](https://github.com/sxinyuhoo/jev-mine-sweeping) - 用 TypeSafe Jev（System One）驱动扫雷自动通关：HTML 扫雷页每走一步实时问模型，并把它的选项、概率、代码已证明的事实全部可视化。Play Minesweeper with TypeSafe Jev (System One): an HTML game that asks the model every move and visualises its options, probabilities and the facts the code proved.

## Research, Evals, and Reimplementations

Benchmarks, calibration studies, and open replicas.

- [kev](https://github.com/jaredpalmer/kev) - Tiny Jev-like model built on top of Qwen2.5-0.5B you can train and run on your MacBook.
- [dinostomp](https://github.com/collapseindex/dinostomp) - A verification layer for AI evaluations. Checks the instrument, not just the score: data, scorer, runs, numbers, claims, and itself.
- [jevassert](https://github.com/dtduc-git/jevassert) - Record/replay regression tests for Jev (TypeSafe System One) question packs — accuracy, calibration and cost gates in CI.
- [SemIf](https://github.com/TheoLeeCJ/SemIf) - Semantic ifs from open models, on a 3090 at home. Independent; not affiliated with Jev or TypeSafe.
- [jev-benchmarks](https://github.com/AbdelStark/jev-benchmarks) - Probability-aware evaluation for typed decision models: calibration, selective risk, latency, and reproducible benchmarks.
- [openjev](https://github.com/TheoLeeCJ/openjev) - Semantic ifs from open models, on a 3090 at home. Independent; not affiliated with Jev or TypeSafe.
- [openjev](https://github.com/bnsd55/openjev) - Jev-style parallel constrained decisions for any MLX model on Apple Silicon. Typed, schema-valid JSON in one forward pass.
- [WindTunnel](https://github.com/nekuda-ai/WindTunnel) - A WebMCP benchmark, measures WebMCP against other browser-agent interfaces.
- [typesafe-local](https://github.com/aabolfazl/typesafe-local) - Inspired by TypeSafe Ai, Ask a local LLM typed questions, get calibrated probabilities instead of text. Structured output without generation or parsing. MLX / Apple Silicon.
- [llm-prompt-techniques-on-jev](https://github.com/leepokai/llm-prompt-techniques-on-jev) - Chain-of-thought and self-refinement for TypeSafe's Jev: feed its typed answers back as state and ask again. Benchmarks vs TypeSafe's own cookbook numbers.
- [jev-arena](https://github.com/meetr1912/jev-arena) - A calibration arena for TypeSafe Jev: reliability, Brier/ECE, and confidence-gated risk-coverage on analytically-known random worlds.
- [jev-dspy-lab](https://github.com/jmanhype/jev-dspy-lab) - Reproducible calibration and selective-risk benchmarks for Jev/TypeSafe decisions in DSPy workflows.
- [jev-exploration](https://github.com/SamuelSacco/jev-exploration) - Jev (TypeSafe) exploratory thread: claim audit, live demos, and runnable code.
- [jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop) - Unofficial study: Jev-style parallel typed decisions on stock 1.5B-8B models on an Apple Silicon laptop. Benchmarks, research notes, and a Hugging Face Space demo.
- [jevcal](https://github.com/abhixhek/jevcal) - Stop guessing confidence thresholds: calibrate, threshold, and drift-check typed decision models (TypeSafe Jev) against an LLM teacher.

## Learning

Tutorials, example galleries, and playgrounds.

- [jev](https://github.com/inematds/jev) - Análise crítica e plano de aplicação do Jev em decisões estruturadas.
- [jev-starter](https://github.com/hamakyo/jev-starter) - Typed, policy-driven decision workflows on top of TypeSafe AI Jev: confidence routing, fallbacks, evaluation, and RAG patterns for TypeScript apps.
- [jev-preview](https://github.com/ArkadyBuryakov/jev-preview) - TUI Sandbox for Typesafe Jev API.
- [jev-for-engineers](https://github.com/Foadsf/jev-for-engineers) - Eight minimal working examples of TypeSafe's Jev (a System One model) applied to mechanical and electrical engineering: CAD/CAE/CAM routing, FEM result triage, DFM screening, BOM alignment, hallucination-proof extraction. Zero dependencies.
- [neo4jev](https://github.com/jexp/neo4jev) - Typesafe.ai System One Model Jev navigating a Neo4j graph by using a classifier over neighbouring relationships.
- [jev-lab](https://github.com/BrendanH18/jev-lab) - Six small apps and a workbench that show what TypeSafe's Jev (System One) model can do.
- [jev-control-room](https://github.com/thisisjorge/jev-control-room) - A visual control room for typed AI evaluations, structured decision-making, and confidence-aware policy gating using Vercel AI SDK and TypeSafe Jev.
- [Jevs-Garage](https://github.com/JGalego/Jevs-Garage) - A garage full of tiny experiments for building critical systems with System One & Jev 🔧🧠⚡.
- [jev-playground](https://github.com/shivanathd/jev-playground) - BYOK playground for TypeSafe Jev (System One): Choice, Score, Noul examples for production gates.
- [typesafe-playground](https://github.com/TypeSafeAI/typesafe-playground) - Community TypeSafe AI playground: 110 use cases, games, dilemmas and model challenges, with editable prompts, A/B comparisons and a mobile-friendly UI.
- [jev-playground](https://github.com/wustep/jev-playground) - Can a System One model steer music? Jev picks the plan (enums only); code renders sheet, audio and MIDI.
- [jev-orange-book](https://github.com/hehuihuang/jev-orange-book) - Jev 模型橙皮书：52页中文工程实战手册，公开资料、12个案例与可下载PDF.

## Other Lists

Community-maintained lists and directories.

- [awesome-jev-by-typesafe](https://github.com/Anil-matcha/awesome-jev-by-typesafe) - Evidence-backed use cases, patterns, prompts, and starter code for TypeSafe Jev — a System One model for fast, typed, confidence-aware decisions in software.
- [jev-lab](https://github.com/llt22/jev-lab) - Hands-on research lab for TypeSafe's Jev (System One model): reproducible benchmarks of Noul/Choice/Score primitives, confidence gating, fan-out latency, agent control — plus a living audit of the Jev ecosystem.
- [jev-radar](https://github.com/everyinfra/jev-radar) - 📡 全网最全 · The world's most comprehensive tracker of the Jev (TypeSafe AI System One) ecosystem — 220+ documented cases · 108 confidence-graded entries · verified & rescanned every 3 hours · API access guide included.
- [awesome-jev-usecases](https://github.com/aliaihub/awesome-jev-usecases) - Evidence-backed use cases, patterns, and guidance for building with Jev, TypeSafe AI's System One model. Every claim is labeled and sourced.
- [awesome-jev-apps](https://github.com/Justmalhar/awesome-jev-apps) - Awesome Collection of apps built with Jev - a System One model.
- [awesome-typesafe-jev](https://github.com/thevibeworks/awesome-typesafe-jev) - Curated list of projects built on TypeSafe's Jev model, read before listed. With media and our own measurements. Not affiliated with TypeSafe AI.
- [awesome-jev-projects](https://github.com/logicrw/awesome-jev-projects) - Awesome Jev: source-backed open-source ecosystem radar, plain-language project discovery, and automatic GitHub sync.
- [awesome-jev](https://github.com/fatwang2/awesome-jev) - A source-backed Jev project directory with a reusable Jev-only GitHub review workflow.
- [awesome-jev-zh](https://github.com/yzfly/awesome-jev-zh) - Jev / TypeSafe System One 中文精选列表：官方资料、SDK、爆款应用、Agent 工具、开源复现与独立评测，附中文上手指南，每日自动收录 GitHub 热门项目。.
- [awesome-jev](https://github.com/cobanov/awesome-jev) - A curated, source-backed list of projects built with Jev, TypeSafe AI's System One model for typed decisions.
- [awesome-jev-usecases](https://github.com/anandi1989/awesome-jev-usecases) - Evidence-backed index of real-world Jev (TypeSafe AI System One) use cases, cookbook, how-to, repos, patterns, and measured results.
- [awesome-jev](https://github.com/hellogumbo/awesome-jev) - A community directory of projects built on Jev, TypeSafe AI's System One model.
- [awesome-jev-typesafe](https://github.com/valentynkit/awesome-jev-typesafe) - Typed decisions with TypeSafe's Jev, the first System One model.
- [awesome-jev](https://github.com/rhc98/awesome-jev) - Projects built on Jev (TypeSafe AI's System One model), curated by Jev itself.

## Other

Genuine Jev projects that fit no category above.

- [syllago-docs](https://github.com/OpenScribbler/syllago-docs) - Documentation site for Syllago—the package manager for AI coding tool content.
- [dag-jev](https://github.com/Joymfl/dag-jev) - DAG creation out of unordered items via Jev.

## How This List Is Made

Discover: GitHub repository search, code search for SDK usage, and links from other community lists. Enrich: README excerpt, file listing, manifest dependencies, and activity metadata. Judge: one Jev call per repository with 11 typed questions, gates as Noul, category and pattern as Choice, substance, docs, and novelty as Score. Curate: code applies thresholds and weights to the stored judgments, so changing policy never re-runs inference. Publish: this README and the site are generated from `data/curated.json` every day.

Question set `v2`, model `jev-1.13.0`. The calibration against human labels is on the [how it works](https://awesome-jev.xyz/how-it-works) page.

## Contributing

Missing project? [Submit it](https://github.com/rhc98/awesome-jev/issues/new?template=submit.yml) with the repository URL. A bot checks the link, the next daily run judges it, and the verdict is posted back on the issue. This README carries the top 15 by composite in each category; everything else that passes the gate is on the site. Think Jev got one wrong? [Say so](https://github.com/rhc98/awesome-jev/issues/new?template=jev-got-it-wrong.yml) and a bot drafts the `data/overrides.yaml` change for a maintainer to review. Do not edit this README directly; it is regenerated.
