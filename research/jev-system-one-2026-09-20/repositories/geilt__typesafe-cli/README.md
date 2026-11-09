# TypeSafe CLI

Small Python CLI + agent skill for [TypeSafe System One](https://docs.typesafe.ai/introduction) (Jev).

It evaluates a **state** against typed **Choice / Score / Noul** questions and prints structured answers. It is **not** a chat model: no generated prose, no JSON-from-prose parsing.

Vendor docs: https://docs.typesafe.ai/llms.txt

Requires **Python 3.9+** (stdlib only: `urllib`, `json`, `argparse`). Linux, macOS, or any `python3`.

**When to use it (full writeup):** [USE-CASES.md](USE-CASES.md)

## Setup

```bash
git clone https://github.com/geilt/typesafe-cli.git
cd typesafe-cli
chmod +x typesafe

# API key — keep it out of git
export TYPESAFE_API_KEY='apikey_…'

# optional: put the binary on PATH
mkdir -p ~/.local/bin
cp typesafe ~/.local/bin/typesafe
# ensure ~/.local/bin is on PATH
```

Install the agent skill (Claude / Codex / Grok / other Agent Skills hosts):

```bash
mkdir -p ~/.agents/skills/typesafe
cp skills/typesafe/SKILL.md ~/.agents/skills/typesafe/SKILL.md
```

Optional env:

| Variable | Default |
|----------|---------|
| `TYPESAFE_API_KEY` | required unless `--creds` |
| `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` |
| `TYPESAFE_DEFAULT_MODEL` | `jev-latest` |

`--creds path.json` is an alternative to the env var. JSON shape: `{"api_key":"…"}`.

## Commands

```bash
typesafe info                 # endpoints; does not print the key
typesafe models
typesafe smoke                # docs quickstart example
typesafe ask --state "…" --noul is_urgent="Does this convey urgency?"
typesafe ask --state-file s.json --questions-file q.json --json
```

Endpoints used:

- `POST https://api.typesafe.ai/v1/systemone` — evaluate
- `GET https://api.typesafe.ai/v1/models` — list models
- Auth: `Authorization: Bearer $TYPESAFE_API_KEY`

## When to use it

Use TypeSafe when **code** needs a snap judgment over unstructured input and you already know the answer *shape*: route, classify, score, yes/no, rerank, guardrail.

Do **not** use it to generate text, write code, or replace a deterministic rule. Ask atomic questions; send every independent question about the same state in one `ask`; combine answers in your code. Noul `0.5` means unsure, not “medium.” Choice/Score `confidence` is how peaked the distribution is.

See [USE-CASES.md](USE-CASES.md) for when to use TypeSafe vs a chat model, how to write questions, and first slices. See `skills/typesafe/SKILL.md` for the full flag set and how to read answers.
