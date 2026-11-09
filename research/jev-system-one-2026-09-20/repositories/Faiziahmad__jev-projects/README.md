# jev-projects

7 projects built with [TypeSafe Jev](https://typesafe.ai) — System One AI model with calibrated probabilities.

## Dev Tools

| Package | What it does | Install |
|---------|-------------|---------|
| [jeval](./jeval/) | LLM output evaluator — scores relevance, safety, tone and more | `pip install jeval` |
| [jev-fsm](./jev-fsm/) | Probabilistic state machine with Jev-powered transitions and guards | `pip install jev-fsm` |
| [jev-soc](./jev-soc/) | SOC alert triage — auto-close noise, auto-page critical incidents | `pip install jev-soc` |
| [jevops](./jevops/) | Pentest findings classifier — batch classify nmap/ffuf/wpscan output | `pip install jevops` |

## Games

| Game | What it does |
|------|-------------|
| [verdict](./verdict/) | AI courtroom judge — argue cases, Jev scores logic and persuasion |
| Snake | Classic snake with Jev play-style analysis after each game |
| BRAWL | 2-player fighter with Jev combat analysis |

## Requirements

```bash
export TYPESAFE_API_KEY="your-key-here"
```

Get early access: [typesafe.ai](https://typesafe.ai)

## How Jev works

- **Score** — 0 to N-1 float, calibrated probability across rubric levels
- **Noul** — 0.0–1.0 probability that a statement is true
- **Choice** — picks one option from a dict with confidence
- All questions in one API call — O(1) latency regardless of count
- $0.042/M input tokens · output free · 70–500ms latency
