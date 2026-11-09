# typesafe

CLI for [TypeSafe](https://typesafe.ai) Jev. Run it from a shell, or let an agent run it.

Jev answers `noul`, `choice`, and `score` questions over JSON `state`. It does not chat, and it only sees what you send.

## Install

Python 3.10+. API key: [TypeSafe console](https://console.typesafe.ai/settings/keys).

```bash
curl -fsSL https://github.com/maddygoround/typesafeai-cli/releases/latest/download/install.sh | bash
```

```bash
pipx install typesafeai-cli
```

`pip install typesafeai-cli` is the same package.

```bash
export TYPESAFE_API_KEY=apikey_…
```

## Usage

`typesafe ask` takes a state file and a questions file. Point each instruction at state with backticks.

```json
{
  "message": "I was charged twice for order A-104. Please refund the duplicate.",
  "policy": "Duplicate charges are eligible for an immediate refund."
}
```

```json
{
  "refund_requested": {
    "type": "noul",
    "instructions": "Does `message` request a refund?"
  },
  "intent": {
    "type": "choice",
    "instructions": "What does `message` ask for?",
    "criteria": {
      "refund": "The customer wants money returned",
      "information": "Explanation only",
      "other": "Something else"
    }
  }
}
```

[`examples/ticket`](examples/ticket) and [`examples/code-change`](examples/code-change) are full copies.

```bash
typesafe ask --state-file state.json --questions-file questions.json
typesafe noul "Does this request a refund?" --state "I was charged twice."
```

Keep those JSON files under `${TMPDIR:-/tmp}/codex/<project>/`. `typesafe skills install` copies the typesafe-cli skill. `typesafe auth status` reports `has_key` and nothing else.

## Commands

| | |
| --- | --- |
| `ask` | State file + questions file |
| `noul` / `choice` / `score` | One question |
| `find` | Search a file |
| `rank` | Order a JSON shortlist |
| `extract` | Pick a span already in the text |
| `verify` | Check a claim against a source |
| `screen` | Jailbreak / injection / sensitive-data / harm |
| `suggest-skill` | At most one skill name |
| `decide` | Map answers to yes / no / uncertain (no HTTP) |
| `models` | Model aliases |
| `smoke` | Live docs quickstart |
| `auth status` | Whether a key is loaded |
| `agent schema` | JSON command tree |
| `skills install` | Official TypeSafe skill + typesafe-cli |

Exit `0` answered, `1` request failed, `2` bad flags or questions.
