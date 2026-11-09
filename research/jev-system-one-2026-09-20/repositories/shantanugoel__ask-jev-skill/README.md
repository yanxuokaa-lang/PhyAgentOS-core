# askjev

Hermes skill: call TypeSafe **Jev** (`jev-latest`) as a typed tiebreaker. Jev is not a chat model. It returns Choice / Score / Noul answers with probabilities so an agent can act or escalate.

## Install

```bash
mkdir -p "${HERMES_HOME:-$HOME/.hermes}/skills/autonomous-ai-agents/askjev"
cp -R SKILL.md scripts "${HERMES_HOME:-$HOME/.hermes}/skills/autonomous-ai-agents/askjev/"
```

Put `TYPESAFE_API_KEY` in `$HERMES_HOME/.env`. Never commit the key.

## Disable

Set `ASKJEV_DISABLED=1` in that `.env`, or delete the skill directory.

## Run

```bash
python3 scripts/askjev.py choice --state '...' --question 'Which path?' \
  --option a='...' --option b='...'
python3 scripts/eval.py   # live reliability suite (needs the API key)
```

See `SKILL.md` for when to call Jev, confidence gates, and pitfalls.
