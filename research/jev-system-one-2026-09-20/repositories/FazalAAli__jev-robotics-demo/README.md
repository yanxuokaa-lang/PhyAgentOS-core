# Jev vs LLM: robot arm control

A simulated Franka arm with a 4-finger Allegro hand (MuJoCo) stacks a blue cube on a red one, driven by two
kinds of AI:

- **`agent.py`**: an LLM (Claude Opus 5 by default) with three low-level tools: `move_hand_to(x, y, z)`,
  `set_hand(closed)`, `get_state()`. It reasons through every step itself.
- **`jev_agent.py`**: [Jev](https://typesafe.ai) by TypeSafe, a "System One" model that answers typed questions
  with probabilities in a few hundred ms. Code proposes small moves and simulates each one ahead in a scratch
  copy of the physics; Jev picks the move, decides when to grasp and release, and decides when the task is done.
  The design follows [jev_fsd](https://github.com/BrendanH18/jev_fsd): code owns the math, Jev owns the judgment.

One recorded run each:

|              | Claude Opus 5 | Jev     |
|--------------|---------------|---------|
| Result       | stacked       | stacked |
| Time         | 158.8 s       | 19.1 s  |
| Cost         | $0.75         | $0.0006 |

That Opus run needed one retry; clean first-try Opus runs took about 55 s and $0.19.
Times include arm motion at real speed.

## Setup (macOS or Linux)

```sh
nix develop                                   # Python 3.12 + uv (or bring your own Python 3.12 and uv)
uv venv .venv && uv pip install --python .venv -r requirements.txt

# Robot models from MuJoCo Menagerie (only the two we need)
git clone --depth 1 --filter=blob:none --sparse https://github.com/google-deepmind/mujoco_menagerie.git menagerie
git -C menagerie sparse-checkout set franka_emika_panda wonik_allegro
```

On macOS, anything that opens the viewer must run with `mjpython` (installed with `mujoco`), not `python`.

Check the sim works (scripted pick-up, no AI):

```sh
.venv/bin/mjpython robot.py            # with viewer
.venv/bin/python robot.py --headless   # asserts the cube is lifted
```

## API keys

Keys are read from environment variables only. Set them without echoing them into your shell history:

```sh
read -s TYPESAFE_API_KEY && export TYPESAFE_API_KEY      # Jev: request early access at console.typesafe.ai
read -s OPENROUTER_API_KEY && export OPENROUTER_API_KEY  # LLM via OpenRouter...
read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY    # ...or directly via Anthropic (used if no OpenRouter key)
```

## Run

```sh
TASK="Put the blue cube on top of the red cube. The stack must stay standing after the hand lets go."

.venv/bin/mjpython jev_agent.py "$TASK"                      # Jev, with viewer
.venv/bin/mjpython agent.py "$TASK"                          # LLM, with viewer
MODEL=z-ai/glm-5.3 .venv/bin/mjpython agent.py "$TASK"       # any OpenRouter model with tool support
```

Add `--headless` to run without a window (much faster: arm motion isn't paced to real time). Each run ends by
printing a `TIME:` and `COST:` line (Jev: $0.042 per million input tokens, output free; Opus 5: $5 / $25 per
million input / output tokens, list price).

## Making the video

Runs are recorded headless and rendered offscreen, so there are no windows or screen capture involved.

```sh
# 1. Record (retry until you like the run)
RECORD=videos/jev.npz  .venv/bin/python jev_agent.py --headless
RECORD=videos/opus.npz .venv/bin/python agent.py --headless "$TASK"

# 2. Render each run to a 720x1440 portrait MP4 (title, live clock and cost, latest log line).
#    Optional third argument: playback speed for the run itself (the 3 s final hold stays at 1x).
nix-shell -p ffmpeg   # or any ffmpeg on PATH
.venv/bin/python replay.py videos/jev.npz  videos/jev.mp4
.venv/bin/python replay.py videos/opus.npz videos/opus_3x.mp4 3

# 3. Side by side as a 1080x1080 square (the shorter clip holds its last frame)
ffmpeg -i videos/opus_3x.mp4 -i videos/jev.mp4 -filter_complex \
  "[1:v]tpad=stop_mode=clone:stop_duration=300[b];[0:v][b]hstack=inputs=2:shortest=1,scale=1080:1080[v]" \
  -map "[v]" -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart videos/side_by_side.mp4
```

The replay clock is the live-equivalent time: real wall time while the model was thinking, plus simulated time
while the arm moved.

`record.py` is the older approach: it screen-records the live viewer window (needs Screen Recording permission
for your terminal on macOS).

## Files

| File | What it does |
|------|--------------|
| `scene.py` | Builds the scene from Menagerie: Franka arm, Allegro hand mounted palm-to-flange, two cubes |
| `robot.py` | Sim wrapper: inverse kinematics, hand poses, real-time stepping, viewer overlay, run recording |
| `agent.py` | LLM agent (Anthropic SDK tool runner; OpenRouter or Anthropic) |
| `jev_agent.py` | Jev agent: sense, sample, simulate, ask |
| `replay.py` | Renders a recorded run to MP4 |
| `record.py` | Screen-records a live viewer run (macOS) |

## License

MIT. The robot models come from [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) under
their own licenses and are not included in this repo.
