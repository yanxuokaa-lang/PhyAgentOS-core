# jev-judgment

[English](README.md) | [한국어](README.ko.md)

An [Agent Skill](https://agentskills.io) that sends closed judgments to
[TypeSafe Jev](https://typesafe.ai) and acts on the probabilities. The
main coding model keeps writing code. Jev answers yes/no, choice, and
score questions in ~250 ms so the agent guesses less and interrupts the
user only when a person must decide.

This repository is the skill only. Install it with the
[skills CLI](https://skills.sh); it does not depend on any particular
agent harness.

## Install

```bash
npx skills add HyunjunJeon/jev-judgment
npx skills add HyunjunJeon/jev-judgment -g -a claude-code codex
```

Then set `TYPESAFE_API_KEY` in the environment or in `<cwd>/.env`.
Mint a key at [console.typesafe.ai](https://console.typesafe.ai).
Without a key the bundled script fails open and the agent continues as
if the skill were not installed.

Requires `python3` 3.9+ (standard library only) and network access to
`api.typesafe.ai`.

## What it does

Call Jev at three points:

1. **Before asking the user a closed question** — if the conversation
   already determines the answer, proceed and say so; otherwise ask.
2. **Before a command that may destroy data, leak secrets, or reach
   beyond the task** — stop and confirm when any dimension crosses its
   threshold.
3. **After a command fails** — classify the failure and check the output
   for secrets before retrying.

Jev's confidence is evidence about the context, not permission to act.
Deletion outside the request, breaking changes, new dependencies, paid
or remote actions, and anything the user said to ask about always go to
the user.

The request body is the TypeSafe API as-is:
`POST https://api.typesafe.ai/v1/systemone` with `{state, questions}`.
The bundled `scripts/jev.py` redacts credentials, truncates long
strings, and never blocks the agent on a network error.

Full protocol, thresholds, and question templates:
[`skills/jev-judgment/SKILL.md`](skills/jev-judgment/SKILL.md).

## Layout

```
jev-judgment/
├── skills/jev-judgment/
│   ├── SKILL.md
│   ├── scripts/jev.py
│   └── references/
│       ├── questions.md
│       └── api.md
├── LICENSE
└── README.md
```

The `skills/<name>/SKILL.md` layout is what
`npx skills add owner/repo` discovers.

## License

MIT
