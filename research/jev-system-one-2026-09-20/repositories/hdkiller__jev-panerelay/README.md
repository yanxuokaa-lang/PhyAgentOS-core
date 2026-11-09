# jev-panerelay ⚡🌐

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Decisions_API-purple.svg)](https://openrouter.ai/)
[![Panerelay](https://img.shields.io/badge/Browser-Panerelay_CDP-green.svg)](https://f-loat.github.io/panerelay/)

**Ultra-fast (sub-second) browser automation** combining **[TypeSafe's Jev](https://docs.typesafe.ai/introduction)** decision model with **[Panerelay](https://f-loat.github.io/panerelay/)** to drive your live, authenticated Chrome or Edge browser via **[OpenRouter](https://openrouter.ai/)**.

---

## Why jev-panerelay?

Traditional AI browser agents (like standard Playwright + Vision LLM setups) take **10–25 seconds per action**. They capture full-screen screenshots, upload megabytes of image tokens, and ask large multimodal models to guess `(x, y)` coordinates.

**`jev-panerelay` changes the paradigm:**
- ⚡ **Sub-Second Execution (~350–500ms per step)**: Uses TypeSafe's Jev decision model (`~typesafe/jev-latest` on OpenRouter Decisions API) to pick structured DOM actions directly from an atomic accessibility snapshot.
- 🔑 **Zero Re-Authentication**: Connects directly to your running Chrome/Edge browser via Panerelay. Reuses your existing logins, active sessions, and cookies without opening blank profiles or triggering MFA gates.
- 💸 **10x Cheaper**: Only invokes an LLM (`google/gemini-2.5-flash`) when text typing is explicitly needed (`TYPE_TEXT`). Normal clicks, dropdowns, and navigations bypass generative token costs.
- 🧩 **Agent Skill Ready**: Works as a standalone CLI tool or as a drop-in skill for local coding assistants (**Claude Code**, **OpenCode**, **Codex**, **Antigravity**) embedded inside Panerelay's Chrome Side Panel.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Live Chrome Browser (Authenticated Session)                │
│  - Your real tabs, cookies, and active logins                │
└──────────────────────────────▲───────────────────────────────┘
                               │ Chrome DevTools Protocol (CDP)
┌──────────────────────────────▼───────────────────────────────┐
│  Panerelay Gateway (http://127.0.0.1:43827/cdp/browser-use)  │
│  - Manages browser attachments & safe tab authorization      │
└──────────────────────────────▲───────────────────────────────┘
                               │ Native IPC / WebSocket
┌──────────────────────────────▼───────────────────────────────┐
│  jev-panerelay CLI / Agent Skill                             │
│  - Captures atomic snapshot.js (interactive DOM controls)    │
│  - Executes mouse clicks, scrolls, text inputs, and submits  │
└──────────────────────────────▲───────────────────────────────┘
                               │ HTTPS (sub-second API calls)
┌──────────────────────────────▼───────────────────────────────┐
│  OpenRouter                                                  │
│  - Decisions API: ~typesafe/jev-latest (actions)             │
│  - Completions API: google/gemini-2.5-flash (text inputs)    │
└──────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

1. **Panerelay**:
   - Install the official [Panerelay Chrome Extension](https://chromewebstore.google.com/detail/panerelay/panplnkjlkoceaonlmpdekjphgmbggmi).
   - Set up the local Native Host:
     ```bash
     npx --yes @panerelay/setup
     ```
   - Confirm Panerelay is connected and ready:
     ```bash
     npx --yes @panerelay/setup doctor
     ```
2. **OpenRouter API Key**:
   - An API key with access to the OpenRouter Decisions API (`https://openrouter.ai/`).

---

## Installation

### Option A: Install globally via `uv` (Recommended)

```bash
uv tool install git+https://github.com/hdkiller/jev-panerelay.git
```
*(Or clone locally and install with `uv tool install --editable .`)*

### Option B: Clone and run directly

```bash
git clone https://github.com/hdkiller/jev-panerelay.git ~/Develop/pets/jev-panerelay
cd ~/Develop/pets/jev-panerelay
uv sync
```

---

## Configuration

Create a `.env` file in the project directory (or export the variables in your shell):

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Required: Your OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-...

# Decisions Model (defaults to OpenRouter's Jev endpoint)
TYPESAFE_BASE_URL=https://openrouter.ai/api/alpha/decisions
TYPESAFE_MODEL=~typesafe/jev-latest

# Text Generation Helper (only invoked for TYPE_TEXT operations)
TEXT_MODEL_BASE_URL=https://openrouter.ai/api/v1
TEXT_MODEL=google/gemini-2.5-flash
TEXT_MODEL_REASONING=none

# Panerelay Gateway
BU_CDP_URL=http://127.0.0.1:43827/cdp/browser-use
BU_NAME=panerelay
```

---

## CLI Usage

### 1. Start at a URL with a Goal

```bash
jev-panerelay "https://news.ycombinator.com" "Click on the comments of the first story"
```
Or with explicit options:
```bash
jev-panerelay --url "https://en.wikipedia.org" --task "Search for 'Python programming language' and open the article"
```

### 2. Drive an Already Open Chrome Tab

List all currently open tabs in your live browser:
```bash
jev-panerelay --list-tabs
```

Attach to a specific open tab using its target ID:
```bash
jev-panerelay --tab "ceae01cd-2768-434f-bdaf-8569efd0a4ce" --task "Fill out the contact form with sample data"
```

### 3. Command-Line Options

```
usage: jev-panerelay [-h] [-u OPT_URL] [-t OPT_TASK] [--tab TAB_ID]
                     [--list-tabs] [-m MAX_STEPS] [--close] [-q]
                     [pos_url] [pos_task]

options:
  -u, --url URL          Starting page URL
  -t, --task, --goal     Natural language goal / task description
  --tab TAB_ID           Attach to an existing open tab ID instead of creating one
  --list-tabs            List all open browser tabs accessible via Panerelay
  -m, --max-steps N      Maximum steps before stopping (default: 30)
  --close                Close the browser tab when finished (default: keep open)
  -q, --quiet            Suppress step-by-step logs
```

---

## Using as an Agent Skill (Panerelay Side Panel)

You can use `jev-panerelay` as a skill for conversational AI agents (**Claude Code**, **OpenCode**, **Codex**, or **Antigravity**) running inside the **Panerelay Chrome Side Panel**.

This lets the conversational agent act as the high-level planner, while delegating the ultra-fast UI clicks and typing to Jev.

### 1. Install the Skill

Create `~/.agents/skills/jev-browser/SKILL.md`:

```markdown
---
name: jev-browser
description: Ultra-fast browser automation using TypeSafe Jev via Panerelay and OpenRouter. Use when asked to operate the browser, click buttons, fill forms, search, select options, or complete tasks on web pages in the user's Chrome session.
---

# Jev Browser Automation

Use `jev-panerelay` for ultra-fast, sub-second browser automation directly inside the user's live Chrome browser.

## Operating the Current Tab
When Panerelay provides an injected context with `<target-uuid>`:

```bash
jev-panerelay --tab "<target-uuid>" --task "<task description>"
```

## Operating from a URL
```bash
jev-panerelay --url "https://example.com" --task "<task description>"
```
```

### 2. Chat in the Side Panel

When browsing in Chrome:
1. Open the **Panerelay Side Panel**.
2. Click **"Operate this page"** or ask:
   > *"Find the pricing page and summarize the tier options."*
3. The side panel agent runs `jev-panerelay --tab <uuid> --task "Navigate to pricing"`, which reaches the page in ~1–2 seconds!

---

## How It Works Under the Hood

1. **Atomic DOM Snapshot (`snapshot.js`)**: Evaluates visible, interactive elements (buttons, inputs, links, dropdowns) and extracts bounding boxes, accessibility roles, labels, and scroll states into a clean JSON action space.
2. **Action Policy (`choose`)**: Sends the page state and criteria to OpenRouter's Decisions API. Jev outputs probability distributions across operations (`CLICK`, `TYPE_TEXT`, `SELECT`, `SCROLL`, `WAIT`, `DONE`, `BLOCKED`) and target elements.
3. **Target Execution**: The CDP client hit-tests the exact DOM node identity, scrolls if needed, and dispatches native hardware input events (`mousePressed`, `mouseReleased`, `insertText`).
4. **Resilience**: Freshness markers guarantee the target node hasn't mutated or shifted between observation and action; stale pages trigger an instant re-observation.

---

## Contributing

Contributions, feedback, and pull requests are welcome!
Please feel free to open an issue or submit a PR on GitHub.

---

## License

MIT © [László Rácz](https://github.com/hdkiller)
