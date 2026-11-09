# Ormus Jev resources

Open teaching pack for **TypeSafe Jev** (System One) as Ormus uses it inside Grok Bot and coding agents.

> Study seeds: [@DataChaz 10 steps](https://x.com/DataChaz/status/2101206777924858319) · [@AIGuide_](https://x.com/AIGuide_/status/2101119480361361685) → [article](https://x.com/i/article/2100744524951932928) · Canonical docs: [docs.typesafe.ai](https://docs.typesafe.ai)

## What Jev is

A typed decision model: state + questions → **Choice**, **Score**, **Noul** (not free-form chat). Confidence is returned by the model; never invent it.

Division of labor: **code computes**, **LLMs create**, **Jev decides**, humans Approve irreversible side effects.

## Ormus three lanes

1. **Decision gate** — before send / pay / merge / cancel  
2. **Claim verify** — claims vs evidence  
3. **Context screen** — untrusted text before it enters context (filter, not a hard security boundary)

See [docs/three-lanes.md](docs/three-lanes.md).

## Jev suite map

Thin public repos that teach one primitive or pattern each (seeded from the DataChaz 10-step roadmap). Hub stays here; siblings stay focused.

| Repo | Focus | Seed step |
|------|--------|-----------|
| [jev-primitives](https://github.com/HermeticOrmus/jev-primitives) | Choice / Score / Noul explainers + examples | 1–4 |
| [jev-decision-gate](https://github.com/HermeticOrmus/jev-decision-gate) | Bounded forks (agent / model / tool / human escalate) | 6 |
| [jev-batch-decisions](https://github.com/HermeticOrmus/jev-batch-decisions) | Batch vs sequential decisions | 5 |
| [jev-rank-wide-read-narrow](https://github.com/HermeticOrmus/jev-rank-wide-read-narrow) | Shortlist wide, then spend compute narrow | 8 |
| [jev-state-questions-action-verify](https://github.com/HermeticOrmus/jev-state-questions-action-verify) | State → Questions → Action → Verify loop | 9 |
| [jev-grok-bot](https://github.com/HermeticOrmus/jev-grok-bot) | Grok Bot wiring (extends this hub) | — |
| [jev-anti-jobs](https://github.com/HermeticOrmus/jev-anti-jobs) | Keep Jev out of math / writing / irreversible exec | 10 |
| [jev-benchmark-loop](https://github.com/HermeticOrmus/jev-benchmark-loop) | Benchmark the whole agent loop, not single calls | 7 |

## Quick paths (this hub)

| Path | File |
|------|------|
| Grok Bot setup | [docs/grok-bot-setup.md](docs/grok-bot-setup.md) |
| Public skill | [skills/jev-in-grok-bot/SKILL.md](skills/jev-in-grok-bot/SKILL.md) |
| Example packs | [examples/](examples/) |
| Study notes | [docs/study-notes.md](docs/study-notes.md) |

## Gold Hat

Empower installers. Never pack API keys. Name `TYPESAFE_API_KEY` + Jev MCP in installer memory only. See [GOLD_HAT.md](GOLD_HAT.md).

**Claim hygiene:** never invent or repeat unverified speed/cost multipliers as Ormus claims. If TypeSafe or DataChaz publish figures, attribute them — or omit numbers and teach the pattern.

## Related

- TypeSafe skills: https://github.com/typesafe-ai/skills  
- Ormus Jev Desk bot template (scrubbed, no keys) — ask Diego / Auric for export after Approve  

## License

MIT. Jev / TypeSafe product terms remain with TypeSafe AI.

## Suite (extended 2026-09-19)

### Lanes
- [jev-confidence-routing](https://github.com/HermeticOrmus/jev-confidence-routing)
- [jev-mcp-setup](https://github.com/HermeticOrmus/jev-mcp-setup)
- [jev-claim-verify](https://github.com/HermeticOrmus/jev-claim-verify)
- [jev-context-screen](https://github.com/HermeticOrmus/jev-context-screen)

### Also
- [jev-primitives](https://github.com/HermeticOrmus/jev-primitives) · [jev-decision-gate](https://github.com/HermeticOrmus/jev-decision-gate) · [jev-batch-decisions](https://github.com/HermeticOrmus/jev-batch-decisions) · [jev-rank-wide-read-narrow](https://github.com/HermeticOrmus/jev-rank-wide-read-narrow) · [jev-state-questions-action-verify](https://github.com/HermeticOrmus/jev-state-questions-action-verify) · [jev-grok-bot](https://github.com/HermeticOrmus/jev-grok-bot) · [jev-anti-jobs](https://github.com/HermeticOrmus/jev-anti-jobs) · [jev-benchmark-loop](https://github.com/HermeticOrmus/jev-benchmark-loop)

### Grok Build Libre ports
See org: LibreUIUX / SessionFlow / GEO / DevOps / SecOps / Embed / GameDev / FinTech / Mobile / MLOps / Arch / Copy `-Grok-Build`.
