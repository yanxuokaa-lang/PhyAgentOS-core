# Tetris / Jev

[한국어](README.ko.md)

Watch TypeSafe Jev play a familiar 10 x 20 falling-block game. A desktop Pygame
window shows animated placements, upcoming pieces, score, line clears, and Jev's
placement probabilities and response latency.

## Watch the two players

Same seed. Same 60-piece budget. Same 2x animation speed. Two different decision makers.
Click a preview to watch the full gameplay video.

| Jev / live API decisions | Offline / fixed board heuristic |
| --- | --- |
| [![Jev gameplay preview](media/jev-preview.gif)](media/jev.mp4) | [![Offline gameplay preview](media/offline-preview.gif)](media/offline.mp4) |
| [Full gameplay — 1:15](media/jev.mp4) · [Screenshot](media/jev.png) | [Full gameplay — 0:29](media/offline.mp4) · [Screenshot](media/offline.png) |

### Demo results

| Metric | Jev | Offline |
| --- | ---: | ---: |
| Seed | 42 | 42 |
| Pieces placed | 60 | 60 |
| Lines cleared | 22 | 22 |
| Score | 3,800 | 3,700 |
| Final maximum height | 3 | 3 |
| Final holes | 1 | 1 |
| API calls | 60 | 0 |
| Mean decision latency | 770 ms | Not measured; no API |
| End condition | Piece limit | Piece limit |

This is **one demonstration, not a benchmark of general superiority**. The score difference
comes from the timing and grouping of line clears under level-scaled scoring. Neither run
topped out. Model decisions and latency may vary on a repeat run.

## Run on Windows

Prerequisites: Python 3.13+ and [uv](https://docs.astral.sh/uv/).
Clone this repository and open its directory:

```powershell
git clone https://github.com/chahero/tetris-jev.git
cd tetris-jev
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"
Copy-Item .env.example .env  # Only on first setup; do not overwrite an existing key.
```

Set `TYPESAFE_API_KEY=your-key` in `.env`, then double-click `play.cmd` or run:

```powershell
.\.venv\Scripts\tetris-jev.exe
```

The installed editable app loads `.env` from this project directory, regardless
of the terminal's working directory. Environment variables take precedence.
Never commit `.env`. API requests incur normal provider usage charges.

For an offline demonstration, double-click `play-offline.cmd` or use:

```powershell
.\.venv\Scripts\tetris-jev.exe --policy heuristic
```

Controls: **Space** pause/resume, **R** restart with the same seed, **+/-** cycle
animation speed, **Esc/Q** close. Buttons provide the same controls. Restart is
disabled while a request is in flight. Pause prevents new requests and freezes
animation; one already-started request may complete. Errors pause the run and
show a retry button, never silently switch to the offline policy.

The default budget is **200 pieces per run**, with at most one API request per
piece (no automatic retries). The window stays open at the limit or top-out.
Restart begins a new run with a fresh budget. Change the limit with `--max-pieces`.

## What Jev controls

This is **placement-based Tetris**, not a real-time keyboard agent or an official
Tetris rules implementation. Jev chooses among every legal vertical-drop
placement (unique rotation + column). The engine calculates landing positions
and each candidate's resulting height, holes, bumpiness and cleared lines.
Candidates are not ranked or pruned by a heuristic before being sent to Jev.
The selected move is then animated and committed. The board never advances
while inference is pending, so network latency cannot interrupt a jump or drop.

- 7-bag piece generator; reproducible seed and next-three preview.
- No hold, wall kicks, tucks, T-spins, combos or real-time gravity.
- A candidate must fit at row zero and descend vertically; top-out means no legal drop remains.
- Score: 100 / 300 / 500 / 800 for 1 / 2 / 3 / 4 lines, multiplied by the
  level before clearing (1 + total lines // 10).
- Offline mode uses a simple weighted board heuristic; its UI does not invent
  confidence or probability values.
- Jev does inference only. Running more games does not train model weights.

## Logs and experiments

JSONL logs in `artifacts/` include run seed and policy, the exact decision input,
chosen placement, probabilities, actual post-placement board, score changes,
errors, episode boundaries and final state. API keys are never recorded.
Candidate descriptions can be reconstructed from the recorded board and piece
with `engine.placements`. Compare policies using the same seed and piece budget:

```powershell
.\.venv\Scripts\tetris-jev.exe --headless --policy heuristic --seed 42 --max-pieces 200
.\.venv\Scripts\tetris-jev.exe --headless --policy jev --seed 42 --max-pieces 200
```

Animation speed changes viewing speed, not the board supplied to the model.
The API uses a 15-second HTTP timeout and no automatic retries. There is one
background request at a time; closing the UI does not wait for its daemon worker.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\ruff.exe format --check src tests
```

`engine.py` owns deterministic rules, `policy.py` owns Jev/offline decisions,
and `app.py` owns the UI, run lifecycle and logging. The game uses procedurally
drawn blocks and system fonts, with no external game artwork or ROMs.

To open the window without making API calls yet, use `--paused` and press Space when ready.
