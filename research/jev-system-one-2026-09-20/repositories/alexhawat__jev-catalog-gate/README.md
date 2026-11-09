# jev-catalog-gate

Pre-LLM **catalog gate**: score tools and skills with [TypeSafe](https://typesafe.ai) / Jev, keep only high-probability items before the model call.

**Status:** scaffolding. Public MIT. Python monorepo.

## Surfaces (planned)

| Package / adapter | Role |
|-------------------|------|
| `packages/core` | Host-agnostic gate (`score` / `filter`) |
| `packages/cli` | `jev-catalog-gate` CLI |
| `adapters/skill` | Soft skill wrapper (calls CLI) |
| `adapters/hook` | Cursor / Claude Code pre-turn hook |
| `adapters/mcp` | MCP gateway (advertise only survivors) |
| `adapters/harness` | Drop-in middleware for agent loops |

## License

MIT
