# Jev Traffic Sim

Interactive top-down browser traffic simulator that compares three traffic-signal controllers — Fixed, Adaptive, and Jev — under identical seeded workloads, with a headless benchmark harness for reproducible runs. The simulation engine is framework-independent TypeScript; the browser UI renders it with Canvas 2D from a Web Worker.

## Tech stack

- Next.js (App Router) + TypeScript
- Tailwind CSS
- Zustand (UI state)
- Recharts (benchmark results)
- Canvas 2D rendering; Web Worker simulation loop
- Vitest (tests)

## Development

```bash
pnpm install     # install dependencies
pnpm dev         # start the dev server at http://localhost:3000
pnpm lint        # eslint
pnpm typecheck   # tsc --noEmit
pnpm test        # vitest run
pnpm build       # production build
```

The detailed product requirements document lives in `docs/` and is intentionally local-only — it is not committed to this repository.
