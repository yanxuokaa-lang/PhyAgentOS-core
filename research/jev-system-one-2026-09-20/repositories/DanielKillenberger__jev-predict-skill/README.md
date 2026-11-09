# jev-predict-skill

Predict another skill's next closed decision — without running that skill.

`jev-predict-skill` is a host agent skill. Point it at any other skill and it
reports the discrete outcome that skill *would* pick right now, with a
confidence and a probability over every outcome. It gets there by asking
[TypeSafe](https://typesafe.ai) **Jev** to make the pick, not by executing the
target skill.

## Why

Jev is TypeSafe's System One model. You send it a `state` and a typed question;
it returns a typed answer — a `Choice`, a `Score`, or a `Noul` — with
probabilities. It does not generate text. So when a skill's job ends in a named
verdict (`SHIP` / `NEEDS_WORK`, a routing label, an approve/reject), you don't
have to run the whole skill to see where it lands. You extract the skill's own
outcome set, hand it to Jev as a closed `Choice`, and read the pick.

That's the whole idea: a slow, decision-shaped skill collapsed into one typed
prediction.

See [docs.typesafe.ai](https://docs.typesafe.ai/) for the model and API.

## When to use it

Invoke it as `/jev-predict-skill` or `jev-predict <skill>`.

Good targets are **closed-decision** skills — ones that end in a predetermined,
named set of outcomes (a review verdict, a phase choice, a router label). The
outcomes have to come from the target skill itself.

Not a fit: open-ended generation, freeform writing, or any skill whose result
isn't a finite named set. Those get a *no prediction* report, not a guess.

## Install

It's a single `SKILL.md`. Copy it where your agent looks for skills, or point
your agent at this repo.

- Skill file: [`SKILL.md`](SKILL.md) (mirror at
  [`.cursor/skills/jev-predict-skill/SKILL.md`](.cursor/skills/jev-predict-skill/SKILL.md)).
- Set `TYPESAFE_API_KEY` in the environment. The skill reads it at call time and
  never writes it into a file, a report, or a commit. Get a key at
  [typesafe.ai](https://typesafe.ai).

No package, no build step.

## Example

```
jev-predict /flow-next:impl-review
```

A successful run reports the pick and the numbers behind it:

```
predicted: SHIP
confidence: 0.86
probabilities:
  SHIP              0.86
  NEEDS_WORK        0.11
  none_of_the_above 0.03
breakdown noul: 0.78
```

When it can't stand behind a prediction, it says so and stops instead of
inventing an answer:

```
no prediction — assessment failed (401 auth)
```

## How it works

1. **Resolve** the argument — a skill file path, a directory with a `SKILL.md`, a
   slash/skill name it looks up under the usual skill roots, or pasted
   frontmatter.
2. **Gather** the read-only evidence that skill's next decision actually depends
   on, into Jev's `state`. Kept compact; the target skill is never run.
3. **Break down** — ask Jev (`type: noul`) whether the skill reduces to a closed
   set of outcomes. Below a `0.65` threshold it reports *cannot break down* and
   stops.
4. **Extract labels** — take the next decision's outcomes from the target skill
   itself (never invented), and always add `none_of_the_above`.
5. **Choose** — Jev picks one label (`type: choice`) and returns the confidence
   and probabilities. That's the answer.

[`SKILL.md`](SKILL.md) is the full contract — exact questions, thresholds, HTTP
and retry rules.

## Limits

- **Fails closed.** No prediction when the argument isn't a skill, can't be
  broken down, the Jev call fails (auth / HTTP / parse), or Jev returns
  `none_of_the_above`. A stop is a valid outcome.
- **One decision.** It predicts the *next* closed decision only, not a whole
  sequence of downstream picks.
- **The target owns the labels.** Outcomes come from the skill under prediction;
  this skill never makes up a label to fill the set.

## Links

- [`SKILL.md`](SKILL.md) — the skill and its contract
- [typesafe.ai](https://typesafe.ai) — TypeSafe
- [docs.typesafe.ai](https://docs.typesafe.ai/) — Jev / System One docs
