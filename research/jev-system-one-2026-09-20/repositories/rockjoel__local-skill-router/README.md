# local-skill-router

**Local-first skill router for coding agents** (Cursor, Claude Code, Codex, …).

> Phase 1 of every agent setup: *“I’ll just add one more skill.”*  
> Phase 2: the context window looks like lasagna.  
> Phase 3: this repo.

If you’ve ever watched an agent politely load **twelve** playbooks for “hi”, burn a pile of tokens, and still pick the wrong one — welcome. You’re among friends.

This tool picks **at most one** skill — or proudly returns **`none`** — from a small catalog **you** control.

- **Default: offline** (no API, milliseconds — your wallet can breathe)
- **Prefer `none`** over a wrong match (silence is a feature)
- **Thin always-on** mindset: don’t pay rent on rules you don’t need every turn
- **Optional** second-pass judge when local is unsure — plug in what you like
- **You own the catalog** — random GitHub skill dumps are *data*, not gospel (prompt injection is a thing)

## Inspiration (and what this is *not*)

This project was **inspired by [TypeSafe Jev](https://typesafe.ai)** — typed “System One” judgment instead of dumping more prose into every chat. Building and shipping this repo happened **thanks to that idea**.

**Not an official TypeSafe / Jev product.** No affiliation claimed. Just a portable pattern:

1. Route locally first (fast, free, fail-open).
2. If ambiguous, ask a **judge**: Jev today, or any future System One–style API, rules engine, or your own heuristic tomorrow.
3. Open **one** skill — or none.

Swap the judge; keep the idea. That’s the point.

## The plot twist (short version)

Stacking skills feels productive. Until it doesn’t.  
Overlapping triggers, stale instructions, always-on bloat, mysterious loops.

Treat routing as a **decision**, not “paste more markdown into every chat.”  
Boring is how you keep tokens.

## Quickstart

```bash
python tests/test_router.py
python -m skill_router.router "got a 429 on download"
python -m skill_router.router "hello"
```

Example output:

```json
{
  "ok": true,
  "skill": "rate-limit-helper",
  "reason": "alias",
  "provider": "local",
  "candidates": ["rate-limit-helper"]
}
```

`"hello"` → `none`. The agent can just say hello. Revolutionary.

Edit `examples/catalog.md` (or pass `--catalog path/to/your.md`).

## How it works

1. **Greeting / empty** → `none`
2. **Alias hit** (keywords in the catalog) → that skill
3. **Token overlap** with the “when” column → best skill, or `none` if weak / ambiguous
4. Agent opens **one** `SKILL.md` (or none). Never glob the whole skills folder like it’s an all-you-can-eat buffet.

## Optional judge (Jev *or* whatever you prefer)

When local returns `none` / `ambiguous`, you can call a second layer:

- **[TypeSafe Jev](https://typesafe.ai)** — what inspired this, and what some setups use in production
- **Any other** typed-judgment / classifier / rules — same contract: pick a skill id or `none`
- **Nothing** — stay fully offline; the local router is enough for many cases

Keep **fail-open**: if the judge is down, keep the local result.  
This repo ships **without** API keys or vendor lock-in on purpose.

## Agent skill (optional)

Copy `agent/SKILL.md` into your agent skills folder if you want the agent to run the CLI when unsure.

**TIP 001:** on a real task (not a greeting), run the router **before** the big model guesses which skill to open — then load at most that one `SKILL.md`.

## Why this beats “skill maximalism”

| The lasagna path | This path |
|---|---|
| Always-on mega-rules | Thin always-on + route on demand |
| Load many skills “just in case” | Max **one** skill or **none** |
| One vendor forever | Local first; judge is swappable |
| Trust random GitHub skill dumps | Catalog is yours; foreign text is untrusted |

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Forks and pull requests welcome.  
If you open a PR that adds “always load 40 skills”, I will gently send you back to Phase 1.
