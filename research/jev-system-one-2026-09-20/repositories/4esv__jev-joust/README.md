# jev-joust

Two [TypeSafe Jev](https://typesafe.ai) players, one per controller, in NES Joust. Requires `rom/joust.nes`.

![Jev vs Jev](runs/jev-vs-jev-20260919-160528.gif)

One match per row, 2026-09-19, `jev-latest`, 2-player game A, up to 3600 frames; a match ends early when a player is out.

| player 1 | player 2 | frames | lives lost | score | Jev calls | cost |
|---|---|---|---|---|---|---|
| jev | jev | 1280 | 3 / 5 | 1000 / 1000 | 320 | $0.013 |
| jev | rules | 2896 | 5 / 4 | 2250 / 3500 | 362 | $0.013 |
| rules | jev | 1208 | 2 / 5 | 1000 / 250 | 151 | $0.006 |
| jev | jev-tactic | 1584 | 2 / 5 | 1000 / 1000 | 396 | $0.013 |
| jev-tactic | jev | 1824 | 5 / 5 | 500 / 750 | 456 | $0.017 |
| jev-tactic | rules | 3600 | 5 / 3 | 1750 / 5000 | 450 | $0.014 |
| rules | jev-tactic | 3600 | 3 / 5 | 2750 / 1750 | 450 | $0.013 |
| rules | rules | 3600 | 5 / 5 | 2750 / 750 | 0 | $0.000 |

| bot | seats | lives lost per 1000 frames | score per 1000 frames |
|---|---|---|---|
| `rules` | 6 | 1.19 | 851 |
| `jev-tactic` | 4 | 1.89 | 471 |
| `jev` | 6 | 2.48 | 621 |

`jev`'s flap Noul follows the situation; its stick Choice barely does. Over 239 decisions: mean p(flap) 0.77 with the nearest rider more than 20 px above, 0.67 within 20 px of level, 0.47 and 0.46 with it 20–60 and over 60 px below, 0.80 within 25 px of the floor. The stick pointed toward a lower rider in 38 of 60 decisions and away from a higher one in 27 of 47.

Median Jev latency 0.19 s; about 900 input tokens per `jev` call, 720 per `jev-tactic` call.

## Run

```bash
cp .env.example .env        # TYPESAFE_API_KEY
uv sync
uv run python joust.py --play --p1 jev --p2 jev       # a match; bots are jev, jev-tactic, rules or idle
uv run python joust.py --play --p1 jev --p2 rules --max-frames 7200
uv run python joust.py --scan       # hold each input on each controller, print RAM addresses that move with it
uv run python joust.py --frames     # scripted inputs on both controllers, writes runs/smoke.gif
```

A match writes `runs/<p1>-vs-<p2>-<stamp>.gif`, a `.json` with every state, answer and controller plan, and a line in `runs/results.jsonl`. It ends when a player is out of lives or at `--max-frames` (default 3600, one minute of game time).

## Notes

- Every 8 frames each player gets its own view of the game as JSON: itself, then every other rider nearest first, as a sentence plus numbers. Both requests run concurrently; the emulator waits for them.
- `jev` holds the controller: a Choice (`left`, `right`, `none`) is the stick and a Noul is the flap button, flapping at one press per 4 frames while the answer is 0.5 or more.
- `jev-tactic` answers one Choice (`attack`, `climb`, `evade`) and code flies it. `rules` picks among the same tactics with fixed thresholds and shares that executor.
- Flap rates, measured from open air over 48 frames: no flaps falls 90 px, one per 12 frames falls 49, one per 6 holds height, one per 4 climbs 38.
- Platforms and eggs are not in the state.
- RAM map (no published one; found with `--scan`, by matching bytes against sprite positions, and by reading the HUD):

| bytes | meaning |
|---|---|
| `0x54+p`, `0x58+p` | player x, y; y = 240 while dead |
| `0xE9+p` | respawns left |
| `0xEB..0xED`, `0xEE..0xF0` | score, BCD, low byte first |
| `0x720+i`, `0x72E+i`, i < 7 | enemy x, y; y = 240 is an empty slot |

- Boot: the title appears near frame 600; Select three times moves the cursor to `2 PLAYER GAME A`, then Start.
- nes-py wires only controller 0 through `step()`; `Joust.step(p1, p2)` writes controller 1's buffer before stepping.
- Snapshot/restore via nes-py's `_backup`/`_restore`, as in [jev-mario](https://github.com/4esv/jev-mario).
