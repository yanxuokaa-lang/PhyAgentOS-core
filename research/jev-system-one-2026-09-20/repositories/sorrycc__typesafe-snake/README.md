# jev plays snake

TypeSafe's Jev (a System One decision model, not an LLM) plays Snake in real time.
Code generates the legal moves and exact facts about each one (food distance, reachable
cells via flood fill, dead ends); Jev picks one with a single `choice` question per step.
If the answer misses the tick deadline, the snake just keeps going straight.

## Run

```sh
cp .env.example .env   # set TYPESAFE_API_KEY
pnpm install
pnpm dev               # web http://localhost:5188, proxy http://127.0.0.1:8787
```

The API key lives only in the Hono proxy (`server/index.ts`); the browser calls `/api/decide`.

## Layout

- `src/game/engine.ts` – pure snake engine (seeded RNG)
- `src/game/analysis.ts` – legal moves, flood fill, dead-end detection, fallback move
- `src/game/controller.ts` – fixed-clock loop: ask Jev at tick start, play what arrived at tick end
- `src/jev/prompt.ts` – state + choice question sent to Jev, strategy presets
- `server/index.ts` – `POST /api/decide` via `@typesafe-ai/sdk`
- `src/components/` – dark dashboard UI: `Board` (canvas, interpolates the snake between ticks), `StrategyBar`, `StatusCard`, `CurrentDecision`, `DecisionFeed`

`pnpm test` runs the engine and controller tests, `pnpm typecheck` runs tsc.
