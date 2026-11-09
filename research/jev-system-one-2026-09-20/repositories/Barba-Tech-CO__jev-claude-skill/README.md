# jev — a Claude Code skill for TypeSafe's Jev decision model

Jev writes no text. You send one `state` plus named typed questions — pick one, score this,
yes or no — and it answers all of them in a single ~0.4 s request for a fraction of a cent,
with calibrated probabilities your code branches on.

This skill wraps that for [Claude Code](https://claude.com/claude-code) (and anything else
that reads a `SKILL.md`), through any of three providers:

| provider | key | endpoint | model |
|---|---|---|---|
| TypeSafe direct | `TYPESAFE_API_KEY` | `POST https://api.typesafe.ai/v1/systemone` | `jev-latest` |
| Vercel AI Gateway | `AI_GATEWAY_API_KEY` | `POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model` | `typesafe-ai/jev` |
| OpenRouter | `OPENROUTER_API_KEY` | `POST https://openrouter.ai/api/alpha/decisions` | `typesafe/jev-1.13` |

The providers disagree on the wire — TypeSafe and OpenRouter call a yes/no question `noul`,
Vercel calls it `boolean` and returns confidence in `providerMetadata` — so the script
translates both ways. You always write `boolean` and always read the same answer shape.

## Install

Copy `jev/` into `~/.claude/skills/` (or a project's `.claude/skills/`), then store a key —
hidden prompt, one verification call, `~/.config/jev/credentials` at mode 0600:

```bash
python3 scripts/jev.py set-key --provider openrouter
```

## Use

```bash
python3 scripts/jev.py ask --state "retries charge us twice, fix it TODAY" --questions '{
  "urgent": {"type": "boolean", "instructions": "Does this express urgency?"},
  "team": {"type": "choice", "instructions": "Which team owns this?",
           "criteria": {"billing": "charges and refunds", "technical": "bugs and integrations"}},
  "anger": {"type": "score", "instructions": "How frustrated is the customer?",
            "criteria": ["Calm", "Concerned", "Furious"]}
}'
```

```json
{"provider": "openrouter", "model": "typesafe/jev-1.13-20260917", "latency_ms": 383,
 "usage": {"input_tokens": 421, "cost": 1.7682e-05},
 "answers": {"urgent": {"type": "boolean", "probability": 0.99},
             "team": {"type": "choice", "choice": "technical",
                      "probabilities": {"technical": 0.77, "billing": 0.23, "sales": 0.0},
                      "confidence": 0.66},
             "anger": {"type": "score", "score": 2.0, "label": "Very angry",
                       "probabilities": {"0": 0.0, "1": 0.0, "2": 1.0}, "confidence": 1.0}}}
```

`python3 scripts/jev.py doctor` reports which providers hold a key and answer.
`python3 -m unittest discover -s tests` runs offline — every reply faked, no key needed.

[SKILL.md](SKILL.md) holds the rest: when to reach for it, what never to send, how to read a
fractional score, and recipes for routing, memory filtering, triage and grading.

Stdlib only, Python 3.8+. MIT. Jev and TypeSafe are products of TypeSafe AI; this project is
independent, and owes the idea to [hermes-jev-skills](https://github.com/kerpopule/hermes-jev-skills).
