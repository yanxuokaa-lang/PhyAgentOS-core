# 🧠⚡ Dual-Process AI

[![CI](https://github.com/taro1985/dual-process-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/taro1985/dual-process-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Route cheap decisions to a calibrated classifier. Send only the hard ones to an LLM.

> "Don't send everything to an LLM. Fast brain decides, deep brain thinks."

---

## 💡 The Idea

Most AI applications send every request to a large language model — including trivial ones like "show server status" or "list repos". That is slow, expensive, and unnecessary.

Dual-Process AI splits the work along the lines Kahneman drew:

|                    | System 1 (Fast)                          | System 2 (Slow)                      |
| ------------------ | ---------------------------------------- | ------------------------------------ |
| **Kahneman**       | Intuitive, automatic                     | Deliberate, analytical               |
| **Implementation** | [Jev](https://typesafe.ai) (TypeSafe AI) | Gemini 3.8 Flash                     |
| **Output**         | Typed decision + confidence              | Free-form text                       |
| **Latency**        | ~70–500 ms                               | 500–5000 ms                          |
| **Input cost**     | $0.042 / 1M tokens (output free)         | Standard token pricing               |
| **Use case**       | Routing, classification, safety gates    | Reasoning, code generation, analysis |

The key mechanism is not speed — it is **calibrated confidence**.

Jev is trained with RLCD (Reinforcement Learning for Calibrated Decisions), which optimizes probability calibration against verifiable ground truth rather than human preference. That means the confidence score it returns can actually be used as a threshold. An RLHF-trained LLM asked "how sure are you?" gives a number shaped by what humans like to hear; Jev gives a number you can put in an `if` statement.

That single property is what makes the whole pattern work:

```
confidence >= THRESHOLD  →  System 1 decides, done
confidence <  THRESHOLD  →  escalate to System 2
```

```
User Input
    │
    ▼
┌────────────────────────────┐
│  System 1 (Jev)            │
│  typed decision + conf.    │
└──────────┬─────────────────┘
           │
   ┌───────┴────────┐
 conf ≥ τ        conf < τ
   │                │
   ▼                ▼
┌─────────┐  ┌──────────────────┐
│ Direct  │  │  System 2 (LLM)  │
│ Execute │  │  Gemini 3.8 Flash│
└─────────┘  └──────────────────┘
```

---

## ⚠️ Status

Jev was announced on 2026-09-15 and is currently in early-access behind a waitlist. Without an API key this repo runs in **degraded mode**: a keyword matcher stands in for System 1.

Degraded mode is not an equivalent System 1. It produces no calibrated confidence, so threshold-based escalation is replaced by a conservative rule — anything not on the allowlist escalates. Treat the keyword path as a way to run the code, not as a claim about the pattern.

---

## 📦 What's Included

| File               | Description                                                                             |
| ------------------ | --------------------------------------------------------------------------------------- |
| `router.py`        | Core router — System 1 classifies and scores, System 2 reasons                          |
| `safety_gate.py`   | PreToolUse hook for AI coding agents — blocks dangerous shell commands before execution |
| `hermes_gate.py`   | Autonomous agent integration hook for HermesAgent command execution loops               |
| `memory_scorer.py` | Sub-millisecond episodic memory & context relevance scorer (JevMemoryScorer)            |
| `tool_pruner.py`   | Sub-millisecond dynamic MCP tool selector / pruner for token efficiency & accuracy      |
| `demo_cli.py`      | Interactive terminal CLI demo showcasing Fast & Slow AI in real-time                    |
| `benchmark.py`     | Automated benchmark suite comparing DPAI against legacy All-to-LLM                      |
| `discord_bot.py`   | Discord bot with rich embeds, mobile-optimized cards, and remote ops (Docker/Git)       |
| `.env.example`     | Template for API keys                                                                   |

---

## 🚀 Quick Start

### Installation

```bash
# Install directly from GitHub
pip install git+https://github.com/taro1985/dual-process-ai.git

# Or install for local development with uv
git clone https://github.com/taro1985/dual-process-ai.git
cd dual-process-ai
uv pip install -e .
```

### Quick Run

```bash
cp .env.example .env    # add GEMINI_API_KEY, and TYPESAFE_API_KEY if you have one

# Interactive Demo (Instant ANSI interactive experience)
uv run python demo_cli.py

# Benchmark (Simulates 850 requests, measures cost & latency reduction)
uv run python benchmark.py

# Run bot or router
uv run python router.py
uv run python discord_bot.py
```

Hook configuration for AI coding agents:

```json
{
  "hooks": [
    {
      "event": "PreToolUse",
      "command": "python /path/to/safety_gate.py",
      "timeout_ms": 5000
    }
  ]
}
```

---

## 🏗️ Architecture

### Router (`from dpai import DualProcessRouter`)

```python
from dpai import DualProcessRouter

router = DualProcessRouter(threshold=0.85, use_adaptive_threshold=True)

# System 1: Low-risk read-only (0.02ms, $0)
result = router.process("What's the server status?")
print(result["output"])

# System 2: Deep reasoning escalation
result = router.process("Design a microservice architecture for this")
print(result["output"])
```

`JevClassifier` sends the input plus a typed question set and gets back a choice and a confidence score in one pass. `GeminiReasoner` runs only on escalation, and receives conversation history so multi-turn dialogue stays coherent.

The threshold is the one knob worth tuning. Lower it and you pay more but misroute less; raise it and the opposite. Pick it from your own escalation data, not from this README.

### Safety Gate (`safety_gate.py`)

```
rm -rf /        → DENY
DROP DATABASE   → DENY
fork bomb       → DENY
echo hello      → ALLOW
git status      → ALLOW
```

This is a guardrail, not a security boundary. The standalone path is a blocklist, and blocklists are bypassable by construction — variable expansion, base64, `find -delete`, aliases, and anything else that reaches the same syscall by a different spelling will pass. It exists to stop an agent from doing something stupid by accident, not to stop an adversary doing something malicious on purpose.

Routing a command through Jev raises the ceiling — TypeSafe's own demos cover prompt-injection resistance and PII detection, which is the same shape of problem — but does not turn this into a sandbox. Use a container for that.

---

## 🎯 Design Principles

1. **LLM as last resort** — don't invoke a frontier model for a lookup-table task.
2. **Routing fails open** — low confidence escalates to System 2. The router never refuses.
3. **Safety fails closed** — the gate is the one component that blocks. Unparseable input is denied, not passed.
4. **Trust the number, not the vibe** — escalation is driven by a calibrated score, which is why the classifier choice matters.
5. **Cost-aware** — every response reports which system handled it and what it cost.

---

## 📊 Performance

Measured on a Sony VAIO, 2 cores, 3.7 GB RAM — the point being that the fast path needs no local GPU and no local model.

### 📊 Benchmark Results (850 Requests Simulation)

| Metric                              | All-to-LLM (Legacy) | DPAI (Dual-Process) | Improvement                    |
| :---------------------------------- | :------------------ | :------------------ | :----------------------------- |
| **Total Processed Requests**        | 850                 | 850                 | -                              |
| **System 1 Instant Responses ($0)** | 0 (0%)              | 500 (58.8%)         | **+58.8% fast path**           |
| **LLM Invocations**                 | 850                 | 200                 | **-76.5% calls**               |
| **Avg System 1 Latency**            | N/A                 | **0.020 ms**        | **Sub-millisecond**            |
| **Dangerous Commands Blocked**      | 0 (Vulnerable)      | 150 (100% Denied)   | **100% Mechanical Hard Block** |
| **Estimated Cost**                  | $0.2104             | $0.0495             | **-76.5% cost**                |
| **Total Projected Latency**         | 552.5 s             | 130.0 s             | **-76.5% latency**             |

Run `uv run python benchmark.py` to reproduce these measurements.

---

## 🔗 Prior Art

Model routing and cascading are established ideas — RouteLLM, semantic-router, and LLM cascades all cover the same ground. What is new here is the classifier: a non-autoregressive model that returns a calibrated score in one pass makes confidence-threshold routing practical in a way that an embedding-similarity router or a small LLM judge does not.

---

## 🤝 Credits

- Kahneman, D. (2011). _Thinking, Fast and Slow_
- [TypeSafe AI / Jev](https://typesafe.ai) — System 1 classifier
- [Google Gemini](https://ai.google.dev) — System 2 reasoning

---

## 📄 License

MIT
