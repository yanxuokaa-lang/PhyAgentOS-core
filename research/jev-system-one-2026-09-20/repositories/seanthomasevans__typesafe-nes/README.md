# typesafe-nes

Jev, TypeSafe's non-generative decision model, plays NES games through stable-retro:
Super Mario Bros., Contra, and Mega Man. A companion repo does the same for Doom through ViZDoom.

Every few frames, code reads the game's RAM and writes a few lines of plain words about the
situation. One TypeSafe request asks a handful of typed questions in parallel (Choice, Score,
Noul). Code turns the answers into controller buttons. Jev never sees pixels and never
generates text; it returns a choice, a score, or a probability, with calibrated confidence.

## What Jev decides, and what code does

| Game | Jev is asked, every 6 frames | Code owns |
|---|---|---|
| Super Mario Bros. | move (run, jump, stomp, wait), danger (Score), stomp (Noul), full_speed (Noul) | RAM to words, the tile scan (gaps, walls), takeoff frame and A-hold length from gap width or wall height, a run-up state machine for tall pipes, edge refusal |
| Contra | danger (Score), move (run, jump, prone, hold), aim (forward, up, diagonal up, diagonal down), fire (Noul) | Sprite-list perception (objects, size, position, motion), fire cadence, stuck-jump |
| Mega Man | danger (Score), move (run, jump, climb, hold, back_up), fire (Noul) | Sprite-list perception, ladder search when stuck (ladders are background tiles) |

Every code decision is logged as an override in red on the side panel and in `decisions.jsonl`,
next to the exact words Jev saw and every probability it returned. That log is the point: you
can see per frame what was the model's judgment and what was the harness.

## Results (2026-09-18, single runs)

| Game | Outcome | Median latency | Cost |
|---|---|---|---|
| Super Mario Bros. | World 1-1 completed, 340 on the clock, one death | 175 to 200 ms per decision | about $0.02 per game-minute |
| Contra | Jungle to screen 9, several deaths | about 210 ms | about $0.02 per game-minute |
| Mega Man | Climbs the first ladder of Cut Man's stage, then stalls | about 200 ms | about $0.02 per game-minute |

The harness carries game knowledge (jump physics tables, which enemies are stompable, the
run-up maneuver). Jev decides what to do; code decides the exact frame. If you want a stricter
split, remove the timing tables from `mariobot/brain.py` and let Jev pick jump and hold length
itself; it dies a lot more, which is itself the data point.

## Setup

You supply your own ROMs. They are never part of this repository (`refs/` is gitignored).

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
echo 'TYPESAFE_API_KEY=...' > .env

# Build the stable-retro integration for each ROM you have (the Mario one also accepts the
# Super Mario Bros. + Duck Hunt combo cart; the RAM layout is the same):
.venv/bin/python make_integration.py --game mario   --rom "/path/to/Super Mario Bros.nes"
.venv/bin/python make_integration.py --game contra  --rom "/path/to/Contra (USA).nes"
.venv/bin/python make_integration.py --game megaman --rom "/path/to/Mega Man (USA).nes"
```

## Run

```bash
.venv/bin/python run.py         --seconds 180 --show   # Mario
.venv/bin/python run_contra.py  --seconds 180 --show   # Contra
.venv/bin/python run_megaman.py --seconds 180 --show   # Mega Man
```

`--show` opens a live window (game at 2x plus the judgment panel). Each run writes
`runs/<name>/run.mp4`, `decisions.jsonl`, and `summary.json`, and regenerates `runs/index.html`,
a viewer of every run with its numbers and video. `probe.py` runs Mario with no Jev calls, to
check perception.

## Things learned the hard way

- nes-py loads these ROMs but its controller input never registered here; three probes were
  watching Contra's attract demo (its GAME OVER letters are 8x16 sprites that look like lives
  icons). stable-retro's cores work. The Contra wrapper now treats the demo's lives byte (98) and
  the absence of medal sprites as "not a game".
- Super Mario Bros. keeps its tile map in a two-page ring buffer; columns past the screen's right
  edge hold stale data. Trust only what is on screen or you get phantom gaps.
- The game jumps only on a fresh A press. Holding A across decisions leaves Mario standing at a
  pipe with the button down.
- Jev reads literally. "A wall or a ladder is probably in the way" produced ninety seconds of
  holding up where there was no ladder.

## Layout

- `nesbot/` generic pieces: `sprites.py` (OAM shadow at 0x200 to objects with motion),
  `runner.py` (loop, recorder, logs), `panel.py`
- `mariobot/`, `contrabot/`, `megabot/` per-game emulator wrapper, perception, questions, policy
- `make_index.py` builds `runs/index.html`

MIT. Built with the TypeSafe Python SDK against jev-1.13.0.
