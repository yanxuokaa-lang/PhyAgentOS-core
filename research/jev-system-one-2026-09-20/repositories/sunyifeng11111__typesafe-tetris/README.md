# TypeSafe Tetris

**English** | [简体中文](README_zh.md)

![TypeSafe Tetris interface](assets/typesafe-tetris-stack-lab.png)

An autonomous Tetris experiment played entirely by **JEV**. The browser owns the board and seven-bag queue, a local stack analyzer ranks legal placements, and TypeSafe System One selects where each tetromino lands.

> [!IMPORTANT]
> TypeSafe can select only from the legal placements supplied for the current piece. It cannot invent a rotation or column. The local gateway rebuilds the candidate set and validates every response before the browser applies it.

## Features

- JEV plays the complete run, with every tetromino placement selected through TypeSafe
- Standard 10×20 board with a deterministic seven-bag piece sequence
- Three profiles: Sprint / 20 lines, Marathon / 40 lines, and Endurance / 100 lines
- Every legal rotation and column is evaluated locally; the best 12 candidates are sent to TypeSafe
- Stack evaluation accounts for line clears, aggregate height, peak height, holes, bumpiness, and wells
- TypeSafe sees the locked board, current piece, and three-piece preview queue
- Decisions animate from the top of the board before locking and clearing lines
- API failures pause the current run and can be retried without changing the board
- Candidate probabilities, confidence, latency, tokens, and decision history remain inspectable

## How it works

```text
Board and seven-bag queue in the browser
        ↓ enumerate every legal landing
Local stack analyzer
        ↓ top 12 candidate placements
TypeSafe System One
        ↓ select exactly one supplied placement
Local gateway validates the response
        ↓
Browser animates, locks, clears lines, and starts the next turn
```

The local analyzer simulates every legal rotation and column for the current tetromino. It scores the resulting board, sends only the strongest bounded option set to TypeSafe, and keeps execution strictly sequential: decide, animate, lock, clear, then continue.

## Quick start

Install [Node.js](https://nodejs.org/) and [pnpm](https://pnpm.io/), then run:

```bash
pnpm install
cp .env.example .env
```

Add your TypeSafe API key to `.env`:

```dotenv
TYPESAFE_API_KEY=your_api_key
PORT=8789
```

Start the development environment:

```bash
pnpm dev
```

- Game UI: <http://127.0.0.1:5191>
- Local decision gateway: <http://127.0.0.1:8789>
- Health check: <http://127.0.0.1:8789/decision/health>

> [!CAUTION]
> Never expose a real API key in frontend code or commit it to Git. Keep it only in the ignored `.env` file used by the local gateway.

## Interface guide

- **01 Stack observation** — the 10×20 board, falling piece, current piece, and three-piece preview.
- **02 Run parameters** — line target, decision interval, and the strategy brief sent to TypeSafe.
- **03 Link telemetry** — request count, successful answers, average latency, and input tokens.
- **04 Current option set** — supplied rotations and columns, local scores, and TypeSafe choice probabilities.
- **05 Decision record** — applied placements, stack evidence, cleared lines, confidence, and response latency.

## Run profiles

| Profile | Board | Target |
| --- | ---: | ---: |
| Sprint | 10×20 | 20 lines |
| Marathon | 10×20 | 40 lines |
| Endurance | 10×20 | 100 lines |

A run succeeds when it reaches the selected line target. It ends early if the stack reaches the ceiling and no legal placement remains.

## Decision boundary

Each request to the local gateway contains:

- the locked 10×20 board
- the current tetromino
- the next three tetrominoes
- the current line count, target, score, combo, and step
- the operator-editable strategy brief

The gateway independently rebuilds the legal candidate set and rejects any response outside it. The remaining seven-bag order, random generator state, browser controller state, and API key never enter the request body.

## Project structure

```text
src/domain/tetris.ts              Tetris rules, seven-bag queue, locking, and line clears
src/domain/strategy.ts            Legal-placement enumeration and stack evaluation
src/application/autopilot.ts      Autonomous decision, animation, and run state machine
src/infrastructure/remoteJudge.ts Browser adapter for the gateway
src/ui/                           React interface and playfield rendering
server/gateway.ts                 Local TypeSafe decision gateway
```

## Commands

| Command | Purpose |
| --- | --- |
| `pnpm dev` | Start the game UI and local gateway |
| `pnpm test` | Run engine, strategy, and controller tests |
| `pnpm typecheck` | Check TypeScript types |
| `pnpm build` | Create a production build |

## Verification

```bash
pnpm test
pnpm typecheck
pnpm build
```

The test suite covers deterministic seven-bag generation, legal placement enumeration, locking and line clears, ceiling collisions, ranked candidate generation, line-clear promotion, public-observation isolation, gateway failure recovery, request cancellation, visible falling animation, and pausing during a drop.

---

This project's concept was inspired by the Snake project [sorrycc/typesafe-snake](https://github.com/sorrycc/typesafe-snake); its code, interface, Tetris engine, stack analyzer, and API contract are independently implemented.
