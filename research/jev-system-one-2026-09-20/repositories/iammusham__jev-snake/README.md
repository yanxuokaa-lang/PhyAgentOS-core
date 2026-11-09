# Jev Snake

An experimental Snake environment where the game engine owns deterministic rules and [TypeSafe AI's Jev](https://docs.typesafe.ai/sdk/python) makes the movement decision from structured state on every tick.

The project includes a browser-based human baseline and a pygame experiment client. Jev mode uses the same Python engine, replacing only the source of each requested direction.

## Architecture

```text
snake_game/
├── game.py       # pure game rules and state transitions
├── jev_agent.py  # typed Jev adapter
├── state.py      # game state -> JSON-compatible AI state
├── config.py     # defaults and environment overrides
├── main.py       # pygame loop, rendering, CLI, and research logs
├── web.py        # browser UI server and human-control WebSocket
└── web_static/   # dependency-free HTML/CSS/JavaScript frontend
```

The engine rejects an impossible 180-degree reversal, but it does not pathfind or override Jev's choice to avoid a wall, obstacle, or body collision. If the API fails, the explicitly logged fallback is to continue in the current direction.

## Local setup

Nothing needs to be installed globally. From this project directory, create and activate a virtual environment, then install all Python requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
```

These commands are instructions only; this repository does not automatically install packages.

## Play the human baseline in a browser

```bash
python -m snake_game.web
```

Open <http://127.0.0.1:8000>. Choose Human or Jev, a versioned difficulty, and a seed, then start the run. Human mode uses arrow keys or WASD. Jev mode sends the structured state to TypeSafe on every game tick and displays the returned choice, calibrated confidence, probability distribution, latency, and fallback errors live.

Jev mode requires `TYPESAFE_API_KEY`. Put it in the project-local `.env` (loaded when the server starts) or export it in the server process environment:

```bash
export TYPESAFE_API_KEY='your-key'
python -m snake_game.web
```

The browser never receives the API key. If a Jev request fails, the game logs the error and uses the explicit `fallback_keep_direction` policy for that tick; it does not silently pathfind for the model.

Human and Jev movement use the same fixed server clock. Jev inference runs asynchronously between movement ticks and cannot slow the board. When Jev misses a decision deadline, the snake holds its current direction for that tick and the miss is displayed and logged. The completed decision is applied at the next available tick. This keeps physical speed identical while making inference limitations visible rather than hiding them.

All three difficulty presets use the same 20×20 board and the same latency-safe speed of 1.5 moves/second for clean Human/Jev comparisons. Easy has no obstacles or decoys. Medium has 8 obstacles and 3 amber decoy fruits. Hard has 20 obstacles and 7 decoys. Red fruit scores; touching an amber decoy ends the run. Decoys reshuffle whenever real fruit is eaten, adding dynamic uncertainty without changing speed. Food, obstacles, and decoys are randomized by the recorded seed, so a run is both varied and exactly reproducible.

## Run the pygame client

Manual mode first:

```bash
python -m snake_game.main --mode manual
```

Use arrow keys or WASD. Space pauses, `R` restarts, and Escape quits.

For Jev mode, create an API key in the TypeSafe console and expose it only in your shell:

```bash
export TYPESAFE_API_KEY='your-key'
python -m snake_game.main --mode jev --log-file experiment.log
```

Useful experiment controls:

```bash
python -m snake_game.main \
  --mode jev \
  --width 20 --height 20 \
  --obstacles 12 \
  --tick-rate 5 \
  --seed 42 \
  --model jev-latest \
  --log-file experiment.log
```

Each tick logs JSON containing the full current state. Jev ticks additionally log its choice, confidence/probability distribution when exposed by the SDK, request latency, decision source, and any error. The terminal tick logs the final status, cause, score, and tick count.

## Tests

The engine tests do not require pygame or network access:

```bash
python -m pytest
```

## Benchmark validity

Snake does not have one official, widely adopted benchmark environment. This project therefore identifies every run with:

- environment version (`snake-jev-v2`)
- named difficulty preset
- exact random seed
- controller type
- score, survival ticks, and terminal reason

Do not claim that a single high score proves ability. Compare controllers over the same fixed seed suite and report score and survival distributions. Human runs provide one baseline; random, greedy, and Jev controllers can then be evaluated under identical rules. A future Gymnasium wrapper can expose this engine through the standard `reset`/`step` interface without changing its rules.
