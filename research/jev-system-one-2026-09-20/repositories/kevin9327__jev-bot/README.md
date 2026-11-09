<p align="center">
  <img src="https://img.shields.io/badge/model-jev--latest-14b8a6" alt="jev-latest">
  <img src="https://img.shields.io/badge/POST-api.typesafe.ai%2Fv1%2Fsystemone-0f766e" alt="System One endpoint">
  <img src="https://img.shields.io/badge/primitives-Choice%20%2B%20Score%20%2B%20Noul-134e4a" alt="primitives">
  <img src="https://img.shields.io/badge/python-3.10%2B-3776ab" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-5eead4" alt="MIT">
  <img src="https://img.shields.io/badge/not-an%20LLM%20chat-111827" alt="Not an LLM chat">
</p>

<p align="center"><b>Support text in. Typed answers out. Code picks a canned reply.</b><br>
<code>POST /v1/systemone</code> · <code>jev-latest</code> · Choice + Score + Noul · <code>reply</code> / <code>escalate</code> / <code>block</code></p>

# JevBot

JevBot is a **support/moderation bot that is not an LLM chatbot**. Incoming user text is a System One `state`. One `POST https://api.typesafe.ai/v1/systemone` with `model: "jev-latest"` mixes **Choice + Score + Noul**. Python composes the action and selects a **fixed** reply from a `TEMPLATES` dict. Jev never generates the reply prose.

Sibling catalog of mixed-primitive apps: [kevin9327/jev-master](https://github.com/kevin9327/jev-master).

## Why this is not a chatbot

Large language models write paragraphs. Support software needs a judgment — *billing or technical?* *calm or abusive?* *does a human need to take this?* — and then a **known** message. Jev returns typed probabilities. This repo owns control flow and every string the user sees.

| Question id | Primitive | Returns |
| --- | --- | --- |
| `intent` | **Choice** `billing` \| `technical` \| `account` \| `off_topic` | `choice`, `probabilities`, `confidence` |
| `severity` | **Score** calm / frustrated / abusive | `score`, `legend`, `probabilities`, `confidence` |
| `needs_human` | **Noul** "A human agent should take this" | `noul` in `[0, 1]` |

`compose_bot_action` turns those answers into:

| Field | Meaning |
| --- | --- |
| `intent` | The Choice label |
| `action` | `reply` \| `escalate` \| `block` |
| `template_id` | `billing_help` / `tech_help` / `account_help` / `off_topic` / `human_handoff` / `blocked` |
| `reply` | The matching string from `TEMPLATES` in `jevbot.bot` |

Rules in code, not in a prompt:

- `needs_human.noul >= 0.8` or `severity.score >= 1.6` → **escalate** (`human_handoff`)
- abusive (`severity.score >= 2`) **and** noul high → **block** (`blocked`)
- `intent.confidence < 0.5` → **escalate**
- otherwise **reply** with the canned template for `intent`

## Quickstart

Python 3.10+. Get a TypeSafe key from the [dashboard](https://console.typesafe.ai/settings/keys) and export `TYPESAFE_API_KEY` (never commit it). A local file at `C:\Users\swsz9\Downloads\jevkey.txt` is also accepted.

```bash
git clone https://github.com/kevin9327/jev-bot
cd jev-bot
python -m pip install -e ".[dev]"
python -m pytest
python -m jevbot --state examples/stripe-ticket.txt
```

That command prints JSON `{ "answers", "decision" }` where `decision` is the compose dict (`intent`, `action`, `template_id`, `reply`). The reply is a constant from source, not model output.

Same entry point via the console script:

```bash
jev-bot --state examples/stripe-ticket.txt
```

## Example input

`examples/stripe-ticket.txt`:

```text
Hi, I've been trying to connect my Stripe account for 3 days and it keeps failing. I'm losing sales. Please help ASAP.
```

One mixed request asks intent (Choice), severity (Score), and needs_human (Noul). `compose_bot_action` maps that to a canned template.

## Architecture

```
user text (state)  -->  POST https://api.typesafe.ai/v1/systemone  (jev-latest)
                        typed answers (no prose)
                        -->  compose_bot_action() in this repo
                        -->  reply | escalate | block  +  TEMPLATES[template_id]
```

`jevbot.client.build_systemone_payload` / `evaluate` are separate from the composer so tests feed real-shaped answers with a fake transport and never hit the network.

## Secrets

The API key is runtime-only (`TYPESAFE_API_KEY` or the Downloads key file). This tree gitignores `.env`, `jevkey.txt`, `apikey_*`, and `.venv`. Do not paste keys into README, tests, or CI.

## Tests

```bash
python -m pytest
```

Tests call the **shipped** payload builder (Choice + Score + Noul in one body) and the **shipped** composer with real-shaped answers (`choice` + `probabilities` + `confidence`, `score` + `legend`, `noul` in 0–1). `run_bot` is exercised with a fake transport.

## License

MIT. See [LICENSE](LICENSE). Not affiliated with TypeSafe.
