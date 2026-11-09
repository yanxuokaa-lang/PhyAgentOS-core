# pong-jev

TypeSafe's Jev plays Atari Pong.

Jev is a System One model. It does not generate text. You give it a `state` and a
set of typed questions, and it returns structured answers with calibrated
probabilities. This project asks it one question per frame:

> Which way should I move my paddle right now? `up`, `down` or `stay`

Jev returns the choice, a probability for each option, and a confidence value.
Code moves the paddle.

## The design constraint

The jaggedness notes for `jev-1.13` say the model is weak at arithmetic,
counting and comparing magnitudes, and that unrelated detail in the `state`
costs accuracy. Pong is entirely numbers, so no coordinate is ever sent to the
model. `src/core.ts` does every calculation and sends five short phrases:

```json
{
  "ball_vertical_position": "far below my paddle",
  "ball_horizontal_position": "around the middle of the court",
  "ball_direction": "travelling towards my paddle",
  "ball_vertical_drift": "drifting downward",
  "my_paddle_position": "in the upper half of the court"
}
```

A test asserts that this payload contains no digits.

The vertical field is already relative. Code computes `ball_y - paddle_y` and
sorts the result into a bucket, so Jev never compares two positions. It receives
the comparison and decides what to do about it. The geometry lives in code and
Jev maps the relationship to an action, which is what the jaggedness notes ask
for.

Scores, opponent position, ball speed and court size are all left out. They do
not affect the decision, and extra detail in the `state` lowers accuracy.

`--encode raw` sends the coordinates instead, so you can measure what the
wording is worth rather than take my word for it.

## Running it

```bash
bun install
python3 -m venv .venv
.venv/bin/pip install "gymnasium[atari]" ale-py fastapi uvicorn numpy
cp .env.example .env    # add your TYPESAFE_API_KEY
```

The environment runs as its own process:

```bash
bun run bridge
```

Then the agent:

```bash
bun start                          # dashboard
bun start -- --headless            # one line per decision
bun start -- --policy heuristic    # code baseline, no API calls
```

Press space to start and stop, `s` to single step, `d` for the debug panel, `q`
to quit.

## Playing against it

```bash
bun start -- --duel            # first to 7
bun start -- --duel --aim      # harder
```

You are the left paddle, on `up`/`k` and `down`/`j`. Jev is the right paddle.
This runs on a local court in `src/sim.ts` instead of ALE, because ALE only
exposes one controllable paddle. The bridge is not needed.

## Latency

In watch mode, latency does not affect how well Jev plays. ALE only advances
when the agent steps it, so a slow call makes the game run in slow motion and
the paddle is never late.

In a duel the court runs in real time, so a 400ms round trip is real reaction
lag. Two flags reduce it.

`--aim` changes which question about the ball gets turned into words. By
default Jev is told where the ball is now, and that answer is 400ms stale by the
time it arrives. With `--aim`, code extrapolates the ball's path to the paddle,
including bounces off the top and bottom rails, and Jev is told where it will
arrive. That point does not change while the ball is in flight, so a slow reply
is still a correct one.

The difference shows up clearly when the ball is level with the paddle but
climbing. Without `--aim` the state reads "level with the centre of my paddle"
and Jev says stay, which loses the point. The ball bounces off the top rail and
lands at y=151, below the paddle. With `--aim` the state reads "clearly below my
paddle" and Jev moves down.

`--concurrency` overlaps calls, which is safe because they carry no session
state. Replies that finish out of order are dropped by sequence number, so an
older answer never overwrites a newer one. Measured over identical 30 second
windows:

| concurrency | calls in 30s | decision age | per-call latency | cost |
|---|---|---|---|---|
| 1 | 74 | 196ms | 379ms | $0.0016 |
| 3 | 221 | 111ms | 379ms | $0.0049 |

Per-call latency does not move, so the gain comes from overlapping. Cost scales
with the number of calls.

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--policy` | `jev` | `jev` or `heuristic` |
| `--encode` | `semantic` | `semantic`, `predictive`, `tactical` or `raw` |
| `--repeat` | `2` | env steps to hold each decision |
| `--min-confidence` | `0` | below this, fall back to the code heuristic |
| `--seed` | | env seed |
| `--max-steps` | `100000` | stop after N decisions |
| `--duel` | off | play against Jev |
| `--target` | `7` | points to win a duel |
| `--aim` | off | aim at the predicted arrival point |
| `--concurrency` | `3` | overlapping Jev calls in a duel |

## Layout

```
bridge/pong_bridge.py   ALE/Pong-v5 behind a JSON step API
src/core.ts             arithmetic, wording, the question, the baseline policy
src/jev.ts              TypeSafe System One client, one POST, no SDK
src/bridge.ts           HTTP client for the environment
src/agent.ts            the play loop, emits ticks and never prints
src/sim.ts              Pong simulator for duels
src/tui.ts              OpenTUI dashboard, owns all drawing
src/duel.ts             the duel screen
src/cli.ts              flags and entry point
```

`core.ts` and `sim.ts` are pure and `agent.ts` never prints, so the logic is
testable without a terminal and one agent drives both the dashboard and
`--headless`.

## What the environment actually does

Every value below was measured with `scripts/calibrate.py` rather than taken
from a reference, because getting any of them wrong looks exactly like a bad
policy.

| RAM address | Meaning |
|---|---|
| 49 | ball x |
| 54 | ball y, reads 0 between points |
| 50 | opponent paddle y |
| 51 | agent paddle y |
| 13, 14 | scores, unreliable |

Action 2 moves the paddle towards the top rail and action 3 towards the bottom.

`frameskip=2`. At 4 the paddle overshoots and a policy that tracks the ball
perfectly still loses 1-21.

`repeat_action_probability=0.0`. `ALE/Pong-v5` defaults to 0.25 sticky actions,
which on its own loses every game.

The playfield is x 68 to 190, not the 0 to 205 the ball's x byte suggests. The
paddles sit at 68 and 190 and nothing is drawn outside that span. Using the byte
range squashes the court to a third of its width and makes the ball appear to
bounce off nothing.

Score comes from rewards. The RAM bytes at 13 and 14 are not reliable counters,
and reading them produced a 21-2 scoreline after 146 decisions, which cannot
happen.

## Results

The code heuristic in `core.ts` wins 21-3 against the built-in Atari opponent.
It exists as a baseline and as the fallback when confidence is low.

Jev, on `--encode semantic` with no predictive help, led 7-4 after 3328
decisions in the run that was going as this was written. Confidence tracks the
position: around 0.99 when the ball is clearly above or below the paddle, and
0.25 to 0.55 in ambiguous frames. `--min-confidence` turns that into a fallback
to the heuristic, and I have not yet swept it to see whether it improves the
score.

## Cost

Input tokens only, at $42 per billion, with output free. A decision is about 520
input tokens, so 1000 decisions costs roughly $0.02.
