# jev-skill — the Jev agent skill

Give any AI coding agent a fast, typed "fuzzy `if`": one skill that teaches it to
call the **Jev** (TypeSafe AI's System One model) Decision API for routing,
guardrails, scoring and gating — returning a **choice**, a **score**, or a
**yes/no probability** instead of free text.

## Install in Claude Code

```bash
claude plugin marketplace add codaaiteam/jev-skill
claude plugin install jev@jev-skill
```

## Any other agent

Paste into your agent:

> Install the Jev agent skill: fetch https://jevtypesafeai.com/skill/SKILL.md and
> follow it to call the Jev Decision API with my JEV_API_KEY.

Or drop the file in manually:

```bash
curl -o ~/.claude/skills/jev/SKILL.md --create-dirs \
  https://jevtypesafeai.com/skill/SKILL.md
```

## Get a key

The skill calls the hosted, metered Jev API at `https://jevtypesafeai.com/api/v1/decide`
(no TypeSafe waitlist). Get a `jv_live_` key at https://jevtypesafeai.com/pricing
and set it as `JEV_API_KEY`. Output tokens are free; you pay per input token.

Independent project — not TypeSafe AI. For official access see https://typesafe.ai.
