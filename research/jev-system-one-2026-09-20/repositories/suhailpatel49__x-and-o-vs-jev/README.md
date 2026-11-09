# X & O vs Jev

A browser tic-tac-toe game where you play **X** and TypeSafe Jev plays **O**.
The app sends the board to the TypeSafe System One API. Jev returns typed answers and probabilities. The browser code owns the game rules and applies the selected move.

## Requirements

- Node.js 18 or later
- A [TypeSafe API key](https://console.typesafe.ai/keys)

The project has no package dependencies. You do not need to run `npm install`.

## Run locally

From this directory, run:

```bash
node server.js
```

Open [http://localhost:3000](http://localhost:3000), enter your TypeSafe API key, and start a game.

Do not open `index.html` directly. The browser must use `server.js` as a same-origin proxy for the TypeSafe API.

To use a different port:

```bash
PORT=8080 node server.js
```

## Game controls

- **New game** starts a game with you as the first player.
- **New game, Jev starts** starts a game with Jev as the first player.
- **Give Jev tactical hints** adds code-calculated wins and blocks to the move options.
- **Jev's top choice** uses the highest-probability move returned by Jev.
- **Sample from probabilities** samples a move from Jev's probability distribution.
- **Retry Jev's move** retries a failed or timed-out request without changing the board.
- **Change API key** replaces the saved browser key.

The side panel shows the pre-move board, move probabilities, confidence, threat assessment, optimal-play outlook, request time, and token usage.

## How a Jev move works

Each turn sends one request with the board state and three questions:

| Question | Type | Purpose |
| --- | --- | --- |
| `move` | Choice | Select one legal empty cell for O. |
| `threat` | Noul | Estimate whether X has an immediate one-move win. |
| `outlook` | Score | Evaluate the position as an X forced win, optimal draw, or O forced win. |

The app validates the response before it changes the board. It rejects missing, malformed, or illegal move answers. It retries rate limits and server errors up to two times after the first attempt.

See the [TypeSafe API reference](https://docs.typesafe.ai/api) for the request and response format.

## API key and privacy

The browser saves the API key in `localStorage` when storage is available. If storage is blocked, the key stays in memory for the current page session. The browser sends the key to the local proxy in the `Authorization` header.

`server.js` forwards the request to TypeSafe. It does not store or log the API key or request body. Clear this site's browser data to remove the saved key.

The server is a small local development server. It has no user authentication. Do not expose it directly to the public internet.

## Environment variables

| Variable | Used by | Default |
| --- | --- | --- |
| `PORT` | `server.js` | `3000` |
| `TYPESAFE_API_URL` | `server.js`, `live-check.js` | `https://api.typesafe.ai/v1/systemone` |
| `TYPESAFE_KEY` | `live-check.js` | None |

`TYPESAFE_API_URL` is useful for testing with a compatible non-production endpoint.

## Run the live API check

The live check sends one real board position to TypeSafe and validates the response shape and move quality. It can use `TYPESAFE_KEY` from the environment, `./.env`, or `../.env`.

```bash
TYPESAFE_KEY=your_key node live-check.js
```

Or create an ignored `.env` file:

```dotenv
TYPESAFE_KEY=your_key
```

Then run:

```bash
node live-check.js
```

The check does not print the API key. It calls the real API and can consume API usage.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | User interface, game rules, request building, response validation, and browser state. |
| `server.js` | Static file server and same-origin API proxy. |
| `live-check.js` | Manual live API check. |
| `.gitignore` | Excludes API keys, dependencies, and local system files. |
