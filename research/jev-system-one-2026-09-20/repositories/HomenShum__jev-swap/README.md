# jev-swap

**Swap a System 2 pipeline component for a System 1 TypeSafe Jev decision without breaking
what depended on it.** Investigation first, original pipeline kept as the live fallback,
promotion only on paired live evaluation that an independent judge re-ran.

A [Claude Code](https://claude.com/claude-code) skill. Also readable as plain instructions by
any coding agent that can follow a markdown file.

---

## Why

Jev returns typed decisions, `Choice`, `Score`, or `Noul`, in a few hundred milliseconds for
about $0.04 per million input tokens. Most LLM calls inside a pipeline are not writing
anything; they are deciding something and then getting parsed. Those are swap candidates.

The trap is that the component you are replacing owned more than its label. It cited a
source, computed an offset, wrote an explanation, set a cache key, flipped a UI state. Swap
the call for a typed decision that returns a valid label and every one of those can break
while every type check passes. A valid decision type does not guarantee a correct decision,
and a correct decision does not guarantee a correct downstream outcome.

So this skill refuses to start at the swap:

> Preserve the component's responsibility, not merely its response schema.

## The loop

```
GRASP ──> GATHER ──> PLAN ──> WORK ──> JUDGE
 name     trace      shape    swap +   re-run,
 the      every      fall-    3 arms   never
 job      consumer   back     live     read
```

| Phase | Who | Output |
| --- | --- | --- |
| GRASP | Planner (strong model) | one-sentence responsibility claim, or an early KEEP |
| GATHER | cheap worker subagents fan out, Planner consolidates | responsibility map: every output field with producer now / producer after / consumers / invariant / evidence, plus a frozen case set with five planted controls |
| PLAN | Planner | migration shape, Jev questions written against the documented failure modes, versioned fallback policy, eval design with a falsifier and a budget |
| WORK | cheap workers | adapter behind `JEV_SWAP_MODE`, three arms executed through the real entrypoint, eval card written by the runner |
| JUDGE | fresh-context judge | KEEP / REJECT / NEEDS_EVIDENCE, then QUALIFIED_CANDIDATE or BLOCKED; PROMOTED only after deploy plus readback |

## Five migration shapes

| Shape | When |
| --- | --- |
| KEEP | generation, arithmetic, dates, exact extraction, multi-hop; or no case set can be built |
| REPLACE | the whole contract is one bounded decision |
| SPLIT | Jev decides, the original model keeps the explanation or new text |
| CASCADE | Jev above a versioned threshold, the original below it and on every failure |
| VERIFY | Jev screens generated output without becoming its source of truth |

## Three arms, always

| Arm | Runs | Exists because |
| --- | --- | --- |
| A | original only | the supported baseline; zero Jev calls or it is contaminated |
| B | Jev only, raw | the candidate's true quality and calibration |
| C | Jev with fallback | what production would run; alone it can hide a candidate that falls back on every case |

Both isolated (same intermediate input) and end-to-end (own upstream outputs). Raw
probabilities and the threshold policy version are kept beside every decision.

## The gate

```bash
python scripts/gate.py swap/<component>
python scripts/gate.py --self-test
```

Stdlib only. Fails the packet when a field is owned by Jev but is arithmetic, a date, an
exact string, or generated text; when any field has no evidence; when a planted control is
missing; when arm B or C made zero Jev calls; when arm A made any; when the critical-error
rate is above the ceiling or above the baseline; when the fallback rate is at the ceiling;
when graders changed between plan and eval; when the map or card still carries the template's
illustrative marker or `REPLACE_ME` residue; when a status claims versions it does not carry;
when PROMOTED has no readback. A verdict of KEEP over failing evidence is itself a failure.

## Install

Claude Code, user-level:

```bash
git clone https://github.com/HomenShum/jev-swap ~/.claude/skills/jev-swap
```

Project-level: clone into `.claude/skills/jev-swap`. Then `/jev-swap <component>` or just ask
to "swap this to Jev". Any other agent: point it at `SKILL.md`.

Pair it with TypeSafe's own [agent skill](https://github.com/typesafe-ai/skills) for the
request and response shapes; this one adds the investigation, the fallback and the proof.

## Layout

```
SKILL.md                      the loop, roles, hard gates, stop rules
reference/JEV-CONTRACT.md     endpoint, primitives, answer fields, limits, jaggedness (docs as of 2026-09-18)
reference/RESPONSIBILITY-MAP.md   GRASP and GATHER: what to trace, map schema, case set
reference/MIGRATION-SHAPES.md     PLAN: shapes, question design, fallback design, eval design, worked example
reference/EVAL.md             WORK and JUDGE: arms, metrics, judge protocol, verdicts, human handoff
templates/                    responsibility-map.json, swap-plan.md, eval-card.json, worker-packet.md
scripts/gate.py               the mechanical gate
```

## What is deliberately not here

- No runtime library. The decision boundary is a few dozen lines in the target repo's own
  language, and the SDKs (`typesafe-sdk`, `@typesafe-ai/sdk`) already retry and type the
  answers. A generic wrapper would be copied blindly; a checked plan cannot be.
- No use-case catalog. Whether a component should be swapped is decided by its map, not by a
  list.
- No claims about Jev's accuracy on your data, and no measurements of Jev at all: no live Jev
  call was made while building this skill. The skill exists because that number has to be
  measured in your pipeline, three arms, live.

## Provenance

Designed 2026-09-18 from three ChatGPT design threads on TypeSafe Jev adoption and
planner-worker-judge campaigns, from docs.typesafe.ai as read that day (API reference,
models, primitives, confidence, SDKs, fan-out pattern, and the jev-1.13 jaggedness page),
and from the browser-use `jev-ultrafast` README (github.com/browser-use/jev-ultrafast) for
the one non-TypeSafe example in the contract file. The failure-mode table in
`reference/JEV-CONTRACT.md` is TypeSafe's own; re-verify before quoting it onward.

## License

MIT
