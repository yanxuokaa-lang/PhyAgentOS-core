<!-- Rendered from data/entries.json by scripts/render.mjs. Edit the data, not this file. -->
# Awesome TypeSafe Jev [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

[![site](https://img.shields.io/badge/site-browse_with_media-1f6f4a)](https://thevibeworks.github.io/awesome-typesafe-jev/)
[![entries](https://img.shields.io/badge/entries-1093-informational)](data/entries.json)
[![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

<p align="center">
  <a href="https://thevibeworks.github.io/awesome-typesafe-jev/"><img src="docs/assets/banner.svg" alt="Awesome TypeSafe Jev: a question goes in, a probability comes out" width="820"></a>
</p>

A curated list of projects built on [Jev](https://typesafe.ai), TypeSafe AI's System One model. Jev does not write text. You send a `state` and typed questions (Choice, Score, Noul) and get probabilities back.

**1093 projects, 35 editors' picks, 70 things to read and watch. Nothing is listed unread.** A sweep of GitHub, npm and Hugging Face found 2,163 candidate repos; 1,493 passed mechanical checks; all of those that are actually about Jev were reviewed (1,340), and 1093 are listed. Stars were not a criterion: the median candidate has 0.

**[Browse the site](https://thevibeworks.github.io/awesome-typesafe-jev/)** for media, filters and search. The data is one file: [`data/entries.json`](data/entries.json).

Not affiliated with TypeSafe AI.

## Contents

- [Browser and computer use](#browser-and-computer-use)
- [Agent tooling](#agent-tooling)
- [Games and control](#games-and-control)
- [Benchmarks and research](#benchmarks-and-research)
- [Applications and demos](#applications-and-demos)
- [Official](#official)
- [SDKs and integrations](#sdks-and-integrations)
- [Read and watch](#read-and-watch)
- [Measured by us](#measured-by-us)
- [Other lists](#other-lists)
- [How entries get in](#how-entries-get-in)
- [Contributing](#contributing)

## Browser and computer use

Agents that click and type, with Jev making each step's decision.

### [jev-ultrafast](https://github.com/browser-use/jev-ultrafast)

<a href="https://github.com/browser-use/jev-ultrafast"><img src="docs/media/browser-use__jev-ultrafast.gif" alt="jev-ultrafast: Browser agent where one Jev request picks both the operation and the target element from an indexed DOM table, with a small LLM writing typed text" width="640"></a>

<sub>Media: browser-use/jev-ultrafast (MIT)</sub>

Browser agent where one Jev request picks both the operation and the target element from an indexed DOM table, with a small LLM writing typed text.

**Why it is here:** 1x demo GIF/MP4 of a Google Flights search, README claims 7,073 ms for that run and a median 9.450 s to 7.092 s across six alternating runs with stated measurement boundaries, plus uv setup, library API and offline tests.

**Know before you use it:** Timings are three repeats of one task on one browser profile, and it needs a second paid key for the text model.

<sub>MIT · Python</sub>

### [jev-turbo](https://github.com/sightmap/jev-turbo)

<a href="https://github.com/sightmap/jev-turbo"><img src="docs/media/sightmap__turbo.gif" alt="jev-turbo: Go CLI that turns a page into named sightmap components and has Jev pick the next action and judge goal completion, with no large model in the loop" width="640"></a>

<sub>Media: sightmap/turbo (MIT)</sub>

Go CLI that turns a page into named sightmap components and has Jev pick the next action and judge goal completion, with no large model in the loop.

**Why it is here:** npm and go install lines, a real step log with per-phase timings, a 1x demo GIF, and README claims 10/10 goals on two sites at 0.24 to 0.30 s a step versus Claude Sonnet in the same seat, with run files in bench/.

**Know before you use it:** Goals are 2 to 12 steps on cooperative sites, and typed values must be supplied by the user or an optional Claude planning call.

<sub>MIT · Go</sub>

### [jev-browse](https://github.com/kyrylosyzonenko/jev-browse)

<a href="https://github.com/kyrylosyzonenko/jev-browse"><img src="docs/media/kyrylosyzonenko__jev-browse.gif" alt="jev-browse: CLI and MCP server where Jev picks every click, which supplied text to type, and when to stop, with Vercel agent-browser executing the actions" width="640"></a>

<sub>Media: kyrylosyzonenko/jev-browse (MIT)</sub>

CLI and MCP server where Jev picks every click, which supplied text to type, and when to stop, with Vercel agent-browser executing the actions.

**Why it is here:** Demo GIF of a full checkout flow, runs via npx, exit codes, stated limits; README claims 30/30 passes at 4.4 s median and $0.0009 per task vs Claude Code 30/30 at 9.4 s and $0.0679 on the same 10 tasks x 3 runs, with a rerunnable eval.mjs.

**Know before you use it:** Ten short tasks only, and it sends page content and any supplied password to the API on every step.

<sub>MIT · JavaScript</sub>

### [mobile-jev](https://github.com/droidrun/mobile-jev)

Android phone agent on the Mobilerun API where Jev chooses each tap, type, scroll, or app launch, with a React studio, CLI, and execution traces.

**Why it is here:** Demo GIF of Uber navigation (README claims about 21 seconds for 9 actions and says no booking was completed), a dark-theme demo that re-reads the switch to verify, and `pnpm check` CI.

**Know before you use it:** Requires a paid Mobilerun device and key, so it is not reproducible without that vendor's service.

<sub>MIT · JavaScript</sub>

### [typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use)

macOS computer-use loop: OCR plus accessibility tree become a numbered item list, Jev picks action and target, a writer model handles free text only.

**Why it is here:** Install and usage, per-step run folders with exact payloads and probabilities for offline replay, CI and tests; README claims $0.0002 and 0.13-0.38 s per decision vs $0.032 and 5.2 s for a frontier model on the same screenshot.

**Know before you use it:** No demo video or task success rate; the cost comparison is a single decision, and the README admits the frontier model needed no date-parsing help.

<sub>MIT · Python</sub>

### [jev-browser](https://github.com/Ying-Kai-Liao/jev-browser)

Playwright library, CLI, and MCP server where the calling LLM names one outcome per step and Jev picks element, action, and done/blocked/irreversible status.

**Why it is here:** npm package with a one-line `claude mcp add`, offline and e2e tests, a bench runner with ground-truth checks, and a demo video in the README; README claims 40/42 tasks correct on live sites with 0 false done claims.

**Know before you use it:** The token-saving comparison against a Playwright-MCP loop is an estimate, and the 42-task suite is self-built and self-scored.

<sub>MIT · JavaScript</sub>

### [jev-mobile](https://github.com/Friedjof/jev-mobile)

Android control loop where Jev picks one action from a prevalidated list built from the UI tree, run through Mobile MCP or a bundled accessibility bridge.

**Why it is here:** uv install and devices/inspect/decide/run CLI commands, confidence and margin gates with escalation, an Android companion app, Docker and MCP surfaces, CI, and a live Jev smoke test script.

**Know before you use it:** Proof of concept exercised only on Android Settings, and the README still carries a note to add the demo GIF, so the recording may not exist.

<sub>MIT · Python</sub>

- [jkudish/jev-browser](https://github.com/jkudish/jev-browser) **(notable)** - Headless browser agent as MCP server, CLI and library where Jev picks one page action per step and scores goal-met and stuck probabilities. <sub>MIT · TypeScript</sub>
- [pumpkinredbean/bside](https://github.com/pumpkinredbean/bside) **(notable)** - CLI that drives the Aside browser with Jev picking action and element each tick from an enumerated set, with a timed benchmark against two LLM engines. <sub>MIT · JavaScript</sub>
- [agent-labs-dev/fastbrowse](https://github.com/agent-labs-dev/fastbrowse) **(notable)** - Browser agent where Jev picks each action from indexed page controls while an LLM plans and reads, citing page quotes; includes a 21-task head-to-head eval. <sub>MIT · Python</sub>
- [brnyxx/jev-ra](https://github.com/brnyxx/jev-ra) **(notable)** - MCP server and CLI giving coding agents a browser where Jev picks operation and element each step; README reports 4-8x faster than browser-use on 3 tasks. <sub>MIT · Python · [live](https://brnyxx.github.io/jev-ra/)</sub>
- [CaiZongyuan/mobile-agent](https://github.com/CaiZongyuan/mobile-agent) **(notable)** - Android phone agent that reads the accessibility tree via Mobilerun Portal, has Jev choose among candidate actions and taps via adb; timings reported. <sub>no license · Python</sub>
- [divyekant/jev-qa](https://github.com/divyekant/jev-qa) **(notable)** - Python runner for browser acceptance tests and design conformance checks driven by Jev, with frozen evaluation reports and seeded-defect results. <sub>no license · Python</sub>
- [godovasik/infcraft-typesafe](https://github.com/godovasik/infcraft-typesafe) **(notable)** - Browser agent where Jev picks an operation and an indexed element each step and a small LLM only types text, with an Infinite Craft adapter. <sub>MIT · Python</sub>
- [jcpsimmons/jev-macos-loop](https://github.com/jcpsimmons/jev-macos-loop) **(notable)** - Native macOS computer-use loop: OmniParser CoreML, Vision OCR and accessibility labels feed Jev, which picks the element to click; 6/6 tasks measured. <sub>AGPL-3.0 · JavaScript</sub>
- [affirmitv/ghosthands](https://github.com/affirmitv/ghosthands) - GUI automation that drives a real screen through a USB-HID Pico, with Jev choosing the operation and element from an indexed control table. <sub>MIT · Python</sub>
- [moritzkremb/jev-voice-browser](https://github.com/moritzkremb/jev-voice-browser) - Node app that controls a headed Chromium by voice, asking Jev a dozen typed questions on every partial transcript to decide intent and target. <sub>MIT · JavaScript</sub>
- [wy-coliney/jev-browser-use](https://github.com/wy-coliney/jev-browser-use) - Codex browser skill that hands navigation, clicks, toggles and scrolling to Jev while Codex keeps text input and final verification. <sub>MIT · JavaScript</sub>
- [razaanstha/ulka](https://github.com/razaanstha/ulka) - Chromium side-panel extension where an FX planner sets subgoals and Jev picks constrained actions from the accessibility tree, via Vercel AI Gateway. <sub>MIT · TypeScript</sub>
- [hqman/JevScout](https://github.com/hqman/JevScout) - Agent skill and CLI that drives Chrome over CDP through company sites while Jev scores every link and job posting against a query. <sub>no license · Python</sub>
- [SomeshSampat2/android-control](https://github.com/SomeshSampat2/android-control) - MCP server controlling Android devices over ADB with a Jev fast mode for goal-driven steps, tap-by-description and yes/no screen questions. <sub>Apache-2.0 · Python</sub>
- [grabbou/jevil](https://github.com/grabbou/jevil) - Mobile QA agent that reads an iOS or Android app via agent-device, lets Jev choose each action until pass or fail, and saves a trace and recording. <sub>no license · JavaScript</sub>
- [vinilana/jev-browser](https://github.com/vinilana/jev-browser) - TypeScript Playwright harness where an OpenRouter LLM plans subgoals and writes field text while Jev chooses each action and judges the final outcome. <sub>no license · TypeScript</sub>
- [kbitgood/jev-cdp](https://github.com/kbitgood/jev-cdp) - Bun/TypeScript port of jev-ultrafast that drives Chrome over CDP with Jev choosing one operation and observed target per step, plus a verified todo scenario. <sub>MIT · TypeScript</sub>
- [matthewdonsemail-lab/open-typesafe-camoufox](https://github.com/matthewdonsemail-lab/open-typesafe-camoufox) - CLI browser agent that drives headed Camoufox from a DOM read, asking Jev for each next action and calling a writing model only for free text. <sub>no license · Python</sub>
- [Nainish-Rai/jev-frontend-qa](https://github.com/Nainish-Rai/jev-frontend-qa) - Python CLI for frontend QA where Jev selects browser actions over observed controls while code checks DOM, HTTP and SQLite contracts, with a todo demo. <sub>no license · Python</sub>
- [paulsmith/computer-use-jev](https://github.com/paulsmith/computer-use-jev) - Go CLI that drives native macOS apps through the Accessibility API, with Jev choosing the next action and target token from the current snapshot. <sub>MIT · Go</sub>
- [ranjan2829/AskJev](https://github.com/ranjan2829/AskJev) - Chrome/Brave extension plus MCP server where Jev picks on-page actions over CDP and a guard freezes pay, delete, send and publish clicks. <sub>MIT · TypeScript</sub>
- [romaluev/jev-ego](https://github.com/romaluev/jev-ego) - TypeScript browser agent for the ego lite browser reusing jev-ultrafast's indexed action policy; Jev picks operation and target in one request. <sub>no license · TypeScript</sub>
- [eriestra/almond-fastloop](https://github.com/eriestra/almond-fastloop) - About 200 lines of dependency-free Node that drive Chrome over DevTools with Jev choosing each action, plus a hosted five-event browser-agent benchmark. <sub>MIT · HTML · [live](https://sites.almond.build/browser-use-olympics/)</sub>
- [himomohi/aside-jev](https://github.com/himomohi/aside-jev) - MCP server and skill that lets Aside browser agents pick actions via Jev Choice over an app-owned candidate table, with validation and a mock mode. <sub>MIT · Python</sub>
- [NobleSpartan6/otto](https://github.com/NobleSpartan6/otto) - Electron desktop agent for macOS and Windows that reads selected apps via accessibility APIs and local OCR and lets Jev choose each action. <sub>MIT · TypeScript · [live](https://noblespartan6.github.io/otto/)</sub>
- [serejaris/voice-browser](https://github.com/serejaris/voice-browser) - Chrome MV3 extension and local preview that control the active tab by voice or text, with Jev via Vercel AI Gateway choosing among limited DOM actions. <sub>MIT · JavaScript</sub>
- [tontoko/jev-browser](https://github.com/tontoko/jev-browser) - Playwright-based SDK, persistent CLI, and MCP server where Jev selects among observed DOM candidates for act, observe, extract, and bounded goal runs. <sub>Apache-2.0 · JavaScript</sub>
- [abeatrix/cline-plugin-jev-browser](https://github.com/abeatrix/cline-plugin-jev-browser) - Cline plugin giving the agent a Playwright browser where Jev picks operation and DOM target each step via AI Gateway and a small LLM writes typed text. <sub>no license · TypeScript</sub>
- [AE-AlphaEdge/grokskill-jev](https://github.com/AE-AlphaEdge/grokskill-jev) - Fork of Browser Use's jev-ultrafast adding a Grok Build skill, a PowerShell runner, reuse of the open Chrome tab and a long-lived harness daemon. <sub>MIT · Python</sub>
- [aidil2105/jev-browser-pilot](https://github.com/aidil2105/jev-browser-pilot) - Python package for browser and desktop automation over CDP where the model only picks the next candidate id and code handles observe, act and verify. <sub>MIT · Python</sub>
- [alexbejan/jevkit](https://github.com/alexbejan/jevkit) - Python judgement layer for desktop and phone automation: verify an action landed, pick a listed element, classify a screen, each with an act/caution/stop gate. <sub>no license · Python</sub>
- [Austin-Resi/grok-bot-go-fast](https://github.com/Austin-Resi/grok-bot-go-fast) - Bot plugin that ports the jev-ultrafast loop: DOM snapshot, Jev picks the node via AI Gateway, CDP click, pausing for text or unclear decisions. <sub>no license · TypeScript</sub>
- [Ayush0054/menso](https://github.com/Ayush0054/menso) - Native macOS voice assistant where Jev selects one candidate from a request-scoped catalog of Mac actions and the app requires local approval to execute. <sub>MIT · Swift</sub>
- [bartek-filipiuk/linux-agent-workbench](https://github.com/bartek-filipiuk/linux-agent-workbench) - Linux desktop app where an agent drives a containerized terminal and browser, with an experimental mode that hands fast browser subgoals to Jev. <sub>MIT · TypeScript</sub>
- [bottlebrushes/jev-orb](https://github.com/bottlebrushes/jev-orb) - macOS push-to-talk floating orb that transcribes speech with local Whisper and dispatches the goal to jev-ultrafast to drive the browser. <sub>no license · Makefile</sub>
- [cartermccann/typesafe-computer-use-hyprland](https://github.com/cartermccann/typesafe-computer-use-hyprland) - Fork of typesafe-computer-use adding a Hyprland adapter: grim screenshot, tesseract OCR, Jev Choice, then hyprctl and ydotool actions. <sub>MIT · Python</sub>
- [CorieW/JevTest](https://github.com/CorieW/JevTest) - TypeScript CLI for exploratory browser testing: Jev picks Playwright actions, deterministic assertions decide pass/fail, traces replay without API calls. <sub>no license · TypeScript</sub>
- [eriestra/browser-use-olympics](https://github.com/eriestra/browser-use-olympics) - Hosted five-event timed benchmark for browser agents plus a roughly 200-line Chrome DevTools loop where Jev picks each action. <sub>MIT · HTML · [live](https://sites.almond.build/browser-use-olympics/)</sub>
- [feliperfpereira/jevBrowser](https://github.com/feliperfpereira/jevBrowser) - Playwright task runner where Jev picks the next action and target element from an ARIA snapshot each step, with a CLI and an HTTP API. <sub>no license · TypeScript</sub>
- [jal-co/jev-agent-browser](https://github.com/jal-co/jev-agent-browser) - Python adapter where Jev picks the next browser operation and target and Vercel Agent Browser executes it, with a JSON-lines server for Pi. <sub>MIT · Python</sub>
- [jangya/jev-webmcp](https://github.com/jangya/jev-webmcp) - Chrome side-panel agent that uses Jev to select and run tools exposed by WebMCP-enabled pages, with an optional helper model for argument values. <sub>MIT · TypeScript</sub>
- [jasonduncan/jev-browser](https://github.com/jasonduncan/jev-browser) - Agent skill and runtime where Jev selects page elements in a continuous observe, act, verify loop using the agent's existing browser tools. <sub>MIT · JavaScript</sub>
- [jdorado/ez-fast-browser](https://github.com/jdorado/ez-fast-browser) - Plugin for Ez agents that runs bounded Chromium sessions where Jev picks an operation and target from an indexed table of visible controls. <sub>MIT · Python</sub>
- [jekhov/jekhov](https://github.com/jekhov/jekhov) - Playwright library and CLI where Jev picks a target from filtered accessibility-tree candidates or abstains, currently proposing actions in shadow mode. <sub>MIT · TypeScript</sub>
- [jfariasf87/Krilin](https://github.com/jfariasf87/Krilin) - Python host and Kotlin accessibility service that let Jev choose grounded actions on an Android emulator, with CLI, optional MCP server and demo app. <sub>MIT · Python</sub>
- [juancristobalgd1/jevRemote](https://github.com/juancristobalgd1/jevRemote) - Playwright CLI that lists visible labelled links and buttons, asks Jev which to click toward a goal, and prints confidence and latency per step. <sub>no license · TypeScript · [live](https://juancristobalgd1.github.io/jevRemote/)</sub>
- [krw82/jev-playwright-mcp](https://github.com/krw82/jev-playwright-mcp) - MCP proxy in front of @playwright/mcp that uses Jev to classify page state, mask prompt-injection spans, prune snapshots to a goal, and gate risky actions. <sub>MIT · TypeScript</sub>
- [legostin/jev-browser](https://github.com/legostin/jev-browser) - Browser automation MCP server and skill for Codex and Claude Code where Jev chooses action sequences and a Chrome extension executes them. <sub>no license · TypeScript</sub>
- [MahmoudAdelbghany/jev-browser](https://github.com/MahmoudAdelbghany/jev-browser) - Browser MCP server where Jev picks each Playwright action in one call and escalates to the driving LLM on low confidence, loops or stalls. <sub>no license · JavaScript</sub>
- [maskjelly/TiVM](https://github.com/maskjelly/TiVM) - Computer-use agent for a disposable Docker Linux desktop that reads the AT-SPI accessibility tree and lets Jev or GPT plan clicks, with per-task verdicts. <sub>MIT · Python</sub>
- [max1874/jev-computer-use](https://github.com/max1874/jev-computer-use) - macOS computer-use agent where Jev picks from a numbered table of accessibility-tree elements and menu commands instead of screenshots. <sub>MIT · Python</sub>
- [MSalvalaggio/jev-reflex](https://github.com/MSalvalaggio/jev-reflex) - MCP server that lets Claude hand off a whole browser task; Jev picks each click, type or select from an element table and returns a verifiable result. <sub>MIT · Python</sub>
- [novnski/luna-computer-use](https://github.com/novnski/luna-computer-use) - Computer-use MCP server and Chrome extension where Jev selects the live UI element for every browser or native action and the caller plans. <sub>no license · JavaScript</sub>
- [phd-peter/ego-jev](https://github.com/phd-peter/ego-jev) - Bounded browser loop where Jev picks an operation and target from the current ego-lite snapshot and a text model is called only to type text. <sub>MIT · TypeScript</sub>
- [raydocs/egolite-jev](https://github.com/raydocs/egolite-jev) - Agent skill that clicks through pages in ego-browser using a Jev Choice over ranked controls and reports success only on a URL or title match. <sub>MIT · JavaScript</sub>
- [schulxf/browser-qa](https://github.com/schulxf/browser-qa) - Agent skill for browser QA that drives agent-browser, requires screenshot inspection and uses Jev for bounded evidence judgments before a review gate. <sub>MIT · JavaScript</sub>
- [tylergibbs1/sift](https://github.com/tylergibbs1/sift) - Chrome extension that scores each Google result with four Noul and one Score question, reorders the page, and dims or folds sales pages and SEO filler. <sub>MIT · TypeScript</sub>
- [victortran0904/Jev-Browser-Use](https://github.com/victortran0904/Jev-Browser-Use) - Local browser agent where Jev picks one bounded action from a DOM snapshot of up to 180 elements and code validates and executes it via an extension. <sub>no license · TypeScript</sub>
- [xpressabhi/jev-browser](https://github.com/xpressabhi/jev-browser) - OpenCode plugin and harness-agnostic core where Jev picks one operation and target per cycle from visible page text and a small model writes typed text. <sub>MIT · TypeScript</sub>
- [yatharth1706/jev-automation](https://github.com/yatharth1706/jev-automation) - Voice-controlled Playwright browser where one Jev call picks intent, target element and risk, with confidence-gated confirmation. <sub>no license · TypeScript</sub>
- [yishu-ziyu/By-Your-Side](https://github.com/yishu-ziyu/By-Your-Side) - Chrome side-panel assistant for reading and web tasks that optionally routes display commands through Jev, cutting median latency 2.60s to 0.77s. <sub>no license · TypeScript</sub>
- [yousudip/lizard-agent](https://github.com/yousudip/lizard-agent) - Playwright browser agent with no LLM calls: Jev answers a 7-question fan-out per step over a typed action space, with HUD and JSONL traces. <sub>MIT · Python</sub>

## Agent tooling

Routers, guardrails, verifiers and harness parts built on typed answers.

### [pi-warden](https://github.com/DevMortimer/pi-warden)

<a href="https://github.com/DevMortimer/pi-warden"><img src="docs/media/devmortimer__pi-warden.png" alt="pi-warden: Guardrail extension for the Pi coding agent: Jev judges each write/edit/bash call against project rules and steers the agent instead of prompting the user" width="640"></a>

<sub>Media: DevMortimer/pi-warden (MIT)</sub>

Guardrail extension for the Pi coding agent: Jev judges each write/edit/bash call against project rules and steers the agent instead of prompting the user.

**Why it is here:** README claims a paired A/B eval (150 headless runs: 6 rule violations with it off, 0 on) with a separate mechanical checker, a replay of 17,160 guarded calls from 321 sessions, 185 offline tests, and publishes the axes where it showed no effect.

**Know before you use it:** Only works inside Pi, the benchmark lives in the same repo as the tool, and sample sizes are small (15 tasks, two models) by the author's own admission.

<sub>MIT · TypeScript</sub>

### [pi-jev](https://github.com/y0usaf/pi-jev)

Pi coding agent extension that gates bash/write/edit calls with four Jev questions, judges bash output for secrets and failure class, and adds a jev_ask tool.

**Why it is here:** One-line `pi install`, full config reference, and calibration tables; README claims 53 output fixtures run three times each (203 requests, 0 failures, 126 ms median) and documents a rejected question wording with its scores.

**Know before you use it:** Gate thresholds rest on six states with a handful of runs each, which the README itself calls a smoke calibration, so enforce mode is off by default.

<sub>MIT · TypeScript</sub>

### [winnow](https://github.com/GhalebDweikat/winnow)

Claude Code plugin that asks Jev per block whether a large Read/Bash/Grep result is needed, and replaces confident-no blocks with a recallable stub.

**Why it is here:** Plugin install commands, a keyless `winnow demo --fake`, shadow mode, pytest + plugin tests with a CI badge, and an offline replay harness; README claims results on 300 real cases with 97 blind hand labels and 16 ms sidecar hook overhead.

**Know before you use it:** The measured numbers live in docs/DESIGN.md rather than the README, and the weak-label regret is by its own admission an upper bound from one person's sessions.

<sub>MIT · Python</sub>

### [jev-axi](https://github.com/shiftynick/jev-axi)

CLI for agents and scripts: pick/rate/check/rank/filter, diff review, log triage, injection guard, pre-tool-use safety hook, git hooks, GitHub Action.

**Why it is here:** Published on npm with CI, real command output, a local cache and usage ledger; README claims the safety hook blocks 18/18 harmful of 44 labeled tool calls (bench/cases/safety.yaml) and reports a negative result: 25% fewer files read but same cost on a 390k-line repo.

**Know before you use it:** Very broad surface for a days-old tool, and the safety benchmark is a small self-labeled set.

<sub>MIT · TypeScript</sub>

### [jev-router](https://github.com/gargpratyush/jev-router)

<a href="https://github.com/gargpratyush/jev-router"><img src="docs/media/gargpratyush__jev-router.png" alt="jev-router: Loopback proxy that launches Claude Code or Codex and uses one Jev call per user turn to pick the model tier, with a /jev-explain report of each decision" width="640"></a>

<sub>Media: gargpratyush/jev-router (MIT)</sub>

Loopback proxy that launches Claude Code or Codex and uses one Jev call per user turn to pick the model tier, with a /jev-explain report of each decision.

**Why it is here:** npm install plus `jev-claude`/`jev-codex` commands, explicit routing policy rules, model-picker screenshots, and an `npm test` suite plus a live routing test script.

**Know before you use it:** No measurement of routing quality or cost saved, it depends on undocumented CLI wire formats, and README says it was developed and tested on Windows only.

<sub>MIT · JavaScript</sub>

### [jev-review](https://github.com/NiazMorshed2007/jev-review)

Local MCP server with one tool that scores a diff on ~19 code-quality dimensions via Jev Score questions and reports per-dimension deltas between reviews.

**Why it is here:** Demo video, install commands for Claude Code/Codex/Cursor/OpenCode, documented tool schema, unit and MCP protocol tests with local fakes, and an explicit statement of what is sent to the API.

**Know before you use it:** No evidence that the Jev scores track real code quality; the agent loop could chase numbers, which the README only addresses with guidance text.

<sub>MIT · TypeScript</sub>

### [jev-mcp](https://github.com/jkudish/jev-mcp)

MCP server exposing Jev as agent tools: verify claims against evidence, screen fetched text for injection, rank candidates, classify batches, decide.

**Why it is here:** Published npm package with install lines for five MCP clients, argument/result pairs labelled as live output for every tool, CI badge, unit tests plus key-gated e2e tests, and four provider backends.

**Know before you use it:** Self-described proof of concept; thresholds are cookbook defaults and the 'real use' examples are three anecdotes, not an evaluation.

<sub>MIT · TypeScript</sub>

### [typesafe-mcp](https://github.com/itsmostafa/typesafe-mcp)

Single Go binary MCP server exposing one `evaluate` tool that forwards state plus Choice/Score/Noul questions to Jev, directly or via OpenRouter.

**Why it is here:** Install script with checksum-verified releases, one-command registration for Claude Code/Desktop/Codex/pi, worked request example, 429/529 retry behavior, and `task check` running tests with -race.

**Know before you use it:** Thin pass-through to the API; its value is the packaging and client setup, not any logic beyond the official SDK.

<sub>MIT · Go</sub>

### [psearch](https://github.com/komikat/psearch)

CLI and MCP server that fetches pages in local Chromium and has Jev score page relevance and choose which links to follow in a breadth-first crawl.

**Why it is here:** uv tool install, concrete CLI examples with depth, budget and batch options, MCP config, documented statuses and exit codes, and offline tests using local browser fixtures.

**Know before you use it:** No measured latency or retrieval-quality numbers, and discovery depends on a rate-limited anonymous Parallel endpoint.

<sub>MIT · Python</sub>

- [tamaratran/fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction) **(notable)** - Claude Code plugin and npm library that compacts context by having Jev score each tool call and result, dropping stale ones and keeping the rest verbatim. <sub>MIT · TypeScript</sub>
- [compozy/yoshi](https://github.com/compozy/yoshi) **(notable)** - Local proxy for Claude Code and Codex that asks Jev which completed tool spans are still needed and replaces the rest with omission markers before forwarding. <sub>MIT · TypeScript</sub>
- [jomatsu/pi-jev-auto-mode](https://github.com/jomatsu/pi-jev-auto-mode) **(notable)** - Pi extension that gates bash, write and edit calls with deterministic rules first, then Jev judgment, failing closed; thresholds come from measured calibration. <sub>MIT · TypeScript</sub>
- [anpicasso/hermes-jev-approvals](https://github.com/anpicasso/hermes-jev-approvals) **(notable)** - Hermes Agent provider plugin that answers smart command approvals with one Jev Choice, benchmarked against a chat LLM on 156 real commands. <sub>MIT · Python</sub>
- [BorisLeMeec/jev](https://github.com/BorisLeMeec/jev) **(notable)** - Claude Code plugin and Go CLI that answers find/ask questions over a codebase with Jev and narrows large reads via a hook, with measured token savings. <sub>MIT · Go</sub>
- [zoidsh/tenet](https://github.com/zoidsh/tenet) **(notable)** - Go CLI that judges every commit against plain-language rules in .tenet/config.yml using Jev probabilities as pass/fail cutoffs, with timing and cost benchmarks. <sub>MIT · Go</sub>
- [adarshmishra07/jcm-router](https://github.com/adarshmishra07/jcm-router) **(notable)** - Local proxy between Claude Code and Anthropic that has Jev pick model and effort per message, routing subagents and guarding main-chat cache cost. <sub>MIT · TypeScript</sub>
- [TinyFrontier/wince](https://github.com/TinyFrontier/wince) **(notable)** - CLI that rates a diff green, yellow or red for review attention and suggests reviewers from path rules plus per-file Jev questions, measured on 60 MRs. <sub>MIT · Python</sub>
- [coldteadotai/abide](https://github.com/coldteadotai/abide) **(notable)** - Hook for Claude Code, Codex and OpenCode that checks every edit against your AGENTS.md rules with Jev, measured by replaying 93 real sessions. <sub>MIT · TypeScript</sub>
- [noplan-inc/limpet](https://github.com/noplan-inc/limpet) **(notable)** - Single-file Stop hook for coding agents that asks Jev one yes/no per plain-language rule and sends the agent back to work when a rule is violated. <sub>MIT · Python</sub>
- [aruniyer/jevcoder](https://github.com/aruniyer/jevcoder) **(notable)** - Pi extension where Jev picks the next tool or edit action each step while the chosen LLM fills arguments; compared on 10 SWE-bench Verified samples. <sub>no license · TypeScript</sub>
- [clownware/bouncer](https://github.com/clownware/bouncer) **(notable)** - Claude Code PreToolUse hook that classifies each tool call against a YAML policy into allow, ask or deny, observe-only by default with a calibration command. <sub>no license · JavaScript</sub>
- [ddfeyes/jev-mode](https://github.com/ddfeyes/jev-mode) **(notable)** - Dependency-free Python tool that moves a coding agent's bulk triage judgments to Jev; A/B on 1000 items showed 78 percent fewer tokens. <sub>MIT · Python</sub>
- [enriquejuncorichi-create/pi-jev-assist](https://github.com/enriquejuncorichi-create/pi-jev-assist) **(notable)** - Pi extension that reviews an agent's claims against recorded evidence, suggests skills, lists callers before a write and prunes context with Jev. <sub>no license · TypeScript</sub>
- [fstandhartinger/auto-model-router](https://github.com/fstandhartinger/auto-model-router) **(notable)** - LLM router that uses one Jev call to classify each turn, then picks the model with lowest expected cost given cache state, quota and measured success. <sub>MIT · Python</sub>
- [ibrahemid/git-jev-stage](https://github.com/ibrahemid/git-jev-stage) **(notable)** - Git subcommand that stages only the hunks matching a sentence, deciding include, exclude or mixed per hunk with Jev and applying one atomic patch. <sub>MIT · TypeScript</sub>
- [ilkerulusoy/pi-jev-compact](https://github.com/ilkerulusoy/pi-jev-compact) **(notable)** - Pi extension that compacts context by having Jev score each tool call and result, deleting unneeded ones and leaving the rest byte-identical. <sub>no license · TypeScript</sub>
- [islee23520/omo-jevlike-router](https://github.com/islee23520/omo-jevlike-router) **(notable)** - Local Jev-style skill router for OmO: frozen Qwen2.5-0.5B plus a small head trims the skill catalog to top-K per prompt, with held-out recall numbers. <sub>MIT · Python</sub>
- [maito1201/jev-harness](https://github.com/maito1201/jev-harness) **(notable)** - Claude Code, Codex and opencode hooks that use Jev to check scope on writes and send back hollow completion claims at Stop, plus a self-check CLI. <sub>no license · JavaScript</sub>
- [MNWinn/agent-switchboard](https://github.com/MNWinn/agent-switchboard) **(notable)** - Action gates and decision routing for agent harnesses with paired cost runs comparing Jev routing, deterministic checks and a GPT baseline. <sub>no license · JavaScript</sub>
- [QuentinDanblon/pi-fast-jev-compaction](https://github.com/QuentinDanblon/pi-fast-jev-compaction) **(notable)** - Pi extension that asks Jev which old tool calls and results are still needed and drops or truncates the rest, with replayed-session savings measured. <sub>no license · TypeScript</sub>
- [rashedInt32/jev-gates](https://github.com/rashedInt32/jev-gates) **(notable)** - Claude Code plugin with six Jev-judged hooks that escalate rule breaks, out-of-scope edits, unmet asks, unverified test claims and dishonest commit messages. <sub>MIT · JavaScript</sub>
- [sharziki/groundcheck](https://github.com/sharziki/groundcheck) **(notable)** - Python library that checks whether a RAG answer is supported by its source using Jev, with AUC, latency and cost measured on 1,600 labeled examples. <sub>no license · Python</sub>
- [suraj-phanindra/wellposed](https://github.com/suraj-phanindra/wellposed) **(notable)** - Linter for Jev requests that flags badly posed questions such as a Choice with no none-of-the-above option or a path missing from state. <sub>MIT · JavaScript</sub>
- [thehumanworks/jevgrep](https://github.com/thehumanworks/jevgrep) **(notable)** - Rust natural-language grep that asks Jev one question per line per file chunk in parallel and prints files, regions and lines with probabilities and cost. <sub>no license · Rust</sub>
- [whiletrueee/router](https://github.com/whiletrueee/router) **(notable)** - OpenAI-compatible LLM router where Jev scores each request on 8 dimensions and a plain-code policy picks the cheapest capable model. <sub>no license · JavaScript</sub>
- [notque/vexjoy-agent](https://github.com/notque/vexjoy-agent) - Coding-agent toolkit whose /d command uses one Jev call to pick the specialist agent, skill and pipeline for a plain-English request. <sub>MIT · Python · [live](https://vexjoy.com)</sub>
- [robbyczgw-cla/hermes-web-search-plus](https://github.com/robbyczgw-cla/hermes-web-search-plus) - Hermes web search and extraction plugin where optional Jev confirms news queries, scores extracted page bodies and fills missing language. <sub>MIT · Python · [live](https://websearchplus.xyz)</sub>
- [thruwire/foreman](https://github.com/thruwire/foreman) - Python asyncio supervisor that watches a Codex CLI worker and asks Jev nine Noul questions per observation to decide continue, verify, retry, stop or finish. <sub>MIT · Python</sub>
- [devagrawal09/jev-review](https://github.com/devagrawal09/jev-review) - Staged code-review pipeline that chains Noul, Choice and Score calls over a Git diff or whole codebase and shows findings in a local dashboard. <sub>MIT · TypeScript</sub>
- [kitze/skillbox](https://github.com/kitze/skillbox) - Self-hosted, versioned skills library for AI agents served over MCP with scoped clients and optional Jev-based skill recommendations. <sub>MIT · TypeScript</sub>
- [dbreunig/building-with-jev-skill](https://github.com/dbreunig/building-with-jev-skill) - Agent skill covering Jev question design, state structure, confidence thresholds and diagnosing weak questions, installable as a Claude Code plugin. <sub>no license</sub>
- [shiro-0x/hersona](https://github.com/shiro-0x/hersona) - Persona template library for agents with CLI and MCP server, plus an optional Jev-backed decide command that recommends reply, ask, search, tool or hold. <sub>MIT · Python · [live](https://shiro-0x.github.io/hersona/)</sub>
- [Dicklesworthstone/skillranker](https://github.com/Dicklesworthstone/skillranker) - Rust CLI that ranks agent skills for the next step from live session context using Jev, with Claude Code hooks, abstention, TUI and local feedback. <sub>no license · Rust</sub>
- [0xNatoshi/jev-codex-router](https://github.com/0xNatoshi/jev-codex-router) - Local server that classifies each Codex turn with Jev and routes it to a cheaper or stronger model with a matching reasoning effort. <sub>MIT · Python</sub>
- [shantanugoel/ask-jev-skill](https://github.com/shantanugoel/ask-jev-skill) - Hermes agent skill with a Python script that calls Jev for a typed Choice/Score/Noul tiebreaker and a disable switch. <sub>MIT · Python</sub>
- [IAmUnbounded/save-token-jev-clean](https://github.com/IAmUnbounded/save-token-jev-clean) - Jev-guided context compaction with adapters for Codex, OpenCode, Claude Code and raw Anthropic/OpenAI transcripts, keeping user and assistant text verbatim. <sub>MIT · TypeScript</sub>
- [nidhi-singh02/agent-router](https://github.com/nidhi-singh02/agent-router) - CLI that filters coding-agent subscriptions by quota rules, asks Jev to rank the rest and pick effort, then launches the agent in a Herdr pane. <sub>MIT · TypeScript</sub>
- [DevMortimer/pi-typesafe](https://github.com/DevMortimer/pi-typesafe) - Pi extension adding a batched typesafe_evaluate tool, a terminal playground and a shared typed Jev client and key store for other extensions. <sub>MIT · TypeScript</sub>
- [jon-devlapaz/jev-me](https://github.com/jon-devlapaz/jev-me) - Agent skill for Cursor that interviews you about a plan while Jev scores which questions matter and whether your answers settle them; logs kept locally. <sub>MIT · Python</sub>
- [blakestone-x/jev-mcp](https://github.com/blakestone-x/jev-mcp) - MCP server exposing typed classify, score, check, match and screen tools backed by Jev, with pinned install commands for Claude Code, Codex and Cursor. <sub>MIT · Python</sub>
- [benomahony/nouls](https://github.com/benomahony/nouls) - Semantic linter and language server that splits files into functions with tree-sitter and asks Jev yes/no rule questions per function. <sub>no license · Python · [live](https://benomahony.github.io/nouls/)</sub>
- [DECRUX9812/typesafe-skill-router](https://github.com/DECRUX9812/typesafe-skill-router) - Opt-in Hermes Agent plugin that asks Jev which installed skill fits a request and appends a one-line hint to the user message. <sub>MIT · Python</sub>
- [devagrawal09/jev-code](https://github.com/devagrawal09/jev-code) - CLI for coding agents that routes a request to one of four Jev workflows: find relevant code, check a diff, triage test failures or review comments. <sub>MIT · TypeScript</sub>
- [mejiasd3v/pi-jev-router](https://github.com/mejiasd3v/pi-jev-router) - Pi coding-agent extension where Jev picks the model and reasoning effort for a session from a configured list, then pins both. <sub>MIT · JavaScript</sub>
- [TheoOliveira/pi-jev](https://github.com/TheoOliveira/pi-jev) - Pi extension using Jev to activate only the tools a prompt needs, suggest skills, pick a model tier and retain tool history during compaction. <sub>MIT · TypeScript</sub>
- [GodsBoy/jev-agent-skill-router](https://github.com/GodsBoy/jev-agent-skill-router) - Python CLI and library that routes a request to one skill from a large catalogue via batched Jev Choice rounds, with a 72-request benchmark report. <sub>MIT · Python</sub>
- [huntedman/JevLint](https://github.com/huntedman/JevLint) - CLI linter that sends source files and plain-English conventions to Jev and reports a per-file violation probability, with a magic-strings plugin. <sub>MIT · TypeScript · [live](https://jevlint.com)</sub>
- [Kevthetech143/super-jev](https://github.com/Kevthetech143/super-jev) - Zero-dependency TypeScript harness looping evidence, Jev judgments, permitted tool actions and verification, with JSONL traces and replay. <sub>MIT · TypeScript</sub>
- [lakeday-org/perch](https://github.com/lakeday-org/perch) - CLI that scans code per method for semantic defects with Jev, supports custom plain-language rules in perch.yaml and installs agent skills. <sub>MIT · JavaScript · [live](https://perchscan.com)</sub>
- [sharziki/semdecide](https://github.com/sharziki/semdecide) - Unix CLI that pipes text or JSONL through Jev to get predicates, routes and scores with thresholds, JSON output and stable exit codes for scripts and CI. <sub>MIT · Python</sub>
- [theyashwanthsai/jevals](https://github.com/theyashwanthsai/jevals) - Python eval framework that grades saved LLM outputs or agent traces against score and noul checks answered by Jev, with a confidence per result. <sub>MIT · Python</sub>
- [3clyp50/a0-typesafe-ai](https://github.com/3clyp50/a0-typesafe-ai) - Agent Zero plugin adding a typesafe_query tool that sends mixed Choice, Noul and Score questions to Jev and renders probability cards in chat. <sub>MIT · Python</sub>
- [BillionsBobby/JevRouter](https://github.com/BillionsBobby/JevRouter) - Router that merges models, subagents, skills, MCP tools and CLIs into one Jev Choice, then applies permission and risk policy; has a Toolathlon comparison. <sub>MIT · TypeScript</sub>
- [DanRWilloughby/snifftest](https://github.com/DanRWilloughby/snifftest) - Prose linter CLI that runs local regex rules for AI-writing tells and, after consent, sends paragraphs to Jev for judgment rules with a no-judgment band. <sub>MIT · TypeScript</sub>
- [Eriskii/ErisLint](https://github.com/Eriskii/ErisLint) - Rust linter driven by JSON rules that ask Jev questions about functions and map answers to warnings or errors, with a VS Code extension. <sub>AGPL-3.0 · Rust</sub>
- [harrymunro/beadsort](https://github.com/harrymunro/beadsort) - CLI and agent skill that labels every issue in a beads backlog with Jev judgments, dry run first, then writes the labels back. <sub>MIT · Python</sub>
- [y0usaf/typesafe-cli](https://github.com/y0usaf/typesafe-cli) - Shell command `jev` with noul, choice, score and batched ask subcommands that read state from flags, files or stdin and print numeric answers. <sub>MIT · TypeScript</sub>
- [arunav25/jev-mcp](https://github.com/arunav25/jev-mcp) - MCP server exposing one evaluate tool for Jev plus a harness that compares Jev with an LLM on shared datasets using Brier, calibration and McNemar. <sub>MIT · JavaScript</sub>
- [baronunread/leanest](https://github.com/baronunread/leanest) - Bun CLI that asks Jev whether a git diff could affect each Playwright or Vitest test file and runs only the rest, failing open to the full suite. <sub>MIT · TypeScript · [live](https://leanest.pages.dev/)</sub>
- [Brainwires/jevwire](https://github.com/Brainwires/jevwire) - Six MCP tools, an embeddable decision library and a Claude Code hook plugin that places Jev judgments before tool calls, after fetches and at turn end. <sub>MIT · TypeScript</sub>
- [geilt/typesafe-cli](https://github.com/geilt/typesafe-cli) - Stdlib-only Python CLI with ask, models and smoke commands plus an installable agent skill for sending typed questions to Jev. <sub>no license · Python</sub>
- [HyunjunJeon/pi-quiet-ask](https://github.com/HyunjunJeon/pi-quiet-ask) - pi coding-agent extension with a JSON rule engine that asks Jev to gate tool calls, flag leaked secrets, triage ask_user questions and check claimed completion. <sub>MIT · TypeScript</sub>
- [jvsteiner/jevex](https://github.com/jvsteiner/jevex) - Experimental agent loop where Jev picks and approves each MCP tool call while an LLM only fills arguments and prose, with a token and latency benchmark. <sub>MIT · Python</sub>
- [keeltrace/hermes-jev](https://github.com/keeltrace/hermes-jev) - Hermes Agent plugin adding decide, rank, verify and assess tools, an optional pre-tool-call gate and a Jev-driven context curation engine. <sub>MIT · Python</sub>
- [AbdelStark/bicameral](https://github.com/AbdelStark/bicameral) - Pi coding-agent harness where Jev scores tool-call safety, test weakening and looping, and YAML policy maps scores to allow, confirm, block, warn or steer. <sub>MIT · TypeScript</sub>
- [abhixhek/jevcal](https://github.com/abhixhek/jevcal) - Python CLI that calibrates Jev against an LLM teacher on your data, picks per-question confidence thresholds for an accuracy target and fails CI on drift. <sub>MIT · Python</sub>
- [andrueandersoncs/jev-semantic-linter](https://github.com/andrueandersoncs/jev-semantic-linter) - Bun CLI that checks Markdown-defined engineering rules against the current git change using Choice routing over hunks and Noul rule judgments. <sub>no license · TypeScript</sub>
- [ayushgml/greenwash-oss](https://github.com/ayushgml/greenwash-oss) - GitHub App that asks Jev yes/no questions about each changed PR hunk to flag weakened assertions, skipped tests, hard-coded answers and disabled CI steps. <sub>Apache-2.0 · Python</sub>
- [BeLazy167/typesafe-mod](https://github.com/BeLazy167/typesafe-mod) - Claude Code function hook that sends the agent's this-or-that questions and per-prompt skill ranking to Jev, answering itself only above a confidence floor. <sub>MIT · TypeScript</sub>
- [caiovicentino/jev-shield](https://github.com/caiovicentino/jev-shield) - Stdio MCP proxy that screens tool calls, results and tool descriptions with Jev, layering allowlists and taint tracking, with a bundled attack demo. <sub>MIT · JavaScript</sub>
- [FirasSX914/Janus](https://github.com/FirasSX914/Janus) - CLI that measures on your labelled data or logs where Jev's confidence justifies falling back to a larger model, then routes by that measured threshold. <sub>MIT · Python</sub>
- [HyunjunJeon/jev-judgment](https://github.com/HyunjunJeon/jev-judgment) - Agent Skill with a stdlib Python script that asks Jev before closed user questions, before risky commands and after failures, redacting secrets and failing open. <sub>MIT · Python</sub>
- [iamvatsalpatel/tiershift](https://github.com/iamvatsalpatel/tiershift) - LLM router that starts every prompt on the cheapest tier and escalates on Jev signals per a YAML policy, with a 120-prompt blind-judged cost comparison. <sub>MIT · TypeScript</sub>
- [iJ03l/jear](https://github.com/iJ03l/jear) - Rust CLI that routes requests across NEAR AI Cloud models and IronClaw agents by budget, quality and sensitivity using Jev answers, with 60 offline tests. <sub>Apache-2.0 · Rust</sub>
- [jerryfane/omp-jev-compaction](https://github.com/jerryfane/omp-jev-compaction) - omp extension that has Jev score tool calls and truncates stale results verbatim, remembering decisions so the prompt-cache prefix is rarely rewritten. <sub>MIT · TypeScript</sub>
- [jodan-alberts/sokit](https://github.com/jodan-alberts/sokit) - Stdlib-only Python agent harness around System One models adding a tool registry, data providers, confidence gates, memory and a labelled-eval loop. <sub>MIT · Python</sub>
- [joelhooks/pi-fast-jev-compaction](https://github.com/joelhooks/pi-fast-jev-compaction) - Pi extension that asks Jev two noul questions per tool call to keep, truncate or drop stale tool history while leaving conversation text verbatim. <sub>MIT · TypeScript</sub>
- [keltokhy/jgrep](https://github.com/keltokhy/jgrep) - grep-style CLI that matches lines, paragraphs or files against a plain-language description via one Jev yes/no question each, streaming from pipes. <sub>MIT · Python</sub>
- [leepokai/jev-guard](https://github.com/leepokai/jev-guard) - npm hook for Claude Code, Codex, Cursor and other agents that asks Jev three typed questions per tool call to deny, ask or allow, and flags injected results. <sub>MIT · JavaScript</sub>
- [leonaaardob/fast-dev-compaction](https://github.com/leonaaardob/fast-dev-compaction) - Codex plugin port of fast-jev-compaction that has Jev decide which tool calls to keep verbatim and re-injects them after Codex compacts. <sub>MIT · TypeScript</sub>
- [lomeshdutta/skill-router](https://github.com/lomeshdutta/skill-router) - CLI for Claude Code that ranks installed skills against the session goal with Jev and points to skills.sh search when none fits. <sub>MIT · Python</sub>
- [maker-KK/todo-jev](https://github.com/maker-KK/todo-jev) - Python CLI that classifies a request with Jev against 20 skill profiles and local environment checks to recommend a rule, skill or foundation-model route. <sub>MIT · Python</sub>
- [molis-ai/jev-workbench](https://github.com/molis-ai/jev-workbench) - Local service for defining, previewing and publishing versioned Jev judgment functions callable over HTTP and MCP with scoped client tokens. <sub>MIT · TypeScript</sub>
- [MongLong0214/jev-gate](https://github.com/MongLong0214/jev-gate) - Experimental Claude Code setup where Jev decides per delegated task which Claude tier does the work, with a candid account of what is unverified. <sub>no license · TypeScript</sub>
- [noelzappy/tripwire](https://github.com/noelzappy/tripwire) - AI SDK middleware and OpenAI-compatible proxy that runs seven Jev checks on each LLM response under a YAML policy, with a decision log and eval CLI. <sub>MIT · TypeScript</sub>
- [Nyarlathoteppppp/pi-heed](https://github.com/Nyarlathoteppppp/pi-heed) - pi extension that extracts constraints from what the user said (English or Chinese) and has Jev check each side-effecting tool call against them first. <sub>MIT · TypeScript</sub>
- [ocportal-dev/oc-permissions-classifier](https://github.com/ocportal-dev/oc-permissions-classifier) - OpenCode v2 plugin that sends permission requests resolving to ask to an LLM or Jev reviewer, fails closed on errors and writes an audit log. <sub>MIT · TypeScript</sub>
- [opaielsheikh/typesafe-migration-guard](https://github.com/opaielsheikh/typesafe-migration-guard) - CI gate API that asks Jev to classify SQL migration statements as safe or dangerous and returns 403 before destructive DDL reaches Supabase Postgres. <sub>no license · TypeScript</sub>
- [rashedInt32/jev-mcp](https://github.com/rashedInt32/jev-mcp) - MCP server and Claude Code plugin exposing classify, score, check and batched ask tools, reading the key from env or a file, never a tool argument. <sub>MIT · TypeScript</sub>
- [scale-venture-partners/riff](https://github.com/scale-venture-partners/riff) - Prose linter CLI with ruff-style rule codes, mixing static Python rules with semantic rules each answered by one Jev call and reported with probabilities. <sub>MIT · Python</sub>
- [ShivamPansuriya/jev-skill-gate](https://github.com/ShivamPansuriya/jev-skill-gate) - Scores installed Claude Code skills against the current project with Jev and writes skillOverrides to hide irrelevant ones, with a committed labelled eval. <sub>MIT · JavaScript</sub>
- [sufianetaouil/every](https://github.com/sufianetaouil/every) - CLI that asks one yes/no question of every function in a codebase and ranks them by Jev probability, with caching and a self-test. <sub>MIT · Python</sub>
- [thejorgg/omp-jev](https://github.com/thejorgg/omp-jev) - Oh My Pi plugin adding Jev-based routing and an opt-in checkpoint orchestrator, with editable XDG config and a validating CLI. <sub>no license · TypeScript</sub>
- [tumf/jev-cli](https://github.com/tumf/jev-cli) - PyPI-installable CLI and stdio MCP server for noul, choice and score questions with JSON output, exit codes and official, Vercel or OpenRouter providers. <sub>MIT · Python</sub>
- [0xdesign/design-gate](https://github.com/0xdesign/design-gate) - CLI approval loop for coding agents that renders the app, runs measured design checks plus Jev design questions and returns a ranked fix list. <sub>MIT · TypeScript</sub>
- [aegsrl7/jevmap](https://github.com/aegsrl7/jevmap) - Zero-dependency Node CLI that maps a codebase into units and has Jev rank the files relevant to a task, benchmarked against 32 real commits. <sub>MIT · JavaScript</sub>
- [altryne/jevify](https://github.com/altryne/jevify) - Agent skill, installed via npx skills, that finds where Jev fits in a codebase or idea and drafts typed question packs from docs and community examples. <sub>MIT · Python</sub>
- [ari-becker/commentlint](https://github.com/ari-becker/commentlint) - Rust linter that extracts code comments with tree-sitter and fails those that miss Jev yes/no rules such as active voice, configurable per directory. <sub>MIT · Rust</sub>
- [bestagentkits/jev-skillful](https://github.com/bestagentkits/jev-skillful) - Prompt hook for Claude Code, Codex and Pi that shortlists installed skills and MCP servers with BM25 and uses one Jev call to inject at most one suggestion. <sub>MIT · TypeScript</sub>
- [buchmark/claude-jev](https://github.com/buchmark/claude-jev) - Claude Code plugin with five MCP tools that score review findings, debug hypotheses, design options and grep hits with Jev. <sub>MIT · TypeScript</sub>
- [BunsDev/typesafe-router](https://github.com/BunsDev/typesafe-router) - TypeScript router library and Next.js demo that asks Jev one choice question over allowed tools or models, then applies confidence and fallback policy. <sub>no license · TypeScript · [live](https://typesafe-router.vercel.app)</sub>
- [burnigtm/jev-mcp](https://github.com/burnigtm/jev-mcp) - Stdio MCP server for Cursor and Codex with patch review, claim verification, content screening and ranking tools returning auto/review/escalate. <sub>MIT · TypeScript</sub>
- [BYK/jev-mcp](https://github.com/BYK/jev-mcp) - MCP server with jev_ask, jev_map for bulk triage and jev_eval for measuring question variants and threshold sweeps on labelled examples. <sub>MIT · TypeScript</sub>
- [carlsonchik/judging-with-typesafe](https://github.com/carlsonchik/judging-with-typesafe) - Letta agent skill with a Jev wrapper script, a paragraph-level document scanner and tested rules for reading uncertain scores. <sub>no license · Python</sub>
- [CryptoOda/typesafe-guard](https://github.com/CryptoOda/typesafe-guard) - Python guardrail library and ASGI middleware checking prompt injection, jailbreak, PII and secrets in one Jev request, with a 50-sample benchmark. <sub>MIT · Python</sub>
- [DanielKillenberger/jev-predict-skill](https://github.com/DanielKillenberger/jev-predict-skill) - Agent skill that extracts another skill's closed outcome set and asks Jev which verdict it would reach, without running that skill. <sub>no license · HTML</sub>
- [drevantonder/jevlint](https://github.com/drevantonder/jevlint) - JS/TS linter where Oxc finds candidates and Jev scores each rule as a probability; review/audit modes, JSON and GitHub annotation output, cached judgments. <sub>MIT · TypeScript</sub>
- [drevantonder/rangerjev](https://github.com/drevantonder/rangerjev) - CLI that splits a codebase by file, function or call tree and asks Jev typed questions per unit, with dry-run cost preview and an agent skill. <sub>MIT · TypeScript</sub>
- [Ezbaze/jevies](https://github.com/Ezbaze/jevies) - Python helpers that use Jev to review Jev setups: question type, instruction wording, option overlap, score rubric order and test coverage. <sub>MIT · Python</sub>
- [fatwang2/jev-review-action](https://github.com/fatwang2/jev-review-action) - GitHub Action that reviews catalog submissions or classifies pull requests against a JSON policy using only Jev and a fixed comment template. <sub>MIT · JavaScript</sub>
- [felpsdev/jev-classifier](https://github.com/felpsdev/jev-classifier) - Local gateway and MCP tool that has Jev suggest or choose the next tool for Codex, Claude Code, OpenCode and Cursor, logging every decision. <sub>MIT · TypeScript</sub>
- [gmaxxxie/jev-cli](https://github.com/gmaxxxie/jev-cli) - Stdlib Python CLI for Jev via the OpenRouter Decisions API, plus two pi coding-agent extensions for decisions and candidate triage. <sub>MIT · TypeScript</sub>
- [greenyamao/Antigravity-mcp-semantic-search-with-TypeSafeAi](https://github.com/greenyamao/Antigravity-mcp-semantic-search-with-TypeSafeAi) - Python MCP server with a two-stage Jev code locator returning 15-line snippets and a diff auditor flagging removed guards and debug leftovers. <sub>MIT · Python</sub>
- [harrymunro/decision-first](https://github.com/harrymunro/decision-first) - Agent skill that spots bounded-judgment steps, tries Jev before regex or LLM prompts, and logs each attempt in a reusable decision-lab directory. <sub>MIT · Python</sub>
- [hemanth/tool-prune](https://github.com/hemanth/tool-prune) - JS and Python library that prunes agent tool schemas to relevant candidates using offline vector search or Jev, with a direct-dispatch fast path. <sub>MIT · JavaScript · [live](https://hemanth.github.io/tool-prune/)</sub>
- [hl/jen](https://github.com/hl/jen) - Go CLI that checks a git diff or files against a plan document with typed Jev questions in one request and can gate on a verdict. <sub>no license · Go</sub>
- [Indosaram/typesafe-judge](https://github.com/Indosaram/typesafe-judge) - Rust CLI and agent skill for choice/score/noul calls and a git diff gate with exit codes, printing the raw API JSON. <sub>no license · Rust</sub>
- [jtsang4/jev-cli](https://github.com/jtsang4/jev-cli) - CLI that takes a state and typed questions and prints JSON answers, with config, doctor check and optional Vercel AI Gateway routing. <sub>MIT · TypeScript</sub>
- [lhemerly/mcts-agent](https://github.com/lhemerly/mcts-agent) - MCTS coding agent where Gemini proposes actions and Jev prunes (Noul), sets priors (Choice) and values states (Score), with a D3 tree visualizer. <sub>MIT · Python</sub>
- [luantak/is-malicious](https://github.com/luantak/is-malicious) - CLI that sends a codebase's source, build and CI files to Jev and reports suspicious files and line ranges with probabilities; diff-only scans, CI exit codes. <sub>MIT · TypeScript</sub>
- [Nasrallah-AL/jev-cli](https://github.com/Nasrallah-AL/jev-cli) - npm CLI (jevctl) with verify, screen, classify, extract, find, rerank, match and route commands, JSON output and exit codes for CI gating. <sub>MIT · TypeScript · [live](https://jevcli.vectorz.app/)</sub>
- [NicolasMontone/jev-tool-permissions](https://github.com/NicolasMontone/jev-tool-permissions) - Vercel AI SDK layer that uses Jev to approve, escalate or block each tool call and to prune irrelevant tool definitions, fail-closed over deterministic rules. <sub>no license · TypeScript</sub>
- [NieXi/agent-guard](https://github.com/NieXi/agent-guard) - Claude Code PreToolUse hook on PyPI that scores destructive risk and policy violation of each tool call and returns allow, ask or deny, failing closed. <sub>MIT · Python</sub>
- [ntedvs/commentcop](https://github.com/ntedvs/commentcop) - CLI that scores JS/TS code comments for accuracy and usefulness against the surrounding code and lists the weakest first, with a cost estimate. <sub>MIT · TypeScript</sub>
- [omni-/ask-jev](https://github.com/omni-/ask-jev) - PowerShell UserPromptSubmit hook for Codex that audits the recorded conversation or answers a typed yes/no question about it via a :jev command. <sub>MIT · PowerShell</sub>
- [paulobueno164/jev-mcts](https://github.com/paulobueno164/jev-mcts) - MCTS/PUCT planner for agent workflows using Jev for priors and value; irreversible steps need a human and milestones are granted only on probe exit codes. <sub>no license · TypeScript</sub>
- [poponline63/hermes-jev-north-star](https://github.com/poponline63/hermes-jev-north-star) - Hermes Agent skill that turns a goal into a checkable finish line; shell commands gate the verifiable parts and Jev judges the fuzzy requirements. <sub>MIT · Python</sub>
- [prismhq/jev-router](https://github.com/prismhq/jev-router) - LiteLLM proxy hook exposing one OpenAI-compatible model id where Jev picks the serving model from capability-filtered candidates in router.yaml. <sub>MIT · Python</sub>
- [qkal/Canny](https://github.com/qkal/Canny) - Claude Code and Codex hook that keeps a ledger of agent actions and refuses 'done' without a passing check; Jev only advises on claims and rule violations. <sub>MIT · TypeScript</sub>
- [Ravinder82/jev-flash-router](https://github.com/Ravinder82/jev-flash-router) - MCP server exposing one evaluate_decision tool (noul, choice or score) that calls Jev through OpenRouter's Decisions API for coding agents. <sub>MIT · TypeScript</sub>
- [redrossa/pi-model-router](https://github.com/redrossa/pi-model-router) - Pi extension that classifies each prompt with a Jev Choice over user-defined categories and switches to the first matching logged-in model for that run. <sub>MIT · TypeScript</sub>
- [rhighs/jev-code](https://github.com/rhighs/jev-code) - Interactive coding CLI that builds Python, Bash and TypeScript source through constrained AST choices made by Jev, then runs tools with permission prompts. <sub>no license · TypeScript</sub>
- [siddicky/omp-typesafe](https://github.com/siddicky/omp-typesafe) - Extension for the omp coding agent that adversarially reviews tool results and messages with Jev batteries plus git-grep evidence, and adds a typesafe_ask tool. <sub>MIT · TypeScript</sub>
- [simota/tenbin](https://github.com/simota/tenbin) - MCP server and agent skill to decompose a judgment into Choice/Score/Noul questions, lint them, evaluate on labelled rows, rerank and walk taxonomies. <sub>MIT · TypeScript</sub>
- [StefanoITA/ts-jev-cost-calculator](https://github.com/StefanoITA/ts-jev-cost-calculator) - Offline CLI and Python function that estimate tokens, USD cost and context fit of a System One request before sending, and read real cost from a response. <sub>MIT · Python</sub>
- [TheBous/jev-flash-review](https://github.com/TheBous/jev-flash-review) - Local MCP review engine plus three agent skills that evaluate a diff against rules.json as Choice questions, locate evidence hunks and confirm violations. <sub>no license · TypeScript</sub>
- [thesammykins/jev_ampcode](https://github.com/thesammykins/jev_ampcode) - Amp directory plugin that gives the agent an advisory tool for comparing supplied alternatives against supplied evidence, with secret handling rules. <sub>no license · TypeScript</sub>
- [thrashr888/clue](https://github.com/thrashr888/clue) - Rust CLI that normalizes JSON/JSONL from gh, bd, Cider or SQLite, ranks records against a query with TypeSafe, and assembles byte-budgeted context bundles. <sub>MIT · Rust</sub>
- [Timileyin-Agbaje/Nem](https://github.com/Timileyin-Agbaje/Nem) - Fail-closed Node/TypeScript guardrail CLI that evaluates a proposed agent action with Jev Nouls and returns ALLOW, REVIEW or BLOCK without executing it. <sub>no license · TypeScript</sub>
- [tonyzdev/PiJ](https://github.com/tonyzdev/PiJ) - Terminal coding agent built on Pi that uses Jev to shortlist skills, rank searched code excerpts and classify tool failures, all advisory. <sub>MIT · TypeScript</sub>
- [waddle-zoo/signal-weave](https://github.com/waddle-zoo/signal-weave) - MCP and webhook service that checks whether a moved dashboard or query signal matters, using adapter evidence and Jev typed judgments; Superset demo stack. <sub>Apache-2.0 · Python</sub>
- [Wang-auspicious/codex-jev-compaction](https://github.com/Wang-auspicious/codex-jev-compaction) - Codex plugin (skill, stdio MCP tool, CLI) that asks Jev which old read-only tool pairs to keep and builds a verbatim handoff packet. <sub>MIT · JavaScript</sub>
- [Wang-auspicious/pi-jev-compaction](https://github.com/Wang-auspicious/pi-jev-compaction) - Pi extension that hooks compaction, has Jev judge old read-only tool pairs and returns an extractive transcript instead of a written summary. <sub>MIT · TypeScript</sub>
- [zbush/jev-context](https://github.com/zbush/jev-context) - Codex plugin that runs ripgrep, has Jev keep only relevant passages, and logs paired filtered/unfiltered payloads so token savings can be reproduced. <sub>MIT · JavaScript</sub>
- [019ec6e2/pi-jev-compact](https://github.com/019ec6e2/pi-jev-compact) - Pi extension port of fast-jev-compaction: Jev scores every past tool call in one request, stale ones are dropped or truncated, kept text stays verbatim. <sub>no license · TypeScript</sub>
- [0451-software/ts-semantic-lint](https://github.com/0451-software/ts-semantic-lint) - Configurable TypeScript linter where Jev judges code meaning (swallowed errors, misleading names) and user rules map judgments to warnings or errors. <sub>MIT · TypeScript</sub>
- [0xArx/jevegis](https://github.com/0xArx/jevegis) - Hosted guardrail API that scans LLM input, output and documents for injection, jailbreaks, leaks and unsafe content in one Jev request; 42-case eval. <sub>MIT · TypeScript · [live](https://jevegis.vercel.app)</sub>
- [24601/Augustus](https://github.com/24601/Augustus) - Agent skill for designing Jev-backed systems: mappings from classical decision methods, validation gates, a boundary audit and an offline Brier evaluator. <sub>MIT · Python</sub>
- [24601/rh-guard](https://github.com/24601/rh-guard) - Claude Code and Cursor hook server that blocks reward-hacking tool use such as tampering with tests or graders, using structural denies plus Jev scoring. <sub>no license · TypeScript</sub>
- [aaravriyer193/OpenSmoke](https://github.com/aaravriyer193/OpenSmoke) - Trace scanner that asks Jev three questions per agent step to find runs broken by missing keys, tools or files, then groups them into incidents. <sub>MIT · Python</sub>
- [aaronshaf/opencode-jev-model-router](https://github.com/aaronshaf/opencode-jev-model-router) - OpenCode plugin on npm where Jev picks a fast, balanced, strong or long tier each turn and the plugin switches to the first eligible model in that tier. <sub>MIT · TypeScript</sub>
- [AC40/autolsp](https://github.com/AC40/autolsp) - VS Code extension that has Jev rank completions from installed language servers and shows the top one as ghost text or auto-inserts it after a pause. <sub>MIT · TypeScript</sub>
- [AkashPriyadarshii/jev-scout](https://github.com/AkashPriyadarshii/jev-scout) - Rust CLI and MCP server that fetches real candidates from GitHub and crates.io, then has Jev score fit, license and maintenance for a query. <sub>MIT · Rust</sub>
- [AlexBabescu/ActionJev](https://github.com/AlexBabescu/ActionJev) - GitHub and Gitea Action shipping static Rust binaries that asks Jev structured review questions about PR changes and posts a summary comment with reports. <sub>Apache-2.0 · Python</sub>
- [alexshpunt/pi-agent-foreman](https://github.com/alexshpunt/pi-agent-foreman) - Pi extension that reviews the final exchange of a run and sends the agent back to work if it stopped early, with TypeSafe as an optional judge. <sub>MIT · TypeScript</sub>
- [alexykn/jevscan](https://github.com/alexykn/jevscan) - Code-quality scanner that extracts functions and classes with tree-sitter and has Jev evaluate YAML rules over them for Python, Rust, Perl, TS and JS. <sub>MIT · Python</sub>
- [ali-abassi/pi-jev](https://github.com/ali-abassi/pi-jev) - Pi coding-agent extension that asks a five-question ballot each turn for goal drift, looping, goal conflict and unsafe actions, then steers or notifies. <sub>MIT · Shell</sub>
- [All-Light/reflex-arc](https://github.com/All-Light/reflex-arc) - Python library where Jev triages incoming events to stored reflexes and a reasoning LLM handles novel ones and writes a new reflex, with shadow-mode promotion. <sub>MIT · Python</sub>
- [aniruddh-krovvidi/switchboard](https://github.com/aniruddh-krovvidi/switchboard) - OpenAI-compatible gateway that screens each request for injection, harm and PII and routes to a small or large backend, plus a calibration eval script. <sub>no license · Python</sub>
- [annenpolka/qlint](https://github.com/annenpolka/qlint) - Linter for suites of natural-language judgment questions: checks references, leakage, gates and bindings, builds execution plans and replays recorded runs. <sub>MIT · TypeScript</sub>
- [aoprisan/jev-ts-repl](https://github.com/aoprisan/jev-ts-repl) - Terminal REPL for drafting System One requests with typed questions, a lesson track, cost preview, and export of the session as TypeScript or Rust. <sub>MIT · TypeScript</sub>
- [ArkadyBuryakov/jev-preview](https://github.com/ArkadyBuryakov/jev-preview) - Textual TUI sandbox for the System One API: edit state, build questions in a form, view answers as probability bars, keep per-request history. <sub>MIT · Python</sub>
- [aserjam100/jev-firewall](https://github.com/aserjam100/jev-firewall) - Small JavaScript coding agent where Jev routes each step to list, search, read, test or stop and only calls OpenAI for generation or low confidence. <sub>no license · JavaScript</sub>
- [AshutoshVJTI/progressgate](https://github.com/AshutoshVJTI/progressgate) - npm library that watches recent agent steps for repeated contradicted assumptions using six Jev signals and returns CONTINUE, WARN, REPLAN or HALT. <sub>MIT · TypeScript</sub>
- [bmccarn/tracecheck](https://github.com/bmccarn/tracecheck) - Local MCP server and CLI that checks a coding agent's defect hypotheses against quoted source evidence and scores 19 quality dimensions separately. <sub>MIT · TypeScript</sub>
- [caiovicentino/jev-align](https://github.com/caiovicentino/jev-align) - CLI and MCP server that checks an LLM response or agent plan for sycophancy, deception, scope creep and irreversibility, with 12 labeled test fixtures. <sub>MIT · JavaScript</sub>
- [Calq-dev/ask-jev](https://github.com/Calq-dev/ask-jev) - Claude Code plugin with tools to ask yes/no questions about a file, filter many files by a question, or find the answering line without reading it. <sub>no license · JavaScript</sub>
- [cbruyndoncx/AskJev-MCP](https://github.com/cbruyndoncx/AskJev-MCP) - MCP server built on the official JS SDK with ask_choice, ask_noul, ask_score, a batched ask and list_models tools. <sub>no license · JavaScript</sub>
- [chapel/hermes-jev-skills](https://github.com/chapel/hermes-jev-skills) - Hermes plugin adding a search_skills tool and turn-start skill suggestions by asking one Noul per skill description. <sub>no license · Python</sub>
- [christian-taillon/opencode-jev-compactor](https://github.com/christian-taillon/opencode-jev-compactor) - OpenCode v2 compaction-hook plugin that asks narrow questions per tool item to keep, truncate or drop it and builds a checkpoint from verbatim evidence. <sub>MIT · TypeScript</sub>
- [chungsubeen0/jevmcp](https://github.com/chungsubeen0/jevmcp) - Local MCP server for Codex and Claude Code that offloads routine yes/no judgments to Jev with validation, policy profiles, cache and telemetry. <sub>MIT · Python</sub>
- [clankagent/pi-jev](https://github.com/clankagent/pi-jev) - Two Pi extensions: a jev_watch tool that returns when process output meets agent-described conditions, and per-request skill suggestions. <sub>Unlicense · TypeScript</sub>
- [ClemensSchartmueller/jev-guard](https://github.com/ClemensSchartmueller/jev-guard) - Go hook for Claude Code, Codex CLI and Antigravity that checks paths and secrets locally, then asks Jev about blast radius before a tool call runs. <sub>MIT · Go</sub>
- [conraddavisjr/ai-evals-cafe](https://github.com/conraddavisjr/ai-evals-cafe) - Eval harness for multi-agent pipelines shown as a 3D cafe, with scoped MCP tools, scripted scenarios and a blinded judge that can run on Jev or an LLM. <sub>no license · TypeScript</sub>
- [cpaczek/s1s](https://github.com/cpaczek/s1s) - CLI and local server that finds files, maps a subject and traces flows in a Git repo using a lexical index for recall and typed judgments for precision. <sub>MIT · TypeScript · [live](https://s1s.iar.dev)</sub>
- [dakdevs/decide-mcp](https://github.com/dakdevs/decide-mcp) - Stdio MCP server on npm whose decide tool returns a recommended choice with percentages via AI Gateway, with configurable bias profiles and routing. <sub>MIT · TypeScript</sub>
- [DanBennettUK/hermes-jev-compaction](https://github.com/DanBennettUK/hermes-jev-compaction) - Hermes Agent context-engine plugin that keeps, truncates or drops old tool calls from two probabilities each while leaving user and assistant text verbatim. <sub>MIT · Python</sub>
- [danielgshea/jev-graph](https://github.com/danielgshea/jev-graph) - LangGraph analyst agent where Jev classifies requests, approves tool calls, scores search results and grades the final answer. <sub>no license · Python</sub>
- [davidrydberg/git-judge](https://github.com/davidrydberg/git-judge) - GitHub Action that judges every PR hunk and posts one comment with what to read first, skipped hunks, undescribed changes and secret or data-loss gates. <sub>MIT · TypeScript</sub>
- [dayhaysoos/jevals](https://github.com/dayhaysoos/jevals) - Local workbench started with npx for writing Noul, Choice and Score evaluations with expected answers, running them and comparing saved runs in SQLite. <sub>MIT · TypeScript</sub>
- [devinat1/system-one-router](https://github.com/devinat1/system-one-router) - pi-coding-agent extension on npm, based on pi-model-router, that uses Jev as the classifier picking a high, medium or low model tier each turn. <sub>MIT · TypeScript</sub>
- [doeixd/jev-pref](https://github.com/doeixd/jev-pref) - npx linter that turns AGENTS.md preferences into semantic rules, checks diff hunks with Jev and reports findings back to the coding agent. <sub>MIT · JavaScript</sub>
- [DoGMaTiiC/hermes-jev](https://github.com/DoGMaTiiC/hermes-jev) - Two stdlib-only Hermes Agent plugins: a pre-tool risk gate and a per-turn skill router, both calling Jev through the Vercel AI Gateway. <sub>no license · Python</sub>
- [dpaluy/jev-compact](https://github.com/dpaluy/jev-compact) - Context-pruning plugin for the Pi harness that scores tool-call traces with two Noul questions and drops only pairs below threshold, keeping the rest verbatim. <sub>no license · TypeScript</sub>
- [droid-Q/jev-skill-router](https://github.com/droid-Q/jev-skill-router) - Codex CLI plugin whose UserPromptSubmit hook asks Jev which installed skills are relevant to the prompt and selects up to N above a threshold. <sub>no license · JavaScript</sub>
- [dryob/hermes-jev-context-engine](https://github.com/dryob/hermes-jev-context-engine) - Hermes Agent context engine, ported from fast-jev-compaction, that keeps, truncates or drops old tool calls by Jev score instead of summarising. <sub>no license · Python</sub>
- [dsandrade/jevra](https://github.com/dsandrade/jevra) - Alpha plugin for Codex and Claude Code whose PreToolUse hook redirects large file reads to a helper where Jev selects the source excerpts. <sub>MIT · TypeScript</sub>
- [dtjohnson83/rag-gate](https://github.com/dtjohnson83/rag-gate) - Small HTTP API that scores already-retrieved RAG chunks for relevance and prompt injection with Jev and returns kept and dropped lists. <sub>MIT · TypeScript</sub>
- [dtsuka/jev-review](https://github.com/dtsuka/jev-review) - CLI that screens every source file for bug, security, performance and other review flags with Jev and writes a JSON triage report. <sub>no license · TypeScript</sub>
- [Ducstii/pi-advisor](https://github.com/Ducstii/pi-advisor) - pi coding-agent extension adding a jev_advise tool that batches choice, score and yes/no questions and flags near-ties for the user. <sub>MIT · TypeScript</sub>
- [duketopceo/jev-compact](https://github.com/duketopceo/jev-compact) - Python transcript compactor for Claude Code that scores spans with Jev, keeps top spans verbatim, tombstones the rest, and restores them via an MCP server. <sub>MIT · Python</sub>
- [EliaAlberti/jev-rules](https://github.com/EliaAlberti/jev-rules) - Claude Code plugin that asks Jev one yes/no per standing rule and injects only the rules relevant to the current prompt or edited file. <sub>MIT · JavaScript · [live](https://eliaalberti.github.io/jev-rules/)</sub>
- [ermagent-star/jev-model-router](https://github.com/ermagent-star/jev-model-router) - Opencode plugin and CLI where Jev classifies each task and a policy maps it to the cheapest free Zen model, with a fail-closed paid-model gate. <sub>MIT · TypeScript</sub>
- [eyenpi/actionreflex](https://github.com/eyenpi/actionreflex) - Python gate that checks each agent tool call against a set of policies in one Jev request and returns allow, block or escalate with probabilities. <sub>MIT · Python</sub>
- [fabricio852/jevshift](https://github.com/fabricio852/jevshift) - Codex plugin with four hooks where Jev classifies prompts, blocks bad computer actions, auto-allows safe permissions and trims large tool output. <sub>MIT · JavaScript</sub>
- [felipeduartea/agent-guard](https://github.com/felipeduartea/agent-guard) - PreToolUse guard for Codex, Claude Code and Devin CLI that runs fixed emergency checks, then has Jev judge commands against plain-language policy rules. <sub>no license · Python</sub>
- [felixfisher/pi-jev-compaction](https://github.com/felixfisher/pi-jev-compaction) - Experimental Pi extension that asks Jev two yes/no questions per old tool call and stores an auditable keep, truncate or drop replay. <sub>MIT · TypeScript</sub>
- [fiale-plus/jev-cli](https://github.com/fiale-plus/jev-cli) - Unofficial npm CLI for agents with ask, gate and replay commands, question-file linting, cost estimates and exit codes that encode the decision. <sub>MIT · TypeScript</sub>
- [flaviusapop/jev-router](https://github.com/flaviusapop/jev-router) - Local proxy launchers for Claude Code, Codex, Grok and opencode that rewrite each turn's model and reasoning effort from a Jev classification. <sub>MIT · JavaScript</sub>
- [FleeexCorp/jev-orchestrator](https://github.com/FleeexCorp/jev-orchestrator) - Claude Code skill and CLI that hand delegate, parallelise, retry and stop decisions to Jev while Codex workers run in separate git worktrees. <sub>MIT · TypeScript</sub>
- [fscm44xyz/jevtrace](https://github.com/fscm44xyz/jevtrace) - Local DevTools that wrap the official SDK client, record every state, question and probability to SQLite and replay decisions with edits. <sub>MIT · TypeScript</sub>
- [furedea/reflex-state](https://github.com/furedea/reflex-state) - Pi coding-agent extension that tracks changed files, check validity and blockers outside the main LLM, using Jev for typed semantic decisions with replay. <sub>MIT · TypeScript</sub>
- [getexcited/stepwarden](https://github.com/getexcited/stepwarden) - Claude Code plugin that checks each pending tool call against the session plan with Jev and allows, asks or blocks by probability thresholds. <sub>Apache-2.0 · TypeScript</sub>
- [gloridifice/pi-jev-router](https://github.com/gloridifice/pi-jev-router) - Pi 0.85.1 extension, off by default, adding Jev-driven model switching, tool-call review and periodic context filtering with a /jev setup wizard. <sub>MIT · TypeScript</sub>
- [glyzinie/jev-cerebras-gateway](https://github.com/glyzinie/jev-cerebras-gateway) - Bun CLI that has Jev classify a prompt's route and complexity via Vercel AI Gateway, then picks the reasoning effort for a Cerebras-hosted generator. <sub>no license · TypeScript</sub>
- [gnoviawan/omp-jev-tools](https://github.com/gnoviawan/omp-jev-tools) - oh-my-pi extension adding jev_judge, jev_route, jev_rerank and jev_verify tools plus a /jev slash command for quick yes/no checks. <sub>no license · TypeScript</sub>
- [goulinkh/omp-semantic-policy](https://github.com/goulinkh/omp-semantic-policy) - oh-my-pi plugin that compiles project instructions into policy rules and checks each agent action against them, using Jev for semantic evaluation. <sub>no license · TypeScript</sub>
- [gshost1/vercel-compaction](https://github.com/gshost1/vercel-compaction) - Claude Code plugin that scores old tool calls with Jev through the Vercel AI Gateway and drops or truncates stale ones instead of summarising. <sub>MIT · TypeScript</sub>
- [hangarbay/jev.mcp](https://github.com/hangarbay/jev.mcp) - Go MCP server, shipped as a Docker image, exposing classify, score, check, ask and models tools backed by Jev. <sub>MIT · Go</sub>
- [hatt-io/jevkeep](https://github.com/hatt-io/jevkeep) - Codex plugin that asks Jev which conversation excerpts still matter before compaction and restores them verbatim beside Codex's own summary. <sub>MIT · TypeScript</sub>
- [hemanth/pkg-gate](https://github.com/hemanth/pkg-gate) - npm library and CLI that evaluates a package's preinstall/install/postinstall scripts with System One and returns allow, warn or block. <sub>MIT · JavaScript · [live](https://hemanth.github.io/pkg-gate/)</sub>
- [henstarr/JBrancher](https://github.com/henstarr/JBrancher) - JavaScript decision layer for agent loops: deterministic rule first, then Jev scores a fixed candidate action set, then fallback to the existing actor. <sub>MIT · JavaScript</sub>
- [heph2/pi-typesafe-router](https://github.com/heph2/pi-typesafe-router) - Pi extension that classifies each prompt with Jev into fast, balanced or deep routes, shadow-logging by default, with a Home Manager module. <sub>MIT · TypeScript</sub>
- [Hexdigest123/typesafe-comment](https://github.com/Hexdigest123/typesafe-comment) - Python CLI that lints code comments on five heuristics via System One and exits non-zero below thresholds, with GitHub annotations and tree-sitter languages. <sub>MIT · Python</sub>
- [HomenShum/jev-swap](https://github.com/HomenShum/jev-swap) - Claude Code skill for replacing an LLM pipeline component with a Jev decision: responsibility mapping, three-arm live eval, fallback and an independent judge. <sub>MIT · Python</sub>
- [ibrahemid/jevprune](https://github.com/ibrahemid/jevprune) - CLI and Claude Code plugin that keeps only task-relevant lines of command output, decided per line by Jev, with full output recoverable from disk. <sub>MIT · TypeScript</sub>
- [iefnaf/pi-jev](https://github.com/iefnaf/pi-jev) - pi extension suite offering verbatim context compaction and per-turn cheap-or-strong model routing via TypeSafe or OpenRouter, set through /jev. <sub>MIT · TypeScript</sub>
- [ingebyd/fast-jev-compaction-openrouter](https://github.com/ingebyd/fast-jev-compaction-openrouter) - Fork of the fast-jev-compaction Claude Code plugin that reaches Jev through OpenRouter with zero-data-retention routing forced on every request. <sub>MIT · TypeScript</sub>
- [integrate-your-mind/jev-codex-plugin](https://github.com/integrate-your-mind/jev-codex-plugin) - Codex plugin with tools and lifecycle hooks that ask Jev to pick tools or models, diagnose failed commands and check completion claims against evidence. <sub>MIT · TypeScript</sub>
- [ioOvOoi/Pi-Jev](https://github.com/ioOvOoi/Pi-Jev) - Extension for the pi coding agent adding a batched mixed-type jev tool, a /jev panel, key login and Noul as a permission authorizer. <sub>MIT · TypeScript</sub>
- [its-panzer/jev-model-router](https://github.com/its-panzer/jev-model-router) - Python router and CLI that asks Jev to size a request and returns the cheapest Claude tier able to finish it, evaluated on 100 labelled cases. <sub>MIT · Python</sub>
- [its-panzer/skilltree](https://github.com/its-panzer/skilltree) - Local web app and MCP server that arranges agent skills as a tree and has Jev make a typed choice at each level to pick a path. <sub>MIT · JavaScript</sub>
- [Jabbslad/pi-jev-tools](https://github.com/Jabbslad/pi-jev-tools) - Pi extension adding jev_rank, jev_classify, jev_search and typesafe_evaluate tools that build batched Jev questions in code for the coding model. <sub>MIT · TypeScript</sub>
- [jcressler/fast-jev-compaction-codex](https://github.com/jcressler/fast-jev-compaction-codex) - Codex plugin that archives tool evidence as content-addressed records around native compaction and uses Jev to rank what to surface for recovery. <sub>MIT · TypeScript</sub>
- [jeiel85/jevscope](https://github.com/jeiel85/jevscope) - Local workbench for editing state and Choice/Score/Noul questions, running JSONL cases in batch, comparing two definitions and checking expectations. <sub>MIT · TypeScript · [live](https://jeiel85.github.io/jevscope/)</sub>
- [jethrojones/hermes-jev-router](https://github.com/jethrojones/hermes-jev-router) - Hermes Agent plugin that has Jev grade each request into five capability levels and routes it to a locally discovered model, showing a route card. <sub>no license · Python</sub>
- [Jiiiin/codex-jev-compaction](https://github.com/Jiiiin/codex-jev-compaction) - Codex plugin that has Jev select tool records to checkpoint before native compaction and restore after, plus a CLI that exports a trimmed transcript copy. <sub>MIT · JavaScript</sub>
- [jon-devlapaz/jev-decisions](https://github.com/jon-devlapaz/jev-decisions) - Agent skill that runs architecture decisions through one Jev call with Cynefin, reversibility, quality-attribute and premortem lenses, ending in an ADR. <sub>MIT</sub>
- [jon-devlapaz/Jevvy-chase](https://github.com/jon-devlapaz/Jevvy-chase) - Agent skill for Cursor where Jev picks the best next clarifying question from supplied candidates until the session ends in a written plan. <sub>MIT · Python</sub>
- [juanegido/jev-pr-judge](https://github.com/juanegido/jev-pr-judge) - Web app and GitHub Action that judge whether a pull request does what it claims via one Jev call, with policy thresholds in TypeScript. <sub>MIT · TypeScript · [live](https://jev-pr-judge.vercel.app)</sub>
- [kaijia323/dsh-plugin-jev](https://github.com/kaijia323/dsh-plugin-jev) - Zero-dependency DeepSeek Harness plugin registering a jev_decide tool over either the TypeSafe API or Vercel AI Gateway, with smoke tests. <sub>MIT · HTML</sub>
- [KamilPostrozny/pi-fast-jev-compaction](https://github.com/KamilPostrozny/pi-fast-jev-compaction) - Pi extension where Jev decides per tool call which old results stay in model context, with pressure bands and a grounding note after pruning. <sub>MIT · TypeScript</sub>
- [KamilPostrozny/pi-jev-code](https://github.com/KamilPostrozny/pi-jev-code) - Pi extension that gates a single coding agent with Jev pre-edit checks, evidence review, final diff audit and append-only telemetry. <sub>MIT · TypeScript</sub>
- [KaushikKC/JevScope](https://github.com/KaushikKC/JevScope) - Agent trace observability tool that asks Jev eight independent questions per step (alignment, progress, stuck, phase) and tests judgment stability. <sub>MIT · TypeScript</sub>
- [kaustav1996/reflex](https://github.com/kaustav1996/reflex) - Coding agent built on Pi where Jev gates every tool action, monitors progress, checks completion claims and routes model tiers. <sub>MIT · TypeScript</sub>
- [kcc989/keeled](https://github.com/kcc989/keeled) - TypeScript agent harness where a Jev controller selects actions and assesses progress while LLMs only generate plans, tool input and responses. <sub>no license · TypeScript</sub>
- [Kelbie/hunch](https://github.com/Kelbie/hunch) - CLI and GitHub Action that reviews changed lines against plain-English rules using Jev via Vercel AI Gateway, with a per-rule precision/recall eval command. <sub>MIT · TypeScript</sub>
- [kleosr/cursor-clijev-compaction](https://github.com/kleosr/cursor-clijev-compaction) - Cursor CLI plugin that captures tool I/O, scores each item with Jev noul questions before compaction and re-injects kept facts verbatim afterwards. <sub>MIT · TypeScript</sub>
- [konstantinosbotonakis/codex-context-diet](https://github.com/konstantinosbotonakis/codex-context-diet) - Codex PostToolUse plugin that asks Jev five questions about each bulky tool result and replaces stale ones with a bounded head and a note. <sub>no license · TypeScript</sub>
- [legacybridge-tech/pi-typesafe-jev](https://github.com/legacybridge-tech/pi-typesafe-jev) - pi extension exposing five tools (noul, choice, score, evaluate, pinned ask) that call the Jev API via fetch, with key setup commands. <sub>no license · TypeScript</sub>
- [lhotwll217/jev-cli](https://github.com/lhotwll217/jev-cli) - CLI over the System One API: JSON in, typed answers out, with keychain auth, saved question schemas, batches and dry-run. <sub>no license · TypeScript</sub>
- [lukebward/typesafe-aws-policies](https://github.com/lukebward/typesafe-aws-policies) - Pulumi CrossGuard policy pack where Python checks AWS resource config and Jev judges whether it exceeds the stated intent, flagging at p >= 0.8. <sub>no license · Python</sub>
- [luomo66ccff/reflexmesh](https://github.com/luomo66ccff/reflexmesh) - Decision runtime that records Jev-style tool-call judgments from Codex MCP, Claude Code hooks and DeepSeek Harness into SQLite for replay. <sub>MIT · JavaScript</sub>
- [maddygoround/typesafeai-cli](https://github.com/maddygoround/typesafeai-cli) - Python CLI for agents and shells with ask, noul, choice, score, find, rank, extract, verify and screen commands plus an installable skill. <sub>MIT · Python</sub>
- [madeye/pi-jev](https://github.com/madeye/pi-jev) - Pi extension that uses Jev to pick focused file excerpts for a local coding model, with exact-result caching, outage cooldown and recorded measurements. <sub>MIT · TypeScript</sub>
- [Madhumasa84/jrx](https://github.com/Madhumasa84/jrx) - CLI gate for coding agents that combines local hard rules with Jev risk signals and a deterministic policy returning allow, review or hold. <sub>Apache-2.0 · Python</sub>
- [maharshi365/oc-agent-router](https://github.com/maharshi365/oc-agent-router) - OpenCode plugin that asks Jev which configured model each new task subagent should run on, with a fallback model and timeout. <sub>MIT · TypeScript</sub>
- [mahavirn/mnjev-cli](https://github.com/mahavirn/mnjev-cli) - Zero-dependency Node terminal tool that infers the question type from plain text, captures command output as state and prints probability bars. <sub>MIT · TypeScript</sub>
- [manojlds/jev-review](https://github.com/manojlds/jev-review) - Code-review CLI that sends a bounded git diff to Jev with 23 typed questions and maps answers to approve, comment, request changes or escalate. <sub>no license · TypeScript</sub>
- [marcus/frost](https://github.com/marcus/frost) - Go CLI that has Jev assess a task prompt, then picks a model, harness and effort level locally from your configured catalog and policy. <sub>MIT · Go</sub>
- [masaki39/natural-language-interface](https://github.com/masaki39/natural-language-interface) - zsh tool that turns a natural-language request into a real command line for gh, git, docker and ~700 CLIs by having Jev pick subcommands and flags. <sub>no license · TypeScript</sub>
- [mastnacek/pi-decision-gate](https://github.com/mastnacek/pi-decision-gate) - Pi coding-agent plugin for human approval of every tool call with Jev risk scoring via OpenRouter and spend tracking in Czech koruna. <sub>MIT · TypeScript</sub>
- [memovai/openevals](https://github.com/memovai/openevals) - Langfuse-compatible trace server on one SQLite file that uses Jev to judge every step and whole trajectories of agent runs. <sub>MIT · TypeScript</sub>
- [Mentioum/judgement](https://github.com/Mentioum/judgement) - Go library and JSON-first CLI for System One that validates requests offline and evaluates them, built for use from agents and scripts. <sub>MIT · Go</sub>
- [micic-mihajlo/jev-tool-runner](https://github.com/micic-mihajlo/jev-tool-runner) - Codex hooks, MCP tool and CLI where Jev picks source reads, searches and checks to run while Codex only writes code. <sub>no license · JavaScript</sub>
- [minhgv/jev-mcp](https://github.com/minhgv/jev-mcp) - MCP server with diff review, change-risk, requirement-check, claim-verify, screening and ranking tools that return an auto, review or escalate action. <sub>MIT · TypeScript</sub>
- [misaalya/jev-traversal](https://github.com/misaalya/jev-traversal) - Terminal semantic code search where Jev walks folder to file to function and returns the matching location with a probability. <sub>no license · TypeScript</sub>
- [moezubair/check-risk](https://github.com/moezubair/check-risk) - CLI and GitHub Action that scores code-change risk from path and dependency rules plus Jev semantic signals, and recommends checks and reviewers. <sub>MIT · TypeScript</sub>
- [MoonTory/claude-jev-guard](https://github.com/MoonTory/claude-jev-guard) - Claude Code PreToolUse hook that asks Jev five questions about each Bash or edit call and returns allow, ask or deny. <sub>no license · TypeScript</sub>
- [MoonTory/pi-jev-harness](https://github.com/MoonTory/pi-jev-harness) - Pi extension where Jev routes tools per turn, pre-fetches relevant file windows, trims long tool output, detects loops and guards tool calls. <sub>no license · TypeScript</sub>
- [morcoan/JevSeek](https://github.com/morcoan/JevSeek) - Desktop coding agent where Jev selects the next tool, DeepSeek fills in arguments and OpenHands executes, with a React UI and saved sessions. <sub>MIT · Python</sub>
- [moto-taka/jev-orchestrator](https://github.com/moto-taka/jev-orchestrator) - Local TUI orchestrator where Jev makes typed assignment, review and approval decisions while Codex, Claude Code, Pi and OpenCode do the work. <sub>MIT · TypeScript</sub>
- [mpiv-ai/bb-plugin-typesafe-router](https://github.com/mpiv-ai/bb-plugin-typesafe-router) - BB plugin that uses Jev to pick harness, model and reasoning effort for a thread's first message, then asks the user to confirm. <sub>MIT · TypeScript</sub>
- [MrDesjardins/jevrealtimecodecheck](https://github.com/MrDesjardins/jevrealtimecodecheck) - VS Code and Cursor extension that checks your git diff against Markdown rule files with one Jev question per rule, then rates severity and locates lines. <sub>no license · TypeScript</sub>
- [mwijanarko1/pi-jev-agent](https://github.com/mwijanarko1/pi-jev-agent) - Pi extension that has Jev choose the next tool before each model step so the main model sees only that tool's schema. <sub>MIT · TypeScript</sub>
- [nekowasabi/jev-routing-go](https://github.com/nekowasabi/jev-routing-go) - Go proxy for Claude Code, Codex and Grok Build that prunes tool results and uses Jev to narrow each step's tools to one schema. <sub>MIT · Go</sub>
- [NicolasMontone/jev-evals](https://github.com/NicolasMontone/jev-evals) - Rubric-based eval harness for LLM outputs that sends all rubrics for a case in one Jev call via Vercel AI Gateway and prints the real cost. <sub>no license · TypeScript</sub>
- [NicolasMontone/jev-memory](https://github.com/NicolasMontone/jev-memory) - Long-term memory layer for the Vercel AI SDK with Jev write, retrieve and evict gates that store and return facts verbatim. <sub>no license · TypeScript</sub>
- [NitayRabi/hunch](https://github.com/NitayRabi/hunch) - CLI and Claude Code/Codex plugin that walks a repo with Jev or OpenJEV classifications to gather file snippets relevant to a task. <sub>MIT · TypeScript</sub>
- [nitoba/opencode-jev-router](https://github.com/nitoba/opencode-jev-router) - OpenCode 2 plugin that asks Jev for the next tool before each model call and exposes one tool, a top-K shortlist or the full catalog by confidence. <sub>MIT · TypeScript</sub>
- [noetion/dsh-jev](https://github.com/noetion/dsh-jev) - DeepSeek Harness bundle registering a jev_ask tool so an agent can send mixed noul, choice and score questions in one call. <sub>MIT · TypeScript</sub>
- [obekt/jev-agentic-ops](https://github.com/obekt/jev-agentic-ops) - Python patterns for a Jev decision layer beside a reasoning model: stdlib client, pre-publish content gate, brief priors and an A/B harness vs an LLM. <sub>no license · Python</sub>
- [obetomuniz/paseo-jev-route](https://github.com/obetomuniz/paseo-jev-route) - Paseo daemon plugin that classifies a prompt with Jev into staff, review, cheap or lead lanes, then creates a workspace and launches the agent. <sub>MIT · TypeScript</sub>
- [Obrais-cloud/typesafe-mcp](https://github.com/Obrais-cloud/typesafe-mcp) - Python MCP server with judge, rerank and raw systemone tools, where a local Ollama model compiles natural language into typed Jev requests. <sub>no license · Python</sub>
- [Obrais-cloud/typesafe-translate](https://github.com/Obrais-cloud/typesafe-translate) - CLI where a local Ollama model compiles a plain-language request into a valid state and questions payload, validates it and runs it on Jev. <sub>no license · Python</sub>
- [oceanByte/tsai-cli](https://github.com/oceanByte/tsai-cli) - Shell CLI for noul, choice and score questions with assertion flags that turn any answer into a CI or pre-commit gate with distinct exit codes. <sub>MIT · TypeScript</sub>
- [okooo5km/jev](https://github.com/okooo5km/jev) - Single-file stdlib Python CLI and agent skill for yes, pick and score decisions from the shell via Jev on OpenRouter, with batch specs. <sub>Apache-2.0 · Python</sub>
- [Olli0103/openclaw-typesafe-ai](https://github.com/Olli0103/openclaw-typesafe-ai) - OpenClaw plugin exposing one optional typesafe_decide tool that sends caller-supplied state and typed questions to Jev, with SecretRef credentials. <sub>MIT · TypeScript</sub>
- [open-sdlc/typesafe-security-review](https://github.com/open-sdlc/typesafe-security-review) - 122 Python classifiers, one per OWASP cheat sheet, that score source text with Noul questions, plus a runner that fans a file out to all of them. <sub>no license · Python</sub>
- [OpenAgentsInc/bender](https://github.com/OpenAgentsInc/bender) - Coding agent written in Bend2 and C that uses Jev to classify the next action and an OpenRouter model to generate code. <sub>MIT · C</sub>
- [ourines/hermes-jev](https://github.com/ourines/hermes-jev) - Hermes Agent tool plugin exposing Jev judgments through either the TypeSafe API or Cloudflare AI, with interactive key setup and no cross-provider fallback. <sub>MIT · Python</sub>
- [Panebianco00/jev-claude](https://github.com/Panebianco00/jev-claude) - Claude Code plugin with decide/check MCP tools and hooks that gate plan approval, user questions, risky commands and installs on Jev answers. <sub>MIT · TypeScript</sub>
- [Parth-Hariyani3001/Jev-Bench](https://github.com/Parth-Hariyani3001/Jev-Bench) - React and FastAPI dashboard that judges LLM outputs with Jev for correctness, relevance, hallucination and safety, stores results in SQLite and runs CSV suites. <sub>no license · TypeScript</sub>
- [peterbb148/typesafe-cli](https://github.com/peterbb148/typesafe-cli) - Standalone CLI binaries for macOS, Linux and Windows that store an API key, list models and run Choice, Score and Noul questions from JSON. <sub>no license · Python</sub>
- [phuthuycoding/jev-audit](https://github.com/phuthuycoding/jev-audit) - Pre-commit auditor sending the git diff to Jev for secret-leak, vulnerability, quality and scope questions, with a 79-case eval corpus and chunking. <sub>no license · Python</sub>
- [picaye/jev-compaction](https://github.com/picaye/jev-compaction) - Context compaction for Hermes sessions that scores each tool call with two Noul questions and drops or truncates stale ones while keeping all text verbatim. <sub>MIT · JavaScript</sub>
- [Pinutss/jev-agent-router](https://github.com/Pinutss/jev-agent-router) - Python router exposed over HTTP and MCP that picks one agent from a registry, abstains or falls back once; local heuristic by default, Jev as optional judge. <sub>MIT · Python</sub>
- [Pinutss/jev-mcp-router](https://github.com/Pinutss/jev-mcp-router) - MCP tool selector that picks tools from a catalog under a token budget without running them; local heuristic by default, Jev as optional judge. <sub>MIT · Python</sub>
- [Pinutss/jev-memory-selector](https://github.com/Pinutss/jev-memory-selector) - Filter that trims an agent's retrieved memories to a token budget, offered as Python API, HTTP and MCP; local heuristic by default, Jev as optional judge. <sub>MIT · Python</sub>
- [prajwal-svm/jev-decision-gate](https://github.com/prajwal-svm/jev-decision-gate) - GitHub Action that labels and comments on PRs with Jev's change kind, three risk flags and a ship/needs_review/risky verdict. <sub>no license · Python · [live](https://prajwal-s-venkatesh.github.io/jev-decision-gate/)</sub>
- [prodBirdy/painpoints](https://github.com/prodBirdy/painpoints) - Rust CLI, MCP server and native viewer that has Jev score every source file on six architecture pain dimensions and writes a ranked report for coding agents. <sub>MIT · Rust</sub>
- [pZacca/askjev](https://github.com/pZacca/askjev) - MCP server that lets an agent ask Jev a plain question and get calibrated probabilities, run locally via npx or hosted on Cloudflare Workers. <sub>MIT · TypeScript · [live](https://jev.zacca.dev/mcp)</sub>
- [rainbowpuffpuff/jev-builder-loop](https://github.com/rainbowpuffpuff/jev-builder-loop) - Grok skill that mixes Jev probabilities with priors to choose a builder agent's next act, with a small benchmark from a real release session. <sub>MIT · Python</sub>
- [raj8525/universal-jev](https://github.com/raj8525/universal-jev) - CLI and MCP server giving coding agents Jev choice, noul, score and command-guard calls plus pruning of stale tool outputs from transcripts. <sub>MIT · JavaScript</sub>
- [raulahumada/security-jev](https://github.com/raulahumada/security-jev) - Reusable GitHub workflow combining Gitleaks and npm audit with Jev security and quality questions to comment on and block PR merges. <sub>no license · TypeScript</sub>
- [Rawson08/the-llm-dispatcher](https://github.com/Rawson08/the-llm-dispatcher) - OpenAI-compatible proxy and Claude Code/Codex wrappers that ask Jev five questions per request to pick the cheapest adequate model and effort; TypeScript and C#. <sub>MIT · C#</sub>
- [rbalch/typesafeai-review](https://github.com/rbalch/typesafeai-review) - Diff reviewer that slices hunks, asks Jev narrow typed questions per hunk and composes verdict, score and findings in code; run with uv. <sub>no license · Python</sub>
- [RemiCarbonne/jev-code-context-router](https://github.com/RemiCarbonne/jev-code-context-router) - Indexes a repository, asks Jev to select relevant symbols and injects bounded source context into Claude Code, Hermes or MCP clients. <sub>MIT · Python</sub>
- [Rika-Labs/proof](https://github.com/Rika-Labs/proof) - Code review linter where plain-English rules in a TypeScript file are judged by Jev against changed hunks or whole files, with thresholds and a cache. <sub>MIT · TypeScript</sub>
- [Ripwords/agent-gate-loop](https://github.com/Ripwords/agent-gate-loop) - GitHub Action turning an issue into a PR via a Claude fixer, gated by guards, checks, a reviewer and Jev verification of findings and scope. <sub>no license · TypeScript</sub>
- [RiskAverseTech/toolgate](https://github.com/RiskAverseTech/toolgate) - Claude Code PreToolUse hook that scores tool calls with Jev for destructive, exfiltration, privilege and off-task risk under a YAML policy. <sub>MIT · TypeScript</sub>
- [rubichandrap/hermes-jev-guard](https://github.com/rubichandrap/hermes-jev-guard) - Hermes Agent plugin using Jev for per-turn lane and model-tier planning, a tool-risk gate and a done-check after file edits; stdlib only, fail-open. <sub>MIT · Python</sub>
- [rustfuture/reflex-control](https://github.com/rustfuture/reflex-control) - Rust policy engine combining deterministic checks with Jev signals to accept, retry, verify or escalate agent work, logged to SQLite with a synthetic benchmark. <sub>MIT · Rust</sub>
- [SadiqOnGithub/jev-lab](https://github.com/SadiqOnGithub/jev-lab) - Interactive terminal session and canned test cases for asking Jev noul, choice and score questions against a pasted state through OpenRouter. <sub>no license · TypeScript</sub>
- [SashaSkind/beyondgreen](https://github.com/SashaSkind/beyondgreen) - Typed scout/critic/investigator/verifier loop that inspects evidence left by a passing end-to-end test and decides regression, clean or insufficient. <sub>no license · TypeScript · [live](https://sashaskind.github.io/beyondgreen/)</sub>
- [seanperkins/omp-jev-watchdog](https://github.com/seanperkins/omp-jev-watchdog) - Shadow-only Oh My Pi extension that uses Jev to record instruction conflicts and false verification claims without steering the agent. <sub>MIT · TypeScript</sub>
- [Shashank-H/pi-jev-context-curator](https://github.com/Shashank-H/pi-jev-context-curator) - Pi extension asking Jev one Noul per new message unit to permanently drop context no future turn needs, fail-open with fingerprint caching. <sub>MIT · TypeScript</sub>
- [Shifty-Eye-Games/foreman-jev](https://github.com/Shifty-Eye-Games/foreman-jev) - Fork of thruwire/foreman where Jev supervises a Codex worker through Vercel AI Gateway, with a mandatory acceptance command and read-only Azure PR review. <sub>MIT · Python</sub>
- [shishiv/pi-jeev](https://github.com/shishiv/pi-jeev) - Pi extension exposing a jev_decide tool that compares two to eight options with balanced evidence and returns recommend, abstain or review_required. <sub>no license · TypeScript</sub>
- [slandau3/pi-fast-jev](https://github.com/slandau3/pi-fast-jev) - Pi extension that asks Jev two noul questions per aged tool call and keeps, truncates or drops it from context, caching verdicts in the session file. <sub>no license · TypeScript</sub>
- [souhoc/hunch](https://github.com/souhoc/hunch) - Go CLI that sends a GitHub PR's diff, body and project guidelines to Jev and prints a typed review rubric with probability bars. <sub>no license · Go</sub>
- [stillroom/agent-workflow-lab](https://github.com/stillroom/agent-workflow-lab) - Teaching lab for an agent workflow with typed state, allow-listed transitions, one Jev judgment and a human approval gate; 65 tests and a replayable recording. <sub>MIT · Python</sub>
- [STRML/omp-classifier](https://github.com/STRML/omp-classifier) - OMP plugin that sends unvetted bash commands and process-spawning eval payloads to Jev and prompts on unsafe or unsure verdicts, failing closed. <sub>MIT · TypeScript</sub>
- [taisan11/jev-agent](https://github.com/taisan11/jev-agent) - Terminal coding agent where Jev picks the next action as a Choice and Codex generates the commands and file contents, with an OpenTUI approval UI. <sub>no license · TypeScript</sub>
- [TannerMidd/specpi-jev-guard](https://github.com/TannerMidd/specpi-jev-guard) - Pi extension that gates shell and file tool calls with local rules plus a Jev danger probability via OpenRouter or TypeSafe, failing closed. <sub>MIT · JavaScript</sub>
- [tea1013/jev-guard](https://github.com/tea1013/jev-guard) - Go CLI that asks Jev whether a shell command risks data loss or secret leaks and prompts for confirmation before running it. <sub>no license · Go</sub>
- [tgiridhar/claude-code-jev-smart-router](https://github.com/tgiridhar/claude-code-jev-smart-router) - HTTP proxy for Claude Code that has Jev classify each request and rewrites the model field, switching only when prompt-cache rebuild cost pays back. <sub>MIT · Python</sub>
- [thiago-ss/jev-review](https://github.com/thiago-ss/jev-review) - PR review bot asking Jev typed correctness, security and verification questions, applying deterministic approval gates; dry-run and comment-only by default. <sub>no license · Python</sub>
- [trufyrelabs/tru-jev-harness](https://github.com/trufyrelabs/tru-jev-harness) - TypeScript harness with a Jev RAG relevance gate and a tool-risk gate returning allow, escalate or block, plus mock mode and a Vite playground. <sub>MIT · TypeScript</sub>
- [tvdavies/jev-review-lab](https://github.com/tvdavies/jev-review-lab) - Stdlib Python scripts that ask pinned Jev yes/no risk questions about a git diff and record uncalibrated hints, with an explicit data egress contract. <sub>no license · Python</sub>
- [twilwa/pi-typesafe](https://github.com/twilwa/pi-typesafe) - Pi extension running four Jev hazard checks before bash/write/edit and four diff-quality checks after, in advisory, shadow or blocking mode. <sub>no license · TypeScript</sub>
- [twwright/jeverything](https://github.com/twwright/jeverything) - Installable agent skill for finding and implementing Jev decision points in a repo, with Gateway and native SDK examples and a companion course. <sub>MIT · [live](https://jeverything.vercel.app/courses/jev)</sub>
- [vava-nessa/pi-jev-compaction](https://github.com/vava-nessa/pi-jev-compaction) - Pi extension that replaces summarizing compaction by having Jev score each old tool call and deleting dead ones while keeping the rest verbatim. <sub>MIT · TypeScript</sub>
- [vayungodara/jev-lint](https://github.com/vayungodara/jev-lint) - CLI that lints an Obsidian vault or Markdown wiki for contradictions and stale claims with Jev under a dollar budget, writing an HTML evidence report. <sub>MIT · Python · [live](https://jevlint.vayun.net)</sub>
- [vedang/pi-progress-bar](https://github.com/vedang/pi-progress-bar) - Pi widget that discovers session tasks and shows reported progress and task health from Jev Score/Choice judgments rendered with local labels. <sub>no license · TypeScript</sub>
- [Verhex/xerify](https://github.com/Verhex/xerify) - CLI, library and MCP server that verifies claims against bounded evidence through a second provider, with Jev typed decisions as a verifier adapter. <sub>MIT · TypeScript · [live](https://verhex.github.io/xerify/)</sub>
- [viniciosrab/opencode-jev-router](https://github.com/viniciosrab/opencode-jev-router) - OpenCode plugin that has Jev rank relevant tools before each request, logging in shadow mode and narrowing the tool catalog only in opt-in active mode. <sub>MIT · TypeScript</sub>
- [vnmoorthy/siege](https://github.com/vnmoorthy/siege) - Hackathon system where a Jev allow/block/escalate gate guards a support agent's tool calls and a defender loop rewrites the gate policy from breaches. <sub>MIT · TypeScript · [live](https://vnmoorthy.github.io/siege/)</sub>
- [watany-dev/jev-playground](https://github.com/watany-dev/jev-playground) - Codex hooks auto-mode wired to Jev with design and gateway reports, plus prefecture-guessing and RGB score samples. <sub>no license · TypeScript</sub>
- [willfish/pi-observational-memory-jev](https://github.com/willfish/pi-observational-memory-jev) - pi extension that has Jev keep/drop and classify verbatim transcript candidates into a ledger used for model-free compaction. <sub>MIT · TypeScript</sub>
- [xpressabhi/job-search-skills](https://github.com/xpressabhi/job-search-skills) - Two agent skills that find jobs and autofill ATS applications in the user's Chrome, using Jev for eligibility, fit, duplicate and form-answer judgments. <sub>MIT · JavaScript · [live](https://xpressabhi.github.io/job-search-skills/)</sub>
- [yanmad27/jev-ask](https://github.com/yanmad27/jev-ask) - Claude Code plugin that intercepts AskUserQuestion and lets Jev answer when derivable, gated by a second 'is this personal' question. <sub>no license · JavaScript</sub>
- [yannip1234/ask-jev](https://github.com/yannip1234/ask-jev) - Two Codex skills plus a dependency-free Python/curl CLI for sending typed Jev checks on plans, edits and completion claims during work. <sub>no license · Python</sub>
- [youyo/decio](https://github.com/youyo/decio) - Go CLI that turns piped context into a choice, boolean or score via Jev and optionally dispatches pre-declared actions from YAML config. <sub>MIT · Go</sub>
- [zavocc/ground-zero](https://github.com/zavocc/ground-zero) - Python library that uses Jev via OpenRouter to check whether model responses and tool-call outputs are grounded in the prompt and sources. <sub>no license · Python</sub>
- [zhangxaochen/dsh-jev](https://github.com/zhangxaochen/dsh-jev) - Cordis plugin bundle for DeepSeek Harness adding a Jev client, semantic loop guard, shell safety gate and top-K tool pruner. <sub>MIT · TypeScript</sub>
- [zsoXi/agent-handoff-gate](https://github.com/zsoXi/agent-handoff-gate) - Experimental protocol, schemas and offline evaluation kit for checking evidence behind worker agents' PASS/BLOCKED reports with Jev. <sub>MIT · Python</sub>

## Games and control

Jev making real-time decisions in a game or a simulator.

### [tsai-sc](https://github.com/phyous/tsai-sc)

<a href="https://github.com/phyous/tsai-sc"><img src="docs/media/phyous__tsai-sc.png" alt="tsai-sc: Harness where Jev plays the original StarCraft shareware Strongarm mission from structured state via mouse and keyboard, recording every action probability" width="640"></a>

<sub>Media: phyous/tsai-sc (MIT)</sub>

Harness where Jev plays the original StarCraft shareware Strongarm mission from structured state via mouse and keyboard, recording every action probability.

**Why it is here:** Release videos, a victory screenshot, and an evidence bundle with a verifier; README claims one win with 421 decisions, 382.95 ms median API latency, and 9,445,640 input tokens, and states this does not establish a win rate.

**Know before you use it:** A single successful run on development attempt 16, with heavy harness-side candidate generation and strategy guidance in the prompt; setup is tested on macOS Apple Silicon only.

<sub>MIT · Python</sub>

### [jev-drone](https://github.com/RomanSlack/jev-drone)

<a href="https://github.com/RomanSlack/jev-drone"><img src="docs/media/romanslack__jev-drone.png" alt="jev-drone: MuJoCo quadrotor that flies a five-station obstacle course from its camera, with Jev making the tactical maneuver choice at ~2.5 Hz under a code safety reflex" width="640"></a>

<sub>Media: RomanSlack/jev-drone (MIT)</sub>

MuJoCo quadrotor that flies a five-station obstacle course from its camera, with Jev making the tactical maneuver choice at ~2.5 Hz under a code safety reflex.

**Why it is here:** Ablation with Jev disabled (README claims 17.7 m vs 77.5 m, 80 calls, 0.11 s median latency), run and replay commands, screenshots, and a list of simulator bugs and negative results.

**Know before you use it:** The Jev result is a single run, and the README states an earlier 3-seed comparison showed no advantage.

<sub>MIT · Python</sub>

- [i2cjak/RISC-jeV](https://github.com/i2cjak/RISC-jeV) **(notable)** - Web simulator that runs compiled C on a SERV RISC-V core whose logic-gate lookup tables come from 22 Jev boolean answers. <sub>no license · Python · [live](https://jev-riscv-production.up.railway.app)</sub>
- [lbotinelly/jev-little-airways](https://github.com/lbotinelly/jev-little-airways) **(notable)** - Browser air-traffic toy where each plane asks Jev four batched questions every 1.6 s (route, emergency, response, clearance), with a live request monitor. <sub>MIT · HTML</sub>
- [0x963D/last-exit](https://github.com/0x963D/last-exit) **(notable)** - Cyberpunk border-crossing bluff game where Jev reads your statements and picks the inspector's next action; ships a 100-crossing evaluation with raw logs. <sub>no license · JavaScript · [live](https://gate.fade.tools)</sub>
- [ably-labs/jev-pong](https://github.com/ably-labs/jev-pong) **(notable)** - Pong where the ball advances one step per model decision, racing Jev against chat LLMs in four lanes over an Ably channel, with recorded latency stats. <sub>Apache-2.0 · TypeScript · [live](https://jev-pong.ably.dev)</sub>
- [alee792/robojev](https://github.com/alee792/robojev) **(notable)** - Controls a real Trossen WidowX arm and a MuJoCo sim from natural language, with Jev answering typed judgments about 10 times a second; documents its limits. <sub>no license · Python</sub>
- [denikuchero/jev-chess-lab](https://github.com/denikuchero/jev-chess-lab) **(notable)** - Six recorded chess experiments with Jev alone, with a tactical filter and with a Stockfish shortlist, with PGNs, costs, replays and candid conclusions. <sub>GPL-3.0 · Python · [live](https://denikuchero.github.io/jev-chess-lab/)</sub>
- [Icohen007/jev-play-ping-pong](https://github.com/Icohen007/jev-play-ping-pong) **(notable)** - Dependency-free Node script where Jev plays a browser table-tennis game in real time from structured telemetry, with a recorded 11-0 run and cost figures. <sub>MIT · JavaScript · [live](https://indispensable-lingonberry-hot.julius.site/)</sub>
- [IgorWarzocha/jev-plays-balatro](https://github.com/IgorWarzocha/jev-plays-balatro) **(notable)** - Balatro mod and controller where Jev plans the run and picks every move from structured state; documents the best run falling short at ante 8. <sub>no license · Python</sub>
- [integrate-your-mind/jev-nethack](https://github.com/integrate-your-mind/jev-nethack) **(notable)** - Jev-controlled NetHack player with runner, public viewer, recorded games, a BC/PPO pilot and published negative experiment results. <sub>no license · Python · [live](https://jev-nethack-live.poppybyte.chatgpt.site)</sub>
- [kentaro/jev-shogi](https://github.com/kentaro/jev-shogi) **(notable)** - Jev plays shogi against Fairy-Stockfish by choosing among all legal moves, with per-game records, videos, costs and lookahead variants. <sub>no license · Python</sub>
- [MoonTory/jev-snake](https://github.com/MoonTory/jev-snake) **(notable)** - Browser Snake where Jev answers seven questions per tick, with code veto, greedy baseline, ablation switches, headless eval and a coach-learning loop. <sub>no license · TypeScript</sub>
- [safzanpirani/pong-jev](https://github.com/safzanpirani/pong-jev) **(notable)** - Jev plays Atari Pong from five digit-free phrases per frame, with a heuristic baseline, raw-coordinate mode for comparison and a human duel mode. <sub>no license · TypeScript</sub>
- [tirukovelamanoj/jev-plays-doom](https://github.com/tirukovelamanoj/jev-plays-doom) **(notable)** - ViZDoom agent where Jev picks one of three buttons from structured monster positions, scored over 20 seeded episodes against random and hand-coded play. <sub>MIT · Python</sub>
- [tryaksh/jev-pick-and-place-study](https://github.com/tryaksh/jev-pick-and-place-study) **(notable)** - MuJoCo pick-and-place pilot comparing Jev, Claude Haiku and reactive rules over 20 episodes each, with traces, video and stated limits. <sub>no license · Python</sub>
- [fhshaik/typesafe-mario](https://github.com/fhshaik/typesafe-mario) - Python harness that parses NES emulator RAM into structured JSON and lets Jev pick one of seven controller actions every few frames in Super Mario Bros. <sub>no license · Python</sub>
- [standardagents/jevpilot](https://github.com/standardagents/jevpilot) - Three.js driving simulator where Jev chooses among sampled steering-and-speed paths up to four times a second, with candidate and JSON inspectors. <sub>no license · JavaScript · [live](https://jevpilot.standardagents.ai)</sub>
- [sorrycc/typesafe-snake](https://github.com/sorrycc/typesafe-snake) - Browser Snake where code computes legal moves and flood-fill facts and Jev picks one per tick through a Hono proxy, going straight if the answer is late. <sub>no license · TypeScript</sub>
- [shantanugoel/mario-jev](https://github.com/shantanugoel/mario-jev) - Python prototype that plays NES Super Mario Bros by sending decoded RAM state to Jev and composing its movement and jump answers into controller buttons. <sub>no license · Python</sub>
- [Reisenbug/TerraBlind](https://github.com/Reisenbug/TerraBlind) - Terraria tModLoader mod where Jev answers five questions every 200 ms to steer boss fights while code handles aiming, timing and movement. <sub>no license · C#</sub>
- [emrickgarrett/OneVOneJev](https://github.com/emrickgarrett/OneVOneJev) - Server-authoritative browser FPS where one player duels a Jev-controlled sniper that gets move, aim and fire questions about nine times a second. <sub>no license · TypeScript</sub>
- [kavehmz/typesafe-playground](https://github.com/kavehmz/typesafe-playground) - Dockerized demos: a support-message decision lab and 3D driving simulations where Jev picks lane and target speed from simulated sensor data. <sub>no license · JavaScript</sub>
- [arielweinberger/jev-autopilot](https://github.com/arielweinberger/jev-autopilot) - Three.js drone simulator where Jev answers four stick-axis Choices and two booleans per step to fly across a generated city and land. <sub>no license · TypeScript</sub>
- [vinilana/live-jev](https://github.com/vinilana/live-jev) - Browser 2D self-driving sim where Jev answers four typed driving questions every 200 ms, with a side-by-side LLM driver comparing latency and cost. <sub>no license · JavaScript</sub>
- [AbdelStark/heist-one](https://github.com/AbdelStark/heist-one) - Browser stealth game where Jev supplies each guard's threat, suspicion and intent judgments while a deterministic 30 Hz server validates every proposal. <sub>MIT · TypeScript</sub>
- [leftspace89/JevBird](https://github.com/leftspace89/JevBird) - Pygame Flappy Bird where Jev picks one of several simulated flight paths per pipe, with chosen and rejected paths drawn on screen. <sub>MIT · Python</sub>
- [0xtrou/rubikjev](https://github.com/0xtrou/rubikjev) - Next.js 3D Rubik's cube game where Jev rates your scramble with a tier and difficulty while a deterministic solver streams the solution. <sub>no license · TypeScript · [live](https://rubikjev.solo.engineer)</sub>
- [4anti/jev-broadcast-lab](https://github.com/4anti/jev-broadcast-lab) - Chess arena where Jev picks among chess.js legal moves while in-browser Stockfish scores the game for the operator only. <sub>no license · JavaScript</sub>
- [AmoghCreator/doom-jev](https://github.com/AmoghCreator/doom-jev) - ViZDoom agent that serializes depth and label data to a YAML report and queries Jev at about 10 Hz for goal, movement and fire choices with a terminal HUD. <sub>no license · Python</sub>
- [Amrit-Nigam/jev-royal](https://github.com/Amrit-Nigam/jev-royal) - macOS agent that plays Clash Royale through iPhone Mirroring using local template matching for perception and Jev to pick among code-validated plays. <sub>no license · TypeScript</sub>
- [anxkhn/JevPlaysPokemon](https://github.com/anxkhn/JevPlaysPokemon) - Runner where Jev picks moves and switches from a JSON battle state against the FireRed Elite Four, via Pokemon Showdown or an mGBA ROM with a dashboard. <sub>GPL-3.0 · HTML</sub>
- [erhanmeydan/jev2048](https://github.com/erhanmeydan/jev2048) - Playwright agent that plays a live 2048 site with one Jev choice call per move and prints the four direction probabilities. <sub>MIT · Python</sub>
- [lukaske/jev-doom-agent](https://github.com/lukaske/jev-doom-agent) - Two Chocolate Doom WebAssembly instances side by side where Jev Choice picks tactical macros from structured game state and a local controller executes them. <sub>no license · TypeScript</sub>
- [ojusave/route-lab](https://github.com/ojusave/route-lab) - Persuasion game on Render Workflows where you pitch an invention to three fictional judges; TypeScript and Python versions using TypeSafe and OpenRouter. <sub>no license · TypeScript · [live](https://route-lab-typescript-web.onrender.com)</sub>
- [phureewat29/got-jev](https://github.com/phureewat29/got-jev) - Game of Thrones roleplay where an LLM writes each scene and Jev labels location, beat, mood, danger and in-fiction status to drive header, music and retries. <sub>no license · TypeScript · [live](https://jev.phureewat.com)</sub>
- [phyous/tsai-civ2](https://github.com/phyous/tsai-civ2) - Harness that has Jev play original Civilization II in a DOSBox browser runtime via Choice vectors, with a spectator dashboard of action probabilities. <sub>no license · Python</sub>
- [raihankhan-rk/jevarena](https://github.com/raihankhan-rk/jevarena) - Next.js spectator demo where two independent Jev agents play Snake side by side in separate iframes using only indexed direction-button clicks. <sub>MIT · TypeScript</sub>
- [Smartitect/2048](https://github.com/Smartitect/2048) - Python 2048 engine with console, pygame and browser UIs where a Jev player picks among legal moves from engine-simulated outcomes of each direction. <sub>MIT · Python</sub>
- [TarunTomar122/jev-askable-arm](https://github.com/TarunTomar122/jev-askable-arm) - ManiSkill Franka arm sim where Jev picks one of about 30 hardcoded primitives per step to complete plain-English pick, place and press goals. <sub>MIT · Python</sub>
- [XieChengYuan/jev-gomoku](https://github.com/XieChengYuan/jev-gomoku) - Nine simultaneous Gomoku boards where two Jev players given different text inputs pick moves by Choice, with per-move request/response inspection and replay. <sub>no license · JavaScript · [live](https://xiechengyuan.github.io/jev-gomoku/)</sub>
- [404priyanshu/wikirace](https://github.com/404priyanshu/wikirace) - Live Wikipedia link race between GPT and Jev with identical candidate links per hop, timing per call, and a shortest-path scorer on the same link graph. <sub>no license · JavaScript</sub>
- [4esv/jev-mario](https://github.com/4esv/jev-mario) - Harness where Jev plays Super Mario Bros from a templated text description of emulator RAM, with per-level runs compared to a scripted run-and-jump baseline. <sub>no license · Python</sub>
- [AliUraish/Jev_SO101](https://github.com/AliUraish/Jev_SO101) - SO-101 robot arm prototype where a vision model describes two camera views and Jev picks a typed skill and answers unsafe/done checks; offline demo and tests. <sub>no license · Python</sub>
- [aoprisan/tavern-brawl](https://github.com/aoprisan/tavern-brawl) - Multiplayer text arena in Rust where players type free-form moves from phones and one request classifies kind, target, force and rule-breaking. <sub>no license · Rust</sub>
- [asfarsadewa/werewolf](https://github.com/asfarsadewa/werewolf) - Browser Werewolf game where each message is judged on about twenty questions and seven villagers update visible wolf probabilities from the answers. <sub>MIT · TypeScript · [live](https://werewolf.asfarlab.fun)</sub>
- [ashaazami/river-run-typesafe](https://github.com/ashaazami/river-run-typesafe) - Pygame River Raid-style shooter with a pilot that asks Jev in one request which of 20 lanes to fly, whether to fire and how fast to go. <sub>MIT · Python</sub>
- [bahramzada/jev-taxi-dispatch](https://github.com/bahramzada/jev-taxi-dispatch) - Real-time taxi dispatch simulation on a Baku map asking four questions per order (driver, urgency, fake order, service type), compared with Gemini Flash Lite. <sub>MIT · JavaScript</sub>
- [bugkiwi/turing-jail](https://github.com/bugkiwi/turing-jail) - Three-level web interrogation game where Jev judges a written statement on plea, logic and paradox, with shareable sealed runs. <sub>no license · TypeScript · [live](https://turing-jail.vercel.app)</sub>
- [chahero/tetris-jev](https://github.com/chahero/tetris-jev) - Pygame Tetris viewer where Jev picks each placement, showing probabilities and latency, with a same-seed heuristic run and recorded results for comparison. <sub>no license · Python</sub>
- [CharryLee0426/jev-test](https://github.com/CharryLee0426/jev-test) - Workbench where Jev plays flappybird.io and play.tetris.com in Chrome, choosing every maneuver or placement, with a launcher for adding more games. <sub>no license · TypeScript</sub>
- [chensterman/talos](https://github.com/chensterman/talos) - Minecraft bot driven over HTTP: code plans the tech tree and a batched request every 1.5s picks skill, target, danger and progress. <sub>MIT · TypeScript</sub>
- [chocochu/keeclub](https://github.com/chocochu/keeclub) - Web app for Jungle and Aeroplane Chess with invite rooms and offline same-device play, where AI seats are driven by a configured TypeSafe key. <sub>no license · TypeScript</sub>
- [DanMcInerney/robots-world](https://github.com/DanMcInerney/robots-world) - Multi-robot and drone control testbed comparing Jev control arrangements with Claude and Codex pilots over MAVLink, with recorded flight matrices. <sub>no license · TypeScript</sub>
- [Dencyuman/terrarium](https://github.com/Dencyuman/terrarium) - Browser society simulation where each resident's action per tick is chosen by Jev from feasible actions while a generative LLM deliberates in the background. <sub>no license · TypeScript</sub>
- [dj-thank/jve-driven](https://github.com/dj-thank/jve-driven) - Driving simulation lab that rebuilds Tokyo streets from PLATEAU and OSM open data and tests Jev driving decisions in shadow or live mode. <sub>no license · Python</sub>
- [ellistev/typesafe-minecraft-demo](https://github.com/ellistev/typesafe-minecraft-demo) - Mineflayer Minecraft bot whose movement, mining and block placing are chosen one API decision at a time, with a live dashboard of each call. <sub>no license · JavaScript</sub>
- [enderzcx/dsh-spire-jev](https://github.com/enderzcx/dsh-spire-jev) - DeepSeek Harness plugin exposing nine native tools so the agent can play Slay the Spire 2 through the spire-jev controller. <sub>MIT · JavaScript</sub>
- [enderzcx/spire-jev](https://github.com/enderzcx/spire-jev) - Slay the Spire 2 controller where a planner model sets strategy, Jev picks routine combat moves and code verifies multi-card turn plans. <sub>MIT · JavaScript</sub>
- [esoyuince/vector-atc](https://github.com/esoyuince/vector-atc) - Air traffic control simulation on Cloudflare Workers with 100 synthetic aircraft steered by Jev decisions, incident reports and recorded replay. <sub>MIT · JavaScript · [live](https://atc.alaz.tr)</sub>
- [ewitulsk/JevCraft](https://github.com/ewitulsk/JevCraft) - NeoForge 1.21.1 Minecraft mod where Jev picks targets for a local-player takeover mode and for persistent companions commanded via /jev goal. <sub>MIT · Java</sub>
- [filippos95/cybercab-jev](https://github.com/filippos95/cybercab-jev) - Three.js robotaxi game where Jev chooses lane and speed from plain-English obstacle descriptions while the player throws hazards onto the road. <sub>no license · JavaScript</sub>
- [gradiuscypher/spacebrains](https://github.com/gradiuscypher/spacebrains) - Autonomous SpaceTraders.io player where OpenRouter LLMs write long-horizon plans and Jev makes per-ship tactical Choice/Noul decisions, with a web UI. <sub>MIT · Python</sub>
- [hegargarcia/jev-playground](https://github.com/hegargarcia/jev-playground) - Tic-tac-toe app where the player faces Jev and four LLMs on separate boards, each choosing from the same legal moves via Vercel AI Gateway. <sub>no license · TypeScript</sub>
- [iammusham/jev-snake](https://github.com/iammusham/jev-snake) - Snake environment where Jev chooses the direction each tick from structured state, with a browser human baseline, pygame client and logged fallbacks. <sub>no license · Python</sub>
- [IAnMove/jev-game-agent](https://github.com/IAnMove/jev-game-agent) - Super Mario Bros controller on BizHawk where Jev picks moves from RAM state and emulator lookahead while Python records and backtracks. <sub>no license · Python</sub>
- [iluoxw/jev-vs-llm-snake](https://github.com/iluoxw/jev-vs-llm-snake) - Side-by-side snake game where Jev and an OpenAI-compatible LLM share seed, tick rate and facts, comparing score, timeouts, latency and cost. <sub>no license · TypeScript</sub>
- [jammaru/jev-lab](https://github.com/jammaru/jev-lab) - Two web demos: a 100-NPC town simulation where Jev picks each person's next action, and a shogi board where Jev picks Gote's reply from legal moves. <sub>MIT · TypeScript</sub>
- [jdhornsby/typesafe-jev](https://github.com/jdhornsby/typesafe-jev) - Python CLI that has Jev play chess against Stockfish under seven board encodings and reports per-move confidence for each. <sub>no license · Python</sub>
- [JLarky/chess-jev-web](https://github.com/JLarky/chess-jev-web) - Web chess against Jev with a legal-moves mode and a chaos mode where it picks any piece and any square. <sub>no license · TypeScript · [live](https://chess-jev-web.vercel.app)</sub>
- [JLarky/jev-chess](https://github.com/JLarky/jev-chess) - Browser chess game against Jev where one Choice over the legal UCI moves picks each move and chess.js enforces the rules. <sub>no license · TypeScript · [live](https://jev-chess-one.vercel.app)</sub>
- [joshbla/jev-plays-2048](https://github.com/joshbla/jev-plays-2048) - Local 2048 on the original engine where Jev picks each move from one-step previews of the legal moves, with pacing controls and JSON run export. <sub>no license · TypeScript</sub>
- [juancamiloqhz/roverlab](https://github.com/juancamiloqhz/roverlab) - Browser 3D planetary rover sandbox where a selectable Jev controller chooses actions, with a decision timeline, probabilities and baseline fallback. <sub>no license · TypeScript</sub>
- [KnlnKS/F-00](https://github.com/KnlnKS/F-00) - Harness that lets Jev play live Gen 9 random battles on Pokemon Showdown, picking from legal actions with damage-calc evidence and a spectator UI. <sub>no license · TypeScript</sub>
- [kspviswa/chakravyuha-jev](https://github.com/kspviswa/chakravyuha-jev) - Browser ring-maze where Jev picks every move; overruled moves are marked red and a history page checks whether confidence predicts accuracy. <sub>MIT · JavaScript</sub>
- [kunalkushwaha/jevkart](https://github.com/kunalkushwaha/jevkart) - Terminal car game in Go where every steering decision is a Jev call, making API latency visible; includes a headless latency bench. <sub>no license · Go</sub>
- [kxzk/typesafe-jev-drone-demo](https://github.com/kxzk/typesafe-jev-drone-demo) - Three.js drone simulator with a FastAPI backend where Jev chooses among nine candidate movements and the request and response are inspectable. <sub>no license · Python</sub>
- [KyleKreuter/jev2048](https://github.com/KyleKreuter/jev2048) - Web app running many 2048 games in parallel with Jev choosing each move, plus an editor for the board state format sent to it. <sub>no license · TypeScript</sub>
- [lambertsj/beatjev](https://github.com/lambertsj/beatjev) - Cloudflare Worker game: 25 rounds of spam-or-not where a human races Jev on speed and accuracy, with fairness rules and a shareable result. <sub>no license · JavaScript</sub>
- [M-Yanagishawa/jev-speed](https://github.com/M-Yanagishawa/jev-speed) - Real-time Speed card game on Cloudflare Workers where Jev plays as two VOICEVOX characters, with per-move probability and latency logs. <sub>no license · TypeScript · [live](https://jev-speed.mun0412.workers.dev)</sub>
- [MachineLearning-Nerd/jev-tetris](https://github.com/MachineLearning-Nerd/jev-tetris) - Streamlit Tetris where the engine enumerates legal placements, Jev chooses one by ID, and code verifies the cells before locking the piece. <sub>no license · Python</sub>
- [manuvikash/jev-chess](https://github.com/manuvikash/jev-chess) - Python server where Jev plays chess against an OpenAI model, streaming moves over SSE with latency, eval and per-game JSONL records. <sub>no license · Python</sub>
- [MartinPuli/f1](https://github.com/MartinPuli/f1) - 3D racing sim where ten drivers, each with its own Jev model and prompt, race seeded procedural circuits with saved replays. <sub>MIT · JavaScript · [live](https://jevf1.vercel.app)</sub>
- [melonash/pleaseno](https://github.com/melonash/pleaseno) - Daily persuasion game where Jev scores seven emotional levers in each free-text attempt and picks the character's authored reply. <sub>no license · TypeScript · [live](https://pleasenoo.vercel.app)</sub>
- [memorysaver/jev-atari-lab](https://github.com/memorysaver/jev-atari-lab) - Atari (ALE) experiments where Jev answers structured control questions, with logged Pong trials against random and scripted baselines. <sub>GPL-2.0 · Python</sub>
- [milanboers/jev-plays-pokemon](https://github.com/milanboers/jev-plays-pokemon) - Pokemon Red agent on PyBoy that feeds Jev a text snapshot from RAM and turns parallel yes/no answers into goals and button presses. <sub>no license · Python</sub>
- [mittal-parth/jev-experiments](https://github.com/mittal-parth/jev-experiments) - Python loops where Jev drives Chrome's dino game and a local Krunker-style arena from structured state, with a heuristic fallback and decision inspector. <sub>no license · Python</sub>
- [mizchi/jev-gomoku](https://github.com/mizchi/jev-gomoku) - MoonBit Jev API client, one-shot question CLI and a Jev-vs-Jev gomoku CLI that renders games to real-time GIFs. <sub>no license · MoonBit</sub>
- [mizuamedesu/SuperTuxKart-Jev](https://github.com/mizuamedesu/SuperTuxKart-Jev) - SuperTuxKart fork with a local controller that lets Jev drive the real game from structured engine telemetry. <sub>no license · C++</sub>
- [mocchalera/naimono-lab](https://github.com/mocchalera/naimono-lab) - Family word game about inventing nonexistent words; a Cloudflare Worker asks Jev whether each word exists, with an LLM referee for borderline cases. <sub>no license · JavaScript · [live](https://naimono-lab.mocchalera.app)</sub>
- [NesanSelvan/pacman-jev](https://github.com/NesanSelvan/pacman-jev) - Pacman where each Jev call is one game tick: eight typed questions pick the direction and fill a live read-out panel. <sub>no license · TypeScript</sub>
- [nozo-moto/jev-reverse](https://github.com/nozo-moto/jev-reverse) - Browser and CLI Reversi where Jev chooses among legal moves given board features, playable against Jev, a one-ply CPU or Jev vs Jev. <sub>no license · JavaScript</sub>
- [Ode98/guessing-game-v2](https://github.com/Ode98/guessing-game-v2) - Yes/no word-guessing game where Jev answers yes, no, too ambiguous or exploit attempt, with the secret word kept in an encrypted token. <sub>no license · TypeScript</sub>
- [ojusave/beat-jev](https://github.com/ojusave/beat-jev) - 3D penalty shootout against Jev run as a Render Workflows task with scores in Postgres, in TypeScript and Python versions. <sub>MIT · TypeScript · [live](https://beat-jev-typescript-web.onrender.com)</sub>
- [opaielsheikh/ps2-ai-agent](https://github.com/opaielsheikh/ps2-ai-agent) - Python agent that captures a PCSX2 window, asks Jev for the next move, injects virtual PS2 controller input and draws a telemetry HUD. <sub>no license · Python</sub>
- [oqzl/JevSamples](https://github.com/oqzl/JevSamples) - Cloudflare Worker agent-world simulation asking Jev five questions per agent per turn, plus a leak-controlled JRA horse-racing backtest. <sub>no license · JavaScript</sub>
- [pahndev/Type-Safe-Maze-Demo-](https://github.com/pahndev/Type-Safe-Maze-Demo-) - Dependency-free Node app where Jev picks each move through a random maze from discovered cells only, with a per-move diagnostics panel and BFS comparison. <sub>no license · JavaScript</sub>
- [Para-FR/casse-brique-typesafe](https://github.com/Para-FR/casse-brique-typesafe) - Next.js brick breaker whose paddle can be handed to Jev, which picks one of 16 target zones every 150 ms from the computed ball path. <sub>no license · TypeScript</sub>
- [patrickhaahr/jevjack](https://github.com/patrickhaahr/jevjack) - Bun server that deals blackjack and asks Jev for hit/stand/double/split per hand, with a probability-bar UI and a seeded A/B eval against basic strategy. <sub>MIT · TypeScript</sub>
- [pholgy/little-cab](https://github.com/pholgy/little-cab) - Local 2D taxi simulation where Jev via OpenRouter picks passengers, routes and driving commands during a timed shift, logging decisions, latency and API spend. <sub>MIT · TypeScript</sub>
- [Riti0208/jevbug](https://github.com/Riti0208/jevbug) - Artificial-life simulation where Jev decides for 2D creatures, measuring whether meaningless signals become informative versus no-communication controls. <sub>no license · TypeScript · [live](https://jevbug.vercel.app)</sub>
- [rolki-png/JevArena](https://github.com/rolki-png/JevArena) - Next.js spectator arena where two Jev agents play Snake against each other through Vercel AI Gateway, with a labeled demo policy when no key. <sub>MIT · TypeScript · [live](https://jev-arena-ochre.vercel.app)</sub>
- [rudrasingh500/jev_minecraft](https://github.com/rudrasingh500/jev_minecraft) - Mineflayer bot that picks Minecraft survival actions from a legal-action menu via Jev toward beating the Ender Dragon, with viewer, memory and run logs. <sub>no license · JavaScript</sub>
- [shantanugoel/jev-games](https://github.com/shantanugoel/jev-games) - Visual lab where Jev plays Super Mario Bros, Kung Fu and Doom through emulator plugins, with step, replay and a scripted baseline mode. <sub>no license · Python</sub>
- [shantanugoel/tetris-ai](https://github.com/shantanugoel/tetris-ai) - Browser Tetris with a REST API played by a built-in search agent, a Jev Choice-over-landings agent or any OpenAI-compatible chat model; 170 test assertions. <sub>MIT · JavaScript</sub>
- [sharosoo/jev-omok](https://github.com/sharosoo/jev-omok) - 3D WebGL gomoku where a deterministic engine handles forced tactics and Jev picks non-forced moves and commentary via a Cloudflare Worker. <sub>no license · TypeScript · [live](https://omok.sharosoo.com)</sub>
- [siroccomask/snake-jev](https://github.com/siroccomask/snake-jev) - Desktop Snake where one Jev call per tick answers nine collision and food questions and Python composes the move; reports one 29-food run. <sub>MIT · Python</sub>
- [smalltownrobotics/proxima-1024](https://github.com/smalltownrobotics/proxima-1024) - Generation-ship command sim in Python with a 3D browser UI where Jev models how 1,024 fictional crew respond to the player's decisions. <sub>MIT · Python</sub>
- [SongMarco/jev-jstris](https://github.com/SongMarco/jev-jstris) - Controller that lets Jev choose Tetris placements and plays real Jstris in Chromium by keyboard, verifying each landing; one 40-line sprint completed. <sub>MIT · TypeScript</sub>
- [stbenjam/jev-boarding](https://github.com/stbenjam/jev-boarding) - Local airplane boarding simulator comparing five fixed boarding orders with a Jev dispatcher that picks passengers per free row from scan and seat events. <sub>no license · JavaScript</sub>
- [stbenjam/jevagotchi](https://github.com/stbenjam/jevagotchi) - Local virtual pet in the browser whose feeding, play and medicine decisions are made by Jev via OpenRouter on a configurable check-in interval. <sub>no license · JavaScript</sub>
- [Taufique-Ansari/dunjev](https://github.com/Taufique-Ansari/dunjev) - Three-act Phaser side-scrolling brawler where enemies query Jev for attack, dodge, block or retreat, with a live probability panel. <sub>no license · TypeScript · [live](https://dunjev.vercel.app)</sub>
- [techadnank9/traceclaw](https://github.com/techadnank9/traceclaw) - Hackathon browser game about filing house rules after a failed bakery shift, with Jev as a second judge answering three typed questions per rule. <sub>MIT · TypeScript</sub>
- [ThanabordeeN/drone-city-simulator](https://github.com/ThanabordeeN/drone-city-simulator) - Browser 3D drone simulator with an automation API and an AI control tab where Jev scores pitch, strafe, yaw and vertical at 5 Hz via OpenRouter. <sub>no license · TypeScript</sub>
- [TheGali/terrarium](https://github.com/TheGali/terrarium) - Browser sandbox where Jev picks one of eleven controls for a creature each step, with a full log of state, questions, probabilities and latency. <sub>MIT · JavaScript</sub>
- [TholeG/typesafe-chess](https://github.com/TholeG/typesafe-chess) - Jev-vs-Jev chess where each move is a Choice over legal moves annotated by code, with optional MCTS using Jev's distributions as policy and value. <sub>MIT · JavaScript</sub>
- [tpaulshippy/shady-town](https://github.com/tpaulshippy/shady-town) - Mafia-style party game for a TV plus phones where Jev moderates and drives live suspicion meters from claims, votes and reactions. <sub>no license · Ruby</sub>
- [tpiros/escape-from-mos-eisley](https://github.com/tpiros/escape-from-mos-eisley) - Free-text gamebook where Gemini authors JSON books and Jev judges each typed action with one batch of questions that the engine turns into rules. <sub>no license · TypeScript</sub>
- [Waxmell114514/jev-fps](https://github.com/Waxmell114514/jev-fps) - Browser aim trainer where Jev answers target Choice, engage Noul and tempo Score every 90 ms and code handles the aiming; simulator fallback without a key. <sub>no license · TypeScript</sub>
- [wbarakat/jev-bomb](https://github.com/wbarakat/jev-bomb) - Pygame bomb-defusal game where Jev reads written rulebooks and picks one action per decision across wires, button, password and maze modules. <sub>no license · Python</sub>
- [wbarakat/jev-snake](https://github.com/wbarakat/jev-snake) - Snake played in real time by Jev choosing among three moves plus a danger score, with a live belief panel and heuristic fallback. <sub>no license · Python</sub>
- [Xy2002/poker-jev-test-bench](https://github.com/Xy2002/poker-jev-test-bench) - React Texas Hold'em game that probes Jev at every betting decision and shows its answers beside a Monte Carlo rule-based coach. <sub>MIT · JavaScript</sub>
- [Yasserbhb/Agent-JEV-Tetris](https://github.com/Yasserbhb/Agent-JEV-Tetris) - Tetris where Jev picks each move from seven legal actions annotated with code-computed landing outcomes, with notes on what fixed play. <sub>no license · HTML</sub>
- [yeger00/jev-chess](https://github.com/yeger00/jev-chess) - Chrome extension plus Node service that plays chess.com bot games by asking Jev to choose among chess.js legal moves, with decision logs. <sub>no license · TypeScript</sub>
- [YYK2007/jev-flappy](https://github.com/YYK2007/jev-flappy) - Flappy Bird where Jev chooses flap or coast every 160 ms from projected physics, showing probabilities, latency, tokens and cost. <sub>no license · JavaScript · [live](https://jev-flight-school.yusufkusibati.chatgpt.site)</sub>

## Benchmarks and research

Measurements, evals and open reimplementations. Read the method before the number.

### [SemIf](https://github.com/TheoLeeCJ/SemIf)

<a href="https://github.com/TheoLeeCJ/SemIf"><img src="docs/media/theoleecj__openjev.gif" alt="SemIf: Open reproduction of the Jev interface: reads typed option probabilities from Qwen3.5-4B logits in one forward pass; includes a WebGPU browser demo" width="640"></a>

<sub>Media: TheoLeeCJ/openjev (MIT)</sub>

Open reproduction of the Jev interface: reads typed option probabilities from Qwen3.5-4B logits in one forward pass; includes a WebGPU browser demo.

**Why it is here:** Pinned model revision, committed fixtures, runners and raw results; README claims 1.023 s vs 5.332 s for 21 criteria against generated JSON on one RTX 3090 and 0.845 vs Jev's published 0.883 agreement on a 102-row subset.

**Know before you use it:** Does not call Jev at all; the Jev number it compares against is copied from TypeSafe's published records on a 102-row alignable subset.

<sub>MIT · Python · [live](https://openjev.com)</sub>

### [open-jev](https://github.com/JoshuaSP/open-jev)

Inference harness that gets typed JSON decisions from DiffusionGemma by constrained final-logit readout, scored against Jev's 20 public eval cases.

**Why it is here:** README claims 408 replayed questions with a per-workflow table (87.8% grouped 2-step vs 90.8% saved Jev), pinned model revision and library versions, Modal reproduce commands, included receipts, and a disclosed bookkeeping bug.

**Know before you use it:** Never calls the Jev API (compares against saved outputs), references are model-derived, and reproducing needs an H100 plus gated model access.

<sub>MIT · Python</sub>

### [jevlike](https://github.com/vinnylarouge/jevlike)

Research starter that trains a small one-pass option-attention scorer returning a probability per text option, with Doom and chess controller examples.

**Why it is here:** Runnable quickstart (synthetic data, train, eval, predict), shuffled-context control, released checkpoints, and a demo video; README claims 26% on target-disjoint Wikispeedia against about 8% for controls.

**Know before you use it:** It does not use Jev or match its API, and the README states the headline numbers come from earlier local experiments, not the quickstart.

<sub>MIT · Python</sub>

### [typesafe-ai-benchmark](https://github.com/iammrduncan/typesafe-ai-benchmark)

Side-by-side benchmark UI running Jev against Qwen on Cerebras over seven synthetic workloads, recording latency, cost and fixture agreement.

**Why it is here:** Demo GIF/MP4, raw exports and methodology docs, run instructions; README claims Jev p50 176 ms and $0.0119 vs Qwen p50 215 ms and $0.3106 over ~480 requests, and reports scenes where Jev lost (Home 15/24 vs 24/24).

**Know before you use it:** One run on synthetic fixtures from a dev machine, which the README states; the repo description ('LLM gateway that mimics Jev') no longer matches the README.

<sub>MIT · TypeScript</sub>

### [jev-on-a-laptop](https://github.com/rorshopping/jev-on-a-laptop)

Study of Jev-style parallel typed decisions on stock 1.5B-8B models on an Apple Silicon laptop, scored against TypeSafe's public eval cases.

**Why it is here:** One-command setup and benchmark scripts with raw results in the repo; README claims 373 reference question-pairs with local Qwen2.5-7B at 73.8% agreement versus Jev's published 86.6%, and retracts an earlier 5-case tie.

**Know before you use it:** It never calls Jev (Jev's numbers are TypeSafe's published ones), the engine is a third-party recreation, and the repo carries an x-posts promo folder.

<sub>no license · Python · [live](https://huggingface.co/spaces/rorshopping/parallel-constrained-decisions)</sub>

### [decider](https://github.com/Mapika/decider)

Open 2B reproduction of the System One model class, fine-tuned from Qwen3.5-2B-Base, that serves TypeSafe's /v1/systemone format so official SDKs work with it.

**Why it is here:** Released weights on Hugging Face, train and serve scripts, and result tables; README claims held-out accuracy 0.741 / ECE 0.088 on 24 tasks versus 0.642 / 0.105 for the base model, plus a candid limitations list.

**Know before you use it:** No license on the repo, no comparison against Jev itself, and the reference `train.sh full` recipe has by its own admission never been run end to end.

<sub>no license · Python</sub>

- [TianyuCodings/NanoJev](https://github.com/TianyuCodings/NanoJev) **(notable)** - 0.6B open replica of Jev with training pipeline, model and dataset, compared side by side with Jev on maze and Snake runs. <sub>MIT · Python · [live](https://nanojev.tianyuchen99.chatgpt.site)</sub>
- [kshetrajna12/reflex](https://github.com/kshetrajna12/reflex) **(notable)** - Open re-creation of Jev on Qwen3.5 that answers typed questions with calibrated probabilities, with a WebGPU in-browser demo. <sub>MIT · Python · [live](https://kshetrajna12.github.io/reflex/)</sub>
- [r-ms/mini-jev](https://github.com/r-ms/mini-jev) **(notable)** - Preregistered experiment reading option-letter logits from frozen Qwen3-4B instead of grammar-constrained JSON, with accuracy CIs and speed results. <sub>MIT · Python</sub>
- [mizchi/jev-playground](https://github.com/mizchi/jev-playground) **(notable)** - MoonBit Jev client plus experiments (gomoku, MOBA, shell-risk hook, ESLint plugin, small DSL) with written reports measuring which decision patterns work. <sub>no license · TypeScript</sub>
- [AbdelStark/jev-benchmarks](https://github.com/AbdelStark/jev-benchmarks) **(notable)** - Evaluation harness measuring accuracy, calibration, selective coverage and latency of Jev versus GLiNER2.5 on three BTZSC classification sets. <sub>Apache-2.0 · Python</sub>
- [carlaiau/jev-reranking](https://github.com/carlaiau/jev-reranking) **(notable)** - Zero-shot reranking comparison of Jev against monoBERT and published TREC DL 2019 runs on MS MARCO, reporting nDCG, MAP, time and API cost. <sub>MIT · Python</sub>
- [aabolfazl/typesafe-local](https://github.com/aabolfazl/typesafe-local) **(notable)** - MLX server mimicking /v1/systemone on a local Qwen model by caching the document KV and reading answer-token logits, with post-hoc calibration and stated limits. <sub>MIT · Python</sub>
- [mahlernim/jev-korean-benchmark](https://github.com/mahlernim/jev-korean-benchmark) **(notable)** - Frozen 100-question-per-cell check of Jev on Korean versus English reading, paraphrase and medical exam sets, with every response recorded. <sub>no license · Python · [live](https://ahn-lab.org/jev-korean-benchmark/)</sub>
- [mithalouni/system-one-open](https://github.com/mithalouni/system-one-open) **(notable)** - Open Jev replica on Gemma 4 E2B LoRA and Gemma 3 270M served on Modal, with public-eval scores against Jev and eight recorded demo replicas. <sub>no license · Python · [live](https://mithalouni--jev-serve-e2b-full-server-web.modal.run)</sub>
- [RINNECODER/jev-behavior-study](https://github.com/RINNECODER/jev-behavior-study) **(notable)** - Behaviour study of Jev 1.13.0 from 11,621 requests plus Snake and 3D city driving experiments, with raw results, limits and offline verification. <sub>MIT · Python · [live](https://rinnecoder.github.io/jev-behavior-study/city_demo/)</sub>
- [sgoedecke/system-one](https://github.com/sgoedecke/system-one) **(notable)** - Open reimplementation of the System One interface on open LLMs via single-token choice inference, with Doom and Wikirace demos on Qwen3-8B. <sub>no license · Python</sub>
- [zhuyansen/jev-search-rerank-eval](https://github.com/zhuyansen/jev-search-rerank-eval) **(notable)** - Graded relevance eval of Jev reranking vs BM25 and embeddings on 164 zh/en queries and 9,831 pairs, with bootstrap CIs and judge-circularity measured. <sub>MIT · Python</sub>
- [ikermoel/open-alternative-jev](https://github.com/ikermoel/open-alternative-jev) **(notable)** - Python library answering packed typed questions from an open-weights LLM's next-token distribution in one forward pass, benchmarked on RACE-H and MMLU. <sub>Apache-2.0 · Python</sub>
- [wondertwins/jev-benchmark](https://github.com/wondertwins/jev-benchmark) **(notable)** - Two benchmarks of Jev with raw requests included: chess move selection against Stockfish and NPC addressee detection on speech-to-text transcripts. <sub>MIT · Python</sub>
- [anessbelbati/jev-rerank-bench](https://github.com/anessbelbati/jev-rerank-bench) **(notable)** - Reranking benchmark of Jev against Cohere Rerank 4, zerank-2 and a chat model over 14 datasets from the same BM25 candidates, with saved raw responses. <sub>MIT · Python · [live](https://anessbelbati.com/lab/jev-reranking/)</sub>
- [AnshChoudhary/typesafe-ai-firewall](https://github.com/AnshChoudhary/typesafe-ai-firewall) **(notable)** - Shadow-mode harness evaluating a five-hazard Jev firewall for agent tool calls on 600 records, with pass/fail gates, ablations and a failure report. <sub>no license · Python</sub>
- [arnabgho/rlcd-lite](https://github.com/arnabgho/rlcd-lite) **(notable)** - Reconstruction of RLCD: parallel constrained JSON decoding on a causal LM trained with GRPO and a Brier-score reward, with calibration evals. <sub>Apache-2.0 · Python</sub>
- [catoenm/first-instinct](https://github.com/catoenm/first-instinct) **(notable)** - Open training experiments for a 9B decision model with released adapters and raw predictions, reporting SFT gains and RL runs that did not help. <sub>MIT · Python</sub>
- [Gaurav-Gosain/jev-sec-bench](https://github.com/Gaurav-Gosain/jev-sec-bench) **(notable)** - Blind benchmarks of Jev on 662 deepset prompt-injection messages and 200 vulnerable-code pairs, with raw per-sample results and a TUI. <sub>MIT · Go</sub>
- [gemanor/jev-code-review-benchmark](https://github.com/gemanor/jev-code-review-benchmark) **(notable)** - Benchmark of Jev vs Gemini Flash vs Claude on four Python code review rules over 1,080 calls, reporting cost, latency, accuracy and consistency. <sub>MIT · Python</sub>
- [PistachioAIHQ/jev-synergy-screening](https://github.com/PistachioAIHQ/jev-synergy-screening) **(notable)** - Evaluates Jev include/exclude screening of 851 ADHD MEDLINE abstracts against Cohen 2006 triage labels, with F1, latency, cost and an LLM head-to-head. <sub>no license · Python</sub>
- [SamuelSacco/jev-exploration](https://github.com/SamuelSacco/jev-exploration) **(notable)** - Evidence ledger on Jev's calibration: recomputes public ECE figures against noise floors and runs an 800-item difficulty gradient of its own. <sub>no license · Python</sub>
- [TokenTrim/jev-agent-failure-benchmark](https://github.com/TokenTrim/jev-agent-failure-benchmark) **(notable)** - Runs Jev on all 6,257 text traces of the Who&When Pro failure-attribution benchmark using the official scorer and compares with the paper's LLM baselines. <sub>Apache-2.0 · Python</sub>
- [4esv/jev-eval](https://github.com/4esv/jev-eval) **(notable)** - Independent eval of Jev vs GPT-5.6 Terra on three labeled public datasets (300 items each): accuracy, calibration error, latency, cost and repeatability. <sub>no license · Python</sub>
- [adammichaelwood/jev-music-theory-1](https://github.com/adammichaelwood/jev-music-theory-1) **(notable)** - Experiment testing Jev on SATB part-writing and a theory quiz against Claude models across score formats and framings, plus a generative Rhodes chord stream. <sub>no license · TypeScript · [live](https://adammichaelwood.com/jev-music-theory-1/)</sub>
- [anisselbd/jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) **(notable)** - Reproducible benchmark of Jev versus Claude Haiku 4.5 on 2,000 phishing emails covering accuracy, calibration, latency, cost and non-AI baseline controls. <sub>no license · Python</sub>
- [bitnovus/jev-spam-eval](https://github.com/bitnovus/jev-spam-eval) **(notable)** - Notebook evaluation of zero-shot ham/spam/phishing classification on 5,733 emails versus TF-IDF baselines, showing the effect of added email context. <sub>MIT · Jupyter Notebook</sub>
- [blas0/jev-shadcn-lint-eval](https://github.com/blas0/jev-shadcn-lint-eval) **(notable)** - Eval that runs shadcn-ui/lint on 131 rule cases and asks Jev whether each finding is right and its message actionable; reports 82 percent agreement. <sub>no license · JavaScript</sub>
- [dnikolayev/typesafe-offload-bench](https://github.com/dnikolayev/typesafe-offload-bench) **(notable)** - Study of direct, relay and code-owned cascade workflows on 100 synthetic classification cases across six coding-agent models, with stated caveats. <sub>MIT · Python</sub>
- [EmilLindfors/jev-horingssvar-eval](https://github.com/EmilLindfors/jev-horingssvar-eval) **(notable)** - Eval of Jev against DeepSeek V4.1 Flash on 24 Norwegian public hearing responses with eleven questions, a label guide, raw predictions and metrics scripts. <sub>no license · Python</sub>
- [Gaurav-Gosain/jev-alpha-bench](https://github.com/Gaurav-Gosain/jev-alpha-bench) **(notable)** - Go benchmark of Jev on 5,000 Nasdaq-100 headlines measuring rank IC against excess returns; reads news well but finds no tradeable alpha. <sub>MIT · Go</sub>
- [Gaurav-Gosain/jev-headline-bench](https://github.com/Gaurav-Gosain/jev-headline-bench) **(notable)** - Go benchmark asking Jev to pick the winner of 10,984 Upworthy headline A/B tests, with exploratory and confirmatory splits and a placebo control. <sub>MIT · Go</sub>
- [hev/reranker](https://github.com/hev/reranker) **(notable)** - Reranker recipe putting a query and up to 30 documents in one Jev call, with nDCG@10 results on BEIR against Cohere, Voyage and LLM judges. <sub>Apache-2.0 · Python</sub>
- [jaredpalmer/kev](https://github.com/jaredpalmer/kev) **(notable)** - Open Jev-style model: LoRA and pointer head on Qwen2.5-0.5B answering typed questions in one prefill pass, with a /v1/systemone-compatible server. <sub>Apache-2.0 · Python</sub>
- [jourdanlabs/assay-001](https://github.com/jourdanlabs/assay-001) **(notable)** - Pre-registered test of Jev calibration and type safety on Banking77 and CLINC150 with sealed raw responses, scorer and an independent re-score. <sub>no license · Python · [live](https://donttrustme.ai/assay-001.html)</sub>
- [jujumilk3/jev-calibration-audit](https://github.com/jujumilk3/jev-calibration-audit) **(notable)** - API-only calibration audit of Jev over seven experiments and about 7,000 calls: abstain removal, Korean, Noul/Choice coherence, invariance, interference. <sub>MIT · Python</sub>
- [KantaHayashiAI/jev-does-not-play-dice](https://github.com/KantaHayashiAI/jev-does-not-play-dice) **(notable)** - Experiments showing Jev reports high Choice probabilities on fair dice and coin draws and distorts stated forecast odds, with recorded outputs and scripts. <sub>MIT · JavaScript</sub>
- [konsumer/opendecision](https://github.com/konsumer/opendecision) **(notable)** - Self-hostable System One implementation: model architecture, teacher distillation pipeline and a /v1/systemone-compatible server, with measured limits. <sub>no license · Python</sub>
- [lab-dados/jev-anotacao-sentencas](https://github.com/lab-dados/jev-anotacao-sentencas) **(notable)** - Comparison of Jev, Gemini and GPT on annotating 12 variables in 120 Brazilian court rulings, reporting accuracy, latency and cost. <sub>no license · Python · [live](https://lab-dados.github.io/jev-anotacao-sentencas/)</sub>
- [lowspecbot-GH/latency-probe](https://github.com/lowspecbot-GH/latency-probe) **(notable)** - Measures DNS, TCP, TLS and TTFB to api.typesafe.ai from Tokyo, US East and US West, cold vs keep-alive, against AWS reference endpoints. <sub>MIT · JavaScript · [live](https://latency-probe-eight.vercel.app)</sub>
- [mameli/jev-vs-luna](https://github.com/mameli/jev-vs-luna) **(notable)** - Benchmark of Jev vs GPT-5.6 Luna on 100 synthetic reviews x 3 repeats across five fields, reporting accuracy, macro F1, latency and cost. <sub>no license · Python</sub>
- [nican2018/shade-arena-jev-monitor](https://github.com/nican2018/shade-arena-jev-monitor) **(notable)** - SHADE-Arena fork evaluating Jev as a sabotage monitor and per-action gate against Gemini 2.5 Flash and Pro, with AUC figures and a report. <sub>MIT · Python</sub>
- [objectgraph/jev-samegame-bench](https://github.com/objectgraph/jev-samegame-bench) **(notable)** - Benchmark of 21 ways to present a SameGame board to Jev across 40 boards, with all 76,795 requests and responses logged and bootstrap comparisons. <sub>MIT · TypeScript · [live](https://objectgraph.com/blog/jev-plays-samegame/)</sub>
- [omauser119/JaxModels](https://github.com/omauser119/JaxModels) **(notable)** - Open typed-decision model: frozen Qwen3.5-0.8B plus a 1,026-parameter decision head in C++/llama.cpp, with a local server the TypeSafe JS SDK can point at. <sub>MIT · Python</sub>
- [onlyoneaman/jev-eval](https://github.com/onlyoneaman/jev-eval) **(notable)** - Write-up and code comparing Jev with gpt-5.4-mini and gpt-5.6-luna on four public classification sets and private pipeline decisions, about 16,000 calls. <sub>MIT · TypeScript</sub>
- [pcarrier/skibidu](https://github.com/pcarrier/skibidu) **(notable)** - Chibi Scheme program that has Jev build a small arithmetic interpreter from an empty AST, one typed decision at a time, until sandboxed acceptance tests pass. <sub>no license · Scheme</sub>
- [ritza-co/asset-register-experiments-report](https://github.com/ritza-co/asset-register-experiments-report) **(notable)** - Reproducible experiments showing a trailing newline flips a TypeSafe Noul answer 10/10 times, plus a batched accuracy comparison against an LLM. <sub>no license · Python</sub>
- [SAGAR-TAMANG/sarvam-jev](https://github.com/SAGAR-TAMANG/sarvam-jev) **(notable)** - Jev-style typed decisions read from constrained logits on sarvam-1 for Indic text, with accuracy against openjev models and shared-prefill timings. <sub>no license · Python · [live](https://sarvam-jev.feynmanpi.com/)</sub>
- [Shogo-nfrealmusic/jev-eval](https://github.com/Shogo-nfrealmusic/jev-eval) **(notable)** - Third-party comparison of Jev with gpt-4o-mini and Claude Sonnet 4.5 on routing 60 synthetic multilingual booking inquiries, with raw results and a replay demo. <sub>no license · TypeScript</sub>
- [spranab/yantrik-inference](https://github.com/spranab/yantrik-inference) **(notable)** - Open local server that reads many typed answers from one batched forward pass of an open-weights model, with benchmarks against JSON generation. <sub>Apache-2.0 · Python</sub>
- [sypherin/jev-trace-classifier](https://github.com/sypherin/jev-trace-classifier) **(notable)** - Benchmark of Jev vs local Qwen on 4,579 collusion.wiki pages for agent-vs-human authorship; reports that neither beats the majority baseline. <sub>MIT · Python</sub>
- [TokenTrim/jev-routing-experiment](https://github.com/TokenTrim/jev-routing-experiment) **(notable)** - Evaluation of Jev as an LLM router on RouterArena and LLMRouterBench, including a no-Jev ablation that matches the Jev result. <sub>Apache-2.0 · Python</sub>
- [vclic/smoking-extraction-benchmark](https://github.com/vclic/smoking-extraction-benchmark) **(notable)** - Paired benchmark of Jev vs OpenAI structured outputs on 1,000 synthetic clinical notes with ten typed fields, reporting accuracy, cost and latency. <sub>no license · Python</sub>
- [yonidavidson/browser-duel](https://github.com/yonidavidson/browser-duel) **(notable)** - Wiki-race experiment comparing Jev, two GPT models and a confidence-gated hybrid picking links in one browser, with cost and time tables. <sub>no license · TypeScript</sub>
- [yonidavidson/qa-duel](https://github.com/yonidavidson/qa-duel) **(notable)** - Compares Jev, a screenshot-reading GPT reviewer and a confidence-gated hybrid on black-box QA of saucedemo.com with known defects, reporting TP/FP, cost, time. <sub>no license · TypeScript</sub>
- [zephel01/Jev-sample](https://github.com/zephel01/Jev-sample) **(notable)** - Experiment code and 2,320 raw logs comparing one 4-way Choice with four decomposed Noul questions on 120 routing scenarios; README reports 48.3% vs 98.3%. <sub>MIT · Python</sub>
- [zhuyansen/jev-cold-start-prior](https://github.com/zhuyansen/jev-cold-start-prior) **(notable)** - Study of whether Jev answers on a day-one README predict later stars for 1,132 repos, compared with TF-IDF models, with bootstrap CIs. <sub>MIT · Python</sub>
- [zhuyansen/jev-issue-pulse](https://github.com/zhuyansen/jev-issue-pulse) **(notable)** - Study labelling 25,052 GitHub issues with Jev to detect broken releases (null result) and match triage labels versus keyword and sentiment. <sub>MIT · Python</sub>
- [zhuyansen/jev-news-cold-start](https://github.com/zhuyansen/jev-news-cold-start) **(notable)** - Study on MIND news logs testing whether zero-shot Jev headline judgments predict cold-start CTR, with temporal split, baselines and bootstrap CIs. <sub>MIT · Python</sub>
- [ekzhang/openjev-sglang](https://github.com/ekzhang/openjev-sglang) - Server implementing the Jev HTTP API with Qwen3.6-35B-A3B on SGLang prefill, deployable on Modal with a smoke test for all three answer types. <sub>no license · Python · [live](https://ekzhang--openjev-sglang-openjev.us-west.modal.direct)</sub>
- [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya) - Python package and fine-tuned open model answering choice/score/noul questions over a state in one forward pass with confidence gating. <sub>Apache-2.0 · Jupyter Notebook</sub>
- [hr98w/jev-visual](https://github.com/hr98w/jev-visual) - Jev-like visual inference on Apple Silicon: Qwen3.5-0.8B on MLX scores candidate answers about an image from logits, with UI, CLI, API and game demos. <sub>MIT · Python</sub>
- [vinilana/jev-eval-agent](https://github.com/vinilana/jev-eval-agent) - Eval harness comparing an agent that picks among 100 mocked tools itself with one where Jev picks the tool each step, over 6 tasks and 8 LLMs. <sub>no license · HTML</sub>
- [snellingio/system-one](https://github.com/snellingio/system-one) - Proof-of-concept HTTP service on MLX that returns Choice, Score and Noul probabilities by reading a local model's logits at a fixed answer position. <sub>MIT · Python</sub>
- [daseinlabs/open-jev](https://github.com/daseinlabs/open-jev) - Zero-shot one-pass option scorer on Gemma 3 4B via MLX that exposes a /v1/systemone-shaped endpoint, with a terminal Doom demo. <sub>no license · Python</sub>
- [bnsd55/jevmlx](https://github.com/bnsd55/jevmlx) - Python library and CLI that scores every allowed answer of a Pydantic schema in one MLX forward pass on Apple Silicon, returning a probability per field. <sub>MIT · Python</sub>
- [razorback16/openjev](https://github.com/razorback16/openjev) - Open decision server speaking the Jev wire API on DiffusionGemma 26B via vLLM, so the official SDKs work against it unchanged. <sub>Apache-2.0 · Python · [live](https://codiv.ai)</sub>
- [zmtomorrow/TypeAR](https://github.com/zmtomorrow/TypeAR) - Typed-decision client for open autoregressive models served by SGLang, using one-token constrained decoding and prefix-cache reuse over a JSON Schema. <sub>no license · Python</sub>
- [genai-craft/openvons](https://github.com/genai-craft/openvons) - Open Jev-style decision layer for text, images and Japanese voice commands using frozen models plus small trained heads, calibration and a none option. <sub>no license · Python · [live](https://genai-craft.com)</sub>
- [goodrahstar/jev-column-race](https://github.com/goodrahstar/jev-column-race) - Side-by-side race labelling 1,000 app reviews with Jev and Gemini Flash in four columns, with recorded timings, cost and star-rating agreement. <sub>MIT · JavaScript · [live](https://jev-column-race.vercel.app)</sub>
- [siliconkernel/vllm-jev-decison](https://github.com/siliconkernel/vllm-jev-decison) - vLLM 0.29 plugin endpoint that scores candidate labels for a finite JSON Schema and returns typed values with confidence and abstention, no generation. <sub>MIT · Python</sub>
- [kikoncuo/jevfire](https://github.com/kikoncuo/jevfire) - Parallel typed decisions on stock LLMs through vLLM by scoring single-token labels, with CUDA benchmarks and in-browser Mario and driving demos. <sub>MIT · JavaScript · [live](https://kikoncuo.github.io/jevfire/learn.html)</sub>
- [wmoto-ai/local-decision-playground](https://github.com/wmoto-ai/local-decision-playground) - Single-file web app that restricts a vLLM model to defined options and shows renormalised logprob shares per candidate for text, JSON or image input. <sub>no license · HTML</sub>
- [zhihz/openjev](https://github.com/zhihz/openjev) - Local bilingual web UI and API that reads next-token label probabilities from frozen Qwen3-4B to answer Choice and Binary questions over supplied candidates. <sub>no license · Python</sub>
- [y0usaf/jev-lm](https://github.com/y0usaf/jev-lm) - Word-level text generator that uses Jev Choice as the output layer with an n-gram drafter and Noul chunk verification, plus a bits-per-token eval. <sub>MIT · TypeScript</sub>
- [adhyaay-karnwal/jev-chat](https://github.com/adhyaay-karnwal/jev-chat) - Research decoder that assembles chat replies from Jev Choice distributions using a hierarchical codebook and speculative fan-out, with paper and traces. <sub>MIT · Python</sub>
- [CrimsonLuckyLabs/kev](https://github.com/CrimsonLuckyLabs/kev) - Local reimplementation of the Noul/Choice/Score interface that scores option tokens from a 4-bit Qwen2.5 on MLX, with an offline mock backend and tests. <sub>MIT · Python</sub>
- [zhengxuyu/litjev](https://github.com/zhengxuyu/litjev) - Server that reproduces the /v1/systemone schema on Qwen checkpoints by reading option scores from the output head, with a browser front end. <sub>Apache-2.0 · Python</sub>
- [justinhe16/trade-jev](https://github.com/justinhe16/trade-jev) - Backtest of Jev as a buy/sell/hold trader on 15 days of NQ order-book data against baselines, with stored answers replayable under new settings. <sub>MIT · Python</sub>
- [AdamPippert/granite-decisions](https://github.com/AdamPippert/granite-decisions) - Local Choice/Score/Noul inference on IBM Granite 4.1 3B via ROCm llama.cpp, with trainable heads, calibration and a model card of limitations. <sub>MIT · Python</sub>
- [CompleteDotTech/paper-package](https://github.com/CompleteDotTech/paper-package) - Manuscript and frozen evidence package for an empirical study of Jev on entity matching and relation verification, with offline replay and null results. <sub>no license · Python</sub>
- [DECRUX9812/openjev](https://github.com/DECRUX9812/openjev) - Local CPU classifier for job postings using a frozen bge-small encoder and small MLP heads behind a Jev-like typed interface. <sub>MIT · Python</sub>
- [Franzferdinan51/SystemOne](https://github.com/Franzferdinan51/SystemOne) - Local Choice/Score/Noul layer over small GLiClass checkpoints in one batched pass, with temperature, Platt and isotonic calibration. <sub>MIT · Python</sub>
- [grishahq/decisionbridge](https://github.com/grishahq/decisionbridge) - Python adapter that makes OpenAI, Anthropic, OpenRouter or local MLX models act as a Jev-style choice function with calibration and abstention. <sub>MIT · HTML</sub>
- [Hoyant-Su/JevSpawn](https://github.com/Hoyant-Su/JevSpawn) - Inference-only typed decisions from frozen Qwen3.5-4B with shared prefixes and categorical readout, timed on SQuAD2 answerability across four H100s. <sub>no license</sub>
- [jgridifier/jev-research-eval](https://github.com/jgridifier/jev-research-eval) - Eval harness that drives a pinned browser-use/jev-ultrafast checkout through 11 research cases plus stress suites and regenerates QC-graded HTML reports. <sub>no license · HTML</sub>
- [johnymontana/extraction-knowledge-graph-experiments](https://github.com/johnymontana/extraction-knowledge-graph-experiments) - Knowledge-graph extraction notebooks, several using Jev for assertion gating, relation selection per entity pair and contradiction detection. <sub>no license · Jupyter Notebook</sub>
- [rogeriochaves/jev-experiments](https://github.com/rogeriochaves/jev-experiments) - Go benchmarks of Jev latency, throughput, limits and judge accuracy, plus toys that make Jev emit caveman text and grammar-constrained JavaScript via Choice. <sub>no license · Go</sub>
- [shamazharikh/qwen-rlcd](https://github.com/shamazharikh/qwen-rlcd) - Inference-only prototype of a Jev-style decision model on Qwen3.5-0.8B using prefix-fork execution to isolate parallel question branches. <sub>no license · Python</sub>
- [zsavage8/padflow-jev-evals](https://github.com/zsavage8/padflow-jev-evals) - Small benchmark of three typed decisions from a land-development SaaS: JSON schemas, anonymized seed rows and a runner scoring accuracy, calibration and cost. <sub>MIT · Python</sub>
- [30Signals/typesafe-bench](https://github.com/30Signals/typesafe-bench) - Benchmark of Jev against Azure AI Foundry deployments on BANKING77 and CLINC150 intent classification, reporting accuracy, cost and latency. <sub>no license · Python</sub>
- [Abhi001vj/system-one-open](https://github.com/Abhi001vj/system-one-open) - Open reimplementation of the System One interface on open-weights models: prefill state once, score answer tokens for all questions in one pass. <sub>no license · Python</sub>
- [aieo-product/jev-gamebenchmark](https://github.com/aieo-product/jev-gamebenchmark) - Sandbox where Jev and LLMs play falling-block puzzle games head-to-head in real time; you edit one strategy file that defines how Jev is asked. <sub>MIT · Python</sub>
- [AIPI-mvoronovych/JEVBenchmark-Contradiction-Detection](https://github.com/AIPI-mvoronovych/JEVBenchmark-Contradiction-Detection) - Runs the CLASH contradiction-detection multiple-choice protocol on Jev with images replaced by COCO captions, plus controls and an ablation. <sub>no license · Python</sub>
- [akash-kamat/system-one-gemma](https://github.com/akash-kamat/system-one-gemma) - Open Jev-style decision model: Gemma 3 270M with a linear scoring head that scores every option in one batched forward pass. <sub>no license · Python</sub>
- [CGnomazoid/Tripwire](https://github.com/CGnomazoid/Tripwire) - Local open-weight judge that gates agent tool calls by reading answer-token logits in one forward pass with temperature calibration, on MLX or PyTorch. <sub>MIT · Python</sub>
- [cleverfakealias/jev-sandbox](https://github.com/cleverfakealias/jev-sandbox) - Actionability gate experiment over 42 Salesforce-style case fixtures, fourteen questions per request, with confusion matrix, threshold sweep and run viewer. <sub>no license · TypeScript</sub>
- [codeitlikemiley/system-one-adapter-rust](https://github.com/codeitlikemiley/system-one-adapter-rust) - Rust crate reproducing the system_one interface on top of OpenAI or Anthropic models so an LLM can be compared against TypeSafe. <sub>MIT · Rust</sub>
- [cympfh/jev-trial](https://github.com/cympfh/jev-trial) - Small Python probes of Jev on a syllogism, a text-only Doom tick and self-play tic-tac-toe, with recorded probabilities and notes on where it fails. <sub>no license · Python</sub>
- [danielgshea/jev-as-a-judge](https://github.com/danielgshea/jev-as-a-judge) - Judge reliability experiment: 100 repeats on five frozen agent outputs comparing rating variance of a Jev evaluator against a GPT evaluator. <sub>no license · Python</sub>
- [danielhirt/jev-lab](https://github.com/danielhirt/jev-lab) - Bun CLI that tests Jev through OpenRouter for repeatability, perturbation sensitivity and agreement with Claude Haiku at temperature 0, with dated findings. <sub>no license · TypeScript</sub>
- [dbobo4/local-llm-probabilistic-decision-engine](https://github.com/dbobo4/local-llm-probabilistic-decision-engine) - Python library that turns local open-weight LLMs into decision engines by scoring candidate answer sequences directly, generating zero tokens. <sub>Apache-2.0 · Python</sub>
- [deepanwadhwa/OpenDecision](https://github.com/deepanwadhwa/OpenDecision) - Open reimplementation of Choice, Noul and Score on ModernBERT zero-shot, serving a /v1/systemone endpoint compatible with the TypeSafe Python SDK. <sub>Apache-2.0 · Python</sub>
- [dnakhoa/jev-deferred-crispification](https://github.com/dnakhoa/jev-deferred-crispification) - Position paper with CPU-reproducible code arguing Jev lacks hidden-Markov belief and fuzzy membership, plus two trajectory-level audit metrics. <sub>no license · TeX</sub>
- [eggmasonvalue/jev-takes-mauboussin](https://github.com/eggmasonvalue/jev-takes-mauboussin) - Evaluation of Jev on Mauboussin's 50-question confidence calibration quiz, reporting accuracy, Brier score and comparison with 948 human takers. <sub>no license · Python</sub>
- [flintfromthebasement/llm-routing-verification-bench](https://github.com/flintfromthebasement/llm-routing-verification-bench) - Dependency-free Node benchmark of 23 cases for tier routing and draft verification that runs Jev via OpenRouter Decisions alongside chat models. <sub>MIT · JavaScript</sub>
- [HackSing/jev-report](https://github.com/HackSing/jev-report) - 52-page Chinese research report auditing Jev's launch claims, with a reproducible 50-sample Chinese test pack and a table tracing 143 cited figures. <sub>MIT · Python</sub>
- [henteko/jev-dev-cloudflare](https://github.com/henteko/jev-dev-cloudflare) - Latency bench that calls Jev through the same Hono API on Cloudflare Workers and on Node/VPS, with Server-Timing breakdown and a React compare page. <sub>MIT · TypeScript</sub>
- [inkwell-finance/jev-switchyard](https://github.com/inkwell-finance/jev-switchyard) - Fork of NVIDIA NeMo Switchyard testing Jev as the routing classifier between Kimi K2.7 Code and Claude Opus 4.7, with a 20-task comparison runner. <sub>Apache-2.0 · Python</sub>
- [jellydn/signal-gate](https://github.com/jellydn/signal-gate) - Benchmark harness comparing Jev, deterministic rules and an LLM on 100 synthetic financial-anomaly scenarios for accuracy, latency, cost and calibration. <sub>no license · TypeScript</sub>
- [jmanhype/jev-dspy-lab](https://github.com/jmanhype/jev-dspy-lab) - Offline harness computing calibration, selective risk, latency and modeled cost for Jev decisions in DSPy pipelines from recorded fixtures. <sub>MIT · Python</sub>
- [karimatayuta/tiny-jev](https://github.com/karimatayuta/tiny-jev) - Local Japanese judgment model returning choice, score and noul from Qwen3-Reranker yes/no scores, with LoRA training scripts and benchmark reports. <sub>no license · HTML</sub>
- [kentaro/jev-fizzbuzz](https://github.com/kentaro/jev-fizzbuzz) - FizzBuzz solved by asking Jev only divisibility questions, with logged accuracy from 2 to 30 digit numbers showing where divide-by-3 breaks. <sub>no license · HTML · [live](https://kentarokuribayashi.com/jev-fizzbuzz/)</sub>
- [kleosr/jevsor](https://github.com/kleosr/jevsor) - Python engine exposing Jev-style Choice, Score and Noul evaluation over caller-provided models such as Ollama or OpenAI-compatible endpoints. <sub>MIT · Python</sub>
- [knowlet/Decision-Theoretic-Mixture-of-Agents](https://github.com/knowlet/Decision-Theoretic-Mixture-of-Agents) - Reproducible study comparing mixture-of-agents selector strategies, including a 192-question OpenJev head-to-head, with paper and verification bundle. <sub>no license · Python</sub>
- [kotoba-lang/typed-decisions](https://github.com/kotoba-lang/typed-decisions) - Jev-shaped typed-decision model trained on ModernBERT and LLaDA-MoE backbones, comparing latency, accuracy, calibration and training cost. <sub>no license · Python</sub>
- [KrzysztofStaron/jev-experiments](https://github.com/KrzysztofStaron/jev-experiments) - Two experiments via Vercel AI Gateway: drawing images by scoring each pixel, and a relevance filter bench of base LLM versus LLM plus Jev. <sub>no license · TypeScript</sub>
- [kvnloo/z0int](https://github.com/kvnloo/z0int) - OpenJev runtime for Jev-style typed decisions on local hardware with logit readout and trainable scorers, plus a personalization roadmap. <sub>MIT · Python · [live](https://openjev.com)</sub>
- [lukevs/jev-at-home](https://github.com/lukevs/jev-at-home) - Jev-shaped inference on an open LLM: one shared-prefix prefill, batched question suffixes, softmax over single-token labels (Qwen3-4B). <sub>no license · Python</sub>
- [maustin10/OpenSystem1-classifier](https://github.com/maustin10/OpenSystem1-classifier) - Smoke test comparing Jev 1.13.0 with a local ModernBERT zero-shot NLI classifier on multiple-choice classification and BFCL tool routing. <sub>no license · Python</sub>
- [mihir-s-05/jev-reward-model](https://github.com/mihir-s-05/jev-reward-model) - PPO experiment setup testing Jev as terminal and shaping reward for a Qwen3.5-4B actor on dependency-workflow tasks; code and CPU tests only so far. <sub>no license · Python</sub>
- [misaalya/snbt-jev-bench](https://github.com/misaalya/snbt-jev-bench) - Benchmark of Jev on 159 community-reconstructed questions from Indonesia's SNBT 2025 entrance test, with audited answer keys and raw responses. <sub>no license · Python</sub>
- [nitro527/jev_project](https://github.com/nitro527/jev_project) - Jev-style decision engine over any OpenAI-compatible LLM using max_tokens=1 logprobs, wrapped as an MCP server with probe and benchmark scripts. <sub>no license · Python</sub>
- [novvoo/nanojev](https://github.com/novvoo/nanojev) - nanoGPT-style single-file model with choice, score and abstain heads trained with a cross-entropy, ECE and REINFORCE calibration loss. <sub>no license · Python</sub>
- [oeo/narrow-inference](https://github.com/oeo/narrow-inference) - Proof-of-concept decisions API over local or BYOK LLMs that reads single-token label logprobs, errors on incomplete coverage and logs latency and cost. <sub>no license · TypeScript</sub>
- [opedoussaut/lean-ai](https://github.com/opedoussaut/lean-ai) - Side-by-side PoC of four architectures on synthetic industrial incidents, including Jev typed decisions with confidence-based escalation and calibration metrics. <sub>no license · Python</sub>
- [pst2154/Typesafe_Testing](https://github.com/pst2154/Typesafe_Testing) - Benchmark scripts comparing Jev typed classifications against SOL, Qwen, Llama, Needle and DiffusionGemma, with written routing and reasoning reports. <sub>no license · Python</sub>
- [qjy0128/Jevtest](https://github.com/qjy0128/Jevtest) - Web test bench that runs labeled text samples through five Jev questions to evaluate sensitive-data detection, thresholds and consistency. <sub>no license · JavaScript · [live](https://qjy0128.github.io/Jevtest/)</sub>
- [qte77/2026-09-12-WandB-AGIH-CoreWeave-Hack](https://github.com/qte77/2026-09-12-WandB-AGIH-CoreWeave-Hack) - Hackathon critique-refine loop fixing Elixir bugs where real test failures are diagnosed by a TypeSafe Choice before a stronger model retries. <sub>no license · Python · [live](https://qte77.github.io/2026-09-12-WandB-AGIH-CoreWeave-Hack/)</sub>
- [Sagnnik/jev-like](https://github.com/Sagnnik/jev-like) - Experiment reading A/B/C/D logits from a frozen Qwen model to play Snake without generation, with latency and agreement measurements on a laptop GPU. <sub>no license · Python</sub>
- [shellneko/minigrid-jev](https://github.com/shellneko/minigrid-jev) - Benchmark running Jev on 18 MiniGrid tasks by sending the JSON state and a Choice over actions each step, with parallel episodes and JSON results. <sub>no license · Python</sub>
- [sio-funmatsu/fmjev](https://github.com/sio-funmatsu/fmjev) - Local HTTP server imitating the /v1/systemone shape using Apple's on-device fm model, with uncalibrated outputs and stated differences from Jev. <sub>no license · Python</sub>
- [sueszli/qwen27b-jev](https://github.com/sueszli/qwen27b-jev) - Small open reproduction of Jev's Choice on Qwen3.8-27B that reads option probabilities from logits instead of generating an answer. <sub>MIT</sub>
- [sypherin/quorum](https://github.com/sypherin/quorum) - Local reimplementation of the /v1/systemone contract over any llama-server endpoint using constrained decoding and logprobs, plus a calibration harness. <sub>no license · Python</sub>
- [teyhouse/jev-secret-detection](https://github.com/teyhouse/jev-secret-detection) - Eval that scores Jev's Noul on 100 file snippets for real secrets, reporting accuracy, AUC, Brier score and round-trip vs server latency. <sub>no license · Python</sub>
- [themsquared/jev-benchmark](https://github.com/themsquared/jev-benchmark) - Benchmark of Jev on 60 hand-labelled agent tool calls across four risk classes, with committed per-call results, latency and confidence analysis. <sub>Apache-2.0 · Python</sub>
- [thijmenkam/jev-benchmarks](https://github.com/thijmenkam/jev-benchmarks) - Harness comparing Jev with a reference LLM on four typed decision tasks, reporting accuracy, Brier, ECE, repeat agreement, latency and cost. <sub>no license · Python</sub>
- [trophee-bot/typesafe-oracles](https://github.com/trophee-bot/typesafe-oracles) - Node measurement rig probing Jev Choice, Score and Noul against Haiku baselines for accuracy, run-to-run stability, wording effects and cost. <sub>no license · JavaScript</sub>
- [twilson724/tw_typesafe](https://github.com/twilson724/tw_typesafe) - Redacted experiment wiki comparing TypeSafe System One with four LLM agents on retrieval, batching and cost, with an offline arithmetic check. <sub>no license · Python</sub>
- [TyrellD1/typesafe-ai_smoke-test](https://github.com/TyrellD1/typesafe-ai_smoke-test) - 30-prompt eval of routing queries to a work or life store with two Jev Noul questions, with per-row probabilities, latency and tokens. <sub>no license · HTML</sub>
- [vehas/thaiexam-jev-charts](https://github.com/vehas/thaiexam-jev-charts) - Static chart pages of Jev on 567 ThaiExam questions vs 110 other models: cost and speed against accuracy, plus confidence calibration. <sub>no license · HTML · [live](https://vehas.github.io/thaiexam-jev-charts/)</sub>
- [wfzyx/von](https://github.com/wfzyx/von) - Local open-source decision model with a 14MB CPU backend and a server matching the /v1/systemone wire protocol, with a benchmark table. <sub>no license · Python</sub>
- [whyihaveyou/s1-bench](https://github.com/whyihaveyou/s1-bench) - Early benchmark CLI for calibrated decision models with Jev and Kimi CLI adapters and two seed tasks covering calibration and robustness. <sub>MIT · Python</sub>
- [xingwudao/OpenJev](https://github.com/xingwudao/OpenJev) - Independent Jev-style decision API with a local mock server, Python and JS SDKs, schema validation and tests; probabilities are synthetic. <sub>no license · Python</sub>
- [xucian/fbyte-jev-vs-claude](https://github.com/xucian/fbyte-jev-vs-claude) - Benchmark scripts comparing Jev via OpenRouter with Claude Opus and Sonnet on five 20-case classification tasks, with an HTML report. <sub>no license · HTML</sub>
- [zhuyansen/jev-support-pulse](https://github.com/zhuyansen/jev-support-pulse) - Study labelling 170k support tweets with Jev to detect outages before brands acknowledge them, compared with volume, keyword and sentiment baselines. <sub>MIT · Python</sub>

## Applications and demos

End-user tools with Jev doing the judgment.

### [jevmeter](https://github.com/ChetasLua/jevmeter)

<a href="https://github.com/ChetasLua/jevmeter"><img src="docs/media/chetaslua__jevmeter.gif" alt="jevmeter: Python CLI that transcribes a video, scores every sentence with Jev Noul questions, and renders a 16:9 edit with live meters, flags and a scoreboard" width="640"></a>

<sub>Media: ChetasLua/jevmeter (MIT)</sub>

Python CLI that transcribes a video, scores every sentence with Jev Noul questions, and renders a 16:9 edit with live meters, flags and a scoreboard.

**Why it is here:** Demo GIFs and frames from a real debate run, installer plus `jevmeter doctor`, a no-footage mock example, and README claims 1,191 calls / 1,182,843 input tokens / $0.0497 for the full debate.

**Know before you use it:** The '99% held-out accuracy' is on 200 sentences the author wrote, and a 'BS index' on politicians invites reading model probabilities as fact-checks despite the README caveats.

<sub>MIT · Python</sub>

### [unclutter](https://github.com/kitze/unclutter)

Chrome/Firefox extension where Jev classifies page elements as ad, promo, newsletter, social or cookie clutter and saves reversible hiding rules per template.

**Why it is here:** Build and load steps for both browsers, direct and Vercel AI Gateway endpoints documented, a 0.9 probability-and-confidence gate, detailed privacy limits, and a synthetic-input live smoke script.

**Know before you use it:** README opens with about 100 lines of the author's product and sponsor promotion, and shows no screenshot or measured precision.

<sub>MIT · TypeScript</sub>

### [killmyidea](https://github.com/monteduro/killmyidea)

Web app that sends a startup idea to Jev as 10 parallel questions and maps the weighted 0-4 scores to a KILL, FIX, or SHIP verdict.

**Why it is here:** Live site, local run and mock mode, unit tests, a synthetic scoring benchmark runner, and a per-result panel showing raw Jev answers, probabilities, latency, and tokens.

**Know before you use it:** No license, the weights and thresholds are hand-picked with no benchmark results shown, and submitted ideas are archived server-side unless the user opts out.

<sub>no license · TypeScript · [live](https://killmyidea.stemonte.io)</sub>

### [jevlogs](https://github.com/reachjalil/jevlogs)

npm library, CLI, and local OTLP HTTP/JSON receiver that scores each log with Jev for diagnostic value and priority so only useful records go to LLM analysis.

**Why it is here:** Published npm package (README claims jevlogs@0.3.0), `npx jevlogs --live` receiver, exporter wrapper code, CI badge, and a status table that states live accuracy and savings are not yet validated.

**Know before you use it:** The savings figures are modeled assumptions, not measurements, the default `npx jevlogs` demo makes no Jev call, and it reaches Jev only through Vercel AI Gateway.

<sub>MIT · TypeScript · [live](https://jevlogs.workspaceagent.workers.dev)</sub>

### [barrunto](https://github.com/elpumberto/barrunto)

Chrome extension that asks Jev nine yes/no questions per X post or HN comment and labels, fades or hides bait, flame, snark and tangents via weighted recipes.

**Why it is here:** Release zip and build steps, tuning mode exposing every Jev answer per item, precise account of what leaves the browser, headless smoke test, and lint-enforced module boundaries with tests.

**Know before you use it:** No screenshots or accuracy numbers, and the README says the Hacker News recipes are not yet tuned against real data.

<sub>MIT · TypeScript</sub>

- [Bewinxed/jevgpt](https://github.com/Bewinxed/jevgpt) **(notable)** - Chat REPL that decodes replies one word at a time by running a 20,000-word vocabulary through bucketed Jev choice questions and a final run-off. <sub>MIT · TypeScript</sub>
- [djangobeatty/textured](https://github.com/djangobeatty/textured) **(notable)** - Browser synthesiser where Jev turns a typed sound description into typed judgments that code maps onto synth parameters. <sub>MIT · TypeScript · [live](https://textured.fyi/)</sub>
- [Code-Forge-AU/jev-llm](https://github.com/Code-Forge-AU/jev-llm) **(notable)** - Text generator built only on Jev: picks one word per round trip from vocabulary split across 255-option Choice questions, with CLI, web chat and bench script. <sub>no license · Python</sub>
- [keltokhy/jlink](https://github.com/keltokhy/jlink) **(notable)** - Record linkage for researchers: state the match rule in English, Jev returns a match probability per candidate pair; Python, CLI, Stata and R. <sub>MIT · Python</sub>
- [dg-coreylweathers/jev-voice-agent](https://github.com/dg-coreylweathers/jev-voice-agent) **(notable)** - Realtime voice agent with no LLM: Deepgram Flux ends the turn, Jev picks a pre-written reply, Flux TTS speaks it; offline replay of five scenarios. <sub>MIT · TypeScript</sub>
- [dy-ma/jev-world](https://github.com/dy-ma/jev-world) **(notable)** - Web demo that asks Jev land-or-water for each map coordinate and replays the recorded responses, with throughput and latency tables per resolution. <sub>no license · TypeScript · [live](https://jev-world.vercel.app)</sub>
- [kyotofin/tax-doc-classifier](https://github.com/kyotofin/tax-doc-classifier) **(notable)** - TypeScript library classifying a tax document page into its IRS form and page kind with Jev, evaluated on 261 forms with a reproducible eval. <sub>Apache-2.0 · TypeScript</sub>
- [misbahsy/doc-router](https://github.com/misbahsy/doc-router) **(notable)** - Rust tool that judges per PDF page whether OCR is needed, extracts text pages locally and sends only the rest to an OCR provider. <sub>MIT · Rust</sub>
- [ohernandezdev/jevmod](https://github.com/ohernandezdev/jevmod) **(notable)** - Moderation toolkit giving per-category probabilities for messages, with Discord, Telegram and Reddit bots, CLI, HTTP API, MCP server and a benchmark. <sub>MIT · Python · [live](https://jevmod.dev)</sub>
- [RshaCuDeVidro/jev-recon](https://github.com/RshaCuDeVidro/jev-recon) **(notable)** - Subdomain triage CLI that asks Jev seven typed questions per asset and ranks with weighted Python arithmetic; includes cache, mock server and benchmark. <sub>no license · Python</sub>
- [TPAteeq/tocsin](https://github.com/TPAteeq/tocsin) **(notable)** - Rust log triage that masks and Drain-groups lines, asks Jev four questions once per new pattern and routes to page, ticket or log, with cost figures. <sub>MIT · Rust · [live](https://tpateeq.github.io/tocsin/)</sub>
- [vishesh-baghel/typesafe](https://github.com/vishesh-baghel/typesafe) **(notable)** - Hacker News front page scored by Jev on six dimensions and re-ranked client-side with sliders, with experiments that changed the design documented. <sub>no license · TypeScript · [live](https://upweight.vercel.app)</sub>
- [jarrodwatts/jev-trader](https://github.com/jarrodwatts/jev-trader) - Bun bot that asks Jev buy-or-sell every Monad block and posts a post-only limit order on the Kuru MON-USDC book, streaming each block over SSE. <sub>MIT · TypeScript · [live](https://jev-trader-production.up.railway.app)</sub>
- [MillionSend/millionsend](https://github.com/MillionSend/millionsend) - Open-source Resend-compatible email platform on AWS SES with an optional Jev judge that monitors outbound content after sending. <sub>AGPL-3.0 · TypeScript · [live](https://millionsend.com)</sub>
- [rokcso/bluenoise](https://github.com/rokcso/bluenoise) - Browser extension that filters noisy X replies with local rules, plus an opt-in second pass that asks Jev about replies no rule matched. <sub>MIT · TypeScript · [live](https://chrome.google.com/webstore/detail/ponbeiihcconklnlphjcnbfkghnimpid)</sub>
- [realZachi/typesafe-adblock](https://github.com/realZachi/typesafe-adblock) - Chrome MV3 extension that finds ad-shaped DOM elements in code, asks Jev one Noul per candidate in a batch, and removes those above a threshold. <sub>MIT · JavaScript</sub>
- [trungdq88/youtube-sponsor-detection](https://github.com/trungdq88/youtube-sponsor-detection) - Chrome extension and web app that find YouTube sponsor reads from captions or live audio with Jev and skip them above a confidence threshold. <sub>no license · JavaScript</sub>
- [superagents-lab/jev-search](https://github.com/superagents-lab/jev-search) - Web search app where Jev picks sources, time range and query terms, then scores each Search1API result for relevance; links only, no generated answers. <sub>MIT · TypeScript · [live](https://jev.s1.dev)</sub>
- [mrnugget/jev-shell-history](https://github.com/mrnugget/jev-shell-history) - zsh plugin showing fish-style autosuggestions by asking Jev which of the last 100 history entries the typed input is completing. <sub>no license · TypeScript</sub>
- [brainstormity/Jev-Moderation-Bot](https://github.com/brainstormity/Jev-Moderation-Bot) - Discord moderation bot that uses Jev to flag spam and scam links, escalates penalties per offense, profiles members, and reuses pardoned messages as examples. <sub>no license · Python</sub>
- [devanshbatham/commit-miner](https://github.com/devanshbatham/commit-miner) - Rust CLI that scans Git history and classifies each commit with Jev as bug fix, security fix with CWE, or change type, exporting HTML or CSV reports. <sub>no license · Rust</sub>
- [quantskills/QuantStudio](https://github.com/quantskills/QuantStudio) - Local quant research workbench whose futures paper-trading page uses Jev to watch the market and propose trade plans the user must confirm. <sub>GPL-3.0 · JavaScript · [live](https://www.quantskills.ai/)</sub>
- [ellipsis-dev/blink](https://github.com/ellipsis-dev/blink) - Bun CLI that finds a file for a natural-language query by having Jev score file and folder names and sending weighted walkers down the directory tree. <sub>no license · TypeScript</sub>
- [iamadi11/mcp-ui-poc](https://github.com/iamadi11/mcp-ui-poc) - Chat studio that turns a message and API URL into an embeddable widget, with Jev making the layout decisions and an LLM used only at low confidence. <sub>MIT · JavaScript · [live](https://mcp-ui-poc.vercel.app/)</sub>
- [zadescoxp/Jev-Trades](https://github.com/zadescoxp/Jev-Trades) - Next.js dashboard that streams one-minute crypto candles, sends indicator states to Jev and applies its decisions to a simulated paper portfolio. <sub>Apache-2.0 · Python · [live](https://jevtrades.zadescoxp.com)</sub>
- [AboveColin/HA-Jev](https://github.com/AboveColin/HA-Jev) - Home Assistant integration that turns Jev questions about entities into sensors and actions, adds an Assist agent and tracks daily token spend and budget. <sub>MIT · Python</sub>
- [BunsDev/typesafe-ai-playground](https://github.com/BunsDev/typesafe-ai-playground) - Next.js playground with 110 editable Jev examples, A/B input comparison, routing and extraction demos, games and simulations. <sub>MIT · TypeScript · [live](https://typesafe-ai-playground.vercel.app)</sub>
- [iomiras/sponsor-skipper](https://github.com/iomiras/sponsor-skipper) - Chrome MV3 extension that classifies YouTube caption segments with Jev ahead of playback and skips or offers to skip sponsor reads. <sub>no license · JavaScript</sub>
- [GiesN/typesafe-jev-workflow](https://github.com/GiesN/typesafe-jev-workflow) - Small async LangGraph workflow that classifies mocked emails as invoice or general with a Jev Choice and routes them, with offline tests. <sub>no license · Python</sub>
- [AIsa-team/worth-replying](https://github.com/AIsa-team/worth-replying) - Web app that profiles a domain, searches X through AIsa and has Jev answer five typed questions per tweet to queue, flag or archive reply candidates. <sub>MIT · TypeScript · [live](https://worth-replying.aisa.one)</sub>
- [andrelandgraf/rate-my-pricing](https://github.com/andrelandgraf/rate-my-pricing) - Web app that scores pricing pages for clarity via an LLM agent on Neon Functions, with a fail-open Jev QA gate before a rating is listed. <sub>no license · TypeScript</sub>
- [andrelandgraf/safer-with-jev](https://github.com/andrelandgraf/safer-with-jev) - Public HTTP gate where Jev inspects a request body for prompt injection or unsafe images and replies, then optionally forwards it to a target URL. <sub>no license · TypeScript · [live](https://safer-with-jev.com)</sub>
- [aowang-ai/jev-trade](https://github.com/aowang-ai/jev-trade) - Hyperliquid trading bot with five per-coin sleeves where Jev picks side and open/close/hold each tick; defaults to dry run with a Next.js dashboard. <sub>no license · TypeScript · [live](https://jev-trade.com)</sub>
- [av/naiou](https://github.com/av/naiou) - Terminal yes/no oracle with a 3D visualization that can answer by sending the input to Jev as a single Noul question. <sub>MIT · TypeScript</sub>
- [cocktailpeanut/jevthoven](https://github.com/cocktailpeanut/jevthoven) - Prompt-to-MIDI studio where each plan, harmony and bar pattern is one Jev Choice rendered to notes by code, with piano-roll editing and MIDI export. <sub>no license · TypeScript</sub>
- [frostney/clean-code-review](https://github.com/frostney/clean-code-review) - Next.js app that judges each file of a GitHub PR against Clean Code questions with Jev, then has an LLM write a short review; also served over MCP. <sub>MIT · TypeScript · [live](https://clean-code-review.vercel.app)</sub>
- [mkotlikov/jev-grug](https://github.com/mkotlikov/jev-grug) - Chat toy that makes Jev reply by repeatedly choosing the next word from a small caveman vocabulary, with a mock fallback when no key is set. <sub>MIT · TypeScript · [live](https://jev-grug-chat.mkotlikov.chatgpt.site/)</sub>
- [raihankhan-rk/diffjury](https://github.com/raihankhan-rk/diffjury) - Next.js app that fetches a public GitHub PR and asks Jev nine typed questions in one call to show merge risk, review depth and a verdict. <sub>no license · TypeScript</sub>
- [0xtrou/yggdrasight](https://github.com/0xtrou/yggdrasight) - Crypto research terminal whose multi-agent classification and synthesis layers run as typed Jev judgments over discovery output. <sub>no license · TypeScript · [live](https://yggdrasight.com/)</sub>
- [AlbionaHoti/refgarden](https://github.com/AlbionaHoti/refgarden) - 3D gallery of references from The Met, NASA and Cosmos where Jev chooses search phrases and highlights items from their metadata. <sub>MIT · TypeScript · [live](https://jev-curator.vercel.app)</sub>
- [croll83/jarvis](https://github.com/croll83/jarvis) - Voice and Telegram smart-home assistant that routes each command with one Jev call for intent, action, entity and injection, falling back to local Qwen. <sub>MIT · Python</sub>
- [drewling/zero](https://github.com/drewling/zero) - macOS menu-bar app that runs each morning, has Jev judge which Gmail threads are still open loops and reversibly archives the rest via label swaps. <sub>AGPL-3.0 · Python</sub>
- [Foadsf/jev-for-engineers](https://github.com/Foadsf/jev-for-engineers) - Eight zero-dependency Python examples applying Jev to engineering work such as FEM log triage, DFM screening and BOM line matching, all run against the live API. <sub>MIT · Python</sub>
- [harshil1712/slidepilot](https://github.com/harshil1712/slidepilot) - Slidev addon plus Cloudflare Worker that transcribes the presenter and asks Jev whether the slide's point is complete before auto-advancing. <sub>MIT · TypeScript</sub>
- [haseeb-heaven/jev-system-one](https://github.com/haseeb-heaven/jev-system-one) - Terminal UI where a LangGraph pipeline has Jev set response policy and review drafts while OpenAI writes them, shown beside a decision report. <sub>MIT · Python</sub>
- [hellogumbo/should-ai-kill-us-all](https://github.com/hellogumbo/should-ai-kill-us-all) - Cloudflare Pages site that feeds daily odd-news and AI headlines to Jev every ten minutes and shows its verdict, doom score and raw request. <sub>CC0-1.0 · JavaScript · [live](https://shouldaikillusall.com)</sub>
- [manifoldor/xtags](https://github.com/manifoldor/xtags) - Chrome extension and userscript that labels each X timeline post with Jev-judged intent plus rage-bait, synthetic and undisclosed-ad flags. <sub>MIT · JavaScript</sub>
- [nickthompson480/typesafe-ai-playground](https://github.com/nickthompson480/typesafe-ai-playground) - Local no-dependency Python server and web UI with 110 editable Jev examples in 22 categories, including 41 A/B prompt comparisons. <sub>MIT · JavaScript</sub>
- [nternet-company/hater](https://github.com/nternet-company/hater) - Firefox/Chrome extension that asks Jev on every keystroke which reaction-cat meme fits your X draft, with an editable memes.json. <sub>MIT · JavaScript</sub>
- [reycn/smart-switch](https://github.com/reycn/smart-switch) - macOS window switcher that on a hotkey sends recent app-switch history to Jev as one choice question and activates the predicted app, with a 1 s fallback. <sub>AGPL-3.0 · Swift</sub>
- [rishi-raj-jain/pg-redact](https://github.com/rishi-raj-jain/pg-redact) - Next.js and Neon Postgres demo where Jev labels PII spans in support messages and a redact() SQL function masks them by viewer role. <sub>no license · TypeScript · [live](https://pg-redact.vercel.app)</sub>
- [sosopop/jev_stock](https://github.com/sosopop/jev_stock) - Python pipeline that builds a past-only state for a Hong Kong stock, asks Jev for an up/flat/down forecast and renders an HTML report, with stated caveats. <sub>no license · Python</sub>
- [sriganesh/jevibe-check](https://github.com/sriganesh/jevibe-check) - Chrome extension that labels tone of Bluesky posts and drafts with Jev, supports custom classifiers and blur or collapse filters, and tracks usage cost. <sub>MIT · JavaScript</sub>
- [the-data-sherpa/project_blackout](https://github.com/the-data-sherpa/project_blackout) - Local cybersecurity lab that simulates attacks on a synthetic company and replays how Jev's compromise probability and severity change as telemetry arrives. <sub>no license · TypeScript</sub>
- [unicodeveloper/jevocks](https://github.com/unicodeveloper/jevocks) - Stock terminal web app that gathers evidence with five parallel Valyu searches and has Jev estimate whether the price will be higher in 30 days. <sub>no license · TypeScript · [live](https://jevinik.up.railway.app)</sub>
- [vmendes90/jev-shield](https://github.com/vmendes90/jev-shield) - Manifest V3 Chrome extension that asks Jev whether feed cards are native ads and collapses them, alongside network rules and video-ad handling. <sub>MIT · TypeScript</sub>
- [0xnairb/research_desk](https://github.com/0xnairb/research_desk) - FastAPI demo that feeds yfinance profiles and headlines to Jev across five stages to rank trade ideas, with a tab showing each request. <sub>no license · Python</sub>
- [ai-suifeng/comment-jev-chrome](https://github.com/ai-suifeng/comment-jev-chrome) - Chrome extension that classifies Bilibili, Douyin, Xiaohongshu and YouTube comments as hostile, filler, idea or normal and scores hostility. <sub>no license · JavaScript</sub>
- [AkashPriyadarshii/jev-curate](https://github.com/AkashPriyadarshii/jev-curate) - Rust CLI with Python bindings that streams Parquet or JSONL rows through Jev question presets to split training data into kept and rejected sets. <sub>MIT · Rust</sub>
- [alxcrt/is-odd-jev](https://github.com/alxcrt/is-odd-jev) - Zero-dependency npm package and CLI that asks Jev whether a number is odd and returns the probability, documenting Vercel AI Gateway differences. <sub>no license · JavaScript</sub>
- [BunsDev/clarity-judge](https://github.com/BunsDev/clarity-judge) - Next.js app that checks writing for hedging, filler, passive voice and other named axes as separate Jev questions, with a no-key mock mode. <sub>no license · TypeScript · [live](https://judge.jev.works)</sub>
- [fernandoviac/judged](https://github.com/fernandoviac/judged) - Interactive terminal interface for asking Jev yes/no, choice and score questions about a context, runnable via npx, bunx or deno. <sub>no license · TypeScript</sub>
- [godie/just-another-job-application-tracker](https://github.com/godie/just-another-job-application-tracker) - Job application tracker that uses Jev server-side for email classification, email-to-application matching, fit scoring and CSV header mapping. <sub>MIT · TypeScript · [live](https://jajat.godieboy.com)</sub>
- [gtaras7/typesafe-jev](https://github.com/gtaras7/typesafe-jev) - Local CV screening workbench that asks Jev fixed typed questions per CV and re-scores stored answers instantly when the role policy changes. <sub>MIT · TypeScript</sub>
- [hemanth/tc39-atlas](https://github.com/hemanth/tc39-atlas) - Web explorer of TC39 proposals enriched by Jev with adoption path, cognitive overhead, motivation, web-compat risk and architectural signal judgments. <sub>no license · TypeScript</sub>
- [hemanth/traffic-guard](https://github.com/hemanth/traffic-guard) - Node and Python request gate for bot mitigation (header order, HMAC velocity tokens, PoW, honeypots) that optionally escalates to five Jev questions. <sub>no license · Python</sub>
- [Infrawrench/Jeeves](https://github.com/Infrawrench/Jeeves) - Rust Discord and Twitch moderation bot where admins write rules in plain English and Jev judges messages and strike history against them. <sub>MIT · Rust</sub>
- [JanOstrowka/typesafe-assist](https://github.com/JanOstrowka/typesafe-assist) - Home Assistant conversation agent that maps Assist commands to built-in intents with one Jev fan-out request and a fallback agent. <sub>no license · Python</sub>
- [jevbook/jevscan](https://github.com/jevbook/jevscan) - CLI, library and MCP server that scores an EVM token address as ape/watch/avoid with rug-risk and liquidity scores; local engine by default, Jev with a key. <sub>MIT · JavaScript</sub>
- [joevidev/ui-generator-instinct-jev](https://github.com/joevidev/ui-generator-instinct-jev) - Next.js demo where Jev picks and configures real shadcn/ui components from a free-text description using only Choice, Noul and Score answers. <sub>no license · TypeScript · [live](https://ui-generator-instinct-jev.vercel.app)</sub>
- [kesku/jev-freeform](https://github.com/kesku/jev-freeform) - Chat experiment that makes Jev produce text one character at a time by running a 98-option Choice over candidate next characters with branch search. <sub>no license · JavaScript</sub>
- [kitze/pagegrade](https://github.com/kitze/pagegrade) - WXT browser extension that grades sections of a web page for clarity, writing and on-page SEO using Jev. <sub>MIT · TypeScript</sub>
- [kt3k/jevchat](https://github.com/kt3k/jevchat) - Deno chat UI where Jev replies by choosing from fixed answer sets (yes/no, pirate, tabloid headlines) and picks the chat title from question fragments. <sub>no license · JavaScript · [live](https://jevchat.kt3k.deno.net)</sub>
- [LamplighterPaul/jev-piano](https://github.com/LamplighterPaul/jev-piano) - Web piano improviser: Jev chooses key, metre, tempo, the chord for every bar from an unfiltered 36-chord bank, melody shape and when the piece ends. <sub>MIT · TypeScript</sub>
- [Little-Planet-Labs/jev-playground](https://github.com/Little-Planet-Labs/jev-playground) - Next.js playground to paste a state, build a mix of noul, choice and score questions, and view the returned distributions and confidence from one request. <sub>no license · TypeScript · [live](https://jev-playground-zeta.vercel.app)</sub>
- [markjaquith/typesafe-ai-playground](https://github.com/markjaquith/typesafe-ai-playground) - Rust CLI of Jev experiments: PHI detection over files, Tree-sitter code-comment review, tone analysis and business/occupation classification. <sub>MIT · Rust</sub>
- [MartinSWDev/gen-ui](https://github.com/MartinSWDev/gen-ui) - Web app where one Jev call picks a shadcn/ui display and field bindings for pasted or live JSON, timing Jev latency with p50/p95. <sub>no license · TypeScript · [live](https://gen-ui-wheat.vercel.app)</sub>
- [nmokaria27/job-scraper-bot](https://github.com/nmokaria27/job-scraper-bot) - Discord job-posting bot on GitHub Actions with an optional Jev second pass that scores surviving jobs so the 25-slot cap posts the best matches. <sub>no license · Python</sub>
- [NorbertBodziony/guard-jev](https://github.com/NorbertBodziony/guard-jev) - Text moderation demo: one systemOne call screens 7 Noul hazards plus a severity Score, and code applies strict or permissive policy thresholds. <sub>no license · TypeScript</sub>
- [onecuriousmindset/sweep](https://github.com/onecuriousmindset/sweep) - Chrome extension that blurs or removes posts on X, Reddit, LinkedIn and Hacker News matching plain-word Hide or Show-only rules, with your own key. <sub>MIT · JavaScript</sub>
- [RafalWilinski/vibecheck](https://github.com/RafalWilinski/vibecheck) - Chrome extension that scores a draft X post on virality, clarity, ragebait, regret risk and more under the composer, with editable JSON rubrics. <sub>no license · JavaScript</sub>
- [rivianpratama/JevPixelArt](https://github.com/rivianpratama/JevPixelArt) - Web app that draws pixel art by asking Jev one Score question per colour channel per pixel and painting the canvas as answers arrive. <sub>no license · JavaScript · [live](https://jevpixel.vercel.app)</sub>
- [rthomas24/jev-realtime-trading](https://github.com/rthomas24/jev-realtime-trading) - Electron paper-trading app where Jev calls up/down/flat on live Alpaca or Coinbase prices every second and the app enforces stops and books trades. <sub>MIT · TypeScript</sub>
- [russellromney/jevons](https://github.com/russellromney/jevons) - Dry-run MON trading research bot that uses Jev as a market-state sensor while deterministic code picks strategy, checks costs and emits paper orders. <sub>no license · TypeScript · [live](https://jevons.fly.dev/)</sub>
- [sstehniy/jev-calculator](https://github.com/sstehniy/jev-calculator) - iOS 6-style calculator whose results come from Jev evaluation steps streamed from a Bun server, with a lifetime API budget. <sub>no license · TypeScript · [live](https://jev-calculator.vercel.app)</sub>
- [svmanth/jmarket](https://github.com/svmanth/jmarket) - Manifest V3 Chrome extension that adds a Jev probability line under each Polymarket card without sending the market price to the model. <sub>MIT · JavaScript</sub>
- [TanayPadar/gpt-vs-jev](https://github.com/TanayPadar/gpt-vs-jev) - Next.js demo that sends the same short input to GPT and to Jev and shows generated text beside three Noul probabilities. <sub>MIT · TypeScript · [live](https://gptvsjev.vercel.app)</sub>
- [TheOnlyArtz/TheOnlyArtz.github.io](https://github.com/TheOnlyArtz/TheOnlyArtz.github.io) - Hebrew RTL React app that ranks Knesset party lists against a free-text ideology by sending full manifestos as Choice criteria via a Supabase function. <sub>no license · JavaScript · [live](https://theonlyartz.github.io/)</sub>
- [tylerjharden/harden-jev-decides](https://github.com/tylerjharden/harden-jev-decides) - Next.js decision board that sends eleven stream-project ideas in one request and lets code gate and weight Jev's answers to pick a winner. <sub>no license · TypeScript · [live](https://harden-jev-decides.vercel.app)</sub>
- [unownone/jevsume](https://github.com/unownone/jevsume) - Resume review app on a Cloudflare Worker with D1 that runs typed questions for general or per-job scoring and stores every request and raw output. <sub>no license · TypeScript</sub>
- [WebGrga/btc-jev-signal](https://github.com/WebGrga/btc-jev-signal) - Non-trading experiment where Jev forecasts BTC higher/lower at 15m, 1h, 4h and day close from structured market state and code scores outcomes. <sub>no license · TypeScript · [live](https://lab.rokogrga.com/btc-jev)</sub>
- [zaferayan/jev-example](https://github.com/zaferayan/jev-example) - Small TypeScript ticket-triage example (Turkish README) with a script running the same task on Claude Opus and measured latency for both. <sub>no license · TypeScript</sub>
- [zampierid4p/n8n-nodes-typesafe](https://github.com/zampierid4p/n8n-nodes-typesafe) - n8n community node that sends a state and a set of Noul, Choice and Score questions in one request, with optional one output branch per question. <sub>MIT · TypeScript</sub>
- [0xSarnavo/potpie-doc-parser](https://github.com/0xSarnavo/potpie-doc-parser) - Extractive docs search over the Potpie docs: BM25 shortlist then one Jev call picks the answering block verbatim or reports it is not covered. <sub>no license · Python</sub>
- [adagora/try_pixelRAG_optional_BM25_hybrid_JEV](https://github.com/adagora/try_pixelRAG_optional_BM25_hybrid_JEV) - Visual PDF retrieval layer over PixelRAG with Jev modes for query expansion, chunk and page reranking, and an answerability score. <sub>no license · Python</sub>
- [adebmbng/jev-trade-prediction](https://github.com/adebmbng/jev-trade-prediction) - Mobile-first BTC/ETH dashboard with live Binance candles and indicators where Jev gives a long/short/wait or exit/wait call; places no orders. <sub>no license · TypeScript</sub>
- [adiun/clinical-trial-screener](https://github.com/adiun/clinical-trial-screener) - Local web app that screens about 500 synthetic clinical notes against editable trial criteria, one Jev call per note, streaming results with an eval drawer. <sub>no license · TypeScript</sub>
- [afanjul/jev-llm](https://github.com/afanjul/jev-llm) - Python toy that forces Jev to act as an autoregressive text generator by choosing each next word, character or code token from closed candidate lists. <sub>no license · Python</sub>
- [agupta01/jev-8-ball](https://github.com/agupta01/jev-8-ball) - Pixel-art magic 8 ball: a Modal-hosted FastAPI backend asks Jev nine Noul judgments per question and the static page shows the answer. <sub>MIT · Python · [live](https://www.arunavgupta.com/jev-8-ball/)</sub>
- [ai-suifeng/twitter-laji-fliter-chrome](https://github.com/ai-suifeng/twitter-laji-fliter-chrome) - Chrome extension that batches X/Twitter replies to Jev with two Noul questions each and hides porn-spam or abusive replies behind a clickable placeholder. <sub>no license · JavaScript</sub>
- [alex-sun-kuo/jev-consumer-research](https://github.com/alex-sun-kuo/jev-consumer-research) - Python notebooks and CLI recipes that score A/B messages against synthetic persona panels and analyze interview transcripts, with a fake-API test stub. <sub>no license · Jupyter Notebook</sub>
- [andwaller/jev-movie-rerank-demo](https://github.com/andwaller/jev-movie-rerank-demo) - Script that recalls candidate movies from a Neo4j graph with Cypher and reranks the shortlist in one request using a Score question per candidate. <sub>MIT · Python</sub>
- [ankitkapooor/autocode](https://github.com/ankitkapooor/autocode) - Orthopedic medical-coding platform where Jev validates extracted facts and selects codes from a published codebook, with shadow and primary engine modes. <sub>no license · Python · [live](https://orthocode.ankitkapoor.me)</sub>
- [armsteadj1/vibe-smart-router](https://github.com/armsteadj1/vibe-smart-router) - Node demo that scores five candidate payment paths per synthetic transaction, using Jev for feature discovery and per-transaction context under a code policy. <sub>MIT · JavaScript</sub>
- [aserjam100/filing-radar](https://github.com/aserjam100/filing-radar) - Live dashboard that polls SEC EDGAR for new 8-K filings and asks seven questions per filing on event type, impact, materiality and red flags. <sub>no license · Python</sub>
- [asfarsadewa/human-compiler](https://github.com/asfarsadewa/human-compiler) - Web app that lints emails and posts like a compiler: a lexer finds phrases, one request measures about 45 traits, rules emit rustc-style diagnostics. <sub>MIT · TypeScript · [live](https://human-compiler.asfarlab.fun)</sub>
- [AstrBotDevs/astrbot_plugin_reply_gate](https://github.com/AstrBotDevs/astrbot_plugin_reply_gate) - AstrBot plugin that decides per chat message whether it should reach the LLM at all and which message to reply to, using validated Choice probabilities. <sub>MIT · Python</sub>
- [awun8191/jev-resume-analyzer](https://github.com/awun8191/jev-resume-analyzer) - React and FastAPI app that reviews an uploaded CV, optionally against a job posting, in one batched request and shows each question's probabilities. <sub>no license · Python</sub>
- [Ayush0054/metis](https://github.com/Ayush0054/metis) - Python library, CLI and reusable GitHub Action that classifies new issues, suggests an existing label and asks for missing details. <sub>MIT · Python</sub>
- [beapps-tech/triaz-pozadavku](https://github.com/beapps-tech/triaz-pozadavku) - Czech demo that triages customer change requests with 22 typed judgments and code rules deciding agent, clarify, split or developer, showing each weight. <sub>no license · JavaScript</sub>
- [blackopsrepl/jev-team-calendar](https://github.com/blackopsrepl/jev-team-calendar) - Local web app that reads a folder of resumes, has Jev estimate per-skill evidence for a project, then a constraint solver schedules the team week. <sub>Apache-2.0 · Rust</sub>
- [box-community/box-jev-incident-triage](https://github.com/box-community/box-jev-incident-triage) - Demo that pulls a Box PDF as Markdown, asks incident type, severity and escalation, applies a code policy and writes the result back as Box metadata. <sub>no license · Python</sub>
- [BradMyrick/Jev-Rug-Checker](https://github.com/BradMyrick/Jev-Rug-Checker) - Single-file EVM token screener that pulls GoPlus and DexScreener data, checks hard facts in code and asks Jev the fuzzy ones for a PASS/CAUTION/AVOID. <sub>MIT · Python</sub>
- [brandonbryant12/transcript-scorecard](https://github.com/brandonbryant12/transcript-scorecard) - Support-call scoring demo that replays a transcript turn by turn and rescores a weighted scorecard on each turn, storing evidence and latency in SQLite. <sub>no license · TypeScript</sub>
- [BrendanH18/jev-lab](https://github.com/BrendanH18/jev-lab) - Six demo apps on one fictional coffee business (email shield, command dispatch, autopilot and more) plus a workbench, all making live calls. <sub>MIT · Python</sub>
- [brendenehlers/syntax-highlighting](https://github.com/brendenehlers/syntax-highlighting) - Rust web app that highlights any code with no grammar: splits it into BPE tokens and asks one Choice per token in a single request, capped at 440 tokens. <sub>no license · Rust</sub>
- [BrunooMoniz/polymarket-btc-5m-agent](https://github.com/BrunooMoniz/polymarket-btc-5m-agent) - Polymarket BTC 5-minute trading agent that prices in code and uses Jev as a veto and volatility-regime gate, with paper mode and shadow profiles. <sub>MIT · Python</sub>
- [bugkiwi/elons-job](https://github.com/bugkiwi/elons-job) - Chrome MV3 extension that hides sexual and solicitation replies on X status pages behind a restorable placeholder, with custom rules and a corpus benchmark. <sub>no license · JavaScript</sub>
- [cbetz/extremely-specific-council](https://github.com/cbetz/extremely-specific-council) - Web toy where twelve characters vote on your idea via one request of 36 questions covering vote, enthusiasm and confusion, with shareable result cards. <sub>MIT · TypeScript · [live](https://extremely-specific-council-five.vercel.app)</sub>
- [cbuctok/n8n-nodes-judgment](https://github.com/cbuctok/n8n-nodes-judgment) - n8n community node offering evaluate, decide, rank, rate, composite and yes/no operations over the System One API for workflow branching. <sub>MIT · TypeScript</sub>
- [cephalization/jev-triage](https://github.com/cephalization/jev-triage) - Multiplayer triage dashboard syncing GitHub issues and PRs into Postgres and Zero, where typed answers suggest next steps and human corrections feed later runs. <sub>MIT · TypeScript</sub>
- [Charlyhno-eng/jev-document-classification](https://github.com/Charlyhno-eng/jev-document-classification) - Local web app that sorts a folder's documents into category subfolders via AI Gateway, sending low-confidence ones to review with an audit and restore. <sub>MIT · TypeScript</sub>
- [chiragrohit/jev-extension](https://github.com/chiragrohit/jev-extension) - Chrome side-panel extension with a local Node server that asks whether the page answers a question, then scrolls to and highlights the passage. <sub>no license · JavaScript</sub>
- [chrisXchen/typesafe-cookie-consent](https://github.com/chrisXchen/typesafe-cookie-consent) - Chrome extension that detects cookie banners and popups, asks four questions about the text and buttons, and clicks the declining option; BYOK. <sub>MIT · TypeScript</sub>
- [chumputys/adjudge](https://github.com/chumputys/adjudge) - Chrome ad blocker without filter lists: batches unknown third-party hosts, sponsored blocks and popups for classification and caches verdicts as rules. <sub>no license · JavaScript</sub>
- [colinmcdermott/emoji-jev](https://github.com/colinmcdermott/emoji-jev) - Emoji autocomplete page that on each typing pause asks one Choice over up to 254 emojis plus emotion, mood, urgency and sarcasm questions. <sub>no license · TypeScript · [live](https://emoji-jev.whop.site)</sub>
- [dagmawibabi/jevclassifier](https://github.com/dagmawibabi/jevclassifier) - SvelteKit app that classifies Telegram Desktop JSON exports with custom questions and cost meters, plus a chat that picks words from a dictionary. <sub>no license · Svelte · [live](https://jevclassifier.vercel.app)</sub>
- [danfry1/jev-triage](https://github.com/danfry1/jev-triage) - GitHub Action that labels new issues from the repo's own labels, flags duplicates and spam in one request, with thresholds and a dry-run default. <sub>MIT · TypeScript</sub>
- [davext/classifier-wiki-race](https://github.com/davext/classifier-wiki-race) - Web app where Jev races between two Wikipedia articles by choosing one link per hop, showing state, questions, probabilities and timing. <sub>MIT · JavaScript</sub>
- [DevvGwardo/ghost-route](https://github.com/DevvGwardo/ghost-route) - Map app that overlays ALPR cameras and ranks OSRM driving routes by camera exposure, with Jev choosing the winner and a heuristic fallback. <sub>MIT · TypeScript</sub>
- [digitalnivuk97-ctrl/safenet](https://github.com/digitalnivuk97-ctrl/safenet) - Go terminal LAN monitor that scores devices with local rules, then blends in Jev threat verdicts and logs latency and agreement for comparison. <sub>GPL-3.0 · Go</sub>
- [distributedlabs/magic-8-ball](https://github.com/distributedlabs/magic-8-ball) - Next.js Magic 8 Ball that sends each question to Jev as one Choice over the twenty classic answers and shows the top pick. <sub>no license · TypeScript</sub>
- [DomMonte/n8n-nodes-typesafe-ai](https://github.com/DomMonte/n8n-nodes-typesafe-ai) - n8n community node exposing yes/no, choice and score questions so workflows can branch on the returned probabilities. <sub>MIT · TypeScript</sub>
- [dpshde/berean](https://github.com/dpshde/berean) - Web app that takes a claim, beam-searches the Berean Standard Bible with Jev Choice/Noul, and answers yes or no with the best supporting verses. <sub>MIT · TypeScript</sub>
- [ec812/typesafe-playground](https://github.com/ec812/typesafe-playground) - Next.js playground for building custom Choice/Score/Noul questions plus a stock-news signal analyzer, with results saved to local SQLite. <sub>no license · TypeScript</sub>
- [edsonayllon/jev-prototype](https://github.com/edsonayllon/jev-prototype) - Feed triage app that tags RSS, X or pasted posts by type, sentiment and novelty with six Jev questions, then ranks them with a formula in code. <sub>MIT · TypeScript</sub>
- [EdytaKucharska/ticket-quest](https://github.com/EdytaKucharska/ticket-quest) - Ticket triage demo that ranks a backlog by Cost of Delay from Jev scores, gates auto-routing on certainty and races a bring-your-own-key LLM. <sub>MIT · TypeScript · [live](https://ticket-quest-three.vercel.app)</sub>
- [EricKwong/call-scope](https://github.com/EricKwong/call-scope) - Windows Electron call companion that transcribes locally with Whisper and uses Jev to judge when a prepared question has been asked and answered. <sub>no license · JavaScript</sub>
- [EtienneLescot/jev-router](https://github.com/EtienneLescot/jev-router) - Static demo page where two Jev calls triage a support ticket and code picks the agent, model tier and reasoning depth, showing raw requests. <sub>MIT · HTML · [live](https://etiennelescot.github.io/jev-router/)</sub>
- [ferxalbs/aether-hold](https://github.com/ferxalbs/aether-hold) - Next.js pre-send checker that gives a draft post, email or support reply a SEND, REWRITE, HOLD or BLOCK verdict from one Jev request plus coded policy. <sub>no license · TypeScript</sub>
- [FindMalek/guesswork](https://github.com/FindMalek/guesswork) - zsh autosuggestion plugin that sends recent shell history to a model and shows the most likely command inline with its confidence score. <sub>MIT · TypeScript</sub>
- [frankied003/fraud-jev](https://github.com/frankied003/fraud-jev) - Next.js fraud control room demo that scores a stream of fictional payments with Jev and races the same batch against a Claude prompt. <sub>no license · TypeScript</sub>
- [fstandhartinger/auto-router-demo](https://github.com/fstandhartinger/auto-router-demo) - Public web playground for auto-model-router showing the Jev classification, per-model pricing, the routing decision and the streamed answer. <sub>MIT · Python · [live](https://whichmodel.app.mintapis.com)</sub>
- [g-h-miles/beatbox](https://github.com/g-h-miles/beatbox) - Browser beatbox-to-MIDI instrument that classifies drum hits with a local acoustic model plus Jev on acoustic measurements, with reported F1 scores. <sub>MIT · TypeScript</sub>
- [galigutta/jev-use-cases](https://github.com/galigutta/jev-use-cases) - Use-case map site where a Cloudflare Worker and GitHub Actions grade each proposed entry for novelty with Jev before Codex opens an auto-merged PR. <sub>no license · Python · [live](https://galigutta.github.io/jev-use-cases/)</sub>
- [gastonmira/typesafe-triage-demo](https://github.com/gastonmira/typesafe-triage-demo) - Spanish-language Next.js demo showing one systemOne call's intent, urgency and anger judgments beside the fixed code policy that decides routing. <sub>no license · TypeScript · [live](https://typesafe-triage-demo.vercel.app)</sub>
- [GhrezaKh74/JevTicktRouter](https://github.com/GhrezaKh74/JevTicktRouter) - .NET 10 and React 19 support-ticket triage for Persian and English where Jev answers five batched questions and .NET rules make the final call. <sub>no license · C#</sub>
- [Gildra-Foundation/news](https://github.com/Gildra-Foundation/news) - Telegram news bot for World of Warcraft that uses Jev to pre-filter RSS, Reddit and X items before an LLM fact-maps and writes the Russian post. <sub>no license · Python</sub>
- [gishi-yama/jev-demo](https://github.com/gishi-yama/jev-demo) - Three dependency-free Node demos judging Japanese text: intent triage with hidden-complaint detection, subjectivity, and per-word spoken/written register. <sub>no license · HTML</sub>
- [gzawadzki/jev-usecases](https://github.com/gzawadzki/jev-usecases) - Seven Python demos on Polish text, from app-review inbox and content guard to essay rubric scoring, each with measured counts or agreement. <sub>MIT · Python</sub>
- [haibt163/jev](https://github.com/haibt163/jev) - Playground web app with support routing, compare-and-choose and content triage modules where Jev judges and application rules decide. <sub>no license · TypeScript · [live](https://jev-eosin.vercel.app)</sub>
- [harukishimo/ewo_order](https://github.com/harukishimo/ewo_order) - Japanese painting-commission app on Next.js and Supabase where Jev extracts size, style and urgency from chat and code prices and queues the order. <sub>no license · TypeScript · [live](https://ewo-order.vercel.app)</sub>
- [hatif03/try-typesafe-app](https://github.com/hatif03/try-typesafe-app) - Two Next.js demos: Policy Jury flags one-sided clauses in a ToS URL, Agent Supply Jury screens npm package text for instruction-override attempts. <sub>no license · TypeScript · [live](https://try-typesafe-appsapp.vercel.app)</sub>
- [haydarsahin0/Jev](https://github.com/haydarsahin0/Jev) - GitHub Actions pipeline that scores new arXiv AI papers with Jev twice a day and publishes a ranked static site on GitHub Pages. <sub>no license · Python</sub>
- [hugo-alves/jev-router-playground](https://github.com/hugo-alves/jev-router-playground) - Static web playground where Jev picks a model from a pool of OpenRouter candidates and you compare its pick with the answer you judge best. <sub>MIT · JavaScript · [live](https://kvhx37ziab90c.space.minimax.io)</sub>
- [ibnuh/Flow.Launcher.Plugin.JevFileSearch](https://github.com/ibnuh/Flow.Launcher.Plugin.JevFileSearch) - Flow Launcher plugin for Windows that reranks fuzzy file and app matches by intent using one three-question Jev request per query. <sub>no license · C#</sub>
- [inematds/jev](https://github.com/inematds/jev) - Portuguese decision lab with ten example cases, request export, a cost calculator and a stdlib Python client; all shown answers are simulated. <sub>no license · Python · [live](https://inematds.github.io/jev/app/)</sub>
- [JacksonLee2285/retry-is-a-decision](https://github.com/JacksonLee2285/retry-is-a-decision) - Java reference implementation where Jev picks RETRY, WAIT, DLQ or ESCALATE from failure context, behind hard invariants and a confidence gate. <sub>MIT · Java</sub>
- [JacobLinCool/jev-paper-judge](https://github.com/JacobLinCool/jev-paper-judge) - Cloudflare Worker app that splits an uploaded PDF paper into passages and has Jev judge understandability and completeness per passage in parallel. <sub>MIT · TypeScript · [live](https://jev-paper-judge.jacob.workers.dev)</sub>
- [jagenaujagenau/ground-truth](https://github.com/jagenaujagenau/ground-truth) - Browser extension that rates political lean, piece type, topic and loaded language of the current article from one Jev call via a key-holding service. <sub>MIT · TypeScript · [live](https://groundtruth.click/)</sub>
- [jangya/jev-in-action](https://github.com/jangya/jev-in-action) - Four Express demos of Jev decisions: expense categorization, flight choice, appointment slot picking and routing a real MCP tool call. <sub>MIT · JavaScript · [live](https://jev-in-action-psi.vercel.app)</sub>
- [jasondotsetHacked/jev-discord-gate-v1](https://github.com/jasondotsetHacked/jev-discord-gate-v1) - AWS CDK Discord bot where Jev Noul questions decide whether the generative model should reply and which recent messages to include, with shadow mode. <sub>no license · JavaScript</sub>
- [jh1373/jev-search](https://github.com/jh1373/jev-search) - Obsidian plugin preview that searches a vault locally and reranks top results with Jev only after the user approves what is sent. <sub>MIT · TypeScript</sub>
- [jjjjuuudde/jev-ad-blocker](https://github.com/jjjjuuudde/jev-ad-blocker) - Chrome extension that describes rendered page elements to Jev in batches and hides the ones it is confident are ads, with popup review and cost display. <sub>MIT · JavaScript</sub>
- [JordiParraCrespo/typesafe-ai-trading-showcase](https://github.com/JordiParraCrespo/typesafe-ai-trading-showcase) - Web demo showing live BTC, ETH and XRP prices with a shared Jev buy/wait judgment built from 60 seconds of Coinbase trades; places no trades. <sub>no license · TypeScript · [live](https://typesafe-ai-trading-showcase.vercel.app)</sub>
- [Joshirod/Acervo](https://github.com/Joshirod/Acervo) - Desktop app that searches a local folder, ranks passages with Jev and reports when the answer is not there, with an optional OpenAI/Claude benchmark mode. <sub>MIT · TypeScript</sub>
- [jwallio/jev-trader](https://github.com/jwallio/jev-trader) - Bun bot that asks Jev buy or sell on the Kuru MON-USDC book every Monad block and posts a post-only limit order, with dry-run mode and an SSE feed. <sub>MIT · TypeScript · [live](https://jev-trader-production.up.railway.app)</sub>
- [jxucoder/mimicry](https://github.com/jxucoder/mimicry) - Local web app and Chrome extension that rewrites drafts in your voice with an OpenAI writer and Jev as the style and meaning judge in a bounded loop. <sub>no license · Python</sub>
- [kamesan1577/re-heitan](https://github.com/kamesan1577/re-heitan) - Chrome extension that hides or blurs abusive posts in the X timeline using batched Jev score and noul questions with local caching. <sub>no license · TypeScript</sub>
- [Kelp710/moderation-jev](https://github.com/Kelp710/moderation-jev) - Next.js pre-send chat checker that asks Jev four questions per keystroke pause and blocks or flags the message by thresholds in code. <sub>no license · TypeScript</sub>
- [kevin9327/jev-master](https://github.com/kevin9327/jev-master) - Python monorepo of small CLI apps (ticket routing, confidence gate, pitch scoring) that mix Choice, Score and Noul in one call and decide in code. <sub>MIT · Python</sub>
- [knowlet/jevlens](https://github.com/knowlet/jevlens) - MV3 Chrome extension that annotates articles, X and Threads posts with Jev decisions, adding local OCR and visual labels from post images as evidence. <sub>MIT · JavaScript</sub>
- [komikat/jev-bfs](https://github.com/komikat/jev-bfs) - CLI that finds a path between two Wikipedia articles by having Jev rank outgoing links in a beam search, with a live terminal display. <sub>MIT · Python</sub>
- [kortexa-ai/mappity](https://github.com/kortexa-ai/mappity) - Map app where a free-text wish is judged by Jev against hundreds of OpenStreetMap places and the likely matches light up. <sub>MIT · JavaScript · [live](https://kortexa-ai.github.io/mappity/)</sub>
- [kostysh/goblin-hr](https://github.com/kostysh/goblin-hr) - Web demo that scores six fantasy applicants with four typed Jev questions and builds a three-member party with weights in TypeScript. <sub>no license · TypeScript</sub>
- [Kush614/MLforge](https://github.com/Kush614/MLforge) - Hackathon ML loop that trains, evaluates, diagnoses from Weave traces and uses TypeSafe to pick one typed corrective move per round. <sub>no license · Python</sub>
- [kylemclaren/jevql](https://github.com/kylemclaren/jevql) - psql-style client for plain Postgres that evaluates jev() and jev_prob() predicates in SQL client-side, with explain and cost estimates. <sub>MIT · Go · [live](https://jevql.fly.dev/)</sub>
- [lainollll/lm-studio-typesafe-chat](https://github.com/lainollll/lm-studio-typesafe-chat) - Tkinter chat app where LM Studio writes replies and Jev classifies tone, triggers rewrites and suppresses redundant live video narration. <sub>no license · Python</sub>
- [LamplighterPaul/forma-system1-experiment](https://github.com/LamplighterPaul/forma-system1-experiment) - Web experiment where Jev picks layout, blocks and colours for a page or diagram and an optional small LLM only fills text slots. <sub>MIT · TypeScript · [live](https://forma-experiment.zammitpaul.com)</sub>
- [Le0C/jev-mechanic](https://github.com/Le0C/jev-mechanic) - Car workshop triage demo where Jev reads free-text answers, code walks a diagnostic flowchart, and tokens, cost and time are logged; 90 tests. <sub>no license · Python</sub>
- [LingXuanYin/jev-chat](https://github.com/LingXuanYin/jev-chat) - Chat experiment that assembles each reply word by word from dictionary candidates chosen by Jev, with an offline fixture mode. <sub>no license · Python · [live](https://cohub.live/ncyg191125/jev-chat/w/jev-chat)</sub>
- [linw1995/dify-plugin-typesafe-ai](https://github.com/linw1995/dify-plugin-typesafe-ai) - Dify tool plugin with a Yes/No node and a multi-question Evaluate node that expose Jev probabilities and a boolean decision to workflows. <sub>MIT · Python</sub>
- [LukasCaha/jev-theme](https://github.com/LukasCaha/jev-theme) - Maps a typed phrase onto a 42-color palette with one Jev Choice and draws color bands sized by probability. <sub>no license · JavaScript</sub>
- [luxus/ha-conversation-jev](https://github.com/luxus/ha-conversation-jev) - Home Assistant conversation agent that uses Jev to route an utterance to a fast light-control path or hand it off to a Grok agent. <sub>no license · Python</sub>
- [m0rphtail/triagedy](https://github.com/m0rphtail/triagedy) - Rust CLI filter that reads JSONL security alerts, asks five typed questions per alert via Jev or an OpenAI-compatible backend, and emits decisions. <sub>MIT · Rust</sub>
- [mahynotch/newsscore](https://github.com/mahynotch/newsscore) - Async Python library and CLI that fetches a ticker's weekly news from financial APIs, scores each article with Jev and aggregates one number. <sub>MIT · Python</sub>
- [makefinks/jev-feed-filter](https://github.com/makefinks/jev-feed-filter) - Chrome extension that blurs or collapses X and YouTube feed posts whose Jev filter probability exceeds a threshold, based on free-text guidance. <sub>MIT · TypeScript</sub>
- [maraichr/jev-triage](https://github.com/maraichr/jev-triage) - Case board that triages cross-border B2B trade cases (customs holds, short payments, sanctions hits) with Jev via OpenRouter, with a mock mode. <sub>MIT · JavaScript</sub>
- [MarissaFamularo/citation-verifier](https://github.com/MarissaFamularo/citation-verifier) - Browser tool that pairs each citing sentence in a manuscript with the cited paper, has Claude find a quote and Jev score support vs contradiction. <sub>MIT · JavaScript · [live](https://verify.papertrellis.com)</sub>
- [Michaelvasandani/J-Mail](https://github.com/Michaelvasandani/J-Mail) - Local read-only unified inbox for multiple Gmail accounts that labels each synced message with Jev category and needs-reply, deadline and payment flags. <sub>no license · TypeScript</sub>
- [milanterhes/ai-column-jev](https://github.com/milanterhes/ai-column-jev) - Web app that adds Jev-judged yes/no, category or score columns to an uploaded CSV, with low-confidence row review and export. <sub>no license · TypeScript</sub>
- [mohamedmenasy/job_posting_fit_scorer](https://github.com/mohamedmenasy/job_posting_fit_scorer) - Local job-posting evaluator: Jev extracts typed signals from a posting and a deterministic scorer produces an explainable 0-100 fit score. <sub>MIT · Python</sub>
- [mohannadize/jev-ielts-test](https://github.com/mohannadize/jev-ielts-test) - IELTS Writing Task 2 practice app that bands an essay with four Jev Score questions over the official descriptors plus three Noul checks. <sub>no license · TypeScript</sub>
- [MrDesjardins/jev-send-guard](https://github.com/MrDesjardins/jev-send-guard) - Background desktop agent that watches the focused text field in allowlisted apps and shows a popup if Jev finds the draft curt or lacking a clear ask. <sub>no license · Python</sub>
- [mttcnnng/jev-tsla-demo](https://github.com/mttcnnng/jev-tsla-demo) - Vanilla JS demo that puts Jev judgments between a TSLA moving-average rule and an explicit position policy, showing request and answers on screen. <sub>MIT · JavaScript</sub>
- [n-yokomachi/jev-dev](https://github.com/n-yokomachi/jev-dev) - Side-by-side viewer that has Jev and an LLM judge the same utterance into eight emotion axes and shows the divergence, latency and resulting replies. <sub>no license · TypeScript</sub>
- [nafisazizir/x-jev](https://github.com/nafisazizir/x-jev) - Chrome extension that badges X posts as worth it, thin or slop from one Jev Score via Vercel AI Gateway, with a labelled eval set for rubric edits. <sub>no license · TypeScript</sub>
- [narulaskaran/jev-data-questions](https://github.com/narulaskaran/jev-data-questions) - Playground where you upload a CSV or URL, draft a question and watch Jev classify every row into a live class-distribution chart. <sub>no license · TypeScript · [live](https://jev-gamecast.vercel.app)</sub>
- [neddes/sloppy-jevs-extension](https://github.com/neddes/sloppy-jevs-extension) - Manifest V3 Chrome extension that sends page and X-feed text to Jev as two Noul questions and blurs content scored as AI-written prose or ads. <sub>MIT · JavaScript</sub>
- [newuser7171/antivirus](https://github.com/newuser7171/antivirus) - Static file scanner that extracts entropy, strings and PE/ELF/Office/PDF features and asks Jev for threat verdicts and severity. <sub>no license · Python</sub>
- [ns2250225/nameType](https://github.com/ns2250225/nameType) - Static web app that has Jev pick a Pokemon primary and secondary type for any name via OpenRouter and renders a share card. <sub>no license · HTML · [live](https://801939cb.pinme.dev/)</sub>
- [Obrais-cloud/ticket-rerank](https://github.com/Obrais-cloud/ticket-rerank) - FastAPI service that gives each support ticket a Jev urgency Score and returns the batch sorted, with concurrency caps and retries. <sub>no license · Python</sub>
- [ojusave/seefood](https://github.com/ojusave/seefood) - Hotdog-or-not app: a local SqueezeNet labels the photo in a Render Workflow and Jev judges the text labels. <sub>no license · TypeScript · [live](https://seefood-6wov.onrender.com)</sub>
- [onehopeA10/jev-x-spam-filter](https://github.com/onehopeA10/jev-x-spam-filter) - Chrome extension that hides crypto-shill and porn spam replies under X posts using local rules first, then Jev via Vercel AI Gateway for unclear cases. <sub>no license · JavaScript</sub>
- [pavanmadiraju91/jev_art](https://github.com/pavanmadiraju91/jev_art) - Local web app that turns a typed phrase into moving 3D art by having Jev rate the mood of the words. <sub>no license · Python</sub>
- [pavy23/jev_typesafeai_test](https://github.com/pavy23/jev_typesafeai_test) - Local web playground for noul/choice/score requests plus a shipyard owner-comment triage sample with mock server tests, documented in Korean. <sub>no license · Python</sub>
- [pekth/draftpulse](https://github.com/pekth/draftpulse) - Live scorer for X post drafts that asks Jev for category, hook, share, dwell and slop scores and combines them with code-side weights. <sub>no license · TypeScript</sub>
- [Pimmetjeoss/tribe-crm-jev](https://github.com/Pimmetjeoss/tribe-crm-jev) - Lead-intake pilot for Tribe CRM where Jev judges unstructured lead messages and TypeScript handles lookups, thresholds, idempotency and dry-run write plans. <sub>no license · TypeScript</sub>
- [piyush97/focus-tube](https://github.com/piyush97/focus-tube) - Chrome and Firefox extension that hides YouTube Shorts and reveals only videos Jev rates as useful for learning, through a Cloudflare Worker. <sub>MIT · JavaScript</sub>
- [ponyo877/jev-realtime-brain-scanner](https://github.com/ponyo877/jev-realtime-brain-scanner) - Live 'brain map' of 53 kanji that reshuffles as you speak: on-device macOS speech recognition feeds a 55-question Jev call via OpenRouter, drawn in p5.js. <sub>no license · JavaScript</sub>
- [qwts/postlens](https://github.com/qwts/postlens) - Chrome/Brave extension adding a JEV Analyze button to X posts that shows eight Jev analysis dimensions inline. <sub>no license · JavaScript</sub>
- [ravi3594444/jev-agent1](https://github.com/ravi3594444/jev-agent1) - Feed and tender monitor that scores every incoming item with Jev, gates keep/review/drop on confidence, and builds a digest with a LangGraph chat agent. <sub>no license · Python</sub>
- [renatosousa/jev-trader](https://github.com/renatosousa/jev-trader) - News sentiment classifier and buy/sell/hold signal generator over MetaTrader5 data, calling Jev via Vercel AI Gateway, with a local dashboard. <sub>no license · Python</sub>
- [Rhyn0w0/Flashbang](https://github.com/Rhyn0w0/Flashbang) - Expo and Convex dating app where private comments on profiles are analysed by Jev through the Vercel AI SDK to refine suggested matches. <sub>no license · TypeScript</sub>
- [rivianpratama/JeVJ](https://github.com/rivianpratama/JeVJ) - Local music visualiser that downloads a track, runs DSP analysis, asks Jev how each passage feels and renders a cue timeline as smoke visuals. <sub>no license · TypeScript</sub>
- [robipop22/Jev-is-odd](https://github.com/robipop22/Jev-is-odd) - npm package that asks Jev whether an integer is odd and returns the answer with confidence, token usage and latency; validates input before calling. <sub>MIT · JavaScript</sub>
- [rolottr/x-jev-classifier](https://github.com/rolottr/x-jev-classifier) - Chrome extension that badges every X post with an archetype and verdict from about 15 Jev questions sent in one request. <sub>AGPL-3.0 · JavaScript</sub>
- [rubenvitt/cefr-loop](https://github.com/rubenvitt/cefr-loop) - Demo loop where Jev scores a German paragraph's CEFR level, Claude simplifies it, and Jev re-checks until target, stall or cap. <sub>no license · Python</sub>
- [sambhav/jev-explained](https://github.com/sambhav/jev-explained) - Static interactive guide explaining Jev to product people through scripted routing demos, an architecture comparison and an editable cost calculator. <sub>no license · HTML</sub>
- [sandra-arato/icon-matcher](https://github.com/sandra-arato/icon-matcher) - CLI that matches a UI section title to one of about 8,800 Hugeicons and Lucide icons by sharding them into parallel Jev Choice questions. <sub>MIT · TypeScript</sub>
- [sandra-arato/icon-matcher-ui](https://github.com/sandra-arato/icon-matcher-ui) - Web demo for icon-matcher showing the chosen icon, shard count, confidence and runner-ups, served through a rate-limited server-side key. <sub>MIT · TypeScript · [live](https://icon-matcher-ui.vercel.app)</sub>
- [santos-sanz/jev-audio-beeper](https://github.com/santos-sanz/jev-audio-beeper) - TypeScript proof of concept that scores word-timestamped Spanish transcripts for profanity with Jev and beeps the matching intervals via ffmpeg. <sub>no license · TypeScript</sub>
- [sethsaler/jevgram](https://github.com/sethsaler/jevgram) - AI-text detector that runs each sentence or paragraph through a battery of Jev evaluations and reports the percentage flagged; CLI and drag-and-drop web app. <sub>MIT · Python</sub>
- [sgaabdu4/capture](https://github.com/sgaabdu4/capture) - Mac voice diary that transcribes locally with Parakeet, has Jev split and file thoughts into groups, then saves approved items to Notion. <sub>MIT · Dart</sub>
- [Shifros/RageBot](https://github.com/Shifros/RageBot) - Next.js chatbot that uses Jev to select sarcastic canned replies and score the user's rage for a live meter. <sub>no license · TypeScript · [live](https://rage-bot-two.vercel.app)</sub>
- [shivam-raval96/multiagent-jev-monitor](https://github.com/shivam-raval96/multiagent-jev-monitor) - Local chatbot that streams an LLM reply while Jev scores the growing text on six hazard Noul questions every 900 ms and colours segments by category. <sub>no license · JavaScript</sub>
- [shivam2003-dev/typesafe-triage-guard](https://github.com/shivam2003-dev/typesafe-triage-guard) - Python CLI with three Jev pipelines for support-ticket triage, alert triage and a deploy-risk gate, sharing a reusable hazard-battery engine. <sub>MIT · Python</sub>
- [ShupingR/scam-shield](https://github.com/ShupingR/scam-shield) - Scam text checker combining code-extracted link signals with eleven Jev questions and a tunable weighted policy; includes a labeled-sample eval script. <sub>no license · TypeScript · [live](https://scam-shield-seven-ecru.vercel.app)</sub>
- [smammadov1994/Signal98](https://github.com/smammadov1994/Signal98) - Error-tracking SDK plus a Windows 98-styled monitor that has Jev judge each event as urgent, user-facing or novel to page or suppress it. <sub>no license · JavaScript</sub>
- [smasato/jev-jp-address](https://github.com/smasato/jev-jp-address) - CLI that normalizes messy Japanese addresses against the Japan Post KEN_ALL master, asking Jev a Choice only where rules cannot decide, and prints the postcode. <sub>no license · TypeScript</sub>
- [solrac149/typesafelicious](https://github.com/solrac149/typesafelicious) - Live text visualizer that asks Jev for intent, emotion, urgency and intensity in one request and drives particle colors and motion from the probabilities. <sub>no license · TypeScript</sub>
- [sora-33/jev-mail-sorter](https://github.com/sora-33/jev-mail-sorter) - Self-hosted Docker web app that classifies Gmail inbox mail with Jev, applies labels at confidence 0.80 or higher and queues the rest for review. <sub>MIT</sub>
- [spivi/cloudforge-jev](https://github.com/spivi/cloudforge-jev) - Sidecar that grades a student's cloud attack-path writeup against a cloudforge answer key using three Jev Nouls and a depth Score. <sub>Apache-2.0 · Python</sub>
- [Spykoninho/trading-bot-jev](https://github.com/Spykoninho/trading-bot-jev) - Paper-trading crypto bot on Binance prices where Jev answers closed questions about news and posts while a trend-following algorithm places orders. <sub>no license · TypeScript</sub>
- [stbenjam/jev-drums](https://github.com/stbenjam/jev-drums) - Browser drum machine that fills a 6x16 step pattern from 96 Jev choice questions per generation via OpenRouter, evolving on bar boundaries. <sub>no license · JavaScript</sub>
- [stbenjam/jev-eight-ball](https://github.com/stbenjam/jev-eight-ball) - Magic eight ball web toy where Jev picks one of the 20 classic answers through OpenRouter's Decisions endpoint, showing confidence and latency. <sub>no license · JavaScript</sub>
- [steventsao/jevzen](https://github.com/steventsao/jevzen) - Chrome extension that swaps X posts matching your plain-language rules for zen or cat photos based on Jev probabilities, with one-click reveal. <sub>MIT · TypeScript</sub>
- [SudhansuuRanjan/typesafe_xlabeller](https://github.com/SudhansuuRanjan/typesafe_xlabeller) - Browser extension plus Cloudflare Worker that labels X timeline posts as ragebait, spam, hidden ad and more, batching 20 posts into one Jev call. <sub>no license · JavaScript</sub>
- [syndicalt/winnow](https://github.com/syndicalt/winnow) - Browser SQL studio over four fixture tables where an English WHERE condition is scored per row by Jev for filter, rank, classify and score modes. <sub>no license · TypeScript</sub>
- [tanzeelak/house-agent](https://github.com/tanzeelak/house-agent) - WhatsApp house agent that classifies roommate messages with TypeSafe for intent and urgency, then logs requests and sublet leads to SQLite and Sheets. <sub>no license · Python</sub>
- [Tatuck/jev-boe-demo](https://github.com/Tatuck/jev-boe-demo) - Daily pipeline that scores each item of Spain's official gazette with Jev for relevance, 13 topics and a best paragraph, published as a static site. <sub>no license · TypeScript · [live](https://tatuck.github.io/jev-boe-demo/)</sub>
- [The-Little-AI-Company/callout](https://github.com/The-Little-AI-Company/callout) - Windows tray app that on a hotkey has Jev score selected text for manipulation signals and checks its claims against fetched sources. <sub>no license · TypeScript · [live](https://the-little-ai-company.github.io/callout/)</sub>
- [TheBous/lodgify-listener](https://github.com/TheBous/lodgify-listener) - Webhook server that triages Lodgify guest messages with Jev using property notes and thread history, notifying the owner on Telegram when needed. <sub>no license · TypeScript</sub>
- [thenewpotato/privacy-facts](https://github.com/thenewpotato/privacy-facts) - Web app that turns a privacy policy URL or text into a 14-question label with Jev answers, confidence and source excerpts. <sub>MIT · JavaScript</sub>
- [thenoahhein/jev-temporal-demo](https://github.com/thenoahhein/jev-temporal-demo) - Temporal workflow demo of an incident-response loop where Jev picks the next action as an Activity and the run survives retries and worker crashes. <sub>no license · TypeScript</sub>
- [thestrabusiness/typesafe-8ball](https://github.com/thestrabusiness/typesafe-8ball) - Magic 8-Ball CLI and web UI that maps a Jev Noul and Score to the 20 classic answers, with rate limiting and tests using a fake client. <sub>no license · TypeScript</sub>
- [thevibeworks/pagepilot](https://github.com/thevibeworks/pagepilot) - Browser extensions and a Node proxy where Jev votes on page text groups to author a reading spec that replays for 0 tokens, escalating to an LLM on failure. <sub>MIT · HTML</sub>
- [TKY-27/JevSlop](https://github.com/TKY-27/JevSlop) - Web app that fetches a public note.com article and rates it on eight writing-quality axes with Jev, computing a weighted Slop Score in code. <sub>MIT · TypeScript</sub>
- [toorop/veille-by-jev](https://github.com/toorop/veille-by-jev) - Nightly pipeline that collects Hacker News stories, triages them with typed Jev questions and has an LLM write a French Markdown digest. <sub>no license · Python</sub>
- [vertexcover-io/who-is-hiring](https://github.com/vertexcover-io/who-is-hiring) - Filterable board of HN Who is hiring posts, each labeled by 16 Jev Choice questions and rebuilt by a GitHub Action every 6 hours. <sub>no license · Python · [live](https://blog.vertexcover.io/who-is-hiring/)</sub>
- [vicpon/signals](https://github.com/vicpon/signals) - Dashboard giving a bullish/bearish/neutral signal per stock or crypto ticker from Jev judgments over news articles, shown beside an OpenAI comparison. <sub>no license · HTML · [live](https://signals-plum.vercel.app)</sub>
- [vkpdeveloper/mrsecret](https://github.com/vkpdeveloper/mrsecret) - Chrome extension that blurs secrets and PII on pages using regex detectors plus Jev classification of short snippets, with cached verdicts. <sub>no license · TypeScript</sub>
- [wadadanet/faq-jev-router](https://github.com/wadadanet/faq-jev-router) - Static bilingual FAQ demo that cascades Jev Choices from category to article or not-found, with a Cloudflare Worker proxy holding the key. <sub>MIT · JavaScript</sub>
- [Waxmell114514/jev-trade](https://github.com/Waxmell114514/jev-trade) - Simulated BTC/ETH trading loop that discretizes price features into words, asks Jev six typed questions per tick and runs a cost-aware execution simulator. <sub>no license · Python</sub>
- [Waxmell114514/x-feeder](https://github.com/Waxmell114514/x-feeder) - CLI that gathers Reddit, HN, news and RSS posts on an issue, has Jev classify stance per document, and reports per-source-tier consensus and divergence alerts. <sub>no license · Python</sub>
- [WebGrga/jev-board-lab](https://github.com/WebGrga/jev-board-lab) - Browser CSV workbench that runs up to 20 user-defined Noul/Choice/Score questions per row through a Cloudflare Worker proxy. <sub>no license · JavaScript</sub>
- [WeSecureYou/Jev-test](https://github.com/WeSecureYou/Jev-test) - Node CLI, REST API and web page that ask Jev for an occupation's AI layoff risk, trajectory and accountability need, with mock data when no key is set. <sub>no license · TypeScript · [live](https://jev-test.vercel.app)</sub>
- [willprout/magic-8-ball](https://github.com/willprout/magic-8-ball) - Magic 8 Ball web app where a Cloudflare Worker asks Jev one Choice over twenty replies and shows measured click-to-answer latency. <sub>no license · TypeScript · [live](https://willprout.github.io/magic-8-ball/)</sub>
- [windymelt/ddskk-jev](https://github.com/windymelt/ddskk-jev) - Emacs minor mode that reorders ddskk Japanese kana-kanji conversion candidates by Jev Choice probabilities from surrounding text. <sub>GPL-3.0 · Emacs Lisp</sub>
- [Wizhill05/typesafe-image-diffusion](https://github.com/Wizhill05/typesafe-image-diffusion) - Generates 16x16 pixel art by asking Jev 256 parallel Choice questions, one per pixel, then re-asking with 3x3 neighbourhoods as refinement passes. <sub>no license · HTML</sub>
- [wustep/jev-playground](https://github.com/wustep/jev-playground) - Web demos where Jev picks only enum labels for a music plan that code renders to sheet, audio and MIDI, plus a trolley-problem judge. <sub>no license · TypeScript · [live](https://jev-playground.vercel.app)</sub>
- [xmili233/Logra](https://github.com/xmili233/Logra) - Next.js platform where a local agent drafts forms and workflow graphs and published flows use Jev via OpenRouter for semantic branching. <sub>MIT · TypeScript</sub>
- [xshubhamg/twtry](https://github.com/xshubhamg/twtry) - Scheduled eve agent that scrapes HN, Reddit and dev.to, has Jev judge candidates, rewrites them with DeepSeek and queues 15 tweet slots. <sub>MIT · TypeScript</sub>
- [Yashilot/Jev-HA](https://github.com/Yashilot/Jev-HA) - Smart-home assistant pipeline where Jev handles routing, extraction and classification and a local Ollama LLM only answers questions. <sub>no license · Python</sub>
- [ybentlili/JevTest](https://github.com/ybentlili/JevTest) - Minimal customer-mail bot demo comparing a run with and without Jev: Jev classifies and verifies refunds, code applies thresholds, Claude writes. <sub>no license · Python</sub>
- [yonidavidson/subtext](https://github.com/yonidavidson/subtext) - Message bus where subscriptions are English sentences and Jev answers one Noul per subscription per message; local web demo with a mock judge. <sub>MIT · TypeScript</sub>
- [yutkat/github-star-organizer-jev](https://github.com/yutkat/github-star-organizer-jev) - Python tool and GitHub Actions workflow that classifies starred repos into existing GitHub Lists with Jev and can apply the assignments. <sub>MIT · Python</sub>
- [zsoXi/FeedGate](https://github.com/zsoXi/FeedGate) - Chrome extension that uses Jev judgments to reversibly collapse spam and unwanted ads in the X feed while keeping ordinary promotional posts. <sub>GPL-3.0 · JavaScript</sub>

## Official

From TypeSafe AI. Start here if you have not made a call yet.

### [skills](https://github.com/typesafe-ai/skills)

Official agent skill that teaches coding agents to design System One workflows, find current docs and compose typed judgments in code.

**Why it is here:** First-party repo with Claude Code plugin and skills.sh install commands and a linked SKILL.md.

**Know before you use it:** A single skill, and the README does not show what it contains.

<sub>MIT</sub>

### [typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python)

Official Python client for the TypeSafe API: `client.system_one(state=..., questions=...)` with typed question classes such as Choice.

**Why it is here:** First-party repo with a `uv add typesafe-sdk` install line and a runnable Choice quickstart.

**Know before you use it:** README is minimal and defers everything else to the hosted docs.

<sub>MIT · Python</sub>

### [typesafe-sdk-js](https://github.com/typesafe-ai/typesafe-sdk-js)

Official TypeScript/JavaScript client for the System One endpoint, with answer types inferred from the questions passed in.

**Why it is here:** Published npm package with an install command and a complete typed `systemOne` example; ships ESM, CommonJS and declarations.

**Know before you use it:** README is minimal and points to source files for options and defaults.

<sub>MIT · TypeScript</sub>

### [system-one-adapter-python](https://github.com/typesafe-ai/system-one-adapter-python)

Official Python client with the same system_one API as typesafe_sdk but answered by OpenAI or Anthropic models, for comparing Jev against an LLM.

**Why it is here:** pip install extras, sync and async usage code, an options table, and per-attempt debug records that can be replayed.

**Know before you use it:** LLM-produced probabilities are not calibrated, and the README gives no comparison results of its own.

<sub>MIT · Python</sub>

## SDKs and integrations

Clients and adapters beyond the official Python and JS SDKs.

### [ai-cli](https://github.com/vercel-labs/ai-cli)

Vercel AI SDK terminal CLI whose `ai evaluate` command asks Boolean, Choice and Score questions over stdin, with Jev as the default evaluation model.

**Why it is here:** npm install, a fully specified evaluate interface (flags, question-file schema, output shape, exit codes, jq gating example) and explicit notes on Jev's numeric and date limits.

**Know before you use it:** Jev is one command in a general generation CLI and is reached through Vercel AI Gateway, so it needs a gateway key rather than a TypeSafe key.

<sub>no license · TypeScript · [live](https://ai-cli.dev/docs/evaluate)</sub>

### [advocaat](https://github.com/pithings/advocaat)

TypeScript client with tagged-template helpers (ask.if, ask.choice, ask.switch, ask.score) that batch typed Jev questions and return typed answers.

**Why it is here:** Install command, extensive usage examples including the exact request JSON sent, a full options reference, and Vercel AI Gateway support with locally computed confidence.

**Know before you use it:** A convenience layer over the same endpoint the official SDK covers, with no retries and no tests mentioned in the README.

<sub>MIT · TypeScript</sub>

- [zaidmukaddam/cascade-search](https://github.com/zaidmukaddam/cascade-search) **(notable)** - Search-query parser where a 27K-parameter in-browser model tags each word with confidence and only low-confidence spans are escalated to Jev. <sub>MIT · TypeScript · [live](https://cascade.scira.ai)</sub>
- [EugeneBoondock/jevsql](https://github.com/EugeneBoondock/jevsql) **(notable)** - SQLite functions jev_noul, jev_choice and jev_score for filtering and ranking rows by meaning, with batching, a content-hash cache and a cost guard. <sub>MIT · JavaScript</sub>
- [WiktorB2004/llama-index-jev](https://github.com/WiktorB2004/llama-index-jev) **(notable)** - LlamaIndex reranker and router selectors backed by Jev Score and Choice, with BEIR nfcorpus and SciFact nDCG@5 gains reported with confidence intervals. <sub>MIT · Python · [live](https://wiktorb2004.github.io/llama-index-jev/)</sub>
- [Query-farm/vgi-typesafe](https://github.com/Query-farm/vgi-typesafe) **(notable)** - VGI worker exposing choice, noul and score as DuckDB table functions for LATERAL joins, with concurrent per-row requests and deduplicated values. <sub>MIT · Python · [live](https://query.farm/vgi/)</sub>
- [avshalomd/longjev](https://github.com/avshalomd/longjev) **(notable)** - Python wrapper that accepts states over the 32K limit by having Jev score chunks, keeping the best, then answering; ships evals of where it helps. <sub>MIT · Python</sub>
- [mattn/sqlite3-jev](https://github.com/mattn/sqlite3-jev) **(notable)** - SQLite loadable extension in C that adds jev_noul, jev_choice and jev_score SQL functions calling the System One API via libcurl. <sub>MIT · C</sub>
- [cequence-io/openai-scala-client](https://github.com/cequence-io/openai-scala-client) - Async Scala client for OpenAI and other LLM providers that now includes a TypeSafe Jev adapter. <sub>MIT · Scala</sub>
- [realZachi/pg-jev](https://github.com/realZachi/pg-jev) - PostgreSQL extension adding jev(), jev_prob(), jev_choice() and jev_score() SQL functions that judge rows in batched, cached Jev requests. <sub>no license · Python · [live](https://pgjev.com)</sub>
- [typesafeainate/dspy-typesafeify](https://github.com/typesafeainate/dspy-typesafeify) - Proof-of-concept DSPy fork with a decorator that sends bool, Literal and score output fields to Jev and leaves free-text fields to the LM. <sub>MIT · Python</sub>
- [yusukebe/hono-jev-router](https://github.com/yusukebe/hono-jev-router) - Experimental Hono router that matches requests to plain-language route descriptions using one Noul question per route in a single Jev call. <sub>MIT · TypeScript</sub>
- [jexp/neo4jev](https://github.com/jexp/neo4jev) - Python library, notebooks and Streamlit app that walk a Neo4j graph hop by hop, with Jev choosing the next relationship and beam search over its probabilities. <sub>MIT · Jupyter Notebook</sub>
- [kieranklaassen/ruby_llm-typesafe](https://github.com/kieranklaassen/ruby_llm-typesafe) - RubyLLM 2 provider that maps a noul/choice/score schema DSL onto with_schema and returns parsed Jev answers; rejects streaming and tools up front. <sub>MIT · Ruby</sub>
- [dannote/jev](https://github.com/dannote/jev) - Elixir library that treats Jev as a peer process: reply to it from a GenServer and pattern match on typed answers in handle_answer clauses. <sub>MIT · Elixir</sub>
- [Muvon/octolib](https://github.com/Muvon/octolib) - Rust library unifying 25+ AI providers that includes typed yes/no, choice and score evaluation through Jev, directly or via Cloudflare AI Gateway. <sub>Apache-2.0 · Rust · [live](https://octomind.run/product/octolib/)</sub>
- [Tangerg/typesafe-sdk-go](https://github.com/Tangerg/typesafe-sdk-go) - Go client for the System One API with typed Noul/Choice/Score questions and answer accessors, no third-party dependencies, plus a runnable demo. <sub>MIT · Go</sub>
- [Twister915/typesafe-ai](https://github.com/Twister915/typesafe-ai) - Rust crate for the System One API with typed Noul, Choice and Score results, async reqwest or blocking ureq backends and observable retries. <sub>Apache-2.0 · Rust</sub>
- [jomatsu/zod-jev](https://github.com/jomatsu/zod-jev) - Zod 4 add-on that attaches semantic rules to a schema, sends them to Jev in one request per parse and turns low probabilities into Zod issues, failing closed. <sub>MIT · TypeScript</sub>
- [giuliosmall/pg_typesafe](https://github.com/giuliosmall/pg_typesafe) - PostgreSQL 16/17 C extension exposing Noul, Choice and Score as SQL functions, with batched variants and a timed NYC 311 demo. <sub>MIT · C</sub>
- [saibimajdi/typesafeai-dotnet-sdk](https://github.com/saibimajdi/typesafeai-dotnet-sdk) - .NET client for the System One API with typed questions, retry and Retry-After handling, raw-JSON passthrough for unknown fields and AOT-clean annotations. <sub>MIT · C# · [live](https://saibimajdi.github.io/typesafeai-dotnet-sdk/)</sub>
- [ainame/swift-typesafe](https://github.com/ainame/swift-typesafe) - Unofficial Swift SDK mirroring the Python SDK, with a @QuestionSet macro that generates typed Choice, Noul and Score answers. <sub>MIT · Swift</sub>
- [flitsinc/go-llms](https://github.com/flitsinc/go-llms) - Go LLM library for Anthropic, Google and OpenAI that also supports Jev typed judgments driven by a JSON output schema. <sub>MIT · Go</sub>
- [inanna-malick/jev-dsl](https://github.com/inanna-malick/jev-dsl) - Haskell DSL where a packet of labelled Jev questions has an inferred type, renders to request JSON and returns answers as typed records. <sub>MIT · Haskell</sub>
- [joshmn/typesafe-sdk](https://github.com/joshmn/typesafe-sdk) - Ruby gem client for the System One API with Noul, Choice and Score question classes and typed response accessors. <sub>MIT · Ruby</sub>
- [danvega/hello-jev-java](https://github.com/danvega/hello-jev-java) - Single-file Java 25 example that posts one support message with a noul, a choice and a score question using only the JDK HTTP client. <sub>no license · Java</sub>
- [docxology/daf-jev](https://github.com/docxology/daf-jev) - Python Jev client with question builders, confidence gates, a concurrent batch evaluator, usage ledger, calibration statistics, CLI and MCP server. <sub>MIT · Python</sub>
- [gilljon/typesafe-ai-rs](https://github.com/gilljon/typesafe-ai-rs) - Async and blocking Rust client for the System One API with typed questions, retries, cancellation and parity notes against the official SDKs. <sub>MIT · Rust · [live](https://docs.rs/typesafe-ai-rs)</sub>
- [mateonunez/jod](https://github.com/mateonunez/jod) - TypeScript library binding a Zod or Standard Schema state and named questions into one object that validates locally then returns typed Jev answers. <sub>MIT · TypeScript</sub>
- [nitoba/questions](https://github.com/nitoba/questions) - TypeScript library for typed decisions from Zod schemas or question batches over Jev, Vercel or generative models, with confidence gates, retries and replay. <sub>MIT · TypeScript</sub>
- [2389-research/typesafe-go](https://github.com/2389-research/typesafe-go) - Zero-dependency Go client with generic question handles so each Noul, Choice or Score answer is read back with its own compile-time type. <sub>MIT · Go</sub>
- [alterhq/typesafe-sdk-swift](https://github.com/alterhq/typesafe-sdk-swift) - Dependency-free Swift 6 client for the TypeSafe API ported from the official SDKs, with bearer-token provider support for backend proxying. <sub>MIT · Swift</sub>
- [AntonioCoppe/jev-harness](https://github.com/AntonioCoppe/jev-harness) - TypeScript library wrapping Jev calls with an action policy, confidence gate, shadow mode, recipes and a fixture-replay eval CLI. <sub>MIT · TypeScript</sub>
- [Butochnikov/laravel-typesafe-jev](https://github.com/Butochnikov/laravel-typesafe-jev) - Laravel package adding auto-discovery, config, a facade, scoped DI and a recording test fake on top of the community PHP SDK for Jev. <sub>MIT · PHP</sub>
- [cole-gillespie/typesafe-go](https://github.com/cole-gillespie/typesafe-go) - Unofficial Go SDK with typed Choice/Score/Noul constructors and accessors, retries, context support and no third-party dependencies. <sub>MIT · Go</sub>
- [Hawxy/TypeSafeAI.Net](https://github.com/Hawxy/TypeSafeAI.Net) - .NET client with typed QuestionSet handles, enum-backed Choice, DI and retries, plus a Microsoft.Extensions.AI package for guardrail and routing middleware. <sub>Apache-2.0 · C#</sub>
- [hhhapz/typesafe-go](https://github.com/hhhapz/typesafe-go) - Go client for the System One endpoint with typed question structs, configurable retry policy and per-attempt timeouts. <sub>MIT · Go</sub>
- [InsaneArts/typesafe-sdk-swift](https://github.com/InsaneArts/typesafe-sdk-swift) - Dependency-free Swift package for the System One API with answer types inferred from the questions passed in. <sub>MIT · Swift</sub>
- [jamesward/zio-typesafe-ai](https://github.com/jamesward/zio-typesafe-ai) - Scala 3 ZIO client where questions go in a NamedTuple and answers come back with matching typed fields, with range-checked criteria and Probability types. <sub>Apache-2.0 · Scala</sub>
- [nshkrdotcom/typesafe_sdk](https://github.com/nshkrdotcom/typesafe_sdk) - Elixir SDK for the System One API with Choice, Score and Noul structs and typed response structs, published on Hex. <sub>MIT · Elixir</sub>
- [Premo-Cloud/typesafe-sdk-java](https://github.com/Premo-Cloud/typesafe-sdk-java) - Community Java 17 client on Maven Central mirroring the official SDK shape, with lambda configurers and a Spring Boot starter. <sub>MIT · Java</sub>
- [reachjalil/jev-tree](https://github.com/reachjalil/jev-tree) - npm library that walks a JSON taxonomy and calls Jev once per level so a choice can span more than the 255-option cap. <sub>MIT · TypeScript · [live](https://reachjalil.github.io/jev-tree/)</sub>
- [AboveColin/jevclient](https://github.com/AboveColin/jevclient) - Async Python client on PyPI with local validation of option and level limits and measured latency for 3 to 400 questions per call. <sub>MIT · Python</sub>
- [adtyavrdhn/pydantic-jev-examples](https://github.com/adtyavrdhn/pydantic-jev-examples) - One-file Pydantic AI examples using Jev as input guardrail, shell-command judge and game controller. <sub>no license · Python</sub>
- [Butochnikov/typesafe-sdk-php](https://github.com/Butochnikov/typesafe-sdk-php) - PHP 8.2 client for System One with typed Noul, Choice and Score DTOs, Guzzle-promise async calls, retries and PSR-3 logging. <sub>MIT · PHP</sub>
- [codeitlikemiley/typesafe-sdk-rust](https://github.com/codeitlikemiley/typesafe-sdk-rust) - Rust crate matching the Python SDK 0.6.0 contract, with async and blocking clients and an AGENTS.md for coding agents. <sub>MIT · Rust</sub>
- [colliber/duckdb-jev](https://github.com/colliber/duckdb-jev) - DuckDB extension whose jev_choice, jev_score, jev_noul and jev_ask functions return ENUM, DOUBLE and STRUCT columns typed from the criteria. <sub>MIT · C++</sub>
- [fgn/jevgo](https://github.com/fgn/jevgo) - Stdlib-only Go client with functional options, sentinel errors and slog, plus a separate Langfuse instrumentation module. <sub>MIT · Go</sub>
- [Gaurav-Gosain/jev-go](https://github.com/Gaurav-Gosain/jev-go) - Go client with YesNo, OneOf and Levels constructors and typed answer accessors for the System One API. <sub>MIT · Go</sub>
- [GenieRobot/typesafe-ai-rails](https://github.com/GenieRobot/typesafe-ai-rails) - Rails gem adding credentials config, persisted usage and cost telemetry, and database-backed confidence policies over the community Ruby SDK. <sub>MIT · Ruby</sub>
- [guillemus/jev-go](https://github.com/guillemus/jev-go) - Minimal unofficial Go client for the System One endpoint covering Noul, Choice, Score, structured inputs and model listing. <sub>no license · Go</sub>
- [hamakyo/jev-starter](https://github.com/hamakyo/jev-starter) - npm package and GitHub template layering decision contracts, confidence thresholds, fallbacks and evaluation on the official TypeScript SDK. <sub>MIT · TypeScript</sub>
- [jb2197/pydantic-jev](https://github.com/jb2197/pydantic-jev) - Compiles Pydantic Literal, Enum, float and bool fields into Jev Choice/Score/Noul questions, with a Pydantic Graph router example and tests. <sub>MIT · Python</sub>
- [JedimEmO/typesafe-client](https://github.com/JedimEmO/typesafe-client) - Async Rust client for the System One API with compile-time typed answer keys, request validation, retries and an in-memory fake for tests. <sub>Apache-2.0 · Rust</sub>
- [kgonia/typesafe-sdk-java](https://github.com/kgonia/typesafe-sdk-java) - Zero-dependency Java 21 client for the System One API with typed Noul, Choice and Score question builders and answer accessors. <sub>MIT · Java</sub>
- [latere-ai/typesafe-ai-go-sdk](https://github.com/latere-ai/typesafe-ai-go-sdk) - Stdlib-only unofficial Go client with typed Noul/Choice/Score questions, typed answer accessors and structured API errors. <sub>Apache-2.0 · Go</sub>
- [nola-lang/nola-typesafe-test](https://github.com/nola-lang/nola-typesafe-test) - Example ticket-triage project for the Nola language's typesafe() provider, mapping literal unions and booleans to Jev choice and yes/no questions. <sub>no license · TypeScript</sub>
- [qddegtya/qualm](https://github.com/qddegtya/qualm) - TypeScript library with tagged-template is/choice/score questions where every decision must handle an unsure branch at compile time; TypeSafe and Cloudflare. <sub>MIT · TypeScript</sub>
- [Stumble/jev-go](https://github.com/Stumble/jev-go) - Community Go SDK for the System One API with direct and Vercel gateway providers, an interactive CLI, and an agent skill plus AGENTS.md integration guide. <sub>MIT · Go</sub>
- [Vicente-MD/jev-resilience](https://github.com/Vicente-MD/jev-resilience) - Spring Boot WebFlux starter whose @SemanticCircuitBreaker annotation has Jev flag HTTP 200 bodies that encode errors and raises an exception, failing open. <sub>no license · Java</sub>
- [withzombies/jev-go](https://github.com/withzombies/jev-go) - Stdlib-only Go client for the System One API with typed Noul, Choice and Score questions, explicit config and an SDK parity document. <sub>Apache-2.0 · Go</sub>
- [ziyu/sytem-one-sdk](https://github.com/ziyu/sytem-one-sdk) - Zero-dependency TypeScript SDK with evaluate(state, questions), protocol adapters, a Cloudflare Workers AI binding, decision helpers and uncertainty gates. <sub>MIT · JavaScript</sub>
- [AbdelStark/s1-rs](https://github.com/AbdelStark/s1-rs) - Rust derive macros that turn enums and structs into Choice, Score and Noul questions with confidence-gated verdicts and a fake client for tests. <sub>MIT · Rust</sub>
- [AbdelStark/typesafe-rs](https://github.com/AbdelStark/typesafe-rs) - Community Rust client on crates.io for System One with async and blocking clients, a questions! macro, retries matching the official SDKs and a mock crate. <sub>MIT · Rust · [live](https://docs.rs/typesafe-rs/latest/typesafe_rs/)</sub>
- [abeldzan/jev-rs](https://github.com/abeldzan/jev-rs) - Async Rust client for the TypeSafe API with typed questions, model discovery, retries and an optional blocking client; not yet on crates.io. <sub>MIT · Rust</sub>
- [adibhanna/typesafego](https://github.com/adibhanna/typesafego) - Stdlib-only Go client for the TypeSafe API with Noul, Choice and Score helpers, typed answer accessors and a runnable triage example. <sub>MIT · Go</sub>
- [alpibrusl/lex-judge](https://github.com/alpibrusl/lex-judge) - Package for the Lex language exposing Noul, Choice and Score judgments as a net-only effect with a decided() confidence helper. <sub>no license · Lex</sub>
- [anilsenay/jev](https://github.com/anilsenay/jev) - Unofficial Go client using generics so a Choice over your own enum returns that type, with Sure(threshold) helpers and pre-send validation. <sub>MIT · Go</sub>
- [aoprisan/typesafe-ai-rust-sdk](https://github.com/aoprisan/typesafe-ai-rust-sdk) - Unofficial Rust client for the System One API with async and blocking modes, mirroring the official Python SDK's retries and error handling. <sub>MIT · Rust</sub>
- [aoprisan/typesafe-ai-scala-sdk](https://github.com/aoprisan/typesafe-ai-scala-sdk) - Dependency-free Scala 3 client for System One mirroring the official Python SDK's retries and errors, with blocking, CompletableFuture and Future calls. <sub>MIT · Scala</sub>
- [ask-rb/ask-decisions](https://github.com/ask-rb/ask-decisions) - Ruby gem with Choice, Score and Noul decision primitives, batching and a static test provider, using TypeSafe as the default backend. <sub>MIT · Ruby</sub>
- [binnash/typesafe-sdk](https://github.com/binnash/typesafe-sdk) - PHP 8.2 client for the System One API using PSR-18 HTTP clients, with retries, typed answers and Laravel integration. <sub>no license · PHP</sub>
- [Biztactix-Ryan/TypeSafe.Sdk.C-](https://github.com/Biztactix-Ryan/TypeSafe.Sdk.C-) - C# port of the official Python and JS SDKs for .NET 10, AOT-compatible, tested against a stubbed HTTP handler only. <sub>MIT · C#</sub>
- [carllippert/jev-router](https://github.com/carllippert/jev-router) - Express middleware with no route table: handlers register an English intent and one Choice picks which runs, returning 404 below 0.65 confidence. <sub>MIT · TypeScript</sub>
- [cephalization/phoenix-jev-example](https://github.com/cephalization/phoenix-jev-example) - TypeScript example that runs Jev through the AI SDK evaluation API and wraps it in an OpenInference evaluator span traced to Arize Phoenix. <sub>MIT · TypeScript</sub>
- [CodeAlive-AI/mastra-jev-moderation](https://github.com/CodeAlive-AI/mastra-jev-moderation) - Single-file Mastra input Processor that blocks a turn when P(block) passes a threshold and labels a category, failing open on errors. <sub>MIT · TypeScript</sub>
- [david1gp/jev](https://github.com/david1gp/jev) - TypeScript client and CLI for System One that returns Result values instead of throwing, with valibot validation; targets Node 22 and Bun. <sub>MIT · TypeScript</sub>
- [Dujaydis/JevSysUno](https://github.com/Dujaydis/JevSysUno) - TypeScript decision-definition layer over the official SDK with a calibration eval harness and 65 tests; never run against the live API. <sub>no license · TypeScript</sub>
- [edteamlat/EDcheck](https://github.com/edteamlat/EDcheck) - Server-side library that attaches semantic rules to Zod 4 schemas and compiles them into one batched Jev request per object. <sub>MIT · TypeScript</sub>
- [FelineStateMachine/typesafe-go](https://github.com/FelineStateMachine/typesafe-go) - Unofficial zero-dependency Go SDK for the System One API with typed Noul/Choice/Score questions, checked answer accessors and context-aware retries. <sub>MIT · Go</sub>
- [FFatTiger/new-api-plugin-typesafe](https://github.com/FFatTiger/new-api-plugin-typesafe) - Task plugin for the new-api gateway that exposes native /v1/systemone with channel routing, model mapping, token billing and a Vercel AI Gateway upstream. <sub>Apache-2.0 · JavaScript</sub>
- [Fox-Islam/typesafe-sdk-php](https://github.com/Fox-Islam/typesafe-sdk-php) - Unofficial PHP 8.3 client with a fluent question builder that switches between the TypeSafe API and OpenRouter's decisions endpoint. <sub>MIT · PHP</sub>
- [hfiguera/typesafe_ai](https://github.com/hfiguera/typesafe_ai) - Elixir client built on Mint with supervised HTTP/2 connections, bounded concurrency, request deadlines, retries and telemetry. <sub>MIT · Elixir</sub>
- [javiergradiche/ruby_llm-providers-typesafe](https://github.com/javiergradiche/ruby_llm-providers-typesafe) - RubyLLM provider gem with an evaluate block DSL for noul, choice and score questions that returns typed answers, probabilities and cost. <sub>MIT · Ruby · [live](https://rubygems.org/gems/ruby_llm-providers-typesafe)</sub>
- [jonesmelton/verdict](https://github.com/jonesmelton/verdict) - OCaml 5.2 Eio client for the System One API where question handles carry their answer type, with TLS, bounded requests and retries. <sub>MIT · OCaml</sub>
- [jun-shiromizu/mastra-jev](https://github.com/jun-shiromizu/mastra-jev) - Reference patterns for using Jev inside Mastra agents, tools, workflows, memory, guardrails and evals, with a mock mode for tests. <sub>no license · TypeScript</sub>
- [kazz187/jev-sdk-go](https://github.com/kazz187/jev-sdk-go) - Unofficial Go 1.27 client with generic typed questions so a Choice over your enum returns that type, plus batching, retries and no dependencies. <sub>MIT · Go</sub>
- [kedi-lang/kedi-typesafe](https://github.com/kedi-lang/kedi-typesafe) - Python package exposing Jev as a Pydantic AI model and LangChain structured-output backend for booleans, literals and extracted strings. <sub>MIT · Python</sub>
- [kentaro/jevex](https://github.com/kentaro/jevex) - Elixir library adding ~> and ~>> operators so Noul, Choice and Score calls compose in pipelines, with configurable backends. <sub>MIT · Elixir</sub>
- [kunobi-ninja/kunobi-jev](https://github.com/kunobi-ninja/kunobi-jev) - Unofficial Rust client for System One with question builders, limit checks, blocking and fake-client features, and measured token cost of batching. <sub>Apache-2.0 · Rust</sub>
- [lu-zero/systemone](https://github.com/lu-zero/systemone) - Executor-agnostic Rust client for the systemone API on isahc, with derive-macro and facet-reflection crates for building Choice criteria from enums. <sub>MIT · Rust</sub>
- [luiginotmario/postgres-Jev](https://github.com/luiginotmario/postgres-Jev) - PostgreSQL extension adding a jev(row, 'predicate') function for natural-language WHERE clauses via OpenRouter, plus a search playground. <sub>no license · TypeScript · [live](https://postgres-jev.vercel.app)</sub>
- [marandaneto/typesafe-sdk-swift](https://github.com/marandaneto/typesafe-sdk-swift) - Swift 6 package for the TypeSafe API on URLSession with no third-party dependencies, covering iOS, macOS, tvOS, watchOS and visionOS. <sub>MIT · Swift</sub>
- [mattneel/typesafe](https://github.com/mattneel/typesafe) - Community Elixir client for System One with noul/choice/score builders, typed answer structs, Req transport, telemetry and test helpers. <sub>MIT · Elixir</sub>
- [mattneel/typesafe.zig](https://github.com/mattneel/typesafe.zig) - Community Zig client for System One where answer types, enum choices and probability structs are derived from the questions at compile time. <sub>MIT · Zig</sub>
- [mhmdkzr/jev](https://github.com/mhmdkzr/jev) - Go client with builder-style Noul, Choice and Score questions whose typed answers are read back by question handle, stdlib only. <sub>MIT · Go</sub>
- [mzainzulifqar/jev-php-sdk](https://github.com/mzainzulifqar/jev-php-sdk) - PHP 8.1+ client for the System One API over any PSR-18 HTTP client, with typed result accessors and Laravel support. <sub>MIT · PHP</sub>
- [netf/typesafe-sdk-rs](https://github.com/netf/typesafe-sdk-rs) - Rust port of the official Python SDK with async builders, an optional blocking client, matching errors and retries, and doctested examples. <sub>MIT · Rust</sub>
- [Nibir1/typesafe-go](https://github.com/Nibir1/typesafe-go) - Go client for System One with typed Noul, Choice and Score questions, typed answers, test doubles and retries, verified against the live API. <sub>Apache-2.0 · Go</sub>
- [nishimotz/hello-jev](https://github.com/nishimotz/hello-jev) - Japanese Python tutorial for Jev with a helper that smooths over request differences between TypeSafe direct, Vercel AI Gateway and Cloudflare. <sub>no license · Python</sub>
- [nitinnat/jev-gateway](https://github.com/nitinnat/jev-gateway) - Dockerized local HTTP service exposing POST /v1/evaluate that forwards state and questions to Jev through Vercel AI Gateway. <sub>MIT · JavaScript</sub>
- [nu-sync/effect-evaluation](https://github.com/nu-sync/effect-evaluation) - Effect-native TypeScript client for System One exposed as a Layer-provided service with typed questions, answers and failures. <sub>MIT · TypeScript</sub>
- [ppweni/typesafe_rs](https://github.com/ppweni/typesafe_rs) - Async Rust client for the TypeSafe API modelled on the Python SDK 0.6.0, with builders for Noul/Choice/Score, retries and model listing. <sub>MIT · Rust</sub>
- [rajivkuriakose/typesafe-jev-examples](https://github.com/rajivkuriakose/typesafe-jev-examples) - Python worked examples with a client that picks TypeSafe or OpenRouter from the environment, starting with seven-question ticket triage and offline tests. <sub>MIT · Python</sub>
- [recodelabs/duckdb-jev](https://github.com/recodelabs/duckdb-jev) - DuckDB C++ extension adding jev(), jev_prob() and jev_choice() SQL functions so rows can be filtered, ranked and classified in plain English. <sub>MIT · C++</sub>
- [riclib/llm-wires](https://github.com/riclib/llm-wires) - Rust crate with one Provider trait over Anthropic and OpenAI HTTP shapes plus a Judge trait for typed System One questions. <sub>MIT · Rust</sub>
- [sashimikun/sql-jev](https://github.com/sashimikun/sql-jev) - TypeScript library adding cached jev() predicates, scores and choices to SQL queries on SQLite, Turso/libSQL and Cloudflare D1, with deploy commands. <sub>no license · TypeScript</sub>
- [sava-software/typesafe-client](https://github.com/sava-software/typesafe-client) - Java client for the System One API with typed question and answer types, a recording/replay decorator and a separate evaluation harness module. <sub>Apache-2.0 · Java</sub>
- [SergeAx/typesafe-sdk-go](https://github.com/SergeAx/typesafe-sdk-go) - Go SDK for System One with Noul, Choice and Score question types, typed answer accessors and forward-compatible handling of unknown answer types. <sub>MIT · Go</sub>
- [shanginn/jev-php](https://github.com/shanginn/jev-php) - PHP 8.5 SDK for Jev on OpenRouter with Noul, Choice and Score question objects, enum mapping and readonly DTO results; installable via Composer. <sub>MIT · PHP</sub>
- [Shubham510/typesafe-go](https://github.com/Shubham510/typesafe-go) - Unofficial Go client for the System One API with Noul, Choice and Score constructors, retries and model listing; standard library only. <sub>MIT · Go</sub>
- [soderlind/ai-provider-for-jev](https://github.com/soderlind/ai-provider-for-jev) - WordPress plugin with a settings page, PHP helpers ask_noul/ask_choice/ask_score, an authenticated REST proxy and a JavaScript client for Jev. <sub>no license · PHP</sub>
- [SoundBlaster/Jev4Mellea](https://github.com/SoundBlaster/Jev4Mellea) - Python adapter that plugs Jev checks into Mellea 0.7.0 as Requirement validators, with offline contract tests and a live check CLI; not yet run end to end. <sub>Apache-2.0 · Python</sub>
- [syndicalt/docjev](https://github.com/syndicalt/docjev) - TypeScript sidecar that filters, ranks, classifies and scores JSON documents from a document DB with Jev, caching judgments per condition. <sub>no license · TypeScript</sub>
- [tinyhumansai/tinyjevclient](https://github.com/tinyhumansai/tinyjevclient) - Rust client for System One that validates answers against the request and returns latency, attempts and usage alongside typed results. <sub>GPL-3.0 · Rust</sub>
- [typesend/typesafe_ai](https://github.com/typesend/typesafe_ai) - Elixir client with typed question and answer structs, retries, telemetry, concurrent fan-out and offline test stubs. <sub>MIT · Elixir · [live](https://typesafe-api.hexdocs.pm/readme.html)</sub>
- [valksor/typesafe-sdk-go](https://github.com/valksor/typesafe-sdk-go) - Unofficial Go client for the System One API with typed Noul, Choice and Score, retries, typed errors and an injectable http.Client. <sub>MIT · Go</sub>
- [valksor/typesafe-sdk-php](https://github.com/valksor/typesafe-sdk-php) - Unofficial PHP 8.4 client for the System One API with typed questions, retries, typed exceptions and a swappable transport, on Packagist. <sub>MIT · PHP</sub>
- [vinnie357/typesafe_sdk_ex](https://github.com/vinnie357/typesafe_sdk_ex) - Elixir SDK built on Req, modelled on the official JS SDK, with noul/choice/score helpers and status-mapped error structs. <sub>no license · Elixir</sub>
- [wescld/jevIf](https://github.com/wescld/jevIf) - One-file JS helper that turns a natural-language condition into a Jev Noul with threshold, plus a single-request jevSwitch for multiple conditions. <sub>MIT · JavaScript</sub>
- [yairshy/decido](https://github.com/yairshy/decido) - Python library for typed probabilistic decisions with a Jev provider, batching, request budgets, ranking, a CLI and local MCP tools. <sub>MIT · Python</sub>
- [ZENOTME/openasking](https://github.com/ZENOTME/openasking) - Rust SDK for Jev with a builder for bool, choice and score questions, supporting the direct TypeSafe API and Vercel AI Gateway. <sub>MIT · Rust</sub>
- [zhirschtritt/typesafe-go](https://github.com/zhirschtritt/typesafe-go) - Dependency-free Go client for the TypeSafe v1 API with Noul/Choice/Score helpers, retries honoring Retry-After and typed HTTP errors. <sub>MIT · Go</sub>

## Read and watch

70 pieces, each opened and read. Notes say what you get, and attribute claims to their authors.

### Official docs worth reading first

TypeSafe's own pages. The failure-modes page is the one most people skip.

- [Quick start](https://docs.typesafe.ai/introduction/quickstart) - Shortest path to a first call: get a key, send one state with typed questions, read the answers. <sub>TypeSafe AI</sub>
- [API reference](https://docs.typesafe.ai/api) - HTTP reference for POST /v1/systemone: request body (state, model, questions), answer shapes per question type, rate-limit handling. <sub>TypeSafe AI</sub>
- [Primitives (Questions)](https://docs.typesafe.ai/primitives) - Overview of the three question types (Choice, Score, Noul), what each returns, how to pick one, and how to ask several in one call. <sub>TypeSafe AI</sub>
- [Choice](https://docs.typesafe.ai/primitives/choice) - Choice picks one option from a declared set and returns the selected option, a probability per option, and a confidence value. <sub>TypeSafe AI</sub>
- [Score](https://docs.typesafe.ai/primitives/score) - Score rates the state against ordered descriptive levels and returns a score, a probability per level, and a confidence value. <sub>TypeSafe AI</sub>
- [Noul](https://docs.typesafe.ai/primitives/noul) - Noul asks a yes/no question and returns the probability that the answer is yes. <sub>TypeSafe AI</sub>
- [State](https://docs.typesafe.ai/concepts/state) - What state is, how to structure it (string, JSON object or array), and how to give the model the context a question needs. <sub>TypeSafe AI</sub>
- [Confidence](https://docs.typesafe.ai/confidence) - How TypeSafe reports certainty, how confidence differs from probability, and how to use it to decide whether code should act. <sub>TypeSafe AI</sub>
- [Models](https://docs.typesafe.ai/models) - Model card for jev-1.13.0: $0.042 per million input tokens, free output, rate limits, 64k context (32k for state), text-only input. <sub>TypeSafe AI</sub>
- [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) - TypeSafe's own list of known weak spots in jev-1.13, which it says will be fixed in later versions; read before designing questions. <sub>TypeSafe AI</sub>
- [How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) - Design guidance: keep code in control of flow and side effects, and hand the model only narrow, structured decisions. <sub>TypeSafe AI</sub>
- [Patterns](https://docs.typesafe.ai/patterns) - Index of four architecture patterns: speculative fan-out, confidence-gated routing, composite scoring, and intent routing. <sub>TypeSafe AI</sub>
- [Agent skill](https://docs.typesafe.ai/agent-skill) - Install commands for a skill that gives Claude Code, Codex and other coding agents the question types, patterns and API usage. <sub>TypeSafe AI</sub>
- [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions) - Cookbook: 13 questions over the GDPR Wikipedia article; TypeSafe reports one batched call is 12.2x cheaper and 10.0x faster than 13 single calls. <sub>TypeSafe AI</sub>
- [Re-ranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe) - Cookbook: re-ranks 30-passage BM25 shortlists for 40 CLERC legal queries; TypeSafe reports top-1 going from 5% to 18% and top-10 from 38% to 62%. <sub>TypeSafe AI</sub>
- [Guardrails for LLMs](https://docs.typesafe.ai/cookbooks/llm_guardrails) - Cookbook: screen messages into and out of an LLM app with hazard questions and a severity score, then threshold to pass, review or block. <sub>TypeSafe AI</sub>
- [Classifying RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages) - Cookbook: score each retrieved passage in one request, then decide in code which reach the answering model; drops prompt-injection passages. <sub>TypeSafe AI</sub>
- [Function calling](https://docs.typesafe.ai/cookbooks/function_calling) - Cookbook: maps natural-language trading requests to typed function calls by turning function names and closed-set arguments into questions. <sub>TypeSafe AI</sub>

### Where you can call it

Providers that serve Jev besides TypeSafe's own API.

- [Jev (typesafe)](https://developers.cloudflare.com/ai/models/typesafe/jev/) - Cloudflare AI model page for typesafe/jev: 32,000-token context, env.AI.run and curl examples with Noul, Choice and Score, plus sample responses. <sub>Cloudflare</sub>
- [TypeSafe Jev now available in AI Gateway](https://www.netlify.com/changelog/typesafe-jev-ai-gateway/) - Netlify changelog: call Jev from Netlify Functions via @typesafe-ai/sdk with no API key setup, billed to Netlify credits; includes a contact-form routing example. <sub>Netlify · 2026-09-17</sub>
- [AI SDK Providers: TypeSafe](https://ai-sdk.dev/providers/ai-sdk-providers/typesafe-ai) - Docs for @ai-sdk/typesafe-ai: experimental_evaluate with choice, score and boolean (Noul) questions, limits per type, rounding, confidence metadata, retries. <sub>Vercel AI SDK</sub>

### Open models and demos on Hugging Face

TypeSafe has released no weights. These are community reproductions of the idea; numbers are each card's own.

- [pngwn/open-jev](https://huggingface.co/spaces/pngwn/open-jev) - Gradio demo of the pngwn Qwen3.5-4B scorer: prefill state once, score all question/option branches in parallel; card reports 0.740 accuracy, ECE 0.047 on 500 Gradio PRs. <sub>pngwn · 2026-09-17</sub>
- [monotykamary/LFM2.5-2.6B-RLCD](https://huggingface.co/monotykamary/LFM2.5-2.6B-RLCD) - Inference-only parallel constrained decoding on unchanged LFM2.5-2.6B; card reports ~9.9x speedup on L40S but 72.2% field accuracy on fresh cases vs 94.4% for AR JSON. <sub>monotykamary · 2026-09-16</sub>
- [com-kotobalabs/open-jev-deberta-v3-large](https://huggingface.co/com-kotobalabs/open-jev-deberta-v3-large) - DeBERTa-v3-large with a span head for choice/score/noul, trained on banking77, SST-5 and BoolQ gold labels; card reports 0.854 in-domain and 0.690 OOD accuracy. <sub>com-kotobalabs · 2026-09-18</sub>
- [mobarmg/jev-schema-scorer-deberta-v3-large](https://huggingface.co/mobarmg/jev-schema-scorer-deberta-v3-large) - DeBERTa-v3-large scalar scorer over (state, question+candidate) pairs, trained on 7,650 synthetic questions in 30 domains; card reports 0.889 choice acc, 0.940 noul acc. <sub>mobarmg · 2026-09-17</sub>
- [pngwn/system-one-qwen3.5-4b-scorer](https://huggingface.co/pngwn/system-one-qwen3.5-4b-scorer) - Qwen3.5-4B-Base with LoRA r=16 and a scalar option-scoring head, 12,913 questions, 9 task families; card reports 0.707 test accuracy, ECE 0.044 after temperature scaling. <sub>pngwn · 2026-09-16</sub>
- [harshatheg/Qwen-2.5-1B-RLCD](https://huggingface.co/harshatheg/Qwen-2.5-1B-RLCD) - MLX inference code, no new weights: Qwen2.5-1.5B-Instruct-4bit scores enum/boolean JSON fields in parallel; card reports 5.6x-7.0x speedup vs autoregressive (M4 Max). <sub>harshatheg · 2026-09-16</sub>
- [multimodalart/jev-reproductions-tracker](https://huggingface.co/spaces/multimodalart/jev-reproductions-tracker) - Static Space listing open Jev reproduction attempts in one grid (decoding tricks, diffusion, trained scorers, prior art, explainers), sorted by an engagement score. <sub>multimodalart · 2026-09-17</sub>
- [shreyansh26/Qwen-2.5-1B-RLCD](https://huggingface.co/shreyansh26/Qwen-2.5-1B-RLCD) - PyTorch server code, no fine-tuned weights: batched and FlexAttention tree scoring of enum/boolean fields on Qwen2.5-1.5B-Instruct; card gives no benchmark numbers. <sub>shreyansh26 · 2026-09-16</sub>
- [notnotsamuel/LFM2.5-350M-RLCD](https://huggingface.co/notnotsamuel/LFM2.5-350M-RLCD) - Inference-only constrained field scoring on unchanged LFM2.5-350M; card reports 8.46x (M2 Max) to 62.91x (L40S) speedup on 28 booleans at 60.7-64.3% field accuracy. <sub>notnotsamuel · 2026-09-16</sub>
- [pngwn/system-one-qwen3.5-4b-scorer-v2b](https://huggingface.co/pngwn/system-one-qwen3.5-4b-scorer-v2b) - v2 retrain of the pngwn Qwen3.5-4B-Base LoRA scorer on 45,932 questions for 2 epochs; card reports 0.803 val accuracy and ECE 0.022 (val split only, n=5,087). <sub>pngwn · 2026-09-17</sub>
- [heman10x/rlcd-modernbert-151m](https://huggingface.co/heman10x/rlcd-modernbert-151m) - 151M GLiClass ModernBERT-base classifier with CE+Brier loss, temperature scaling, an abstain slot; card reports 95.0% top-1 and 3.35% ECE on 1,000 Banking77-based cases. <sub>heman10x · 2026-09-17</sub>
- [aahf/JevBenchmark](https://huggingface.co/spaces/aahf/JevBenchmark) - Static article comparing Jev, GPT-5.6 Sol and XGBoost on four synthetic ad outcomes; card reports similar quality at ~64x lower estimated API cost and 5.4x lower latency. <sub>aahf · 2026-09-17</sub>
- [epsilon3/Qwen-2.5-1B-RLCD-Fast](https://huggingface.co/epsilon3/Qwen-2.5-1B-RLCD-Fast) - Tree-attention variant of harshatheg's inference code on unchanged Qwen2.5-1.5B-Instruct; card reports up to 2.37x faster field decode and 98% less extra memory on M4 Pro. <sub>epsilon3 · 2026-09-16</sub>
- [Foodoo1/Qwen3-14B-RLCD-Decision-LoRA](https://huggingface.co/Foodoo1/Qwen3-14B-RLCD-Decision-LoRA) - QLoRA on Qwen3-14B with loss on the single decision token, 4,152 synthetic fraud-triage cases; card reports 98.8% vs 85.2% base on 200 held-out synthetic cases, 4 fields. <sub>Foodoo1 · 2026-09-18</sub>
- [DavidHatley/system-one-mini](https://huggingface.co/DavidHatley/system-one-mini) - 69.3M DistilBERT with five fixed classification heads over synthetic software-diagnosis summaries; card says not a Jev reproduction, reports 86.25% final-set accuracy. <sub>DavidHatley · 2026-09-16</sub>
- [reachjalil/jevlogs-triage-explorer](https://huggingface.co/spaces/reachjalil/jevlogs-triage-explorer) - Gradio explorer for the jevlogs log-triage benchmark; makes no live Jev calls and recomputes routing from saved probabilities on sanitized Loghub HDFS and BGL samples. <sub>reachjalil · 2026-09-17</sub>
- [mobarmg/jev-schema-scorer](https://huggingface.co/spaces/mobarmg/jev-schema-scorer) - Gradio demo and API for mobarmg/jev-schema-scorer-deberta-v3-large; you write your own choice/noul/score schema and it returns per-question distributions. <sub>mobarmg · 2026-09-17</sub>
- [Eloiselatourdepise/qwen-rlcd-demo](https://huggingface.co/spaces/Eloiselatourdepise/qwen-rlcd-demo) - Static in-browser (WebGPU/WASM) side-by-side demo of harshatheg/Qwen-2.5-1B-RLCD parallel constrained decoding vs autoregressive JSON generation; card gives no numbers. <sub>Eloiselatourdepise · 2026-09-18</sub>
- [pngwn/system-one-demo](https://huggingface.co/spaces/pngwn/system-one-demo) - Gradio demo of the pngwn Qwen3.5-4B-Base LoRA scorer next to Qwen3.5-4B instruct; card reports 0.705 test accuracy, ECE 0.046 and ~112 ms per query at 16 options or fewer. <sub>pngwn · 2026-09-16</sub>

### Datasets

- [reachjalil/jevlogs-log-triage-benchmark](https://huggingface.co/datasets/reachjalil/jevlogs-log-triage-benchmark) - 5,000 sanitized Loghub HDFS/BGL log lines with live Jev routing decisions and token counts; card reports 0.993 HDFS recall but only 0.84% of lines filtered out. <sub>reachjalil · 2026-09-17</sub>
- [Mikhail/mini-jev-runs](https://huggingface.co/datasets/Mikhail/mini-jev-runs) - 27,900 decision records with fp32 option-letter logits from frozen Qwen3-4B-Instruct-2507 on CLINC150; card reports 0.848 accuracy and scores that are not calibrated. <sub>Mikhail · 2026-09-18</sub>
- [SargeDev/jev-distill-corpus](https://huggingface.co/datasets/SargeDev/jev-distill-corpus) - 148,160 query-passage rows with 0-7 graded relevance from a typed-judgment (Choice) API and a 32B teacher; card reports 91.0% binary agreement, Pearson r=0.897. <sub>SargeDev · 2026-09-18</sub>
- [reachjalil/jev-luna-pagerduty-trigger](https://huggingface.co/datasets/reachjalil/jev-luna-pagerduty-trigger) - 3,000 synthetic checkout/payments log lines with page/no-page gold labels plus Jev and GPT-5.6 Luna runs; card reports Jev v3 at p>=0.50 with 1.000 recall and precision. <sub>reachjalil · 2026-09-17</sub>
- [reachjalil/jev-tree-choice-cap](https://huggingface.co/datasets/reachjalil/jev-tree-choice-cap) - 180 synthetic tickets over a 320-leaf incident taxonomy testing Jev's 255-option Choice cap; card reports authored tree walk 180/180 vs 90/180 when truncating to 255. <sub>reachjalil · 2026-09-18</sub>
- [pngwn/system-one-decisions](https://huggingface.co/datasets/pngwn/system-one-decisions) - Training set for the pngwn scorer: 12,913/1,452/1,751 rows of state, typed question, options, answer index; card body is the upstream support-ticket dataset text. <sub>pngwn · 2026-09-16</sub>
- [DavidHatley/system-one-mini-data](https://huggingface.co/datasets/DavidHatley/system-one-mini-data) - 28,000 deterministic synthetic software-diagnosis summaries with five fixed labels, used to train DavidHatley/system-one-mini; card says not a Jev or RLCD reproduction. <sub>DavidHatley · 2026-09-16</sub>

### Hands-on reports

Someone ran it and wrote down what happened.

- [Testing TypeSafe Jev, Mistral and Gemini for local event validation](https://nearhere.events/blog/typesafe-jev-mistral-gemini-event-validation) - Near Here reports Jev matched 48/50 event-listing decisions vs 43 for Gemini 3.5 Flash-Lite and 42 for Mistral Small 4, at 0.59s and $0.043 per 1,000 decisions. <sub>Jon Reed (Near Here) · 2026-09-16</sub>
- [Mini-Vibe Check: TypeSafe's Jev Judged Everything I've Written in 0.7 Seconds](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds) - Every's head of evals ran Jev over his own writing; the free preview explains the yes/no-probability idea and says accuracy is still open. Rest needs an account. <sub>Mike Taylor (Every) · 2026-09-15</sub>
- [jev 同士に五目並べで対戦させた](https://zenn.dev/mizchi/articles/jev-plays-gomoku) - mizchi had Jev play gomoku against itself via one Choice over legal moves; a 25-move game took 13.9s, about 500ms per move, with confidence logged per move. Repo linked. <sub>mizchi · 2026-09-17 · ja</sub>
- [TypeSafeのJevを正しく驚く、それってLLMでできませんか？](https://zenn.dev/nwn/articles/824026c76116e0) - Author rebuilt the parallel-answer trick with Gemma3 270M first-token logits and reports 77x over JSON output; in a Mario harness Jev still beat the older LLMs tried. <sub>ヨ (nwn) · 2026-09-17 · ja</sub>

### Explainers

What it is and how to think about it. No original testing unless the note says so.

- [Jev means structured output is interesting again](https://www.seangoedecke.com/jev-means-structured-output-is-interesting-again/) - Skeptical read: argues prefilling a normal LLM and sampling one constrained token gets most of the speed (he reports 2-3x on Qwen2.5-1.5B) and doubts a technical moat. <sub>Sean Goedecke · 2026-09-16</sub>
- [Typed Decisions, Not Chat](https://warmersun.com/jev/) - Briefing that sets each launch claim against TypeSafe's own footnotes: eval labels come from two LLMs, the 0% hallucination figure is not empirical, no paper or weights. <sub>Warmer Sun · 2026-09-16</sub>
- [Jev: The Language Model That Won't Talk](https://anthonymaio.substack.com/p/jev-the-language-model-that-wont) - Analysis from secondary sources: Jev 67.8% vs GPT Sol 74.1% on TypeSafe's evals, RLCD unpublished, and calibrated answers need not compose into a calibrated workflow. <sub>Anthony Maio · 2026-09-16</sub>
- [He Says He Co-Invented ChatGPT. His New AI, Jev, Won't Write a Word](https://dev.to/gabrielanhaia/he-says-he-co-invented-chatgpt-his-new-ai-jev-wont-write-a-word-e3c) - TypeScript ticket-triage walkthrough with the AI SDK provider plus a threshold routing function; no live run (author had no key), numbers are vendor-reported. <sub>Gabriel Anhaia · 2026-09-17</sub>
- [AI That Doesn't Talk: A Plain-English Guide to TypeSafe's Jev](https://ziplyne.agency/blog/ai-that-doesnt-talk-typesafe-jev-guide) - Long beginner guide with Python SDK snippets, use cases by industry, a list of reasons to stay skeptical, and a shadow-run rollout plan. No testing of its own. <sub>Isaac Horowitz (ZipLyne) · 2026-09-16</sub>
- [What Is Jev? How to Implement Typesafe AI’s Decision Model (Practical Guide)](https://mohammedshehu.com/jev-typesafe-ai/) - Python SDK intro plus a proposed (not built) use in the author's chargeback tool; test results quoted are Every's, not his own. <sub>Mo Shehu · 2026-09-16</sub>
- [TypeSafe JEV Explained: AI Decisions Without a Chatbot](https://www.theneuron.ai/explainer-articles/typesafe-jev-system-one-models-explained/) - Short non-technical explainer of the launch post and RLCD; all figures are company-reported and the only counterpoint is that general LLMs keep getting cheaper. <sub>Grant Harvey (The Neuron) · 2026-09-16</sub>
- [TypeSafe Jev: the First Decision-Only Model Class, Benchmarked and Priced](https://www.developersdigest.tech/blog/typesafe-jev-system-one-models-release-guide-2026) - Rewrite of the launch post and evals site: per-model accuracy/cost/latency table, pricing, curl example. No testing of its own; repeats TypeSafe's caveats. <sub>Developers Digest · 2026-09-16</sub>

### Videos

- [Livestream Coding with the new TypeSafe AI JEV Model | Parallel Constrained Decoding](https://www.youtube.com/watch?v=5Lx4DLLYafM) - Livestream (about 2h19m) breaking down Jev and sketching network architectures for JSON-predictor models; per the description the content starts near 6:57. <sub>Neural Breakdown with AVB · 2026-09-17</sub>
- [100x Faster? He Co-Created ChatGPT. Now He Built the Opposite: Meet Jev.](https://www.youtube.com/watch?v=oAI-5lhKWyU) - Launch walkthrough with sources on screen: blog caveats, Doom and Wikiracing demos, the two outside tests, 'can't hallucinate' read closely, X thread questions. <sub>Reindent · 2026-09-16</sub>
- [Jev by TypeSafe AI: Jev vs LLMs - Parallel Sampling, Lower Latency, and Typed Outputs](https://www.youtube.com/watch?v=JQFNpX1w6vY) - Nine-minute explainer: parallel sampling vs autoregression, RLCD, the primitives, an expense-claim example, and limits around semantic errors and auditability. <sub>Alex Hitt · 2026-09-17</sub>

### News

- [TypeSafe AI debuts model for machines that plays Doom](https://www.theregister.com/ai-and-ml/2026/09/16/typesafe-ai-debuts-model-for-machines-that-plays-doom/5296711) - Launch coverage: $40M funding, typed probabilistic output, the Doom demo, pricing, and why "hallucination-free" is not a fair comparison since answers can still be wrong. <sub>Thomas Claburn (The Register) · 2026-09-16</sub>
- [LLMの193倍速い“判断だけのAI”「Jev」、ChatGPTの共著研究者が開発](https://pc.watch.impress.co.jp/docs/news/2141599.html) - Japanese launch report; notes Almeida is one of about 20 InstructGPT co-authors, not ChatGPT's inventor, and that 193.6x/444.6x come from TypeSafe's own evals. <sub>竹元 かつみ (PC Watch) · 2026-09-17 · ja</sub>
- [[AINews] Jev: a “System One Model” that only decides/classifies/routes/scores — >100x faster, >200x cheaper than small frontier LLMs](https://www.latent.space/p/ainews-jev-a-system-one-model-that) - Daily roundup leading with the launch; the Jev part is a short digest of X reactions (classifier/judge/router use, "not a GPT replacement", DSPy parallels). <sub>Latent Space · 2026-09-16</sub>
- [Browser Use's Jev Ultrafast Cuts Browser Agent Costs 90% With Indexed DOM Actions](https://alphasignal.ai/news/browser-use-s-jev-ultrafast-cuts-browser-agent-costs-90-with-indexed-dom-actions) - Reports Browser Use's MIT-licensed agent where Jev picks an action and element index per step; Google Flights demo in about 7s at a reported $0.0039. Paywalled midway. <sub>AlphaSignal Newsroom · 2026-09-17</sub>

### Discussion

- [Introducing System One Models and Jev](https://news.ycombinator.com/item?id=49717558) - Main launch thread (1,871 points, about 490 comments): whether the speed comparison is apples-to-oranges, classifier/encoder parallels, and requests for demo code. <sub>Hacker News · 2026-09-15</sub>
- [Reverse-engineered Jev-like model](https://news.ycombinator.com/item?id=49731282) - Thread on the jevlike repo (160 points): replication attempts, a commenter reporting a DiffusionGemma "Jev mode" at about 0.2s per decision, and a Qwen-2.5-1B clone. <sub>Hacker News · 2026-09-16</sub>
- [OpenJev](https://news.ycombinator.com/item?id=49752041) - Thread on openjev.com (108 points, 53 comments): commenters note it is unaffiliated, emulates Jev with Qwen3 0.6B, takes 0.5-2s on an M2 Max, and question the name. <sub>Hacker News · 2026-09-18</sub>
- [Open-sourced jev architecture last year with model,paper and dataset](https://news.ycombinator.com/item?id=49736660) - Author claims a March 2025 arXiv paper (2503.23303) with open model and dataset used a similar non-autoregressive probability design; replies debate credit. <sub>Hacker News · 2026-09-17</sub>

## Measured by us

Numbers in vendor docs are the vendor's. These are ours, run against `jev-1.13.0` on 2026-09-18 from one network location. Scripts and raw results are in [`lab/`](lab/).

<a href="https://thevibeworks.github.io/awesome-typesafe-jev/lab.html"><img src="docs/media/lab-latency.png" alt="Strip plot of Jev request latency by number of questions per call" width="720"></a>

- Counting breaks the way TypeSafe says it does: asked whether "strawberry" has exactly three r, Jev says yes at 0.60; asked whether it has exactly two, it says yes at 0.79.
- Their fix works, mostly: one yes/no question per item, summed in code, counted 11 of 12 fruits in a 23-item list. The miss was "lime" at 0.32.
- On 33 known-answer cases: controls 4/4, dates 6/6, negation and indirection 6/6, adversarial 4/4, arithmetic 5/6, counting 5/7. Arithmetic answers sat near 0.5, which is the usable signal.
- Latency depends on when you call. The fastest request stays near 250 ms up to 25 questions per call, which supports the parallel-questions claim, but medians ranged from 310 ms (1 question) to 4.7 s (200 questions), and an earlier run the same day was several times faster at 200.
- The 3-question quickstart call billed 424 input tokens: about $0.000018 at the listed $0.042 per million.

[Open the interactive version](https://thevibeworks.github.io/awesome-typesafe-jev/lab.html).

## Other lists

- [hellogumbo/awesome-jev (awesomejev.com)](https://github.com/hellogumbo/awesome-jev) - The largest directory, several hundred entries with star counts refreshed daily.
- [aliaihub/awesome-jev-usecases](https://github.com/aliaihub/awesome-jev-usecases) - Use cases grouped by industry, with evidence links.
- [AbdelStark/awesome-typesafe](https://github.com/AbdelStark/awesome-typesafe) - Broader TypeSafe ecosystem list.
- [yzfly/awesome-jev-zh](https://github.com/yzfly/awesome-jev-zh) - Chinese-language list.

## How entries get in

Discovery is a script, [`scripts/discover.mjs`](scripts/discover.mjs): repository search, topic search, and code search for repos whose code references the API or an SDK, plus npm and Hugging Face. The raw sweep is not published, since it contains spam and unrelated repos.

Mechanical checks, no judgment ([`scripts/gate.py`](scripts/gate.py)): the repo is live, not a fork, not archived, not empty, created in the launch window, has a README of at least 600 characters, and that README or the description mentions Jev, TypeSafe or System One. Repos that pass and are about Jev are recorded in [`data/candidates.json`](data/candidates.json).

Then a reviewer reads it. Two tiers:

- **Editors' picks** (35): README read in full. Each carries a "why it is here" line and, where there is one, the weakness you should know first. Some carry media.
- **Listed** (1058): the README's opening and metadata were reviewed against the same rules. One line saying what it does. **(notable)** marks the ones a reviewer flagged as clearly above the rest: measurements with a method, a demo shown working, tests, or an honest limits section.

Rules for both: it does something concrete with Jev, or reproduces its interface in the open; the README shows how to run it or what it does in specifics; it is not a stub, a plan, a link collection, or a bare copy of the official SDKs. Stars are not a criterion in either direction. Descriptions are written by the reviewer in plain words, and numbers from a README are reported as the README's claims.

Reviewing was done by AI reviewers working to this rubric, with spot checks by a human-directed editor. It will contain mistakes. If an entry is wrong or you want yours removed, open an issue.

Media is copied into this repo only when the source repo's license allows it, and is credited. Otherwise it is linked.

## Contributing

Add an object to [`data/entries.json`](data/entries.json), run `npm run validate && npm run render`, open a PR. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

List and code: [MIT](LICENSE). Media belongs to its credited authors. "TypeSafe" and "Jev" are names of TypeSafe AI.
