# sudoku-jev

A sudoku game (and a two-player chess game at `/chess`) that an AI decision model plays. The browser makes a random puzzle and opens a websocket. A click on **Solve** starts the loop. The backend sends the board and every legal placement to the TypeSafe Jev model through OpenRouter. Jev picks one placement. The browser applies it, reports the new board, and the loop runs until the puzzle is solved or the model makes three mistakes.

Jev is a decision model, not a text model. It rates a list of options and returns one choice with probabilities. It does not compute, so the code does the sudoku rules and gives Jev only legal moves. Each option carries the digits that fit in its cell. Jev decides between them.

A visual explanation of the loop, with a captured request and response, is on [GitHub Pages](https://jaysonsantos.github.io/sudoku-jev/).

## Run

```sh
cp .env.example .env   # set OPENROUTER_API_KEY
direnv allow           # loads .env and the nix shell
pnpm install --frozen-lockfile
pnpm build
pnpm start             # http://localhost:8080
```

The `.envrc` file has two lines and stays local:

```sh
dotenv_if_exists
use flake
```

With Docker:

```sh
docker build -t sudoku-jev .
docker run --rm -p 8080:8080 -e OPENROUTER_API_KEY=... sudoku-jev
```

## Configure

Every setting is a long flag, an environment variable, and a default. A flag wins over the variable.

| Flag | Variable | Default | Meaning |
|---|---|---|---|
| `--openrouter-api-key` | `OPENROUTER_API_KEY` | none, required | OpenRouter API key |
| `--openrouter-url` | `OPENROUTER_URL` | `https://openrouter.ai/api/alpha/decisions` | Decisions endpoint |
| `--jev-model` | `JEV_MODEL` | `typesafe/jev-1.13` | Model id on OpenRouter |
| `--port` | `PORT` | `8080` | Listen port |
| `--host` | `HOST` | `0.0.0.0` | Listen address |
| `--static-dir` | `STATIC_DIR` | `frontend/dist` | Frontend build to serve |

`node backend/src/main.ts health` calls the health route and exits with a nonzero code on failure. The Docker image uses it as the health check.

## How the loop works

1. The browser generates a puzzle with one solution and keeps the solution.
2. **Solve** starts the loop. After every change the browser sends `{ type: "state", board, rejected, mistakes, status }` on `/ws`.
3. The backend computes the legal placements, drops the rejected ones, and asks Jev one `choice` question per batch of 255 options. Option ids look like `row_3_col_7_value_5`.
4. The backend answers `{ type: "decision", move, probability, confidence, ... }`.
5. The browser checks the move against the solution. A right value fills the cell. A wrong value counts as a mistake and joins `rejected`. Three mistakes lose the game. **Pause** stops the loop, **New game** makes a new puzzle.

## Develop

```sh
pnpm dev          # backend on 8080, Vite on 5173 with a proxy for /ws
scripts/lint.sh   # prek run --all-files
scripts/test.sh   # typecheck and node --test
scripts/all.sh    # lint, test, build
```

Layout: `shared/` holds the sudoku and chess rules and message types, `backend/` the Node server, `cloudflare/` the Worker and Durable Object, `frontend/` the React app, `test/` the suites. See `AGENTS.md` for the rules of the repository.

## Chess

`/chess` is the same SPA and the same `/ws` session. One shared chessboard.js board shows the same position to both sides. White and Black each have a color label and a countdown clock on that board. The side to move asks Jev for its play.

1. **Play** starts the loop. The browser sends `{ type: "state", game: "chess", fen, rejected, status }`.
2. The backend lists legal UCIs with chess.js, sorts them, and keeps at most 150. Option ids look like `uci_e2e4`.
3. Jev returns the most probable play. The backend checks the pick is legal. An illegal or unknown pick is dropped and the same position is asked once more. A second failure is an error.
4. The browser applies a legal move on the shared board and the other color becomes the side to move.

## Cloudflare

The SPA needs a Worker to terminate `/ws`. Cloudflare Workflows cannot hold a WebSocket; this app uses a Durable Object instead.

| Item | Value |
|---|---|
| Routes | `/` sudoku SPA, `/chess` chess SPA, `/ws` GameSession, `/healthz` |
| Health | `/healthz` |
| Binding | `GAME_SESSION` |
| Class | `GameSession` |
| Isolation | one Durable Object per browser session (`getByName` with a new UUID) |

`wrangler.jsonc` runs the Worker first for `/ws` and `/healthz`. Everything else is the Vite SPA in `frontend/dist`.

```sh
pnpm build
cp .dev.vars.example .dev.vars   # set OPENROUTER_API_KEY for local wrangler
pnpm cf:dev                      # wrangler dev, SPA + /ws
```

Deploy:

```sh
pnpm exec wrangler secret put OPENROUTER_API_KEY
pnpm cf:deploy
```

`OPENROUTER_URL` and `JEV_MODEL` are Wrangler vars with the same defaults as the Node server. After deploy the browser talks to `wss://<worker-host>/ws`.

A preview upload (`wrangler versions upload`, used by Workers Builds on non-`main` branches) cannot create the `GameSession` namespace. The first production `wrangler deploy` (or the Workers Build on `main`) provisions the Durable Object and binds `GAME_SESSION`.

## Release

Commits follow Conventional Commits. The version and the changelog come from the history.

```sh
scripts/release.sh        # bump, changelog, commit, annotated tag
git push --follow-tags    # release.yml builds the image and publishes the release
```

The same release runs from the Actions tab with the `release-tag` workflow.
