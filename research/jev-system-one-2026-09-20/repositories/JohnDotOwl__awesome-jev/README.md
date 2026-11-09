# Awesome Jev [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

> Curated list of projects built on [Jev](https://typesafe.ai), TypeSafe AI's System One model for typed decisions.

Jev takes a state plus typed questions (Choice, Score, Noul) and returns typed answers with calibrated probabilities in one request. It does not generate text. Model id `jev-latest`. Docs: [docs.typesafe.ai](https://docs.typesafe.ai). Early access since 2026-09-15.

Not affiliated with TypeSafe AI.

318 entries · last refreshed 2026-09-18

## Contents

- [Official](#official)
- [SDKs and clients](#sdks-and-clients)
- [Integrations](#integrations)
- [Agent tooling](#agent-tooling)
- [Browser and computer use](#browser-and-computer-use)
- [Applications](#applications)
- [Games and simulations](#games-and-simulations)
- [Demos and playgrounds](#demos-and-playgrounds)
- [Benchmarks and research](#benchmarks-and-research)
- [Other lists](#other-lists)

## Official

Docs, SDKs, and resources from TypeSafe AI.

- [TypeSafe AI](https://typesafe.ai) - Company homepage, waitlist, and product overview.
- [Documentation](https://docs.typesafe.ai) - Introduction, primitives, patterns, cookbooks, HTTP API, and SDK references.
- [Quick start](https://docs.typesafe.ai/introduction/quickstart) - Shortest path from an API key to a typed decision.
- [Playground](https://console.typesafe.ai/playground) - Paste a state, add questions, and see typed answers in the browser.
- [HTTP API](https://docs.typesafe.ai/api) - Request and response contract for POST /v1/systemone.
- [Primitives](https://docs.typesafe.ai/primitives) - Choice, Score, and Noul: the three question types and what they return.
- [Launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev) - Architecture, RLCD training, pricing, Doom and Wikiracing demos, and FAQ.
- [Discord](https://discord.gg/typesafe) - Official TypeSafe server.
- [TypeSafe on X](https://x.com/typesafeai) - Product and research updates.
- [TypeSafe JavaScript SDK](https://github.com/typesafe-ai/typesafe-sdk-js) - The official TypeScript/JavaScript library for the TypeSafe API.
- [TypeSafe Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python) ([site](https://docs.typesafe.ai/sdk/python)) - The official Python library for the TypeSafe API.
- [System One adapter (Python)](https://github.com/typesafe-ai/system-one-adapter-python) - Drop-in TypeSafeClient replacement backed by LLM APIs.
- [TypeSafe agent skills](https://github.com/typesafe-ai/skills) ([site](https://typesafe.ai)) - Agent skills for building with TypeSafe's System One API.
- [daggerverse](https://github.com/typesafe-ai/daggerverse) ([site](https://daggerverse.docs.typesafe.ai/)) - Collection of useful Dagger modules.

## SDKs and clients

Community clients for languages without an official SDK.

- [advocaat](https://github.com/pithings/advocaat) - A small, type-safe client for asking AI questions about your data, powered by TypeSafe Jev.
- [typesafe-sdk-swift](https://github.com/InsaneArts/typesafe-sdk-swift) - Swift SDK for TypeSafe AI.
- [TypeSafeAI.Net](https://github.com/Hawxy/TypeSafeAI.Net) ([site](https://docs.typesafe.ai/)) - .NET SDK for the TypeSafe AI platform.
- [jev-go](https://github.com/Stumble/jev-go) - Community Go SDK for TypeSafe AI Jev / System One.
- [jev-go](https://github.com/guillemus/jev-go) - Unofficial Go SDK for TypeSafe AI's Jev API.
- [jev-go](https://github.com/Gaurav-Gosain/jev-go) - Go client for TypeSafe's System One API and its model Jev: typed judgments and calibrated probabilities instead of generated text.
- [jev-sec-bench](https://github.com/Gaurav-Gosain/jev-sec-bench) - Blind security benchmarks for Jev, TypeSafe's System One model: prompt injection and vulnerable code detection, built on jev-go.
- [jevclient](https://github.com/AboveColin/jevclient) ([site](https://pypi.org/project/jevclient/)) - Async Python client for TypeSafe Jev. Typed questions in, probabilities and choices out, no prose to parse.
- [jevgo](https://github.com/fgn/jevgo) - Go client for TypeSafe AI's System One API (Jev), with optional Langfuse instrumentation.
- [typesafe_sdk](https://github.com/nshkrdotcom/typesafe_sdk) - An idiomatic, type-safe Elixir port of the official TypeScript AI SDK (ai / ai-sdk) providing unified LLM integrations, streaming text and structured outputs, tool calling, and agentic workflows. Jev is their current flagship model and is the first System One model.
- [jev](https://github.com/anilsenay/jev) - Unofficial Go client for TypeSafe's System One API and its model, Jev.
- [jev](https://github.com/mhmdkzr/jev) - An unofficial Go client for TypeSafe's System One Jev model.
- [jev](https://github.com/david1gp/jev) - Result-based TypeSafe System One client library and jev command-line interface.
- [jev-rs](https://github.com/abeldzan/jev-rs) - Async-first Rust SDK for the TypeSafe AI API.
- [jev-sdk-go](https://github.com/kazz187/jev-sdk-go) - Go 1.27 client for TypeSafe AI's Jev (System One) API: typed questions, typed answers.
- [kunobi-jev](https://github.com/kunobi-ninja/kunobi-jev) - Rust client for the TypeSafe System One API (Jev).
- [tinyjevclient](https://github.com/tinyhumansai/tinyjevclient) - An integration with jev by typesafe.ai in Rust.
- [typesafe_ai](https://github.com/typesend/typesafe_ai) ([site](https://typesafe-api.hexdocs.pm/readme.html)) - Typed Elixir client for TypeSafe AI and its Jev System One model, with offline test stubs, concurrent fan-out, and atom-keyed answers.
- [typesafe-client](https://github.com/sava-software/typesafe-client) - Java client for the TypeSafe System One API (Jev): typed questions in, calibrated probabilities out.
- [typesafe-go](https://github.com/zhirschtritt/typesafe-go) - Idiomatic Go SDK for the TypeSafe AI API.
- [typesafe-rs](https://github.com/AbdelStark/typesafe-rs) ([site](https://docs.rs/typesafe-rs/latest/typesafe_rs/)) - Latency-first Rust SDK for TypeSafe System One.
- [typesafe-sdk](https://github.com/binnash/typesafe-sdk) - PHP & Laravel SDK for TypeSafe AI's JEV Model series.
- [typesafe-sdk-go](https://github.com/valksor/typesafe-sdk-go) - Unofficial Go SDK for the TypeSafe AI System One API — 1:1 parity with the official JS and Python SDKs. Not affiliated with TypeSafe AI.
- [typesafe-sdk-php](https://github.com/valksor/typesafe-sdk-php) ([site](https://packagist.org/packages/valksor/typesafe-sdk-php)) - Unofficial PHP SDK for the TypeSafe AI System One API — 1:1 parity with the official JS and Python SDKs. Not affiliated with TypeSafe AI.

## Integrations

Jev inside frameworks, gateways, databases, and platforms.

- [pg-jev](https://github.com/realZachi/pg-jev) ([site](https://pgjev.com)) - Ask your Postgres tables questions in plain language. A PostgreSQL extension powered by TypeSafe's Jev.
- [neo4jev](https://github.com/jexp/neo4jev) - Typesafe.ai System One Model Jev navigating a Neo4j graph by using a classifier over neighbouring relationships.
- [HA-Jev](https://github.com/AboveColin/HA-Jev) - Home Assistant integration for TypeSafe Jev. Ask a question about your house and get a probability, a choice or a score as an entity.
- [jev-playground](https://github.com/Little-Planet-Labs/jev-playground) ([site](https://jev-playground-zeta.vercel.app)) - A small Next.js app for experimenting with TypeSafe AI's Jev model (System One).
- [laravel-typesafe-jev](https://github.com/Butochnikov/laravel-typesafe-jev) - Unofficial Laravel integration for TypeSafe Jev AI with typed responses, async requests, scoped dependency injection, and testing fakes.
- [safer-with-jev](https://github.com/andrelandgraf/safer-with-jev) - Neon Function proxy for the Neon AI Gateway with TypeSafe Jev routing.
- [cartshield](https://github.com/ndolinschi/cartshield) ([site](https://cartshield.vercel.app)) - CartShield — SMB checkout fraud disposition via TypeSafe Jev.
- [Jev on Vercel AI Gateway](https://vercel.com/ai-gateway/models/jev) - Hosted typesafe-ai/jev for AI SDK evaluate calls.
- [jev-atlas](https://github.com/gorock007/jev-atlas) ([site](https://jev-atlas.vercel.app)) - An independent, evidence-first field guide to Jev (TypeSafe AI's System One model) — for people and for coding agents. Not affiliated with TypeSafe AI.
- [jev-playground](https://github.com/wustep/jev-playground) ([site](https://jev-playground.vercel.app)) - Can a System One model steer music? Jev picks the plan (enums only); code renders sheet, audio and MIDI.
- [jev-pr-judge](https://github.com/juanegido/jev-pr-judge) ([site](https://jev-pr-judge.vercel.app)) - Typed verdicts on pull requests with TypeSafe System One (Jev): one parallel call, policy in code, usable as a GitHub Action.
- [jev1](https://github.com/jflam/jev1) - Jev (TypeSafe System One) proof of concept: smart-home assistant demo.
- [jevplay](https://github.com/ndolinschi/jevplay) ([site](https://jevplay.vercel.app)) - TypeSafe Jev playground — custom Choice/Score/Noul builder with live distributions.
- [lanebreak](https://github.com/ndolinschi/lanebreak) ([site](https://lanebreak.vercel.app)) - LaneBreak — support ticket priority+routing via TypeSafe Jev.
- [magi-system-on-jev](https://github.com/hide-G/magi-system-on-jev) - MAGI system (Neon Genesis Evangelion) recreated with Jev, TypeSafe AI's System One model. 3 sages deliberate your question.
- [pulselane](https://github.com/ndolinschi/pulselane) ([site](https://pulselane-topaz.vercel.app)) - PulseLane — clinic triage decisions via TypeSafe Jev.
- [ticket-quest](https://github.com/EdytaKucharska/ticket-quest) ([site](https://ticket-quest-three.vercel.app)) - Playful ticket triage that shows how TypeSafe Jev's typed, probability-backed decisions compare with prompting an LLM. Cost of Delay ranking, certainty-gated routing, bring-your-own-key LLM race.
- [typesafe-assist](https://github.com/JanOstrowka/typesafe-assist) - Home Assistant Assist conversation agent powered by TypeSafe's Jev (System One) model.
- [Vercel AI SDK provider](https://ai-sdk.dev/providers/ai-sdk-providers/typesafe-ai) - @ai-sdk/typesafe-ai plus experimental_evaluate using jev-latest.

## Agent tooling

Gates, routers, reviewers, MCP servers, and skills for coding agents.

- [fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction) - Replaces Claude Code compaction summaries with Jev keep/delete decisions so kept content stays verbatim.
- [foreman](https://github.com/thruwire/foreman) - Software Factory Foreman based on TypeSafe Jev model.
- [jev-review](https://github.com/devagrawal09/jev-review) - A staged code-review workflow and local dashboard built with TypeSafe Jev.
- [jev-review](https://github.com/NiazMorshed2007/jev-review) - Local-first MCP plugin for continuous software-quality review by AI coding agents, powered by Jev.
- [jev-mcp](https://github.com/jkudish/jev-mcp) - Proof of concept MCP for Typesafe's new Jev AI model.
- [pi-warden](https://github.com/DevMortimer/pi-warden) - Guardrails for Pi built on pi-typesafe that steer the agent instead of interrupting you: Jev judges irreversible and off-task tool calls, detects stuck loops, checks unverified done claims, flags slop.
- [building-with-jev-skill](https://github.com/dbreunig/building-with-jev-skill) - A skill for writing and improving programs that call Jev, TypeSafe's System One model.
- [typesafe-mcp](https://github.com/itsmostafa/typesafe-mcp) - Mcp connector to give your AI agent direct access to typesafe ai's jev model.
- [pi-jev](https://github.com/y0usaf/pi-jev) - TypeSafe Jev as a decision layer for the Pi coding agent: a measured tool-call gate plus jev_ask for typed, calibrated answers.
- [ask-jev-skill](https://github.com/shantanugoel/ask-jev-skill) - Skill for Hermes, and other agents, to ask typesafe's jev.
- [jev-codex-router](https://github.com/0xNatoshi/jev-codex-router) - Per-turn model & reasoning routing for Codex, driven by Jev (TypeSafe System One): picks the model, thinking depth and speed mode for every turn.
- [agent-router](https://github.com/nidhi-singh02/agent-router) - CLI that picks Cursor, Claude Code, Codex, or OpenCode + model/effort for a task, then launches it. Powered by Jev and Herdr.
- [winnow](https://github.com/GhalebDweikat/winnow) - A calibrated context sieve for Claude Code: every tool result is judged by a System One model before it enters context.
- [jev-axi](https://github.com/shiftynick/jev-axi) - Agent-ergonomic CLI for TypeSafe's Jev: fast calibrated judgments (pick, rate, check, rank, triage, guard) from the shell.
- [jev-mcp](https://github.com/blakestone-x/jev-mcp) - MCP server for TypeSafe Jev: typed classify, score, check, match and screen for any agent, with confidence on every answer.
- [pi-jev-router](https://github.com/mejiasd3v/pi-jev-router) - Automatic model routing for Pi using TypeSafe's Jev through Vercel AI Gateway.
- [typesafe-skill-router](https://github.com/DECRUX9812/typesafe-skill-router) - TypeSafe (Jev) skill routing for Hermes Agent: names the one skill worth loading, before the model call. Opt-in, stdlib only, ~$0.001 per routed turn.
- [jev-agent-skill-router](https://github.com/GodsBoy/jev-agent-skill-router) - Typed, confidence-aware agent skill routing with TypeSafe Jev.
- [typesafe-cli](https://github.com/geilt/typesafe-cli) - CLI and agent skill for TypeSafe System One (Jev): typed Choice, Score, and Noul judgments.
- [ailerix](https://github.com/tylerjharden/ailerix) ([site](https://ailerix.vercel.app)) - Type-safe model router. Jev (System One) banks each request to a typed catalog route.
- [AskJev](https://github.com/ranjan2829/AskJev) ([site](https://docs.typesafe.ai/introduction)) - AskJev — Jev autopilot for any website + guard on irreversible clicks (TypeSafe System One, not Claude).
- [diffjury](https://github.com/raihankhan-rk/diffjury) - DiffJury — TypeSafe Jev PR risk router + code review coach.
- [jcm-router](https://github.com/adarshmishra07/jcm-router) - Local proxy that picks the Claude model and effort per message using TypeSafe Jev. Routes subagents, leaves your cached main chat alone.
- [jev-gate](https://github.com/MongLong0214/jev-gate) - Not every coding task needs your best model. Experimental Jev-powered model routing for Claude Code — V3 prototype runs today, V4 routes at the task boundary.
- [jev-judgment](https://github.com/HyunjunJeon/jev-judgment) - Agent Skill: send closed coding-agent judgments to TypeSafe Jev.
- [jev-shield](https://github.com/caiovicentino/jev-shield) - Semantic MCP firewall powered by Jev — screens every tool call, tool result, and tool description with calibrated System One verification. 94% block recall, 0 false positives, ~$0.00002/check.
- [skill-router](https://github.com/lomeshdutta/skill-router) - Tell Claude Code which installed skill a session needs, using Jev (TypeSafe AI) for the decision and skills.sh for discovery.
- [typesafe-migration-guard](https://github.com/opaielsheikh/typesafe-migration-guard) - Automated database migration safety reviewer powered by TypeSafe AI (Jev System One model).
- [claude-jev](https://github.com/buchmark/claude-jev) - Claude Code plugin that scores review findings, debug hypotheses and design options with TypeSafe's Jev — calibrated probabilities instead of one more opinion.
- [fast-dev-compaction](https://github.com/leonaaardob/fast-dev-compaction) - Codex plugin: verbatim Jev-guided context restoration around session compaction. Port of tamaratran/fast-jev-compaction to Codex lifecycle hooks.
- [jev-guard](https://github.com/leepokai/jev-guard) - Auto mode for every coding agent, built on Jev: risk-scores every tool call with session context (deny / ask / allow), flags prompt injection in results, checks skills and plugins. Claude Code, Codex, Copilot, Gemini, Cursor, pi, OpenCode, ACP.
- [jev-mcp](https://github.com/rashedInt32/jev-mcp) ([site](https://www.npmjs.com/package/jev-mcp)) - MCP server exposing TypeSafe Jev as typed, calibrated judgment tools: classify, score, check, batched ask. Ships as a Claude Code plugin.
- [jev-predict-skill](https://github.com/DanielKillenberger/jev-predict-skill) - Predict another skill's next closed decision with TypeSafe Jev — without running that skill.
- [jev-router](https://github.com/prismhq/jev-router) - Open-source LLM router that uses TypeSafe's Jev to pick a model, on top of LiteLLM.
- [jev-skill-gate](https://github.com/ShivamPansuriya/jev-skill-gate) - Cut Claude Code's skill manifest by ~75% with TypeSafe Jev. Scores every installed skill for relevance and hides the rest via skillOverrides — 12,750 → 3,185 tokens on a 217-skill install, for $0.0009 a session.
- [jev-skillful](https://github.com/bestagentkits/jev-skillful) - Per-prompt capability router for coding agents: resolves installed skills, MCP servers, agents and commands against your prompt via TypeSafe Jev, and measures whether the injection actually helps.
- [jev-system-architect](https://github.com/samtay32/jev-system-architect) - System-architecture skill for TypeSafe AI Jev/System One — find fuzzy semantic judgment and turn it into small Choice/Score/Noul primitives.
- [jev-workbench](https://github.com/molis-ai/jev-workbench) - Build versioned judgment functions on TypeSafe's Jev once, then call the same published version from your backend over HTTP and from coding agents over MCP. The vendor key stays on your machine.
- [pi-fast-jev-compaction](https://github.com/joelhooks/pi-fast-jev-compaction) - Pi extension: verbatim context compaction with TypeSafe Jev decisions.
- [pi-model-router](https://github.com/redrossa/pi-model-router) - Pi extension that classifies each prompt with TypeSafe's Jev and routes it to the best model you're logged into.
- [PiJ](https://github.com/tonyzdev/PiJ) - A terminal coding agent with Jev in the loop: skill selection, code ranking, and failure triage.
- [toolgate](https://github.com/ndolinschi/toolgate) ([site](https://toolgate.vercel.app)) - Agent tool/MCP call gate — allow / ask_human / deny via TypeSafe Jev.
- [ActionJev](https://github.com/AlexBabescu/ActionJev) - Structured code review for GitHub and Gitea Actions, powered by TypeSafe Jev and written in Rust.
- [agent-workflow-lab](https://github.com/stillroom/agent-workflow-lab) - Typed state, explicit transitions, one narrow model judgment, and a human approval gate — a rebuildable agent workflow using and testing Jev.
- [askjev](https://github.com/pZacca/askjev) - Unofficial MCP server for Jev (Typesafe AI).
- [Augustus](https://github.com/24601/Augustus) - Agent skill: design judgment-assisted systems with TypeSafe Jev (System One). Maps Choice/Score/Noul onto decision theory, reranking, and routing. Composition algebra, question design, validation gates. MIT.
- [hermes-jev](https://github.com/keeltrace/hermes-jev) - Typed System One decisions, ranking, verification, and an opt-in Hermes tool gate using TypeSafe Jev.
- [jev-mcp](https://github.com/minhgv/jev-mcp) - TypeSafe Jev MCP decision layer for coding agents and CI.
- [jev-mobile](https://github.com/Friedjof/jev-mobile) - Fast structured Android control loops with TypeSafe Jev and Mobile MCP.
- [jev-pref](https://github.com/doeixd/jev-pref) - Jev-powered user-preference code reviewer setup (skills.sh-installable agent skill).
- [jev-review-action](https://github.com/fatwang2/jev-review-action) - Configurable GitHub submission review and PR classification with TypeSafe Jev. No text-generation model.
- [jev-router-playground](https://github.com/hugo-alves/jev-router-playground) ([site](https://kvhx37ziab90c.space.minimax.io)) - Interactive playground for testing Jev model-routing decisions against OpenRouter models.
- [jevify](https://github.com/altryne/jevify) ([site](https://thursdai.news)) - An agent skill to discover TypeSafe Jev opportunities, design typed questions, and learn from recent community experiments.
- [jevwire](https://github.com/Brainwires/jevwire) - Jev decision layer for agents: MCP server, embeddable DecisionModel library, and an escalate-only Claude Code plugin (TypeSafe AI's Jev).
- [limpet](https://github.com/noplan-inc/limpet) - A Stop hook that stops your coding agent from stopping too early. Plain-language rules, judged by jev.
- [omp-jevens-classifier](https://github.com/STRML/omp-jevens-classifier) - Jev-powered model-judged permission gate for OMP (TypeSafe System One).
- [openclaw-plugin-typesafe-ai](https://github.com/jason-allen-oneal/openclaw-plugin-typesafe-ai) - TypeSafe AI (Jev System One) plugin for OpenClaw - sub-100ms group triage, tool safety guardrails, compaction curation, and model routing.
- [pi-jev](https://github.com/clankagent/pi-jev) - Jev-powered semantic process conditions and skill suggestions for Pi.
- [reflex-state](https://github.com/furedea/reflex-state) - Jev-powered execution state for Pi coding agents. Track changes, checks, and blockers outside the main LLM, with evidence-backed updates and replay. Inspired by SKILL.state.
- [the-llm-dispatcher](https://github.com/Rawson08/the-llm-dispatcher) - An LLM router that uses Jev (TypeSafe System One) to dispatch each request to the cheapest model and lowest reasoning effort that will do the job. OpenAI-compatible proxy, Claude Code and Codex wrappers, TypeScript and C#.
- [typesafe-mcp](https://github.com/Obrais-cloud/typesafe-mcp) - MCP server exposing TypeSafe (Jev/System One) to the fleet: judge, rerank, systemone.
- [vibe-smart-router](https://github.com/armsteadj1/vibe-smart-router) - A Node-first, policy-bounded payment-context scorer using Jev for held-out feature discovery and per-transaction context.
- [wellposed](https://github.com/suraj-phanindra/wellposed) - Lint your jev requests before they come back confidently wrong.

## Browser and computer use

Browser, desktop, and mobile automation where Jev chooses the action.

- [jev-ultrafast](https://github.com/browser-use/jev-ultrafast) ([site](https://browser-use.com)) - Browser agent with a dynamic action space. Jev picks the operation and DOM target; a small LLM writes text only when typing is needed.
- [typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) - Computer use at about $0.0002 a step: OCR the screen, classify the next action with TypeSafe, click. macOS.
- [mobile-jev](https://github.com/droidrun/mobile-jev) - Jev project.
- [jev-browser](https://github.com/jkudish/jev-browser) - Browser use using Typesafe's Jev model.
- [typesafe-adblock](https://github.com/realZachi/typesafe-adblock) - 🧹 Fun project: a Chrome extension that asks a tiny AI decision model (TypeSafe Jev) "is this DOM element an ad?" and pops it off the page. BYOK, no backend, not a real ad blocker.
- [jev-browser](https://github.com/Ying-Kai-Liao/jev-browser) - Browser automation where an LLM plans and Jev (Typesafe System One) decides. Library, CLI and MCP server.
- [live-jev](https://github.com/vinilana/live-jev) - 2D autonomous car simulation in the browser, driven by TypeSafe's Jev decision model.
- [jev-ego](https://github.com/romaluev/jev-ego) - Fast browser agent for ego lite. One TypeSafe request per step; an agent or Jev picks the move.
- [aside-jev](https://github.com/himomohi/aside-jev) - Aside agents decide with TypeSafe Jev (System One: Choice/Score/Noul). Not a Cua binding — Jev is the model, Aside is the browser runtime.
- [barrunto](https://github.com/elpumberto/barrunto) - A Chrome extension that brings TypeSafe's Jev to X.com to analyze posts as you browse.
- [computer-use-jev](https://github.com/paulsmith/computer-use-jev) - MacOS computer use driven by Jev (TypeSafe System One) as the decision maker.
- [jev-browser](https://github.com/tontoko/jev-browser) - One grounded Jev/Playwright core: typed SDK, persistent CLI, and MCP server with native browser operations and deterministic assertions.
- [jev-research](https://github.com/sherajdev/jev-research) - Practical guide to using TypeSafe Jev with Herdr and Claude, Codex, Hermes, and browser agents.
- [jev-browser](https://github.com/KesavanKing/jev-browser) - Local browser automation UI that uses TypeSafe Jev to choose bounded page actions and a text model only for field values.
- [jev-voice-browser](https://github.com/moritzkremb/jev-voice-browser) - Control a real browser by voice. Jev (TypeSafe System One) decides intent + target in ~300 ms per spoken word; Playwright acts — often before you finish the sentence.
- [jevRemote](https://github.com/juancristobalgd1/jevRemote) ([site](https://juancristobalgd1.github.io/jevRemote/)) - Reproducible text-first browser automation experiment with TypeSafe Jev and Playwright.
- [typesafe-computer-use-hyprland](https://github.com/cartermccann/typesafe-computer-use-hyprland) - Hyprland/NixOS fork of typesafe-computer-use — grim + hyprctl + ydotool, TypeSafe Jev decisions.

## Applications

Products, CLIs, and pipelines that call Jev.

- [jev-trader](https://github.com/jarrodwatts/jev-trader) - One AI trade decision every Monad block. Jev on Kuru MON-USDC.
- [jevmeter](https://github.com/ChetasLua/jevmeter) - Put a live Jev (TypeSafe) meter on any video: every sentence scored, rendered as a 16:9 edit.
- [skillranker](https://github.com/Dicklesworthstone/skillranker) - Rust CLI powered by Jev from TypeSafe.ai that ranks agent skills for the next step using live session context. Includes Claude Code hooks, structured JSON, abstention, and local feedback. Requires a TypeSafe API key.
- [reflex](https://github.com/kshetrajna12/reflex) - A small open decision model: state + typed questions -> calibrated probabilities. A Jev / System One re-creation on Qwen3.5.
- [jevmlx](https://github.com/bnsd55/jevmlx) - Jev-style parallel constrained decisions for any MLX model on Apple Silicon. Typed, schema-valid JSON in one forward pass.
- [blink](https://github.com/ellipsis-dev/blink) - Codebase search powered by Jev from @typesafe-ai.
- [tsai-sc](https://github.com/phyous/tsai-sc) - TypeSafe Jev controls original StarCraft shareware through keyboard and mouse with recorded action probabilities.
- [jev-reranking](https://github.com/carlaiau/jev-reranking) - Search engine experimentation on the TREC collections. Currently focused on zero-shot reranking implementations with typesafe.ai's JEV model.
- [Jev-Trades](https://github.com/zadescoxp/Jev-Trades) ([site](https://jevtrades.zadescoxp.com)) - Trading bot with the all new TypeSafe AI's first system one model named as Jev.
- [pi-jev-auto-mode](https://github.com/jomatsu/pi-jev-auto-mode) - Jev (TypeSafe System One) backed auto mode for the Pi coding agent: semantically auto-approves bash, write, and edit tool calls and fails closed when a decision cannot be made.
- [yoshi](https://github.com/compozy/yoshi) - Context-pruning proxy for Claude Code and Codex: Jev judges which history is still needed, measured not claimed. POC here now, heading soon into https://github.com/compozy/compozy.
- [jev](https://github.com/dannote/jev) - TypeSafe Jev for OTP: reply to Jev from a GenServer and pattern match on its answer.
- [Jevbridge](https://github.com/gamesonrblx/Jevbridge) - ACP-compatible adapter that bridges TypeSafe Jev with any LLM — computer use and typed decisions alongside Codex, Claude, Grok, and OpenCode.
- [semdecide](https://github.com/sharziki/semdecide) - Typed semantic decisions for Unix pipelines and CI, powered by TypeSafe AI Jev.
- [super-jev](https://github.com/Kevthetech143/super-jev) - A small, extensible decision-to-action harness for TypeSafe Jev.
- [typesafe-cli](https://github.com/y0usaf/typesafe-cli) - Ask Jev typed questions from the shell: noul, choice, and score answers as numbers, not prose.
- [a0-typesafe-ai](https://github.com/3clyp50/a0-typesafe-ai) - TypeSafe AI Jev judgments for Agent Zero, with typed tools and probability cards.
- [jev-chat](https://github.com/adhyaay-karnwal/jev-chat) - A chatbot from typed Jev decisions: hierarchical speculative decoding over System One probabilities.
- [jev-code](https://github.com/devagrawal09/jev-code) - Bounded TypeSafe Jev workflows for coding agents.
- [jev-search](https://github.com/superagents-lab/jev-search) ([site](https://jev.s1.dev)) - Search the web with TypeSafe's Jev: source selection, query understanding and relevance ranking. Built with Search1API.
- [jod](https://github.com/mateonunez/jod) ([site](https://npmjs.com/package/@mateonunez/jod)) - Semantic schemas over TypeSafe's Jev — validate the state locally, then project typed answers.
- [OneVOneJev](https://github.com/emrickgarrett/OneVOneJev) - 1v1 Jev quickscope arena — Three.js + TypeSafe System One.
- [jev_stock](https://github.com/sosopop/jev_stock) - An experimental JEV-powered framework for forecasting short-term stock price direction from structured market data.
- [jev-cli](https://github.com/tumf/jev-cli) ([site](https://docs.typesafe.ai/introduction)) - Small dependency-free CLI for TypeSafe Jev.
- [jev-for-engineers](https://github.com/Foadsf/jev-for-engineers) - Eight minimal working examples of TypeSafe's Jev (a System One model) applied to mechanical and electrical engineering: CAD/CAE/CAM routing, FEM result triage, DFM screening, BOM alignment, hallucination-proof extraction. Zero dependencies.
- [jev-harness](https://github.com/AntonioCoppe/jev-harness) - Decision harness for TypeSafe Jev — confidence gates, shadow mode, recipes, and evals. Claude CLI 48.9s → Jev 1.3s on the same row-filter job.
- [jev-system-one](https://github.com/haseeb-heaven/jev-system-one) - A polished OpenAI + TypeSafe Jev terminal interface for answers with transparent decision reports.
- [jevgpt](https://github.com/Bewinxed/jevgpt) - A chatbot built on a model that cannot generate text (TypeSafe AI's Jev, driven autoregressively).
- [jevibe-check](https://github.com/sriganesh/jevibe-check) - A live tone labeler for Bluesky posts and drafts, using TypeSafe's Jev API.
- [riff](https://github.com/scale-venture-partners/riff) - A small, fast prose linter: ruff-style rule codes for writing, backed by TypeSafe's Jev model.
- [should-ai-kill-us-all](https://github.com/hellogumbo/should-ai-kill-us-all) ([site](https://shouldaikillusall.com)) - We ask Jev, TypeSafe AI's System One model, whether AI should kill us all. Every ten minutes. Using the actual headlines.
- [tiershift](https://github.com/iamvatsalpatel/tiershift) - Shift every LLM call to the cheapest model that can handle it. Routing decided by TypeSafe Jev in ~180 ms. No training data. Policy in plain YAML. TypeScript and Python.
- [trade-jev](https://github.com/justinhe16/trade-jev) - Backtest Jev (TypeSafe) as a BUY/SELL/HOLD trader on NQ L10 order-book data.
- [typesafe-mod](https://github.com/BeLazy167/typesafe-mod) - Claude Code mod that routes decisions to TypeSafe's Jev model: ranks installed skills per prompt, and answers the agent's own this-or-that questions when confident.
- [ask-jev](https://github.com/omni-/ask-jev) - Utilizing Jev, the RLCD-type model provided by TypeSafe AI, to independently and cheaply judge agentic coding sessions.
- [axiom-agent-runtime](https://github.com/axiomarchitecture/axiom-agent-runtime) - Reference prototype exploring agentic commerce: TypeSafe/Jev → Axiom → Argent → Silverscript on Kaspa.
- [btc-jev-signal](https://github.com/WebGrga/btc-jev-signal) - Experimental multi-horizon BTC signal generator using TypeSafe Jev probabilities and Binance market data.
- [Canny](https://github.com/qkal/Canny) - Stops AI coding agents from claiming work is done without evidence. Deterministic hooks decide, TypeSafe's Jev advises. Append-only ledger, zero runtime dependencies.
- [clarity-judge](https://github.com/BunsDev/clarity-judge) ([site](https://judge.jev.works)) - Multi-axis writing quality checker powered by TypeSafe AI's Jev model. Separate named checks, each with its own verdict and confidence.
- [every](https://github.com/sufianetaouil/every) - Ask a yes/no question of every function in a codebase. Ranked answers in seconds, for cents. Grep whose pattern is a question, powered by TypeSafe Jev.
- [harden-jev-decides](https://github.com/tylerjharden/harden-jev-decides) - JEV picks which stream idea becomes the live MVP. TypeSafe System One decision board.
- [hermes-jev-approvals](https://github.com/anpicasso/hermes-jev-approvals) - PoC: TypeSafe Jev as the reviewer for Hermes Agent smart command approvals. 8.7x faster, 4.4x fewer prompts, measured on 153 real commands. Approvals only.
- [jev-cli](https://github.com/jtsang4/jev-cli) - CLI for TypeSafe AI's Jev evaluation model — typed questions in, structured JSON answers out.
- [jev-dsl](https://github.com/inanna-malick/jev-dsl) - Agent-first Haskell DSL for TypeSafe's Jev judgment model: typed packets, inferred types, answers under the same labels.
- [jev-mcts](https://github.com/paulobueno164/jev-mcts) - Busca em arvore (MCTS/PUCT) com avaliacao tipada do TypeSafe Jev e portao humano obrigatorio. A arvore supoe, a sonda mede: marco so e concedido por codigo de saida verde.
- [jev-realtime-trading](https://github.com/rthomas24/jev-realtime-trading) - Paper trading agents on a live tape, decided every second by TypeSafe's Jev (System One). Electron desktop app.
- [jev-rerank-bench](https://github.com/anessbelbati/jev-rerank-bench) - Can a decision model beat dedicated rerankers? TypeSafe Jev vs Cohere Rerank 4 vs ZeroEntropy zerank-2 vs a chat-model baseline: 14 datasets, every raw API response, bootstrap ranges on every gap.
- [jev-resilience](https://github.com/Vicente-MD/jev-resilience) - Non-blocking Spring Boot Starter for Spring WebFlux that implements a Semantic Circuit Breaker to detect silent HTTP 200 failures using TypeSafe Jev.
- [jev-starter](https://github.com/hamakyo/jev-starter) - Typed, policy-driven decision workflows on top of TypeSafe AI Jev: confidence routing, fallbacks, evaluation, and RAG patterns for TypeScript apps.
- [jev-tree](https://github.com/reachjalil/jev-tree) ([site](https://reachjalil.github.io/jev-tree/)) - Recursive Jev choice over a taxonomy. Select from more than 255 options without breaking TypeSafe Jev's choice cap.
- [jevbot](https://github.com/tyleree/jevbot) - Options trading bot (backtest + Alpaca paper only) with TypeSafe Jev as the decision core.
- [jevsql](https://github.com/EugeneBoondock/jevsql) - SQL with natural-language predicates, powered by TypeSafe's Jev. Filter, rank, classify and score rows by meaning — batched, cached and cost-guarded.
- [judging-with-typesafe](https://github.com/carlsonchik/judging-with-typesafe) - Скилл для агентов Letta: суждения по критериям через TypeSafe System One (Jev).
- [mcts-agent](https://github.com/lhemerly/mcts-agent) - Discriminative Monte Carlo Tree Search using TypeSafe Jev System One Primitives and Gemini.
- [omp-typesafe](https://github.com/siddicky/omp-typesafe) - TypeSafe AI (Jev) adversarial reviewer and typesafe_ask tool for the omp coding agent.
- [otto](https://github.com/NobleSpartan6/otto) - Open-source native computer use for macOS and Windows: TypeSafe Jev, local OCR, and selective planning.
- [pg_typesafe](https://github.com/giuliosmall/pg_typesafe) - Pre-alpha PostgreSQL extension for TypeSafe AI (Jev) categorical classification.
- [pi-jev](https://github.com/TheoOliveira/pi-jev) - Semantic tool routing and typed System One decisions for the Pi coding agent using TypeSafe Jev.
- [pi-quiet-ask](https://github.com/HyunjunJeon/pi-quiet-ask) - TypeSafe Jev as the pi coding agent's quiet decision layer.
- [research_desk](https://github.com/0xnairb/research_desk) - TypeSafe Jev demonstration for new analyzation — experimenting with Jev for fast analysis of news and tickers.
- [rpg-jev](https://github.com/lmvdz/rpg-jev) - A living-world RPG whose NPCs are decided by TypeSafe's Jev judge model; code owns rules, numbers and state.
- [ts-jev-cost-calculator](https://github.com/StefanoITA/ts-jev-cost-calculator) - Unofficial CLI + Python estimator of tokens, cost and context limits for TypeSafe (System One / Jev) API requests. Not affiliated with TypeSafe.
- [typesafe-ai-firewall](https://github.com/AnshChoudhary/typesafe-ai-firewall) - Shadow-mode validation harness for a pre-execution firewall on AI agent tool calls (TypeSafe/Jev). Real run, findings in report.md.
- [casse-brique-typesafe](https://github.com/Para-FR/casse-brique-typesafe) - A Next.js brick breaker whose paddle is controlled in real time by TypeSafe AI's Jev model. Built with Claude Code.
- [chakravyuha-jev](https://github.com/kspviswa/chakravyuha-jev) - Chakravyuha — a polar ring-maze where every move is a Jev (TypeSafe System One) decision. A fun experiment: the model picks each move, the walk grades it green or red, and the history page asks whether its confidence score can be trusted. BYOK, no build step.
- [cleaner](https://github.com/mahan-ym/cleaner) - An experiment with JEV from typesafe.ai to clean up my useless data.
- [draftpulse](https://github.com/pekth/draftpulse) - Experimental: live X draft viral scorer powered by TypeSafe Jev.
- [dsh-jev](https://github.com/noetion/dsh-jev) - DSH bundle that registers jev_ask for TypeSafe Jev noul, choice, and score answers.
- [duckdb-jev](https://github.com/recodelabs/duckdb-jev) - Natural-language WHERE clauses for DuckDB, powered by TypeSafe's Jev.
- [emoji-jev](https://github.com/colinmcdermott/emoji-jev) - Emoji autocomplete at the speed of typing. TypeSafe AI Jev on a Whop-hosted TanStack Start app.
- [FeedGate](https://github.com/zsoXi/FeedGate) - Precision-first Chrome feed filter (v2.1.0) using TypeSafe Jev judgments: promotional posts are kept unless independently strong spam or ad evidence appears. Reversible cosmetic filtering, zero runtime dependencies.
- [focus-tube](https://github.com/piyush97/focus-tube) - Distraction-free YouTube learning feed powered by TypeSafe AI's Jev System One model.
- [jev-audit](https://github.com/phuthuycoding/jev-audit) - AI-powered pre-commit auditor backed by TypeSafe System One (Jev) — blocks secrets, vulns & low-quality code in ~300ms. 79-case test corpus at 100% accuracy.
- [jev-claude](https://github.com/takezou621/jev-claude) - Claude Code hooks backed by Jev (TypeSafe AI) — let a cheap evaluation-only model decide whether the work is actually done.
- [jev-consumer-research](https://github.com/alex-sun-kuo/jev-consumer-research) - Consumer research explorations using TypeSafe's Jev.
- [jev-curate](https://github.com/AkashPriyadarshii/jev-curate) - High-throughput synthetic & pretraining dataset sifter for AI fine-tuning teams in Rust & Python. Parquet & JSONL streaming, Jev speculative fan-out, and post-training reasoning rubrics.
- [jev-deferred-crispification](https://github.com/dnakhoa/jev-deferred-crispification) - Position paper: the Hidden-Markov and fuzzy primitives missing from TypeSafe AI's Jev and System-One decision models. Two lemmas, one principle (Deferred Crispification), one architecture (BSF-S1).
- [jev-demos](https://github.com/Bud-ro/jev-demos) - Demos to test the effectiveness of TypeSafe's "Jev" System One Model.
- [jev-document-classification](https://github.com/Charlyhno-eng/jev-document-classification) - JEV Document Classification enables the rapid and cost-effective classification of text-based documents using AI, leveraging TypeSafe's "System One" model.
- [jev-experiments](https://github.com/amithkk/jev-experiments) - Experiments with Typesafe's Jev.
- [jev-gates](https://github.com/rashedInt32/jev-gates) - Six calibrated gates for Claude Code, judged by TypeSafe Jev: rules, scope, intent, done, claims, and commit honesty. Each one escalates, none ever approves.
- [jev-judge-bench](https://github.com/cmartinez9/jev-judge-bench) - Binary LLM-judge bench — compare Jev (TypeSafe System One) against a frontier LLM judge on speed, cost, and agreement with human labels.
- [jev-lab](https://github.com/Menny1337/jev-lab) - TypeScript experiments, evaluations, and latency benchmarks for TypeSafe's Jev model.
- [jev-lab](https://github.com/BrendanH18/jev-lab) - Six small apps and a workbench that show what TypeSafe's Jev (System One) model can do.
- [jev-lab](https://github.com/danielhirt/jev-lab) - Experiments on TypeSafe Jev (System One decision model) via OpenRouter: repeatability, perturbation, and LLM baseline comparison.
- [jev-paper-judge](https://github.com/JacobLinCool/jev-paper-judge) ([site](https://jev-paper-judge.jacob.workers.dev)) - Feedback on your paper in seconds.
- [jev-plays-pokemon](https://github.com/milanboers/jev-plays-pokemon) - Playing Pokemon Red using TypeSafe Jev.
- [jev-report](https://github.com/HackSing/jev-report) - 发明 RLHF 的人，这次做了个不会说话的模型：Jev 独立研究报告。52 页 PDF + 50 条中文实测复现包 + 143 条可回溯数据表.
- [Jev-Rug-Checker](https://github.com/BradMyrick/Jev-Rug-Checker) - A multi-chain EVM token screener built on Jev by @TypeSafe AI.
- [jev-system-one](https://github.com/heaven-hm/jev-system-one) - A polished OpenAI + TypeSafe Jev terminal interface for answers with transparent decision reports.
- [jev-taxi-dispatch](https://github.com/bahramzada/jev-taxi-dispatch) - Real-vaxt taksi dispetçerlik simulyasiyası — TypeSafe JEV (System One) modeli ilə.
- [jev-test](https://github.com/JustinRoderick/jev-test) - Testing typesafe.ai new model Jev.
- [jev-trade](https://github.com/djascorp/jev-trade) - Trading project using JEV by TypeSafe AI.
- [jev-vphone-cli](https://github.com/gpazo/jev-vphone-cli) - Jev from Typesafe.ai + vphone-cli.
- [jev-wave](https://github.com/ndolinschi/jev-wave) - TypeSafe Jev research + 5 product specs.
- [jev-x-posts](https://github.com/samoweb3/jev-x-posts) - Sortable 48-hour X post report for Jev, TypeSafe AI and Diogo Almeida, with Jev sentiment labels.
- [jevagotchi](https://github.com/stbenjam/jevagotchi) - A tiny virtual pet cared for by TypeSafe Jev through OpenRouter.
- [JEVBenchmark-Contradiction-Detection](https://github.com/AIPI-mvoronovych/JEVBenchmark-Contradiction-Detection) - Checking JEV's Contradiction detection (Model by TypeSafe.AI).
- [jevtrafficsim](https://github.com/skcache/jevtrafficsim) - TypeSafe AI's first model Jev takes on an entire city's traffic.
- [lm-studio-typesafe-chat](https://github.com/lainollll/lm-studio-typesafe-chat) - Tkinter chat and live visual narration with LM Studio, TypeSafe Jev, and Chatterbox TTS.
- [magic-8-ball](https://github.com/distributedlabs/magic-8-ball) - A TypeSafe Jev-powered Magic 8 Ball.
- [metis](https://github.com/Ayush0054/metis) - Metis: automatic GitHub issue triage powered by TypeSafe AI Jev. A reusable GitHub Action.
- [mrsecret](https://github.com/vkpdeveloper/mrsecret) - Mr. Secret — blurs secrets & PII on any page using TypeSafe AI Jev.
- [pagegrade](https://github.com/kitze/pagegrade) - Grade page sections for clarity, writing and on-page SEO. WXT + TypeSafe AI Jev.
- [penr-oz-jev-syslog-analyzer](https://github.com/derinworks/penr-oz-jev-syslog-analyzer) - An asyncio daemon that tails journald or syslog and asks Jev, for each event, which subsystem it belongs to, how severe it is, and whether it's noise. Plain code then ignores the event, alerts on it, or escalates it to a human when confidence is low.
- [pi-jeev](https://github.com/shishiv/pi-jeev) - A bounded TypeSafe Jev decision tool for Pi.
- [pi-typesafe](https://github.com/twilwa/pi-typesafe) - Pi coding-agent extension built on the TypeSafe AI System One API (Jev).
- [pi-typesafe-jev](https://github.com/legacybridge-tech/pi-typesafe-jev) - A pi extension that exposes TypeSafe (Jev, System One) judgments as five pi tools, so a model can make narrow semantic judgments while your code and your users keep control of thresholds, weights, and actions.
- [ps2-ai-agent](https://github.com/opaielsheikh/ps2-ai-agent) - Autonomous PlayStation 2 AI Agent with real-time visual telemetry HUD powered by TypeSafe Jev System One.
- [re-heitan](https://github.com/kamesan1577/re-heitan) - X（旧Twitter）のタイムラインから誹謗中傷を取り除く Chrome 拡張。判定を TypeSafe の System One モデル Jev で行う。
- [reranker](https://github.com/hev/reranker) - Use Jev (TypeSafe's System One model) as a calibrated reranker: one call, up to 30 documents, a probability per document. Apache-2.0.
- [s1-rs](https://github.com/AbdelStark/s1-rs) - Typed System One layer for Rust (Choice/Score/Noul).
- [snbt-jev-bench](https://github.com/misaalya/snbt-jev-bench) - Jev on Indonesia's SNBT 2025 university entrance test: 159 questions, seven subtests, audited answer keys.
- [system-one-gemma](https://github.com/akash-kamat/system-one-gemma) - Open-source Jev-style System One decision model. Gemma 3 270M with a scoring head — fast, calibrated decisions in a single forward pass. No text generation. Inspired by TypeSafe.ai's Jev.
- [ticket-rerank](https://github.com/Obrais-cloud/ticket-rerank) - FastAPI service that reranks support tickets by urgency using TypeSafe (Jev / System One).
- [typesafe-image-diffusion](https://github.com/Wizhill05/typesafe-image-diffusion) - Diffusion-style pixel art out of a general classifier (TypeSafe Jev): 256 parallel pixel questions + refinement passes.
- [typesafe-jev](https://github.com/gtaras7/typesafe-jev) - Screen a folder of CVs with the TypeSafe Jev decision model: typed judgments, an editable policy, free re-scoring.
- [typesafe-translate](https://github.com/Obrais-cloud/typesafe-translate) - Escribe lenguaje natural y un LLM local lo compila a variables de TypeSafe (state + questions) y las ejecuta (Jev / System One).

## Games and simulations

Games and simulations with Jev making the moves.

- [typesafe-mario](https://github.com/fhshaik/typesafe-mario) - A TypeSafe/Jev agent that plays Super Mario Bros. from structured emulator state.
- [jev-drone](https://github.com/RomanSlack/jev-drone) - Camera-only autonomous drone in MuJoCo with a small judgment model (TypeSafe Jev) in the loop at 2.5Hz.
- [typesafe-snake](https://github.com/sorrycc/typesafe-snake) - Snake auto-played by TypeSafe's Jev model: one System One choice per tick, legal moves and facts generated in code.
- [jevfire](https://github.com/kikoncuo/jevfire) ([site](https://kikoncuo.github.io/jevfire/)) - JEV-inspired parallel decisions for CUDA LLMs. One context, many decisions. vLLM API, game-agent examples, and reproducible benchmarks.
- [heist-one](https://github.com/AbdelStark/heist-one) - Observable browser stealth game: Jev makes typed guard judgments while deterministic code owns the world.
- [jev-autopilot](https://github.com/arielweinberger/jev-autopilot) - This demo uses Jev from TypeSafe AI to autonomously fly a drone in a random city from point A to point B, avoiding obstacles along the way. A trip costs $0.01.
- [got-jev](https://github.com/phureewat29/got-jev) ([site](https://jev.phureewat.com)) - Jev (TypeSafe AI) PoC through Game of Thrones.
- [jev-broadcast-lab](https://github.com/4anti/jev-broadcast-lab) - Operator lab for TypeSafe Jev. Chess Arena, closed-schema booths, Stockfish HUD for review only.
- [tsai-civ2](https://github.com/phyous/tsai-civ2) - TypeSafe Jev plays original Civilization II in a browser, with live action probabilities. Experimental full-game harness.
- [cyber-breach-jev](https://github.com/rchovatiya88/cyber-breach-jev) - Cyber-Breach: The Jev Protocol - A tactical cyberpunk arena combat game powered by TypeSafe AI Jev System One decision model.
- [jev-chess-lab](https://github.com/denikuchero/jev-chess-lab) ([site](https://denikuchero.github.io/jev-chess-lab/)) - Jev chess experiments: independent decisions vs tactical and Stockfish assistance, with full traces and video replays.
- [jev-play-ping-pong](https://github.com/Icohen007/jev-play-ping-pong) ([site](https://indispensable-lingonberry-hot.julius.site/)) - Jev plays browser table tennis in real time: structured telemetry, typed decisions, ordinary Chrome inputs, and auditable evidence.
- [jev-plays-2048](https://github.com/joshbla/jev-plays-2048) - A visible 2048 experiment powered by TypeSafe.
- [jev-plays-doom](https://github.com/tirukovelamanoj/jev-plays-doom) - A System One model driving the game through structured state, no pixels.
- [jev-snake](https://github.com/iammusham/jev-snake) - An experimental Snake environment where the game engine owns deterministic rules and TypeSafe AI's Jev makes the movement decision from structured state on every tick.
- [jev-tetris](https://github.com/MachineLearning-Nerd/jev-tetris) - A visual TypeSafe demo where Jev chooses verified Tetris placements.
- [river-run-typesafe](https://github.com/ashaazami/river-run-typesafe) - River shooter game in Python, inspired by Atari's River Raid, played by a TypeSafe AI pilot.
- [typesafe-3d-chess](https://github.com/malDuffin/typesafe-3d-chess) - 3D chess powered by TypeSafe AI (Jev). AI vs AI by default, or play either side. Multiple difficulty levels.
- [typesafe-chess](https://github.com/TholeG/typesafe-chess) - Chess where both players are TypeSafe's Jev model: every move is a typed Choice decision.
- [typesafe-jev-drone-demo](https://github.com/kxzk/typesafe-jev-drone-demo) - Three.js drone simulator with a Python backend and live TypeSafe Jev navigation.

## Demos and playgrounds

Live demos and playgrounds.

- [jev-synergy-screening](https://github.com/PistachioAIHQ/jev-synergy-screening) - Jev (TypeSafe System One) × ASReview SYNERGY abstract screening demo — Choice/Noul vs gold labels.
- [typesafe-arena](https://github.com/DeepBlueDynamics/typesafe-arena) - A playground for TypeSafeAI's Jev Model.
- [jev-ad-preflight](https://github.com/cardotrejos/jev-ad-preflight) - Typesafe/Jev public X demo.
- [jev-should-i-apply](https://github.com/cardotrejos/jev-should-i-apply) - Typesafe/Jev public X demo.
- [jev-synergy-screening](https://github.com/pistachiopranay/jev-synergy-screening) - Jev (TypeSafe System One) × ASReview SYNERGY abstract screening demo — Choice/Noul vs gold labels.
- [jev-user-jury](https://github.com/cardotrejos/jev-user-jury) - Typesafe/Jev public X demo.
- [jevvin-off](https://github.com/nsillik/jevvin-off) - Prototyping against TypeSafe's Jev System One API: a one-ticket quickstart and a Bluesky Jetstream firehose demo.
- [typesafe-ai-playground](https://github.com/markjaquith/typesafe-ai-playground) - A playground for experiments around Jev, TypeSafe's System One model.
- [typesafe-playground](https://github.com/kavehmz/typesafe-playground) - Interactive experiments with TypeSafe Jev, from support routing to 3D driving simulations with real AI decisions and visible sensor inputs.

## Benchmarks and research

Benchmarks, evals, calibration studies, and open replicas.

- [openjev](https://github.com/TheoLeeCJ/openjev) - Runs a Jev-like interface on a local model by reading option logits instead of generating text.
- [jevlike](https://github.com/vinnylarouge/jevlike) - Train a small model that chooses among a changing list of text options, one probability per option in a single pass.
- [openjev-sglang](https://github.com/ekzhang/openjev-sglang) ([site](https://ekzhang--openjev-sglang-openjev.us-west.modal.direct)) - Jev-compatible API endpoint based on open models (prefill-only).
- [typesafe-ai-benchmark](https://github.com/iammrduncan/typesafe-ai-benchmark) ([site](https://hackersintheloop.org/)) - This is a LLM Gateway that mimics typesafe ai structured output. Like an imposter Jev.
- [daf-jev](https://github.com/docxology/daf-jev) - Daf-jev: composable Python toolkit for TypeSafe's Jev (System One) decision API — question builders, confidence gates, evaluator, calibration, CLI, MCP server, agent skill.
- [openjev](https://github.com/zhihz/openjev) - Local bilingual probability decisions from context, questions, and candidate answers. Independent research preview inspired by TypeSafe Jev.
- [system-one-open](https://github.com/mithalouni/system-one-open) - Open replica of TypeSafe's Jev: typed calibrated decisions in one forward pass, on Gemma 4 E2B / Gemma 3 270M (Modal).
- [jev-benchmark](https://github.com/wondertwins/jev-benchmark) - Benchmarks and a playground for TypeSafe's Jev (System One) model: chess, and who-is-the-player-talking-to for speech-to-text game NPCs.
- [almond-fastloop](https://github.com/eriestra/almond-fastloop) - Almond-fastloop: Almond's browser computer-use rig (Chrome DevTools + TypeSafe Jev), and the Browser Use Olympics benchmark it is measured on.
- [jev-agent-failure-benchmark](https://github.com/TokenTrim/jev-agent-failure-benchmark) - Benchmarking Jev (Typesafe.ai) against a strong LLM on the Who&When Pro agent-failure-attribution benchmark (text subset).
- [jev-little-airways](https://github.com/lbotinelly/jev-little-airways) - A show-and-tell capability study for Jev, TypeSafe's System One decision model.
- [padflow-jev-evals](https://github.com/zsavage8/padflow-jev-evals) - Typed-decision benchmark from PadFlow (land development SaaS): schemas, anonymized labeled rows, and a runner for confidence-calibrated models like TypeSafe Jev.
- [Verdict-open-jev](https://github.com/Heman10x-NGU/Verdict-open-jev) - Non-autoregressive decision engine on ModernBERT (151M) with calibrated uncertainty (RLCD), TypeSafe AI Jev benchmark audit, and in-browser WebGPU playground.
- [jev-benchmark](https://github.com/themsquared/jev-benchmark) - Reproducible benchmark for TypeSafe AI's Jev on agent tool-call risk classification: accuracy, latency, and whether the confidence score is worth routing on.
- [jev-evals](https://github.com/NicolasMontone/jev-evals) - Rubric-based eval harness cheap enough to run on every PR, powered by typesafe-ai/jev.
- [jev-finance-benchmark](https://github.com/hifizz/jev-finance-benchmark) - Typesafe.ai model jev finance benchmark.
- [jev-gamebenchmark](https://github.com/aieo-product/jev-gamebenchmark) - Sandbox & benchmark: optimize how you ask Jev (TypeSafe System One) to play falling-block puzzle games, head-to-head against LLMs.
- [jev-tick-lab](https://github.com/shunta-furukawa/jev-tick-lab) - A forward-only experiment: Jev (TypeSafe System One) making one-second trading judgments on bitbank, logged for calibration analysis.
- [openjev-experiments](https://github.com/zefir1990/openjev-experiments) ([site](https://demensdeum.com)) - Openjev experiments.
- [switchboard](https://github.com/aniruddh-krovvidi/switchboard) - Guardrail + model router for LLM gateways on TypeSafe's Jev (System One model), with an independent accuracy/calibration/latency evaluation. Stdlib Python.
- [typesafe-ai_smoke-test](https://github.com/TyrellD1/typesafe-ai_smoke-test) - Smoke test: route prompts to a work or life database with TypeSafe AI (Jev), 30-case eval.

## Other lists

Other public directories of Jev projects.

- [awesome-jev-by-typesafe](https://github.com/Anil-matcha/awesome-jev-by-typesafe) ([site](https://typesafe.ai/)) - Evidence-backed use cases, patterns, prompts, and starter code for TypeSafe Jev — a System One model for fast, typed, confidence-aware decisions in software.
- [awesome-typesafe](https://github.com/AbdelStark/awesome-typesafe) ([site](https://abdelstark.github.io/awesome-typesafe/)) - A curated list of official resources and community projects for TypeSafe, System One models, and Jev.
- [awesome-jev](https://github.com/yibie/awesome-jev) - A curated list of public projects, integrations, and discussions built on Jev — TypeSafe AI's System One model for typed decisions.
- [awesome-jev](https://github.com/AnotiaWang/awesome-jev) - A curated list of awesome Jev / TypeSafe System One applications, libraries, and resources.
- [awesome-jev](https://github.com/hellogumbo/awesome-jev) ([site](https://awesomejev.com)) - A community directory of projects built on Jev, TypeSafe AI's System One model.
- [awesome-jev](https://github.com/sontakey/awesome-jev) - Unofficial list of insanely useful TypeSafe AI Jev / System One projects.
- [awesome-jev](https://github.com/OmniJev/awesome-jev) ([site](https://omnijev.github.io/awesome-jev/)) - Papers, open reproductions and independent evaluations behind System One models and Jev.
- [awesome-jev-use-cases](https://github.com/SeeAPI/awesome-jev-use-cases) ([site](https://www.seeapi.com/)) - Explore real-world use cases and projects built with TypeSafe AI's Jev: content moderation, AI agents, model routing, and semantic search. Curated by SeeAPI.
- [awesome-jev-usecases](https://github.com/aliaihub/awesome-jev-usecases) - Evidence-backed use cases, patterns, and guidance for building with Jev, TypeSafe AI's System One model. Every claim is labeled and sourced.
- [awesome-jev](https://github.com/rhc98/awesome-jev) ([site](https://awesome-jev.xyz)) - Projects built on Jev (TypeSafe AI's System One model), curated by Jev itself.
- [awesome-jev](https://github.com/fatwang2/awesome-jev) - A source-backed Jev project directory with a reusable Jev-only GitHub review workflow.
- [awesome-jev-prompt](https://github.com/yangzhou-chaofan/awesome-jev-prompt) - Latest top 100 showcases for jev (keep updating) from x / github / latest sources.
- [awesome-jev-zh](https://github.com/yzfly/awesome-jev-zh) ([site](https://typesafe.ai)) - Jev / TypeSafe System One 中文精选列表：官方资料、SDK、爆款应用、Agent 工具、开源复现与独立评测，附中文上手指南，每日自动收录 GitHub 热门项目。

## Contributing

Edit `data/projects.json` (it drives this README) and run `npm run build`. See [CONTRIBUTING.md](CONTRIBUTING.md).
