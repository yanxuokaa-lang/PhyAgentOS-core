# NanoJev viewer

**A nano replica of [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev).** The English interface reads recorded model results from local JSON files. It uses plain HTML, CSS, and JavaScript, with no framework or external scripts.

**[Open the standalone side-by-side site](https://nanojev.tianyuchen99.chatgpt.site)** · [Snake](https://nanojev.tianyuchen99.chatgpt.site/#snake) · [Maze](https://nanojev.tianyuchen99.chatgpt.site/#maze)

From the repository root:

```bash
python3 -m http.server 8080 --bind 127.0.0.1 --directory web
```

Open **http://127.0.0.1:8080/side-by-side.html** for the light three-panel comparison. Add `#snake` or `#maze` to open a game directly. The dark arcade remains at `http://127.0.0.1:8080/arcade.html`, the earlier comparison at `http://127.0.0.1:8080/comparison.html`, and the decision lab at `http://127.0.0.1:8080`. Serve only the `web` directory. Opening the HTML as a local file can prevent JSON loading.

The main viewer offers model and episode selection, step controls, playback, action probabilities, recorded execution details, and parallel batches. V2 and V3 have different evaluation cohorts; their summaries remain separate. Sampled controllers display the action that was actually taken, including when it differs from the most probable action. Completed trajectories hold their final state.

## Light side-by-side comparison

[![Jev, NanoJev, and Untuned Qwen exploring the maze side by side](../assets/side_by_side_maze.png)](https://nanojev.tianyuchen99.chatgpt.site/#maze)

[Download the maze video (MP4)](../assets/side_by_side_maze.mp4) · 27 seconds · 1440 × 1120 · 30 fps

`side-by-side.html` reads `side_by_side_results.json` and displays **Jev / NanoJev / Untuned Qwen** together. All panels advance by the same environment step. Each completed run freezes at its recorded final state while the others continue. Each frame's probability bars describe the last decision that produced that state; frame zero has no decision probabilities.

The maze uses four independent safety probabilities without normalizing them across directions. Shared exploration code orders edges and repositions through verified paths. Its real native-Qwen baseline reaches the goal in **4,726 attempts with 2,044 collisions**. The original dark arcade still contains the separate **Starting NanoJev** run: 171 attempts and 43 collisions.

Snake uses conditional probabilities over the candidates offered by the common safety and food planner. A single remaining candidate is a forced code move. Its three complete runs remain unchanged: NanoJev collects 27 food over 256 steps, Jev 30 over 256, and Untuned Qwen 25 over 211 before becoming trapped. [Source identities, hashes, and replay checks](../assets/side_by_side_data_manifest.json).

Rebuild the separate comparison data from its recorded sources:

```bash
python3 scripts/build_side_by_side_demo.py --overwrite
```

This performs CPU replay checks and leaves the old arcade data and media unchanged. The source files listed in the manifest must be available locally, including the native maze result and the three selected Snake reports.

To stage the standalone static website, pass an existing ChatGPT Sites project whose `.openai/hosting.json` already defines `static.directory` as `dist`:

```bash
python3 scripts/stage_comparison_site.py --project /path/to/site-project
```

The staging script copies the comparison page, styling, script, and recorded data into that project's `dist/` directory, using the comparison page as `index.html`. It also records the staged file hashes. The separate project keeps hosting configuration outside the model repository.


To export the maze webpage as a shareable MP4:

```bash
node scripts/capture_side_by_side_video.mjs \
  --web-root web --output runs/maze_video --work runs/maze_video_frames \
  --playwright-module /path/to/playwright/index.mjs \
  --ffmpeg /path/to/ffmpeg --chrome /path/to/chrome
```

The video keeps all three systems on the same environment-step timeline and pauses briefly at goal arrivals. It includes the complete run through the last system's final state. The output directory contains the MP4 and its recording manifest; existing video files are never overwritten.

## Maze + Snake: open the decision arcade

The [arcade](arcade.html) reads `arcade_results.json` and replays two recorded showcase runs, with actual actions, probabilities, and complete final outcomes.

- **50×50 maze:** NanoJev reaches the goal in 244 attempts with 36 collisions; Jev uses 2,738 attempts with 1,044 collisions; Starting NanoJev uses 171 attempts with 43 collisions. Models judge local edges while the same exploration code maintains movement memory. Starting NanoJev is an earlier trained checkpoint.
- **12×12 Snake, seed 61005, greedy control:** NanoJev collects 27 food in 256 steps, Jev 30 in 256, and untuned Qwen 25 in 211 before becoming trapped. The common planner filters immediate collisions and ranks static food paths; each model chooses among remaining tied candidates. Single-candidate moves are forced by code.

[Recorded sources and replay verification](../assets/arcade_data_manifest.json) · [Maze GIF](../assets/arcade_maze.gif) / [MP4](../assets/arcade_maze.mp4) · [Snake GIF](../assets/arcade_snake.gif) / [MP4](../assets/arcade_snake.mp4)

The GIFs and MP4s follow NanoJev's complete runs. Use the model tabs to replay the other systems, including their terminal states. The [eight-case comparison](../results/arcade_controller_comparison.json) records both tested controllers; the showcase uses one selected Snake controller for every system.

To recreate the arcade media from its included data, install Playwright and FFmpeg and provide their local paths:

```bash
node scripts/capture_arcade.mjs \
  --web-root web --data web/arcade_results.json \
  --output runs/arcade_media --work runs/arcade_capture \
  --steps-per-second 16 \
  --playwright-module /path/to/playwright/index.mjs \
  --ffmpeg /path/to/ffmpeg \
  --chrome /path/to/chrome
```

The capture checks visible playback controls, every rendered NanoJev state, all six terminal states, and mobile layout. It uses a local allowlisted server and makes no model calls. The [media manifest](../assets/arcade_media_manifest.json) records file hashes and encoded durations.

## Earlier navigation showcase

The showcase presents **NanoJev / Jev / Untuned Qwen** on two TEST maps and two OOD maps. These maps were selected by outcome: NanoJev and Jev reached the goal while Untuned Qwen reached the step limit under both greedy and sampling controllers. The [selection record](../research/nanojev_showcase_selection.json) contains the four episode IDs, rule, actual outcomes, and source hashes. The [showcase notes](../research/nanojev_showcase.md) explain the selection.

Each MP4 includes all four selected cases. Playback advances by environment step. A completed panel stays at its recorded final state while the other trajectories continue. Each GIF includes the **complete first case**, including the unsuccessful baseline's full step horizon and a final outcome hold. The PNG poster shows that case's actual final state.

The six source trajectory files remain unchanged. The reader JSON contains the drawing fields needed for these 24 recorded trajectories. It retains original action probabilities, sampled actions, and source/checkpoint hashes.

## Recreate the earlier comparison media

Rendering requires Python, Node.js, Playwright, Chrome, and FFmpeg with libx264. The static viewer requires none of these tools. The renderer reads existing trajectories and makes no API or GPU calls.

Use the source filenames recorded in the manifest to construct a fresh render. Set the two tool paths below to your local installations:

```bash
python3 - <<'PY'
import json
import subprocess
from pathlib import Path

manifest = json.loads(Path('assets/comparison_media_manifest.json').read_text())
command = ['python3', 'scripts/render_comparison_video.py']
for source in manifest['sources']:
    command += ['--' + source['role'], str(Path('research') / source['artifact'])]
command += [
    '--ffmpeg', '/path/to/ffmpeg',
    '--playwright-module', '/path/to/playwright/index.mjs',
    '--data-output', '/tmp/nanojev-showcase-new.json',
    '--output-dir', '/tmp/nanojev-showcase-new-media',
]
subprocess.run(command, check=True)
PY
```

Outputs must use new paths. The script refuses to replace existing files. `--assemble-only` validates and writes reader data without launching Chrome or encoding video. `--steps-per-second` controls environment-step playback; its default is 4.

The media manifest records source, renderer, reader, and media SHA256 hashes, as well as per-frame episode IDs and environment steps. Capture checks every rendered frame against the recorded state and action and verifies the expected final outcomes for all selected cases. The playback check records real Chrome interaction and exported-video decoding checks.

## Result data

The main viewer reads `demo_results.json`:

```json
{
  "models": [
    {
      "name": "Model display name",
      "checkpoint_sha256": "Recorded checkpoint hash",
      "summary": {},
      "episodes": []
    }
  ],
  "parallel_batches": [],
  "sources": []
}
```

An episode contains `id`, `game`, `split`, `initial_state`, `steps`, and `outcome`, with optional `final_state`. Each step can include `state`, `action`, `next_state`, `probabilities`, `controller`, `distribution_argmax`, `sample_uniform_draw`, `forced`, and `model_forward`. The viewer uses `step.action` for the executed action. Original question and state text may retain the language of the recorded input.

Supported environment states:

```text
grid_navigation: { game, size, walls:[[row,col],...], position:[row,col], goal:[row,col] }
tic_tac_toe:       { game, board:"Nine characters: . / X / O", player:"X or O" }
```

Grid coordinates are zero-based. Unknown environment schemas are shown as JSON. A missing result file produces an empty state.

Parallel batches contain `states` and recorded `execution` fields such as `forward_passes` and `total_paths`. The interface uses those records for its execution counters. Boolean probabilities can be displayed as `false: 1-p_true` and `true: p_true`; the original response remains available.

## Optional inference endpoint

The live form posts its JSON to the same origin at `/api/evaluate`. A model server must implement this endpoint; Python's static HTTP server does not. The usual request shape is `{states:[{id,state,questions}]}` and the response shape is `{states:[{id,answers}],execution}`.

The interface shows the actual response and browser round-trip duration. The backend should load the model once and record its actual forward-pass metadata. API credentials are never embedded in the page.

## Checks

```bash
node --check web/app.js
node --check web/comparison.js
node --check scripts/capture_comparison.mjs
node --check web/arcade.js
node --check scripts/capture_arcade.mjs
node --check web/side-by-side.js
node --check scripts/check_side_by_side.mjs
python3 scripts/test_composed_snake.py
```

The side-by-side browser check compares the displayed states with the exact recording JSON, exercises playback controls, and checks desktop and mobile layouts:

```bash
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
CHROME_EXECUTABLE=/path/to/chrome \
node scripts/check_side_by_side.mjs \
  --web-root web --output-dir runs/comparison_check
```

Replace `--web-root web` with `--url https://nanojev.tianyuchen99.chatgpt.site/` to check the public site in an isolated browser. Use a new output directory for each run. [Published-site browser results](../assets/side_by_side_browser_check.json).

The exported media and viewer were checked with isolated, unsigned-in Chrome 153 and Playwright 1.63. Detailed results are in [the playback check](../assets/comparison_playback_check.json) and [the media manifest](../assets/comparison_media_manifest.json). FFmpeg 7.1 encodes the H.264/yuv420p MP4 files; Pillow is used only for optional GIF frame inspection.
