<p align="center">
  <img src="https://img.shields.io/badge/model-jev--latest-14b8a6" alt="jev-latest">
  <img src="https://img.shields.io/badge/POST-api.typesafe.ai%2Fv1%2Fsystemone-0f766e" alt="System One endpoint">
  <img src="https://img.shields.io/badge/gate-execute%20%2F%20confirm%20%2F%20reject-134e4a" alt="execute confirm reject">
  <img src="https://img.shields.io/badge/python-3.10%2B-3776ab" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-5eead4" alt="MIT">
  <img src="https://img.shields.io/badge/not-a%20coding%20agent-1f2937" alt="Not a coding agent">
  <img src="https://img.shields.io/badge/not-an%20LLM%20chat-111827" alt="Not an LLM chat">
</p>

<p align="center"><b>Proposed tool call in. Typed answers out. Code decides execute / confirm / reject.</b><br>
<code>POST /v1/systemone</code> · <code>jev-latest</code> · Choice + Score + Noul in one call · compose the gate in Python.</p>

# JevHarness

**JevHarness is an agent tool-call harness, not a coding agent and not a chatbot.** It does not write code, stream tokens, or talk to the user. You hand it a proposed agent step (`goal` + tool name + args). It asks [Jev](https://docs.typesafe.ai/concepts/system-one) one mixed request. **Your code** turns the typed answers into `execute`, `confirm`, or `reject`.

Sibling of [`kevin9327/jev-master`](https://github.com/kevin9327/jev-master) (compose-layer demos). This repo is the pre-execution gate for a single tool call.

```
proposed step  -->  POST https://api.typesafe.ai/v1/systemone  (model: jev-latest)
                    Choice verdict + Score irreversible + Noul on_task
                    -->  compose_harness_gate() in this repo
                    -->  execute | confirm | reject
```

## What Jev returns (not what this repo invents)

| Question | Primitive | Meaning |
| --- | --- | --- |
| **verdict** | Choice `allow` / `ask` / `deny` | Should the call run, wait for a human, or be refused? |
| **irreversible** | Score, 3 levels | Easy undo / reversible with effort / hard to unwind |
| **on_task** | Noul | "This tool call advances the stated goal" |

All three mix in a **single** `POST https://api.typesafe.ai/v1/systemone`. Jev does not execute the tool.

## What code composes

`compose_harness_gate` is ordinary Python, inspired by TypeSafe [confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing):

| Condition | `action` | `reason` |
| --- | --- | --- |
| `verdict.confidence < 0.6` | `reject` | `low_confidence` |
| `on_task.noul < 0.4` | `reject` | `off_task` |
| Choice is `deny` | `reject` | `denied` |
| Choice is `ask` **or** `irreversible.score >= 1.5` | `confirm` | `high_stakes_ask` |
| otherwise | `execute` | `allowed` |

Change a threshold, not a prompt.

## Quickstart

Python 3.10+. Get a TypeSafe key from the [dashboard](https://console.typesafe.ai/settings/keys) and export `TYPESAFE_API_KEY` (never commit it).

```bash
git clone https://github.com/kevin9327/jev-harness
cd jev-harness
python -m pip install -e ".[dev]"
python -m pytest
python -m jevharness --state examples/rm-step.json
```

The command prints JSON with typed `answers` plus a composed `decision` (`action` + `verdict` + `reason`). Same shape for a safe read:

```bash
python -m jevharness --state examples/read-step.json
```

`evaluate(..., transport=...)` is injectable. Tests never hit the network.

## Examples

`examples/rm-step.json` — destructive:

```json
{
  "goal": "Tidy the working tree after a failed experiment",
  "tool": "bash",
  "args": { "command": "rm -rf src/" }
}
```

`examples/read-step.json` — reversible:

```json
{
  "goal": "Understand how the harness composes Jev answers into execute/confirm/reject",
  "tool": "read_file",
  "args": { "path": "src/jevharness/gate.py" }
}
```

## Secrets

Runtime-only. This tree gitignores `.env`, `jevkey.txt`, `apikey_*`, and `.venv`. Do not paste keys into README, tests, or logs. The loader reads `TYPESAFE_API_KEY`, then a local key file **outside** the repo.

## Layout

```
src/jevharness/
  client.py   POST /v1/systemone (stdlib urllib)
  answers.py  Choice / Score / Noul parsers
  gate.py     questions + compose_harness_gate + run_step
  cli.py      python -m jevharness
  key.py      env / local file, never printed
```

Docs: [Introduction](https://docs.typesafe.ai/introduction) · [API](https://docs.typesafe.ai/api) · [Confidence routing](https://docs.typesafe.ai/patterns/confidence-routing)

Not affiliated with TypeSafe. JevHarness does not run the tool call; the agent host still must sandbox, allowlist, and keep a kill switch.

## License

MIT. See [LICENSE](LICENSE).
