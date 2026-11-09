# pi-jev-skill-bench

Benchmark for [pi-jev-skill-suggestion](https://github.com/iamdin/pi-jev-skill-suggestion): **BM25 vs TypeSafe Jev** across roster sizes **50 / 100 / 200 / 500**.

This is an experiment harness, not a production claim. Token/USD numbers use documented assumptions (see `lib.ts`).

## What it measures

| Axis | What |
| --- | --- |
| Quality | exact (`hit` + `none_hit`), `wrong_skill`, `false_load`, `miss` |
| Categories | `clear`, `near-miss`, `quiet`, `adversarial` |
| Cost A | tokens saved by stripping `<available_skills>` |
| Cost B | Jev usage (live `--jev` only) |
| Cost C | extra `skill_suggest` tool round-trip (tool mode only) |
| Cache views | `A_naive` (full input), `A_cold` (~1.25× write), `A_warm` (~0.1× read) |

Net = `A − (B + C)`. Warm cache shrinks A a lot — that is intentional.

## Data

- `cases.jsonl` — 43 gold requests labeled against real skill names from the fixture catalogue
- Each tier roster **always includes every labeled skill**, then fills with a seeded sample

You need a skills directory (Pi-style `*/SKILL.md` folders). Default:

```text
../pi-jev-skill-suggestion-fixture/.pi/skills
```

Or set `SKILLS_DIR` / `--skills-dir`.

## Setup

```bash
bun install
```

## Run

BM25 only (no API key):

```bash
bun run.ts --skills-dir /path/to/.pi/skills
# or
bun run.ts --tiers 50,100
```

Live Jev (charges TypeSafe):

```bash
export TYPESAFE_API_KEY=ts_...
bun run.ts --jev --tiers 50,100,200,500
```

Writes `out/results-*.json` and `out/results-*.md`.

## Notes

- Uses `suggest()` from npm `pi-jev-skill-suggestion`
- Token counts are `chars/4` (relative), not a billed tokenizer
- `jev-auto` rows reuse Jev predictions with tool overhead `C = 0`
- Roster tiers default: 50, 100, 200, 500

## License

MIT
