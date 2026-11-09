# Jev Realms

A terminal-only ASCII role-playing game where every non-player character thinks with [Jev](https://typesafe.ai), TypeSafe AI's System One decision model. No dialogue generation, no narrative LLM — just hundreds of tiny, calibrated judgments per play session driving classic RPG behavior: bandits weighing ambush odds, guards reading intent, vendors haggling, wolves picking targets.

**Status: design draft.** This repository currently contains the complete design documentation (game design, Jev AI architecture, roadmap). Implementation has not started. See [Roadmap](docs/ROADMAP.md) for the build order.

## Why

Jev's pitch is *lots of small, cheap, typed decisions inside normal software* instead of one big text-generation call. A game is the most honest way to test that claim: the game loop already runs 10–20 times per second, the NPCs need thousands of decisions per session, and every decision is observable — you watch a bandit charge or flee and know exactly which judgment produced it.

This repo is that test, shaped as a game worth playing.

## What it is

```
        ┌─────────────────────────────────────────────┐
        │            W I L D E R M O O R               │
        │  ~~~~   ♠♠♠   ¶¶¶   ~~~~   ♠♠♠   ≡≡≡        │
        │ Forest Forest Forest Forest Forest Forest   │
        │   [player moves one tile east]               │
        │                                             │
        │ Forest: three bandits notice you.            │
        │                                             │
        │   bandit-1:  hostile=0.91  flee=0.04  → ATTACK│
        │   bandit-2:  hostile=0.34  flee=0.58  → FLEE │
        │   bandit-3:  hostile=0.72  flee=0.19  → ATTACK│
        │                                             │
        │   bandit-2 runs. bandit-1 and 3 charge.     │
        └─────────────────────────────────────────────┘
```

- **World**: hand-authored + procedurally mixed overworld (forests, roads, mountains, rivers), three walled cities, three multi-floor dungeons. ASCII rendering, 60×30 viewport, scrolling camera.
- **NPCs**: townfolk (vendors, guards, thieves, commoners, travellers), wilderness AI (bandits, wolves, bears), dungeon denizens and bosses. Each has personality, needs, and a memory of you.
- **Combat**: turn-based tactical on the grid, spacing, flanking, flee mechanics — decisive when outnumbered.
- **Jev as the brain**: every NPC decision point is a batched Jev query; normal Rust code owns everything else. See [AI architecture](docs/AI_ARCHITECTURE.md).

## Tech stack

| Layer | Choice | Rationale |
| --- | --- | --- |
| Language | Rust | Performance for the world sim, safety for the AI glue, and it's fun |
| UI | `ratatui` + `crossterm` | The de-facto terminal UI stack; widget layers, modal overlays, input polling |
| AI | Jev via Vercel AI Gateway (`typesafe-ai/jev`) | Typed, calibrated decisions at $0.042/1M input tokens; one HTTP client in `jev_client.rs` |
| Storage | none yet | Deterministic world seeding planned (Roadmap M6); game is session-scoped until then |

Rust toolchain edition 2021+ is assumed (`cargo build` / `cargo run` once implementation begins).

## The decision budget

Running every NPC through Jev every tick would be wasteful and silly. The design budget, per in-game turn:

| Tier | Trigger | NPC count | Latency allowance | Example |
| --- | --- | --- | --- | --- |
| 0 — reflex | every tick | all active | none (pure Rust) | pathfind, wander, repath |
| 1 — tactical | per event | ≤ 8 | 150 ms | hostile-flee tradeoff, target pick |
| 2 — social | on interaction | 1 | 300 ms | vendor haggling, guard interrogation |
| 3 — strategic | every N turns | ≤ 1 | 800 ms | dungeon-boss phases, mentor advice |
| 4 — oracle | user-invoked | 1 | 1500 ms | prophecy, artifact identification |

Details and batching strategy: [AI architecture](docs/AI_ARCHITECTURE.md).

## Repository layout (planned)

```
jev-realms/
├── README.md
├── docs/
│   ├── GAME_DESIGN.md      # world, systems, content
│   ├── AI_ARCHITECTURE.md  # Jev integration design
│   └── ROADMAP.md          # milestones M0–M7
├── src/                    # (implementation, future)
├── .gitignore
└── LICENSE
```

## Running

Not yet runnable. When implementation starts:

```bash
export AI_GATEWAY_API_KEY="vck_..."   # your Vercel AI Gateway key
cargo run --release
```

An offline deterministic-decisions mode is planned (Roadmap M2) so the game is playable without an API key — Jev then becomes an enhancement, not a dependency.

## License

MIT
