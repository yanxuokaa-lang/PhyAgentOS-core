# Claude Jev Warden (Claude Code + TypeSafe Jev)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Hooks%20Ready-6366f1.svg)](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview)
[![TypeSafe Jev](https://img.shields.io/badge/Evaluator-TypeSafe%20Jev%201.13-10b981.svg)](https://typesafe.ai)

> **"System prompts are suggestions; Jev PreToolUse hooks are physical laws."**

**Claude Jev Warden** is an autonomous quality gate and aesthetic supervisor for [Claude Code](https://github.com/anthropics/claude-code) powered by **TypeSafe Jev** (`typesafe/jev-1.13`). Operating at the OS process boundary via Claude Code's `PreToolUse` event hook, it intercepts tool executions (`Write`, `Edit`, `MultiEdit`) before changes touch disk, evaluates the draft using Jev's non-autoregressive decision model, and physically blocks substandard work (`Exit Code 2`) while injecting actionable diagnostic feedback into the agent's context.

---

## Direct Jev CLI Commands

You can run TypeSafe Jev evaluations directly from the command line without launching Claude Code:

### 1. Audit Any File with Jev
```bash
# Audit any SVG directly using TypeSafe Jev (1.13)
node bin/jev-audit.js path/to/illustration.svg
```

Output example:
```text
Auditing SVG with TypeSafe Jev (1.13)...
Target: monkey_bike_doubao_warden.svg (20482 bytes)

================ JEV AUDIT REPORT ================
Model:         typesafe/jev-1.13
Quality Score: 84.0% (Approval threshold: >= 80.0%)
Verdict:       approve_dynamic_exquisite (Confidence: 87.0%)
Deficiency:    already_exquisite_and_dynamic
Result:        APPROVED [PASS]
==================================================
```

### 2. Run Benchmark Test Commands
```bash
# Audit the Jev-supervised self-healed output (Score: 84% PASS)
npm run test:supervised

# Audit the unsupervised baseline output (Score: 73% FAIL - desynced fake pedaling)
npm run test:unsupervised
```

### 3. Raw Jev Decisions API Call via cURL
TypeSafe Jev uses the non-autoregressive `{state, questions}` decision schema:
```bash
curl https://openrouter.ai/api/alpha/decisions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "typesafe/jev-1.13",
    "state": {
      "theme": "Dynamic Animated SVG: Monkey riding a bicycle",
      "file": "monkey_bike.svg",
      "svg_snippet": "<svg ...>"
    },
    "questions": {
      "is_exquisite_and_dynamic": {
        "type": "noul",
        "instructions": "Does this SVG qualify as an exquisite dynamic animated illustration?"
      },
      "animation_verdict": {
        "type": "choice",
        "instructions": "Evaluate the dynamic animation implementation.",
        "criteria": {
          "reject_static_or_no_animation": "Completely static or broken animation.",
          "reject_crude_artwork": "Crude artwork or lacks mechanical details.",
          "approve_dynamic_exquisite": "Smooth continuous animations with rich artwork."
        }
      }
    }
  }'
```

---

## How Claude Code + Jev Hook Works

```
[Claude Code Agent] ─── attempts Write/Edit tool call ───┐
                                                         ▼
                                          [PreToolUse Hook: warden.js]
                                                         │
                                    calls TypeSafe Jev Decision Endpoint
                                    (Evaluates motion, kinematics, geometry)
                                                         │
                         ┌───────────────────────────────┴───────────────────────────────┐
                         ▼                                                               ▼
           Quality >= 80% [Approved]                                       Quality < 80% [Rejected]
                   Exit 0                                                          Exit 2
                         │                                                               │
             Writes SVG to disk                                          Hard process interception:
             Mission completed!                                          1. Blocks file from saving
                                                                         2. Injects exact diagnostics:
                                                                            - Missing mechanical details
                                                                            - Inverse kinematics desync
                                                                            - Broken perspective
                                                                         3. Forces agent into self-healing loop
```

---

## Empirical Benchmark: Strong vs. Weak Models Under Jev Supervision

We conducted head-to-head empirical testing on the challenging theme **"Dynamic Animated SVG: Monkey Riding a Bicycle"** across both high-tier and mid/weak reasoning models:

| Dimension | Doubao (`doubao-seed-evolving`) [Unsupervised] | Doubao [Supervised by Jev] | DeepSeek (`deepseek-flash`) [Unsupervised] | DeepSeek [Supervised by Jev] |
| :--- | :--- | :--- | :--- | :--- |
| **Jev Quality Score** | **73.0%** (Fail) / Draft 1: **11.0%** | **84.0%** (Production Pass) | **86.0%** (Single-shot Pass) | **92.0%** (Exquisite Grade) |
| **Head Anatomy & Perspective** | **90° Horror Frontal View** staring at user, neck detached & floating in sky | **Natural Side Profile** with cycling cap, firmly locked into shoulder/neck | Standard side view, static anchor | Standard side view, dynamic riding tuck |
| **Pedal Kinematics** | Generic sinusoidal fake pump (13° ~ -9°), feet fly off 360° rotating crank | **Autonomous Python IK Solver**: 16-frame matrix baking, feet locked to pedals | SMIL vertex interpolation (rubber-band elastic stretching) | **Offline Node IK Solver**: cosine theorem baking, error < 3.3px |
| **Self-Healing Behavior** | None (wasted 3 turns adjusting cloud height over sun) | Interception forced model to invoke Bash + Python to solve trigonometry | None (content with baseline) | Autonomous Playwright DOM testing & shadow DOM bugfix |

### Key Takeaways:
- **For Strong Models (DeepSeek)**: Jev acts as an **optimizer**, eliminating hidden physical flaws and pushing good drafts to exquisite perfection (86% → 92%).
- **For Weaker Models (Doubao)**: Jev acts as a **survival engine & IQ multiplier**. Without supervision, the model produces unviable, broken drafts (11% / 73%). Under physical interception, the model is forced to wake up its tool execution capabilities, write numerical calculation scripts, and achieve viable output (84%).

---

## Interactive Comparison Dashboard

This repository includes a standalone interactive visualizer: [compare.html](compare.html).

Open [compare.html](compare.html) in any browser to toggle between:
1. **Doubao Benchmark**: Live side-by-side comparison of the unsupervised broken model vs. the supervised kinematics-baked model.
2. **DeepSeek Benchmark**: Live comparison of SMIL path morphing vs. rigid-body cosine IK solver.
3. **Comprehensive Metric Matrix**: Detailed breakdown of degrees of freedom, error tolerances, and autonomous reasoning traces.

---

## Quick Start

### 1. Prerequisites
- [Node.js](https://nodejs.org) >= 20.12 (with native `process.loadEnvFile` and `fetch`)
- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) CLI installed
- An [OpenRouter](https://openrouter.ai) API key with access to `typesafe/jev-1.13`

### 2. Installation
```bash
git clone https://github.com/connectedGraph/claude-jev-warden.git
cd claude-jev-warden
```

Create your `.env` file:
```bash
cp .env.example .env
```
Edit `.env` and set:
```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. Configure Claude Code
The hook is already configured in `.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "node .claude/hooks/warden.js"
          }
        ]
      }
    ]
  }
}
```

### 4. Run Claude Code
Launch Claude Code in the project directory and challenge it to generate an illustration:
```bash
claude
```
Prompt example:
> "Please create an elaborate, dynamic animated SVG of a monkey riding a bicycle, with spinning wheels, pedaling crank, and life-like posture motion, saving to monkey_bike.svg."

Watch the Jev Warden intercept low-effort attempts and force Claude to continuously refine its artwork until it meets the Art Director's standards!

---

## Repository Structure

```
claude-jev-warden/
├── bin/
│   └── jev-audit.js          # Direct CLI tool to audit any SVG with TypeSafe Jev
├── .claude/
│   ├── hooks/
│   │   └── warden.js         # PreToolUse hook implementation calling Jev
│   └── settings.json         # Hook matcher configuration
├── compare.html              # Interactive 4-quadrant benchmark dashboard
├── monkey_bike_deepseek_nowarden.svg # DeepSeek baseline output
├── monkey_bike_deepseek_warden.svg   # DeepSeek supervised output
├── monkey_bike_doubao_nowarden.svg   # Doubao baseline output
├── monkey_bike_doubao_warden.svg     # Doubao supervised output
├── monkey_bike_doubao_draft1.svg     # Doubao unassisted first draft
├── .env.example              # Environment variables template
├── package.json
└── README.md
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
