# TypeSafe Jev Gate for Hermes

> A fail-closed policy gate for Hermes Agent tool calls.
>
> Let Jev inspect the risky calls. Keep Hermes in control.

[![Hermes Agent plugin](https://img.shields.io/badge/Hermes%20Agent-plugin-7c3aed)](https://github.com/NousResearch/hermes-agent)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![OpenRouter Decisions API](https://img.shields.io/badge/powered%20by-OpenRouter-111827)](https://openrouter.ai/)

TypeSafe Jev Gate adds a second policy signal before Hermes performs side-effecting tool calls. It classifies the action, redacts sensitive arguments, sends bounded structured state to Jev, and routes the result into Hermes's existing approval flow.

This is a safety layer, not an autonomous permission slip. Hermes hardline blocks, normal authorization, and human approval remain authoritative.

## Why it exists

Tool-using agents need more than a single yes/no check. A request can be technically valid and still be risky because it:

- sends data outside the machine
- repeats an expensive or destructive action
- changes external state when the user's intent is unclear
- contains secrets or prompt-injection content
- arrives while the agent is already performing too many side effects

Jev gives Hermes a typed decision signal for those cases. When Jev is unavailable or uncertain, this plugin fails closed into Hermes approval.

## What it does

- Lets read-only tools and obvious safe terminal commands pass without a network call.
- Evaluates side-effecting tools with redacted, bounded arguments.
- Evaluates paid/external tools such as web search and extraction before they leave the process.
- Escalates repeated calls and excessive side effects in one turn.
- Applies stricter preflight treatment to paid tools.
- Caches Jev decisions briefly to avoid duplicate spend.
- Gives ambiguous multi-step requests an advisory route hint through `pre_llm_call`.
- Blocks clear secret-egress and prompt-injection risks.
- Sends irreversible or uncertain calls to Hermes's normal approval gate.
- Writes metadata-only audit records to `$HERMES_HOME/logs/jev-gate.jsonl`.

## Quick start

### 1. Configure the API key

Use an existing OpenRouter key or create one at <https://openrouter.ai/keys>. Store it as the secret `OPENROUTER_API_KEY` in the active Hermes profile.

The plugin calls the OpenRouter Decisions API at:

```text
https://openrouter.ai/api/alpha/decisions
```

It uses the `~typesafe/jev-latest` model slug. This is not the normal chat-completions endpoint, and Jev does not replace Hermes's conversational model.

### 2. Enable the plugin

```bash
hermes plugins enable typesafe-jev-gate
```

Restart Hermes or its gateway after enabling it.

## Safety model

```text
Hermes hardline blocks
        ↓
TypeSafe Jev Gate
        ↓
Hermes authorization and approval
        ↓
Tool execution
```

The gate can recommend allow, deny, or approval. It cannot override Hermes's existing authorization rules. A Jev outage, malformed response, or uncertain decision is treated as a reason to ask for approval, not a reason to allow the call.

## Architecture

| File | Role |
| --- | --- |
| `config.py` | Policy constants and limits |
| `redaction.py` | Tool classification, secret redaction, fingerprints, and safe action summaries |
| `client.py` | OpenRouter Decisions API client and short-lived cache |
| `policy.py` | Jev request payloads and response parsing |
| `budget.py` | Per-turn repetition and side-effect budgets |
| `hooks.py` | Hermes hook adapters and approval directives |
| `__init__.py` | Minimal plugin entry point |

## Development

Run the test suite:

```bash
uv run pytest
```

Run linting:

```bash
uv run --with 'ruff>=0.16,<0.17' ruff check .
```

## Project status

This plugin is experimental and currently tracks the deployed Hermes plugin at version `0.3.0`. Review the policy behavior and audit output before enabling it in a production Hermes profile. The project is intentionally conservative: when in doubt, it asks Hermes to ask you.

## Keywords

Hermes Agent, Jev, TypeSafe, AI safety, agent safety, tool authorization, tool calling, policy engine, policy gate, OpenRouter, prompt injection defense, secret redaction, human-in-the-loop, approval workflows, fail closed, autonomous agents, LLM security, Python plugin.

## License

See the repository for license details.
