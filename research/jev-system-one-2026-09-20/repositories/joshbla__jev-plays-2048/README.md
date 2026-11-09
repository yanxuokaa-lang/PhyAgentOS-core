# Jev plays 2048

A local, visible 2048 experiment powered by TypeSafe. The board, tile animations, merge rules, scoring, and random spawns come from Gabriele Cirulli’s original game. Jev picks the next move.

## Start

Use Node.js 22.12 or newer. Dependencies are already installed in this workspace.

```sh
npm start
```

Open **http://localhost:3000** and click **Start Jev**. Stop the local server with Ctrl+C. On a fresh checkout, run `npm install` first and put your TypeSafe API key in `.env.local`, following `.env.example`.

The server reads `.env.local`. The key stays server-side and is excluded from git. Port 3000 is fixed; free that port if another app is using it.

## Controls

- **Start / Pause / Resume:** run continuously or inspect the current position.
- **One move:** get one decision, then pause.
- **New game:** save the current played run to session results and start a fresh random board.
- **Playback pace:** full speed, watchable, or slow. These are maximum move rates; actual speed depends on TypeSafe latency.
- **Export JSON:** download all session runs, boards, candidate previews, exact requests/responses, and timings. Results live in this browser tab; export before refreshing or closing it.

The game stops when it reaches 2048, runs out of moves, or reaches 3,000 moves. It also pauses when the tab is hidden. Only the controller moves the board, so manual keyboard input cannot change a measured run.

## What Jev sees

One Choice question asks which legal move best preserves the ability to reach 2048. The input contains the current board and each legal move’s resulting board, score gain, and empty-cell count. Each move option has a short summary of the change in empty cells, score gain, and whether a largest tile is in any corner. Strategy guidance treats corner placement and tile ordering as useful trade-offs, allowing any direction and temporary disruption to improve the position. The original engine computes these one-step previews on detached grids, before the unknown random spawn. No search tree or separate solver chooses moves.

When only one move is legal, the controller takes that forced move without an API request. These moves are labeled in the panel and export. A failed request pauses the run without selecting a substitute move.

`server/questions.ts` contains the full instructions and the pinned model ID. Edit it and restart `npm start` to try different prompts.

## Reading the demo

API latency measures the server-to-TypeSafe round trip, including network travel and response handling. It is not pure inference time. Active time includes request time, game control, and playback pacing, but excludes pauses. Moves per second includes forced moves. Token totals reflect received decisions; requests canceled in flight may still be billed. Automatic API retries are disabled to keep latency measurements transparent.

Move probabilities express Jev’s preference among alternatives, not the probability of eventually winning. Several games are needed to assess success rate because tile spawns are random.

## Checks

```sh
npm run check
npm run build
```

## Original game and skill

The original game is vendored under `public/original-2048` from [gabrielecirulli/2048](https://github.com/gabrielecirulli/2048), commit `478b6ec346e3787f589e4af751378d06ded4cbbc`. Its MIT license is retained in `public/original-2048/LICENSE.txt`. `game.html` supplies the original board markup in an embedded page; `src/game.ts` connects the original engine to the controller.

The TypeSafe skill is installed project-locally under `.agents/skills/typesafe-ai`. Restart OpenCode for automatic discovery in a new session.
